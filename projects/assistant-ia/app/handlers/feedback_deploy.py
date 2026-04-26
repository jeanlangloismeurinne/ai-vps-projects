"""
Gère la notification de déploiement :
- Interroge le service pour récupérer les tickets fermés depuis le dernier déploiement
- Poste le résumé dans le channel Slack principal du service
- Mémorise la date du déploiement en DB
"""
import logging
from datetime import datetime, timezone, timedelta

from app.db import get_pool
from app.services import feedback_client, slack_client
from app.services import registry

logger = logging.getLogger(__name__)

TYPE_EMOJI = {"bug": "🐛", "feature": "✨", "suggestion": "💡", "error": "🔴"}
_DEFAULT_LOOKBACK_DAYS = 30


async def _get_last_deploy(service_name: str) -> datetime:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT last_deploy_at FROM service_deploys WHERE service = $1",
            service_name,
        )
    if row:
        dt = row["last_deploy_at"]
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - timedelta(days=_DEFAULT_LOOKBACK_DAYS)


async def _record_deploy(service_name: str) -> None:
    pool = await get_pool()
    now = datetime.now(timezone.utc)
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO service_deploys (service, last_deploy_at)
            VALUES ($1, $2)
            ON CONFLICT (service) DO UPDATE SET last_deploy_at = EXCLUDED.last_deploy_at
            """,
            service_name,
            now,
        )


async def handle_deploy_complete(service_name: str) -> None:
    svc = registry.by_name(service_name)
    if not svc:
        logger.warning("handle_deploy_complete: service '%s' non trouvé dans le registre", service_name)
        return

    last_deploy = await _get_last_deploy(service_name)
    tickets = await feedback_client.get_closed_since(
        base_url=svc["base_url"],
        since=last_deploy.isoformat(),
        api_key=svc["api_key"],
    )

    await _record_deploy(service_name)

    if not tickets:
        await slack_client.post_message(
            channel=svc["slack_channel"],
            text=f"🚀 *{service_name}* déployé avec succès. Aucun ticket fermé depuis le dernier déploiement.",
            blocks=[],
        )
        return

    lines = [f"🚀 *Déploiement {service_name}* — {len(tickets)} ticket(s) réalisé(s) :"]
    for t in tickets:
        emoji = TYPE_EMOJI.get(t.get("type", ""), "📝")
        desc = (t.get("description") or "")[:120]
        lines.append(f"• {emoji} {desc}")

    text = "\n".join(lines)
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": text}}]
    await slack_client.post_message(
        channel=svc["slack_channel"],
        text=text,
        blocks=blocks,
    )
    logger.info("Deploy notification sent for %s (%d tickets)", service_name, len(tickets))
