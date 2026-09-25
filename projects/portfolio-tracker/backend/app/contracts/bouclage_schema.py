"""
Schéma Pydantic versionné du COMPTE RENDU DE BOUCLAGE (chantier v3, lot 5) — la note honnête.

CE QUE FERME CE LOT
-------------------
Le manager RENVOIE une réponse insuffisante et PRODUIT un mandat de recherche (§3.1) ; jusqu'ici ce
mandat était écrit, classé, horodaté… et JAMAIS relu en production (`grep read_open_mandates app/` =
0 appelant, figure #71). La boucle comité → collecte, que toute la v3 devait fermer, restait ouverte.

Ce contrat est ce que L'UTILISATEUR lit à la fin d'un passage de bouclage : pour chaque renvoi rejoué
PAR LE PROCESSUS NORMAL (traducteur → plan → collecteur, restreint à la question renvoyée — arbitrage
utilisateur 2026-09-25 : pas de chemin de recherche parallèle, #46), son SORT honnête. La décision
d'investissement se prend en connaissance des forces ET des limites du dossier.

QUATRE SORTS, ET POURQUOI QUATRE ET PAS DEUX (le trio #25/#44/#54, + la dispense)
--------------------------------------------------------------------------------
Un renvoi rejoué finit dans EXACTEMENT un de ces états, chacun portant sa charge :

  • `acquis`                 — la recherche a fondé la question : `statut_apres != non_fondable`
                               (répondu, approximé, ou reconnu `sans_objet` — savoir qu'une question
                               n'a pas d'objet est aussi une réponse au renvoi).
  • `collecte_insuffisante`  — on a SU où chercher, la source a déçu (`echec_collecte`) : la donnée
                               n'est pas publiée. `statut_apres == non_fondable`. Honnête : « cherché,
                               pas trouvé ».
  • `mandat_non_executable`  — le traducteur n'a même pas su en faire une ligne de plan
                               (`inobtenable`) : le problème est la QUESTION, pas la recherche.
                               `statut_apres == non_fondable`.
  • `classe_sans_suite`      — le comité a accepté le trou (une DISPENSE existe) : renvoi soldé sans
                               le combler. `statut_apres == non_fondable`.

Confondre `collecte_insuffisante` et `mandat_non_executable` ferait chercher une source plus RÉCENTE
là où il faut RÉÉCRIRE la question — exactement le mode de panne que #53/#54 nomment. Confondre l'un
d'eux avec `acquis` ferait lire « rien à signaler » là où il faut lire « limite connue » (#49).

CE QUE CE CONTRAT VÉRIFIE, ET CE QU'IL NE PEUT PAS VÉRIFIER (#37)
----------------------------------------------------------------
Un contrat valide un OBJET, jamais la cohérence entre plusieurs. Ici :

  ici (Pydantic)                              | là-bas (agent `bouclage.classer_sort`, en Python)
  --------------------------------------------|--------------------------------------------------
  `acquis` ⟺ `statut_apres != non_fondable`   | LEQUEL des trois sorts non fondés (origine de la
  un sort non fondé ⟹ `statut_apres` = non    | collecte `inobtenable`/`echec_collecte`, ou dispense)
  fondable                                    | — le contrat ne voit ni la collecte ni les dispenses
  chaque sort NOMME sa cause (`motif`)        |

La CLASSIFICATION (choisir le sort) est une dérivation déterministe : elle vit dans
`app/agents/v2/bouclage.py::classer_sort`, DÉTENTEUR UNIQUE (#46). Ce contrat n'en tient aucune copie.

Cible : pydantic v2 (container backend). Tester en container, pas le python hôte.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .analysis_v2_schemas import Strict
from .framework_answer_schema import Statut

__all__ = ["SORTS_BOUCLAGE", "SortBouclage", "MandatBoucle", "CompteRenduBouclage"]

# Vocabulaire FERMÉ des sorts d'un renvoi rejoué. Pas de cinquième « en cours » : un passage de
# bouclage est SYNCHRONE — quand il rend la main, chaque mandat lu a reçu son sort ou n'a pas été
# rejoué (et n'apparaît alors pas dans le compte rendu).
SORTS_BOUCLAGE = ("acquis", "collecte_insuffisante", "mandat_non_executable", "classe_sans_suite")
SortBouclage = Literal["acquis", "collecte_insuffisante", "mandat_non_executable", "classe_sans_suite"]

# Les trois sorts qui laissent la question NON FONDÉE — l'inverse d'`acquis`. Un LECTEUR (le check)
# et le pont s'y adossent ; le tenir à un seul endroit évite qu'un ajout de sort divise la règle.
SORTS_NON_FONDES = ("collecte_insuffisante", "mandat_non_executable", "classe_sans_suite")


class MandatBoucle(Strict):
    """Un mandat de renvoi rejoué par le processus normal, et son SORT honnête.

    `mandat_id` trace la ligne `framework_mandates` qui a été servie (`serve_mandate`), pour qu'un
    lecteur remonte du compte rendu au mandat d'origine. `statut_avant`/`statut_apres` sont ceux que
    `serve_mandate` a figés (T8) ; `entry_ids_produits` les pièces que la re-collecte a fondées."""

    question_id: str = Field(min_length=1)
    mandat_id: int
    sort: SortBouclage
    statut_avant: Statut
    statut_apres: Statut
    entry_ids_produits: list[int] = Field(default_factory=list)
    # Le motif NOMME la cause du sort — c'est la moitié « honnête » de la note : « cherché, la donnée
    # n'est pas publiée » n'est pas « question mal posée » (#25 : un état sans cause condamne le
    # lecteur à deviner).
    motif: str = Field(min_length=1)

    @model_validator(mode="after")
    def _le_sort_porte_exactement_sa_charge(self):
        acquis = self.sort == "acquis"
        fonde = self.statut_apres != "non_fondable"
        if acquis and not fonde:
            raise ValueError(
                "sort `acquis` avec `statut_apres == non_fondable` : un renvoi n'est acquis que si la "
                "recherche a FONDÉ la question (répondu/approximé/sans_objet). Sinon c'est un des trois "
                f"sorts non fondés {SORTS_NON_FONDES} — les confondre lit « rien à signaler » là où il "
                "faut lire « limite connue » (#49).")
        if not acquis and fonde:
            raise ValueError(
                f"sort `{self.sort}` avec `statut_apres == {self.statut_apres}` (fondé) : les sorts "
                f"{SORTS_NON_FONDES} laissent la question NON FONDÉE par définition. Une question fondée "
                "est `acquis`.")
        return self


class CompteRenduBouclage(Strict):
    """Ce que l'utilisateur lit après un passage de bouclage — la note honnête, par mandat rejoué.

    NON PERSISTÉ (même doctrine que l'avis du manager, #53/#77) : les effets durables sont les
    nouvelles `framework_answers` et les `framework_mandates` passés `servi`. Ce compte rendu
    s'ASSEMBLE au run et se recalcule à la lecture — un verdict figé ne peut pas signaler qu'il a
    vieilli.
    """

    ticker_id: str = Field(min_length=1)
    framework_id: str = Field(min_length=1)
    framework_version: str = Field(min_length=1)
    # Combien de mandats manager/comité OUVERTS ont été lus au DÉBUT du passage. `len(boucles)` peut
    # être inférieur : un mandat dont la question n'est plus applicable n'est pas rejoué (et le dire
    # est plus honnête que de le compter servi sur rien, #54).
    mandats_lus: int = Field(ge=0)
    boucles: list[MandatBoucle] = Field(default_factory=list)

    @model_validator(mode="after")
    def _on_ne_boucle_pas_plus_que_lu(self):
        if len(self.boucles) > self.mandats_lus:
            raise ValueError(
                f"{len(self.boucles)} boucle(s) pour {self.mandats_lus} mandat(s) lu(s) : on ne sert "
                "pas un mandat qui n'était pas ouvert (`serve_mandate` exige `statut='ouvert'`).")
        ids = [b.mandat_id for b in self.boucles]
        if len(set(ids)) != len(ids):
            raise ValueError("deux boucles sur le même `mandat_id` : un mandat n'est servi qu'une fois.")
        return self
