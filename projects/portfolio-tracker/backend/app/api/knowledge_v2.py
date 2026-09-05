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
from app.knowledge.edgar_feed import EdgarFeedUnavailable, run_edgar_feed
from app.knowledge.financials_feed import FinancialsUnavailable, run_financials_feed
from app.knowledge.synthesis_feed import (
    SYNTHESIS_TARGETS,
    SynthesisUnavailable,
    SynthesisUngrounded,
    run_synthesis_feed,
)
from app.knowledge.staleness import balayage_peremption
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


class EdgarFeedBody(BaseModel):
    """Amorçage du socle EDGAR. Pas de `refresh` : le feed re-mesure toujours chez EDGAR et
    supersede le fait de même poste/exercice s'il existe (idempotent par construction)."""
    persist: bool = True


@router.post("/tickers/{ticker_id}/knowledge/edgar-refresh")
async def edgar_refresh(ticker_id: str, body: EdgarFeedBody):
    """Amorce le SOCLE EDGAR : 8 postes comptables bruts (CA, résultat net, marge brute, OCF,
    capitaux propres, total actif, capex, trésorerie/dette LT) mesurés chez EDGAR → entries
    `fact_financial` tier A.

    **À lancer AVANT `financials-refresh`** sur tout ticker au corpus vide : les ratios y sont
    DÉRIVÉS de ces faits, et le CIK du capex est relu depuis leur `source_url`. Sans ce socle, la
    dimension `financials` (plancher tier A) reste non fondable et le ticker ne peut jamais devenir
    `ready` — c'était le cas de tous les tickers sauf NVDA, dont le socle venait d'un seed manuel.

    Couverture partielle possible : un poste qu'EDGAR ne porte pas reste **absent** (listé dans
    `unfounded`), jamais estimé (#25).

    `EdgarFeedUnavailable` (ticker sans symbole, symbole absent du registre SEC, pas d'ancrage de
    bilan) → **422**."""
    try:
        result = await run_edgar_feed(ticker_id, persist=body.persist)
    except EdgarFeedUnavailable as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("edgar-refresh %s", ticker_id)
        raise HTTPException(status_code=502, detail=f"edgar-feed : {e}")
    return result


@router.post("/tickers/{ticker_id}/knowledge/financials-refresh")
async def financials_refresh(ticker_id: str, body: ValuationFeedBody):
    """Fonde `financials.{roic_pct, fcf_conversion_pct, intensite_capex_pct, levier}` en CALCULANT les
    ratios depuis les faits EDGAR déjà en base (tier A), en récupérant à la source le seul poste
    manquant — le capex (EDGAR `companyconcept`). Provenance EDGAR ⇒ tier A, condition du plancher.

    Le quant n'est PAS utilisé (tier B+ sous le plancher `financials`=A). Couverture partielle possible :
    si EDGAR est indisponible pour le capex, `fcf_conversion_pct`/`intensite_capex_pct` restent non
    fondés (listés dans `unfounded`) plutôt que fabriqués (#25). `refresh=True` re-tente le fetch capex.

    `FinancialsUnavailable` (ticker sans symbole / aucun fait EDGAR en base) → **422**."""
    try:
        result = await run_financials_feed(ticker_id, persist=body.persist, refresh=body.refresh)
    except FinancialsUnavailable as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("financials-refresh %s", ticker_id)
        raise HTTPException(status_code=502, detail=f"financials-feed : {e}")
    return result


class SynthesisBody(BaseModel):
    """Alimentation d'un champ qualitatif par SYNTHÈSE grounded des entries tier A/A-/B+ en base.

    Réservé aux champs que le fetch ne peut PAS fonder (économie unitaire, 5 forces) mais dont le
    matériau existe déjà, épars, dans le KB. `field_path` doit être une cible connue (voir
    `GET /knowledge/synthesis/targets`)."""
    field_path: str = Field(min_length=1)
    persist: bool = True             # False = dry-run (base append-only)
    max_candidates: int = Field(ge=1, le=50, default=20)
    debug_raw: bool = False          # True = renvoie la sortie LLM brute sans validation (diagnostic)


@router.get("/knowledge/synthesis/targets")
async def synthesis_targets():
    """Champs synthétisables (diagnostic) : lesquels, avec quelle dimension et combien de citations
    minimales requises."""
    return {
        "targets": [
            {"field_path": t.field_path, "dimension": t.dimension,
             "entry_type": t.entry_type, "min_citations": t.min_citations}
            for t in SYNTHESIS_TARGETS.values()
        ]
    }


@router.post("/tickers/{ticker_id}/knowledge/synthesize")
async def synthesize(ticker_id: str, body: SynthesisBody):
    """Fonde un champ qualitatif (ex. `produits.unit_economics`, `marche.structure_5forces`) par une
    synthèse GROUNDED : un tour LLM compose la synthèse STRICTEMENT à partir des entries tier A/A-/B+
    déjà en base ; le backend vérifie que chaque assertion cite une entry du corpus (grounding réel,
    #24/#28), dérive le tier « un cran sous la plus faible entry citée » et écrit une entry
    `source_type='agent_synthesis'`, `requires_human_review=True`.

    Jamais un fait fabriqué pour forcer `ready` (G3) : matériau citable insuffisant → **422**
    (`SynthesisUnavailable`) ; synthèse qui sort du corpus → **422** (`SynthesisUngrounded`, rien
    n'est écrit). `persist=false` = dry-run.
    """
    try:
        result = await run_synthesis_feed(
            ticker_id, body.field_path, persist=body.persist,
            max_candidates=body.max_candidates, debug_raw=body.debug_raw,
        )
    except (SynthesisUnavailable, SynthesisUngrounded) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except AgentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("synthesize %s/%s", ticker_id, body.field_path)
        raise HTTPException(status_code=502, detail=f"synthesis-feed : {e}")
    return result


# ── Lecture de la base de connaissance ───────────────────────────────────────

# Colonnes retournées par les deux routes de lecture — embedding (vector(1024)) est
# délibérément ABSENT : illisible et lourd (1024 floats par entrée).
_ENTRY_COLUMNS = (
    "id", "ticker_id", "document_id", "entry_type", "title", "content",
    "content_structured", "tags", "lang", "source_type", "source_url", "source_date",
    "fiscal_period", "reliability_score", "reliability_tier", "reliability_note",
    "has_conflict", "conflict_entry_id", "requires_human_review", "reviewed_by_user",
    "last_reviewed_at", "model_cutoff", "version", "valid_from", "superseded_by",
    "question_status", "question_priority", "resolves_entry_id",
    "is_outdated", "is_deleted", "created_at", "updated_at", "covers",
)
_ENTRY_SELECT = ", ".join(_ENTRY_COLUMNS)

# Tiers valides (même domaine que le CHECK de la migration 024).
_ALL_TIERS = ("A", "A-", "B+", "B", "B-", "C+", "C")


def _build_entries_query(
    ticker_id: str,
    entry_type: Optional[str],
    reliability_tier: Optional[str],
    covers: Optional[str],
    include_inactive: bool,
    limit: int,
    offset: int,
) -> tuple[str, str, str, list]:
    """Construit la requête de listing sans f-string contenant des accolades littérales.

    Les fragments sont concaténés ; les paramètres sont positionnels ($1, $2…).
    Pas de commentaire SQL avec accolades ici — cf. convention #39 / check_fstring_sql.
    """
    conditions = ["ke.ticker_id = $1"]
    params: list = [ticker_id]

    if not include_inactive:
        conditions.append("ke.is_deleted = false")
        conditions.append("ke.superseded_by IS NULL")

    # idx = nombre de paramètres déjà dans params ; incrémenté AVANT chaque ajout.
    idx = 1  # $1 = ticker_id

    if entry_type is not None:
        idx += 1
        conditions.append("ke.entry_type = $" + str(idx))
        params.append(entry_type)

    if reliability_tier is not None:
        idx += 1
        conditions.append("ke.reliability_tier = $" + str(idx))
        params.append(reliability_tier)

    if covers is not None:
        idx += 1
        conditions.append("$" + str(idx) + " = ANY(ke.covers)")
        params.append(covers)

    where = " AND ".join(conditions)

    idx_limit = idx + 1
    idx_offset = idx + 2
    params.append(limit)
    params.append(offset)

    # Compteurs agrégés par tier — calculés en une passe sur les lignes filtrées.
    # Pas de f-string ici : les fragments sont concaténés ou construits par jointure.
    tier_subquery = (
        "SELECT jsonb_build_object("
        + ", ".join(
            "'" + t + "', "
            + "COUNT(*) FILTER (WHERE reliability_tier = '" + t + "')"
            for t in _ALL_TIERS
        )
        + ") AS par_tier FROM knowledge_entries ke WHERE " + where
    )

    sql_count = "SELECT COUNT(*) AS total FROM knowledge_entries ke WHERE " + where

    sql_page = (
        "SELECT " + _ENTRY_SELECT
        + " FROM knowledge_entries ke WHERE " + where
        + " ORDER BY ke.id DESC"
        + " LIMIT $" + str(idx_limit) + " OFFSET $" + str(idx_offset)
    )

    return sql_count, sql_page, tier_subquery, params


@router.get("/tickers/{ticker_id}/knowledge/entries")
async def list_knowledge_entries(
    ticker_id: str,
    entry_type: Optional[str] = None,
    reliability_tier: Optional[str] = None,
    covers: Optional[str] = None,
    include_inactive: bool = False,
    limit: int = 50,
    offset: int = 0,
):
    """Liste les entries de connaissance d'un ticker avec filtres et compteurs agrégés.

    Par défaut n'expose PAS les entries supprimées (`is_deleted=true`) ni les versions
    supersédées (`superseded_by IS NOT NULL`) — la table est append-only versionnée,
    les versions mortes doubleraient la taille du corpus sans apporter d'information utile.

    Filtres :
    - `entry_type` : type d'entry (ex. `fact_financial`, `fact_qualitative`, `agent_synthesis`…).
    - `reliability_tier` : tier exact (A, A-, B+, B, B-, C+, C).
    - `covers` : chemin MVDD exact (ex. `financials.roic_pct`) — filtre via l'index GIN.
    - `include_inactive` : si true, renvoie AUSSI les entries supprimées (`is_deleted`)
      et les versions supersédées. Le nom couvre les deux : ce sont les deux façons
      qu'a une entry d'être hors du corpus vivant.
    - `limit` / `offset` : pagination (défaut 50/0).

    La colonne `embedding` (vector 1024) n'est jamais renvoyée.

    Réponse :
    - `total` : nombre total de lignes correspondant aux filtres (avant pagination).
    - `par_tier` : dict clefé par le tier TEL QU'IL EST STOCKÉ (`"A"`, `"A-"`, `"B+"`,
      `"B"`, `"B-"`, `"C+"`, `"C"`) — pas de nom maquillé, le frontend n'a aucune
      table de correspondance à tenir.
    - `entries` : liste paginée.
    """
    if reliability_tier is not None and reliability_tier not in _ALL_TIERS:
        raise HTTPException(status_code=422, detail="reliability_tier invalide.")
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=422, detail="limit doit être entre 1 et 200.")
    if offset < 0:
        raise HTTPException(status_code=422, detail="offset ne peut pas être négatif.")

    sql_count, sql_page, sql_tier, params = _build_entries_query(
        ticker_id, entry_type, reliability_tier, covers, include_inactive, limit, offset,
    )

    # params contient [ticker_id, ...filtres..., limit, offset]
    # Pour sql_count et sql_tier, on n'a pas besoin de limit/offset (les 2 derniers params).
    params_filter = params[:-2]

    async with get_db_session() as conn:
        total_row = await conn.fetchrow(sql_count, *params_filter)
        total = total_row["total"]

        tier_row = await conn.fetchrow(sql_tier, *params_filter)
        par_tier = dict(tier_row["par_tier"]) if tier_row and tier_row["par_tier"] else {}

        rows = await conn.fetch(sql_page, *params)

    return {
        "total": total,
        "par_tier": par_tier,
        "entries": [dict(r) for r in rows],
    }


@router.get("/tickers/{ticker_id}/knowledge/staleness")
async def knowledge_staleness(ticker_id: str):
    """Balayage de péremption : entries actives ANTÉRIEURES au dernier événement matériel (8-K/6-K).

    **En lecture seule, à dessein.** Décider qu'un fait est remplacé est un jugement sémantique :
    la route propose une liste à re-vérifier, elle n'écrit jamais `superseded_by` (cf. #29 et
    `feedback_optional_schema_gate` — ne pas donner à une heuristique de dates une voix sur ce que
    le corpus affirme).

    ⚠️ **Toujours 200, jamais 503 sur flux injoignable** : le rapport rend alors
    `statut='indeterminable'` avec son avertissement. Un 503 ferait disparaître le rapport, donc
    lire comme « rien à signaler » depuis l'appelant — la panne exacte qu'on ferme ici.
    """
    async with get_db_session() as conn:
        return await balayage_peremption(conn, ticker_id)


@router.get("/knowledge/entries/{entry_id}")
async def get_knowledge_entry(entry_id: int):
    """Détail d'une entry de connaissance.

    La colonne `embedding` (vector 1024) n'est jamais renvoyée.
    Renvoie 404 si l'entry est introuvable (quelle que soit sa valeur `is_deleted`).
    """
    sql = "SELECT " + _ENTRY_SELECT + " FROM knowledge_entries ke WHERE ke.id = $1"
    async with get_db_session() as conn:
        row = await conn.fetchrow(sql, entry_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Entry introuvable.")
    return dict(row)
