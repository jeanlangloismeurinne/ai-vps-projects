"""
ThesisAgent — wrappeur Dust pour la construction de thèses d'investissement.

2 modes :
  freeform        : dialogue naturel, construction collaborative
  json_generation : génère uniquement le JSON de la thèse
"""
import re
import json
import logging

from app.agents.dust_client import DustClient
from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-5"

# Signal injecté en tête de message pour les sociétés non cotées.
# Le prompt Dust intègre directement la logique PE/VC déclenchée par ce signal.
_PRIVATE_SIGNAL = "[company_type: private]\n\n"


class AgentNotSyncedError(Exception):
    """Levée quand l'agent n'est pas marqué synced en DB."""


class ThesisAgent:
    def __init__(self):
        self.client = DustClient()

    async def _check_sync(self):
        """Vérifie que l'agent thesis-agent est synced en DB."""
        from app.db.database import get_db_session
        async with get_db_session() as db:
            row = await db.fetchrow(
                "SELECT synced, dust_agent_id FROM agent_prompts WHERE agent_name = $1",
                "thesis-agent",
            )
        if row is None:
            raise AgentNotSyncedError("Agent 'thesis-agent' introuvable en DB")
        if not row["synced"]:
            raise AgentNotSyncedError("Agent 'thesis-agent' non synchronisé — sync requis avant appel")
        agent_id = row["dust_agent_id"] or settings.DUST_THESIS_AGENT_ID
        if not agent_id:
            raise AgentNotSyncedError("Agent 'thesis-agent' : dust_agent_id non configuré")
        return agent_id

    async def run(self, mode: str, message: str, model_override: str = None, company_type: str = "public") -> dict:
        """
        Appelle le Dust thesis-agent.

        Paramètres :
          mode           : 'freeform' | 'json_generation'
          message        : contenu du message utilisateur (ou historique complet)
          model_override : remplace le modèle par défaut si fourni
          company_type   : 'public' | 'private' — injecte le delta PE/VC si private

        Retourne dict avec : content, tokens_input, tokens_output, cost_usd, conversation_id
        """
        agent_id = await self._check_sync()
        prefix = _PRIVATE_SIGNAL if company_type == "private" else ""
        full_message = f"{prefix}[mode: {mode}]\n\n{message}"
        model = model_override or DEFAULT_MODEL
        result = await self.client.run_agent(
            agent_id=agent_id,
            message=full_message,
            model_override=model,
        )
        return result

    async def run_streaming(self, mode: str, message: str, model_override: str = None, company_type: str = "public"):
        """Async generator — yielde les events Dust au fur et à mesure."""
        agent_id = await self._check_sync()
        prefix = _PRIVATE_SIGNAL if company_type == "private" else ""
        full_message = f"{prefix}[mode: {mode}]\n\n{message}"
        model = model_override or DEFAULT_MODEL
        async for event in self.client.run_agent_streaming(
            agent_id=agent_id,
            message=full_message,
            model_override=model,
        ):
            yield event

    def extract_json(self, content: str) -> dict | None:
        """Extrait le JSON entre ```json et ``` dans la réponse de l'agent."""
        m = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except (json.JSONDecodeError, ValueError):
                logger.warning("ThesisAgent.extract_json: JSON invalide dans la réponse agent")
                return None
        return None
