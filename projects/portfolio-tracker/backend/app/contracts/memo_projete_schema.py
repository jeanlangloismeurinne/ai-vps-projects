"""Contrat de la NOTE DE COMITÉ PROJETÉE (chantier v3, lot 5 — spec §6).

CE QU'IL REMPLACE, ET POURQUOI LE `ResearchMemo` NE POUVAIT PAS SERVIR DE SUPPORT
---------------------------------------------------------------------------------
§6 pose que les blocs du mémo deviennent la **projection** des frameworks acquittés : un bloc = un
framework, un champ = une question. Le réflexe serait de verser les dossiers dans le
`ResearchMemo` existant. C'est impossible, et pas par préférence :

    `Financials.roic_pct: float` est REQUIS, sans défaut.

Un dossier dont `qf_1` est revenue `sans_objet` (RVMD, pré-revenus : « le capital employé
rapporte-t-il plus que son coût ? » n'a pas d'objet) n'a rien à mettre dans cette case. Projeter
dans ce support forcerait donc à produire un ROIC pour une société sans revenus — c'est
**littéralement l'entry #190**, le défaut canonique que ce lot est censé nettoyer, et la cause
racine §0.3. Un formulaire à cases obligatoires fabrique ce qui lui manque.

Le support projeté n'a donc **aucune case pré-imprimée** : il ne porte que ce que le classeur
contient, et il porte le NOM de ce qu'il ne contient pas.

LES QUATRE ÉTATS D'UNE RUBRIQUE, ET POURQUOI AUCUN NE PEUT ÊTRE FUSIONNÉ (#25/#44/#54/#68)
-------------------------------------------------------------------------------------------
Une rubrique vide se lit « rien à signaler ». C'est un mensonge par omission : le comité conclurait
qu'il n'y a pas de sujet. Il faut un état NOMMÉ — et il en faut quatre, parce que le fonds a quatre
situations réellement distinctes, sur lesquelles il n'agit pas pareil :

  · `instruite`                       — méthodologie approuvée, au moins une réponse ACQUITTÉE ;
  · `sans_acquittement`               — méthodologie approuvée, dossier relu, **rien n'a passé les
                                        4 contrôles**. L'absence est une propriété du DOSSIER, et
                                        le remède est une collecte ;
  · `non_revalidable`                 — méthodologie approuvée, dossier ouvert, mais la revue N'A
                                        PAS PU AVOIR LIEU : l'émetteur n'est pas classé, donc on
                                        ignore quelles questions lui sont applicables. L'absence
                                        est une propriété de NOTRE SAISIE, et le remède est un
                                        classement, pas une collecte ;
  · `pas_de_methodologie_approuvee`   — aucun framework ne projette ce chapitre. L'absence est une
                                        décision du FONDS, jamais une propriété de l'émetteur.

Fusionner les deux du milieu fait lire « le manager a tout refusé » là où la vérité est « personne
n'a relu » — c'est **exactement le faux qu'a produit la première version de ce lot**, mesuré sur
RVMD le 2026-09-24 par `tools/montrer_memo_projete.sh` : `financials` sortait « 6 réponses au
dossier, aucune acquittée par le manager » alors qu'aucune revue n'était possible (l'archétype
n'était au dossier nulle part — migration 046). Fusionner les deux du bas fait porter à l'émetteur
une lacune qui est la nôtre.

C'est la troisième case de #68, deux fois : plutôt que de muscler une garde incapable de
distinguer ces situations, on change la FORME de la réponse pour que la confusion ne puisse plus
s'écrire.

CE QUE LE CONTRAT REND IMPOSSIBLE PAR CONSTRUCTION, PLUTÔT QUE DE LE GARDER PAR UN `if`
----------------------------------------------------------------------------------------
  · **publier du non-acquitté SANS LE DIRE** — `PointProjete` exige `manager.verdict == 'acquitte'`,
    OU une acceptation du comité EN VIGUEUR sur cette réponse précise, portée avec la faiblesse
    qu'elle a surmontée (`RetenueParLeComite`, arbitrage A du 2026-09-26). « Ne publier que
    l'instruit » n'est pas une discipline du projecteur : un projecteur qui l'oublierait ne
    construirait pas son objet ;
  · **omettre un chapitre** — `MemoProjete` exige EXACTEMENT l'ordre du jour (`BLOCS_MEMO`). Un
    chapitre omis se lirait comme une propriété du sujet (`feedback_rendu_est_un_producteur`) ;
  · **servir sans l'axe actualité** — le point porte une `FrameworkAnswerServie`, pas une
    `FrameworkAnswer`. La réponse stockée ne porte PAS d'actualité (#53) : elle se recalcule à la
    lecture, et le type d'entrée l'exige au lieu de l'espérer.

⚠️ POURQUOI CE CONTRAT IMPORTE `BLOCS_MEMO` ALORS QUE #37 L'INTERDIRAIT
------------------------------------------------------------------------
`framework_definition_schema` refuse de vérifier qu'un `bloc_memo` existe, et c'est juste : un
framework au `bloc_memo` fautif reste un framework bien formé. Ici c'est autre chose — une note qui
ne couvre pas l'ordre du jour **n'est pas une note de comité**, au même titre qu'un `sens_admis` à
une seule valeur n'est pas un vocabulaire. La complétude est la propriété DÉFINISSANTE de l'objet,
pas une cohérence avec un tiers. Et `BLOCS_MEMO` n'est pas un objet : c'est un vocabulaire inerte,
dérivé, du même rang que `Tier` ou `NATURES`.

Cible : pydantic v2 (container). Tester en container, **pas** le python hôte (v1).
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import Field, model_validator

from .analysis_v2_schemas import Strict
from .comite_schema import AcceptationServie
from .framework_answer_schema import FrameworkAnswerServie
from .memo_blocs import BLOCS_MEMO

__all__ = [
    "MEMO_PROJETE_SCHEMA_VERSION", "ETATS_RUBRIQUE", "EtatRubrique",
    "RetenueParLeComite", "PointProjete", "RubriqueProjetee", "MemoProjete",
]

# Contrat NEUF du lot 5. Il ne bouscule pas `SCHEMA_VERSION` ("v2.0.0") des 4 JSON d'analyse : le
# `ResearchMemo` n'est pas modifié par ce lot, il est DOUBLÉ. Bumper sa version forcerait les 3
# points de synchro (#19) et l'exemple JSON des prompts en base (#39) pour un support qui n'existait
# pas encore.
MEMO_PROJETE_SCHEMA_VERSION = "v3.0.0"

ETATS_RUBRIQUE = (
    "instruite", "sans_acquittement", "non_revalidable", "pas_de_methodologie_approuvee")
EtatRubrique = Literal[
    "instruite", "sans_acquittement", "non_revalidable", "pas_de_methodologie_approuvee"]


class RetenueParLeComite(Strict):
    """Pourquoi un point que le contrôle qualité n'a PAS acquitté figure quand même dans la note.

    ARBITRAGE A (2026-09-26) — ce que fait un vrai fonds : le mémo de comité reprend ce sur quoi le
    comité s'est APPUYÉ pour décider, y compris une information qu'il a retenue en connaissance de
    sa faiblesse — mais il le DIT, avec la faiblesse, qui a tranché, quand et pourquoi. Une note qui
    omettrait la réponse contredirait l'alerte (qui la compte comme réglée) ; une note qui la
    publierait sans mention la ferait passer pour contrôlée. Les deux sont des faux.

    `faiblesse` : ce que le contrôle reproche À LA LECTURE (l'avis du manager est recalculé, #77) —
    pas le souvenir de ce qu'il reprochait le jour de la décision.
    """
    acceptation: AcceptationServie
    faiblesse: str = Field(min_length=1)

    @model_validator(mode="after")
    def _seule_une_acceptation_qui_tient_publie(self):
        if self.acceptation.etat != "en_vigueur":
            raise ValueError(
                f"acceptation `{self.acceptation.etat}` portée au mémo : une acceptation tombée "
                "(fait important publié depuis, analyse refaite) ou invérifiable ne fonde plus rien "
                "— la question repasse devant le comité, elle ne s'imprime pas dans sa note")
        return self


class PointProjete(Strict):
    """Un point de rubrique = UNE question instruite, acquittée par son manager.

    `answer` porte la réponse ENTIÈRE, jamais des champs recopiés : le jour où `FrameworkAnswer`
    gagne un bloc, le point le transporte sans rien savoir de son existence (#46, même geste que
    `COLONNES_DENORMALISEES`). Un point qui aplatirait `verbatim`/`valeur`/`rang` en champs propres
    serait un second contrat de réponse, divergent au premier correctif.
    """
    question_id: str = Field(min_length=1)
    # L'énoncé, lu dans `frameworks.yaml` et transporté ici : le comité lit la QUESTION, pas un id.
    # Il n'est pas dans `FrameworkAnswer` — une réponse ne porte pas son énoncé.
    enonce: str = Field(min_length=1)
    chemin_indexation: str = Field(min_length=1)
    answer: FrameworkAnswerServie
    # L'id de la ligne `framework_answers` dont ce point est la projection. Le comité doit pouvoir
    # remonter à la pièce ; une note sans traçabilité de ligne rouvre §0.3 d'un cran plus haut.
    answer_id: Optional[int] = None
    # Présent SSI le point entre dans la note par une décision du comité et non par le contrôle
    # (arbitrage A). Jamais les deux : une réponse acquittée par le contrôle n'a pas besoin qu'on
    # passe outre, et la marquer « retenue malgré » inventerait une faiblesse.
    retenue_par_comite: Optional[RetenueParLeComite] = None

    @model_validator(mode="after")
    def _un_point_publie_ce_qui_a_ete_acquitte(self):
        if self.answer.question_id != self.question_id:
            raise ValueError(
                f"point `{self.question_id}` portant la réponse de `{self.answer.question_id}` : "
                "un point mal étiqueté range une réponse sous la mauvaise question, et le comité "
                "lit un verdict qui ne répond pas à ce qu'il croit lire")
        acquitte = self.answer.manager is not None and self.answer.manager.verdict == "acquitte"
        if self.retenue_par_comite is not None:
            if acquitte:
                raise ValueError(
                    f"point `{self.question_id}` acquitté par le contrôle ET marqué « retenu par le "
                    "comité malgré sa faiblesse » : la mention inventerait une faiblesse que le "
                    "contrôle ne reproche plus")
            d = self.retenue_par_comite.acceptation.decision
            if (d.answer_id, d.question_id) != (self.answer_id, self.question_id):
                raise ValueError(
                    f"point `{self.question_id}` (réponse #{self.answer_id}) couvert par la décision "
                    f"du comité sur `{d.question_id}` (réponse #{d.answer_id}) : le comité a accepté "
                    "UNE version du dossier, sa décision ne se prête pas à une autre réponse")
            return self
        if not acquitte:
            verdict = None if self.answer.manager is None else self.answer.manager.verdict
            raise ValueError(
                f"point `{self.question_id}` dont la réponse n'est pas acquittée (verdict "
                f"`{verdict}`) : « ne publier que l'instruit » (§6) n'est pas une discipline du "
                "projecteur, c'est une propriété de la note — un renvoi publié serait un avis du "
                "manager présenté comme une conclusion du dossier")
        return self


class RubriqueProjetee(Strict):
    """Un chapitre de la note. Son `etat` COMMANDE ce qu'elle porte, et INTERDIT le reste.

    L'interdiction compte autant que l'obligation : c'est elle qui empêche une rubrique
    `pas_de_methodologie_approuvee` de porter quand même des points (donc de se lire « instruite »
    tout en se déclarant vide), et une rubrique `instruite` de sortir sans aucun point (une rubrique
    vide qui se dit instruite est le pire de tous les faux : elle se lit « rien à signaler »).
    """
    bloc: str = Field(min_length=1)
    etat: EtatRubrique
    # Ce que le comité LIT quand il n'y a pas de points. Toujours présent, y compris sur une
    # rubrique instruite : une note dont certains chapitres s'expliquent et d'autres pas laisse
    # deviner la différence.
    motif: str = Field(min_length=1)

    framework_id: Optional[str] = Field(default=None, min_length=1)
    libelle: Optional[str] = Field(default=None, min_length=1)
    methodologie: Optional[str] = Field(default=None, min_length=1)
    framework_version: Optional[str] = Field(default=None, min_length=1)

    points: list[PointProjete] = Field(default_factory=list)
    # Combien de réponses existent au dossier SANS avoir été acquittées. C'est ce qui sépare « rien
    # n'a été tenté » de « tout a été renvoyé » — deux situations que le seul état
    # `sans_acquittement` ne distingue pas, et sur lesquelles le comité n'agit pas pareil.
    # Descriptif, jamais une porte : aucun seuil ne s'y adosse (§0.6).
    reponses_non_acquittees: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _l_etat_porte_exactement_sa_charge(self):
        adosse = ("framework_id", "libelle", "methodologie", "framework_version")
        if self.etat == "pas_de_methodologie_approuvee":
            portes = [n for n in adosse if getattr(self, n) is not None]
            if portes:
                raise ValueError(
                    f"`{self.bloc}` se déclare sans méthodologie approuvée mais porte {portes} : "
                    "l'absence serait alors celle du dossier, pas celle du référentiel — or ce "
                    "sont deux états distincts, et seul le second est une décision du fonds")
            if self.points or self.reponses_non_acquittees:
                raise ValueError(
                    f"`{self.bloc}` se déclare sans méthodologie approuvée mais porte des "
                    "réponses : une réponse sans question approuvée est exactement le champ "
                    "rédigé à côté du classeur que §0.3 nomme")
            return self

        manquants = [n for n in adosse if getattr(self, n) is None]
        if manquants:
            raise ValueError(
                f"`{self.bloc}` en `{self.etat}` sans {manquants} : une rubrique adossée à une "
                "méthodologie doit dire LAQUELLE, sinon le comité ne peut ni la contester ni la "
                "faire évoluer")
        if self.etat == "instruite" and not self.points:
            raise ValueError(
                f"`{self.bloc}` se déclare instruite sans aucun point : une rubrique vide se lit "
                "« rien à signaler ». C'est l'état `sans_acquittement` qu'elle décrit")
        # Les DEUX états du milieu interdisent les points, et pour des raisons différentes qu'il
        # faut garder distinctes : `sans_acquittement` parce que la revue a eu lieu et n'a rien
        # retenu ; `non_revalidable` parce qu'elle n'a pas pu avoir lieu. Publier un point sous le
        # second serait publier un acquittement que personne n'a prononcé.
        if self.etat in ("sans_acquittement", "non_revalidable") and self.points:
            raise ValueError(
                f"`{self.bloc}` se déclare `{self.etat}` mais porte {len(self.points)} point(s) : "
                "un point n'existe que s'il a été acquitté (cf. `PointProjete`), donc soit l'état "
                "est `instruite`, soit ces points sortent d'une revue qui n'a jamais eu lieu")
        return self


class MemoProjete(Strict):
    """La note remise au comité pour UN émetteur, à UNE date de lecture.

    JAMAIS PERSISTÉE — produite à la lecture, comme `FrameworkAnswerServie` et pour la même raison
    (#53/#54) : elle dépend de l'actualité des fondations, qui n'est pas stockée. Une note figée
    servirait le verdict d'avant le dernier événement matériel.
    """
    schema_version: Literal["v3.0.0"] = "v3.0.0"
    ticker_id: str = Field(min_length=1)
    genere_le: datetime
    # Le référentiel en vigueur AU MOMENT de la projection. Une note qui ne dit pas sous quelle
    # version de méthodologie elle a été produite survit au premier correctif d'énoncé (même écart
    # V10 que `question_coverage` / `collection_plans` / `framework_answers`).
    framework_version: str = Field(min_length=1)
    rubriques: list[RubriqueProjetee] = Field(min_length=1)
    # Verrou Q2, repris du `ResearchMemo` : aucun verdict d'investissement dans la note. La
    # projection ne peut pas en produire — elle n'a nulle part où l'écrire.
    posture: Literal["NEUTRE"] = "NEUTRE"

    @model_validator(mode="after")
    def _la_note_couvre_exactement_l_ordre_du_jour(self):
        vus = [r.bloc for r in self.rubriques]
        if len(set(vus)) != len(vus):
            raise ValueError(f"deux rubriques pour un même chapitre — {sorted(vus)}")
        attendus = set(BLOCS_MEMO)
        if set(vus) != attendus:
            manquants = sorted(attendus - set(vus))
            inventes = sorted(set(vus) - attendus)
            raise ValueError(
                f"la note ne couvre pas l'ordre du jour — manquants : {manquants}, inventés : "
                f"{inventes}. Un chapitre omis ne se lit pas « omis » : il se lit comme une "
                "propriété de l'émetteur, et le comité délibère sur une absence qu'il croit "
                "constatée (`feedback_rendu_est_un_producteur`)")
        return self

    def par_bloc(self) -> dict[str, RubriqueProjetee]:
        """Accès par chapitre. Sûr : le validateur vient de garantir l'unicité et la complétude."""
        return {r.bloc: r for r in self.rubriques}
