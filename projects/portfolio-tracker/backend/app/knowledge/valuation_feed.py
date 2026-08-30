"""
Alimentateur `valorisation` (V2, sprint 1) — fonde `prix_actuel` et `relatif_multiple` depuis le quant.

Motif (00-REPRISE §3) : la dimension MVDD `valorisation` exige trois champs — `prix_actuel`,
`relatif_multiple`, `base_rate_anchor`. Les deux premiers sont des **données de marché** que la
recherche web ne peut pas fonder honnêtement ; ils viennent du DataService (yfinance `.info`). Le
troisième, `base_rate_anchor`, est une **ancre de taux de base** (outside view) — PAS une donnée de
marché — et relève d'un corpus de fréquences empiriques (sprint 2), pas de cet alimentateur.

Principe (mêmes garde-fous que le search-worker, conventions #24/#25) :
  • Le `source_type` est **connu et mesuré** ici, pas déclaré par un modèle : prix, capitalisation,
    valeur d'entreprise et multiples proviennent tous de yfinance `.info` → `source_type='yfinance'`
    (tier B+ 0.75 = pile le plancher de `valorisation`). Le score est recalculé par `store_knowledge`.
  • Un ticker **sans symbole de marché** (privé, `PUB-`/`PRIV-`) ne peut PAS être fondé par le quant →
    `ValuationUnavailable` (jamais une entrée vide qui ferait croire à une couverture, cf. #25).
  • Append-only (A1) : la valorisation est **volatile** ; chaque passe **supersede** l'entrée courante
    du même champ (`supersedes_entry_id`) pour que la KB n'expose que le prix le plus récent.

La transformation `build_valuation_entries()` est **pure** (m1 dict → specs), donc vérifiable
hors-ligne sans réseau ni DB (`backend/checks/check_valuation_feed.py`). L'IO vit dans
`run_valuation_feed()`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from app.config import settings
from app.data_collection.data_service import DataService
from app.db.database import get_db_session
from app.knowledge.service import store_knowledge

logger = logging.getLogger(__name__)

# prix, market cap, EV et TOUS les multiples viennent de yfinance `.info` (cf. m1_quantitative.py).
# yfinance = tier B+ 0.75 dans RELIABILITY_TABLE = plancher exact de la dimension valorisation.
_SOURCE_TYPE = "yfinance"


class ValuationUnavailable(Exception):
    """Le quant ne peut pas fonder la valorisation (ticker sans symbole, ou données de marché
    absentes). Distinct d'un résultat vide : l'appelant DOIT le remonter, pas l'avaler (#25)."""


@dataclass
class ValuationEntrySpec:
    """Une entrée `knowledge_entries` prête à écrire, indépendante de la DB (testable hors-ligne)."""
    field: str            # 'prix_actuel' | 'relatif_multiple' — sert au ciblage supersede + tags
    entry_type: str
    title: str
    content: str
    content_structured: dict[str, Any]
    tags: list[str] = field(default_factory=list)
    source_type: str = _SOURCE_TYPE


def _num(v: Any, *, suffix: str = "", nd: int = 2) -> str:
    """Formatage FR tolérant au None (les multiples manquent parfois : KO n'a pas de FCF yield)."""
    if v is None:
        return "n/d"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if abs(f) >= 1e9:
        return f"{f/1e9:.1f} Md{('' if not suffix else ' ' + suffix)}".replace(".", ",")
    return f"{f:.{nd}f}{suffix}".replace(".", ",")


def build_valuation_entries(
    ticker_id: str, symbol: str, m1: dict[str, Any], *, as_of: date
) -> list[ValuationEntrySpec]:
    """m1 (sortie DataService.get_m1) → specs `prix_actuel` + `relatif_multiple`. Pur, sans IO.

    Lève `ValuationUnavailable` si le prix de marché manque (crumb yfinance corrompu, symbole mort) :
    fonder `prix_actuel` sur un prix absent creuserait un faux trou plutôt qu'un vrai.
    """
    price = m1.get("price") or {}
    val = m1.get("valuation") or {}
    currency = price.get("currency") or "USD"

    current_price = price.get("current_price")
    if current_price is None:
        raise ValuationUnavailable(
            f"{ticker_id} ({symbol}) : prix de marché absent de m1 — valorisation non fondable"
        )

    iso = as_of.isoformat()

    # ── prix_actuel ───────────────────────────────────────────────────────────
    prix_struct = {
        "metric": "prix_actuel",
        "current_price": current_price,
        "currency": currency,
        "market_cap": price.get("market_cap"),
        "enterprise_value": price.get("enterprise_value"),
        "distance_from_52w_high_pct": price.get("distance_from_52w_high_pct"),
        "as_of": iso,
        "symbol": symbol,
    }
    prix_content = (
        f"Prix de marché de {ticker_id} ({symbol}) au {iso} : {_num(current_price)} {currency}. "
        f"Capitalisation {_num(price.get('market_cap'))} {currency}, "
        f"valeur d'entreprise {_num(price.get('enterprise_value'))} {currency}"
    )
    if price.get("distance_from_52w_high_pct") is not None:
        prix_content += f", {_num(price.get('distance_from_52w_high_pct'), suffix=' %')} sous le plus haut 52 semaines"
    prix_content += ". Source : yfinance (données de marché, à rafraîchir avant toute décision)."

    prix = ValuationEntrySpec(
        field="prix_actuel",
        entry_type="fact_financial",
        title=f"Valorisation — prix de marché actuel ({symbol})",
        content=prix_content,
        content_structured=prix_struct,
        tags=["valorisation", "prix_actuel", "market_data", "quant"],
    )

    # ── relatif_multiple ──────────────────────────────────────────────────────
    mult_struct = {
        "metric": "relatif_multiple",
        "pe_ttm": val.get("pe_ttm"),
        "pe_ntm": val.get("pe_ntm"),
        "ev_ebitda": val.get("ev_ebitda"),
        "ev_revenue": val.get("ev_revenue"),
        "price_to_book": val.get("price_to_book"),
        "fcf_yield_pct": val.get("fcf_yield_pct"),
        "as_of": iso,
        "symbol": symbol,
    }
    mult_content = (
        f"Multiples de valorisation de {ticker_id} ({symbol}) au {iso} : "
        f"P/E TTM {_num(val.get('pe_ttm'), suffix='×')}, "
        f"P/E forward {_num(val.get('pe_ntm'), suffix='×')}, "
        f"EV/EBITDA {_num(val.get('ev_ebitda'), suffix='×')}, "
        f"EV/CA {_num(val.get('ev_revenue'), suffix='×')}, "
        f"P/B {_num(val.get('price_to_book'), suffix='×')}, "
        f"rendement FCF {_num(val.get('fcf_yield_pct'), suffix=' %')}. "
        f"Ce sont les multiples ACTUELS (le champ `relatif_multiple`) ; l'ancre de comparaison "
        f"historique/sectorielle (`base_rate_anchor`) relève d'un corpus de base rates distinct. "
        f"Source : yfinance."
    )
    mult = ValuationEntrySpec(
        field="relatif_multiple",
        entry_type="fact_financial",
        title=f"Valorisation — multiples relatifs ({symbol})",
        content=mult_content,
        content_structured=mult_struct,
        tags=["valorisation", "relatif_multiple", "market_data", "quant"],
    )

    return [prix, mult]


async def _current_field_entry_id(conn, ticker_id: str, field_tag: str) -> Optional[int]:
    """Id de l'entrée COURANTE du même champ de valorisation (à superseder). Ciblée par tags —
    le feed est le seul producteur de ces tags, donc pas de collision avec une entrée EDGAR/recherche."""
    row = await conn.fetchrow(
        """
        SELECT id FROM knowledge_entries
        WHERE ticker_id = $1 AND superseded_by IS NULL AND is_deleted = FALSE
          AND tags @> $2
        ORDER BY id DESC LIMIT 1
        """,
        ticker_id, ["valorisation", field_tag],
    )
    return row["id"] if row else None


async def run_valuation_feed(
    ticker_id: str, *, persist: bool = True, refresh: bool = False
) -> dict[str, Any]:
    """Alimente `valorisation.{prix_actuel,relatif_multiple}` pour un ticker depuis le quant.

    `refresh=True` force un fetch yfinance/FMP (sinon cache 4h de get_m1). `persist=False` = dry-run
    (la base est append-only : on regarde avant d'écrire, comme le search-worker).
    """
    async with get_db_session() as conn:
        row = await conn.fetchrow(
            "SELECT ticker_symbol, company_type FROM tickers WHERE id = $1", ticker_id
        )
    if row is None:
        raise ValuationUnavailable(f"ticker inconnu : {ticker_id}")
    if (row["company_type"] or "") == "private" or not row["ticker_symbol"]:
        raise ValuationUnavailable(
            f"{ticker_id} : pas de symbole de marché (privé/PUB-/PRIV-) — DataService ignoré (#11), "
            f"valorisation à fonder par documents uploadés, pas par le quant"
        )
    symbol = row["ticker_symbol"]

    svc = DataService()
    m1 = (
        await svc.refresh_m1(symbol, settings.FMP_API_KEY, context="valuation_feed")
        if refresh
        else await svc.get_m1(symbol, settings.FMP_API_KEY)
    )

    as_of = date.today()
    specs = build_valuation_entries(ticker_id, symbol, m1, as_of=as_of)

    created: list[dict[str, Any]] = []
    if persist:
        async with get_db_session() as conn:
            async with conn.transaction():
                for spec in specs:
                    prev_id = await _current_field_entry_id(conn, ticker_id, spec.field)
                    stored = await store_knowledge(
                        conn,
                        ticker_id=ticker_id,
                        entry_type=spec.entry_type,
                        content=spec.content,
                        source_type=spec.source_type,
                        title=spec.title,
                        content_structured=spec.content_structured,
                        tags=spec.tags,
                        lang="fr",
                        source_date=as_of,
                        supersedes_entry_id=prev_id,
                        covers=[f"valorisation.{spec.field}"],   # index 029 : chemin complet
                    )
                    created.append(dict(stored) | {"field": spec.field, "supersedes": prev_id})
        logger.info(
            "valuation_feed %s (%s) → %d entrée(s) [%s]", ticker_id, symbol, len(created),
            ", ".join(f"{c['field']}#{c['id']}" for c in created),
        )

    return {
        "ticker_id": ticker_id,
        "symbol": symbol,
        "as_of": as_of.isoformat(),
        "source_type": _SOURCE_TYPE,
        "entries": [
            {
                "field": s.field,
                "title": s.title,
                "content": s.content,
                "content_structured": s.content_structured,
                "tags": s.tags,
                "source_type": s.source_type,
            }
            for s in specs
        ],
        "persisted": created,
        "dry_run": not persist,
    }
