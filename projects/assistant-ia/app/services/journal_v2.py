import json
import logging
from datetime import date, datetime, time, timedelta
import pytz
from app.db import get_pool

logger = logging.getLogger(__name__)
_paris = pytz.timezone("Europe/Paris")

# ── Parcours ──────────────────────────────────────────────────────────────────

async def list_parcours() -> list:
    pool = await get_pool()
    return await pool.fetch(
        "SELECT * FROM journal_parcours WHERE archived_at IS NULL ORDER BY sort_order, created_at"
    )

async def list_archived_parcours() -> list:
    pool = await get_pool()
    return await pool.fetch(
        "SELECT * FROM journal_parcours WHERE archived_at IS NOT NULL ORDER BY archived_at DESC"
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

async def archive_parcours(id: str) -> None:
    pool = await get_pool()
    await pool.execute(
        "UPDATE journal_parcours SET archived_at=now(), is_active=false WHERE id=$1", id
    )

async def restore_parcours(id: str) -> None:
    pool = await get_pool()
    await pool.execute("UPDATE journal_parcours SET archived_at=NULL, is_active=true WHERE id=$1", id)

async def delete_parcours(id: str) -> None:
    pool = await get_pool()
    await pool.execute("DELETE FROM journal_parcours WHERE id=$1", id)

# ── Objectifs ─────────────────────────────────────────────────────────────────

async def list_objectifs(parcours_id: str) -> list:
    pool = await get_pool()
    return await pool.fetch(
        "SELECT * FROM journal_objectifs WHERE parcours_id=$1 AND archived_at IS NULL ORDER BY sort_order, created_at",
        parcours_id,
    )

async def list_archived_objectifs(parcours_id: str) -> list:
    pool = await get_pool()
    return await pool.fetch(
        "SELECT * FROM journal_objectifs WHERE parcours_id=$1 AND archived_at IS NOT NULL ORDER BY archived_at DESC",
        parcours_id,
    )

async def get_objectif(id: str):
    pool = await get_pool()
    return await pool.fetchrow("SELECT * FROM journal_objectifs WHERE id=$1", id)

async def create_objectif(
    parcours_id: str, nom: str, description: str,
    frequence: str, jours: list, heure_rappel: str,
    heure_relance: str | None = None,
    recap_actif: bool = False, recap_jour: int = 0, recap_heure: str = "08:00",
) -> str:
    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO journal_objectifs
           (parcours_id, nom, description, frequence, jours, heure_rappel,
            heure_relance, recap_actif, recap_jour, recap_heure)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) RETURNING id""",
        parcours_id, nom, description or None,
        frequence, json.dumps(jours), time.fromisoformat(heure_rappel),
        time.fromisoformat(heure_relance) if heure_relance else None,
        recap_actif, recap_jour, time.fromisoformat(recap_heure),
    )
    return str(row["id"])

async def update_objectif(
    id: str, nom: str, description: str,
    frequence: str, jours: list, heure_rappel: str,
    heure_relance: str | None = None,
    recap_actif: bool = False, recap_jour: int = 0, recap_heure: str = "08:00",
) -> None:
    pool = await get_pool()
    await pool.execute(
        """UPDATE journal_objectifs
           SET nom=$1, description=$2, frequence=$3, jours=$4, heure_rappel=$5,
               heure_relance=$6, recap_actif=$7, recap_jour=$8, recap_heure=$9
           WHERE id=$10""",
        nom, description or None, frequence, json.dumps(jours), time.fromisoformat(heure_rappel),
        time.fromisoformat(heure_relance) if heure_relance else None,
        recap_actif, recap_jour, time.fromisoformat(recap_heure), id,
    )

async def toggle_objectif(id: str, is_active: bool) -> None:
    pool = await get_pool()
    await pool.execute(
        "UPDATE journal_objectifs SET is_active=$1 WHERE id=$2", is_active, id
    )

async def rename_objectif(id: str, nom: str, description: str) -> None:
    pool = await get_pool()
    await pool.execute(
        "UPDATE journal_objectifs SET nom=$1, description=$2 WHERE id=$3",
        nom, description or None, id,
    )

async def archive_objectif(id: str) -> None:
    pool = await get_pool()
    await pool.execute(
        "UPDATE journal_objectifs SET archived_at=now(), is_active=false WHERE id=$1", id
    )

async def restore_objectif(id: str) -> None:
    pool = await get_pool()
    await pool.execute(
        "UPDATE journal_objectifs SET archived_at=NULL, is_active=true WHERE id=$1", id
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
           WHERE o.is_active = true AND o.archived_at IS NULL
             AND p.is_active = true AND p.archived_at IS NULL
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
    objectif_id: str, texte: str, type_: str, config: dict,
    multi_reponses: bool = False,
) -> str:
    pool = await get_pool()
    max_order = await pool.fetchval(
        "SELECT COALESCE(MAX(sort_order), -1) FROM journal_questions WHERE objectif_id=$1",
        objectif_id,
    )
    row = await pool.fetchrow(
        """INSERT INTO journal_questions (objectif_id, texte, type, config, sort_order, multi_reponses)
           VALUES ($1,$2,$3,$4,$5,$6) RETURNING id""",
        objectif_id, texte, type_, json.dumps(config), (max_order or 0) + 1, multi_reponses,
    )
    return str(row["id"])

async def update_question(
    id: str, texte: str, config: dict, is_active: bool,
    multi_reponses: bool = False,
) -> None:
    pool = await get_pool()
    await pool.execute(
        "UPDATE journal_questions SET texte=$1, config=$2, is_active=$3, multi_reponses=$4 WHERE id=$5",
        texte, json.dumps(config), is_active, multi_reponses, id,
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
    question_id: str, objectif_id: str, valeur: dict, session_date: date,
    multi_reponses: bool = False,
) -> None:
    pool = await get_pool()
    if multi_reponses:
        next_index = await pool.fetchval(
            """SELECT COALESCE(MAX(entry_index), -1) + 1
               FROM journal_reponses
               WHERE question_id=$1 AND objectif_id=$2 AND session_date=$3""",
            question_id, objectif_id, session_date,
        )
        await pool.execute(
            """INSERT INTO journal_reponses (question_id, objectif_id, valeur, session_date, entry_index)
               VALUES ($1,$2,$3,$4,$5)""",
            question_id, objectif_id, json.dumps(valeur), session_date, next_index,
        )
    else:
        await pool.execute(
            """INSERT INTO journal_reponses (question_id, objectif_id, valeur, session_date, entry_index)
               VALUES ($1,$2,$3,$4,0)
               ON CONFLICT (question_id, objectif_id, session_date, entry_index)
               DO UPDATE SET valeur=EXCLUDED.valeur, answered_at=now()""",
            question_id, objectif_id, json.dumps(valeur), session_date,
        )

async def get_session_answered_ids(objectif_id: str, session_date: date) -> set:
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT DISTINCT question_id FROM journal_reponses WHERE objectif_id=$1 AND session_date=$2",
        objectif_id, session_date,
    )
    return {str(r["question_id"]) for r in rows}

async def is_objectif_complete(objectif_id: str, session_date: date) -> bool:
    pool = await get_pool()
    required = await pool.fetch(
        """SELECT * FROM journal_questions
           WHERE objectif_id=$1 AND is_active=true AND is_required=true AND deprecated_at IS NULL
           ORDER BY sort_order, created_at""",
        objectif_id,
    )
    if not required:
        return True
    answered = await get_session_answered_ids(objectif_id, session_date)
    return all(str(q["id"]) in answered for q in required)

async def get_session_reponses(objectif_id: str, session_date: date) -> dict:
    """Retourne {question_id: valeur} pour prefill du formulaire (entry_index=0)."""
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT question_id, valeur FROM journal_reponses
           WHERE objectif_id=$1 AND session_date=$2 AND entry_index=0""",
        objectif_id, session_date,
    )
    result = {}
    for r in rows:
        v = r["valeur"]
        result[str(r["question_id"])] = json.loads(v) if isinstance(v, str) else v
    return result

async def get_multi_reponses(question_id: str, objectif_id: str, session_date: date) -> list:
    """Retourne toutes les entrées pour une question multi-réponses."""
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT id, entry_index, valeur, answered_at
           FROM journal_reponses
           WHERE question_id=$1 AND objectif_id=$2 AND session_date=$3
           ORDER BY entry_index""",
        question_id, objectif_id, session_date,
    )
    result = []
    for r in rows:
        v = r["valeur"]
        result.append({
            "id": str(r["id"]),
            "entry_index": r["entry_index"],
            "valeur": json.loads(v) if isinstance(v, str) else v,
        })
    return result

async def delete_reponse(reponse_id: str) -> None:
    pool = await get_pool()
    await pool.execute("DELETE FROM journal_reponses WHERE id=$1", reponse_id)

async def get_questions(objectif_id: str) -> list:
    """Alias de list_active_questions pour usage externe."""
    return await list_active_questions(objectif_id)


async def get_reponses(question_id: str, limit: int = 100) -> list:
    pool = await get_pool()
    return await pool.fetch(
        """SELECT r.*, q.texte as question_texte, q.type as question_type, q.config as question_config
           FROM journal_reponses r
           JOIN journal_questions q ON q.id = r.question_id
           WHERE r.question_id=$1
           ORDER BY r.session_date DESC, r.entry_index ASC
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

async def get_notification_today(objectif_id: str, session_date: date):
    pool = await get_pool()
    return await pool.fetchrow(
        "SELECT * FROM journal_notifications WHERE objectif_id=$1 AND session_date=$2",
        objectif_id, session_date,
    )

async def record_followup(objectif_id: str, session_date: date) -> None:
    pool = await get_pool()
    await pool.execute(
        """UPDATE journal_notifications SET followup_sent_at=now()
           WHERE objectif_id=$1 AND session_date=$2""",
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
    if freq == "weekdays":
        return today.weekday() < 5  # 0=lundi, 4=vendredi
    if freq == "weekly":
        return today.weekday() in jours
    if freq == "monthly":
        return today.day in jours
    return False

async def get_due_objectifs_today() -> list:
    objectifs = await get_all_active_objectifs()
    return [o for o in objectifs if is_due_today(o)]


# ── Sessions Slack ─────────────────────────────────────────────────────────────

async def create_slack_session(
    user_id: str, objectif_id: str, thread_ts: str, session_date: date
) -> None:
    pool = await get_pool()
    await pool.execute(
        """INSERT INTO journal_slack_sessions (user_id, objectif_id, thread_ts, question_index, session_date)
           VALUES ($1,$2,$3,0,$4)
           ON CONFLICT (user_id, objectif_id, session_date)
           DO UPDATE SET thread_ts=EXCLUDED.thread_ts""",
        user_id, objectif_id, thread_ts, session_date,
    )


async def get_slack_session_by_thread(thread_ts: str):
    pool = await get_pool()
    return await pool.fetchrow(
        "SELECT * FROM journal_slack_sessions WHERE thread_ts=$1", thread_ts
    )


async def advance_slack_session(session_id: int, next_index: int) -> None:
    pool = await get_pool()
    await pool.execute(
        "UPDATE journal_slack_sessions SET question_index=$1 WHERE id=$2",
        next_index, session_id,
    )

# ── Récapitulatif hebdomadaire ────────────────────────────────────────────────

async def get_objectifs_recap_dus(weekday: int, heure_str: str) -> list:
    """Objectifs avec recap_actif=TRUE, recap_jour=weekday, recap_heure à l'heure courante (±1 min)."""
    pool = await get_pool()
    return await pool.fetch(
        """SELECT o.*, p.nom as parcours_nom
           FROM journal_objectifs o
           JOIN journal_parcours p ON p.id = o.parcours_id
           WHERE o.recap_actif = TRUE
             AND o.archived_at IS NULL
             AND o.is_active = TRUE
             AND p.is_active = TRUE AND p.archived_at IS NULL
             AND o.recap_jour = $1
             AND to_char(o.recap_heure, 'HH24:MI') = $2""",
        weekday, heure_str,
    )

async def recap_deja_envoye(objectif_id: str, semaine_iso: str) -> bool:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT 1 FROM journal_recap_envois WHERE objectif_id=$1 AND semaine_iso=$2",
        objectif_id, semaine_iso,
    )
    return row is not None

async def marquer_recap_envoye(objectif_id: str, semaine_iso: str) -> None:
    pool = await get_pool()
    await pool.execute(
        """INSERT INTO journal_recap_envois (objectif_id, semaine_iso)
           VALUES ($1,$2) ON CONFLICT DO NOTHING""",
        objectif_id, semaine_iso,
    )

async def get_reponses_semaine(objectif_id: str, semaine_iso: str) -> dict:
    """Retourne {question_texte: [{session_date, valeur, type}]} pour la semaine ISO."""
    pool = await get_pool()
    # Parse semaine_iso "2026-W24" → date range (lundi→dimanche)
    year_str, week_str = semaine_iso.split("-W")
    year, week = int(year_str), int(week_str)
    # ISO week: Monday = day 1
    lundi = datetime.strptime(f"{year}-W{week:02d}-1", "%G-W%V-%u").date()
    dimanche = lundi + timedelta(days=6)

    rows = await pool.fetch(
        """SELECT r.session_date, r.valeur, r.entry_index,
                  q.texte as question_texte, q.type as question_type,
                  q.sort_order as question_sort
           FROM journal_reponses r
           JOIN journal_questions q ON q.id = r.question_id
           WHERE r.objectif_id=$1
             AND r.session_date BETWEEN $2 AND $3
           ORDER BY q.sort_order, r.session_date, r.entry_index""",
        objectif_id, lundi, dimanche,
    )

    result: dict = {}
    for r in rows:
        texte = r["question_texte"]
        if texte not in result:
            result[texte] = []
        v = r["valeur"]
        result[texte].append({
            "session_date": r["session_date"],
            "valeur": json.loads(v) if isinstance(v, str) else v,
            "type": r["question_type"],
        })
    return result
