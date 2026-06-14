import logging
from datetime import datetime
import pytz
from app.services import journal_v2 as svc
from app.services.slack_client import post_text
from app.config import settings
from itsdangerous import URLSafeTimedSerializer

logger = logging.getLogger(__name__)
_paris = pytz.timezone("Europe/Paris")

_JOURS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def _make_recap_token(objectif_id: str, semaine_iso: str) -> str:
    s = URLSafeTimedSerializer(settings.SESSION_SECRET, salt="journal-recap")
    return s.dumps(f"{objectif_id}:{semaine_iso}")


def _fmt_valeur_recap(valeur: dict, type_: str) -> str:
    if type_ in ("text", "short_text"):
        return valeur.get("text", "")
    if type_ in ("note", "scale"):
        v = valeur.get("value", "")
        return str(v)
    if type_ == "yes_no":
        return "Oui" if valeur.get("value") else "Non"
    if type_ == "single_choice":
        c = valeur.get("choice", "")
        o = valeur.get("other")
        return f"{c} — {o}" if c == "__other__" and o else c
    if type_ == "multiple_choice":
        choices = valeur.get("choices", [])
        other = valeur.get("other")
        parts = choices[:]
        if other:
            parts.append(f"Autre : {other}")
        return ", ".join(parts) if parts else "—"
    if type_ == "date":
        return valeur.get("value", "")
    if type_ == "duration":
        return f"{valeur.get('value', '')} {valeur.get('unit', '')}"
    if type_ == "ranking":
        return " → ".join(valeur.get("order", []))
    return str(valeur)


async def send_recap_hebdo():
    """Vérifie chaque minute si un récap hebdo doit être envoyé."""
    now = datetime.now(_paris)
    today_weekday = now.weekday()
    current_time = now.strftime("%H:%M")

    objectifs = await svc.get_objectifs_recap_dus(today_weekday, current_time)
    for obj in objectifs:
        objectif_id = str(obj["id"])
        iso_year, iso_week, _ = now.isocalendar()
        semaine = f"{iso_year}-W{iso_week:02d}"

        if await svc.recap_deja_envoye(objectif_id, semaine):
            continue

        reponses = await svc.get_reponses_semaine(objectif_id, semaine)
        if not reponses:
            continue

        await _envoyer_recap_slack(obj, reponses, semaine)
        await svc.marquer_recap_envoye(objectif_id, semaine)
        logger.info(f"Récap hebdo envoyé: {obj['nom']} ({objectif_id}) semaine={semaine}")


async def _envoyer_recap_slack(obj, reponses: dict, semaine_iso: str) -> None:
    objectif_id = str(obj["id"])
    token = _make_recap_token(objectif_id, semaine_iso)
    recap_url = f"{settings.ASSISTANT_BASE_URL}/journal/recap/{objectif_id}/{semaine_iso}?token={token}"

    # Calcul de la période affichée
    year_str, week_str = semaine_iso.split("-W")
    from datetime import timedelta
    from datetime import datetime as dt
    lundi = dt.strptime(f"{year_str}-W{int(week_str):02d}-1", "%G-W%V-%u").date()
    dimanche = lundi + timedelta(days=6)
    periode = f"du {lundi.strftime('%d/%m')} au {dimanche.strftime('%d/%m')}"

    lines = [f"📋 *Récap semaine — {obj['nom']}* ({periode})\n"]

    for question_texte, entries in reponses.items():
        block = f"\n*{question_texte}*\n"
        for e in entries:
            d = e["session_date"].strftime("%d/%m")
            val = _fmt_valeur_recap(e["valeur"], e["type"])
            nom_jour = _JOURS_FR[e["session_date"].weekday()]
            block += f"• {nom_jour} {d} : {val}\n"
        lines.append(block)

    lines.append(f"\n👉 <{recap_url}|Voir le récap complet>")

    text = "".join(lines)
    if len(text) > 3000:
        text = text[:2900] + f"\n\n…_(message tronqué)_\n👉 <{recap_url}|Voir le récap complet>"

    await post_text(channel=settings.SLACK_CHANNEL_JOURNAL, text=text)
