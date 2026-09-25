"""CLASSER un émetteur — inscrire au dossier l'archétype qui décide des questions applicables.

POURQUOI CET OUTIL EXISTE
--------------------------
L'archétype se tapait à la main sur la ligne de commande d'`executer_chaine.sh`, et disparaissait
avec le terminal. Un décideur sans producteur ne décide jamais : le manager ne pouvait pas
recalculer son avis, et la note projetée lisait cette absence comme un REFUS
(« 6 réponses au dossier, aucune acquittée ») — mesuré sur RVMD le 2026-09-24. La migration 046 lui
a donné une table ; il lui fallait un geste pour l'y mettre.

CE QUE L'OUTIL EXIGE, ET POURQUOI
----------------------------------
  · un MOTIF, toujours — un classement sans motif ne se distingue pas d'un réglage par défaut, et
    c'est lui qui rend des questions hors-sujet. Un hors-sujet sans motif est un trou déguisé ;
  · un archétype DÉCLARÉ dans `frameworks.yaml` — la validation vit chez `persist_archetype` /
    `read_archetype`, qui confrontent au référentiel. Aucun vocabulaire n'est réécrit ici (#46) ;
  · une DATE D'EFFET, par défaut aujourd'hui — un reclassement (« la société est devenue
    rentable au T3 ») est un fait daté, pas une correction. On n'écrase pas, on empile.

    bash tools/classer_emetteur.sh RVMD pre_revenus "Société de biotechnologie en phase clinique…"
    bash tools/classer_emetteur.sh --lire RVMD

Codes : 0 = classé (ou lu) · 1 = refusé (archétype inconnu, motif vide) · 2 = pas exécutable.
"""
from __future__ import annotations

import asyncio
import os
import sys
import traceback
from datetime import date

from app.agents.v2.framework_persist import persist_archetype, read_archetype
from app.agents.v2.frameworks import FrameworkDefinitionRefused, load_frameworks
from app.db.database import close_pool, get_db_session, init_pool


async def _lire(conn, ticker_id: str) -> int:
    courant = await read_archetype(conn, ticker_id=ticker_id)
    if courant is None:
        print(f"\n{ticker_id} — NON CLASSÉ.")
        print("  Ce n'est pas un défaut de lecture : c'est un troisième état, distinct de "
              "« rentable » comme de « pré-revenus ».")
        print("  Tant qu'il dure, la note de comité sort ses chapitres pilotés en "
              "`non_revalidable` — aucune revue n'est possible.\n")
        return 0
    archetype, motif = courant
    print(f"\n{ticker_id} — classé `{archetype}`\n  motif : {motif}\n")
    return 0


async def main() -> int:
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2

    url = os.environ.get("DATABASE_URL") or ""
    if not url:
        print("DATABASE_URL manquante — le dossier n'est pas joignable.", file=sys.stderr)
        return 2

    lecture = argv[0] == "--lire"
    if lecture:
        argv = argv[1:]
        if len(argv) != 1:
            print(__doc__)
            return 2
        ticker_id = argv[0]
    else:
        if len(argv) < 3:
            print(__doc__)
            return 2
        ticker_id, archetype, motif = argv[0], argv[1], argv[2]
        effet = date.fromisoformat(argv[3]) if len(argv) > 3 else date.today()
        if not motif.strip():
            print("Un classement sans motif est un réglage par défaut déguisé — refusé.",
                  file=sys.stderr)
            return 1
        declares = load_frameworks().archetypes
        if archetype not in declares:
            print(f"`{archetype}` n'est pas un archétype déclaré ({sorted(declares)}) — le "
                  f"vocabulaire est détenu par `frameworks.yaml`, jamais par cet outil.",
                  file=sys.stderr)
            return 1

    await init_pool(url)
    try:
        async with get_db_session() as conn:
            if lecture:
                return await _lire(conn, ticker_id)

            avant = await read_archetype(conn, ticker_id=ticker_id)
            async with conn.transaction():
                await persist_archetype(conn, ticker_id=ticker_id, archetype=archetype,
                                        motif=motif, effective_from=effet)
            apres = await read_archetype(conn, ticker_id=ticker_id)

        # L'avant ET l'après, en texte : un outil d'écriture qui n'imprime que « ok » laisse
        # croire qu'il a changé quelque chose même quand la date d'effet le range dans le passé.
        print(f"\n{ticker_id} — avant : "
              f"{'NON CLASSÉ' if avant is None else f'`{avant[0]}`'}")
        print(f"{ticker_id} — après : "
              f"{'NON CLASSÉ' if apres is None else f'`{apres[0]}`'}  (effet {effet})")
        if apres is not None and apres[0] != archetype:
            print(f"  ⚠️ le classement EN VIGUEUR reste `{apres[0]}` : la ligne écrite porte une "
                  f"date d'effet antérieure à celle d'un classement déjà au dossier.")
        print()
        return 0
    except FrameworkDefinitionRefused as e:
        print(f"\nREFUSÉ — {e}\n", file=sys.stderr)
        return 1
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return 2
    finally:
        await close_pool()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
