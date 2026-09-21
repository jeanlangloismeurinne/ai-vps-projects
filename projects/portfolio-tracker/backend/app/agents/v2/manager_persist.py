"""Persistance du MANDAT du manager et de son cycle de vie (chantier v3, lot 4 — migration 043).

ARBITRAGE UTILISATEUR (2026-09-21) — CE QU'ON PERSISTE, ET CE QU'ON RECALCULE
----------------------------------------------------------------------------
L'avis du manager (les 4 contrôles + acquitté/renvoyé) NE SE PERSISTE PAS : il se RECALCULE à la
lecture en rejouant `reviser_framework` (la fonction de production) contre le corpus tel qu'il est
MAINTENANT — exactement comme la porte de complétude (#54) et l'actualité (#53). Un avis figé à
l'écriture ne peut pas signaler qu'il a vieilli : il validerait un dossier dont une source a été
supersédée depuis (la cause n°2 du #50). SEUL l'effet durable d'un renvoi — le MANDAT de recherche
— est archivé, parce que lui a une existence propre : le collecteur doit pouvoir le consommer, et
T8 exige que son statut change au re-run.

Le `ManagerVerdict` complet (avec `mandat_de_recherche_id`) s'ASSEMBLE néanmoins — `assemble_verdict`
— quand le mandat a reçu son id : c'est ce que l'agent ne pouvait pas fournir (il rend une
`Decision`). On l'assemble à la lecture pour servir/afficher, jamais pour le stocker.

⚠️ ATOMICITÉ EXPLICITE (#35). `get_db_session()` n'ouvre aucune transaction. `persist_review` écrit
N mandats liés à une même revue : l'appelant DOIT l'envelopper dans `async with conn.transaction():`.

⚠️ NOMMAGE. Le contrat `FrameworkMandate` appelle le cycle de vie `etat` ; la colonne 039 s'appelle
`statut` (et l'index partiel `idx_framework_mandates_ouvert` la lit). On garde le nom de la colonne
et on mappe `etat`↔`statut` ici — deux nomenclatures d'accord restent deux nomenclatures (#46),
comme `framework_answers` garde `rang_degrade`/`ingredients`.

⚠️ VERSION. Le contrat `FrameworkMandate` ne porte pas `framework_version` (il est par-question et
transient), mais la table l'EXIGE : sans elle, un mandat survit à la question qu'il mandatait
(écart V10, même argument que #64 pour `FrameworkAnswer`). Une revue entière est pour UNE version de
framework : `persist_review` la reçoit une fois (`fichier.schema_version`) et l'écrit sur chaque
mandat.

⚠️ IDEMPOTENCE PAR QUESTION, et pourquoi elle DIFFÈRE du collecteur. Un mandat du collecteur est un
fait d'historique DATÉ (deux échecs successifs sur la même ligne sont deux faits distincts, cf.
`collecte_persist`). Un mandat MANAGER est une requête PERMANENTE par question : re-réviser un
framework ne doit pas empiler des mandats ouverts identiques. `persist_review` n'insère donc que si
aucun mandat manager/comité OUVERT n'existe déjà sur `(ticker, framework, version, question)`.
"""
from __future__ import annotations

from typing import Optional

import asyncpg

from app.agents.v2.manager import Decision, ManagerReview
from app.contracts.framework_answer_schema import FrameworkMandate, ManagerVerdict

__all__ = [
    "persist_mandate",
    "persist_review",
    "serve_mandate",
    "read_open_mandates",
    "assemble_verdict",
]

_ORIGINES_MANAGER = ("manager_renvoi", "comite")


async def _mandat_ouvert_existant(
    conn: asyncpg.Connection,
    *,
    ticker_id: str,
    framework_id: str,
    framework_version: str,
    question_id: str,
) -> Optional[int]:
    """L'id d'un mandat manager/comité OUVERT déjà présent sur cette lignée par-question, ou None."""
    return await conn.fetchval(
        "SELECT id FROM framework_mandates "
        "WHERE ticker_id = $1 AND framework_id = $2 AND framework_version = $3 AND question_id = $4 "
        "AND origine IN ('manager_renvoi', 'comite') AND statut = 'ouvert' "
        "ORDER BY id LIMIT 1",
        ticker_id, framework_id, framework_version, question_id)


async def persist_mandate(
    conn: asyncpg.Connection, mandate: FrameworkMandate, *, framework_version: str,
) -> int:
    """Écrit UN mandat manager/comité neuf ('ouvert'), rend son id. À appeler dans une transaction.

    Un mandat manager n'a pas d'ingrédient (par-question) ; `etat` du contrat → colonne `statut`.
    La consommation ne passe PAS par ici — c'est `serve_mandate`."""
    if mandate.etat != "ouvert":
        raise ValueError("persist_mandate n'écrit qu'un mandat neuf 'ouvert' ; la consommation "
                         "passe par serve_mandate (un mandat servi porte déjà sa trace)")
    if mandate.origine not in _ORIGINES_MANAGER:
        raise ValueError(f"persist_mandate est le canal manager/comité ; origine `{mandate.origine}` "
                         "relève du collecteur (`collecte_persist.persist_aiguillage`)")
    return await conn.fetchval(
        "INSERT INTO framework_mandates "
        "(framework_id, framework_version, question_id, ticker_id, motif, mandat, origine, statut) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, 'ouvert') RETURNING id",
        mandate.framework_id, framework_version, mandate.question_id, mandate.ticker_id,
        mandate.motif, mandate.mandat, mandate.origine)


async def persist_review(
    conn: asyncpg.Connection, review: ManagerReview, *, framework_version: str,
) -> dict[str, object]:
    """Persiste les MANDATS d'une revue — renvois de réponses ET questions applicables sans réponse
    (`ManagerReview.mandats()`). Idempotent par question (cf. docstring du module). À appeler dans une
    transaction (#35). Rend `{mandats_ecrits, mandats_deja_ouverts, ids}`."""
    ecrits = deja = 0
    ids: list[int] = []
    for m in review.mandats():
        existant = await _mandat_ouvert_existant(
            conn, ticker_id=m.ticker_id, framework_id=m.framework_id,
            framework_version=framework_version, question_id=m.question_id)
        if existant is not None:
            deja += 1
            ids.append(existant)
            continue
        ids.append(await persist_mandate(conn, m, framework_version=framework_version))
        ecrits += 1
    return {"mandats_ecrits": ecrits, "mandats_deja_ouverts": deja, "ids": ids}


async def serve_mandate(
    conn: asyncpg.Connection,
    mandate_id: int,
    *,
    statut_avant: str,
    statut_apres: str,
    entry_ids_produits: list[int],
) -> bool:
    """Le collecteur a consommé le mandat : 'ouvert' → 'servi', avec l'avant/après du statut de la
    réponse et les entries produites (T8). Rend True si une ligne a bougé (le WHERE exige 'ouvert' :
    on ne re-sert pas un mandat déjà servi). `statut_apres == statut_avant` est LICITE — une
    recherche qui ne trouve rien laisse la question `non_fondable`, et c'est une information (T8)."""
    res = await conn.execute(
        "UPDATE framework_mandates SET statut = 'servi', statut_avant = $2, statut_apres = $3, "
        "consomme_at = now(), entry_ids_produits = $4 WHERE id = $1 AND statut = 'ouvert'",
        mandate_id, statut_avant, statut_apres, entry_ids_produits)
    return res.endswith(" 1")


async def read_open_mandates(
    conn: asyncpg.Connection, *, ticker_id: str, framework_id: str, framework_version: str,
) -> list[FrameworkMandate]:
    """Les mandats manager/comité OUVERTS d'un émetteur + version — ce que le collecteur rejoue.
    Exclut par construction les mandats du collecteur (origine `inobtenable`/`echec_collecte`) et
    les mandats servis."""
    rows = await conn.fetch(
        "SELECT question_id, ticker_id, motif, mandat, origine FROM framework_mandates "
        "WHERE ticker_id = $1 AND framework_id = $2 AND framework_version = $3 "
        "AND origine IN ('manager_renvoi', 'comite') AND statut = 'ouvert' ORDER BY id",
        ticker_id, framework_id, framework_version)
    return [
        FrameworkMandate(
            framework_id=framework_id, question_id=r["question_id"], ticker_id=r["ticker_id"],
            origine=r["origine"], motif=r["motif"], mandat=r["mandat"], etat="ouvert")
        for r in rows
    ]


def assemble_verdict(decision: Decision, *, mandat_de_recherche_id: Optional[int]) -> ManagerVerdict:
    """Assemble le `ManagerVerdict` COMPLET depuis la `Decision` de l'agent et l'id du mandat persisté
    — le maillon que l'agent ne pouvait pas fournir (il rend une `Decision`, pas un verdict). NON
    persisté (arbitrage : l'avis se recalcule) : assemblé à la lecture pour servir/afficher.

    Un acquittement n'a pas de mandat ; un renvoi en exige un (le contrat le REDIT dans
    `_un_renvoi_produit_quelque_chose`, donc appeler ceci avec `mandat_de_recherche_id=None` sur un
    renvoi lève — c'est voulu : un renvoi sans mandat est l'Écart B)."""
    return ManagerVerdict(
        verdict=decision.verdict,
        controles=decision.controles,
        motif=decision.motif,
        mandat_de_recherche_id=mandat_de_recherche_id if decision.verdict == "renvoye" else None,
    )
