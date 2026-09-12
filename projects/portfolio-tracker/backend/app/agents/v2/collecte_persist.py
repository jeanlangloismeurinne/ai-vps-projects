"""Persistance de la CHAÎNE DE COLLECTE (chantier v3, lot 2c — migration 039).

Le plan (traducteur), les liens de couverture et les mandats (aiguilleur) sont des OBJETS déjà
validés ; ici on les écrit, sans re-juger. Trois destinations :
  · `collection_plans` + `collection_plan_items` — le plan, DATÉ et relisable (« mauvais plan ou
    mauvaise collecte ? » n'est décidable que si le plan est persisté, §3.6) ;
  · `question_coverage` (migration 036) — un lien par ingrédient couvert ;
  · `framework_mandates` (migration 039) — un mandat par ingrédient non rangé, NOMMÉ.

⚠️ ATOMICITÉ EXPLICITE (#35). `get_db_session()` n'ouvre AUCUNE transaction : chaque `execute` part
en autocommit. Ces fonctions prennent donc une `conn` et l'appelant DOIT les envelopper dans
`async with conn.transaction():` — sinon une panne au milieu laisse un plan sans ses lignes, ou des
liens sans leurs mandats. La couverture est un sous-produit déterministe (#58) : on l'écrit avec ses
mandats dans la même transaction, jamais l'un sans l'autre.
"""
from __future__ import annotations

from typing import Any, Optional

import asyncpg

from app.agents.v2.collecteur import ResultatAiguillage
from app.contracts.collection_plan_schema import CollectionPlan

__all__ = ["persist_plan", "persist_aiguillage"]


async def persist_plan(conn: asyncpg.Connection, plan: CollectionPlan) -> int:
    """Écrit le plan + ses lignes, rend l'`id` du plan. À appeler DANS une transaction (#35)."""
    plan_id = await conn.fetchval(
        "INSERT INTO collection_plans (ticker_id, framework_id, framework_version, archetype) "
        "VALUES ($1, $2, $3, $4) RETURNING id",
        plan.ticker_id, plan.framework_id, plan.framework_version, plan.archetype)
    for it in plan.items:
        await conn.execute(
            "INSERT INTO collection_plan_items "
            "(plan_id, question_id, ingredient_id, statut, metrique, source_pressentie, ancre, motif) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
            plan_id, it.question_id, it.ingredient_id, it.statut,
            it.metrique, it.source_pressentie, it.ancre, it.motif)
    return plan_id


async def persist_aiguillage(
    conn: asyncpg.Connection,
    result: ResultatAiguillage,
    *,
    plan_id: Optional[int] = None,
) -> dict[str, Any]:
    """Écrit les liens de couverture ET les mandats — ensemble, dans la même transaction (#35/#58).

    `question_coverage` en `ON CONFLICT DO NOTHING` : le même fait peut couvrir un ingrédient déjà
    couvert (rejeu idempotent), ce n'est pas une erreur. Un mandat, lui, est daté : on n'en dédoublonne
    pas ici (deux échecs successifs sur la même ligne sont deux faits d'historique distincts).
    """
    for lien in result.liens:
        await conn.execute(
            "INSERT INTO question_coverage "
            "(framework_id, framework_version, question_id, ingredient_id, entry_id) "
            "VALUES ($1, $2, $3, $4, $5) ON CONFLICT DO NOTHING",
            lien.framework_id, lien.framework_version, lien.question_id,
            lien.ingredient_id, lien.entry_id)
    for m in result.mandats:
        await conn.execute(
            "INSERT INTO framework_mandates "
            "(framework_id, framework_version, question_id, ingredient_id, motif, origine, plan_id) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7)",
            m.framework_id, m.framework_version, m.question_id, m.ingredient_id,
            m.motif, m.origine, plan_id)
    return {"liens_ecrits": len(result.liens), "mandats_ecrits": len(result.mandats)}
