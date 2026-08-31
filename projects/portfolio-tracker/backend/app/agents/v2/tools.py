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
  3. **Volume maîtrisé.** Le worker tourne jusqu'à 6 tours et tout ce qui entre ici est repayé en
     tokens d'entrée à chaque tour suivant. `query_knowledge` tronque ; `fetch_url` ne tronque plus
     mais **sélectionne** les passages pertinents (cf. `document_search`) — moins de caractères
     rendus, et tout le document couvert.
  4. **Ce que les outils ont rapporté est journalisé** (`RetrievalLog`). Le worker s'en sert pour
     confronter le `source_url` que le modèle déclare à ce qui a effectivement été lu.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional
from urllib.parse import urlparse

from app.db.database import get_db_session
from app.knowledge.service import query_knowledge
from app.knowledge.websearch import SearchUnavailable, fetch_url, web_search

logger = logging.getLogger(__name__)

ToolExecutor = Callable[[dict[str, Any]], Awaitable[Any]]

_MAX_SEARCH_RESULTS = 8
_MAX_KNOWLEDGE_RESULTS = 15
_KNOWLEDGE_CONTENT_CHARS = 700   # de quoi juger d'un doublon, pas de quoi recopier l'entrée


# ── journal de récupération ──────────────────────────────────────────────────
# Profondeurs, du plus faible au plus fort. L'ordre est signifiant : `_DEPTHS.index()` sert à ne
# jamais rétrograder une URL déjà vue plus profondément.
_DEPTHS = ("link", "excerpt", "full")


def canonical_url(url: Optional[str]) -> str:
    """Forme comparable d'une URL : hôte sans `www.`, chemin sans slash final, sans schéma ni ancre.

    On garde la query string : sur EDGAR comme sur bien des sites IR, elle DÉSIGNE le document
    (`?doc=...`), donc l'ignorer confondrait deux dépôts distincts.
    """
    p = urlparse((url or "").strip())
    host = (p.netloc or "").lower().removeprefix("www.")
    if not host:
        return ""
    path = (p.path or "").rstrip("/")
    return f"{host}{path}" + (f"?{p.query}" if p.query else "")


@dataclass
class RetrievalLog:
    """Ce que les outils ont **réellement rapporté** pendant un run, par URL.

    Raison d'être : le `source_url` d'une entry est *déclaré* par le modèle, et c'est ce domaine
    déclaré qui détermine `source_type`, donc `reliability_score`. Rien ne liait jusqu'ici cette URL
    à une récupération effective. Mesuré sur NVDA (run C, 2026-08-23) : sur toute la vie du
    conteneur, deux URL seulement ont été récupérées (cnbc.com, kearney.com) — **aucune sec.gov** —
    et le run a pourtant produit 5 entrées portant un `source_url` sec.gov, `edgar_official`,
    score 0.94 tier A. La convention #24 empêche le modèle de choisir son `source_type` ; elle ne
    l'empêchait pas de le choisir *par l'URL*.

    Ce journal est le fait opposable : le worker y confronte chaque `source_url` avant de laisser le
    domaine fixer le score.
    """
    seen: dict[str, str] = field(default_factory=dict)

    def record(self, url: Optional[str], depth: str) -> None:
        key = canonical_url(url)
        if not key or depth not in _DEPTHS:
            return
        current = self.seen.get(key)
        if current is None or _DEPTHS.index(depth) > _DEPTHS.index(current):
            self.seen[key] = depth

    def depth_of(self, url: Optional[str]) -> Optional[str]:
        """`full` | `excerpt` | `link`, ou None si cette URL n'a jamais été rapportée par un outil."""
        key = canonical_url(url)
        return self.seen.get(key) if key else None


async def exec_web_search(
    args: dict[str, Any],
    *,
    log: Optional[RetrievalLog] = None,
    ticker_id: Optional[str] = None,
) -> dict[str, Any]:
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

    if log is not None:
        # Un résultat porteur de texte a bien fait passer du contenu sous les yeux du modèle, mais
        # seulement un extrait de tête (2 000 car. côté Exa). Un résultat sans texte n'est qu'un lien :
        # titre et URL ne fondent aucune citation.
        for h in hits:
            log.record(h.url, "excerpt" if h.text else "link")

    if not hits:
        return {"query": query, "results": [], "note": "Aucun résultat — la recherche a bien abouti."}
    return {"query": query, "results": [h.to_dict(ticker_id) for h in hits]}


async def exec_fetch_url(
    args: dict[str, Any],
    *,
    query: Optional[str] = None,
    log: Optional[RetrievalLog] = None,
    ticker_id: Optional[str] = None,
) -> dict[str, Any]:
    """`fetch_url(url)` → passages de la page qui répondent à la question du mandat.

    `query` n'est PAS un argument du modèle : c'est le mandat du worker, injecté par
    `build_tool_executors`. L'ouvrier sait déjà ce qu'il cherche — le lui redemander à chaque appel
    ajouterait un argument qu'il peut oublier, sur un outil que le run C montre déjà sous-utilisé.
    """
    url = (args.get("url") or "").strip()
    if not url:
        return {"error": "fetch_url : argument 'url' vide."}
    try:
        result = await fetch_url(url, query=query, ticker_id=ticker_id)
    except ValueError as e:
        return {"error": str(e), "retryable": False}
    except Exception as e:  # noqa: BLE001
        logger.info("exec_fetch_url(%s) : %s", url[:120], e)
        return {"error": str(e), "retryable": True}

    if log is not None:
        # L'URL demandée ET l'URL finale : une redirection ne doit pas faire perdre la trace, et le
        # modèle citera parfois l'une, parfois l'autre.
        log.record(url, "full")
        log.record(result.get("final_url"), "full")
    return result


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


def build_tool_executors(
    *,
    ticker_id: Optional[str],
    query: Optional[str] = None,
    log: Optional[RetrievalLog] = None,
) -> dict[str, ToolExecutor]:
    """Table `nom d'outil → exécuteur` attendue par `run_tool_json_agent`. Les noms DOIVENT
    correspondre au `tools_json` de l'agent en DB (migration 025) — un outil déclaré sans exécuteur
    se traduit par « outil inconnu » côté modèle.

    `query` (le mandat), `log` (journal de récupération) et `ticker_id` (l'émetteur analysé) sont
    fermés dans les exécuteurs plutôt que passés en arguments d'outil : ce sont des faits du run, pas
    des décisions du modèle. `ticker_id` sert désormais à `web_search` et `fetch_url` autant qu'à
    `query_knowledge` — il décide quel domaine est celui de l'émetteur, donc quel `source_type_max`
    le modèle se voit annoncer (#31).
    """

    async def _fetch(args: dict[str, Any]) -> dict[str, Any]:
        return await exec_fetch_url(args, query=query, log=log, ticker_id=ticker_id)

    async def _search(args: dict[str, Any]) -> dict[str, Any]:
        return await exec_web_search(args, log=log, ticker_id=ticker_id)

    return {
        "web_search": _search,
        "fetch_url": _fetch,
        "query_knowledge": make_query_knowledge_executor(ticker_id),
    }
