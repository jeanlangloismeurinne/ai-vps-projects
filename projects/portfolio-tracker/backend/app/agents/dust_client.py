import asyncio
import httpx
import logging
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
        """Extrait le résultat de l'agent depuis la réponse Dust (blocking=True)."""
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

    async def run_agent_streaming(self, agent_id: str, message: str,
                                  model_override: Optional[str] = None,
                                  timeout: int = 720):
        """
        Appelle un agent Dust en mode non-blocking, puis poll les events SSE.
        Yields dicts :
          {"type": "started",          "conversation_id": str}
          {"type": "chain_of_thought", "text": str}
          {"type": "tokens",           "text": str}
          {"type": "done",             "content": str, "chain_of_thought": str,
                                       "tokens_input": int, "tokens_output": int,
                                       "cost_usd": float, "conversation_id": str}
        Raises RuntimeError / TimeoutError en cas d'erreur.
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
        }
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{DUST_API_BASE}/w/{self.workspace_id}/assistant/conversations",
                headers=self.headers,
                json=payload,
            )
            if r.status_code >= 400:
                logger.error(f"Dust {r.status_code}: {r.text[:300]}")
                raise RuntimeError(
                    f"Dust a retourné une erreur {r.status_code} — l'analyse n'a pas été traitée, tu peux relancer sans risque"
                )
            conv_id = r.json()["conversation"]["sId"]

        yield {"type": "started", "conversation_id": conv_id}

        accumulated_content = ""
        accumulated_cot = ""
        last_event_id = None
        deadline = asyncio.get_event_loop().time() + timeout
        silence_timeout = 90
        last_event_time = asyncio.get_event_loop().time()

        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            while asyncio.get_event_loop().time() < deadline:
                if asyncio.get_event_loop().time() - last_event_time > silence_timeout:
                    raise TimeoutError(
                        f"Dust streaming: aucun event depuis {silence_timeout}s (conv {conv_id}) — tu peux relancer sans risque"
                    )
                params = {}
                if last_event_id is not None:
                    params["lastEventId"] = last_event_id
                try:
                    r = await client.get(
                        f"{DUST_API_BASE}/w/{self.workspace_id}/assistant/conversations/{conv_id}/events",
                        headers=self.headers,
                        params=params,
                    )
                except httpx.TimeoutException:
                    await asyncio.sleep(0.3)
                    continue
                if r.status_code >= 400:
                    raise RuntimeError(f"Dust events {r.status_code}: {r.text[:200]}")
                if r.status_code != 200:
                    await asyncio.sleep(0.5)
                    continue

                events = r.json().get("events", [])
                if not events:
                    await asyncio.sleep(0.5)
                    continue

                last_event_time = asyncio.get_event_loop().time()
                for event in events:
                    eid = event.get("eventId")
                    if eid is not None:
                        last_event_id = eid
                    etype = event.get("type")
                    edata = event.get("data", {})

                    if etype == "generation_tokens":
                        text = edata.get("text", "")
                        classification = edata.get("classification", "tokens")
                        if classification == "chain_of_thought":
                            accumulated_cot += text
                            yield {"type": "chain_of_thought", "text": text}
                        else:
                            accumulated_content += text
                            yield {"type": "tokens", "text": text}

                    elif etype == "agent_message_success":
                        agent_msg = edata.get("agentMessage", {})
                        usage = agent_msg.get("usage", {})
                        ti = usage.get("promptTokens", 0)
                        to = usage.get("completionTokens", 0)
                        model = model_override or "claude-sonnet-4-6"
                        cost = await self.track_cost(model, ti, to)
                        yield {
                            "type": "done",
                            "content": accumulated_content,
                            "chain_of_thought": accumulated_cot,
                            "tokens_input": ti,
                            "tokens_output": to,
                            "cost_usd": cost,
                            "conversation_id": conv_id,
                            "model": model,
                        }
                        return

                    elif etype in ("agent_error", "user_message_error"):
                        err = edata.get("error", edata)
                        msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                        raise RuntimeError(f"Erreur agent Dust: {msg}")

        raise TimeoutError(f"Dust streaming: timeout {timeout}s (conv {conv_id}) — tu peux relancer sans risque")

    async def run_agent(self, agent_id: str, message: str,
                        model_override: Optional[str] = None,
                        temperature: float = 0.3, timeout: int = 720) -> dict:
        """
        Appelle un agent Dust en mode blocking=True.
        Dust attend la réponse complète du LLM avant de retourner (une seule requête HTTP).
        Timeout par défaut : 720s (12 min) pour les analyses longues avec Sonnet.
        Aucun retry — en cas d'erreur, l'utilisateur réessaie manuellement.
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
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.post(
                    f"{DUST_API_BASE}/w/{self.workspace_id}/assistant/conversations",
                    headers=self.headers,
                    json=payload,
                )
                if r.status_code >= 400:
                    logger.error(f"Dust {r.status_code}: {r.text[:300]}")
                r.raise_for_status()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            raise RuntimeError(
                f"Dust a retourné une erreur {status} — l'analyse n'a pas été traitée, tu peux relancer sans risque"
            ) from e
        except httpx.TimeoutException as e:
            raise RuntimeError(
                "L'agent Dust n'a pas répondu dans le délai imparti — l'analyse n'a pas été traitée, tu peux relancer sans risque"
            ) from e

        data = r.json()
        try:
            import json as _json, os as _os
            save_path = "/app/feedback-tickets/_dust_last_response.json"
            _os.makedirs(_os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "w") as _f:
                _json.dump({"agent_id": agent_id, "data": data}, _f, indent=2, default=str)
        except Exception:
            pass

        conv_id = data["conversation"]["sId"]
        result = self._extract_agent_result(data, model_override, conv_id)
        if result is None:
            raise TimeoutError(f"Dust blocking: pas de message agent (conv {conv_id})")
        cost = await self.track_cost(result["model"], result["tokens_input"], result["tokens_output"])
        result["cost_usd"] = cost
        return result
