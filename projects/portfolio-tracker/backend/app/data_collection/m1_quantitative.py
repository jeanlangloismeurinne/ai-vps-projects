import yfinance as yf
import requests
import math
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo
import logging

logger = logging.getLogger(__name__)

FMP_BASE = "https://financialmodelingprep.com/api/v3"

TICKER_EXCHANGE_MAP = {
    "CAP": "CAP.PA", "MC": "MC.PA", "AIR": "AIR.PA",
    "SAN": "SAN.PA", "OR": "OR.PA", "BNP": "BNP.PA",
    "ACN": "ACN", "CTSH": "CTSH", "TCS": "TCS",
    "INFY": "INFY", "HCLTECH": "HCLTECH.NS", "WIT": "WIT",
}


def get_yfinance_ticker(ticker: str) -> str:
    return TICKER_EXCHANGE_MAP.get(ticker, ticker)


def get_fmp_data(endpoint: str, api_key: str, params: dict = {}) -> dict:
    params["apikey"] = api_key
    resp = requests.get(f"{FMP_BASE}/{endpoint}", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def collect_quantitative(ticker: str, fmp_api_key: str, base_currency: str = "EUR") -> dict:
    yf_ticker = get_yfinance_ticker(ticker)
    stock = yf.Ticker(yf_ticker)
    info = stock.info or {}

    price_data = {
        "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "currency": info.get("currency", "USD"),
        "market_cap": info.get("marketCap"),
        "enterprise_value": info.get("enterpriseValue"),
        "52w_high": info.get("fiftyTwoWeekHigh"),
        "52w_low": info.get("fiftyTwoWeekLow"),
    }

    if price_data["current_price"] and price_data["52w_high"]:
        price_data["distance_from_52w_high_pct"] = round(
            (price_data["current_price"] / price_data["52w_high"] - 1) * 100, 2
        )

    hist = stock.history(period="1y")
    # `last_close_date` / `price_as_of` ne sont pas décoratifs : ce sont les DATES DE FAIT des
    # mesures ci-dessus (#79). Sans elles, `valuation_feed` datait le relevé du jour de sa lecture.
    price_data["last_close_date"] = None
    if not hist.empty:
        price_data["last_close_date"] = _derniere_cotation(hist)
        price_data["ytd_change_pct"] = _calc_ytd_change(hist)
        price_data["1m_change_pct"] = _calc_period_change(hist, 21)
        price_data["3m_change_pct"] = _calc_period_change(hist, 63)
        price_data["6m_change_pct"] = _calc_period_change(hist, 126)
        price_data["1y_change_pct"] = _calc_window_change(hist)
    price_data["price_as_of"] = _date_du_prix(info, price_data["last_close_date"])

    valuation = {
        "pe_ntm": info.get("forwardPE"),
        "pe_ttm": info.get("trailingPE"),
        "ev_ebitda": info.get("enterpriseToEbitda"),
        "ev_revenue": info.get("enterpriseToRevenue"),
        "price_to_book": info.get("priceToBook"),
        "fcf_yield_pct": None,
    }

    financials = {}
    try:
        fin = stock.financials
        cf = stock.cashflow
        if not fin.empty:
            for i, col in enumerate(fin.columns[:3]):
                year = str(col.year)
                financials[year] = {
                    "revenue": _safe_float(fin, "Total Revenue", i),
                    "operating_income": _safe_float(fin, "Operating Income", i),
                    "net_income": _safe_float(fin, "Net Income", i),
                }
        if not cf.empty:
            for i, col in enumerate(cf.columns[:3]):
                year = str(col.year)
                if year in financials:
                    fcf_val = _safe_float(cf, "Free Cash Flow", i)
                    financials[year]["fcf"] = fcf_val
                    if fcf_val and price_data.get("market_cap"):
                        valuation["fcf_yield_pct"] = round(
                            (fcf_val / price_data["market_cap"]) * 100, 2
                        )
    except Exception as e:
        logger.warning(f"Financials error for {ticker}: {e}")

    eps_estimates = {}
    try:
        # TODO: ajouter FMP_API_KEY dans les variables Coolify — cf. guide démarrage étape 4
        fmp_est = get_fmp_data(
            f"analyst-estimates/{yf_ticker}", fmp_api_key,
            {"period": "annual", "limit": 3}
        )
        for item in (fmp_est or [])[:3]:
            eps_estimates[item.get("date", "")[:4]] = {
                "eps_avg": item.get("estimatedEpsAvg"),
                "revenue_avg": item.get("estimatedRevenueAvg"),
            }
    except Exception as e:
        logger.warning(f"FMP estimates error for {ticker}: {e}")

    return {
        "ticker": ticker,
        "yf_ticker": yf_ticker,
        "collected_at": datetime.utcnow().isoformat(),
        "price": price_data,
        "valuation": valuation,
        "financials_3y": financials,
        "dividend": {
            "annual_dividend": info.get("dividendRate"),
            "dividend_yield_pct": round((info.get("dividendYield") or 0) * 100, 2),
            "payout_ratio": info.get("payoutRatio"),
        },
        "eps_estimates": eps_estimates,
    }


def collect_peers_quantitative(tickers: list, fmp_api_key: str) -> dict:
    result = {}
    for t in tickers:
        try:
            result[t] = collect_quantitative(t, fmp_api_key)
        except Exception as e:
            result[t] = {"error": str(e)}
    return result


def fini(val) -> Optional[float]:
    """Le DÉTENTEUR UNIQUE (#46) de « un non-nombre est une ABSENCE, pas un nombre ».

    `NaN` est un quatrième état muet : il a la FORME d'un nombre, il est **vrai** au sens booléen
    (`if nan:` passe, cf. #47), et il s'écrit en JSON comme le jeton nu `NaN`, que PostgreSQL
    refuse — donc il casse l'écriture du cache m1 **après** que le fetch réseau a été payé.
    Trois producteurs de ce fichier pouvaient en émettre (`_safe_float` et les deux `_calc_*`) :
    la règle vit ici, ils l'appellent (une règle recopiée trois fois n'est corrigée dans aucune).

    `0.0` traverse — c'est une VALEUR mesurée, jamais une absence (#47) ; seuls `None`, les
    non-finis (`nan`, `±inf`) et le non-castable retombent sur `None`.
    """
    if val is None:
        return None
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _safe_float(df, row_name: str, col_idx: int) -> Optional[float]:
    try:
        return fini(df.loc[row_name].iloc[col_idx])
    except Exception:
        return None


def serie_cotee(hist):
    """Le DÉTENTEUR UNIQUE (#46) de « une séance sans cours n'est pas une séance ».

    Arbitrage du fonds du 2026-09-23 : quand le dernier cours manque chez le fournisseur, on marque
    au **dernier cours coté** et on NOTE sa date — on ne laisse pas la fiche vide. C'est la règle
    de #79 transposée au prix : la mesure est datée du dernier FAIT, pas du jour où on la lit.

    Ce que ça répare, mesuré et non supposé (MSFT/NVDA/RVMD, 2026-09-23) : le fournisseur rend
    251 séances dont la DERNIÈRE, le 22/09, a un `Close` vide — identique sur les trois titres,
    donc c'est le fournisseur, pas le titre. Or les quatre variations (1m/3m/6m/YTD) se terminent
    TOUTES à `iloc[-1]` : un seul jour manquant les emportait les quatre d'un coup. Les gardes
    d'alors (`len(hist) < days`, `ytd.empty`) testaient la FORME du cadre, jamais la VALEUR des
    cours aux extrémités.

    Les fenêtres (21/63/126/252) comptent donc des séances RÉELLEMENT COTÉES, ce qui est leur sens.
    """
    return hist[hist["Close"].map(lambda c: fini(c) is not None)]


def _derniere_cotation(hist) -> Optional[str]:
    """Date ISO de la dernière séance cotée — la date à laquelle le fonds a marqué."""
    cotee = serie_cotee(hist)
    return None if cotee.empty else cotee.index[-1].date().isoformat()


def _date_du_prix(info: dict, repli: Optional[str]) -> Optional[str]:
    """Date du `current_price` selon l'horodatage du marché, pas selon l'horloge du serveur.

    `regularMarketTime` est l'heure de la dernière cotation régulière. Mesuré le 2026-09-23 sur
    MSFT : `1790107201` = 22/09 20:00 UTC = la clôture du 22/09 à New York. Autrement dit le
    « prix actuel » était déjà le cours de la VEILLE, et la fiche le datait du jour — exactement
    le défaut que #79 corrige, vivant dans le flux de prix.

    Converti dans le fuseau de la PLACE (`exchangeTimezoneName`) : une clôture asiatique tombe le
    lendemain en UTC, et daterait la mesure d'un jour de trop.
    """
    ts = info.get("regularMarketTime")
    if not isinstance(ts, (int, float)) or not math.isfinite(float(ts)):
        return repli
    try:
        tz = ZoneInfo(info.get("exchangeTimezoneName") or "UTC")
    except Exception:
        tz = timezone.utc
    return datetime.fromtimestamp(float(ts), tz).date().isoformat()


def _calc_period_change(hist, days: int) -> Optional[float]:
    cotee = serie_cotee(hist)
    if len(cotee) < days:
        return None
    debut, fin_ = fini(cotee["Close"].iloc[-days]), fini(cotee["Close"].iloc[-1])
    if debut is None or fin_ is None or debut == 0:
        return None
    return round((fin_ / debut - 1) * 100, 2)


def _calc_window_change(hist, minimum: int = 200) -> Optional[float]:
    """Variation sur TOUTE la fenêtre reçue — premier cours coté → dernier cours coté.

    Pourquoi ce calcul existe séparément : la variation « 1 an » se demandait à
    `_calc_period_change(hist, 252)`, or `period="1y"` rend **251 séances** (mesuré le 2026-09-23
    sur les trois titres). `len(hist) < 252` était donc vrai TOUJOURS — une colonne que jamais
    aucune donnée réelle n'aurait pu remplir, et dont le vide se lisait comme une propriété de
    l'émetteur (#69) alors qu'il était une propriété du seuil.

    La fenêtre EST d'un an par construction : on ne compte pas des séances, on prend ses deux
    bornes cotées. Le `minimum` garde ce que le seuil gardait vraiment — qu'une fenêtre tronquée
    (titre introduit en cours d'année, série amputée) ne soit pas étiquetée « 1 an ».
    """
    cotee = serie_cotee(hist)
    if len(cotee) < minimum:
        return None
    debut, fin_ = fini(cotee["Close"].iloc[0]), fini(cotee["Close"].iloc[-1])
    if debut is None or fin_ is None or debut == 0:
        return None
    return round((fin_ / debut - 1) * 100, 2)


def _calc_ytd_change(hist) -> Optional[float]:
    cotee = serie_cotee(hist)
    ytd = cotee[cotee.index.year == datetime.now().year]
    if ytd.empty:
        return None
    debut, fin_ = fini(ytd["Close"].iloc[0]), fini(ytd["Close"].iloc[-1])
    if debut is None or fin_ is None or debut == 0:
        return None
    return round((fin_ / debut - 1) * 100, 2)
