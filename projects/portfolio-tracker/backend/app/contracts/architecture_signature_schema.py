"""Contrat de la SIGNATURE DE L'ARCHITECTURE du classeur (lot M3, roadmap V3
`12-lot-M3-architecte.md` §6.2, migration 062). Calqué sur `signature_modele_schema.py` (#46) :
même geste, mêmes choix pris « comme un vrai fonds », transposés à l'architecture plutôt qu'à la
fourchette de valorisation — pas de `Fourchette` ici, mais les SIGNAUX ([S2]/[S3b]) que le comité
avait sous les yeux en décidant.

L'INTERRUPTEUR (§2.1/§7 de la spec M3, `signature_de_l_architecture`) fait varier CE QUI EST EN
VIGUEUR (`ArchitectureServie.en_vigueur`), jamais la forme de ce contrat : une décision reste une
décision, signée ou écartée, qu'on exige une signature ou pas pour entrer en vigueur.

Cible : pydantic v2 (container). Module PUR.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import Field, model_validator

from app.contracts.analysis_v2_schemas import Strict
from app.contracts.comite_schema import Texte
from app.contracts.modele_entreprise_schema import Architecture

__all__ = [
    "ActionArchitecture", "EtatArchitecture", "EtatSigneeArchitecture",
    "DemandeDecisionArchitecture", "VersionArchitecture", "DecisionArchitecture",
    "SigneeArchitectureServie", "PropositionArchitectureServie", "EnVigueurArchitectureServie",
    "ArchitectureServie",
]

ActionArchitecture = Literal["signer", "ecarter"]

EtatArchitecture = Literal[
    "aucune_proposee",                     # personne n'a encore proposé d'architecture
    "en_attente_de_signature",              # une version attend, aucune n'a jamais été signée
    "signee",                               # une version signée, rien en attente
    "signee_nouvelle_version_en_attente",   # la signée est affichée, une autre attend le comité
    "aucune_signee",                        # des versions proposées, toutes écartées ou remplacées
]
EtatSigneeArchitecture = Literal["tient", "a_revoir"]


class DemandeDecisionArchitecture(Strict):
    """Ce que l'écran envoie pour signer ou écarter UNE version : le signataire et son motif."""
    auteur: Texte = Field(max_length=120)
    motif: Texte = Field(max_length=4000)


class VersionArchitecture(Strict):
    """Une version PROPOSÉE, telle que le registre la garde (jamais réécrite, migration 061)."""
    id: int
    ticker_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    auteur: Texte
    propose_le: datetime
    architecture: Architecture

    @model_validator(mode="after")
    def _meme_titre_meme_version(self) -> "VersionArchitecture":
        if (self.architecture.ticker_id, self.architecture.version) != (self.ticker_id, self.version):
            raise ValueError(f"la ligne ({self.ticker_id} v{self.version}) ne porte pas "
                             f"l'architecture ({self.architecture.ticker_id} v{self.architecture.version})")
        return self


class DecisionArchitecture(Strict):
    """Une ligne du procès-verbal (migration 062). `signaux` = les écarts NOMMÉS ([S2]/[S3b]) que
    le comité avait sous les yeux en décidant — jamais vide à l'excuse, toujours un tableau."""
    id: int
    architecture_id: int
    ticker_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    action: ActionArchitecture
    auteur: Texte
    motif: Texte
    signaux: list[str] = Field(default_factory=list)
    decide_le: datetime


class SigneeArchitectureServie(Strict):
    """La version signée : tient-elle encore contre le dossier du jour (#53 : rien de stocké n'est
    un verdict) ? Les signaux DU JOUR sont recalculés, distincts de ceux du PV (ce que le comité
    voyait alors)."""
    version: VersionArchitecture
    signature: DecisionArchitecture
    etat: EtatSigneeArchitecture
    motif_etat: str = Field(min_length=1)
    signaux_du_jour: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _coherence(self) -> "SigneeArchitectureServie":
        if self.signature.action != "signer" or self.signature.architecture_id != self.version.id:
            raise ValueError("la signature servie n'est pas celle de cette version")
        return self


class PropositionArchitectureServie(Strict):
    """La version en attente : tient-elle contre le dossier du jour ? Sinon le motif — le comité ne
    pourra pas la signer tant qu'elle ne tient pas."""
    version: VersionArchitecture
    signable: bool
    motif_refus: Optional[str] = None
    signaux: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _coherence(self) -> "PropositionArchitectureServie":
        if self.signable != (self.motif_refus is None):
            raise ValueError("une proposition est signable ssi aucun motif ne l'en empêche")
        return self


class EnVigueurArchitectureServie(Strict):
    """Ce que l'interrupteur `signature_de_l_architecture` fait servir comme architecture EN
    VIGUEUR (§6.2) : `true` → la signée si elle tient, sinon aucune ; `false` → la dernière proposée
    qui tient, signée ou non."""
    version: Optional[VersionArchitecture] = None
    motif: str = Field(min_length=1)

    @model_validator(mode="after")
    def _motif_meme_sans_version(self) -> "EnVigueurArchitectureServie":
        # Une architecture `None` en vigueur dit TOUJOURS pourquoi (#83) — jamais un champ vide
        # que le lecteur devrait deviner.
        return self


class ArchitectureServie(Strict):
    """L'architecture d'un titre, telle que le comité la voit — recalculée à la lecture."""
    ticker_id: str = Field(min_length=1)
    etat: EtatArchitecture
    signee: Optional[SigneeArchitectureServie] = None
    en_attente: Optional[PropositionArchitectureServie] = None
    en_vigueur: EnVigueurArchitectureServie
    versions_proposees: int = Field(ge=0)
    proces_verbal: list[DecisionArchitecture] = Field(default_factory=list)   # le plus récent d'abord
    genere_le: datetime

    @model_validator(mode="after")
    def _etat_coherent(self) -> "ArchitectureServie":
        attendu = {
            (False, False): "aucune_proposee" if self.versions_proposees == 0 else "aucune_signee",
            (False, True): "en_attente_de_signature",
            (True, False): "signee",
            (True, True): "signee_nouvelle_version_en_attente",
        }[(self.signee is not None, self.en_attente is not None)]
        if self.etat != attendu:
            raise ValueError(f"état `{self.etat}` servi, `{attendu}` attendu d'après ses pièces")
        return self
