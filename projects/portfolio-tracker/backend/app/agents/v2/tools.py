"""
Exécuteurs d'outils de la boucle tool-calling V2 (§5.2) — `web_search`, `fetch_url`, `query_knowledge`.

Ce module fait le pont entre le `tools_json` déclaré en DB sur le `search-worker` (migration 025) et
du code réel. Chaque exécuteur prend le dict d'arguments émis par le modèle et rend un objet
JSON-sérialisable réinjecté en message `role=tool`.

Trois principes :

  1. **Un échec est une valeur de retour, pas une exception.** La boucle du runner attrape déjà tout,
     mais on formate ici des `{"error": …}` explicites et actionnables : le modèle doit pouvoir
     distinguer « la recherche a échoué » de « la recherche n'a rien trouvé ». Confondre les deux est
     précisément ce qui produit un `uncovered_fields` mensonger.
  2. **Les arguments du modèle sont des entrées non fiables.** `max_results` est borné, `ticker_id`
     est forcé au ticker de la requête (un ouvrier n'a pas à explorer la connaissance d'un autre
     titre), les URL non http(s) sont rejetées.
  3. **Volume maîtrisé.** Chaque retour est tronqué : le worker tourne jusqu'à 6 tours et tout ce qui
     entre ici est repayé en tokens d'entrée à chaque tour suivant.
"""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Optional

from app.db.database import get_db_session
from app.knowledge.service import query_knowledge
from app.knowledge.websearch import SearchUnavailable, fetch_url, web_search

logger = logging.getLogger(__name__)

ToolExecutor = Callable[[dict[str, Any]], Awaitable[Any]]

_MAX_SEARCH_RESULTS = 8
_MAX_KNOWLEDGE_RESULTS = 15
_KNOWLEDGE_CONTENT_CHARS = 700   # de quoi juger d'un doublon, pas de quoi recopier l'entrée


async def exec_web_search(args: dict[str, Any]) -> dict[str, Any]:
    """`web_search(query, max_results)` → liste de résultats normalisés.

    `source_type_max` accompagne chaque résultat : c'est le plafond de qualification que le domaine
    peut justifier. Le modèle le voit AVANT de rédiger son entry, ce qui lui évite de proposer un
    `source_type` qui sera de toute façon rabattu côté Python.
    """
    query = (args.get("query") or "").strip()
    if not query:
        return {"error": "web_search : argument 'query' vide."}
    try:
        n = int(args.get("max_results") or 5)
    except (TypeError, ValueError):
        n = 5
    n = max(1, min(n, _MAX_SEARCH_RESULTS))

    try:
        hits = await web_search(query, n)
    except SearchUnavailable as e:
        return {"error": f"recherche web indisponible : {e}", "retryable": False}
    except Exception as e:  # noqa: BLE001
        logger.warning("exec_web_search(%r) : %s", query[:80], e)
        return {"error": f"recherche web en échec : {e}", "retryable": True}

    if not hits:
        return {"query": query, "results": [], "note": "Aucun résultat — la recherche a bien abouti."}
    return {"query": query, "results": [h.to_dict() for h in hits]}


async def exec_fetch_url(args: dict[str, Any]) -> dict[str, Any]:
    """`fetch_url(url)` → texte extrait de la page (tronqué)."""
    url = (args.get("url") or "").strip()
    if not url:
        return {"error": "fetch_url : argument 'url' vide."}
    try:
        return await fetch_url(url)
    except ValueError as e:
        return {"error": str(e), "retryable": False}
    except Exception as e:  # noqa: BLE001
        logger.info("exec_fetch_url(%s) : %s", url[:120], e)
        return {"error": str(e), "retryable": True}


def make_query_knowledge_executor(ticker_id: Optional[str]) -> ToolExecutor:
    """`query_knowledge(query, limit, min_reliability)` → entrées COURANTES déjà en base (anti-doublon).

    Le `ticker_id` est celui de la `WorkerRequest`, jamais celui que le modèle passerait en argument :
    la portée de lecture d'un ouvrier est fixée par son mandat.
    """

    async def _exec(args: dict[str, Any]) -> dict[str, Any]:
        query = (args.get("query") or "").strip() or None
        try:
            limit = int(args.get("limit") or 10)
        except (TypeError, ValueError):
            limit = 10
        try:
            min_rel = float(args.get("min_reliability") or 0.0)
        except (TypeError, ValueError):
            min_rel = 0.0

        try:
            async with get_db_session() as conn:
                rows = await query_knowledge(
                    conn,
                    ticker_id=ticker_id,
                    query=query,
                    min_reliability=max(0.0, min(min_rel, 1.0)),
                    limit=max(1, min(limit, _MAX_KNOWLEDGE_RESULTS)),
                )
        except Exception as e:  # noqa: BLE001
            logger.warning("exec_query_knowledge(%r) : %s", (query or "")[:80], e)
            return {"error": f"lecture de la base de connaissance en échec : {e}"}

        return {
            "ticker_id": ticker_id,
            "count": len(rows),
            "entries": [
                {
                    "entry_id": r["id"],
                    "version": r["version"],
                    "entry_type": r["entry_type"],
                    "title": r["title"],
                    "content": (r["content"] or "")[:_KNOWLEDGE_CONTENT_CHARS],
                    "source_type": r["source_type"],
                    "source_date": r["source_date"].isoformat() if r.get("source_date") else None,
                    "reliability_score": float(r["reliability_score"]),
                    "reliability_tier": r["reliability_tier"],
                    "match_mode": r.get("match_mode"),
                }
                for r in rows
            ],
        }

    return _exec


def build_tool_executors(*, ticker_id: Optional[str]) -> dict[str, ToolExecutor]:
    """Table `nom d'outil → exécuteur` attendue par `run_tool_json_agent`. Les noms DOIVENT
    correspondre au `tools_json` de l'agent en DB (migration 025) — un outil déclaré sans exécuteur
    se traduit par « outil inconnu » côté modèle."""
    return {
        "web_search": exec_web_search,
        "fetch_url": exec_fetch_url,
        "query_knowledge": make_query_knowledge_executor(ticker_id),
    }
