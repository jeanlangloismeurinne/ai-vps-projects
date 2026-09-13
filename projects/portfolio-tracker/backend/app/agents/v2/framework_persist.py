"""Persistance de la RÉPONSE et de la DISPENSE (chantier v3, lot 3 maillon 2 — migration 040).

L'ANALYSTE (`agents/v2/analyste.py`) et le pont (`agents/v2/frameworks.py:valider_pont_framework_answer`)
ont déjà jugé l'objet ; ici on l'écrit, sans re-juger. Deux destinations :
  · `framework_answers` — append-only + versionnée (A1, comme `knowledge_entries`, migration 024) :
    une réponse corrigée ne se met pas à jour, elle SUPERSÈDE. La lignée qui décide de ce qu'une
    nouvelle ligne remplace est `(ticker_id, framework, framework_version, question_id, analyste)` —
    PAS sans `analyste` : deux analystes distincts (§3.4, N ≥ 1) ne se supersèdent jamais l'un
    l'autre, seule une correction du MÊME analyste ferme la ligne précédente ;
  · `framework_dispenses` — remplace `DECLARED_NONBLOCKING_GAPS` (dict codé en dur). Idempotente par
    construction (`ON CONFLICT ... DO UPDATE`) : redéclarer la même dispense en met à jour le motif,
    jamais n'en duplique la ligne.

⚠️ ATOMICITÉ EXPLICITE (#35). `get_db_session()` n'ouvre AUCUNE transaction : chaque `execute` part
en autocommit. `persist_answer` fait DEUX écritures liées (l'INSERT neuf, puis l'UPDATE qui ferme
l'ancienne ligne) : l'appelant DOIT les envelopper dans `async with conn.transaction():`, sinon une
panne entre les deux laisserait deux lignes courantes actives sur la même lignée.
"""
from __future__ import annotations

from typing import Any, Optional

import asyncpg

from app.contracts.framework_answer_schema import COLONNES_DENORMALISEES, FrameworkAnswer

__all__ = ["persist_answer", "persist_dispense"]


def _lire_chemin(answer: FrameworkAnswer, chemin: str) -> Any:
    """Résout un chemin du contrat (`fondation.rang_derive`) sur l'objet. `None` si le bloc que le
    chemin traverse est absent — c'est le cas normal : un `non_fondable` n'a pas de `fondation`."""
    obj: Any = answer
    for part in chemin.split("."):
        if obj is None:
            return None
        obj = getattr(obj, part)
    return obj


async def persist_answer(conn: asyncpg.Connection, answer: FrameworkAnswer) -> int:
    """Écrit une réponse, supersède l'éventuelle ligne courante de la MÊME lignée. Rend l'`id` neuf.

    À appeler DANS une transaction (#35). Les colonnes dénormalisées sont lues par le CHEMIN DU
    CONTRAT (`COLONNES_DENORMALISEES`, détenteur unique, #46) — jamais recopiées ici : le jour où
    le contrat gagne un bloc, cette fonction n'a rien à savoir de son existence.
    """
    valeurs = {colonne: _lire_chemin(answer, chemin)
               for colonne, chemin in COLONNES_DENORMALISEES.items()}

    ancien_id = await conn.fetchval(
        "SELECT id FROM framework_answers "
        "WHERE ticker_id = $1 AND framework = $2 AND framework_version = $3 "
        "AND question_id = $4 AND analyste = $5 AND superseded_by IS NULL",
        valeurs["ticker_id"], valeurs["framework"], answer.framework_version,
        valeurs["question_id"], valeurs["analyste"])

    nouveau_id = await conn.fetchval(
        "INSERT INTO framework_answers "
        "(framework, framework_version, question_id, ticker_id, analyste, statut, answer_json, "
        " cited_entry_ids, rang_degrade, methode_approximation, ingredients, motif) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12) RETURNING id",
        valeurs["framework"], answer.framework_version, valeurs["question_id"],
        valeurs["ticker_id"], valeurs["analyste"], valeurs["statut"],
        answer.model_dump(mode="json"), valeurs["cited_entry_ids"], valeurs["rang_degrade"],
        valeurs["methode_approximation"], valeurs["ingredients"], valeurs["motif"])

    if ancien_id is not None:
        await conn.execute(
            "UPDATE framework_answers SET superseded_by = $1 WHERE id = $2",
            nouveau_id, ancien_id)

    return nouveau_id


async def persist_dispense(
    conn: asyncpg.Connection,
    *,
    ticker_id: str,
    framework_id: str,
    framework_version: str,
    question_id: str,
    motif: str,
) -> None:
    """Écrit une dispense — remplace `DECLARED_NONBLOCKING_GAPS`. Idempotente : redéclarer la même
    dispense met à jour son motif plutôt que de dupliquer la ligne."""
    await conn.execute(
        "INSERT INTO framework_dispenses "
        "(ticker_id, framework_id, framework_version, question_id, motif) "
        "VALUES ($1, $2, $3, $4, $5) "
        "ON CONFLICT (ticker_id, framework_id, framework_version, question_id) "
        "DO UPDATE SET motif = EXCLUDED.motif",
        ticker_id, framework_id, framework_version, question_id, motif)
