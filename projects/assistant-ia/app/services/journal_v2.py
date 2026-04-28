import json
import logging
from datetime import date, datetime, time
import pytz
from app.db import get_pool

logger = logging.getLogger(__name__)
_paris = pytz.timezone("Europe/Paris")

# ── Parcours ──────────────────────────────────────────────────────────────────

async def list_parcours() -> list:
    pool = await get_pool()
    return await pool.fetch(
        "SELECT * FROM journal_parcours ORDER BY sort_order, created_at"
    )

async def get_parcours(id: str):
    pool = await get_pool()
    return await pool.fetchrow("SELECT * FROM journal_parcours WHERE id = $1", id)

async def create_parcours(nom: str, description: str) -> str:
    pool = await get_pool()
    row = await pool.fetchrow(
        "INSERT INTO journal_parcours (nom, description) VALUES ($1, $2) RETURNING id",
        nom, description or None,
    )
    return str(row["id"])

async def update_parcours(id: str, nom: str, description: str) -> None:
    pool = await get_pool()
    await pool.execute(
        "UPDATE journal_parcours SET nom=$1, description=$2 WHERE id=$3",
        nom, description or None, id,
    )

async def toggle_parcours(id: str, is_active: bool) -> None:
    pool = await get_pool()
    await pool.execute(
        "UPDATE journal_parcours SET is_active=$1 WHERE id=$2", is_active, id
    )

async def delete_parcours(id: str) -> None:
    pool = await get_pool()
    await pool.execute("DELETE FROM journal_parcours WHERE id=$1", id)

# ── Objectifs ─────────────────────────────────────────────────────────────────

async def list_objectifs(parcours_id: str) -> list:
    pool = await get_pool()
    return await pool.fetch(
        "SELECT * FROM journal_objectifs WHERE parcours_id=$1 ORDER BY sort_order, created_at",
        parcours_id,
    )

async def get_objectif(id: str):
    pool = await get_pool()
    return await pool.fetchrow("SELECT * FROM journal_objectifs WHERE id=$1", id)

async def create_objectif(
    parcours_id: str, nom: str, description: str,
    frequence: str, jours: list, heure_rappel: str,
) -> str:
    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO journal_objectifs
           (parcours_id, nom, description, frequence, jours, heure_rappel)
           VALUES ($1,$2,$3,$4,$5,$6) RETURNING id""",
        parcours_id, nom, description or None,
        frequence, json.dumps(jours), time.fromisoformat(heure_rappel),
    )
    return str(row["id"])

async def update_objectif(
    id: str, nom: str, description: str,
    frequence: str, jours: list, heure_rappel: str,
) -> None:
    pool = await get_pool()
    await pool.execute(
        """UPDATE journal_objectifs
           SET nom=$1, description=$2, frequence=$3, jours=$4, heure_rappel=$5
           WHERE id=$6""",
        nom, description or None, frequence, json.dumps(jours), time.fromisoformat(heure_rappel), id,
    )

async def toggle_objectif(id: str, is_active: bool) -> None:
    pool = await get_pool()
    await pool.execute(
        "UPDATE journal_objectifs SET is_active=$1 WHERE id=$2", is_active, id
    )

async def delete_objectif(id: str) -> None:
    pool = await get_pool()
    await pool.execute("DELETE FROM journal_objectifs WHERE id=$1", id)

async def get_all_active_objectifs() -> list:
    pool = await get_pool()
    return await pool.fetch(
        """SELECT o.*, p.nom as parcours_nom
           FROM journal_objectifs o
           JOIN journal_parcours p ON p.id = o.parcours_id
           WHERE o.is_active = true AND p.is_active = true
           ORDER BY o.heure_rappel"""
    )

# ── Questions ─────────────────────────────────────────────────────────────────

async def list_questions(objectif_id: str, include_deprecated: bool = False) -> list:
    pool = await get_pool()
    if include_deprecated:
        return await pool.fetch(
            "SELECT * FROM journal_questions WHERE objectif_id=$1 ORDER BY sort_order, created_at",
            objectif_id,
        )
    return await pool.fetch(
        """SELECT * FROM journal_questions
           WHERE objectif_id=$1 AND deprecated_at IS NULL
           ORDER BY sort_order, created_at""",
        objectif_id,
    )

async def list_active_questions(objectif_id: str) -> list:
    pool = await get_pool()
    return await pool.fetch(
        """SELECT * FROM journal_questions
           WHERE objectif_id=$1 AND is_active=true AND deprecated_at IS NULL
           ORDER BY sort_order, created_at""",
        objectif_id,
    )

async def get_question(id: str):
    pool = await get_pool()
    return await pool.fetchrow("SELECT * FROM journal_questions WHERE id=$1", id)

async def create_question(
    objectif_id: str, texte: str, type_: str, config: dict
) -> str:
    pool = await get_pool()
    max_order = await pool.fetchval(
        "SELECT COALESCE(MAX(sort_order), -1) FROM journal_questions WHERE objectif_id=$1",
        objectif_id,
    )
    row = await pool.fetchrow(
        """INSERT INTO journal_questions (objectif_id, texte, type, config, sort_order)
           VALUES ($1,$2,$3,$4,$5) RETURNING id""",
        objectif_id, texte, type_, json.dumps(config), (max_order or 0) + 1,
    )
    return str(row["id"])

async def update_question(id: str, texte: str, config: dict, is_active: bool) -> None:
    pool = await get_pool()
    await pool.execute(
        "UPDATE journal_questions SET texte=$1, config=$2, is_active=$3 WHERE id=$4",
        texte, json.dumps(config), is_active, id,
    )

async def deprecate_question(id: str) -> None:
    pool = await get_pool()
    await pool.execute(
        "UPDATE journal_questions SET deprecated_at=now(), is_active=false WHERE id=$1", id
    )

async def move_question(id: str, direction: str) -> None:
    pool = await get_pool()
    q = await pool.fetchrow("SELECT * FROM journal_questions WHERE id=$1", id)
    if not q:
        return
    if direction == "up":
        sibling = await pool.fetchrow(
            """SELECT * FROM journal_questions
               WHERE objectif_id=$1 AND sort_order < $2 AND deprecated_at IS NULL
               ORDER BY sort_order DESC LIMIT 1""",
            q["objectif_id"], q["sort_order"],
        )
    else:
        sibling = await pool.fetchrow(
            """SELECT * FROM journal_questions
               WHERE objectif_id=$1 AND sort_order > $2 AND deprecated_at IS NULL
               ORDER BY sort_order ASC LIMIT 1""",
            q["objectif_id"], q["sort_order"],
        )
    if sibling:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE journal_questions SET sort_order=$1 WHERE id=$2",
                sibling["sort_order"], id,
            )
            await conn.execute(
                "UPDATE journal_questions SET sort_order=$1 WHERE id=$2",
                q["sort_order"], sibling["id"],
            )

# ── Réponses ──────────────────────────────────────────────────────────────────

async def store_reponse(
    question_id: str, objectif_id: str, valeur: dict, session_date: date
) -> None:
    pool = await get_pool()
    await pool.execute(
        """INSERT INTO journal_reponses (question_id, objectif_id, valeur, session_date)
           VALUES ($1,$2,$3,$4)""",
        question_id, objectif_id, json.dumps(valeur), session_date,
    )

async def get_session_answered_ids(objectif_id: str, session_date: date) -> set:
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT question_id FROM journal_reponses WHERE objectif_id=$1 AND session_date=$2",
        objectif_id, session_date,
    )
    return {str(r["question_id"]) for r in rows}

async def is_objectif_complete(objectif_id: str, session_date: date) -> bool:
    questions = await list_active_questions(objectif_id)
    if not questions:
        return True
    answered = await get_session_answered_ids(objectif_id, session_date)
    return all(str(q["id"]) in answered for q in questions)

async def get_reponses(question_id: str, limit: int = 100) -> list:
    pool = await get_pool()
    return await pool.fetch(
        """SELECT r.*, q.texte as question_texte, q.type as question_type, q.config as question_config
           FROM journal_reponses r
           JOIN journal_questions q ON q.id = r.question_id
           WHERE r.question_id=$1
           ORDER BY r.session_date DESC
           LIMIT $2""",
        question_id, limit,
    )

async def get_all_questions_with_stats() -> list:
    pool = await get_pool()
    return await pool.fetch(
        """SELECT q.id, q.texte, q.type, q.config, q.is_active, q.deprecated_at,
                  o.nom as objectif_nom, p.nom as parcours_nom,
                  COUNT(r.id) as nb_reponses,
                  MAX(r.session_date) as last_answered
           FROM journal_questions q
           JOIN journal_objectifs o ON o.id = q.objectif_id
           JOIN journal_parcours p ON p.id = o.parcours_id
           LEFT JOIN journal_reponses r ON r.question_id = q.id
           WHERE q.deprecated_at IS NULL
           GROUP BY q.id, q.texte, q.type, q.config, q.is_active, q.deprecated_at,
                    o.nom, p.nom
           ORDER BY p.nom, o.nom, q.sort_order"""
    )

# ── Notifications ─────────────────────────────────────────────────────────────

async def is_notified_today(objectif_id: str, session_date: date) -> bool:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT 1 FROM journal_notifications WHERE objectif_id=$1 AND session_date=$2",
        objectif_id, session_date,
    )
    return row is not None

async def record_notification(objectif_id: str, session_date: date) -> None:
    pool = await get_pool()
    await pool.execute(
        """INSERT INTO journal_notifications (objectif_id, session_date)
           VALUES ($1,$2) ON CONFLICT DO NOTHING""",
        objectif_id, session_date,
    )

# ── Logique fréquence ─────────────────────────────────────────────────────────

def is_due_today(objectif) -> bool:
    today = date.today()
    freq = objectif["frequence"]
    raw = objectif["jours"]
    jours = raw if isinstance(raw, list) else json.loads(raw or "[]")

    if freq == "daily":
        return True
    if freq == "weekly":
        return today.weekday() in jours  # 0=lundi
    if freq == "monthly":
        return today.day in jours
    return False

async def get_due_objectifs_today() -> list:
    objectifs = await get_all_active_objectifs()
    return [o for o in objectifs if is_due_today(o)]
