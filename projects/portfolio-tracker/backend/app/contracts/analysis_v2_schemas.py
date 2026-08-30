"""
Schémas Pydantic versionnés des 4 JSON d'analyse V2 — DÉRIVÉS des cartes de provenance.

Source de vérité : les cartes de provenance champ-par-champ (voir provenance-viz/index.html
et §8 de 01-spec-v2-unifiee.md). Ce fichier est la matérialisation de la garantie (1)
« JSON valide & complet » et l'un des 3 points de synchronisation (G1) — prompt agent,
frontend, import/validation. Toute évolution de contrat se répercute ici EN MÊME TEMPS que
sur les deux autres points (règle #19 du CLAUDE.md projet).

Règles de dérivation encodées (mécaniques depuis la carte) :
  R.a  extra='forbid' partout           -> verrouille Q2 (aucun verdict dans le memo) et
                                           empêche tout champ hors contrat.
  R.b  nature=factual  -> source_entry_refs OBLIGATOIRE non vide (NonEmptyRefs).
       nature=judgment -> pas de refs directes (grounding délégué à un frère factuel).
       nature=derived  -> pas de refs (grounding hérité des inputs).
       nature=ref      -> le porteur (list[SourceEntryRef]).
  R.c  enums / posture  -> Literal (valeurs closes).
  R.d  base-rate requis (règle 2) -> champ base_rate typé et obligatoire.
  R.e  obligatoires conditionnels -> model_validator.

Amendement 2026-08-19 (findings #1-#3) intégré : management.source_entry_refs,
moat.durabilite_ans.base_rate, industry.croissance_marche_{historique,prospective}.
"""
from __future__ import annotations

from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "v2.0.0"  # bump à tout changement de contrat (3 points de synchro)


# ─────────────────────────── primitives partagées ───────────────────────────
class Strict(BaseModel):
    """Base commune : aucun champ hors contrat n'est accepté (R.a, verrou Q2)."""
    model_config = ConfigDict(extra="forbid")


class SourceEntryRef(Strict):
    entry_id: int
    version: int = 1


# porteur de grounding d'un champ factual : au moins une référence (R.b)
NonEmptyRefs = Annotated[list[SourceEntryRef], Field(min_length=1)]

Tier = Literal["A", "A-", "B+", "B", "B-", "C+", "C"]


class BaseRate(Strict):
    """Ancre base-rate en probabilité (règle 2)."""
    reference_class: str = Field(min_length=1)
    taux: float = Field(ge=0.0, le=1.0)
    ajustement: Optional[str] = None

    @field_validator("taux", mode="before")
    @classmethod
    def coerce_pct_to_fraction(cls, v: object) -> object:
        # Le modèle renvoie parfois 70 (%) au lieu de 0.70 (fraction)
        if isinstance(v, (int, float)) and v > 1:
            return float(v) / 100
        return v


class BaseRatePct(Strict):
    """Ancre base-rate en pourcentage (industry / valuation)."""
    reference_class: str = Field(min_length=1)
    taux_pct: float

    @model_validator(mode="before")
    @classmethod
    def alias_taux(cls, v: object) -> object:
        # Le modèle renvoie parfois `taux` au lieu de `taux_pct` (confusion BaseRate/BaseRatePct)
        if isinstance(v, dict) and "taux" in v and "taux_pct" not in v:
            v = dict(v)
            v["taux_pct"] = v.pop("taux")
        return v


class Scenarios(Strict):
    bear: float
    base: float
    bull: float


class ReverseDcf(Strict):
    croissance_implicite_prix_actuel_pct: float
    verdict: str


# ══════════════════════════ 1. research_memo_json ═══════════════════════════
class BusinessModel(Strict):
    description: str
    drivers_revenus: list[str]
    recurrence_pct: float = Field(ge=0, le=100)
    unit_economics: str                 # derived (hér. financials)
    source_entry_refs: NonEmptyRefs     # bloc factual -> R.b


MoatType = Literal[
    "intangibles", "switching_costs", "network_effects",
    "cost_advantage", "scale_economics", "scale_economics_shared",
]


class Durabilite(Strict):
    forte: int
    incertaine: int
    base_rate: BaseRate                 # finding #2 (règle 2)


class Preuve(Strict):
    fait: str                           # factual
    source_entry_refs: NonEmptyRefs


class Moat(Strict):
    # type/score/trend = judgment, grounding DÉLÉGUÉ à preuves[] (non vide)
    type: list[MoatType] = Field(min_length=1)
    score: int = Field(ge=1, le=5)
    durabilite_ans: Durabilite
    trend: Literal["widening", "stable", "eroding"]
    preuves: list[Preuve] = Field(min_length=1)


class EarningsQuality(Strict):
    score: Literal["high", "medium", "low"]
    accruals_flag: bool
    note: Optional[str] = None


class Levier(Strict):
    dette_nette_ebitda: float


class Financials(Strict):
    roic_pct: float
    wacc_estime_pct: float              # derived (estimé)
    roic_vs_wacc: str                   # derived
    roic_trend_5y: Literal["rising", "stable", "declining"]
    fcf_conversion_pct: float
    intensite_capex_pct: float
    earnings_quality: EarningsQuality
    levier: Levier
    source_entry_refs: NonEmptyRefs


class CapitalAllocationScorecard(Strict):
    ma: str
    buybacks: str
    dividendes: str
    reinvestissement: str
    note: Optional[str] = None


class Management(Strict):
    capital_allocation_scorecard: CapitalAllocationScorecard
    incitations: str                    # factual
    skin_in_game_pct: float             # factual
    candeur: str                        # judgment
    score: int = Field(ge=1, le=5)
    source_entry_refs: NonEmptyRefs     # finding #1 (bloc factual)


class CroissanceProspective(Strict):
    taux_pct: float
    base_rate: BaseRatePct              # finding #3 (règle 2)


class Industry(Strict):
    structure_5forces: str
    croissance_marche_historique_pct: float          # finding #3 (factual)
    croissance_marche_prospective: CroissanceProspective  # finding #3 (prévision)
    cyclicite: Literal["faible", "moyenne", "forte"]
    disruption_vectors: list[str] = Field(default_factory=list)
    position_vs_pairs: str
    source_entry_refs: NonEmptyRefs


class DcfScenarios(Strict):
    bear: float
    base: float
    bull: float
    drivers: dict[str, float]


class Epv(Strict):
    valeur_rentabilite: float
    note: str


class Relatif(Strict):
    multiple: str
    vs_historique: str
    vs_pairs: str


class BaseRateAnchor(Strict):
    reference_class: str = Field(min_length=1)
    taux_base_pct: float
    note: Optional[str] = None


class Valuation(Strict):
    dcf_scenarios: DcfScenarios
    epv: Epv
    reverse_dcf: ReverseDcf             # règle 5 : TOUJOURS présent
    relatif: Relatif
    base_rate_anchor: BaseRateAnchor    # règle 2
    prix_actuel: float                  # factual (Tier A marché) — input critique
    iv_range: tuple[float, float]
    marge_securite_base_pct: float      # derived = indicateur #3 (A3)


class IncertitudeBloquante(Strict):
    question: str
    impact_si_non_resolu: str
    statut: Literal["resolue", "en_cours", "non_resolvable"]
    source_entry_refs: list[SourceEntryRef] = Field(default_factory=list)  # conditionnel


class IncertitudeInvestissable(Strict):
    question: str
    fourchette: str


class ResearchMemo(Strict):
    schema_version: Literal["v2.0.0"] = "v2.0.0"
    business_model: BusinessModel
    moat: Moat
    financials: Financials
    management: Management
    industry: Industry
    valuation: Valuation
    incertitudes_bloquantes: list[IncertitudeBloquante] = Field(default_factory=list)
    incertitudes_investissables: list[IncertitudeInvestissable] = Field(default_factory=list)
    # verrou Q2 : Literal figé + extra='forbid' => aucun verdict ne peut exister
    posture: Literal["NEUTRE"] = "NEUTRE"


# ═══════════════════════ 2. bull_case_json / bear_case_json ══════════════════
class VariantPerception(Strict):
    type: Literal["analytique", "informationnel", "temporel"]
    enonce: str = Field(min_length=1)   # règle 6 : pas d'edge => pas de thèse
    catalyseur_re_rating: str
    horizon_mois: int
    source_entry_refs: NonEmptyRefs


class RechercheDivergente(Strict):
    query: str
    finding_entry_id: int


class Argument(Strict):
    titre: str
    explication: str
    probabilite: float = Field(ge=0, le=1)
    base_rate: BaseRate                 # règle 2 : probabilité ancrée
    source_entry_refs: NonEmptyRefs
    recherche_divergente: list[RechercheDivergente] = Field(default_factory=list)


class Assumptions(Strict):
    croissance_revenue: float
    expansion_marge_fcf: float
    multiple_sortie: float


class ValorisationCote(Strict):
    horizon_ans: int = Field(ge=5)      # A4 : horizon LT
    reverse_dcf: ReverseDcf
    scenarios: Scenarios
    methode: str
    assumptions: Assumptions


class Indicateurs(Strict):
    """A3 : trois axes séparés, jamais fusionnés."""
    qualite_info: float = Field(ge=0, le=1)
    conviction: float = Field(ge=0, le=1)
    marge_securite: float


class GroundingReport(Strict):
    """A2 : rempli par le groundedness-checker (pas auto-déclaré par l'agent)."""
    affirmations_total: int
    etayees: int
    non_etayees: int


class BullCase(Strict):
    schema_version: Literal["v2.0.0"] = "v2.0.0"
    variant_perception: VariantPerception          # règle 6, obligatoire
    arguments: list[Argument] = Field(min_length=1)
    valorisation: ValorisationCote
    catalyseurs: list[str] = Field(default_factory=list)
    conviction: int = Field(ge=1, le=10)
    indicateurs: Indicateurs
    grounding_report: GroundingReport

    @field_validator("conviction", mode="before")
    @classmethod
    def coerce_conviction(cls, v: object) -> object:
        # Le modèle renvoie parfois 0.6 (scale 0-1) au lieu de 6 (scale 1-10)
        if isinstance(v, float):
            if v <= 1.0:
                return max(1, round(v * 10))
            return round(v)
        return v


class ScenarioDestructionValeur(Strict):
    prix_bear: float
    perte_pct: float
    declencheurs: list[str] = Field(min_length=1)


class RefutationItem(Strict):
    cible: str                          # ref d'un argument bull
    contre_argument: str
    source_entry_refs: list[SourceEntryRef] = Field(default_factory=list)


class BearCase(BullCase):
    """Même ossature + spécifiques bear (A6). refutation_du_bull peuplé APRÈS le round (Q4)."""
    failles_bull_conventionnel: list[str] = Field(min_length=1)
    scenario_destruction_valeur: ScenarioDestructionValeur
    conviction_negative: int = Field(ge=1, le=10)
    refutation_du_bull: list[RefutationItem] = Field(default_factory=list)


# ═══════════════════════════ 3. risk_matrix_json ════════════════════════════
Verdict = Literal["PROCEED", "PROCEED_AVEC_CONDITIONS", "PASSER", "SURVEILLER", "TOO_HARD"]


class Axes(Strict):
    """A3 / règle 4 : quatre axes séparés, aucun score global."""
    qualite_business: float = Field(ge=0, le=1)
    qualite_info: float = Field(ge=0, le=1)
    conviction: float = Field(ge=0, le=1)
    marge_securite: float


class RisqueAccepte(Strict):
    risque: str
    probabilite: float = Field(ge=0, le=1)
    impact: Literal["faible", "moyen", "fort"]
    reversible: bool
    base_rate: BaseRate                 # règle 2
    reponse_si_materialise: str
    hypothese_liee: str                 # -> Hypothese.id (pont vers hypotheses[])
    source_entry_refs: NonEmptyRefs


class CapApplique(Strict):
    contrainte: str
    valeur_pct: float
    actif: bool


class RisqueCorrele(Strict):
    facteur: str
    exposition_pct: float


class SizingInputs(Strict):
    conviction: float
    marge_securite: float
    correlation_portefeuille: float     # A8 : nourri par le portefeuille, pas la KB


class OverrideUtilisateur(Strict):
    valeur_pct: float
    override_reason: str = Field(min_length=1)     # A7 : traçabilité obligatoire
    knowledge_entry_ref: Optional[SourceEntryRef] = None


class PositionSizing(Strict):
    pct_formule: float                  # derived : Kelly capé
    pct_recommande: float               # judgment ajusté
    pct_max: float
    methode: str
    inputs: SizingInputs
    cap_applique: CapApplique
    risques_correles_portefeuille: list[RisqueCorrele] = Field(default_factory=list)
    cout_opportunite: str
    ajustement_justification: Optional[str] = None
    override_utilisateur: Optional[OverrideUtilisateur] = None

    @model_validator(mode="after")
    def _justifier_ecart_formule(self):
        if abs(self.pct_recommande - self.pct_formule) > 1e-9 and not self.ajustement_justification:
            raise ValueError("ajustement_justification requis si pct_recommande != pct_formule")
        if self.pct_max > self.cap_applique.valeur_pct:
            raise ValueError("pct_max ne peut dépasser le cap sectoriel (Q6)")
        return self


class SourcesSummary(Strict):
    tier_A: int
    tier_B: int
    tier_C_llm_memory: int
    total_entries: int


class RiskMatrix(Strict):
    schema_version: Literal["v2.0.0"] = "v2.0.0"
    verdict: Verdict                    # SEUL verdict du flux (Q2)
    rationale: str
    axes: Axes
    risques_acceptes: list[RisqueAccepte] = Field(min_length=1)
    pre_mortem: list[str] = Field(min_length=3)    # ≥3 scénarios (Klein)
    position_sizing: PositionSizing
    conditions_entree: list[str] = Field(default_factory=list)
    needs_second_round: bool = False
    second_round_trigger: Optional[str] = None
    sources_summary: SourcesSummary

    @model_validator(mode="after")
    def _obligatoires_conditionnels(self):
        if self.verdict == "PROCEED_AVEC_CONDITIONS" and not self.conditions_entree:
            raise ValueError("conditions_entree requis si verdict=PROCEED_AVEC_CONDITIONS")
        if self.needs_second_round and not self.second_round_trigger:
            raise ValueError("second_round_trigger requis si needs_second_round (Q4)")
        return self


# ═══════════════════════ 4. thesis.hypotheses[] ═════════════════════════════
class Hypothese(Strict):
    id: str
    enonce: str
    kpi: str
    unite: str
    seuil_alerte: float
    seuil_invalidation: float           # règle 3 : falsifiabilité (pilote le monitoring)
    horizon: str
    base_rate: BaseRate                 # règle 2
    statut: Literal["active", "alerte", "invalidee", "confirmee"] = "active"
    source_entry_refs: NonEmptyRefs


def valider_pont_risques_hypotheses(rm: RiskMatrix, hypotheses: list[Hypothese]) -> None:
    """Contrôle inter-JSON (niveau thèse) : chaque risque accepté pointe une hypothèse existante."""
    ids = {h.id for h in hypotheses}
    manquants = [r.hypothese_liee for r in rm.risques_acceptes if r.hypothese_liee not in ids]
    if manquants:
        raise ValueError(f"hypothese_liee sans hypothèse correspondante : {manquants}")
