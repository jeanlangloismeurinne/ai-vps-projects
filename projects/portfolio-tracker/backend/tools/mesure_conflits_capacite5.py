"""Ligne de base de la capacité 5 — ce que la règle d'appariement proposée trouverait, aujourd'hui.

POURQUOI CET OUTIL EXISTE, ET POURQUOI IL TOURNE *AVANT* LE LOT
---------------------------------------------------------------
La capacité 5 (« la contradiction, signalée jamais tranchée ») porte un test d'acceptation nommé :
« sur RVMD, l'entry du communiqué FDA (2026-08-26) et les quatre entries "aucun produit approuvé"
sont mutuellement marquées et remontent dans la file », **et** un test négatif : « deux entries qui
couvrent des champs DIFFÉRENTS ne doivent PAS être appariées ».

La capacité 4 a montré qu'une spec peut désigner le mauvais porteur : elle annonçait RVMD comme
porteur du faux vert, alors que RVMD n'a jamais eu de rapport `readiness`
(`feedback_ligne_de_base_est_une_mesure`). On ne prend donc pas l'énoncé pour argent comptant : on
va **lire dans la base** ce que la règle proposée apparierait réellement.

CE QU'IL MESURE
---------------
1. L'état du levier mort — `has_conflict` / `conflict_entry_id` sur tout le corpus.
2. Les collisions de la clef d'identité **déterministe** (#43), en rejouant `_current_fact_ids`,
   son détenteur unique : y a-t-il encore deux entries courantes répondant à la même question
   chiffrée ? (C'est la seule contradiction qu'on sait détecter sans modèle.)
3. Ce que l'appariement par `covers` proposerait : le nombre de PAIRES candidates, par champ, avec
   la nature et le tier de chaque membre — c'est-à-dire le volume à soumettre à un jugement de
   divergence, donc le coût de la capacité.
4. Le cas d'acceptation nommé par la spec, entry par entry : l'intersection de `covers` entre
   l'entry du communiqué FDA et les entries « aucun produit approuvé ».

CE QU'IL NE FAIT PAS
--------------------
Il n'écrit rien, n'appelle aucun modèle, et ne ré-implémente aucune règle : il importe
`_current_fact_ids` (#43) et `FIELD_PROFILES` (#50). Il ne juge aucune divergence — juger deux
prose l'une contre l'autre est précisément ce que la capacité 5 devra confier à un modèle, et
l'anticiper ici fabriquerait une ligne de base que le code ne produit pas.

Usage : `bash tools/mesure_conflits.sh`
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from itertools import combinations
from typing import Any

import asyncpg

from app.agents.v2.common import FIELD_PROFILES
from app.knowledge.edgar_feed import _current_fact_ids
from tools._corpus_archive import ENTRIES, bandeau

TICKERS = ["NVDA", "MSFT", "RVMD"]

# Le cas d'acceptation nommé par la spec, repéré par ce qu'il DIT et non par son id : un id codé en
# dur se périmerait au premier re-seed, et la mesure sortirait un zéro qui se lirait « rien à
# signaler » (#49).
_MOTIF_APPROBATION = "%approbation FDA%"
_MOTIFS_PERIMES = ("%aucun produit%", "%n'a jamais généré de revenus%",
                   "%approbation non garantie%")

_SQL_ACTIVES = f"""
    SELECT id, ticker_id, entry_type, source_type, source_date, covers, nature,
           reliability_tier, title, content_structured
      FROM {ENTRIES}
     WHERE superseded_by IS NULL AND is_deleted = FALSE AND ticker_id = $1
     ORDER BY id
"""


def _db_url() -> str:
    url = os.environ.get("CHECK_DB_URL") or os.environ.get("DATABASE_URL") or ""
    if not url or url.startswith("postgresql://u:p@h"):
        sys.exit("CHECK_DB_URL/DATABASE_URL manquant — la ligne de base se MESURE, "
                 "elle ne se devine pas.")
    return url.replace("+asyncpg", "")


async def _collisions_deterministes(conn, ticker_id: str, rows: list[dict]) -> dict[str, list]:
    """Deux entries courantes sur la MÊME clef d'identité #43 — la seule contradiction sans modèle.

    On rejoue le détenteur unique (`_current_fact_ids`) au lieu d'écrire un GROUP BY équivalent :
    un jumeau SQL re-divergerait au premier correctif de la règle (#46, et c'est exactement le
    défaut que #43 a corrigé dans `financials_feed`).

    ⚠️ **`poste_kind` ABSENT est un troisième état, jamais un `stock` par défaut** (#44/#53). La
    clef #43 dépend du type de poste — un FLUX s'identifie par `(metric, period_end)`, un STOCK par
    `metric` seul. `_current_fact_ids` le tient de la **spec du producteur**, qui le connaît ; un
    LECTEUR du corpus, lui, ne dispose que de la ligne stockée. La première version de cette mesure
    coerçait l'absence en `stock` et **fabriquait deux collisions** sur NVDA (revenue FY2024/25/26,
    net_income FY2025/26) : trois exercices légitimes lus comme trois réponses à une même question.
    Un rouge fabriqué se paie aussi cher qu'un vert fabriqué. L'indécidable est donc COMPTÉ À PART
    et nommé — c'est le résultat le plus important de cette mesure, pas son bruit de fond.
    """
    vus: set[tuple] = set()
    collisions: list[dict] = []
    indecidables: list[dict] = []
    for r in rows:
        cs = r["content_structured"] or {}
        metric, period_end = cs.get("metric"), cs.get("period_end")
        if r["entry_type"] != "fact_financial" or not metric or not period_end:
            continue
        kind = cs.get("poste_kind")
        if kind not in ("flow", "stock"):
            indecidables.append({"id": r["id"], "metric": metric, "period_end": period_end})
            continue
        clef = (r["source_type"], metric, period_end if kind == "flow" else "<stock>")
        if clef in vus:
            continue
        vus.add(clef)
        ids = await _current_fact_ids(conn, ticker_id, metric, period_end, flow=kind == "flow")
        if len(ids) > 1:
            collisions.append({"clef": clef, "ids": sorted(ids)})
    return {"collisions": collisions, "indecidables": indecidables}


def _paires_par_covers(rows: list[dict]) -> dict[str, list[tuple[int, int]]]:
    """Ce que la règle « même `covers` » soumettrait à un jugement de divergence."""
    index: dict[str, list[int]] = {}
    for r in rows:
        for champ in r["covers"] or []:
            index.setdefault(champ, []).append(r["id"])
    return {c: list(combinations(ids, 2)) for c, ids in index.items() if len(ids) > 1}


def _cas_acceptation(rows: list[dict]) -> dict[str, Any]:
    par_id = {r["id"]: r for r in rows}

    def _cherche(motifs: tuple[str, ...]) -> list[int]:
        trouves = []
        for r in rows:
            texte = f"{r['title'] or ''}\n{r.get('content') or ''}".lower()
            if any(m.strip("%").lower() in texte for m in motifs):
                trouves.append(r["id"])
        return trouves

    approbation = _cherche((_MOTIF_APPROBATION,))
    perimees = _cherche(_MOTIFS_PERIMES)
    paires = []
    for a in approbation:
        for p in perimees:
            ca, cp = set(par_id[a]["covers"] or []), set(par_id[p]["covers"] or [])
            paires.append({"approbation": a, "perimee": p,
                           "covers_approbation": sorted(ca), "covers_perimee": sorted(cp),
                           "intersection": sorted(ca & cp)})
    return {"approbation": approbation, "perimees": perimees, "paires": paires}


async def mesurer(conn, ticker_id: str) -> dict[str, Any]:
    rows = [dict(r) for r in await conn.fetch(_SQL_ACTIVES, ticker_id)]
    # `content` n'est pas dans le SELECT (volumineux) : on le charge à part pour le repérage textuel.
    textes = dict(await conn.fetch(
        f"SELECT id, content FROM {ENTRIES} WHERE ticker_id = $1 "
        "AND superseded_by IS NULL AND is_deleted = FALSE", ticker_id))
    for r in rows:
        r["content"] = textes.get(r["id"], "")
    det = await _collisions_deterministes(conn, ticker_id, rows)
    return {
        "ticker": ticker_id,
        "actives": len(rows),
        "collisions": det["collisions"],
        "indecidables": det["indecidables"],
        "paires": _paires_par_covers(rows),
        "acceptation": _cas_acceptation(rows) if ticker_id == "RVMD" else None,
        "par_id": {r["id"]: r for r in rows},
    }


async def main() -> int:
    print(bandeau())
    conn = await asyncpg.connect(_db_url())
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
    await conn.set_type_codec("json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
    try:
        drapeaux = await conn.fetchrow(
            "SELECT count(*) FILTER (WHERE has_conflict) AS flag,"
            "       count(*) FILTER (WHERE conflict_entry_id IS NOT NULL) AS ref,"
            f"       count(*) AS total FROM {ENTRIES}")
        resultats = [await mesurer(conn, t) for t in TICKERS]
    finally:
        await conn.close()

    print("=== 1. Le levier mort, en base ===")
    print(f"  has_conflict = TRUE        : {drapeaux['flag']}")
    print(f"  conflict_entry_id non NULL : {drapeaux['ref']}")
    print(f"  entries totales            : {drapeaux['total']}")

    total_collisions = total_paires = total_indecidables = total_faits = 0
    for r in resultats:
        print(f"\n=== 2/3. {r['ticker']} — {r['actives']} entries courantes ===")
        print(f"  collisions clef d'identité #43 : {len(r['collisions'])}")
        for c in r["collisions"]:
            print(f"      - {c['clef']} → ids {c['ids']}")
        ind = r["indecidables"]
        print(f"  faits NON keyables par un lecteur (`poste_kind` absent) : {len(ind)}")
        if ind:
            print("      " + ", ".join(f"#{x['id']}:{x['metric']}" for x in ind))
        total_indecidables += len(ind)
        n = sum(len(p) for p in r["paires"].values())
        print(f"  paires candidates par `covers` : {n} sur {len(r['paires'])} champ(s)")
        for champ, paires in sorted(r["paires"].items(), key=lambda kv: -len(kv[1])):
            profil = FIELD_PROFILES.get(champ, {})
            membres = sorted({i for p in paires for i in p})
            detail = ", ".join(
                f"#{i}({r['par_id'][i]['nature'][:3]}/{r['par_id'][i]['reliability_tier']})"
                for i in membres)
            print(f"      - {champ:<42} {len(paires):>2} paires  "
                  f"[nature dominante={profil.get('nature', '?')}] {detail}")
        total_collisions += len(r["collisions"])
        total_paires += n

    print("\n=== 4. Le cas d'acceptation nommé par la spec (RVMD) ===")
    acc = next(r["acceptation"] for r in resultats if r["ticker"] == "RVMD")
    print(f"  entry(ies) « approbation FDA »        : {acc['approbation']}")
    print(f"  entry(ies) « aucun produit approuvé » : {acc['perimees']}")
    apparies = [p for p in acc["paires"] if p["intersection"]]
    for p in acc["paires"]:
        verdict = "APPARIÉE" if p["intersection"] else "NON appariée (covers disjoints)"
        print(f"      #{p['approbation']} vs #{p['perimee']} → {verdict}")
        print(f"          covers #{p['approbation']} = {p['covers_approbation']}")
        print(f"          covers #{p['perimee']} = {p['covers_perimee']}")
    print(f"  → {len(apparies)} paire(s) sur {len(acc['paires'])} seraient appariées "
          f"par la règle `covers`.")

    print(f"\nLIGNE DE BASE — {drapeaux['flag']} entry marquée en conflit · "
          f"{total_collisions} collision(s) déterministe(s) · "
          f"{total_indecidables} fait(s) non keyable(s) par un lecteur · "
          f"{total_paires} paires candidates par `covers` · "
          f"{len(apparies)} paire(s) du cas d'acceptation effectivement appariée(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
