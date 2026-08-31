"""Knowledge Platform (couche 3) — service store/query/snapshot des knowledge_entries."""
from .embeddings import (
    EmbeddingUnavailable,
    backfill_embeddings,
    embed_one,
    embed_texts,
    entry_text,
    is_configured as embeddings_configured,
    to_pgvector,
)
from .websearch import (
    SearchHit,
    SearchUnavailable,
    classify_source_type,
    fetch_url,
    get_search_backend,
    html_to_text,
    issuer_domains_for,
    search_is_configured,
    web_search,
)
from .service import (
    RELIABILITY_TABLE,
    collect_refs,
    compute_reliability,
    get_current_entries,
    query_knowledge,
    snapshot_refs,
    store_knowledge,
)
from .synthesis_feed import (
    SYNTHESIS_TARGETS,
    SynthesisUnavailable,
    SynthesisUngrounded,
    run_synthesis_feed,
)

__all__ = [
    "RELIABILITY_TABLE",
    "compute_reliability",
    "store_knowledge",
    "query_knowledge",
    "get_current_entries",
    "snapshot_refs",
    "collect_refs",
    # synthèse grounded (ingestion-agent mode synthèse)
    "run_synthesis_feed",
    "SynthesisUnavailable",
    "SynthesisUngrounded",
    "SYNTHESIS_TARGETS",
    # embeddings (bge-m3 1024d — migration 027)
    "EmbeddingUnavailable",
    "backfill_embeddings",
    "embed_one",
    "embed_texts",
    "entry_text",
    "embeddings_configured",
    "to_pgvector",
    # accès web du search-worker (Exa/Serper interchangeables)
    "SearchHit",
    "SearchUnavailable",
    "classify_source_type",
    "fetch_url",
    "get_search_backend",
    "html_to_text",
    "issuer_domains_for",
    "search_is_configured",
    "web_search",
]
