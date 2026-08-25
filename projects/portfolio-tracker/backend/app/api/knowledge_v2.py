"""
API V2 — alimentation de la base de connaissance (amont de la chaîne d'analyse).

Expose le `search-worker` (contrat C1) : une requête structurée entre, des `knowledge_entries`
scorées en sortent. C'est le levier qui fait passer un ticker de `thin_qualitative` à `ready` — la
couverture qualitative manquante ne peut venir que de là.

Erreurs : `SearchUnavailable` → **503** (backend de recherche non configuré ou en panne — distinct
d'une recherche infructueuse, qui est un 200 avec `status='not_found'`) ; `AgentNotFoundError` → 404 ;
validation de contrat → 502.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents.providers import AgentNotFoundError
from app.agents.v2.worker import persist_worker_entries, run_search_worker
from app.contracts import OutputSchema, WorkerRequest
from app.contracts.worker_delegation_schema import EntryType, Requester
from app.db.database import get_db_session
from app.knowledge.base_rate_corpus import BaseRateUnavailable, run_base_rate_anchor
from app.knowledge.valuation_feed import ValuationUnavailable, run_valuation_feed
from app.knowledge.websearch import SearchUnavailable, get_search_backend
from app.config import settings

router = APIRouter(tags=["knowledge-v2"])
logger = logging.getLogger(__name__)


@router.get("/knowledge/search/status")
async def search_status():
    """Diagnostic : la recherche web est-elle réellement câblée ? À vérifier AVANT d'imputer un
    manque de couverture à l'absence de sources."""
    try:
        backend = get_search_backend()
        return {"configured": True, "provider": backend.name}
    except SearchUnavailable as e:
        return {"configured": False, "provider": settings.SEARCH_PROVIDER, "reason": str(e)}


class SearchWorkerBody(BaseModel):
    """Forme HTTP d'une `WorkerRequest` (le ticker vient du chemin)."""
    requester: Requester = "knowledge-curator"
    query: str = Field(min_length=1)
    entry_type: EntryType = "fact_qualitative"
    dimension: Optional[str] = None
    field_path: Optional[str] = None
    fiscal_period: Optional[str] = None
    reliability_min: float = Field(ge=0, le=1, default=0.60)
    max_entries: int = Field(ge=1, le=50, default=5)
    divergent: bool = False
    check_existing_first: bool = True
    persist: bool = True   # False = dry-run : on voit ce qui entrerait sans l'écrire
    # Plafond de tours d'outils. Exposé parce qu'il est réellement contraignant : le premier run réel
    # (NVDA, 2026-08-23) est sorti sur « 6 itérations épuisées » avant d'avoir convergé. Le relever
    # coûte des tokens à chaque tour — à régler par mesure, pas par générosité de défaut.
    max_iterations: int = Field(ge=1, le=12, default=6)


@router.post("/tickers/{ticker_id}/knowledge/search")
async def run_worker(ticker_id: str, body: SearchWorkerBody):
    """Délègue une recherche au `search-worker` et (par défaut) persiste les entries retenues.

    Le `dry-run` (`persist=false`) existe parce que la base est **append-only** (A1) : une entrée
    écrite ne se retire pas, elle se supersede. Mieux vaut regarder avant d'écrire.
    """
    req = WorkerRequest(
        requester=body.requester,
        worker="search-worker",
        ticker_id=ticker_id,
        query=body.query,
        output_schema=OutputSchema(
            entry_type=body.entry_type,
            dimension=body.dimension,
            field_path=body.field_path,
            fiscal_period=body.fiscal_period,
        ),
        reliability_min=body.reliability_min,
        max_entries=body.max_entries,
        divergent=body.divergent,
        check_existing_first=body.check_existing_first,
    )

    try:
        exchange = await run_search_worker(req, max_iterations=body.max_iterations)
    except SearchUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except AgentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("search-worker %s", ticker_id)
        raise HTTPException(status_code=502, detail=f"search-worker : {e}")

    created: list[dict] = []
    if body.persist and exchange.response.entries:
        async with get_db_session() as conn:
            async with conn.transaction():
                created = await persist_worker_entries(conn, exchange)

    return {
        "request": exchange.request.model_dump(mode="json"),
        "response": exchange.response.model_dump(mode="json"),
        "persisted": created,
        "dry_run": not body.persist,
    }


class ValuationFeedBody(BaseModel):
    """Alimentation `valorisation` depuis le quant (yfinance/FMP), pas la recherche web."""
    persist: bool = True    # False = dry-run (base append-only)
    refresh: bool = False   # True = force un fetch yfinance/FMP (sinon cache 4h de get_m1)


@router.post("/tickers/{ticker_id}/knowledge/valuation-refresh")
async def valuation_refresh(ticker_id: str, body: ValuationFeedBody):
    """Fonde `valorisation.prix_actuel` + `valorisation.relatif_multiple` depuis le DataService.

    Ce que la recherche web ne peut pas fonder honnêtement (données de marché) est alimenté ici de
    façon déterministe. `base_rate_anchor` (le 3ᵉ champ) N'est PAS produit ici — c'est une ancre de
    base rate (corpus, sprint 2), pas une donnée de marché.

    `ValuationUnavailable` (ticker sans symbole de marché / données absentes) → **422**, distinct
    d'un succès à couverture partielle.
    """
    try:
        result = await run_valuation_feed(ticker_id, persist=body.persist, refresh=body.refresh)
    except ValuationUnavailable as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("valuation-refresh %s", ticker_id)
        raise HTTPException(status_code=502, detail=f"valuation-feed : {e}")
    return result


@router.post("/tickers/{ticker_id}/knowledge/base-rate-anchor")
async def base_rate_anchor(ticker_id: str, body: ValuationFeedBody):
    """Fonde `valorisation.base_rate_anchor` : classe de référence (quant) → base rate (corpus Base
    Rate Book) → entry par-ticker. Seede le corpus transverse au passage (idempotent).

    `BaseRateUnavailable` (ticker non coté / classe indéterminable) → **422**."""
    try:
        result = await run_base_rate_anchor(ticker_id, persist=body.persist, refresh=body.refresh)
    except BaseRateUnavailable as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("base-rate-anchor %s", ticker_id)
        raise HTTPException(status_code=502, detail=f"base-rate-anchor : {e}")
    return result
