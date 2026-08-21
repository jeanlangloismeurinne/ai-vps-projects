"""
Schéma Pydantic versionné de l'INTERFACE ORCHESTRATEUR → OUVRIER (§5.2) — DÉRIVÉ des cartes de provenance.

Contrat le plus AMONT de la chaîne : c'est le boundary par lequel toute donnée entre dans le système.
Un agent métier (curator/research/bull/bear/synthèse/monitoring) ne demande jamais « cherche sur X » ;
il émet une **requête structurée** {query, output_schema attendu, reliability_min} et l'ouvrier
(search-worker/gap-intake/ingestion/groundedness) renvoie des `knowledge_entries` **scorées**,
JAMAIS du texte libre. C'est ce contrat qui rend G3 (donnée versionnée+scorée+figée) vrai à la
frontière : rien n'entre sans source_type + reliability_score + reliability_tier.

`ProducedEntry` (la forme d'une knowledge_entry fraîchement produite) est PARTAGÉE avec C2 (ingestion) :
« 1 forme d'entry → 2 producteurs » (search-worker ici, ingestion-agent en C2). Elle est le
sous-ensemble des colonnes de `knowledge_entries` (migration 024) que l'agent remplit à la création ;
id/version/valid_from/embedding/superseded_by/timestamps sont gérés par la DB (A1, append-only).

Garde-fous encodés :
  G1  extra='forbid' + SCHEMA_VERSION figé -> aucun champ hors contrat ; l'un des 3 points de synchro.
  G3  la WorkerResponse n'a AUCUN champ de texte libre (answer/summary/text) : uniquement `entries[]`
      scorées. Structurellement impossible de renvoyer un fait non sourcé.
  reliability_min honoré : cross-validateur (WorkerExchange) — toute entry retournée a un score >= plancher.
  Plafond de source : aucune entry ne peut être scorée au-dessus du plafond de son source_type
      (baseline + max modulation positive = cross-validation +0.10, §6.3) — anti llm_memory à 0.95.
  P2 (§6.4) : source_type='llm_memory' exige requires_human_review=True + model_cutoff.
  §5.3 : l'ouvrier DÉCLARE model/tier/batch/cache/tokens/cost (ExecutionDeclaration) — coût auditable.
  §13.5 : request_hash persisté (reproductibilité — prompt matérialisé rejouable).
  Pareto (§5.3) : max_entries plafonne le retour ; A6 : `divergent` porte le mandat de falsification (bear).

Cible : pydantic v2 (container backend 2.13.4). Le python hôte a v1 → tester en container.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "v2.0.0"  # même famille que analysis_v2_schemas.py / readiness_report_schema.py

# ── entry_type : cf. commentaire de la table knowledge_entries (migration 024) ──
EntryType = Literal[
    "fact_financial", "fact_qualitative", "event", "quote",
    "analysis", "risk", "llm_memory", "agent_synthesis", "lesson_learned",
]

Tier = Literal["A", "A-", "B+", "B", "B-", "C+", "C"]

# ── source_type + baseline (tier, score) : framework de fiabilité KP §3.3 (autoritaire) ──
# yfinance/fmp = fournisseurs de données de marché structurées (§6.5/§17), non listés au §3.3 mais
# référencés par la table ; baseline alignée sur company_ir_official structuré.
SOURCE_RELIABILITY_BASELINE: dict[str, tuple[str, float]] = {
    "edgar_official": ("A", 0.95),
    "company_ir_official": ("A", 0.90),
    "earnings_transcript_official": ("A-", 0.85),
    "regulator_filing_eu": ("A-", 0.85),
    "yfinance": ("B+", 0.75),
    "fmp": ("B+", 0.75),
    "financial_press": ("B+", 0.75),
    "user_provided_confidential": ("B+", 0.80),
    "user_provided": ("B", 0.70),
    "web_search_reputable": ("B", 0.65),
    "agent_synthesis": ("B-", 0.60),
    "web_search_generic": ("C+", 0.50),
    "llm_memory": ("C", 0.40),
}
SourceType = Literal[
    "edgar_official", "company_ir_official", "earnings_transcript_official",
    "regulator_filing_eu", "yfinance", "fmp", "financial_press",
    "user_provided_confidential", "user_provided", "web_search_reputable",
    "agent_synthesis", "web_search_generic", "llm_memory",
]

# max modulation POSITIVE du score (cross-validation +0.10, §6.3) : plafond dur par source.
_MAX_POSITIVE_MODULATION = 0.10

Worker = Literal["search-worker", "gap-intake", "ingestion-agent", "groundedness-checker"]
Requester = Literal[
    "knowledge-curator", "research-agent", "bull-agent", "bear-agent",
    "thesis-agent", "monitoring-agent", "postmortem-agent",
]
QuestionStatus = Literal["open", "researching", "resolved", "unresolvable"]


class Strict(BaseModel):
    """Base commune : aucun champ hors contrat (G1)."""
    model_config = ConfigDict(extra="forbid")


# ─────────────────────── requête (orchestrateur → ouvrier) ───────────────────────
class OutputSchema(Strict):
    """Ce que l'orchestrateur CHERCHE — jamais OÙ chercher. Le `field_path` ancre le retour sur un
    champ précis du contrat aval (grounding : l'entry comble ce champ)."""
    entry_type: EntryType
    dimension: Optional[str] = None          # dimension MVDD ciblée (business_model, positionnement, …)
    field_path: Optional[str] = None         # champ du contrat aval (ex: 'moat.durabilite_ans')
    fiscal_period: Optional[str] = None       # période visée si applicable


class WorkerRequest(Strict):
    requester: Requester                     # QUI délègue (traçabilité)
    worker: Worker                           # à QUEL ouvrier
    ticker_id: Optional[str] = None          # None = connaissance sectorielle/macro
    query: str = Field(min_length=1)         # question structurée (jamais vide)
    output_schema: OutputSchema              # forme attendue des entries
    reliability_min: float = Field(ge=0, le=1)   # plancher de fiabilité exigé
    max_entries: int = Field(ge=1, le=50, default=10)  # arrêt de Pareto / plafond coût
    divergent: bool = False                  # A6 : mandat de falsification (search-worker du bear)
    check_existing_first: bool = True        # anti-doublon : query_knowledge avant store (gap-intake)


# ─────────────────── entry produite (PARTAGÉE avec C2 ingestion) ───────────────────
class ProducedEntry(Strict):
    """Sous-ensemble des colonnes de `knowledge_entries` (migration 024) qu'un agent remplit à la
    création. Validation STRUCTURELLE seule ici ; la dérivation du score (âge/cross-val/contradiction)
    et l'extraction depuis un document brut sont cardées en C2 (ingestion)."""
    entry_type: EntryType
    title: Optional[str] = None
    content: str = Field(min_length=1)       # Markdown, pivot lisible humain+LLM (jamais vide)
    content_structured: Optional[dict] = None  # ex: {metric, value, period} si applicable
    tags: list[str] = Field(default_factory=list)
    lang: str = "en"
    source_type: SourceType
    source_url: Optional[str] = None
    source_date: Optional[str] = None        # ISO date
    fiscal_period: Optional[str] = None
    reliability_score: float = Field(ge=0, le=1)
    reliability_tier: Tier
    reliability_note: str = Field(min_length=1)  # pourquoi ce score — jamais muet
    requires_human_review: bool = False
    model_cutoff: Optional[str] = None        # ex '2026-01' pour llm_memory
    covers: Optional[str] = None              # field_path que cette entry comble (grounding aval)
    question_status: Optional[QuestionStatus] = None  # si l'entry EST une question ouverte (curator)

    @model_validator(mode="after")
    def _regles_structurelles(self):
        # P2 (§6.4) : mémoire modèle -> revue humaine + cutoff obligatoires
        if self.source_type == "llm_memory":
            if not self.requires_human_review:
                raise ValueError("llm_memory exige requires_human_review=True (P2, §6.4)")
            if not self.model_cutoff:
                raise ValueError("llm_memory exige model_cutoff (P2, §6.4)")
        # Plafond de source : le score ne peut dépasser le baseline + max modulation positive (§6.3).
        baseline_tier, baseline_score = SOURCE_RELIABILITY_BASELINE[self.source_type]
        plafond = baseline_score + _MAX_POSITIVE_MODULATION
        if self.reliability_score > plafond + 1e-9:
            raise ValueError(
                f"{self.source_type}: score {self.reliability_score} > plafond {plafond:.2f} "
                f"(baseline {baseline_score} + cross-val {_MAX_POSITIVE_MODULATION})"
            )
        return self


# ─────────────────────── réponse (ouvrier → orchestrateur) ───────────────────────
class ExecutionDeclaration(Strict):
    """§5.3 / constitution : tout agent déclare tier/modèle/batch/cache. Ici tier='ouvrier' —
    la délégation ne descend que vers des ouvriers (Haiku), jamais l'inverse."""
    tier: Literal["ouvrier"] = "ouvrier"
    model_used: str = Field(min_length=1)
    batch: bool = False                      # Batch API (−50 %) pour l'ingestion de masse
    cache_hit: bool = False
    tokens_in: int = Field(ge=0, default=0)
    tokens_out: int = Field(ge=0, default=0)
    cost_usd: float = Field(ge=0, default=0.0)


class WorkerResponse(Strict):
    """Réponse ouvrier → orchestrateur. G3 : AUCUN champ de texte libre — uniquement `entries[]`
    scorées + les champs non comblés déclarés explicitement (structuré, pas une prose de regret)."""
    request_hash: str = Field(min_length=1)  # §13.5 : hash de la WorkerRequest (reproductibilité)
    worker: Worker
    status: Literal["found", "partial", "not_found"]
    entries: list[ProducedEntry] = Field(default_factory=list)
    uncovered_fields: list[str] = Field(default_factory=list)  # champs demandés non comblés
    execution: ExecutionDeclaration

    @model_validator(mode="after")
    def _status_coherent(self):
        if self.status == "found" and not self.entries:
            raise ValueError("status=found mais aucune entry retournée")
        if self.status == "not_found" and self.entries:
            raise ValueError("status=not_found mais des entries sont présentes")
        return self


# ─────────────────── enveloppe : invariants CROISÉS requête×réponse ───────────────────
class WorkerExchange(Strict):
    """Requête + réponse ensemble — encode les invariants impossibles à poser sur un seul modèle.
    C'est l'objet à valider à la frontière orchestrateur↔ouvrier."""
    request: WorkerRequest
    response: WorkerResponse

    @model_validator(mode="after")
    def _invariants_croises(self):
        req, resp = self.request, self.response
        # cohérence de l'ouvrier
        if resp.worker != req.worker:
            raise ValueError(f"réponse worker={resp.worker} != demandé {req.worker}")
        # reliability_min honoré (le cold-start filet llm_memory ne passe que si min <= 0.40)
        for e in resp.entries:
            if e.reliability_score < req.reliability_min:
                raise ValueError(
                    f"entry score {e.reliability_score} < reliability_min {req.reliability_min}"
                )
        # plafond de retour (arrêt de Pareto / coût)
        if len(resp.entries) > req.max_entries:
            raise ValueError(f"{len(resp.entries)} entries > max_entries {req.max_entries}")
        # type attendu respecté : le contrat de sortie n'est pas décoratif
        want = req.output_schema.entry_type
        mauvais = sorted({e.entry_type for e in resp.entries if e.entry_type != want})
        if mauvais:
            raise ValueError(f"entry_type retournés {mauvais} != demandé '{want}'")
        # A6 : un mandat divergent qui ne trouve rien doit l'ASSUMER explicitement, pas rester muet
        if req.divergent and resp.status == "not_found" and not resp.uncovered_fields:
            raise ValueError("mandat divergent (A6) sans résultat : uncovered_fields doit être explicite")
        return self
