from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


# ── POSITION ─────────────────────────────────────────────────────────────────

class PositionCreate(BaseModel):
    ticker: str
    company_name: str
    sector_schema: str
    exchange: str
    entry_date: date
    entry_price: float
    entry_price_currency: str = "EUR"
    allocation_pct: Optional[float] = None
    quantity: Optional[float] = None
    status: str = "active"


class PositionUpdate(BaseModel):
    allocation_pct: Optional[float] = None
    status: Optional[str] = None
    exit_price: Optional[float] = None
    exit_date: Optional[date] = None
    exit_reason: Optional[str] = None
    exit_notes: Optional[str] = None
    quantity: Optional[float] = None
    schema_json: Optional[dict] = None


# ── HYPOTHESIS ────────────────────────────────────────────────────────────────

class HypothesisCreate(BaseModel):
    code: str
    label: str
    description: Optional[str] = None
    criticality: str  # critical / important / secondary
    verification_horizon: Optional[str] = None
    kpi_to_watch: Optional[str] = None
    confirmation_threshold: Optional[str] = None
    alert_threshold: Optional[str] = None


# ── THESIS ────────────────────────────────────────────────────────────────────

class ThesisCreate(BaseModel):
    thesis_one_liner: str
    bear_steel_man: str
    scenarios: dict
    price_thresholds: Optional[dict] = None
    entry_context: Optional[dict] = None
    hypotheses: List[HypothesisCreate] = []
    peers: Optional[List[dict]] = None
    analyst_track_record: Optional[List[dict]] = None


# ── WATCHLIST ─────────────────────────────────────────────────────────────────

class WatchlistCreate(BaseModel):
    ticker: str
    company_name: Optional[str] = None
    sector_schema: Optional[str] = None
    rationale: Optional[str] = None
    entry_price_target: Optional[float] = None
    trigger_alert_price: Optional[float] = None


class WatchlistUpdate(BaseModel):
    company_name: Optional[str] = None
    rationale: Optional[str] = None
    entry_price_target: Optional[float] = None
    trigger_alert_price: Optional[float] = None
    status: Optional[str] = None
    cash_ready: Optional[bool] = None
    sector_schema: Optional[str] = None


# ── CALENDAR ──────────────────────────────────────────────────────────────────

class CalendarEventCreate(BaseModel):
    ticker: str
    event_type: str
    event_date: date
    trigger_brief_date: Optional[date] = None
    trigger_review_date: Optional[date] = None
    priority: str = "high"
    source: Optional[str] = None
    notes: Optional[str] = None


# ── ANALYST ───────────────────────────────────────────────────────────────────

class AnalystActionCreate(BaseModel):
    analyst_firm: str
    ticker: str
    action_date: date
    action_type: Optional[str] = None
    from_recommendation: Optional[str] = None
    to_recommendation: Optional[str] = None
    from_target: Optional[float] = None
    to_target: Optional[float] = None
    stock_price_at_action: Optional[float] = None
    notes: Optional[str] = None


class AnalystActionUpdate(BaseModel):
    stock_price_30d_after: Optional[float] = None
    stock_price_90d_after: Optional[float] = None
    verdict: Optional[str] = None
    timing_quality: Optional[str] = None


# ── PEER ──────────────────────────────────────────────────────────────────────

class PeerCreate(BaseModel):
    peer_ticker: str
    peer_company_name: Optional[str] = None
    tier_level: int
    rationale: Optional[str] = None
    hypotheses_watched: Optional[List[str]] = None
    metrics_to_extract: Optional[List[str]] = None


# ── PORTFOLIO SETTINGS ────────────────────────────────────────────────────────

class PortfolioSettingsUpdate(BaseModel):
    total_capital_eur: Optional[float] = None
    cash_balance_eur: Optional[float] = None


class CashOperationCreate(BaseModel):
    operation_type: str  # deposit | withdrawal
    amount_eur: float
    notes: Optional[str] = None


# ── WATCHLIST VALIDATE ────────────────────────────────────────────────────────

class WatchlistValidateThesis(BaseModel):
    entry_price_target: Optional[float] = None
    trigger_alert_price: Optional[float] = None
    decision: str  # watch | invest_now


class WatchlistChatMessage(BaseModel):
    message: str
