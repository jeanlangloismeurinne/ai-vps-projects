"""Contrat du PARCOURS DU COMITÉ — les trois niveaux de drill-down (chantier v3, lot 6 maillon 2,
spec §8.1). Ce que chaque écran reçoit, et rien d'autre.

  NIVEAU 1 `DossierTitre`       — « peut-on décider ? » en tête, puis la note de qualité de chaque
                                  méthodologie, puis leurs conclusions (la note de comité projetée).
  NIVEAU 2 `FrameworkDuDossier` — une méthodologie : ses questions, le statut de chacune, l'avis du
                                  manager et ses 4 contrôles.
  NIVEAU 3 `PreuvesQuestion`    — une question : chaque réponse SERVIE, son rang dérivé, les pièces
                                  citées, l'actualité recalculée, la méthode d'approximation.

TOUT EST PRODUIT À LA LECTURE (#53/#54/#77), RIEN N'EST PERSISTÉ
----------------------------------------------------------------
L'avis du manager, l'actualité, la note de qualité et l'alerte se recalculent à chaque GET, par le
seul assembleur `agents/v2/parcours.py`. Un écran qui lirait un verdict stocké servirait celui
d'avant le dernier fait important publié.

L'ARBITRAGE DU COMITÉ QUI COMMANDE LE NIVEAU 1 (2026-09-25, n°3)
----------------------------------------------------------------
Un dossier complet est l'état NORMAL. Quand il ne l'est pas, l'incomplétude s'affiche comme une
ALERTE, en tête, qui nomme ce qui manque et POURQUOI le système n'a pas pu l'obtenir — jamais comme
un compteur parmi d'autres. D'où `PeutOnDecider` : un état, un motif, et la liste NOMINATIVE des
manques, chacun avec sa cause. Un compteur « 5 manques » sans leur liste serait exactement le
compteur que le comité a refusé.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import Field, model_validator

from app.contracts.analysis_v2_schemas import Strict, Tier
from app.contracts.cause_manque_schema import CauseManqueCollecte
from app.contracts.framework_answer_schema import (
    ControlesManager,
    FrameworkAnswerServie,
    NatureEntry,
    Statut,
)
from app.contracts.memo_projete_schema import MemoProjete
from app.contracts.qualite_info_schema import QualiteInfo

# ── Le manque, et sa cause ─────────────────────────────────────────────────────────────────────

# CE QUI MANQUE. Quatre formes, parce qu'elles appellent quatre gestes différents au comité.
NatureManque = Literal[
    "sans_reponse",   # question applicable, aucune réponse au dossier
    "non_fondee",     # l'analyste a répondu « je ne peux pas fonder » (non_fondable)
    "perimee",        # fondée, mais sur des pièces qu'un fait postérieur a rendues caduques
    "renvoyee",       # le contrôle du manager a refusé la réponse
]

# POURQUOI LE SYSTÈME N'A PAS PU L'OBTENIR. Les trois premières sont celles du collecteur, mot pour
# mot (`cause_manque_schema`) ; les autres nomment les cas où la collecte n'est pas en cause.
CauseManque = Literal[
    "recherche_epuisee",       # la source a été lue, la donnée n'y est pas publiée
    "source_indisponible",     # la source n'a pas pu être lue (panne, temps épuisé) : à relancer
    "sans_source_possible",    # aucune source ne produit cet ingrédient pour cette société
    "pieces_insuffisantes",    # tout a été collecté, les pièces ne suffisent pas à conclure
    "pas_encore_cherchee",     # aucun plan de collecte ne couvre encore la question
    "fait_nouveau_publie",     # un fait important publié depuis rend les pièces caduques
    "actualite_indeterminable",  # les pièces ne sont pas datables : la fraîcheur n'est pas prouvée
    "controle_ko",             # le manager a refusé la réponse (contrôle nommé dans l'explication)
]


class IngredientManquant(Strict):
    """Un ingrédient de la question que la dernière collecte n'a pas ramené — la PREUVE de la cause.
    Le motif est la prose du producteur, telle quelle : le comité doit pouvoir lire ce que la
    machine a vraiment rencontré, pas une paraphrase."""
    ingredient_id: str = Field(min_length=1)
    cause: CauseManqueCollecte
    motif: str = Field(min_length=1)
    constate_le: datetime


class Manque(Strict):
    """UNE ligne de l'alerte : ce qui manque, et pourquoi."""
    framework_id: str = Field(min_length=1)
    libelle_framework: str = Field(min_length=1)
    question_id: str = Field(min_length=1)
    enonce: str = Field(min_length=1)
    nature: NatureManque
    cause: CauseManque
    explication: str = Field(min_length=1)
    ingredients: list[IngredientManquant] = Field(default_factory=list)
    # La question est-elle déjà repartie en recherche ? (mandat manager/comité ouvert)
    mandat_ouvert_id: Optional[int] = None
    answer_id: Optional[int] = None

    @model_validator(mode="after")
    def _une_cause_de_collecte_se_prouve(self):
        # Dire « recherche épuisée » sans montrer ce qui a été cherché serait un verdict
        # inattaquable (maquette niveau 3, règle 3). La cause de collecte exige sa preuve.
        if self.cause in ("recherche_epuisee", "source_indisponible", "sans_source_possible"):
            if not self.ingredients:
                raise ValueError(
                    f"cause `{self.cause}` sans aucun ingrédient manquant : une cause de collecte "
                    "se prouve par ce que la collecte a rencontré, ingrédient par ingrédient")
        return self


class PeutOnDecider(Strict):
    """La réponse en tête de la page d'un titre (arbitrage du comité n°3)."""
    etat: Literal["dossier_complet", "dossier_incomplet", "non_revalidable"]
    motif: str = Field(min_length=1)
    manques: list[Manque] = Field(default_factory=list)

    @model_validator(mode="after")
    def _l_etat_dit_la_liste(self):
        if self.etat == "dossier_complet" and self.manques:
            raise ValueError("`dossier_complet` avec des manques : l'alerte serait tue")
        if self.etat == "dossier_incomplet" and not self.manques:
            raise ValueError("`dossier_incomplet` sans aucun manque nommé : un compteur sans sa "
                             "liste est exactement ce que le comité a refusé")
        return self


# ── NIVEAU 1 ───────────────────────────────────────────────────────────────────────────────────

class SyntheseFramework(Strict):
    """Une méthodologie vue du niveau 1 : sa note de qualité et ses décomptes. La note est PUBLIÉE
    à côté du rang moyen, jamais fondue avec lui (#50, portés par `QualiteInfo`)."""
    framework_id: str = Field(min_length=1)
    libelle: str = Field(min_length=1)
    methodologie: str = Field(min_length=1)
    framework_version: str = Field(min_length=1)
    qualite: Optional[QualiteInfo] = None      # None = aucune réponse au dossier
    n_questions: int = Field(ge=0)
    n_applicables: Optional[int] = Field(default=None, ge=0)   # None = émetteur non classé
    n_acquittees: int = Field(ge=0)
    n_renvoyees: int = Field(ge=0)
    n_manques: int = Field(ge=0)


class DossierTitre(Strict):
    """NIVEAU 1 — `/v2/tickers/:id/dossier`."""
    schema_version: Literal["v3.0.0"] = "v3.0.0"
    ticker_id: str = Field(min_length=1)
    archetype: Optional[str] = None
    genere_le: datetime
    peut_on_decider: PeutOnDecider
    frameworks: list[SyntheseFramework]
    memo: MemoProjete


# ── NIVEAU 2 ───────────────────────────────────────────────────────────────────────────────────

class ReponseResumee(Strict):
    """Une réponse vue du niveau 2 — résumée, jamais arrondie : `approxime` reste `approxime`."""
    answer_id: int
    analyste: str = Field(min_length=1)
    statut: Statut
    rang_derive: Optional[Tier] = None
    actualite: Optional[Literal["courante", "perimee", "indeterminable"]] = None
    verdict: Optional[Literal["acquitte", "renvoye"]] = None
    controles: Optional[ControlesManager] = None


class LigneQuestion(Strict):
    question_id: str = Field(min_length=1)
    enonce: str = Field(min_length=1)
    applicable: Optional[bool] = None          # None = émetteur non classé
    dispensee: bool = False
    reponses: list[ReponseResumee] = Field(default_factory=list)
    manque: Optional[Manque] = None


class FrameworkDuDossier(Strict):
    """NIVEAU 2 — `/v2/tickers/:id/frameworks/:fid`."""
    schema_version: Literal["v3.0.0"] = "v3.0.0"
    ticker_id: str = Field(min_length=1)
    archetype: Optional[str] = None
    synthese: SyntheseFramework
    questions: list[LigneQuestion]


# ── NIVEAU 3 ───────────────────────────────────────────────────────────────────────────────────

class PieceCitee(Strict):
    """Une pièce du dossier, telle que le niveau 3 la montre avant qu'on clique dessus. Le rang,
    la nature et la date restent trois colonnes (#50) — aucune pastille composite."""
    entry_id: int
    role: Literal["citee", "ingredient"]
    present_au_corpus: bool                    # False = citée mais introuvable en base
    titre: Optional[str] = None
    source_type: Optional[str] = None
    source_url: Optional[str] = None
    source_date: Optional[date] = None
    date_du_fait: Optional[date] = None
    reliability_tier: Optional[Tier] = None
    nature: Optional[NatureEntry] = None
    remplacee: bool = False                    # supersédée depuis la réponse


class RenvoiAEmettre(Strict):
    """Le manager RENVERRAIT aujourd'hui, mais aucun mandat n'est ouvert : l'avis recalculé a changé
    depuis la dernière revue persistée (une pièce a bougé). Le contrat `ManagerVerdict` interdit un
    renvoi sans mandat (Écart B) — on ne l'invente pas, on NOMME l'état : le prochain passage
    l'émettra."""
    controles: ControlesManager
    motif: str = Field(min_length=1)


class PreuveReponse(Strict):
    answer_id: int
    # La réponse SERVIE (actualité recalculée), avec l'avis du manager attaché quand il est complet.
    answer: FrameworkAnswerServie
    etat_revue: Literal["revue", "renvoi_a_emettre", "non_revalidable"]
    renvoi_a_emettre: Optional[RenvoiAEmettre] = None
    pieces: list[PieceCitee] = Field(default_factory=list)
    # La plus faible des pièces citées : le rang affiché « au survol » se dérive d'elle (maquette,
    # règle 2 : un rang nu se lit comme un jugement, un rang dérivé se conteste).
    rang_plus_faible_cite: Optional[Tier] = None

    @model_validator(mode="after")
    def _l_etat_de_revue_dit_ou_lire_l_avis(self):
        a_un_avis = self.answer.manager is not None
        if (self.etat_revue == "revue") != a_un_avis:
            raise ValueError(f"etat_revue `{self.etat_revue}` mais avis attaché = {a_un_avis}")
        if (self.etat_revue == "renvoi_a_emettre") != (self.renvoi_a_emettre is not None):
            raise ValueError("`renvoi_a_emettre` porté ssi etat_revue = renvoi_a_emettre")
        return self


class PreuvesQuestion(Strict):
    """NIVEAU 3 — `/v2/tickers/:id/frameworks/:fid/q/:qid`. Une question, TOUTES ses réponses
    (deux analystes = deux preuves, jamais une moyenne, §3.4) et, s'il y a lieu, son manque."""
    schema_version: Literal["v3.0.0"] = "v3.0.0"
    ticker_id: str = Field(min_length=1)
    framework_id: str = Field(min_length=1)
    libelle_framework: str = Field(min_length=1)
    framework_version: str = Field(min_length=1)
    question_id: str = Field(min_length=1)
    enonce: str = Field(min_length=1)
    applicable: Optional[bool] = None
    preuves: list[PreuveReponse] = Field(default_factory=list)
    manque: Optional[Manque] = None
