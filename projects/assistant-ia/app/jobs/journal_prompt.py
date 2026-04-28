import logging
from datetime import date, datetime, timedelta
import pytz
from app.services import journal as journal_svc
from app.services import journal_v2 as svc_v2
from app.services.slack_client import post_text
from app.config import settings

logger = logging.getLogger(__name__)
_paris = pytz.timezone("Europe/Paris")


async def send_daily_prompt():
    today = date.today()
    existing = await journal_svc.get_today_prompt(today)
    if existing:
        logger.info("Journal prompt already sent today, skipping")
        return
    ts = await post_text(
        channel=settings.SLACK_CHANNEL_JOURNAL,
        text="💡 *Quel est ton apprentissage du jour ?*",
    )
    await journal_svc.store_prompt(ts, today)
    logger.info(f"Journal prompt sent for {today}, ts={ts}")


async def send_reminder():
    today = date.today()
    if await journal_svc.has_entry_today(today):
        return
    prompt = await journal_svc.get_today_prompt(today)
    if not prompt:
        return
    await post_text(
        channel=settings.SLACK_CHANNEL_JOURNAL,
        text="⏰ Tu n'as pas encore répondu. Quel est ton apprentissage du jour ?",
        thread_ts=prompt["slack_ts"],
    )
    logger.info("Journal reminder sent")


async def check_objectif_reminders():
    """Vérifie chaque minute quels objectifs doivent recevoir leur rappel Slack."""
    now = datetime.now(_paris)
    today = now.date()
    current_hhmm = now.strftime("%H:%M")

    due = await svc_v2.get_due_objectifs_today()
    for o in due:
        objectif_id = str(o["id"])
        rappel = str(o["heure_rappel"])[:5]  # "HH:MM"
        if rappel != current_hhmm:
            continue
        if await svc_v2.is_notified_today(objectif_id, today):
            continue
        if await svc_v2.is_objectif_complete(objectif_id, today):
            continue

        parcours_nom = o.get("parcours_nom", "")
        text = (
            f"📋 *{o['nom']}*"
            + (f" _(Parcours : {parcours_nom})_" if parcours_nom else "")
            + f"\nHeure de remplir ton journal → {settings.ASSISTANT_BASE_URL}/journal/fill/{objectif_id}"
        )
        await post_text(channel=settings.SLACK_CHANNEL_JOURNAL, text=text)
        await svc_v2.record_notification(objectif_id, today)
        logger.info(f"Rappel objectif envoyé: {o['nom']} ({objectif_id})")

    # Rappels de suivi : 3h après le premier message, si non complété
    for o in due:
        objectif_id = str(o["id"])
        rappel_time = o["heure_rappel"]
        followup_hhmm = (datetime.combine(today, rappel_time) + timedelta(hours=3)).strftime("%H:%M")
        if followup_hhmm != current_hhmm:
            continue
        notif = await svc_v2.get_notification_today(objectif_id, today)
        if not notif or notif["followup_sent_at"]:
            continue
        if await svc_v2.is_objectif_complete(objectif_id, today):
            continue
        parcours_nom = o.get("parcours_nom", "")
        text = (
            f"⏰ *Rappel : {o['nom']}*"
            + (f" _(Parcours : {parcours_nom})_" if parcours_nom else "")
            + f"\nTu n'as pas encore rempli ton journal → {settings.ASSISTANT_BASE_URL}/journal/fill/{objectif_id}"
        )
        await post_text(channel=settings.SLACK_CHANNEL_JOURNAL, text=text)
        await svc_v2.record_followup(objectif_id, today)
        logger.info(f"Rappel suivi envoyé: {o['nom']} ({objectif_id})")
