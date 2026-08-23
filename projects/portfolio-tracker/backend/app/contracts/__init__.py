"""
Contrats Pydantic V2 — HOME RUNTIME des schémas d'analyse (SCHEMA_VERSION = v2.0.0).

Origine de conception : `roadmap/provenance-cards/*_schema.py` (dérivés des cartes de provenance).
Le contexte de build du backend est `./backend` seul → roadmap/ est hors image : les contrats
consommés à l'exécution vivent donc ICI. Toute évolution de contrat se répercute sur les 3 points de
synchro (règle #19 CLAUDE.md) — dont ce package. Copie fidèle des schémas figés (seuls les imports
croisés sont passés en relatifs).

Ce lot (chaîne d'analyse) expose : ResearchMemo, BullCase, BearCase, RiskMatrix, Hypothese (analyse) ;
ReadinessReport + compute_verdict (curator gate) ; ContextPack (front-load). Les contrats aval
(worker/ingestion/decision/monitoring/debate/exit) seront copiés au moment de leurs agents.
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
from .readiness_report_schema import ReadinessReport, compute_verdict

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
    "ContextPack",
    "DimensionDigest",
    "CANONICAL_DIMS",
]
