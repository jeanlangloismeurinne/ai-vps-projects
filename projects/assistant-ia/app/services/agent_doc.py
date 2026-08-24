"""
Accès au doc système versionné de l'agent (`agent_system_doc`).

Table append-only : une version n'est **jamais** modifiée en place, on en crée une nouvelle et on
déplace le drapeau `active`. L'index unique partiel `uq_agent_system_doc_active` garantit qu'une
seule ligne est active à la fois.

Isolation (roadmap §5.6) : ce document est le prompt de *cet agent*. Il n'a aucun rapport avec les
`CLAUDE.md` du repo de développement, et ce module ne lit ni n'écrit jamais ces fichiers.
"""
import logging
from dataclasses import dataclass

from app.db import get_pool

logger = logging.getLogger(__name__)


@dataclass
class SystemDoc:
    version: int
    content: str


async def get_active_doc() -> SystemDoc | None:
    """Lit la version active. Appelée **à chaque tour**, jamais mise en cache au démarrage :
    c'est ce qui rend l'approbation d'un diff effective immédiatement, sans redéploiement."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT version, content FROM agent_system_doc WHERE active LIMIT 1"
    )
    if not row:
        return None
    return SystemDoc(version=row["version"], content=row["content"])


async def get_doc_by_version(version: int) -> SystemDoc | None:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT version, content FROM agent_system_doc WHERE version = $1", version
    )
    if not row:
        return None
    return SystemDoc(version=row["version"], content=row["content"])
