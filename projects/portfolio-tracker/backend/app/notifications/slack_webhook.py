"""
SlackWebhook — notifications Slack via Incoming Webhook.
Plus simple que le Socket Mode pour les alertes V1.
"""
import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class SlackWebhook:
    async def send(self, text: str, blocks=None):
        """Envoie un message via le webhook. Silencieux si SLACK_WEBHOOK_URL n'est pas configuré."""
        if not settings.SLACK_WEBHOOK_URL:
            logger.debug("SLACK_WEBHOOK_URL non configuré — notification ignorée")
            return
        payload = {"text": text}
        if blocks:
            payload["blocks"] = blocks
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(settings.SLACK_WEBHOOK_URL, json=payload)
                if r.status_code != 200:
                    logger.warning(f"Slack webhook non-200: {r.status_code} — {r.text}")
        except Exception as e:
            logger.error(f"Slack webhook error: {e}")

    async def send_thesis_validated(
        self, ticker: str, one_liner: str, shares: float, price: float
    ):
        """Notification de validation d'une thèse et ouverture de position."""
        total = shares * price
        text = (
            f":white_check_mark: *Thèse validée — {ticker}*\n"
            f"_{one_liner}_\n"
            f"{shares} titres @ {price:.2f} = *{total:.0f}€*"
        )
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"Thèse validée — {ticker}"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Titres :* {shares}"},
                    {"type": "mrkdwn", "text": f"*Prix d'achat :* {price:.2f}"},
                    {"type": "mrkdwn", "text": f"*Montant total :* {total:.0f}€"},
                ],
            },
        ]
        if one_liner:
            blocks.append(
                {"type": "section", "text": {"type": "mrkdwn", "text": f"_{one_liner}_"}}
            )
        await self.send(text=text, blocks=blocks)

    async def send_monitoring_alert(
        self,
        ticker: str,
        alert_level: str,
        mode: int,
        label: str,
        session_id: int,
    ):
        """Notification d'alerte monitoring (REVIEW_REQUIRED ou CRITICAL)."""
        emoji = ":rotating_light:" if alert_level == "CRITICAL" else ":warning:"
        text = (
            f"{emoji} *Monitoring Alert* — {ticker}\n"
            f"Niveau : *{alert_level}* | Mode : {mode} | Session #{session_id}\n"
            f"Trigger : {label}"
        )
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji.replace(':', '')} Monitoring Alert — {ticker}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Niveau :* {alert_level}"},
                    {"type": "mrkdwn", "text": f"*Mode :* {mode}"},
                    {"type": "mrkdwn", "text": f"*Session :* #{session_id}"},
                    {"type": "mrkdwn", "text": f"*Trigger :* {label}"},
                ],
            },
        ]
        await self.send(text=text, blocks=blocks)

    async def send_monitoring_blocked(self, n_pending: int):
        """Notification quand des sessions sont bloquées par un agent non synchronisé."""
        text = (
            f":lock: *Monitoring bloqué* — {n_pending} session(s) en attente\n"
            f"L'agent monitoring n'est pas synchronisé. "
            f"Rendez-vous sur /admin/agents pour synchroniser."
        )
        await self.send(text=text)

    async def send_price_alert(
        self, ticker: str, current_price: float, alert_price: float, direction: str, label: Optional[str] = None
    ):
        """Notification de déclenchement d'une price alert."""
        direction_text = "au-dessus de" if direction == "above" else "en-dessous de"
        text = (
            f":bell: *Price Alert* — {ticker}\n"
            f"Prix actuel : *{current_price:.2f}* — {direction_text} {alert_price:.2f}"
        )
        if label:
            text += f"\n_{label}_"
        await self.send(text=text)
