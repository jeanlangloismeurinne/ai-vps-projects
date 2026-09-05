"""Index Postgres de la base de connaissance — détenteur unique de `journal_kb_entries`.

Le Markdown du vault est le pivot ; cette table en est un **index dérivé**, reconstructible. Elle a
désormais **deux producteurs** : l'ingestion d'une note libre dans `#journal`
(`handlers/journal_kb.py`) et l'outil `capture_note` de l'agent conversationnel.

D'où ce module. Recopier l'UPSERT du côté de l'agent aurait produit deux écritures de forme
différente dans la même table — et le défaut ne se serait vu qu'à la lecture, une fois les deux
formes mélangées. Une colonne ajoutée ici profite aux deux producteurs ou à aucun.

Ordre d'écriture normatif, inchangé : **Markdown d'abord, Postgres ensuite.** Si l'UPSERT échoue,
la note existe sur disque et l'index est reconstructible ; l'inverse ne serait pas vrai. Les
appelants signalent donc un échec d'index sans le confondre avec une perte de note.
"""
from __future__ import annotations

import hashlib

from app.db import get_pool


def content_hash(body: str) -> str:
    """Hash du verbatim — clef de déduplication. Le body est hashé tel quel : deux notes
    identiques au caractère près sont le même contenu, une reformulation ne l'est pas."""
    return hashlib.sha256((body or "").encode("utf-8")).hexdigest()


async def find_duplicate(hash_: str) -> str | None:
    """Renvoie le `uri` de l'entrée existante ayant ce hash, ou None."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT uri FROM journal_kb_entries WHERE content_hash = $1 LIMIT 1",
            hash_,
        )


async def upsert(
    *,
    doc_id: str,
    uri: str,
    title: str,
    body: str,
    contexte: str | None,
    nature: list[str] | None,
    tags: list[str] | None,
    hash_: str,
    slack_ts: str | None,
) -> None:
    """Écrit (ou réécrit) l'entrée d'index correspondant à un fichier du vault.

    Clef : `doc_id`, qui porte le namespace du producteur (`journal/…`, `notes/…`) — deux
    producteurs ne peuvent donc pas se collisionner sur la même ligne.
    """
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
            doc_id,
            uri,
            title,
            body,
            contexte,
            list(nature or []),
            list(tags or []),
            hash_,
            slack_ts,
        )
