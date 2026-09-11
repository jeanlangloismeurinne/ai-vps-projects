"""Acceptation du TRADUCTEUR contre le VRAI modèle (lot 2c).

Un prompt/schéma n'est pas acquis tant qu'il n'a pas tourné contre le vrai modèle
(`feedback_verifier_contre_api_reelle`). La moitié déterministe est éprouvée hors-ligne par
`checks/check_traducteur.py` ; ICI on fait produire un plan RÉEL par DeepSeek sur deux archétypes
contrastés, on le LIT en texte, et on vérifie les critères mécaniques.

NE PERSISTE RIEN. `traduire()` construit et valide (contrat + pont), n'écrit pas en base.

⚠️ Jamais dans le conteneur `portfolio-backend` : il porte le code DÉPLOYÉ, qui peut précéder celui
qu'on éprouve. Lanceur : `tools/acceptation_traducteur.sh`.

Codes : 0 = tous les critères tenus · 1 = un critère rouge · 2 = pas mesurable (env/modèle indispo).
"""
from __future__ import annotations

import asyncio
import os
import sys
import traceback

from app.agents.v2.frameworks import CollectionPlanRefused, load_frameworks
from app.agents.v2.traducteur import questions_applicables, traduire
from app.db.database import close_pool, init_pool

# NVDA (rentable) vs RVMD (pré-revenus) : contraste maximal, c'est le sens des deux pilotes.
CAS = [
    ("NVDA", "qualite_financiere", "rentable"),
    ("RVMD", "qualite_financiere", "pre_revenus"),
]


def _essentiels(fichier, framework_id, archetype) -> set[tuple[str, str]]:
    return {(q.id, i.id)
            for q in questions_applicables(fichier, framework_id, archetype)
            for i in q.ingredients_requis if i.essentiel}


async def main() -> int:
    url = os.environ.get("DATABASE_URL") or ""
    if not url or not os.environ.get("DEEPINFRA_API_KEY"):
        print("DATABASE_URL / DEEPINFRA_API_KEY manquantes — l'acceptation appelle le VRAI modèle, "
              "elle ne se simule pas.", file=sys.stderr)
        return 2

    fichier = load_frameworks()
    await init_pool(url)
    ok = fail = 0
    try:
        for ticker, framework_id, archetype in CAS:
            print(f"\n{'='*72}\n{ticker} · {framework_id} · archétype « {archetype} »\n{'='*72}")
            ess = _essentiels(fichier, framework_id, archetype)
            try:
                run, plan = await traduire(ticker, framework_id, archetype, fichier=fichier)
            except CollectionPlanRefused as e:
                fail += 1
                print(f"  FAIL plan REFUSÉ par le pont (le modèle a produit un plan incohérent) : {e}")
                continue
            except Exception as e:  # noqa: BLE001
                fail += 1
                print(f"  FAIL {type(e).__name__}: {e}")
                traceback.print_exc()
                continue

            trad = [it for it in plan.items if it.statut == "traduit"]
            inob = [it for it in plan.items if it.statut == "inobtenable"]
            for it in plan.items:
                marque = "  " if (it.question_id, it.ingredient_id) in ess else " ·"
                if it.statut == "traduit":
                    print(f"{marque} {it.question_id}.{it.ingredient_id}")
                    print(f"      → {it.metrique}")
                    print(f"        [source pressentie : {it.source_pressentie} · ancre : {it.ancre}]")
                else:
                    print(f"{marque} {it.question_id}.{it.ingredient_id}")
                    print(f"      ⚠ INOBTENABLE → mandat : {it.motif}")

            couples = {(it.question_id, it.ingredient_id) for it in plan.items}
            manque = ess - couples
            print(f"\n  télémétrie : {run.tokens_in} in / {run.tokens_out} out · "
                  f"${run.cost_usd:.4f} · {len(trad)} traduits / {len(inob)} inobtenables")

            # Critère mécanique (le pont l'a déjà exigé pour rendre le plan — on le REDIT explicitement,
            # pour que le bilan porte sur une ligne réelle, pas sur zéro).
            if not manque:
                ok += 1
                print(f"  ok   les {len(ess)} ingrédients essentiels ont chacun une ligne (T1bis tenu)")
            else:
                fail += 1
                print(f"  FAIL essentiels sans ligne : {sorted(manque)}")

        print(f"\n{'='*72}\n{ok} vérifications OK, {fail} échec(s)")
        print("⚠️ Le reste s'apprécie À LA LECTURE : les métriques et ancres sont-elles bien "
              "celles de CETTE entreprise-là (cash burn/lecture clinique pour RVMD, FCF/clôture "
              "pour NVDA), et cout_du_capital sort-il en inobtenable faute de source déterministe ?")
        return 1 if fail else 0
    finally:
        await close_pool()


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(2)
