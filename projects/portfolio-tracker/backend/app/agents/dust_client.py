import asyncio
import httpx
import logging
import time
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)
DUST_API_BASE = "https://dust.tt/api/v1"

MODEL_COSTS = {
    "claude-sonnet-4-5":        {"input": 0.0039,   "output": 0.0195},
    "claude-sonnet-4-6":        {"input": 0.0039,   "output": 0.0195},
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
        """Extrait le résultat de l'agent depuis la réponse Dust."""
        for group in reversed(data.get("conversation", {}).get("content", [])):
            msgs = [group] if isinstance(group, dict) else group
            for msg in msgs:
                if not isinstance(msg, dict):
                    continue
                if msg.get("type") == "agent_message":
                    if msg.get("status") == "succeeded":
                        blocks = msg.get("content", [])
                        parts = []
                        for b in blocks:
                            if isinstance(b, str):
                                parts.append(b)
                            elif isinstance(b, dict) and b.get("type") == "text":
                                parts.append(b.get("value") or b.get("text") or "")
                        content = "".join(parts)
                        ti = msg.get("usage", {}).get("promptTokens", 0)
                        to = msg.get("usage", {}).get("completionTokens", 0)
                        return {"content": content, "tokens_input": ti,
                                "tokens_output": to,
                                "model": model_override or "claude-sonnet-4-6",
                                "conversation_id": conv_id}
                    elif msg.get("status") == "failed":
                        raise Exception(f"Agent failed: {msg.get('error')}")
        return None

    async def run_agent(self, agent_id: str, message: str,
                        model_override: Optional[str] = None,
                        temperature: float = 0.3, timeout: int = 480) -> dict:
        """
        Crée une conversation Dust (blocking=False) puis poll jusqu'à la réponse.
        Chaque requête HTTP est courte (≤30s) — pas de connexion longue durée.
        Timeout total par défaut : 480s (8 min).
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
            "blocking": False,
        }

        # Étape 1 — créer la conversation (requête légère, timeout 30s)
        conv_id = None
        async with httpx.AsyncClient(timeout=30) as client:
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
                        wait = 5 * (2 ** attempt)  # 5s, 10s, 20s
                        logger.warning(f"Dust rate limit, retry {attempt+1}/3 dans {wait}s")
                        await asyncio.sleep(wait)
                        continue
                if r.status_code >= 400:
                    logger.error(f"Dust POST /conversations {r.status_code}: {r.text[:300]}")
                r.raise_for_status()
                conv_id = r.json()["conversation"]["sId"]
                break
            else:
                raise Exception("Dust rate limit persistant après 3 tentatives")

        # Étape 2 — poll jusqu'à la réponse de l'agent
        logger.info(f"Dust conv {conv_id} créée — polling (timeout {timeout}s)")
        deadline = time.monotonic() + timeout
        poll_url = f"{DUST_API_BASE}/w/{self.workspace_id}/assistant/conversations/{conv_id}"

        async with httpx.AsyncClient(timeout=30) as poll_client:
            poll_interval = 3
            while time.monotonic() < deadline:
                await asyncio.sleep(poll_interval)
                try:
                    pr = await poll_client.get(poll_url, headers=self.headers)
                except Exception as e:
                    logger.warning(f"Dust poll error pour {conv_id}: {e}")
                    continue
                if not pr.ok:
                    logger.warning(f"Dust poll {pr.status_code} pour {conv_id}")
                    continue

                data = pr.json()
                result = self._extract_agent_result(data, model_override, conv_id)
                if result is not None:
                    try:
                        import json as _json, os as _os
                        save_path = "/app/feedback-tickets/_dust_last_response.json"
                        _os.makedirs(_os.path.dirname(save_path), exist_ok=True)
                        with open(save_path, "w") as _f:
                            _json.dump({"agent_id": agent_id, "conv_id": conv_id, "data": data},
                                       _f, indent=2, default=str)
                    except Exception:
                        pass
                    cost = await self.track_cost(result["model"], result["tokens_input"], result["tokens_output"])
                    result["cost_usd"] = cost
                    return result

        raise TimeoutError(f"Agent timeout après {timeout}s (conv {conv_id})")
