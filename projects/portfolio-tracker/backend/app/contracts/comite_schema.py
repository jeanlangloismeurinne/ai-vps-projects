"""Contrat du REGISTRE DU COMITÉ — acquitter / renvoyer, tracés (chantier v3, lot 6 maillon 3, spec
§8.2, audit A7 « overrides utilisateur tracés »).

CE QUE FERAIT UN VRAI FONDS
---------------------------
Un comité d'investissement tient un PROCÈS-VERBAL. Quand il passe outre une faiblesse du dossier
(« on décide sans la marge brute des pairs ») il écrit QUI a décidé, QUAND, sur QUELLE version du
dossier, et POURQUOI — pour qu'on puisse relire la décision six mois plus tard dans son contexte. Un
PV ne se réécrit pas : une décision nouvelle s'AJOUTE, elle n'efface pas l'ancienne. D'où un registre
append-only (`DecisionComite`, une ligne par décision), jamais une colonne « acceptée » sur la
réponse.

Les deux gestes (§8.2) :
  · ACQUITTER — « je prends la réponse telle qu'elle est, avec son rang ». Porte sur UNE réponse
    précise (`answer_id`) : c'est la « version du dossier » que le comité a lue.
  · RENVOYER  — « va chercher ceci ». Emprunte le MÊME canal que le renvoi du manager (un
    `framework_mandate` d'origine `comite`, #46) ; le registre garde le PV, le mandat garde l'ordre
    exécutable.

LES ARBITRAGES DU COMITÉ QUI GOUVERNENT CE CONTRAT (2026-09-25)
--------------------------------------------------------------
  n°1 — PV COMPLET : auteur, instant, version du dossier (framework + version + réponse), et une
        justification écrite NON VIDE. Un « ok » tapé pour passer n'est pas une justification : le
        contrat refuse un motif blanc (et la base le redit, migration 048).
  n°2 — UNE ACCEPTATION TOMBE dès qu'un fait IMPORTANT est publié après elle (résultats, approbation,
        acquisition) ; une information de routine ne la remet pas en cause. ⟹ la validité se
        RECALCULE À LA LECTURE contre `ancre_substantielle` (#53/#54), jamais figée à l'écriture. Le
        registre note le dernier fait important CONNU au moment de la décision (`ancre_*`) ; un fait
        important déposé un jour postérieur à la décision — ou le jour même, s'il n'est pas celui que
        le PV cite — la fait tomber (`comite._fait_nouveau`).

LES ÉTATS D'UNE ACCEPTATION, SERVIS (et pourquoi quatre)
--------------------------------------------------------
  `en_vigueur`               — la réponse acceptée est toujours la réponse courante, et aucun fait
                               important n'a été publié depuis : la question n'est PAS un manque.
  `tombee_reponse_remplacee` — l'analyse a été refaite depuis : le comité avait lu une AUTRE version
                               du dossier. Il doit relire la nouvelle.
  `tombee_fait_nouveau`      — un fait important a été publié après la décision (arbitrage n°2).
  `non_verifiable`           — la source des faits (EDGAR) est injoignable : on ne SAIT pas si un fait
                               est tombé. Ce n'est ni « en vigueur » ni « tombée » (#49 : `none` ≠
                               `unavailable`), et une acceptation qu'on ne peut pas vérifier ne fonde
                               pas une décision du jour.

CE QUE CE CONTRAT VÉRIFIE, ET CE QU'IL NE PEUT PAS VÉRIFIER (#37)
----------------------------------------------------------------
  ici (Pydantic)                               | là-bas (agent `agents/v2/comite.py`, en Python)
  ---------------------------------------------|-------------------------------------------------
  la FORME d'une décision par action           | la réponse acceptée est-elle COURANTE et de CETTE
  un motif / un auteur non blancs              | question ? (lecture de `framework_answers`)
  la trace de l'ancre, cohérente avec son état | QUEL état d'acceptation servir (`servir_acceptation`,
  un état « tombé » porte ce qui l'a fait tomber| détenteur unique de la règle n°2)

Cible : pydantic v2 (container backend). Tester en container, pas le python hôte.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal, Optional

from pydantic import AfterValidator, Field, model_validator

from app.contracts.analysis_v2_schemas import Strict

__all__ = [
    "ACTIONS_COMITE",
    "ActionComite",
    "EtatAncre",
    "EtatAcceptation",
    "ETATS_TOMBES",
    "FaitImportant",
    "DemandeAcquittement",
    "DemandeRenvoi",
    "DecisionComite",
    "AcceptationServie",
    "PositionComite",
]

ACTIONS_COMITE = ("acquitter", "renvoyer")
ActionComite = Literal["acquitter", "renvoyer"]

# L'état de l'ancre matérielle AU MOMENT de la décision — le vocabulaire EXACT de
# `MaterialEventLookup.status` (détenteur : `knowledge/material_events.py`). `none` = on SAIT
# qu'aucun fait important n'a été publié ; `unavailable` = on ne sait pas. Les confondre est le mode
# de panne central du chantier (#49).
EtatAncre = Literal["found", "none", "unavailable"]

EtatAcceptation = Literal[
    "en_vigueur", "tombee_reponse_remplacee", "tombee_fait_nouveau", "non_verifiable"]
# Les états où l'acceptation ne tient PAS aujourd'hui — la question repasse devant le comité.
ETATS_TOMBES = ("tombee_reponse_remplacee", "tombee_fait_nouveau", "non_verifiable")


def _non_blanc(v: str) -> str:
    """Un texte fait de blancs n'est pas un texte : « justification écrite obligatoire » (n°1)."""
    v = v.strip()
    if not v:
        raise ValueError("texte blanc : le procès-verbal exige un texte écrit (arbitrage n°1)")
    return v


Texte = Annotated[str, AfterValidator(_non_blanc)]


class FaitImportant(Strict):
    """Un fait important publié (dépôt EDGAR substantiel), tel que le PV le cite : le comité lit
    « 8-K du 2026-08-26 (approbation) », pas un numéro d'accession."""
    publie_le: date
    accession: Optional[str] = None
    resume: Texte


# ── Les deux DEMANDES (ce que l'écran envoie) ─────────────────────────────────────────────────

class DemandeAcquittement(Strict):
    """« Je prends cette réponse telle qu'elle est, avec son rang. » Le membre du comité signe et
    écrit POURQUOI il passe outre la faiblesse."""
    answer_id: int
    auteur: Texte = Field(max_length=120)
    motif: Texte = Field(max_length=4000)


class DemandeRenvoi(Strict):
    """« Va chercher ceci. » `motif` dit ce qui ne va pas ; `mandat` est l'ordre de recherche
    EXÉCUTABLE que le collecteur recevra, tel quel (contrat `FrameworkMandate.mandat`). `answer_id`
    optionnel : on peut renvoyer une question qui n'a encore aucune réponse."""
    auteur: Texte = Field(max_length=120)
    motif: Texte = Field(max_length=4000)
    mandat: Texte = Field(max_length=4000)
    answer_id: Optional[int] = None


# ── Une ligne du REGISTRE (ce que la base garde) ──────────────────────────────────────────────

class DecisionComite(Strict):
    """Une ligne du procès-verbal, telle qu'elle est archivée. Jamais modifiée (migration 048 : le
    rôle applicatif n'a ni UPDATE ni DELETE sur la table)."""
    id: int
    ticker_id: str = Field(min_length=1)
    framework_id: str = Field(min_length=1)
    framework_version: str = Field(min_length=1)
    question_id: str = Field(min_length=1)
    action: ActionComite
    answer_id: Optional[int] = None
    mandat_id: Optional[int] = None            # le mandat OUVERT par un renvoi
    mandat_remplace_id: Optional[int] = None   # la recherche en cours que la décision a arrêtée
    auteur: Texte
    motif: Texte
    ancre_etat: EtatAncre
    fait_connu: Optional[FaitImportant] = None
    decide_le: datetime

    @model_validator(mode="after")
    def _chaque_action_porte_sa_forme(self):
        if self.action == "acquitter":
            if self.answer_id is None:
                raise ValueError("acquitter sans `answer_id` : le comité accepte UNE réponse précise "
                                 "— la version du dossier qu'il a lue (arbitrage n°1)")
            if self.mandat_id is not None:
                raise ValueError("acquitter avec un `mandat_id` : accepter n'ouvre aucune recherche")
            if self.ancre_etat == "unavailable":
                raise ValueError("acquitter avec une ancre `unavailable` : sans savoir quel fait "
                                 "important était connu, l'acceptation ne pourrait jamais tomber "
                                 "(arbitrage n°2) — la décision doit être refusée, pas archivée")
        else:  # renvoyer
            if self.mandat_id is None:
                raise ValueError("renvoyer sans `mandat_id` : un renvoi qui ne produit aucun mandat "
                                 "est l'Écart B — le comité croirait avoir relancé la recherche")
        if (self.ancre_etat == "found") != (self.fait_connu is not None):
            raise ValueError(f"ancre `{self.ancre_etat}` et fait connu = {self.fait_connu is not None}"
                             " : un fait est cité ssi l'ancre en a trouvé un")
        return self


# ── Ce que le parcours SERT (recalculé à la lecture) ──────────────────────────────────────────

class AcceptationServie(Strict):
    """Une acceptation du comité et son état AUJOURD'HUI — produit par `comite.servir_acceptation`,
    jamais lu en base (#53)."""
    decision: DecisionComite
    etat: EtatAcceptation
    motif_etat: str = Field(min_length=1)
    fait_nouveau: Optional[FaitImportant] = None

    @model_validator(mode="after")
    def _un_etat_tombe_dit_ce_qui_l_a_fait_tomber(self):
        if self.decision.action != "acquitter":
            raise ValueError("une acceptation servie porte une décision `acquitter`")
        if (self.etat == "tombee_fait_nouveau") != (self.fait_nouveau is not None):
            raise ValueError(f"état `{self.etat}` et fait nouveau = {self.fait_nouveau is not None} :"
                             " une acceptation tombée sur un fait NOMME ce fait (quel dépôt, quelle "
                             "date), et seulement elle")
        return self


class PositionComite(Strict):
    """Où en est le comité sur une question : sa DERNIÈRE décision (le PV le plus récent prime) et,
    si c'est une acceptation, son état du jour."""
    derniere: DecisionComite
    acceptation: Optional[AcceptationServie] = None

    @model_validator(mode="after")
    def _l_acceptation_est_la_derniere_decision(self):
        if (self.derniere.action == "acquitter") != (self.acceptation is not None):
            raise ValueError("une acceptation est servie ssi la dernière décision est `acquitter`")
        if self.acceptation is not None and self.acceptation.decision.id != self.derniere.id:
            raise ValueError("l'acceptation servie n'est pas la dernière décision du registre : une "
                             "décision plus récente l'a remplacée")
        return self
