"""
Point d'accroche de la synthèse des consignes @admin.

Le nom `agent_synthesis_stub` est conservé : c'est ce que `@update` (#1787559677493) et le job
hebdomadaire importent. Le stub est désormais câblé sur la vraie chaîne (#1787559677495) puis sur
la publication pour approbation humaine (#1787559677496).

Ce module ne fait qu'enchaîner deux étapes ; il ne décide rien et n'active aucune version.
"""
import logging

logger = logging.getLogger(__name__)


async def run_synthesis(triggered_by: str = "unknown") -> None:
    """Génère une proposition puis la poste pour décision humaine.

    Import local : `agent_synthesis` importe `slack_client`, qui importe la config Slack. Un import
    au niveau module créerait un cycle avec `agent_chat`, qui importe déjà ce fichier.
    """
    from app.handlers import agent_approval
    from app.services import agent_synthesis

    proposal_id = await agent_synthesis.run_synthesis(triggered_by=triggered_by)
    if not proposal_id:
        # Cas normaux : aucune consigne en attente, proposition déjà pendante, refus par les
        # bornes. Chacun a déjà produit son propre message ou sa propre entrée d'audit.
        return

    await agent_approval.post_proposal(proposal_id)
    logger.info(
        "run_synthesis: proposition %s postée pour approbation (triggered_by=%s)",
        proposal_id, triggered_by,
    )
