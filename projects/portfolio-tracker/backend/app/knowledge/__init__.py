"""Knowledge Platform (couche 3) — service store/query/snapshot des knowledge_entries."""
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
]
