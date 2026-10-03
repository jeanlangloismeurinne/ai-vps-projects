"""Rattache à leur point les pièces SŒURS restées orphelines avant #106 — à blanc par défaut.

POURQUOI CET OUTIL EXISTE (mesuré le 2026-10-03)
-------------------------------------------------
Avant #106, une ligne de collecte web n'écrivait qu'UN lien de couverture, vers la première entry
rendue par le chercheur, même quand il en rapportait plusieurs sur le même point. Les autres étaient
bien écrites en base, mais rattachées à rien : le dossier les rangeait « hors index », triées par la
seule date, et le plafond les coupait ou les gardait au hasard du calendrier. Exemple qui a fait
rechercher la classe : RVMD `qf_6.politique_de_capitalisation` cite le 10-K #716 (clos 2025-12-31) ;
le 10-Q #717 (clos 2026-06-30) qui le CONFIRME, écrit dans la même réponse, est orphelin — et la
réponse #985 naît périmée faute de le voir. Mesuré sur la base : 76 orphelines (RVMD, NVDA, MSFT).

#106 corrige la collecte pour l'avenir ; cet outil rejoue la même règle sur le passé, SANS MODÈLE.
La preuve d'appartenance est la TRACE, pas un jugement : les entries d'une même réponse du chercheur
sont écrites dans UNE transaction (`collecte_executor.collecter_un`), donc portent le MÊME
`created_at` ; une orpheline qui partage l'horodatage (et le titre) d'une pièce rattachée vient de
la même réponse, donc du même point.

GARDES (chacune mesurée nulle le 2026-10-03, et revérifiée ici à chaque passage)
  · un horodatage qui désigne PLUSIEURS ingrédients est AMBIGU : rien n'est rattaché, il est listé ;
  · une entry du socle EDGAR ou d'un appariement (tags `edgar` / `appariement`) n'est jamais une
    sœur : ces producteurs écrivent plusieurs POSTES par transaction, et l'horodatage ne dit plus
    rien du point ;
  · seules les entries courantes (`superseded_by IS NULL`) sont rattachées.

CE QUE LE RATTACHEMENT CHANGE — À LIRE AVANT `--ecrire`
  Le dossier élit la pièce la plus récente d'une chemise et la remet AVEC ses sœurs (#107). Une sœur
  plus récente devient donc l'élue ; une pièce remise avant et plus après est une pièce d'une
  collecte PRÉCÉDENTE qui passe en antérieure (signalée). L'outil imprime, chemise par chemise, les pièces remises avant/après : c'est la frontière gratuite
  (`feedback_frontiere_gratuite_avant_depense_modele`).

    bash tools/rattacher_soeurs.sh            # à blanc : liste, ambiguïtés, en-vigueur avant/après
    bash tools/rattacher_soeurs.sh --ecrire   # écrit les liens (une transaction, idempotent)

Codes : 0 = mesure dressée (et liens écrits si demandé) · 2 = pas mesurable.
"""
from __future__ import annotations

import asyncio
import os
import sys
from collections import defaultdict

from app.agents.v2.dossier import _SQL_ENTRIES, assembler_dossier
from app.db.database import close_pool, get_db_session, init_pool

_SQL_SOEURS = """
WITH liee AS (
    SELECT DISTINCT qc.framework_id, qc.framework_version, qc.question_id, qc.ingredient_id,
           e.created_at, e.ticker_id
      FROM question_coverage qc JOIN knowledge_entries e ON e.id = qc.entry_id
)
SELECT o.id, o.ticker_id, o.created_at, l.framework_id, l.framework_version, l.question_id,
       l.ingredient_id
  FROM knowledge_entries o
  JOIN liee l ON l.created_at = o.created_at AND l.ticker_id = o.ticker_id
 WHERE o.superseded_by IS NULL
   AND NOT ('edgar' = ANY(o.tags)) AND NOT ('appariement' = ANY(o.tags))
   AND NOT EXISTS (SELECT 1 FROM question_coverage q WHERE q.entry_id = o.id)
 ORDER BY o.ticker_id, o.id
"""

_SQL_LIENS_TOUS = """
SELECT qc.question_id, qc.ingredient_id, qc.entry_id
  FROM question_coverage qc
 WHERE qc.framework_id = $1 AND qc.framework_version = $2
"""


async def main() -> int:
    ecrire = "--ecrire" in sys.argv[1:]
    url = os.environ.get("DATABASE_URL") or ""
    if not url:
        print("DATABASE_URL manquante — la mesure n'est pas faisable, elle ne se devine pas.",
              file=sys.stderr)
        return 2
    await init_pool(url)
    try:
        async with get_db_session() as conn:
            rows = [dict(r) for r in await conn.fetch(_SQL_SOEURS)]

            # Ambiguïté : un horodatage qui désigne plus d'un INGRÉDIENT (le même ingrédient sous
            # deux questions est légitime — une ligne aveugle partagée, #106).
            par_ts: dict[tuple, set] = defaultdict(set)
            for r in rows:
                par_ts[(r["ticker_id"], r["created_at"])].add(
                    (r["framework_id"], r["framework_version"], r["ingredient_id"]))
            ambigus = {k for k, v in par_ts.items() if len(v) > 1}
            liens = [r for r in rows if (r["ticker_id"], r["created_at"]) not in ambigus]

            print(f"\nSŒURS ORPHELINES — {len({r['id'] for r in rows})} pièce(s), "
                  f"{len(liens)} lien(s) à écrire, {len(ambigus)} horodatage(s) ambigu(s)\n")
            for k in sorted(ambigus, key=str):
                print(f"  ⚠️ AMBIGU {k[0]} {k[1]} → {sorted(par_ts[k])} : rien n'est rattaché")

            # Avant/après, par (ticker, framework, version) touché — l'assemblage réel, plafond
            # sans effet sur l'élection (il ne coupe jamais une pièce en vigueur).
            groupes: dict[tuple, list] = defaultdict(list)
            for r in liens:
                groupes[(r["ticker_id"], r["framework_id"], r["framework_version"])].append(r)
            changements = 0
            for (ticker, fw, ver), rs in sorted(groupes.items()):
                entries = {e["id"]: dict(e) for e in await conn.fetch(_SQL_ENTRIES, ticker)}
                avant_l = [(x["question_id"], x["ingredient_id"], x["entry_id"])
                           for x in await conn.fetch(_SQL_LIENS_TOUS, fw, ver)]
                apres_l = avant_l + [(r["question_id"], r["ingredient_id"], r["id"]) for r in rs]
                avant = {(c.question_id, c.ingredient_id): c.remises
                         for c in assembler_dossier(entries=entries, liens=avant_l, plafond=40).chemises}
                apres = {(c.question_id, c.ingredient_id): c.remises
                         for c in assembler_dossier(entries=entries, liens=apres_l, plafond=40).chemises}
                print(f"── {ticker} · {fw} {ver} — {len(rs)} lien(s)")
                for r in rs:
                    print(f"     + #{r['id']} → {r['question_id']}.{r['ingredient_id']}")
                for point in sorted(apres):
                    if avant.get(point) != apres[point]:
                        changements += 1
                        a = avant.get(point, ())
                        perdues = set(a) - set(apres[point])
                        print(f"   ⇄ {point[0]}.{point[1]} : remises {list(a)} → {list(apres[point])}"
                              + (f"  · passe(nt) en antérieure (collecte précédente) : {sorted(perdues)}" if perdues else ""))
            print(f"\n{changements} chemise(s) changent de pièces remises.")

            if ecrire and liens:
                async with conn.transaction():
                    for r in liens:
                        await conn.execute(
                            "INSERT INTO question_coverage "
                            "(framework_id, framework_version, question_id, ingredient_id, entry_id) "
                            "VALUES ($1, $2, $3, $4, $5) ON CONFLICT DO NOTHING",
                            r["framework_id"], r["framework_version"], r["question_id"],
                            r["ingredient_id"], r["id"])
                print(f"ÉCRIT : {len(liens)} lien(s) de couverture.")
            elif not ecrire:
                print("À BLANC : rien n'est écrit (relancer avec --ecrire).")
    finally:
        await close_pool()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
