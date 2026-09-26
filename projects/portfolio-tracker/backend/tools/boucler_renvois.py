"""UN PASSAGE DE BOUCLAGE comité → collecte (lot 5) — l'entrée de production qui EXERCE le décideur.

    python tools/boucler_renvois.py RVMD qualite_financiere pre_revenus

Ce que fait ce passage (arbitrage utilisateur 2026-09-25, cadence « cycle suivant ») : il lit les
renvois du comité restés OUVERTS, refait la recherche PAR LE MÊME PROCESSUS que l'analyse initiale,
restreint aux questions renvoyées (pas de chemin parallèle, #46), re-répond, SERT les mandats, et
imprime la NOTE HONNÊTE — par renvoi, son sort : acquis · collecte_insuffisante · mandat_non_executable
· classe_sans_suite. C'est ce qui ferme la figure #71 : `serve_mandate`/`read_open_mandates`, testés
mais jamais appelés en prod, le sont désormais.

⚠️ DÉPENSE ET ÉCRIT EN PROD (comme `executer_chaine`) : collecte scopée (traducteur + web),
réponses persistées, mandats passés `servi`. Pas de ROLLBACK — un mécanisme prouvé en transaction
n'a pas tourné. Ne PAS jouer dans `portfolio-backend` (code déployé, possiblement antérieur).

⚠️ LE VERDICT EST À LA LECTURE. Un `acquis` bien formé sur un fait inventé passe les contrôles : ils
gardent la structure, jamais le sens (`feedback_garde_structure_pas_sens`). Relire les verbatims des
réponses re-persistées avant de conclure.

Codes : 0 = passage allé au bout · 1 = rien à boucler (aucun renvoi ouvert) · 2 = pas exécutable (env).
"""
from __future__ import annotations

import asyncio
import os
import sys
import traceback

from app.agents.v2.bouclage import boucler_renvois
from app.db.database import close_pool, init_pool

ANALYSTE = os.environ.get("CHAINE_ANALYSTE", "passage_manuel_v3")


async def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    ticker_id, framework_id, archetype = sys.argv[1], sys.argv[2], sys.argv[3]

    # Les pré-requis se refusent AVANT toute dépense (#40) — un passage qui découvre au milieu qu'il
    # manque une clef aurait déjà écrit des réponses et servi des mandats.
    url = os.environ.get("DATABASE_URL") or ""
    if not url:
        print("DATABASE_URL manquante.", file=sys.stderr)
        return 2
    if not os.environ.get("DEEPINFRA_API_KEY"):
        print("DEEPINFRA_API_KEY manquante — ce passage appelle le VRAI modèle.", file=sys.stderr)
        return 2

    await init_pool(url)
    try:
        print(f"{'='*78}\nPASSAGE DE BOUCLAGE — {ticker_id} · {framework_id} · « {archetype} »\n"
              f"analyste `{ANALYSTE}`\n{'='*78}")
        note = await boucler_renvois(
            ticker_id, framework_id, archetype, analyste=ANALYSTE,
            sur_lecture=lambda lecture: print(lecture.texte()))

        print(f"\nmandats ouverts lus au départ : {note.mandats_lus}")
        if note.mandats_lus == 0:
            print("  aucun renvoi ouvert — rien à boucler (le comité n'attend aucune recherche).")
            return 1

        # Le décompte par sort — la note honnête, en une vue.
        par_sort: dict[str, int] = {}
        for b in note.boucles:
            par_sort[b.sort] = par_sort.get(b.sort, 0) + 1
        print("  sorts : " + (" · ".join(f"{k} {v}" for k, v in sorted(par_sort.items())) or "—"))

        for b in note.boucles:
            print(f"\n  · {b.question_id}  [{b.sort}]  {b.statut_avant} → {b.statut_apres}"
                  f"  (mandat #{b.mandat_id})")
            print(f"      {b.motif}")
            if b.entry_ids_produits:
                print(f"      entries produites : {b.entry_ids_produits}")

        # Un renvoi lu mais NON bouclé (question plus applicable) est dit par la différence.
        non_boucles = note.mandats_lus - len(note.boucles)
        if non_boucles:
            print(f"\n  ⚠️ {non_boucles} mandat(s) lu(s) mais NON rejoué(s) (question plus applicable) — "
                  "laissés ouverts plutôt que servis sur rien.")

        print(f"\n{'='*78}\n⚠️ LE VERDICT EST À LA LECTURE. Un `acquis` bien formé sur un fait inventé "
              "passe les contrôles.\n" + "="*78)
        return 0
    finally:
        await close_pool()


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        raise SystemExit(2)
