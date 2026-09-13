"""
Schéma Pydantic versionné de l'EXTRACTION D'INGESTION (§6.5, roadmap KP §4) — DÉRIVÉ des cartes.

Contrat : document brut (ou source structurée directe) → `knowledge_entries[]`. C'est le producteur
de masse du corpus ; le curator/research/bull/bear ne lisent QUE des entries déjà distillées, jamais
les documents bruts (§5.3 : le coût lourd réel est ici, payé UNE fois en Haiku/batch).

Réutilise `ProducedEntry` de C1 (worker_delegation_schema) : « 1 forme d'entry → 2 producteurs »
(search-worker en C1, ingestion-agent ici). Les invariants structurels de l'entry (P2 llm_memory,
plafond de source, score muet interdit) sont hérités de C1 ; C2 ajoute les invariants d'EXTRACTION.

Deux chemins, tranchés par `extraction_mode` :
  • deterministic — EDGAR Company Facts (XBRL 10 ans) + yfinance → `fact_financial` structurés,
    **AUCUN token LLM** (§6.6 : le structuré bon marché est eager, récupéré dès l'ajout du ticker).
  • llm — ingestion-agent (Haiku/Batch) sur le narratif (10-K/10-Q/press) → qualitatif/risk/event/quote.

Garde-fous encodés (par-dessus ceux de ProducedEntry) :
  ANTI-HALLUCINATION : les nombres financiers ne sont JAMAIS extraits par le LLM. `deterministic`
      ⇒ tout entry_type='fact_financial' + content_structured présent ; `llm` ⇒ entry_type ≠ fact_financial.
      Les chiffres viennent de XBRL/yfinance ; l'Opus n'est payé que pour le jugement aval.
  DÉTERMINISTE = GRATUIT (§6.6) : tier='deterministe' ⇒ tokens=0 et cost=0.
  SOURCE COHÉRENTE AU DOCUMENT : le source_type d'une entry ∈ sources autorisées pour le
      doc_source_type. Un document ne peut PAS produire `llm_memory`/`agent_synthesis` (ceux-là
      viennent d'un modèle / d'un agent, pas d'un document).
  CONFIDENTIEL : `is_confidential` (upload) ⇒ source_type='user_provided_confidential'.
  MATÉRIALITÉ (§4.4) : les candidats sous le plancher 0.3 sont ignorés (non stockés) ; `dropped_immaterial`
      les compte (audit). Anti-bruit.
  A1 (append-only) : une nouvelle période financière SUPERSÈDE l'ancienne (`supersedes_period`),
      jamais de mutation.

Cible : pydantic v2 (container backend 2.13.4). Tester en container (host = v1).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import ConfigDict, Field, model_validator

# forme d'entry + énums partagées, définies une seule fois en C1 (source unique — G1)
from worker_delegation_schema import (
    ProducedEntry, Strict, SCHEMA_VERSION, EntryType, SourceType,
)

__all__ = ["IngestionJob", "IngestionResult", "IngestionExecution", "SCHEMA_VERSION"]

# ── types de document (table knowledge_documents, migration 024) ──
DocType = Literal[
    "10-K", "10-Q", "8-K", "earnings_call", "annual_report",
    "press_release", "investor_day", "news", "investor_update",
]
DocSourceType = Literal["edgar", "ir_scrape", "web_search", "user_upload", "rss"]
ExtractionMode = Literal["deterministic", "llm"]

# quel source_type d'entry un document de tel origine peut légitimement produire.
# Exclut structurellement llm_memory (mémoire modèle) et agent_synthesis (dérivé d'agent) :
# un DOCUMENT ne les produit jamais.
DOC_TO_ENTRY_SOURCES: dict[str, set[str]] = {
    "edgar": {"edgar_official", "earnings_transcript_official"},
    "ir_scrape": {"company_ir_official", "earnings_transcript_official", "regulator_filing_eu"},
    "web_search": {"financial_press", "web_search_reputable", "web_search_generic"},
    "user_upload": {"user_provided", "user_provided_confidential"},
    "rss": {"financial_press", "web_search_reputable", "web_search_generic"},
}

MATERIALITY_FLOOR = 0.3  # §4.4 : ignorer si matérialité < 0.3


class IngestionExecution(Strict):
    """§5.3 : déclaration d'exécution. tier='deterministe' pour XBRL/yfinance (gratuit, §6.6),
    'ouvrier' pour l'ingestion-agent Haiku."""
    tier: Literal["deterministe", "ouvrier"]
    model_used: str = Field(min_length=1)   # 'xbrl-companyfacts'/'yfinance' | 'haiku-4-5'
    batch: bool = False                      # Batch API (−50 %) pour l'ingestion de masse
    tokens_in: int = Field(ge=0, default=0)
    tokens_out: int = Field(ge=0, default=0)
    cost_usd: float = Field(ge=0, default=0.0)

    @model_validator(mode="after")
    def _deterministe_gratuit(self):
        # §6.6 : le structuré (XBRL/yfinance) ne coûte aucun token — sinon c'est un LLM déguisé
        if self.tier == "deterministe" and (self.tokens_in or self.tokens_out or self.cost_usd):
            raise ValueError("tier='deterministe' doit avoir tokens=0 et cost=0 (§6.6)")
        return self


class IngestionJob(Strict):
    """Descripteur de la tâche d'extraction. `document_id=None` pour une source structurée directe
    (Company Facts / yfinance) sans document texte."""
    ticker_id: Optional[str] = None          # None = connaissance sectorielle/macro
    document_id: Optional[int] = None        # FK knowledge_documents ; None si source directe
    doc_type: DocType
    doc_source_type: DocSourceType
    content_hash: str = Field(min_length=1)  # SHA256 — dédup document (skip si déjà ingéré)
    fiscal_period: Optional[str] = None       # 'FY-2026' | 'Q4-2025'
    is_confidential: bool = False
    extraction_mode: ExtractionMode
    segment: Optional[str] = None            # sous-segment d'un gros doc (ex: 'Item 1A Risk Factors')


class IngestionResult(Strict):
    """Sortie de l'ingestion-agent : entries matérielles déjà scorées + provenance de l'extraction."""
    job: IngestionJob                        # écho (traçabilité / reproductibilité)
    entries: list[ProducedEntry] = Field(default_factory=list)
    dropped_immaterial: int = Field(ge=0, default=0)  # candidats < MATERIALITY_FLOOR, ignorés
    supersedes_period: Optional[str] = None  # A1 : période financière rendue obsolète (jamais mutée)
    execution: IngestionExecution

    @model_validator(mode="after")
    def _invariants_extraction(self):
        job = self.job
        autorises = DOC_TO_ENTRY_SOURCES[job.doc_source_type]
        for e in self.entries:
            # 1) source cohérente avec l'origine du document (jamais llm_memory/agent_synthesis)
            if e.source_type not in autorises:
                raise ValueError(
                    f"source_type '{e.source_type}' interdit pour un document '{job.doc_source_type}' "
                    f"(autorisés: {sorted(autorises)})"
                )
            # 2) anti-hallucination : les nombres financiers ne viennent JAMAIS du LLM
            if job.extraction_mode == "deterministic":
                if e.entry_type != "fact_financial":
                    raise ValueError(
                        f"extraction déterministe (XBRL/yfinance) ⇒ fact_financial uniquement, "
                        f"trouvé '{e.entry_type}'"
                    )
                if e.content_structured is None:
                    raise ValueError("fact_financial déterministe exige content_structured {metric,value,period}")
            else:  # llm
                if e.entry_type == "fact_financial":
                    raise ValueError(
                        "extraction LLM ne peut pas produire fact_financial — les chiffres viennent "
                        "de XBRL/yfinance (anti-hallucination, §6.6)"
                    )
            # 3) confidentiel : un upload confidentiel produit des données primaires tracées
            if job.is_confidential and e.source_type != "user_provided_confidential":
                raise ValueError("is_confidential ⇒ source_type='user_provided_confidential'")
            # 4) période financière propagée (indispensable au vieillissement −0.05/an, §6.3)
            if e.entry_type == "fact_financial" and not (e.fiscal_period or job.fiscal_period):
                raise ValueError("fact_financial exige un fiscal_period (entry ou job)")

        # 5) cohérence tier/mode : le déterministe n'utilise pas d'ouvrier LLM et vice-versa
        if job.extraction_mode == "deterministic" and self.execution.tier != "deterministe":
            raise ValueError("extraction déterministe ⇒ execution.tier='deterministe'")
        if job.extraction_mode == "llm" and self.execution.tier != "ouvrier":
            raise ValueError("extraction llm ⇒ execution.tier='ouvrier'")
        return self
