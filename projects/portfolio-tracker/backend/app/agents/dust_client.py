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

DUST_CONTEXT = {
    "timezone": "Europe/Paris",
    "username": "portfolio-tracker",
    "fullName": "Portfolio Tracker",
    "email": "plm@lm-associes.com",
    "profilePictureUrl": None,
    "origin": "api",
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

    def _extract_agent_result(self, data: dict, model_override: str | None, conv_id: str):
        """Extrait le résultat de l'agent depuis la réponse Dust (blocking ou polling)."""
        for group in reversed(data.get("conversation", {}).get("content", [])):
            msgs = [group] if isinstance(group, dict) else group
            for msg in msgs:
                if not isinstance(msg, dict):
                    continue
                if msg.get("type") == "agent_message":
                    if msg.get("status") == "succeeded":
                        blocks = msg.get("content", [])
                        content = "".join(
                            (b.get("value") or b.get("text") or "")
                            for b in blocks
                            if isinstance(b, dict) and b.get("type") == "text"
                        )
                        if not content:
                            # Log pour diagnostiquer la structure réelle des blocs Dust
                            sample = [{"type": b.get("type"), "keys": list(b.keys())} for b in blocks[:5]]
                            logger.warning(f"Dust content vide (conv {conv_id}), blocs: {sample}")
                        ti = msg.get("usage", {}).get("promptTokens", 0)
                        to = msg.get("usage", {}).get("completionTokens", 0)
                        return {"content": content, "tokens_input": ti,
                                "tokens_output": to,
                                "model": model_override or "claude-sonnet-4-5",
                                "conversation_id": conv_id}
                    elif msg.get("status") == "failed":
                        raise Exception(f"Agent failed: {msg.get('error')}")
        return None

    async def run_agent(self, agent_id: str, message: str,
                        model_override: Optional[str] = None,
                        temperature: float = 0.3, timeout: int = 300) -> dict:
        """
        Crée une conversation Dust avec le message inclus et blocking=True.
        Une seule requête HTTP — pas de polling, pas de step intermédiaire.
        Retry automatique sur rate limit (backoff exponentiel, max 3 tentatives).
        """
        await self.check_budget()
        payload = {
            "visibility": "unlisted",
            "title": f"portfolio-{datetime.utcnow().isoformat()}",
            "message": {
                "content": message,
                "mentions": [{"configurationId": agent_id}],
                "context": DUST_CONTEXT,
            },
            "blocking": True,
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(3):
                r = await client.post(
                    f"{DUST_API_BASE}/w/{self.workspace_id}/assistant/conversations",
                    headers=self.headers,
                    json=payload,
                )
                if r.status_code == 403:
                    try:
                        body = r.json()
                    except Exception:
                        body = {}
                    if body.get("error", {}).get("type") == "rate_limit_error":
                        wait = 30 * (2 ** attempt)  # 30s, 60s, 120s
                        logger.warning(f"Dust rate limit, retry {attempt+1}/3 dans {wait}s")
                        await asyncio.sleep(wait)
                        continue
                if r.status_code in (502, 503, 504):
                    wait = 30 * (2 ** attempt)
                    logger.warning(f"Dust {r.status_code}, retry {attempt+1}/3 dans {wait}s")
                    await asyncio.sleep(wait)
                    continue
                if r.status_code >= 400:
                    logger.error(f"Dust /conversations {r.status_code}: {r.text}")
                r.raise_for_status()

                data = r.json()
                conv_id = data["conversation"]["sId"]
                result = self._extract_agent_result(data, model_override, conv_id)
                if result is None:
                    raise TimeoutError(f"Dust blocking: pas de message agent (conv {conv_id})")
                cost = await self.track_cost(result["model"], result["tokens_input"], result["tokens_output"])
                result["cost_usd"] = cost
                return result

            raise Exception("Dust rate limit persistant après 3 tentatives")
