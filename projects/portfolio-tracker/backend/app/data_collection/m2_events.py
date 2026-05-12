import feedparser
import requests
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)

IR_FEEDS = {
    "CAP":  "https://www.capgemini.com/fr-fr/feed/",
    "ACN":  "https://newsroom.accenture.com/rss/",
    "CTSH": "https://ir.cognizant.com/rss/",
    "TCS":  "https://www.tcs.com/rss/press-release",
    "INFY": "https://www.infosys.com/newsroom/rss.xml",
}

MATERIAL_KEYWORDS_NEGATIVE = [
    "profit warning", "avertissement sur résultats", "below expectations",
    "revises guidance downward", "fraud", "investigation",
    "downgrade", "dégradation", "underweight",
]
MATERIAL_KEYWORDS_POSITIVE = [
    "raises guidance", "relève ses objectifs", "above expectations",
    "record", "acquisition", "strategic partnership", "upgrade", "outperform",
]


def get_earnings_calendar(ticker: str) -> dict:
    try:
        from app.data_collection.m1_quantitative import get_yfinance_ticker
        stock = yf.Ticker(get_yfinance_ticker(ticker))
        cal = stock.calendar
        if cal:
            dates = cal.get("Earnings Date", [])
            if dates:
                next_date = dates[0]
                # yfinance 1.x retourne datetime.date, 0.2.x retournait pd.Timestamp
                from datetime import date as _date
                date_obj = next_date if isinstance(next_date, _date) else next_date.date()
                return {
                    "ticker": ticker,
                    "next_earnings_date": str(date_obj),
                    "trigger_brief_date": str(date_obj - timedelta(days=2)),
                    "trigger_review_date": str(date_obj + timedelta(days=1)),
                    "source": "yfinance",
                }
    except Exception as e:
        logger.warning(f"Earnings calendar error for {ticker}: {e}")
    return {"ticker": ticker, "next_earnings_date": None, "source": "manual_required"}


def get_google_news_rss(company_name: str, ticker: str, max_items: int = 15) -> list:
    articles = []
    for query in [f"{company_name} results earnings guidance",
                  f"{company_name} acquisition downgrade upgrade"]:
        url = (f"https://news.google.com/rss/search"
               f"?q={requests.utils.quote(query)}&hl=fr&gl=FR&ceid=FR:fr")
        try:
            for entry in feedparser.parse(url).entries[:max_items]:
                score, direction = _score_materiality(
                    entry.get("title", ""), entry.get("summary", "")
                )
                if score > 0:
                    articles.append({
                        "title": entry.get("title"),
                        "link": entry.get("link"),
                        "published": entry.get("published"),
                        "materiality_score": score,
                        "direction": direction,
                    })
        except Exception as e:
            logger.warning(f"RSS error: {e}")
    seen, unique = set(), []
    for a in sorted(articles, key=lambda x: x["materiality_score"], reverse=True):
        if a["title"] not in seen:
            seen.add(a["title"])
            unique.append(a)
    return unique


def get_ir_feed(ticker: str, max_items: int = 10) -> list:
    feed_url = IR_FEEDS.get(ticker)
    if not feed_url:
        return []
    try:
        return [{"title": e.get("title"), "link": e.get("link"),
                 "published": e.get("published"), "source": "ir_official"}
                for e in feedparser.parse(feed_url).entries[:max_items]]
    except Exception:
        return []


def _score_materiality(title: str, summary: str) -> tuple:
    text = f"{title} {summary}".lower()
    score, direction = 0, "neutral"
    for kw in MATERIAL_KEYWORDS_NEGATIVE:
        if kw in text:
            score += 1; direction = "negative"
    for kw in MATERIAL_KEYWORDS_POSITIVE:
        if kw in text:
            score += 1
            if direction == "neutral":
                direction = "positive"
    return min(score, 3), direction


def collect_m2(ticker: str, company_name: str) -> dict:
    return {
        "ticker": ticker,
        "collected_at": datetime.utcnow().isoformat(),
        "earnings_calendar": get_earnings_calendar(ticker),
        "ir_feed": get_ir_feed(ticker),
        "news": get_google_news_rss(company_name, ticker),
    }
