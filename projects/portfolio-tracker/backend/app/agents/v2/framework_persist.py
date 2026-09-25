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

from datetime import date
from typing import Any, Optional

import asyncpg

from app.contracts.framework_answer_schema import COLONNES_DENORMALISEES, FrameworkAnswer

__all__ = ["persist_answer", "persist_archetype", "persist_dispense",
           "read_answers_courantes", "read_archetype", "read_dispenses"]


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


async def read_answers_courantes(
    conn: asyncpg.Connection,
    *,
    ticker_id: str,
    framework_version: str,
) -> list[tuple[int, FrameworkAnswer]]:
    """Les réponses COURANTES d'un émetteur, pour une version de référentiel. Rend `(id, réponse)`.

    « Courante » = `superseded_by IS NULL`, et cette sélection appartient à la table : la lignée est
    fermée par `persist_answer`, pas re-déduite par le lecteur. La refaire côté appelant en ferait
    un jumeau, divergent le jour où la règle de supersession changera (#46).

    `framework_version` est un paramètre REQUIS, jamais un filtre optionnel : sans lui, le lecteur
    rendrait aussi les réponses écrites contre un énoncé qui a changé, et le projecteur les
    publierait comme si elles répondaient à la question actuelle (écart V10). Un appelant qui veut
    « tout » doit le dire version par version, donc savoir qu'il le fait.

    `answer_json` est de type JSONB : asyncpg le décode déjà. Le revalider par le contrat n'est pas
    redondant — une ligne écrite par une version antérieure du contrat doit LEVER ici, pas se
    charger à moitié.
    """
    rows = await conn.fetch(
        "SELECT id, answer_json FROM framework_answers "
        "WHERE ticker_id = $1 AND framework_version = $2 AND superseded_by IS NULL "
        "ORDER BY id",
        ticker_id, framework_version)
    return [(row["id"], FrameworkAnswer.model_validate(row["answer_json"])) for row in rows]


async def read_archetype(
    conn: asyncpg.Connection,
    *,
    ticker_id: str,
    a_la_date: Optional[date] = None,
) -> Optional[tuple[str, str]]:
    """L'archétype EN VIGUEUR d'un émetteur (migration 046). Rend `(archetype, motif)` ou `None`.

    `None` = **l'émetteur n'est pas classé**, et c'est un troisième état, pas un défaut de lecture :
    il se distingue de « classé rentable » comme de « classé pré-revenus ». Retomber sur un
    archétype par défaut ferait répondre des questions hors-sujet et fabriquerait exactement le
    défaut T4 / entry #190 (un ROIC pour une société sans revenus). L'ignorance se DIT (#25/#44).

    « En vigueur » = la date d'effet la plus récente qui ne soit pas dans le futur. `created_at`
    n'entre pas dans le tri : une saisie tardive ne doit pas prendre le pas sur un classement dont
    l'effet est antérieur.

    ⚠️ LE VOCABULAIRE EST CONFRONTÉ À SON DÉTENTEUR, PAS À UN CHECK SQL. Un archétype stocké qui ne
    figure plus dans `frameworks.yaml` LÈVE : sauté, il rendrait `None` et l'émetteur paraîtrait
    non classé alors qu'il l'est — un contrôle qui dégrade en sortant à zéro est un vert
    (`feedback_check_degrade_en_sortant_a_zero`).
    """
    row = await conn.fetchrow(
        "SELECT archetype, motif FROM ticker_archetypes "
        "WHERE ticker_id = $1 AND effective_from <= $2 "
        "ORDER BY effective_from DESC LIMIT 1",
        ticker_id, a_la_date or date.today())
    if row is None:
        return None

    # Import local : `framework_persist` est importé par des checks sans référentiel monté.
    from app.agents.v2.frameworks import FrameworkDefinitionRefused, load_frameworks

    declares = load_frameworks().archetypes
    if row["archetype"] not in declares:
        raise FrameworkDefinitionRefused(
            f"`{ticker_id}` est classé `{row['archetype']}`, qui n'est plus un archétype déclaré "
            f"({sorted(declares)}) — un classement périmé rendrait hors-sujet des questions qui "
            "s'appliquent, et le manager acquitterait des `sans_objet` fabriqués")
    return row["archetype"], row["motif"]


async def persist_archetype(
    conn: asyncpg.Connection,
    *,
    ticker_id: str,
    archetype: str,
    motif: str,
    effective_from: Optional[date] = None,
) -> int:
    """Classe un émetteur à une date d'effet. APPEND-ONLY : ne met jamais à jour la ligne courante.

    Un reclassement est un FAIT DATÉ (« la société est devenue rentable au T3 »), pas une
    correction : l'écraser perdrait la raison pour laquelle les notes antérieures posaient d'autres
    questions. C'est l'arbitrage du 2026-09-22 — on n'écrase pas, on empile.

    Rejouer le MÊME jour d'effet met à jour le classement de ce jour (`ON CONFLICT`) : c'est une
    correction de saisie, pas un empilement, et l'index unique la rend explicite.
    """
    return await conn.fetchval(
        "INSERT INTO ticker_archetypes (ticker_id, archetype, effective_from, motif) "
        "VALUES ($1, $2, $3, $4) "
        "ON CONFLICT (ticker_id, effective_from) "
        "DO UPDATE SET archetype = EXCLUDED.archetype, motif = EXCLUDED.motif "
        "RETURNING id",
        ticker_id, archetype, effective_from or date.today(), motif)


async def read_dispenses(
    conn: asyncpg.Connection,
    *,
    ticker_id: str,
    framework_id: str,
    framework_version: str,
) -> dict[str, str]:
    """Dispenses actives pour un émetteur + version de framework donnés.

    Rend `{question_id: motif}` — même forme que l'ancienne `nonblocking_gaps_for`, mais keyé
    par question_id (not MVDD field path). Consommé par le manager en lot 4."""
    rows = await conn.fetch(
        "SELECT question_id, motif FROM framework_dispenses "
        "WHERE ticker_id = $1 AND framework_id = $2 AND framework_version = $3",
        ticker_id, framework_id, framework_version)
    return {row["question_id"]: row["motif"] for row in rows}


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
