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

PRIVATE_THESIS_DELTA = """CONTEXTE SOCIÉTÉ NON COTÉE — PE/VC
Adapte chaque étape comme suit :
- Étape 1 : utilise les métriques PE/VC (ARR, EBITDA, burn, runway, LTV/CAC).
- Étape 2 : les pairs sont des sociétés privées ; les multiples sont EV/ARR ou EV/EBITDA.
- Étape 4 : les scénarios expriment une IRR et une valorisation de sortie (M€). Chaque scénario inclut exit_type parmi : ma_strategique, ipo, cession_secondaire, liquidation, recapitalisation.
- Étape 6 : remplace le track record analystes par "Références investisseurs & signaux de marché" (cap table, historique des tours, transactions comparables récentes).
- Étape 7 : les risques incluent obligatoirement le risque de dilution, le risque liquidité (absence de marché secondaire), et le risque clé-homme.
- price_thresholds → "valuation_thresholds" en M€ (pre-money) : entry_max_pre_money_m, reinforce_below_m, dilution_alert_below_m, exit_target_min_m, exit_target_optimal_m.
- Ajouter obligatoirement "exit_scenarios" (liste des scénarios de sortie).
- Ajouter "investor_references" : cap_table_notable, prior_rounds, market_signals.

"""


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
        prefix = PRIVATE_THESIS_DELTA if company_type == "private" else ""
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
        prefix = PRIVATE_THESIS_DELTA if company_type == "private" else ""
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
