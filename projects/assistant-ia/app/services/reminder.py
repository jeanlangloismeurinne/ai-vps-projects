import logging
from app.services import kanban as kanban_svc
from app.services.slack_client import post_text
from app.config import settings

logger = logging.getLogger(__name__)


async def send_due_reminders():
    cards = await kanban_svc.get_cards_due_now()
    for card in cards:
        try:
            await post_text(
                channel=settings.SLACK_CHANNEL_TASKS,
                text=f"⏰ Rappel : *{card['title']}* — due maintenant",
            )
            await kanban_svc.mark_reminder_sent(str(card["id"]))
            logger.info(f"Reminder sent for card {card['id']} — {card['title']}")
        except Exception as exc:
            logger.error(f"Failed to send reminder for card {card['id']}: {exc}")
