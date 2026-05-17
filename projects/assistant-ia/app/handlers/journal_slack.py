"""
Orchestre le flux Q→R→Q du journal dans Slack.
Appelé depuis journal_prompt.py (démarrage) et slack_app.py (réponses).
"""
import json
import logging
from datetime import date

from app.services import journal_v2 as svc
from app.services.slack_client import post_text, post_blocks
from app.config import settings

logger = logging.getLogger(__name__)

_BOT_USER_ID = "bot"  # valeur sentinelle pour créer la session côté bot


def _question_blocks(question, objectif_id: str, q_index: int) -> list:
    """Construit les blocs Block Kit pour une question."""
    type_ = question["type"]
    cfg = question["config"]
    if isinstance(cfg, str):
        cfg = json.loads(cfg)
    texte = question["texte"]

    header = {
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*{texte}*"},
    }

    button_types = ("note", "yes_no", "single_choice")
    if type_ not in button_types:
        return [header]

    elements = []
    if type_ == "yes_no":
        for label, val in [("Oui", "true"), ("Non", "false")]:
            elements.append({
                "type": "button",
                "text": {"type": "plain_text", "text": label},
                "action_id": f"jrn_{q_index}_{val}",
                "value": f"{objectif_id}|{q_index}|{val}",
            })

    elif type_ == "note":
        mn, mx = cfg.get("min", 1), cfg.get("max", 5)
        if mx - mn > 9:
            # Trop de valeurs pour des boutons — texte libre
            return [header]
        for v in range(mn, mx + 1):
            elements.append({
                "type": "button",
                "text": {"type": "plain_text", "text": str(v)},
                "action_id": f"jrn_{q_index}_{v}",
                "value": f"{objectif_id}|{q_index}|{v}",
            })

    elif type_ == "single_choice":
        for i, opt in enumerate(cfg.get("options", [])[:5]):
            elements.append({
                "type": "button",
                "text": {"type": "plain_text", "text": opt[:75]},
                "action_id": f"jrn_{q_index}_{i}",
                "value": f"{objectif_id}|{q_index}|{opt}",
            })

    if not elements:
        return [header]

    return [header, {"type": "actions", "elements": elements}]


def _parse_text_answer(question, text: str) -> dict | None:
    """Convertit une réponse textuelle libre en valeur structurée selon le type."""
    type_ = question["type"]
    cfg = question["config"]
    if isinstance(cfg, str):
        cfg = json.loads(cfg)

    text = text.strip()
    if not text:
        return None

    if type_ in ("text", "short_text"):
        return {"text": text}

    if type_ in ("note", "scale"):
        try:
            return {"value": int(text)}
        except ValueError:
            return None

    if type_ == "yes_no":
        lower = text.lower()
        if lower in ("oui", "yes", "o", "y", "true", "1"):
            return {"value": True}
        if lower in ("non", "no", "n", "false", "0"):
            return {"value": False}
        return None

    if type_ == "single_choice":
        return {"choice": text}

    if type_ == "multiple_choice":
        return {"choices": [c.strip() for c in text.split(",") if c.strip()]}

    if type_ == "duration":
        try:
            cfg_unit = cfg.get("unit", "minutes")
            return {"value": int(text), "unit": cfg_unit}
        except ValueError:
            return None

    if type_ == "date":
        return {"value": text}

    if type_ == "ranking":
        return {"order": [c.strip() for c in text.split(",") if c.strip()]}

    return {"text": text}


async def start_objectif_flow(
    objectif_id: str,
    objectif_nom: str,
    user_id: str,
    channel: str,
    parcours_nom: str = "",
) -> None:
    """Envoie Q1 dans Slack et crée la session."""
    today = date.today()

    if await svc.is_objectif_complete(objectif_id, today):
        return

    questions = await svc.get_questions(objectif_id)
    if not questions:
        return

    header_text = (
        f"📋 *{objectif_nom}*"
        + (f" _(Parcours : {parcours_nom})_" if parcours_nom else "")
        + "\nRéponds directement dans ce fil ↓"
    )
    thread_ts = await post_text(channel=channel, text=header_text)
    if not thread_ts:
        logger.error(f"Impossible d'envoyer le message d'intro pour {objectif_id}")
        return

    await svc.create_slack_session(user_id, objectif_id, thread_ts, today)

    q = questions[0]
    blocks = _question_blocks(q, objectif_id, 0)
    hint = _question_hint(q)
    await post_blocks(
        channel=channel,
        blocks=blocks,
        text=q["texte"],
        thread_ts=thread_ts,
        mrkdwn=hint,
    )
    logger.info(f"Slack Q1 envoyée: objectif={objectif_id}, thread={thread_ts}")


def _question_hint(question) -> str:
    type_ = question["type"]
    cfg = question["config"]
    if isinstance(cfg, str):
        cfg = json.loads(cfg)

    if type_ == "note":
        mn, mx = cfg.get("min", 1), cfg.get("max", 5)
        if mx - mn > 9:
            return f"_Envoie un nombre entre {mn} et {mx}._"
        return ""  # les boutons suffisent

    hints = {
        "text": "_Réponds par un message dans ce fil._",
        "short_text": "_Réponds par un message court._",
        "scale": "_Envoie un chiffre._",
        "duration": "_Envoie un nombre (en minutes ou heures)._",
        "date": "_Envoie une date (AAAA-MM-JJ)._",
        "multiple_choice": "_Envoie tes choix séparés par des virgules._",
        "ranking": "_Envoie les éléments dans l'ordre, séparés par des virgules._",
    }
    return hints.get(type_, "")


async def handle_thread_reply(
    thread_ts: str,
    user_id: str,
    text: str,
    channel: str,
) -> None:
    """Traite une réponse texte dans un fil de session journal Slack."""
    session = await svc.get_slack_session_by_thread(thread_ts)
    if not session:
        return

    today = date.today()
    objectif_id = str(session["objectif_id"])
    q_index = session["question_index"]

    questions = await svc.get_questions(objectif_id)
    logger.info(f"handle_thread_reply: objectif={objectif_id} q_index={q_index}/{len(questions)} text={text[:60]!r}")

    if q_index >= len(questions):
        logger.info("handle_thread_reply: toutes les questions traitées, fin")
        return

    q = questions[q_index]
    valeur = _parse_text_answer(q, text)
    if valeur is None:
        logger.warning(f"handle_thread_reply: réponse non parsée pour type={q['type']}")
        await post_text(
            channel=channel,
            text="Je n'ai pas compris ta réponse. Réessaie.",
            thread_ts=thread_ts,
        )
        return

    await svc.store_reponse(str(q["id"]), objectif_id, valeur, today)
    next_index = q_index + 1
    await svc.advance_slack_session(session["id"], next_index)
    logger.info(f"handle_thread_reply: réponse stockée, avancement à q_index={next_index}")

    await _post_next_question(objectif_id, questions, next_index, channel, thread_ts)


async def handle_block_action(
    objectif_id: str,
    q_index: int,
    raw_value: str,
    user_id: str,
    channel: str,
    thread_ts: str,
) -> None:
    """Traite une réponse via bouton Block Kit."""
    today = date.today()

    questions = await svc.get_questions(objectif_id)
    if q_index >= len(questions):
        return

    q = questions[q_index]
    type_ = q["type"]
    cfg = q["config"]
    if isinstance(cfg, str):
        cfg = json.loads(cfg)

    if type_ == "yes_no":
        valeur = {"value": raw_value == "true"}
    elif type_ == "note":
        try:
            valeur = {"value": int(raw_value)}
        except ValueError:
            return
    else:
        valeur = {"choice": raw_value}

    await svc.store_reponse(str(q["id"]), objectif_id, valeur, today)
    next_index = q_index + 1

    session = await svc.get_slack_session_by_thread(thread_ts)
    if session:
        await svc.advance_slack_session(session["id"], next_index)

    await _post_next_question(objectif_id, questions, next_index, channel, thread_ts)


async def _post_next_question(
    objectif_id: str,
    questions: list,
    next_index: int,
    channel: str,
    thread_ts: str,
) -> None:
    """Poste la prochaine question ou le message de complétion."""
    today = date.today()

    if next_index >= len(questions):
        if await svc.is_objectif_complete(objectif_id, today):
            await post_text(
                channel=channel,
                text="✅ Objectif complété ! Merci pour tes réponses.",
                thread_ts=thread_ts,
            )
        else:
            await post_text(
                channel=channel,
                text=f"✅ Réponses enregistrées. Complète le reste sur {settings.ASSISTANT_BASE_URL}/journal/fill/{objectif_id}",
                thread_ts=thread_ts,
            )
        return

    q = questions[next_index]
    blocks = _question_blocks(q, objectif_id, next_index)
    hint = _question_hint(q)
    await post_blocks(
        channel=channel,
        blocks=blocks,
        text=q["texte"],
        thread_ts=thread_ts,
        mrkdwn=hint,
    )
