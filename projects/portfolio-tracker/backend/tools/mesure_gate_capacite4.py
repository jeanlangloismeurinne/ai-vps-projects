"""Ligne de base de la capacité 4 — combien de champs `couvert` deviendraient `couvert_perime`.

POURQUOI CET OUTIL EST VERSIONNÉ, ET POURQUOI IL TOURNE *AVANT* LE LOT
---------------------------------------------------------------------
Le test central de la capacité 4 est un DELTA : « NVDA et MSFT passent de `ready, 0 gap` à
`not_ready` pour cause de **péremption** ». Un delta n'a de sens que si son état de départ a été
*mesuré*, pas *supposé* (`feedback_ligne_de_base_est_une_mesure`). La rédaction initiale de la spec
visait RVMD et se serait vérifiée sur une **fixture non discriminante** — RVMD n'a jamais eu de
rapport `readiness` et sortirait `not_ready` pour lacune de toute façon.

Il est versionné parce qu'il doit être rejoué **à l'identique** après le lot : un mesureur réécrit
entre les deux mesures ne mesure plus rien (`CHANTIER_OUTILLAGE_DEV.md` §27, la version jetable
dans `/tmp`).

CE QU'IL NE FAIT PAS
--------------------
Il n'écrit rien, n'appelle aucun modèle, et ne ré-implémente aucune règle : il importe l'index de
couverture et les planchers de `curator`, les profils de `common`, l'axe de `actualite` (#46). Ce
qu'il ajoute est la seule chose que personne ne fait encore — **croiser** les deux, ce qui est
précisément le travail de la porte. Si ce croisement diverge un jour de celui de la porte, c'est
que la porte a cessé d'être le détenteur unique.

Usage (réseau `coolify` pour la base, sortie internet pour EDGAR) :

    docker run --rm --network coolify -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app \
      --env-file checks/env.checks -e CHECK_DB_URL="$DATABASE_URL" \
      portfolio-backend-image python tools/mesure_gate_capacite4.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any, Optional

import asyncpg

from app.agents.v2.common import FIELD_PROFILES, MVDD_SPEC
from app.agents.v2.curator import _covers_index, _plancher_for, _tier_ge, nonblocking_gaps_for
from app.knowledge.actualite import etat_actualite_entry
from app.knowledge.material_events import (
    MaterialEventLookup, ancre_substantielle, material_anchor_for_ticker,
)

TICKERS = ["NVDA", "MSFT", "RVMD"]

_SQL_ENTRIES = """
    -- `content_structured` est requis : c'est lui qui porte `claims[].cited_entry_ids` et
    -- `source_entry_refs`, d'où une entry sans `source_date` propre hérite sa date.
    SELECT id, ticker_id, entry_type, source_type, source_date, fiscal_period,
           reliability_score, reliability_tier, covers, nature, content_structured
      FROM knowledge_entries
     WHERE superseded_by IS NULL
       AND (ticker_id = $1 OR ticker_id IS NULL)
     ORDER BY id
"""


def _db_url() -> str:
    url = os.environ.get("CHECK_DB_URL") or os.environ.get("DATABASE_URL") or ""
    if not url or url.startswith("postgresql://u:p@h"):
        # L'URL factice de `checks/env.checks` compte comme une absence : une mesure qui tourne
        # contre une base inexistante rendrait un zéro, et un zéro se lit comme un résultat.
        sys.exit("CHECK_DB_URL/DATABASE_URL manquant — la ligne de base se MESURE, "
                 "elle ne se devine pas.")
    return url.replace("+asyncpg", "")


def _note_ancre(brute: MaterialEventLookup, ancre: MaterialEventLookup) -> str:
    """Ce que le filtrage a changé, en une ligne — pour la LECTURE de la mesure.

    Le filtrage lui-même n'est PAS ici : il vit dans `material_events.ancre_substantielle`, que la
    porte appelle aussi (#46). Un jumeau local aurait mesuré une ligne de base que la porte ne
    produit pas — l'erreur exacte que cet outil existe pour éviter."""
    if ancre.status != "found" or ancre.event is None:
        if brute.status == "found":
            return "tous les dépôts récents sont purement formels (item 9.01 seul)"
        return "aucun filtrage possible (pas d'événement)"
    note = f"ancre substantielle = {ancre.event.resume()}"
    if brute.event and ancre.event.accession != brute.event.accession:
        note += f"  ⚠️ ÉCARTÉ car formel : {brute.event.resume()}"
    return note


async def mesurer(conn, ticker_id: str) -> dict[str, Any]:
    rows = [dict(r) for r in await conn.fetch(_SQL_ENTRIES, ticker_id)]
    index = _covers_index(rows)
    par_id = {r["id"]: r for r in rows}
    dispenses = nonblocking_gaps_for(ticker_id)

    brute = await material_anchor_for_ticker(conn, ticker_id)
    ancre = ancre_substantielle(brute)
    note_ancre = _note_ancre(brute, ancre)

    couverts: list[str] = []
    perimes: list[dict[str, Any]] = []
    lacunes: list[str] = []
    dispenses_vues: list[str] = []

    for spec in MVDD_SPEC:
        dim = spec["dimension"]
        for champ in spec["champs_requis"]:
            path = f"{dim}.{champ}"
            if path in dispenses:
                dispenses_vues.append(path)
                continue
            plancher = _plancher_for(dim, champ, spec["tier_plancher"])
            retenues = [i for i, t in index.get(path, []) if _tier_ge(t, plancher)]
            if not retenues:
                lacunes.append(path)
                continue

            profil = FIELD_PROFILES.get(path, {})
            if not profil.get("actualite_bloquante"):
                couverts.append(path)
                continue

            # `etat_actualite_entry` et non `etat_actualite` : une entry sans `source_date` propre
            # HÉRITE de la plus ancienne de ses entries citées (arbitrage du 2026-09-08). Mesurer
            # avec la fonction nue rendrait `indeterminable` là où la porte lira `perimee` — deux
            # états distincts (#53), donc deux lignes de base différentes.
            etats = {eid: etat_actualite_entry(par_id[eid], ancre=ancre, corpus=par_id)
                     for eid in retenues}
            if any(a.etat == "courante" for a in etats.values()):
                couverts.append(path)
            else:
                perimes.append({
                    "champ": path,
                    "entries": {eid: (a.etat, a.jours_avant_evenement) for eid, a in etats.items()},
                })

    return {
        "ticker": ticker_id,
        "entries_courantes": len(rows),
        "ancre_brute": brute.status,
        "note_ancre": note_ancre,
        "couverts": couverts,
        "perimes": perimes,
        "lacunes": lacunes,
        "dispenses": dispenses_vues,
    }


async def main() -> int:
    conn = await asyncpg.connect(_db_url())
    # ⚠️ Le codec JSONB n'est PAS optionnel ici. `asyncpg.connect()` nu rend `content_structured`
    # comme une CHAÎNE, alors que la production passe par `get_db_session()`, qui l'enregistre et
    # rend un dict. Sans lui, `_entries_citees` voyait un `str`, n'y trouvait aucune citation, et
    # l'entry #59 sortait `indeterminable` là où la porte lit `perimee` : l'outil mesurait une
    # ligne de base que le code ne produit pas — une fixture divergente du réel, cette fois par la
    # forme de la connexion et non par le contenu des données.
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
    await conn.set_type_codec("json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
    try:
        resultats = [await mesurer(conn, t) for t in TICKERS]
    finally:
        await conn.close()

    total_bascules = 0
    for r in resultats:
        print(f"\n=== {r['ticker']} — {r['entries_courantes']} entries courantes ===")
        print(f"  ancre EDGAR : {r['ancre_brute']} · {r['note_ancre']}")
        print(f"  couvert            : {len(r['couverts'])}")
        print(f"  couvert_perime     : {len(r['perimes'])}")
        for p in r["perimes"]:
            detail = ", ".join(f"#{i}={e}{'' if j is None else f'/{j}j'}"
                               for i, (e, j) in p["entries"].items())
            print(f"      - {p['champ']}  [{detail}]")
        print(f"  non_couvert        : {len(r['lacunes'])}")
        for c in r["lacunes"]:
            print(f"      - {c}")
        if r["dispenses"]:
            print(f"  dispensés (non bloquants) : {', '.join(r['dispenses'])}")
        total_bascules += len(r["perimes"])

    print(f"\nLIGNE DE BASE — {total_bascules} champ(s) basculeraient couvert → couvert_perime "
          f"sur {len(TICKERS)} émetteurs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
