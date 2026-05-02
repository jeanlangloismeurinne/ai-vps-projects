import yfinance as yf
import requests
from datetime import datetime
from typing import Optional
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
    if not hist.empty:
        price_data["ytd_change_pct"] = _calc_ytd_change(hist)
        price_data["1m_change_pct"] = _calc_period_change(hist, 21)
        price_data["3m_change_pct"] = _calc_period_change(hist, 63)
        price_data["6m_change_pct"] = _calc_period_change(hist, 126)
        price_data["1y_change_pct"] = _calc_period_change(hist, 252)

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


def _safe_float(df, row_name: str, col_idx: int) -> Optional[float]:
    try:
        val = df.loc[row_name].iloc[col_idx]
        return float(val) if val is not None else None
    except Exception:
        return None


def _calc_period_change(hist, days: int) -> Optional[float]:
    if len(hist) < days:
        return None
    return round((hist["Close"].iloc[-1] / hist["Close"].iloc[-days] - 1) * 100, 2)


def _calc_ytd_change(hist) -> Optional[float]:
    ytd = hist[hist.index.year == datetime.now().year]
    if ytd.empty:
        return None
    return round((ytd["Close"].iloc[-1] / ytd["Close"].iloc[0] - 1) * 100, 2)
