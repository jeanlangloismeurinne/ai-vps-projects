"""LA RÉVISION À LA BAISSE — point 13 (arbitrage de l'utilisateur, 2026-10-18).

« La dernière analyse fait foi, mais toute baisse est signalée au comité avec l'ancienne réponse à
côté et la raison donnée par l'analyste ; le comité peut rétablir l'ancienne d'un geste signé au
PV. » Comme un vrai fonds : un changement de recommandation d'analyste est PUBLIÉ, le gérant voit la
variation et peut la contester — il ne la bloque jamais à l'écriture (principe fondateur n° 3 : pas
de raffinement, la dernière réponse s'affiche toujours).

POURQUOI UN MODULE À PART (et pas dans `parcours.py`). `parcours.py` est déjà le DÉTENTEUR de
l'assemblage des trois niveaux (786 lignes avant ce chantier) ; cette règle est un deuxième geste du
comité à part entière — signalement + rétablissement —, de la même taille et de la même forme que
`classement.py` (#139 : une recommandation PURE recalculée à la lecture + un geste qui écrit). Comme
`classement.recommandation_de_classement` est ensuite simplement APPELÉE par `parcours.py`, sans y
être recopiée, `baisse_a_lire` l'est ici.

DEUX MOITIÉS, COMME TOUT LE CHANTIER V3
----------------------------------------
  · `baisse_a_lire` — PURE, recalculée à CHAQUE lecture (#53/#77), jamais stockée. Elle ne connaît
    que ce qu'on lui passe : aucune base, aucun réseau.
  · le GESTE `retablir` — dans `agents/v2/comite.py` (détenteur unique du procès-verbal, #46),
    pas ici : ce module ne décide QUE si une baisse est à lire, il n'écrit jamais.

LA RÈGLE (simple — pas de raffinement)
---------------------------------------
Ordre de fondement : `repondu` (3) > `approxime` (2) > `non_fondable` (1). `sans_objet` n'entre dans
AUCUNE comparaison (un changement d'applicabilité relève du classement, #139 — ce n'est pas une
baisse de fondement, c'est un autre jugement).

BAISSE = la réponse COURANTE d'une lignée (même ticker, framework, version, question, analyste) a un
fondement STRICTEMENT inférieur à sa PRÉCÉDENTE IMMÉDIATE (la ligne dont `superseded_by` = l'id de la
courante — une relation que la table porte déjà, append-only, migration 024).

La baisse est À LIRE tant qu'aucune décision du comité SUR LA QUESTION n'est datée APRÈS la création
de la réponse courante — quelle qu'en soit l'action (acquitter, renvoyer, réinitialiser, rétablir) :
dès que le comité a statué une fois depuis, il a LU le dossier, le signal s'éteint de lui-même (pas
de second raffinement — une acceptation « tombée » au sens de l'arbitrage n°2 ne rallume PAS le
signal : c'est une règle différente, #46 ne les confond pas).

LE RÉTABLISSEMENT (`retablissable`). La précédente peut être rétablie TELLE QUELLE seulement si son
`answer_json` valide encore contre le contrat `FrameworkAnswer` EN VIGUEUR — une ligne écrite sous un
contrat antérieur (un champ depuis devenu obligatoire) ne se recopie pas à l'identique : le comité
est invité à réinitialiser plutôt (#137), pas à ressusciter un objet que le contrat refuserait à
l'écriture aujourd'hui. Le code vérifie une RELATION (le JSON valide-t-il ?), jamais le sens (#68).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence

from pydantic import ValidationError

from app.contracts.comite_schema import DecisionComite
from app.contracts.framework_answer_schema import FrameworkAnswer, Statut
from app.contracts.parcours_schema import BaisseDeFondement, ReponseBaisse

__all__ = ["ReponsePourBaisse", "RANG_FONDEMENT", "baisse_a_lire"]

# L'ordre de fondement, et lui SEUL (`sans_objet` est volontairement absent : il n'entre dans
# aucune comparaison — un statut qui n'y figure pas ne peut jamais être une baisse).
RANG_FONDEMENT: dict[str, int] = {"non_fondable": 1, "approxime": 2, "repondu": 3}

_MOTIF_CONTRAT_ANTERIEUR = ("écrite sous un contrat antérieur, ne peut être rétablie telle quelle — "
                           "réinitialiser plutôt")


@dataclass(frozen=True)
class ReponsePourBaisse:
    """Une réponse de la lignée, comme `baisse_a_lire` la reçoit — jamais une lecture directe de la
    base (#46 : c'est `charger_etat_dossier`, et lui seul, qui lit).

    `statut_brut` est le statut TEL QUE LA COLONNE le porte, même quand `answer` est `None` (le JSON
    ne valide plus contre le contrat en vigueur) : c'est elle qui garde le fondement et l'affichage
    lisibles, sans prétendre relire un verbatim qu'on ne peut plus valider."""
    answer_id: int
    cree_le: datetime
    statut_brut: Statut
    answer: Optional[FrameworkAnswer] = None


def _resume(r: ReponsePourBaisse) -> str:
    """Le résumé court d'UNE réponse : le motif (`non_fondable`) ou le verbatim, sinon une note
    d'illisibilité EXPLICITE — jamais un verbatim deviné dans un JSON qu'on ne valide plus."""
    if r.answer is None:
        return f"réponse `{r.statut_brut}` écrite sous un contrat antérieur — illisible telle quelle"
    if r.answer.statut == "non_fondable":
        return r.answer.gap.manque
    return r.answer.reponse.verbatim


def baisse_a_lire(
    courante: ReponsePourBaisse,
    precedente: Optional[ReponsePourBaisse],
    decisions: Sequence[DecisionComite],
) -> Optional[BaisseDeFondement]:
    """DÉTENTEUR UNIQUE (#46) de « cette révision à la baisse est-elle à lire ? » (point 13). Pure.

    `decisions` : le registre de LA QUESTION (pas de tout le dossier) — `etat.registre[(fw, q)]`,
    peu importe l'ordre."""
    if precedente is None:
        return None
    rang_courant = RANG_FONDEMENT.get(courante.statut_brut)
    rang_precedent = RANG_FONDEMENT.get(precedente.statut_brut)
    if rang_courant is None or rang_precedent is None:
        return None   # `sans_objet` (de l'un ou l'autre) : hors comparaison
    if rang_courant >= rang_precedent:
        return None   # égal ou hausse : pas une baisse
    if any(d.decide_le > courante.cree_le for d in decisions):
        return None   # le comité a déjà statué depuis : il a lu (quelle qu'en soit l'action)
    if courante.answer is None:
        raise ValueError("la réponse COURANTE doit toujours valider contre le contrat en vigueur — appel fautif")

    raison = (courante.answer.gap.manque if courante.answer.statut == "non_fondable"
             else courante.answer.reponse.verbatim)
    retablissable = precedente.answer is not None
    return BaisseDeFondement(
        precedente=ReponseBaisse(answer_id=precedente.answer_id, statut=precedente.statut_brut,
                                 cree_le=precedente.cree_le, resume=_resume(precedente)),
        courante=ReponseBaisse(answer_id=courante.answer_id, statut=courante.statut_brut,
                               cree_le=courante.cree_le, resume=raison),
        raison_analyste=raison,
        retablissable=retablissable,
        motif_non_retablissable=None if retablissable else _MOTIF_CONTRAT_ANTERIEUR,
    )


def precedente_validee(statut_brut: Statut, answer_json: object) -> Optional[FrameworkAnswer]:
    """Valide l'`answer_json` BRUT d'une précédente contre le contrat EN VIGUEUR — `None` si ça ne
    valide plus (contrat antérieur). Fonction d'IO zéro (aucune base), mais pas pure au sens strict
    (dépend de la VERSION du contrat chargée) : séparée de `baisse_a_lire` pour que celle-ci reste
    testable sans construire un seul `FrameworkAnswer` invalide à la main."""
    try:
        return FrameworkAnswer.model_validate(answer_json)
    except ValidationError:
        return None
