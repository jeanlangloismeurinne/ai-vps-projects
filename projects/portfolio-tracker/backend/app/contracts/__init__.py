"""
Contrats Pydantic V2 — HOME RUNTIME des schémas d'analyse (SCHEMA_VERSION = v2.0.0).

Origine de conception : `roadmap/provenance-cards/*_schema.py` (dérivés des cartes de provenance).
Le contexte de build du backend est `./backend` seul → roadmap/ est hors image : les contrats
consommés à l'exécution vivent donc ICI. Toute évolution de contrat se répercute sur les 3 points de
synchro (règle #19 CLAUDE.md) — dont ce package. Copie fidèle des schémas figés (seuls les imports
croisés sont passés en relatifs).

Ce lot (chaîne d'analyse) expose : ResearchMemo, BullCase, BearCase, RiskMatrix, Hypothese (analyse) ;
ReadinessReport + compute_verdict (curator gate) ; ContextPack (front-load) ; WorkerRequest/
WorkerResponse/WorkerExchange + ProducedEntry (C1, frontière orchestrateur↔ouvrier — search-worker) ;
ThesisValidation + RiskAck/ValuationRange (§9 décision — G2 s'y exerce le plus fort : la décision est
contrainte par l'analyse, pas par l'UX ; lot 7, migration 030) ; Mode1..Mode5 + Mode6Review (§10/§11
monitoring — anti-churn et anti-seuil-mécanique ; lot 8, migration 031).
Les contrats restants (ingestion/debate/exit) seront copiés au moment de leurs agents.
"""
from .analysis_v2_schemas import (
    SCHEMA_VERSION,
    BearCase,
    BullCase,
    Hypothese,
    ResearchMemo,
    RiskMatrix,
    SourceEntryRef,
    valider_pont_risques_hypotheses,
)
from .context_pack_schema import CANONICAL_DIMS, ContextPack, DimensionDigest
from .decision_validate_schema import RiskAck, ThesisValidation, ValuationRange
from .monitoring_mode6_schema import (
    HypothesisReview,
    Mode6Review,
    RendementProspectif,
    ValuationThermometer,
)
from .monitoring_modes_1_5_schema import (
    Mode1PreEvent,
    Mode2QuarterlyReview,
    Mode3DecisionReview,
    Mode4SectorPulse,
    Mode5Routing,
    MonitoringSession,
)
from .readiness_report_schema import ReadinessReport, compute_verdict
from .synthesis_schema import GroundedSynthesis, SynthesisClaim
from .worker_delegation_schema import (
    SOURCE_RELIABILITY_BASELINE,
    ExecutionDeclaration,
    OutputSchema,
    ProducedEntry,
    WorkerExchange,
    WorkerRequest,
    WorkerResponse,
)

__all__ = [
    "SCHEMA_VERSION",
    "ResearchMemo",
    "BullCase",
    "BearCase",
    "RiskMatrix",
    "Hypothese",
    "SourceEntryRef",
    "valider_pont_risques_hypotheses",
    "ReadinessReport",
    "compute_verdict",
    "GroundedSynthesis",
    "SynthesisClaim",
    "ContextPack",
    "DimensionDigest",
    "CANONICAL_DIMS",
    "ThesisValidation",
    "RiskAck",
    "ValuationRange",
    "Mode1PreEvent",
    "Mode2QuarterlyReview",
    "Mode3DecisionReview",
    "Mode4SectorPulse",
    "Mode5Routing",
    "Mode6Review",
    "MonitoringSession",
    "HypothesisReview",
    "ValuationThermometer",
    "RendementProspectif",
    "WorkerRequest",
    "WorkerResponse",
    "WorkerExchange",
    "ProducedEntry",
    "OutputSchema",
    "ExecutionDeclaration",
    "SOURCE_RELIABILITY_BASELINE",
]
