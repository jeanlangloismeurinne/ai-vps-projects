"""
OpportunityAgent — wrappeur Dust pour l'analyse d'opportunités.

3 modes :
  freeform            : dialogue naturel, génère un Investment Brief
  json_generation     : génère uniquement le JSON du brief
  conviction_challenge: débat PASS vs conviction utilisateur
"""
import re
import json
import logging

from app.agents.dust_client import DustClient
from app.config import settings

logger = logging.getLogger(__name__)

# Modèle par défaut pour l'opportunity agent
DEFAULT_MODEL = "gemini-2-5-flash-preview"

PRIVATE_COMPANY_DELTA = """CONTEXTE SOCIÉTÉ NON COTÉE — PE/VC
Cette société n'est pas cotée en bourse. Les règles suivantes s'appliquent :
- Pas de cours de marché ni de données boursières. Utilise exclusivement les données financières fournies (ARR/CA, EBITDA, valorisation dernière levée, métriques clés).
- Remplace les critères de screening boursiers par les 5 critères PE/VC : (1) Marché adressable ≥500M€ OU croissance CA >30% YoY ; (2) Modèle économique avec chemin vers rentabilité (unit economics positives ou runway >18 mois) ; (3) Avantage compétitif défendable ; (4) Catalyseur identifiable à 6-24 mois ; (5) Équipe fondatrice trackable.
- Le diagnostic d'anomalie porte sur l'attractivité des multiples vs comparables privés.
- Les analogies et peers sont des sociétés privées ou des transactions récentes.
- Le "downside floor" est la valorisation plancher (book value ou multiple minimal sectoriel).
- Pas de recommandation de cours cible. Raisonne en valorisation (M€).

"""


class AgentNotSyncedError(Exception):
    """Levée quand l'agent n'est pas marqué synced en DB."""


class OpportunityAgent:
    def __init__(self):
        self.client = DustClient()

    async def _check_sync(self):
        """Vérifie que l'agent opportunity-agent est synced en DB."""
        from app.db.database import get_db_session
        async with get_db_session() as db:
            row = await db.fetchrow(
                "SELECT synced, dust_agent_id FROM agent_prompts WHERE agent_name = $1",
                "opportunity-agent",
            )
        if row is None:
            raise AgentNotSyncedError("Agent 'opportunity-agent' introuvable en DB")
        if not row["synced"]:
            raise AgentNotSyncedError("Agent 'opportunity-agent' non synchronisé — sync requis avant appel")
        agent_id = row["dust_agent_id"] or settings.DUST_OPPORTUNITY_AGENT_ID
        if not agent_id:
            raise AgentNotSyncedError("Agent 'opportunity-agent' : dust_agent_id non configuré")
        return agent_id

    async def run(self, mode: str, message: str, model_override: str = None, company_type: str = "public") -> dict:
        """
        Appelle le Dust opportunity-agent.

        Paramètres :
          mode           : 'freeform' | 'json_generation' | 'conviction_challenge'
          message        : contenu du message utilisateur
          model_override : remplace le modèle par défaut si fourni
          company_type   : 'public' | 'private' — injecte le delta PE/VC si private

        Retourne dict avec : content, tokens_input, tokens_output, cost_usd, conversation_id
        """
        agent_id = await self._check_sync()
        prefix = PRIVATE_COMPANY_DELTA if company_type == "private" else ""
        full_message = f"{prefix}[mode: {mode}]\n\n{message}"
        model = model_override or DEFAULT_MODEL
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
                logger.warning("extract_json: JSON invalide dans la réponse agent")
                return None
        return None
