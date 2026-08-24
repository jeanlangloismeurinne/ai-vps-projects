"""
Branche 4 du dispatcher Slack : note libre écrite en message parent dans #journal.

Chaîne d'ingestion (#1787559677487) :

    message parent → dédup → classifieur → vault Markdown → index Postgres → accusé en thread

L'ordre d'écriture est normatif : **Markdown d'abord, Postgres ensuite**. Le Markdown est le pivot ;
si l'UPSERT échoue, la note existe toujours sur disque et l'index est reconstructible. L'inverse ne
serait pas vrai.

Ce module tourne dans une tâche de fond (`asyncio.create_task` posé par le dispatcher, contrainte
Slack des 3 s). Une tâche de fond qui meurt est invisible en production : toute exception doit donc
produire un message en thread, jamais seulement une ligne de log.
"""
import hashlib
import logging

from app.config import settings
from app.db import get_pool
from app.services import journal_kb_classifier, journal_vault
from app.services.journal_vault import VaultError
from app.services.slack_client import post_text

logger = logging.getLogger(__name__)


def content_hash(body: str) -> str:
    """Hash du verbatim — clef de déduplication. Le body est hashé tel quel : deux notes
    identiques au caractère près sont le même contenu, une reformulation ne l'est pas."""
    return hashlib.sha256((body or "").encode("utf-8")).hexdigest()


async def _find_duplicate(hash_: str) -> str | None:
    """Renvoie le `uri` de l'entrée existante ayant ce hash, ou None."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT uri FROM journal_kb_entries WHERE content_hash = $1 LIMIT 1",
            hash_,
        )


async def _upsert_entry(entry: journal_vault.VaultEntry, body: str, hash_: str, result, slack_ts):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO journal_kb_entries
                (doc_id, uri, title, body, contexte, nature, tags, content_hash, slack_ts)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (doc_id) DO UPDATE SET
                uri          = EXCLUDED.uri,
                title        = EXCLUDED.title,
                body         = EXCLUDED.body,
                contexte     = EXCLUDED.contexte,
                nature       = EXCLUDED.nature,
                tags         = EXCLUDED.tags,
                content_hash = EXCLUDED.content_hash,
                slack_ts     = EXCLUDED.slack_ts,
                updated_at   = now()
            """,
            entry.doc_id,
            entry.relative_path,
            result.title,
            body,
            result.contexte,
            list(result.nature or []),
            list(result.tags or []),
            hash_,
            slack_ts,
        )


def _ack_text(result, entry: journal_vault.VaultEntry) -> str:
    """Accusé au format roadmap §3 : `Noté · professionnel · apprentissage · #management`.

    Le fallback du classifieur doit rester visible — l'utilisateur doit savoir que sa note est
    enregistrée mais non catégorisée, sinon il croit la classification acquise.
    """
    if result.is_fallback:
        parts = ["Noté", "à classer"]
    else:
        parts = ["Noté"]
        if result.contexte:
            parts.append(result.contexte)
        parts.extend(result.nature or [])
        parts.extend(f"#{tag}" for tag in (result.tags or []))
    return " · ".join(parts) + f"\n`{entry.relative_path}`"


async def handle_free_note(event: dict) -> None:
    """Ingère une note libre. Ne lève jamais : signale toujours l'issue dans le thread."""
    channel = event.get("channel", settings.JOURNAL_CHANNEL_ID)
    slack_ts = event.get("ts")
    body = event.get("text", "")

    try:
        hash_ = content_hash(body)

        # Dédup avant tout : évite un appel DeepInfra et un fichier orphelin dans le vault.
        existing_uri = await _find_duplicate(hash_)
        if existing_uri:
            logger.info("journal_kb: note déjà présente (hash=%s uri=%s)", hash_[:12], existing_uri)
            await post_text(
                channel=channel,
                text=f"Déjà noté · `{existing_uri}`",
                thread_ts=slack_ts,
            )
            return

        # Le classifieur ne lève jamais : en cas d'échec il renvoie is_fallback=True.
        result = await journal_kb_classifier.classify(body)

        # 1. Pivot Markdown. S'il échoue, on n'insère rien en base et on le dit.
        entry = await journal_vault.write_entry(
            title=result.title,
            body=body,
            contexte=result.contexte,
            nature=result.nature,
            tags=result.tags,
            slack_ts=slack_ts,
        )

        # 2. Index Postgres. Un échec ici ne perd pas la note (elle est sur disque), mais doit
        #    être signalé : l'entrée serait absente des recherches jusqu'à reconstruction.
        try:
            await _upsert_entry(entry, body, hash_, result, slack_ts)
        except Exception:
            logger.exception("journal_kb: UPSERT échoué pour %s", entry.doc_id)
            await post_text(
                channel=channel,
                text=(
                    f"Note enregistrée dans le vault (`{entry.relative_path}`) mais l'indexation "
                    "a échoué — elle n'apparaîtra pas dans les recherches tant que l'index n'est "
                    "pas reconstruit."
                ),
                thread_ts=slack_ts,
            )
            return

        await post_text(channel=channel, text=_ack_text(result, entry), thread_ts=slack_ts)
        logger.info(
            "journal_kb: note ingérée (doc_id=%s contexte=%s nature=%s fallback=%s)",
            entry.doc_id, result.contexte, result.nature, result.is_fallback,
        )

    except VaultError as exc:
        logger.exception("journal_kb: écriture vault impossible")
        await _report_failure(channel, slack_ts, f"écriture impossible dans le vault ({exc})")
    except Exception as exc:
        logger.exception("journal_kb: échec de l'ingestion")
        await _report_failure(channel, slack_ts, f"{type(exc).__name__}: {exc}")


async def _report_failure(channel: str, slack_ts: str | None, detail: str) -> None:
    """Dernier filet. Si même Slack est injoignable, on log — il n'y a plus de canal utile."""
    try:
        await post_text(
            channel=channel,
            text=f"Note *non* enregistrée — {detail}. Le texte est conservé dans ce fil.",
            thread_ts=slack_ts,
        )
    except Exception:
        logger.exception("journal_kb: impossible de signaler l'échec dans Slack")
