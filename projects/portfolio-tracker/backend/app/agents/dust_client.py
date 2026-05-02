import asyncio
import httpx
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)
DUST_API_BASE = "https://dust.tt/api/v1"

MODEL_COSTS = {
    "claude-sonnet-4-5":        {"input": 0.0039,   "output": 0.0195},
    "gemini-2-5-flash-preview": {"input": 0.000195, "output": 0.00078},
    "gpt-4o-mini":              {"input": 0.000195, "output": 0.00078},
}


class DustBudgetExceededError(Exception):
    pass


class DustClient:
    def __init__(self):
        from app.config import settings
        self.api_key = settings.DUST_API_KEY
        self.workspace_id = settings.DUST_WORKSPACE_ID
        self.headers = {"Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"}

    async def check_budget(self):
        from app.db.database import get_db_session
        month = datetime.utcnow().strftime("%Y-%m")
        async with get_db_session() as db:
            result = await db.fetchrow(
                "SELECT spent_usd, budget_usd FROM dust_budget WHERE month = $1", month
            )
            if result and float(result["spent_usd"]) >= float(result["budget_usd"]):
                raise DustBudgetExceededError(
                    f"Budget épuisé : ${result['spent_usd']:.2f}/${result['budget_usd']:.2f}"
                )

    async def track_cost(self, model: str, tokens_in: int, tokens_out: int) -> float:
        from app.db.database import get_db_session
        from app.notifications.slack_notifier import SlackNotifier
        costs = MODEL_COSTS.get(model, {"input": 0.004, "output": 0.020})
        cost = tokens_in * costs["input"] / 1000 + tokens_out * costs["output"] / 1000
        month = datetime.utcnow().strftime("%Y-%m")
        async with get_db_session() as db:
            await db.execute("""
                INSERT INTO dust_budget (month, spent_usd, budget_usd)
                VALUES ($1, $2, 5.0)
                ON CONFLICT (month) DO UPDATE
                SET spent_usd = dust_budget.spent_usd + $2, last_updated = NOW()
            """, month, cost)
            r = await db.fetchrow(
                "SELECT spent_usd, budget_usd, alert_sent FROM dust_budget WHERE month=$1", month
            )
            if r and float(r["spent_usd"]) / float(r["budget_usd"]) >= 0.8 and not r["alert_sent"]:
                await SlackNotifier().send_budget_alert(float(r["spent_usd"]), float(r["budget_usd"]))
                await db.execute("UPDATE dust_budget SET alert_sent=TRUE WHERE month=$1", month)
        return cost

    async def run_agent(self, agent_id: str, message: str,
                        model_override: Optional[str] = None,
                        temperature: float = 0.3, timeout: int = 120) -> dict:
        await self.check_budget()
        async with httpx.AsyncClient(timeout=timeout) as client:
            # 1. Créer conversation
            r = await client.post(
                f"{DUST_API_BASE}/w/{self.workspace_id}/assistant/conversations",
                headers=self.headers,
                json={"visibility": "unlisted",
                      "title": f"portfolio-{datetime.utcnow().isoformat()}"},
            )
            r.raise_for_status()
            conv_id = r.json()["conversation"]["sId"]

            # 2. Poster message
            r2 = await client.post(
                f"{DUST_API_BASE}/w/{self.workspace_id}/assistant/conversations/{conv_id}/messages",
                headers=self.headers,
                json={"content": message,
                      "mentions": [{"configurationId": agent_id}],
                      "context": {"timezone": "Europe/Paris", "username": "portfolio-tracker",
                                  "fullName": "Portfolio Tracker", "email": "bot@portfolio",
                                  "profilePictureUrl": None}},
            )
            r2.raise_for_status()

            # 3. Polling
            start = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start < timeout:
                await asyncio.sleep(2)
                resp = await client.get(
                    f"{DUST_API_BASE}/w/{self.workspace_id}/assistant/conversations/{conv_id}",
                    headers=self.headers,
                )
                resp.raise_for_status()
                for group in reversed(resp.json().get("conversation", {}).get("content", [])):
                    for msg in group:
                        if msg.get("type") == "agent_message":
                            if msg.get("status") == "succeeded":
                                content = "".join(
                                    b.get("value", "") for b in msg.get("content", [])
                                    if b.get("type") == "text"
                                )
                                ti = msg.get("usage", {}).get("promptTokens", 0)
                                to = msg.get("usage", {}).get("completionTokens", 0)
                                m = model_override or "claude-sonnet-4-5"
                                cost = await self.track_cost(m, ti, to)
                                return {"content": content, "tokens_input": ti,
                                        "tokens_output": to, "cost_usd": cost}
                            elif msg.get("status") == "failed":
                                raise Exception(f"Agent failed: {msg.get('error')}")
            raise TimeoutError(f"Timeout after {timeout}s")
