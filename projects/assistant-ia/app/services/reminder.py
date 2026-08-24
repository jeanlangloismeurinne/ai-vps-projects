import logging
from datetime import datetime, timedelta, timezone

from app.services import kanban as kanban_svc
from app.services.agent_time import format_local
from app.services.slack_client import post_text
from app.config import settings

logger = logging.getLogger(__name__)

# Borne de rattrapage (#1787579840500 a). Au-delà, un rappel échu n'est plus envoyé : réveiller
# des rappels vieux de plusieurs jours au redémarrage serait du bruit, pas un service. Il est
# malgré tout marqué `reminder_sent_at` pour ne pas être resélectionné à chaque tick, et tracé.
CATCHUP_MAX = timedelta(hours=24)


async def send_due_reminders():
    cards = await kanban_svc.get_cards_due_now()
    now = datetime.now(timezone.utc)

    for card in cards:
        card_id = str(card["id"])
        due = card["due_date"]
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        retard = now - due

        # Réservation atomique **avant** l'envoi : deux ticks qui se chevauchent ne peuvent pas
        # produire deux notifications pour la même carte.
        if not await kanban_svc.claim_reminder(card_id):
            continue

        if retard > CATCHUP_MAX:
            # Marqué (par la réservation) mais pas envoyé : il ne réapparaîtra plus, et la trace
            # existe — un rappel manqué ne doit jamais disparaître en silence.
            logger.warning(
                "Reminder skipped (trop ancien : %s de retard) card=%s — %s",
                retard, card_id, card["title"],
            )
            continue

        try:
            await post_text(
                channel=settings.SLACK_CHANNEL_TASKS,
                text=f"⏰ Rappel : *{card['title']}* — {format_local(due)}",
            )
            logger.info("Reminder sent for card %s — %s", card_id, card["title"])
        except Exception as exc:
            # L'envoi a échoué : on relâche la réservation pour que le tick suivant réessaie,
            # sinon la carte serait marquée « notifiée » sans que rien n'ait été notifié.
            await kanban_svc.release_reminder(card_id)
            logger.error("Failed to send reminder for card %s: %s", card_id, exc)
