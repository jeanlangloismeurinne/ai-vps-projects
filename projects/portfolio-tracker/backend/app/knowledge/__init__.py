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
from .service import (
    RELIABILITY_TABLE,
    collect_refs,
    compute_reliability,
    get_current_entries,
    query_knowledge,
    snapshot_refs,
    store_knowledge,
)

__all__ = [
    "RELIABILITY_TABLE",
    "compute_reliability",
    "store_knowledge",
    "query_knowledge",
    "get_current_entries",
    "snapshot_refs",
    "collect_refs",
    # embeddings (bge-m3 1024d — migration 027)
    "EmbeddingUnavailable",
    "backfill_embeddings",
    "embed_one",
    "embed_texts",
    "entry_text",
    "embeddings_configured",
    "to_pgvector",
]
