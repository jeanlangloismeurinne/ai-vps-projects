import asyncio
import httpx
import json
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

    async def _resolve_sse_url(self, conv_id: str, msg_id: str) -> str:
        """
        Suit manuellement le 307 de /api/v1/w/.../events pour obtenir l'URL SSE réelle.
        httpx supprime Authorization lors d'un redirect https→http, d'où l'interception manuelle.
        """
        v1_url = (
            f"{DUST_API_BASE}/w/{self.workspace_id}/assistant/conversations"
            f"/{conv_id}/messages/{msg_id}/events"
        )
        async with httpx.AsyncClient(follow_redirects=False, timeout=10) as client:
            r = await client.get(v1_url, headers=self.headers)
        if r.status_code == 307:
            location = r.headers.get("location", "")
            return location.replace("http://", "https://", 1)
        if r.status_code == 200:
            return v1_url
        raise RuntimeError(f"Dust SSE resolve: statut inattendu {r.status_code}")

    async def run_agent_streaming(self, agent_id: str, message: str,
                                  model_override: Optional[str] = None,
                                  timeout: int = 720):
        """
        Streaming SSE réel.

        Flow :
          1. POST /api/v1/w/.../conversations  blocking=False  → conv_id + agent_message_id
          2. GET  /api/v1/w/.../messages/{mId}/events          → 307 vers URL SSE réelle
          3. GET  {sse_url} avec Authorization ré-injecté      → SSE token-par-token

        Le 307 redirige http→https, ce qui pousse httpx à supprimer Authorization.
        On intercepte le redirect manuellement et on ré-injecte le header sur l'URL finale.

        Yields :
          {"type": "started",          "conversation_id": str}
          {"type": "chain_of_thought", "text": str}
          {"type": "tokens",           "text": str}
          {"type": "done",             "content": str, "chain_of_thought": str,
                                       "tokens_input": int, "tokens_output": int,
                                       "cost_usd": float, "conversation_id": str}
        """
        await self.check_budget()

        # Étape 1 — créer la conversation en non-blocking
        payload = {
            "visibility": "unlisted",
            "title": f"portfolio-{datetime.utcnow().isoformat()}",
            "blocking": False,
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
            data = r.json()

        conv_id = data["conversation"]["sId"]
        try:
            agent_msg_id = data["conversation"]["content"][1][0]["sId"]
        except (IndexError, KeyError, TypeError) as e:
            raise RuntimeError(f"Dust: agent_message introuvable dans la réponse (conv {conv_id})") from e

        yield {"type": "started", "conversation_id": conv_id}

        # Étape 2 — résoudre l'URL SSE via le 307
        sse_url = await self._resolve_sse_url(conv_id, agent_msg_id)
        logger.info(f"Dust SSE URL: {sse_url}")

        # Étape 3 — streamer avec Authorization ré-injecté
        sse_headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "text/event-stream",
        }
        accumulated_content = ""
        accumulated_cot = ""

        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("GET", sse_url, headers=sse_headers) as resp:
                if resp.status_code >= 400:
                    body = await resp.aread()
                    raise RuntimeError(f"Dust SSE {resp.status_code}: {body[:200]}")

                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    raw = line[6:].strip()
                    if raw == "[DONE]":
                        break
                    try:
                        event = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    etype = event.get("type")

                    if etype == "generation_tokens":
                        text = event.get("text", "")
                        classification = event.get("classification", "tokens")
                        if classification == "chain_of_thought":
                            accumulated_cot += text
                            yield {"type": "chain_of_thought", "text": text}
                        else:
                            accumulated_content += text
                            yield {"type": "tokens", "text": text}

                    elif etype == "agent_message_success":
                        agent_msg = event.get("agentMessage", {})
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
                        err = event.get("error", event)
                        msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                        raise RuntimeError(f"Erreur agent Dust: {msg}")

        # Stream terminé sans agent_message_success
        if accumulated_content:
            model = model_override or "claude-sonnet-4-6"
            cost = await self.track_cost(model, 0, 0)
            yield {
                "type": "done",
                "content": accumulated_content,
                "chain_of_thought": accumulated_cot,
                "tokens_input": 0,
                "tokens_output": 0,
                "cost_usd": cost,
                "conversation_id": conv_id,
                "model": model,
            }
        else:
            raise TimeoutError(
                f"Dust SSE: stream terminé sans réponse (conv {conv_id}) — tu peux relancer sans risque"
            )

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
