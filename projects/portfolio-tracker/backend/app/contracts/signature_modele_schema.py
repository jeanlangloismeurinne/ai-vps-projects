"""Contrat de la SIGNATURE du modèle de valorisation (roadmap 05, capacité 4 bis ; #96/#97, migration 051).

CE QUE FERAIT UN VRAI FONDS
---------------------------
Le modèle d'une entreprise (somme des programmes pour RVMD, segments pour NVDA) est PROPOSÉ par
l'analyste, puis SIGNÉ par le directeur de la recherche / le comité. Le procès-verbal dit qui a signé,
quand, quelle version, pourquoi — et QUELLE FOURCHETTE était sous ses yeux : six mois plus tard, on
doit pouvoir relire « le comité a signé 38-61 $ par action le 29/09 », même si les chiffres repris ont
bougé depuis. Une version nouvelle ne remplace pas la signée tant que le comité ne l'a pas signée à son
tour : la fourchette affichée reste celle qu'il a signée (#97, arbitrage n°6).

LES CHOIX QUI EN DÉCOULENT (pris « comme un vrai fonds », 2026-09-29, à confirmer par l'utilisateur)
--------------------------------------------------------------------------------------------------
  1. Deux registres APPEND-ONLY : les VERSIONS proposées (une ligne par version, jamais réécrite) et
     le PROCÈS-VERBAL (une décision par version : signée ou écartée, jamais les deux, jamais deux fois).
  2. Seule la DERNIÈRE version proposée est en attente. Une proposition plus récente REMPLACE celle
     qui attendait (l'analyste a révisé son travail avant la séance) : la remplacée n'est plus
     décidable, elle reste archivée.
  3. Le comité signe ce qu'il VOIT aujourd'hui : la signature rejoue le pont contre le dossier du
     jour ; un modèle qui ne tient plus (pièce remplacée, réponse reprise qui n'est plus acquittée)
     ne se signe pas — il se refuse avec son motif.
  4. Après signature, la fourchette signée est au PV ; la fourchette DU JOUR se recalcule à la lecture
     (#53). Si le modèle signé ne tient plus contre le dossier du jour, il est servi « à revoir », en
     disant pourquoi, avec la fourchette signée toujours affichée — un fonds ne retire pas sa
     valorisation parce qu'une pièce a été remplacée, il la fait mettre à jour.
  5. Motif OBLIGATOIRE pour signer comme pour écarter (A7) ; le signataire est un nom saisi librement
     (même choix que le PV des questions, #84).

CE QUE CE CONTRAT VÉRIFIE (ICI) / CE QU'IL NE PEUT PAS VÉRIFIER (LÀ-BAS, `valorisation/signature.py`)
  la forme d'une décision (signer ⟺ fourchette) | la version décidée est-elle la version EN ATTENTE ?
  une fourchette ordonnée                         | le modèle tient-il contre le dossier du jour ?
  l'état servi cohérent avec ses pièces           | quel état servir (`servir_atelier`, détenteur unique)

Cible : pydantic v2 (container). Module PUR.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import Field, model_validator

from app.contracts.comite_schema import Texte
from app.contracts.analysis_v2_schemas import Strict
from app.contracts.modele_valorisation_schema import ModeleValorisation

__all__ = [
    "ActionModele", "EtatAtelier", "EtatSignee",
    "DemandeDecisionModele", "Fourchette", "VersionModele", "DecisionModele",
    "LigneModifiee", "EcartEntreVersions", "SigneeServie", "PropositionServie", "AtelierServi",
]

ActionModele = Literal["signer", "ecarter"]

# Où en est le modèle d'un titre — servi, jamais stocké.
EtatAtelier = Literal[
    "aucun_modele_propose",          # personne n'a encore proposé de modèle
    "en_attente_de_signature",       # une version attend, aucune n'a jamais été signée
    "signe",                         # une version signée, rien en attente
    "signe_nouvelle_version_en_attente",   # la signée est affichée, une autre attend le comité
    "aucun_modele_signe",            # des versions proposées, toutes écartées ou remplacées
]
# Le modèle signé, relu contre le dossier du jour.
EtatSignee = Literal["tient", "a_revoir"]


class DemandeDecisionModele(Strict):
    """Ce que l'écran envoie pour signer ou écarter UNE version : le signataire et son motif."""
    auteur: Texte = Field(max_length=120)
    motif: Texte = Field(max_length=4000)


class Fourchette(Strict):
    """Trois valeurs PAR ACTION, et pour un arbre d'événements la valeur de chaque événement en échec
    et en succès. Ordonnée : un bas au-dessus du central dirait des scénarios croisés."""
    bas: float
    central: float
    haut: float
    par_evenement: dict[str, tuple[float, float]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _ordonnee(self) -> "Fourchette":
        if not self.bas <= self.central <= self.haut:
            raise ValueError(f"fourchette non ordonnée : {self.bas} / {self.central} / {self.haut}")
        return self


class VersionModele(Strict):
    """Une version PROPOSÉE, telle que le registre la garde (jamais réécrite)."""
    id: int
    ticker_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    auteur: Texte
    propose_le: datetime
    modele: ModeleValorisation

    @model_validator(mode="after")
    def _meme_titre_meme_version(self) -> "VersionModele":
        if (self.modele.ticker_id, self.modele.version) != (self.ticker_id, self.version):
            raise ValueError(f"la ligne ({self.ticker_id} v{self.version}) ne porte pas le modèle "
                             f"({self.modele.ticker_id} v{self.modele.version})")
        return self


class DecisionModele(Strict):
    """Une ligne du procès-verbal. `fourchette` = ce que le comité avait sous les yeux en signant."""
    id: int
    modele_id: int
    ticker_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    action: ActionModele
    auteur: Texte
    motif: Texte
    fourchette: Optional[Fourchette] = None
    decide_le: datetime

    @model_validator(mode="after")
    def _signer_porte_sa_fourchette(self) -> "DecisionModele":
        if (self.action == "signer") != (self.fourchette is not None):
            raise ValueError("une signature porte la fourchette signée, et seulement elle : signer sans "
                             "chiffre rendrait le PV illisible six mois plus tard ; écarter n'en adopte "
                             "aucune")
        return self


class LigneModifiee(Strict):
    cle: str
    avant: float
    apres: float


class EcartEntreVersions(Strict):
    """Ce qui sépare la version en attente de la version signée — ce que le comité relit d'abord."""
    hypotheses_modifiees: list[LigneModifiee] = Field(default_factory=list)
    hypotheses_ajoutees: list[str] = Field(default_factory=list)
    hypotheses_retirees: list[str] = Field(default_factory=list)
    origines_changees: list[str] = Field(default_factory=list)   # même chiffre, autre source
    segments_ajoutes: list[str] = Field(default_factory=list)
    segments_retires: list[str] = Field(default_factory=list)
    mecanique_changee: bool = False
    forme_changee: bool = False


class SigneeServie(Strict):
    """La version signée : la fourchette SIGNÉE (au PV) et celle DU JOUR (recalculée), et si le modèle
    tient toujours contre le dossier."""
    version: VersionModele
    signature: DecisionModele
    etat: EtatSignee
    motif_etat: str = Field(min_length=1)
    fourchette_du_jour: Optional[Fourchette] = None   # None si la mécanique ne tourne plus

    @model_validator(mode="after")
    def _coherence(self) -> "SigneeServie":
        if self.signature.action != "signer" or self.signature.modele_id != self.version.id:
            raise ValueError("la signature servie n'est pas celle de cette version")
        if self.etat == "tient" and self.fourchette_du_jour is None:
            raise ValueError("un modèle qui tient a une fourchette du jour")
        return self


class PropositionServie(Strict):
    """La version en attente : sa fourchette si elle tient contre le dossier du jour, sinon le motif —
    le comité ne pourra pas la signer tant qu'elle ne tient pas."""
    version: VersionModele
    signable: bool
    motif_refus: Optional[str] = None
    fourchette: Optional[Fourchette] = None
    ecart: Optional[EcartEntreVersions] = None      # None s'il n'y a pas de version signée

    @model_validator(mode="after")
    def _coherence(self) -> "PropositionServie":
        if self.signable != (self.motif_refus is None):
            raise ValueError("une proposition est signable ssi aucun motif ne l'en empêche")
        if self.signable and self.fourchette is None:
            raise ValueError("une proposition signable montre sa fourchette")
        return self


class AtelierServi(Strict):
    """Le modèle de valorisation d'un titre, tel que le comité le voit — recalculé à la lecture."""
    ticker_id: str = Field(min_length=1)
    etat: EtatAtelier
    signee: Optional[SigneeServie] = None
    en_attente: Optional[PropositionServie] = None
    versions_proposees: int = Field(ge=0)
    proces_verbal: list[DecisionModele] = Field(default_factory=list)   # le plus récent d'abord
    genere_le: datetime

    @model_validator(mode="after")
    def _etat_coherent(self) -> "AtelierServi":
        attendu = {
            (False, False): "aucun_modele_propose" if self.versions_proposees == 0 else "aucun_modele_signe",
            (False, True): "en_attente_de_signature",
            (True, False): "signe",
            (True, True): "signe_nouvelle_version_en_attente",
        }[(self.signee is not None, self.en_attente is not None)]
        if self.etat != attendu:
            raise ValueError(f"état `{self.etat}` servi, `{attendu}` attendu d'après ses pièces")
        return self
