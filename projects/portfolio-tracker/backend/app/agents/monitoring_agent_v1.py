"""
MonitoringAgentV1 — wrappeur Dust pour le monitoring des thèses V1.

5 modes :
  1 : Pré-event Brief       (gpt-4o-mini)
  2 : Revue Trimestrielle   (gemini-2-5-flash-preview)
  3 : Décision Review       (claude-sonnet-4-5)
  4 : Sector Pulse          (gemini-2-5-flash-preview)
  5 : Routing d'Alerte      (gemini-2-5-flash-preview)
"""
import re
import json
import logging

from app.agents.dust_client import DustClient
from app.config import settings

logger = logging.getLogger(__name__)

# Pas de delta séparé — le prompt Dust intègre la logique PE/VC.
# Le contexte injecté par _build_monitoring_context() inclut déjà "company_type : private".

MODEL_BY_MODE = {
    1: "gpt-4o-mini",
    2: "gemini-2-5-flash-preview",
    3: "claude-sonnet-4-5",
    4: "gemini-2-5-flash-preview",
    5: "gemini-2-5-flash-preview",
}


class AgentNotSyncedError(Exception):
    """Levée quand l'agent n'est pas marqué synced en DB."""


class MonitoringAgentV1:
    def __init__(self):
        self.client = DustClient()

    async def _check_sync(self):
        """Vérifie que l'agent monitoring-agent est synced en DB."""
        from app.db.database import get_db_session
        async with get_db_session() as db:
            row = await db.fetchrow(
                "SELECT synced, dust_agent_id FROM agent_prompts WHERE agent_name = $1",
                "monitoring-agent",
            )
        if row is None:
            raise AgentNotSyncedError("Agent 'monitoring-agent' introuvable en DB")
        if not row["synced"]:
            raise AgentNotSyncedError("Agent 'monitoring-agent' non synchronisé — sync requis avant appel")
        agent_id = row["dust_agent_id"] or settings.DUST_MONITORING_AGENT_ID
        if not agent_id:
            raise AgentNotSyncedError("Agent 'monitoring-agent' : dust_agent_id non configuré")
        return agent_id

    async def run(self, mode: int, message: str, company_type: str = "public") -> dict:
        """
        Appelle le Dust monitoring-agent.

        Paramètres :
          mode         : 1..5
          message      : contexte complet à fournir à l'agent
          company_type : 'public' | 'private' — injecte le delta PE/VC si private

        Retourne dict avec : content, tokens_input, tokens_output, cost_usd, conversation_id
        """
        if mode not in MODEL_BY_MODE:
            raise ValueError(f"Mode invalide : {mode} (attendu 1..5)")
        agent_id = await self._check_sync()
        full_message = f"[mode: {mode}]\n\n{message}"
        model = MODEL_BY_MODE[mode]
        result = await self.client.run_agent(
            agent_id=agent_id,
            message=full_message,
            model_override=model,
        )
        return result

    def extract_json(self, content: str) -> dict | None:
        """Extrait le JSON entre ```json et ``` dans la réponse de l'agent."""
        m = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except (json.JSONDecodeError, ValueError):
                logger.warning("MonitoringAgentV1.extract_json: JSON invalide dans la réponse agent")
                return None
        return None
