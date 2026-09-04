"""
Corpus de base rates + ancre `valorisation.base_rate_anchor` (V2, sprint 2).

Le 3ᵉ champ de la dimension `valorisation` — `base_rate_anchor` — n'est PAS une donnée de marché
(sprint 1) mais une **ancre de taux de base** (outside view, Kahneman/Mauboussin) : la fréquence,
sur une classe de référence, de la trajectoire de croissance que le prix suppose. Une base rate ne se
*génère* pas au LLM (le groundedness-checker la flaggerait `base_rate_fabrique`) — elle se *mesure* sur
des données. On la **cherche dans un corpus empirique**, ici seedé depuis :

    The Base Rate Book (M. Mauboussin, D. Callahan, D. Majd — Credit Suisse / HOLT, sept. 2016),
    Exhibit 2 : distribution des CAGR de ventes des ~1000 premières capitalisations mondiales,
    1950-2015, sociétés mortes incluses (n=53 266 sur l'horizon 3 ans).

Architecture (parallèle au search-worker / valuation_feed) :
  • un **corpus transverse** (`ticker_id IS NULL`, `entry_type='base_rate'`) porte la distribution
    empirique — seedé une fois, réutilisable par TOUS les tickers (tiré par `include_sector=True`) ;
  • un **classifieur déterministe** range un ticker dans sa classe de référence depuis le quant
    (taille en CA, la maille du livre) — aucun LLM ;
  • un **écrivain par-ticker** émet une entry `base_rate` qui fonde `valorisation.base_rate_anchor`
    pour CE ticker, en citant le corpus.

Le `taux_base_pct` final pour la croissance *précise* impliquée par le prix est recalculé à l'analyse
(`run_research` lira `reverse_dcf.croissance_implicite_prix_actuel_pct` et appellera `base_rate_ge`).
L'entry de readiness porte des seuils représentatifs (≥15/20/25 %/an) + la distribution complète.

⚠️ Honnêteté des données : je ne dispose des chiffres EXACTS que pour l'**univers complet** (Exhibit 2).
Le livre montre que la **taille écrase** la persistance (Exhibit 4 ; ex. Tesla, décile CA 4,5-7 Md$ :
>45 %/an sur 10 ans ≈ 0 société). Pour une méga-cap, le `taux_base_pct` de l'univers complet est donc
une **borne haute** explicitement notée comme telle — jamais une distribution méga-cap inventée.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from app.config import settings
from app.data_collection.data_service import DataService
from app.db.database import get_db_session
from app.knowledge.service import store_knowledge
from app.knowledge.units import montant

logger = logging.getLogger(__name__)

BASE_RATE_BOOK = {
    "source": "The Base Rate Book — Mauboussin/Callahan/Majd, Credit Suisse HOLT, sept. 2016",
    "source_url": "https://sorfis.com/wp-content/uploads/2021/09/"
                  "The-Base-Rate-Book-Integrating-the-Past-to-Better-Anticipate-the-Future-September-2016.pdf",
    "sample": "top ~1000 capitalisations mondiales, 1950-2015, sociétés mortes incluses (n=53 266 à 3 ans)",
    "exhibit": "Exhibit 2 — Base Rates of Sales Growth",
}

# Exhibit 2 (chiffres EXACTS). Chaque tranche : borne basse du CAGR de ventes (%) → fréquence (%) par
# horizon. -100 encode la tranche ouverte « <(25) ». La somme de chaque colonne fait 100 %.
_H = ("1Y", "3Y", "5Y", "10Y")
SALES_GROWTH_DISTRIBUTION: list[tuple[float, dict[str, float]]] = [
    (-100, {"1Y": 1.9,  "3Y": 0.6,  "5Y": 0.3,  "10Y": 0.0}),
    (-25,  {"1Y": 1.0,  "3Y": 0.4,  "5Y": 0.3,  "10Y": 0.1}),
    (-20,  {"1Y": 1.7,  "3Y": 1.0,  "5Y": 0.7,  "10Y": 0.3}),
    (-15,  {"1Y": 3.2,  "3Y": 2.2,  "5Y": 1.6,  "10Y": 0.9}),
    (-10,  {"1Y": 6.2,  "3Y": 5.2,  "5Y": 4.2,  "10Y": 3.2}),
    (-5,   {"1Y": 12.2, "3Y": 13.2, "5Y": 12.9, "10Y": 12.4}),
    (0,    {"1Y": 20.6, "3Y": 25.2, "5Y": 28.8, "10Y": 34.2}),
    (5,    {"1Y": 17.8, "3Y": 21.3, "5Y": 24.2, "10Y": 28.3}),
    (10,   {"1Y": 11.4, "3Y": 12.3, "5Y": 12.6, "10Y": 11.6}),
    (15,   {"1Y": 6.8,  "3Y": 6.7,  "5Y": 6.0,  "10Y": 4.5}),
    (20,   {"1Y": 4.5,  "3Y": 3.9,  "5Y": 3.1,  "10Y": 2.0}),
    (25,   {"1Y": 2.9,  "3Y": 2.3,  "5Y": 1.9,  "10Y": 1.1}),
    (30,   {"1Y": 2.0,  "3Y": 1.5,  "5Y": 1.0,  "10Y": 0.6}),
    (35,   {"1Y": 1.3,  "3Y": 1.0,  "5Y": 0.7,  "10Y": 0.3}),
    (40,   {"1Y": 1.1,  "3Y": 0.7,  "5Y": 0.5,  "10Y": 0.2}),
    (45,   {"1Y": 5.5,  "3Y": 2.5,  "5Y": 1.3,  "10Y": 0.3}),
]
SALES_GROWTH_MEDIAN = {"1Y": 5.8, "3Y": 5.4, "5Y": 5.2, "10Y": 4.9}
SALES_GROWTH_MEAN = {"1Y": 14.8, "3Y": 8.1, "5Y": 6.9, "10Y": 5.8}

# Repère de taille du livre : la maille des base rates de ventes est le CA (décile), pas le secteur ;
# la tranche « méga » est CA > 50 Md$ (Exhibit 4). Buckets en USD.
# (borne basse, clef, préfixe de libellé, tranche). Le libellé est composé AVEC la maille réellement
# utilisée : quand le CA manque et qu'on retombe sur la capitalisation, écrire « (CA 10-50 Md$) »
# annoncerait une mesure qu'on n'a pas faite. Le rendu reste mot pour mot l'ancien sur la maille CA.
_SIZE_BUCKETS = [
    (50e9, "mega", "méga-cap", "> 50 Md$"),
    (10e9, "large", "large-cap", "10-50 Md$"),
    (1e9, "mid", "mid-cap", "1-10 Md$"),
    (0.0, "small", "small-cap", "< 1 Md$"),
]


# Seuils de croissance « représentatifs » portés par l'entry de readiness (l'implicite précis est
# recalculé à l'analyse depuis le reverse-DCF).
_REPRESENTATIVE_THRESHOLDS = (15.0, 20.0, 25.0)
_DEFAULT_HORIZON = "5Y"   # horizon LT de la thèse (ValorisationCote impose horizon_ans >= 5)


def _mds(v: Optional[float]) -> str:
    """Montant en dollars, format FR, unité choisie par l'ordre de grandeur (F9).

    La règle elle-même vit dans `knowledge/units.py` — elle était recopiée dans trois producteurs
    et F9 n'en avait corrigé qu'un (F10). Cette fonction n'est plus que la notation « $ » collée.
    """
    return montant(v, "$")


def _exercice(rc: dict[str, Any]) -> str:
    """« (FY2025) » — un CA est un FLUX, il se date (#42). Sans l'exercice, « 0 $ de ventes » n'est
    pas réfutable contre le fait EDGAR correspondant, et un chiffre périmé passe inaperçu (F11)."""
    fy = rc.get("sales_fiscal_year")
    return f" (FY{fy})" if fy else ""


class BaseRateUnavailable(Exception):
    """La classe de référence n'est pas déterminable (ni CA ni capitalisation) — on ne fonde pas
    `base_rate_anchor` sur une classe inventée."""


def base_rate_ge(threshold_pct: float, horizon: str = _DEFAULT_HORIZON) -> float:
    """P(CAGR de ventes ≥ `threshold_pct`) sur l'`horizon`, depuis l'univers complet (Exhibit 2).

    Convention conservatrice : on somme les tranches dont la **borne basse ≥ seuil** (on ne
    fractionne pas la tranche qui contient le seuil). Ex. seuil 20 % / 3 ans = 3,9+2,3+1,5+1,0+0,7+2,5
    = 11,9 %. Sert le calcul de l'ancre à l'analyse une fois l'implicite du reverse-DCF connu.
    """
    if horizon not in _H:
        raise ValueError(f"horizon inconnu : {horizon} (attendu {_H})")
    return round(sum(freq[horizon] for lo, freq in SALES_GROWTH_DISTRIBUTION if lo >= threshold_pct), 1)


def size_bucket(sales_usd: Optional[float], market_cap_usd: Optional[float]) -> tuple[str, str, str]:
    """(clé, libellé, base) — base = 'CA' si le chiffre d'affaires est connu, sinon 'capitalisation'
    (proxy explicite, noté dans l'ancre). Lève si aucun des deux n'est disponible."""
    basis = "CA"
    val = sales_usd
    if val is None:
        basis, val = "capitalisation", market_cap_usd
    if val is None:
        raise BaseRateUnavailable("ni chiffre d'affaires ni capitalisation — classe de référence indéterminable")
    for lo, key, prefixe, tranche in _SIZE_BUCKETS:
        if val >= lo:
            return key, f"{prefixe} ({basis} {tranche})", basis
    _, key, prefixe, tranche = _SIZE_BUCKETS[-1]
    return key, f"{prefixe} ({basis} {tranche})", basis


def _latest_revenue_usd(m1: dict[str, Any]) -> tuple[Optional[float], Optional[str]]:
    """(CA le plus récent, son exercice) depuis financials_3y. `(None, None)` si le CA est absent.

    ⚠️ **Un CA nul est une valeur, pas une absence** (F11, trouvé sur RVMD). Le test était
    `if rev:` — donc `0.0`, falsy, faisait passer à l'exercice précédent **en silence**. RVMD est
    une biotech clinique : 0 $ de ventes en FY2024 comme en FY2025 (EDGAR le confirme sous
    `RevenueFromContractWithCustomerExcludingAssessedTax`), et 11,58 M$ en FY2023, reste d'une
    collaboration éteinte. L'ancre publiait donc « 11,6 M$ de ventes » — un chiffre vieux de deux
    exercices — dans le paragraphe même où F8 déclare l'écart entre capitalisation et CA, et en
    **contradiction avec l'entry EDGAR tier A** du corpus, qui dit 0. Deux réponses actives à la
    même question, comme F5 : c'est le corpus narratif lu par les agents qui portait le conflit.

    Même famille que #44 : *absent* et *nul* sont deux états distincts, et les confondre fait lire
    une propriété de l'émetteur (il ne vend rien encore) comme un trou de collecte.

    L'exercice est rendu avec la valeur parce qu'un CA est un **flux** : le dater est exigé par
    #42, et c'est ce qui rend l'affirmation réfutable contre le fait EDGAR correspondant.
    """
    fin = m1.get("financials_3y") or {}
    years = sorted((y for y in fin if str(y).isdigit()), reverse=True)
    for y in years:
        rev = (fin.get(y) or {}).get("revenue")
        if rev is not None:
            return float(rev), str(y)
    return None, None


@dataclass
class BaseRateAnchorSpec:
    field: str
    entry_type: str
    title: str
    content: str
    content_structured: dict[str, Any]
    tags: list[str] = field(default_factory=list)
    source_type: str = "financial_press"   # étude de recherche financière publiée (CS/HOLT) → B+ 0.75
    source_url: str = BASE_RATE_BOOK["source_url"]


def classify_reference_class(m1: dict[str, Any]) -> dict[str, Any]:
    """Ticker (via m1) → classe de référence déterministe. Aucun LLM."""
    sales, sales_fy = _latest_revenue_usd(m1)
    mcap = (m1.get("price") or {}).get("market_cap")
    key, label, basis = size_bucket(sales, mcap)
    return {
        "metric": "croissance_ventes",
        "size_bucket": key,
        "size_label": label,
        "size_basis": basis,
        "sales_usd": sales,
        "sales_fiscal_year": sales_fy,   # un flux se date (#42) — et c'est ce qui le rend réfutable
        "market_cap_usd": mcap,
        "horizon": _DEFAULT_HORIZON,
    }


def build_base_rate_anchor_spec(
    ticker_id: str, symbol: str, m1: dict[str, Any], *, corpus_entry_id: Optional[int] = None
) -> BaseRateAnchorSpec:
    """Classe le ticker et compose l'entry qui fonde `valorisation.base_rate_anchor`. Pur (sans IO).

    Porte la distribution complète + les seuils représentatifs. Pour une méga-cap, marque le
    `taux_base_pct` de l'univers comme **borne haute** (la persistance chute avec la taille)."""
    rc = classify_reference_class(m1)
    horizon = rc["horizon"]
    thresholds = {f"{int(t)}": base_rate_ge(t, horizon) for t in _REPRESENTATIVE_THRESHOLDS}
    is_mega = rc["size_bucket"] == "mega"

    # Divergence de maille (F8, trouvé sur RVMD) : le bucket est calculé sur le CA, mais son libellé
    # emprunte le vocabulaire de la CAPITALISATION (« small-cap »). Sur une biotech clinique à
    # 44,8 Md$ de capitalisation et moins d'1 Md$ de CA, l'entry annonçait « small-cap » à un agent
    # qui lit du texte — tous les nombres justes, le fait faux (même famille que F6(a)). On ne
    # change pas la classe (le Base Rate Book classe bien par CA) : on DÉCLARE l'écart, puisque
    # c'est précisément l'information distinctive de ce profil d'émetteur.
    mcap_bucket = size_bucket(None, rc.get("market_cap_usd"))[0] if rc.get("market_cap_usd") else None
    mailles_divergentes = (
        rc["size_basis"] == "CA" and mcap_bucket is not None and mcap_bucket != rc["size_bucket"]
    )

    structured = {
        "metric": "base_rate_anchor",
        "reference_class": rc["size_label"],
        "size_bucket": rc["size_bucket"],
        "size_basis": rc["size_basis"],
        # Les deux mesures qui fondent la classe, exposées : sans elles, « small-cap » n'est pas
        # réfutable par le lecteur de l'entry.
        "sales_usd": rc.get("sales_usd"),
        "sales_fiscal_year": rc.get("sales_fiscal_year"),
        "market_cap_usd": rc.get("market_cap_usd"),
        "size_bucket_par_capitalisation": mcap_bucket,
        "mailles_divergentes": mailles_divergentes,
        "horizon": horizon,
        "thresholds_pct_ge": thresholds,          # {"15": .., "20": .., "25": ..} = P(CAGR ≥ seuil)
        "median_growth_pct": SALES_GROWTH_MEDIAN[horizon],
        "mean_growth_pct": SALES_GROWTH_MEAN[horizon],
        "distribution": {str(int(lo)) if lo > -100 else "<-25": freq[horizon]
                         for lo, freq in SALES_GROWTH_DISTRIBUTION},
        "upper_bound_for_size": is_mega,          # True = borne haute, persistance moindre à cette taille
        # Un CAGR de ventes ne se calcule pas depuis une base nulle : le premier dollar vendu est
        # une croissance infinie. La distribution reste l'outside view légitime sur la PERSISTANCE
        # d'une trajectoire, mais l'ancre ne doit pas être lue comme applicable telle quelle à un
        # émetteur sans ventes. On ne retire pas l'ancre (la classe est juste, cf. F8) : on
        # DÉCLARE la limite, sinon un reverse-DCF en aval la franchit sans le savoir.
        "base_ventes_nulle": rc.get("sales_usd") == 0,
        "source": BASE_RATE_BOOK["source"],
        "sample": BASE_RATE_BOOK["sample"],
        "corpus_entry_id": corpus_entry_id,
    }

    p20, p15 = thresholds["20"], thresholds["15"]
    content = (
        f"Ancre base rate (outside view) pour {ticker_id} ({symbol}) — classe de référence : "
        f"{rc['size_label']} (maille {rc['size_basis']}). Sur {horizon.replace('Y', ' ans')}, base rate "
        f"de croissance des ventes ({BASE_RATE_BOOK['sample']}) : P(≥20 %/an)={p20} %, P(≥15 %/an)={p15} %, "
        f"médiane {SALES_GROWTH_MEDIAN[horizon]} %/an. C'est le champ `base_rate_anchor` — une FRÉQUENCE "
        f"empirique, pas un multiple ni une prévision ; le taux exact pour la croissance impliquée par "
        f"le prix se calcule à l'analyse (reverse-DCF). "
    )
    if mailles_divergentes:
        content += (
            f"⚠ La classe est établie sur le CHIFFRE D'AFFAIRES, pas sur la capitalisation : "
            f"{symbol} pèse {_mds(rc['market_cap_usd'])} de capitalisation "
            f"(maille capitalisation : {size_bucket(None, rc['market_cap_usd'])[1].split(' (')[0]}) "
            f"pour {_mds(rc['sales_usd'])} de ventes{_exercice(rc)}. "
            f"Le libellé « {rc['size_label'].split(' (')[0]} » "
            f"qualifie donc le CA, jamais la taille boursière — ne pas le lire comme une petite "
            f"capitalisation. Cet écart est l'information distinctive de l'émetteur (valorisation "
            f"portée par un actif futur, pas par des ventes existantes), pas un défaut de classement. "
        )
    if structured["base_ventes_nulle"]:
        content += (
            f"⚠ Base de ventes NULLE{_exercice(rc)} : un CAGR de ventes ne se calcule pas depuis "
            f"zéro (le premier dollar vendu est une croissance infinie). La distribution ci-dessus "
            f"reste l'outside view sur la PERSISTANCE d'une trajectoire de croissance, mais elle "
            f"n'est pas applicable telle quelle en taux — l'analyse doit ancrer sur autre chose que "
            f"la croissance du CA (pipeline, marché adressable, jalons). Ce zéro est une propriété "
            f"mesurée de l'émetteur, pas un trou de collecte. "
        )
    if is_mega:
        content += (
            "⚠ Borne HAUTE : à cette taille (méga-cap), la persistance de forte croissance est nettement "
            "plus rare que dans l'univers complet (Base Rate Book, Exhibit 4 : >45 %/an sur 10 ans ≈ 0 "
            "société au décile 4,5-7 Md$). "
        )
    content += f"Source : {BASE_RATE_BOOK['source']}."

    return BaseRateAnchorSpec(
        field="base_rate_anchor",
        entry_type="base_rate",
        title=f"Valorisation — ancre base rate de croissance ({rc['size_label']})",
        content=content,
        content_structured=structured,
        tags=["valorisation", "base_rate_anchor", "base_rate", "outside_view"],
    )


# ── Corpus transverse (ticker_id NULL) — seedé une fois, réutilisable par tous les tickers ──────────
def _corpus_content() -> tuple[str, dict[str, Any]]:
    structured = {
        "metric": "sales_growth_base_rates",
        "horizons": list(_H),
        "distribution": [
            {"cagr_ge_pct": (lo if lo > -100 else None), "freq_pct": freq}
            for lo, freq in SALES_GROWTH_DISTRIBUTION
        ],
        "median_pct": SALES_GROWTH_MEDIAN,
        "mean_pct": SALES_GROWTH_MEAN,
        **BASE_RATE_BOOK,
    }
    content = (
        f"Corpus de base rates — croissance des ventes ({BASE_RATE_BOOK['exhibit']}, "
        f"{BASE_RATE_BOOK['sample']}). Distribution des CAGR de ventes sur 1/3/5/10 ans ; médiane à "
        f"3 ans {SALES_GROWTH_MEDIAN['3Y']} %/an, moyenne {SALES_GROWTH_MEAN['3Y']} %/an. Classe de "
        f"référence par taille (CA). Réutilisable par tous les tickers pour ancrer `base_rate_anchor`. "
        f"Source : {BASE_RATE_BOOK['source']}."
    )
    return content, structured


async def seed_base_rate_corpus(conn) -> int:
    """Insère (idempotent) l'entry de corpus transverse et renvoie son id.

    Idempotence : recherche une entry courante `ticker_id IS NULL` taguée `sales_growth_base_rate`."""
    row = await conn.fetchrow(
        """
        SELECT id FROM knowledge_entries
        WHERE ticker_id IS NULL AND superseded_by IS NULL AND is_deleted = FALSE
          AND tags @> $1
        ORDER BY id DESC LIMIT 1
        """,
        ["base_rate", "sales_growth_base_rate"],
    )
    if row:
        return row["id"]
    content, structured = _corpus_content()
    stored = await store_knowledge(
        conn,
        ticker_id=None,
        entry_type="base_rate",
        content=content,
        source_type="financial_press",
        title="Corpus base rates — croissance des ventes (Base Rate Book)",
        content_structured=structured,
        tags=["base_rate", "sales_growth_base_rate", "corpus", "outside_view"],
        lang="fr",
        source_url=BASE_RATE_BOOK["source_url"],
        # pas de source_date : une base rate structurelle 1950-2015 ne « vieillit » pas comme un
        # chiffre trimestriel — la faire décroître avec l'âge serait un faux signal (vintage en note).
    )
    logger.info("base_rate_corpus: entry de corpus seedée #%s", stored["id"])
    return stored["id"]


async def _current_anchor_entry_id(conn, ticker_id: str) -> Optional[int]:
    row = await conn.fetchrow(
        """
        SELECT id FROM knowledge_entries
        WHERE ticker_id = $1 AND superseded_by IS NULL AND is_deleted = FALSE
          AND tags @> $2
        ORDER BY id DESC LIMIT 1
        """,
        ticker_id, ["valorisation", "base_rate_anchor"],
    )
    return row["id"] if row else None


async def run_base_rate_anchor(
    ticker_id: str, *, persist: bool = True, refresh: bool = False
) -> dict[str, Any]:
    """Fonde `valorisation.base_rate_anchor` pour un ticker : classe de référence (quant) → base rate
    (corpus) → entry par-ticker. Seede le corpus au passage (idempotent)."""
    async with get_db_session() as conn:
        row = await conn.fetchrow(
            "SELECT ticker_symbol, company_type FROM tickers WHERE id = $1", ticker_id
        )
    if row is None:
        raise BaseRateUnavailable(f"ticker inconnu : {ticker_id}")
    if (row["company_type"] or "") == "private" or not row["ticker_symbol"]:
        raise BaseRateUnavailable(
            f"{ticker_id} : pas de symbole de marché — classe de référence à établir depuis des "
            f"documents uploadés (société non cotée), pas depuis le quant"
        )
    symbol = row["ticker_symbol"]

    svc = DataService()
    m1 = (
        await svc.refresh_m1(symbol, settings.FMP_API_KEY, context="base_rate_anchor")
        if refresh
        else await svc.get_m1(symbol, settings.FMP_API_KEY)
    )

    created: Optional[dict[str, Any]] = None
    corpus_entry_id: Optional[int] = None
    if persist:
        async with get_db_session() as conn:
            async with conn.transaction():
                corpus_entry_id = await seed_base_rate_corpus(conn)
                spec = build_base_rate_anchor_spec(ticker_id, symbol, m1, corpus_entry_id=corpus_entry_id)
                prev_id = await _current_anchor_entry_id(conn, ticker_id)
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
                    source_url=spec.source_url,
                    supersedes_entry_id=prev_id,
                    covers=[f"valorisation.{spec.field}"],   # index 029 : chemin complet
                )
                created = dict(stored) | {"field": spec.field, "supersedes": prev_id}
        logger.info("base_rate_anchor %s (%s) → entry #%s (corpus #%s)",
                    ticker_id, symbol, created["id"], corpus_entry_id)
    else:
        spec = build_base_rate_anchor_spec(ticker_id, symbol, m1)

    return {
        "ticker_id": ticker_id,
        "symbol": symbol,
        "reference_class": spec.content_structured["reference_class"],
        "entry": {
            "field": spec.field,
            "title": spec.title,
            "content": spec.content,
            "content_structured": spec.content_structured,
            "tags": spec.tags,
            "source_type": spec.source_type,
        },
        "corpus_entry_id": corpus_entry_id,
        "persisted": created,
        "dry_run": not persist,
    }
