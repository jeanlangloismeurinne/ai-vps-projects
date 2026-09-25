"""Le contrat de `qualite_info` — la MESURE de qualité d'information d'un dossier (spec §7, lot 6).

`qualite_info` cesse d'être un jugement du modèle (`RiskMatrix`, un `float` posé par l'analyse) pour
devenir une **dérivée mécanique** des `framework_answers` : part des statuts, part de réponses
périmées, rang moyen des sources. C'est une mesure, plus une appréciation.

POURQUOI CE N'EST PAS UN `float` NU
------------------------------------
Un score qui n'apparaît que comme un nombre dans un blob n'est pas lu, et surtout n'est pas
CONTESTABLE (`feedback_controle_au_point_de_lecture` — c'est ce qui a coûté une journée à la
capacité 4). Le comité doit pouvoir lire POURQUOI le score vaut ce qu'il vaut : combien de questions
s'appliquent, combien sont périmées, sur quelles sources. D'où un objet structuré dont le niveau 3
du parcours affiche chaque composante.

LES QUATRE ARBITRAGES DU FONDS (rendus par l'utilisateur, 2026-09-25)
--------------------------------------------------------------------
  1. `sans_objet` → HORS BASE. Un fonds qui constate qu'une question n'a pas d'objet pour l'émetteur
     (rentabilité du capital pour une biotech pré-revenus) ne se pénalise pas : il sort la question
     du calcul. La qualité d'info ne mesure QUE les questions qui s'appliquent. Si toutes sont hors
     objet, ce n'est pas « 0 % » mais un troisième état nommé (`aucune_question_applicable`, #44).
  2. `approxime` → AUCUNE décote au STATUT. Une approximation aux hypothèses écrites est une réponse
     légitime ; sa moindre qualité est DÉJÀ portée par son rang (la doctrine du cran dégrade A → A−
     pour une reconstruction, `project_synthesis_tier_rule`). La décoter une 2ᵉ fois compterait deux
     fois la même chose (#46). `repondu` et `approxime` valent donc le même crédit de base.
  3. Le tier → PUBLIÉ (`rang_moyen`), JAMAIS fondu dans le scalaire. Un fonds distingue une réponse
     adossée à un 10-K d'une réponse de presse — mais la spec §7 range le rang moyen comme ingrédient
     SÉPARÉ. Le fondre dans `score` recombinerait des axes en un scalaire (interdit #50) et compterait
     deux fois le plancher (qui garantit déjà le tier minimum par question). Le comité lit la solidité
     des sources à côté du score ; la comparaison de `rang_moyen` n'est valable qu'à framework +
     version égaux (écart V9 — d'où les deux champs portés ici).
  4. `perimee` → crédit 0 pour le score du JOUR ; la réponse n'est jamais supprimée pour autant. Une
     information périmée ne fonde pas une décision fraîche (il faut l'actualiser), mais l'historique
     garde sa valeur pour lire les trajectoires — c'est le SCORE qui décote, pas la donnée qui
     disparaît. `indeterminable` (fraîcheur non vérifiable, #53) décote aussi à 0 mais reste COMPTÉ
     à part : son remède est « rendre datable », pas « re-collecter plus récent ».

CE QUE CE CONTRAT INTERDIT
---------------------------
  · `extra='forbid'` (via `Strict`) — aucun champ hors contrat.
  · un `score` sans base, ou une base sans `score` : `score` existe SI ET SEULEMENT SI au moins une
    question s'applique. L'absence de question applicable est un état NOMMÉ, jamais un `score` de 0
    qui se lirait « dossier de mauvaise qualité » là où la vérité est « ce cadre ne s'applique pas ».
  · agréger les `qualite_info` de plusieurs frameworks en un score unique de « qualité du dossier » —
    ce contrat est PAR framework, il n'a nulle part où écrire un agrégat (interdit spec §7 / #50).

Cible pydantic v2 (container backend). Le python hôte peut être en v1 → tester en container.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field, model_validator

from .analysis_v2_schemas import Strict, Tier

__all__ = ["QualiteInfo", "FACTEUR_ACTUALITE"]


# Détenteur unique du crédit d'actualité (#46). `perimee` et `indeterminable` valent 0 pour des
# raisons DIFFÉRENTES (l'une est datée et dépassée, l'autre n'est pas datable) — d'où deux compteurs
# distincts, mais le même effet sur le score du jour : ni l'une ni l'autre ne fonde une décision
# fraîche. `courante` seule vaut plein crédit.
FACTEUR_ACTUALITE: dict[str, float] = {
    "courante": 1.0,
    "perimee": 0.0,
    "indeterminable": 0.0,
}


class QualiteInfo(Strict):
    """La qualité d'information d'UN dossier pour UN framework, à UNE version. Recalculée à la
    lecture (#53/#54) — jamais persistée, jamais reçue en entrée."""

    schema_version: Literal["v3.0.0"] = "v3.0.0"
    framework_id: str = Field(min_length=1)
    framework_version: str = Field(min_length=1)

    # `mesure` : au moins une question s'applique, `score` est un nombre.
    # `aucune_question_applicable` : toutes hors objet — `score` est None, pas 0 (#44).
    etat: Literal["mesure", "aucune_question_applicable"]
    score: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    # Décomposition par statut. `base` = le dénominateur = les questions qui s'appliquent.
    n_repondu: int = Field(ge=0)
    n_approxime: int = Field(ge=0)
    n_non_fondable: int = Field(ge=0)
    n_sans_objet: int = Field(ge=0)          # HORS base — publié pour que le lecteur voie l'exclusion
    base: int = Field(ge=0)                   # = n_repondu + n_approxime + n_non_fondable

    # Actualité, sur les seules réponses FONDÉES (repondu + approxime). Un `non_fondable` n'a pas de
    # fondation, donc pas d'axe actualité — il pèse dans `base` par son crédit nul, pas ici.
    n_courante: int = Field(ge=0)
    n_perimee: int = Field(ge=0)
    n_indeterminable: int = Field(ge=0)

    # La solidité des sources, PUBLIÉE et jamais fondue dans `score` (arbitrage 3 / #50). None quand
    # aucune réponse fondée n'existe (tout est `non_fondable` ou `sans_objet`).
    rang_moyen: Optional[Tier] = None

    @model_validator(mode="after")
    def _coherence(self):
        if self.base != self.n_repondu + self.n_approxime + self.n_non_fondable:
            raise ValueError("`base` incohérente : elle est le nombre de questions APPLICABLES "
                             "(repondu + approxime + non_fondable), le `sans_objet` en est exclu")

        fondees = self.n_repondu + self.n_approxime
        if self.n_courante + self.n_perimee + self.n_indeterminable != fondees:
            raise ValueError("la ventilation d'actualité doit couvrir EXACTEMENT les réponses "
                             "fondées (repondu + approxime) : une réponse fondée a toujours un état "
                             "d'actualité, un `non_fondable` n'en a aucun")

        if (self.rang_moyen is None) != (fondees == 0):
            raise ValueError("`rang_moyen` existe SI ET SEULEMENT SI au moins une réponse est "
                             "fondée : le publier sans réponse fondée serait un rang sur zéro ligne, "
                             "l'omettre alors qu'il en existe une cacherait la solidité des sources")

        if self.etat == "mesure":
            if self.base == 0:
                raise ValueError("`etat='mesure'` sans question applicable : une base vide se DIT "
                                 "(`aucune_question_applicable`), elle ne se score pas à 0 (#44)")
            if self.score is None:
                raise ValueError("`etat='mesure'` sans `score` : la mesure EST le score")
        else:  # aucune_question_applicable
            if self.base != 0:
                raise ValueError("`aucune_question_applicable` avec des questions applicables : "
                                 "l'état ne décrit pas ce que la base mesure")
            if self.score is not None:
                raise ValueError("`aucune_question_applicable` porte un `score` : l'absence de "
                                 "question applicable n'est pas un score, c'est un état (#44)")
        return self
