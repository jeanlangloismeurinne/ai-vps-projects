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
from app.knowledge.datation import constatee
from app.knowledge.service import ENTRIES_COURANTES, store_knowledge

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


# ─────────────────────────────────────────────────────────────────────────────
# Multiples : nom lisible + dénominateur, pour DIRE pourquoi un multiple n'est pas calculable.
# Un multiple est un rapport prix/résultat : son dénominateur doit être strictement positif. Un
# « multiple » négatif ne mesure aucun niveau de valorisation — il signale une PERTE, et son
# classement n'est même pas monotone (une perte deux fois plus lourde rapproche le P/E de zéro par
# le bas, donc le fait paraître « moins cher »). Trouvé sur RVMD, biotech clinique : yfinance rend
# `pe_ntm=-35,95×` et `ev_ebitda=-26,23×`, publiés tels quels dans le corpus lu par les agents.
# Même famille que F1 (`fcf_conversion_pct=+80,77 %` calculé sur deux négatifs) : un ratio flatteur
# né d'une mauvaise nouvelle. Cf. conventions #25 (on n'estime pas) et #42 (on le déclare EN TOUTES
# LETTRES dans le contenu, qui est ce que l'agent lit).
_MULTIPLES: dict[str, tuple[str, str]] = {
    "pe_ttm": ("P/E TTM", "bénéfice net des 12 derniers mois"),
    "pe_ntm": ("P/E forward", "bénéfice net attendu"),
    "ev_ebitda": ("EV/EBITDA", "EBITDA"),
    "ev_revenue": ("EV/CA", "chiffre d'affaires (ou la valeur d'entreprise)"),
    "price_to_book": ("P/B", "capitaux propres comptables"),
}


def _trier_multiples(val: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    """Sépare les multiples en trois états DISTINCTS — jamais deux confondus (cf. F3, `_absents()`).

    Rend `(calcules, non_calculables, absents)` :
      • `calcules`        — dénominateur positif, le multiple est un niveau de valorisation ;
      • `non_calculables` — valeur ≤ 0 : {clef: motif}. La valeur est ÉCARTÉE, pas corrigée ;
      • `absents`         — yfinance ne rend rien (clefs, pour les nommer sans les inventer).

    Confondre « non calculable » et « absent » est le défaut à éviter : le premier est un FAIT sur
    l'émetteur (il perd de l'argent), le second un trou de donnée. Les rendre tous deux en `n/d`
    ferait lire une propriété de l'entreprise comme une lacune de la collecte.
    """
    calcules: dict[str, Any] = {}
    non_calculables: dict[str, str] = {}
    absents: list[str] = []
    for key, (nom, denominateur) in _MULTIPLES.items():
        raw = val.get(key)
        if raw is None:
            absents.append(key)
            continue
        try:
            f = float(raw)
        except (TypeError, ValueError):
            absents.append(key)
            continue
        if f <= 0:
            non_calculables[key] = f"{denominateur} négatif ou nul"
        else:
            calcules[key] = raw
    return calcules, non_calculables, absents


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


def _date_du_fait(m1: dict[str, Any]) -> Optional[date]:
    """DÉTENTEUR UNIQUE (#46) de « à quelle date le marché a-t-il produit ce relevé ? ».

    Deux horodatages remontent du quant, et ils ne disent PAS la même chose :
      · `price_as_of`      — la dernière cotation régulière, celle de `current_price` ;
      · `last_close_date`  — la dernière séance dont la clôture est exploitable, celle sur
                             laquelle reposent les variations 1m/3m/6m/1an/YTD.
    Le relevé est fondé d'abord sur le prix, donc `price_as_of` prime ; `last_close_date` est le
    repli quand le fournisseur n'horodate pas sa cotation.

    Pourquoi ce n'est pas `date.today()` : mesuré le 2026-09-23, le « prix actuel » de MSFT était
    la clôture du 22/09. Dater du jour, c'est faire battre un relevé simplement rafraîchi contre
    un fait réellement plus récent — le défaut que #79 corrige.
    """
    price = m1.get("price") or {}
    for clef in ("price_as_of", "last_close_date"):
        brut = price.get(clef)
        if not brut:
            continue
        try:
            return date.fromisoformat(str(brut)[:10])
        except ValueError:
            logger.warning("valuation_feed : `%s` illisible (%r) — ignoré", clef, brut)
    return None


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
    calcules, non_calculables, absents = _trier_multiples(val)
    # `fcf_yield_pct` n'est PAS un multiple mais un RENDEMENT (FCF / capitalisation) : négatif, il
    # reste monotone et parfaitement interprétable — c'est la consommation de trésorerie rapportée à
    # la capitalisation. Il traverse donc le tri sans être écarté. Ne pas uniformiser la règle « ≤ 0
    # = non calculable » : appliquée ici, elle supprimerait une information vraie.
    fcf_yield = val.get("fcf_yield_pct")

    mult_struct: dict[str, Any] = {
        "metric": "relatif_multiple",
        # Les clefs restent TOUTES présentes : un consommateur qui lit `pe_ntm` doit trouver `None`
        # (non calculable), pas une clef absente qui se lirait comme un oubli du producteur.
        **{k: calcules.get(k) for k in _MULTIPLES},
        "fcf_yield_pct": fcf_yield,
        "multiples_calculables": len(calcules),
        "multiples_non_calculables": non_calculables,   # {clef: motif} — jamais un simple None muet
        "multiples_absents": absents,
        "as_of": iso,
        "symbol": symbol,
    }

    if calcules:
        listing = ", ".join(
            f"{_MULTIPLES[k][0]} {_num(v, suffix='×')}" for k, v in calcules.items()
        )
        mult_content = f"Multiples de valorisation de {ticker_id} ({symbol}) au {iso} : {listing}. "
    else:
        mult_content = (
            f"Valorisation de {ticker_id} ({symbol}) au {iso} : AUCUN multiple de résultat n'est "
            f"calculable. "
        )
    if fcf_yield is not None:
        sens = " (négatif = consommation de trésorerie)" if float(fcf_yield) < 0 else ""
        mult_content += f"Rendement FCF {_num(fcf_yield, suffix=' %')}{sens}. "
    if non_calculables:
        detail = ", ".join(f"{_MULTIPLES[k][0]} ({motif})" for k, motif in non_calculables.items())
        mult_content += (
            f"NON CALCULABLES — {detail}. Un multiple négatif n'est pas un niveau de valorisation : "
            f"il signale une perte, et son classement n'est pas monotone (une perte plus lourde "
            f"rapproche le ratio de zéro par le bas, donc le fait paraître « moins cher »). Ces "
            f"multiples sont donc ÉCARTÉS, jamais publiés tels quels. "
        )
    if absents:
        mult_content += (
            f"ABSENTS des données de marché (à distinguer des précédents : lacune de collecte, pas "
            f"propriété de l'émetteur) — {', '.join(_MULTIPLES[k][0] for k in absents)}. "
        )
    mult_content += (
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
        f"""
        SELECT id FROM knowledge_entries
        WHERE ticker_id = $1 AND {ENTRIES_COURANTES}
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

    # La date du FAIT est celle que le MARCHÉ a produite, jamais l'horloge du serveur (#79).
    # Mesuré le 2026-09-23 sur MSFT : `current_price` valait 498,00 avec `regularMarketTime` au
    # 22/09 20:00 UTC — la clôture de la VEILLE. Le relevé se datait pourtant du jour, ce qui est
    # exactement le défaut que le lot #79 corrige, vivant ici dans le flux de prix.
    # Repli sur aujourd'hui si le fournisseur n'horodate rien : mieux vaut une date trop récente,
    # visible et bornée, qu'une pièce sans date de tri (`indatable` se perdrait au classement).
    as_of = _date_du_fait(m1) or date.today()
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
                        # Un relevé de marché est constaté le jour où le MARCHÉ l'a produit ; le
                        # « document » est la lecture qu'on en fait aujourd'hui. On croyait ces
                        # deux dates confondues : mesuré, elles ne le sont pas — le 2026-09-23 à
                        # 09 h UTC, le dernier cours coté datait du 22/09. Les confondre, c'était
                        # le cas #296 (un fait antérieur reporté sous la date de son classement),
                        # et c'est ce qui faisait battre un vieux relevé rafraîchi contre un fait
                        # récent au tri du dossier.
                        datation=constatee(date_du_fait=as_of, date_du_document=date.today()),
                        supersedes_entry_id=prev_id,
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
