"""Lanceur de la CHAÎNE DE COLLECTE v3 (lot 2c) — traduire → plan → collecter → persister.

Versionné (jamais `/tmp`). Deux modes :
  · `--plan-only` : traduit et AFFICHE le plan + la décision d'aiguillage (edgar/web) par ligne.
    Déterministe côté dispatch, NE PERSISTE RIEN, ~$0.001 (un appel traducteur). À lire AVANT le
    run complet (`feedback_frontiere_gratuite_avant_depense_modele`).
  · mode plein : exécute RÉELLEMENT (EDGAR socle + search-worker web) et PERSISTE plan/liens/mandats.
    ⚠️ Écritures prod + dépense réseau par ligne web.

  docker run --rm --network coolify -v "$PWD:/app" -w /app -e PYTHONPATH=/app \
    --env-file .env <image> python tools/collecter_framework.py NVDA qualite_financiere rentable [--plan-only]
"""
import asyncio
import os
import sys

from app.agents.v2.collecte_executor import (
    executer_collecte_framework,
    poste_pour_metrique,
    router_source,
)
from app.agents.v2.traducteur import traduire
from app.db.database import close_pool, init_pool


async def _plan_only(ticker: str, framework: str, archetype: str) -> None:
    run, plan = await traduire(ticker, framework, archetype)
    edgar = web = inobtenable = 0
    print(f"\nPLAN {ticker} · {framework} · {archetype} (v{plan.framework_version}) — "
          f"{len(plan.items)} ligne(s)\n{'-'*78}")
    for it in plan.items:
        if it.statut == "inobtenable":
            inobtenable += 1
            print(f"  [inobtenable] {it.question_id}.{it.ingredient_id} — {it.motif}")
            continue
        voie = router_source(it.source_pressentie, it.metrique)
        poste = poste_pour_metrique(it.metrique)
        if voie == "edgar":
            edgar += 1
        else:
            web += 1
        print(f"  [{voie:5}] {it.question_id}.{it.ingredient_id} · « {it.metrique} » "
              f"· src={it.source_pressentie!r}" + (f" → poste {poste}" if poste else ""))
    print(f"{'-'*78}\nDISPATCH : {edgar} edgar · {web} web · {inobtenable} inobtenable "
          f"· coût traducteur ≈ ${getattr(run, 'cost_usd', 0) or 0:.4f}")


async def _plein(ticker: str, framework: str, archetype: str) -> None:
    res = await executer_collecte_framework(ticker, framework, archetype)
    print(f"\nCOLLECTE {ticker} · {framework} · {archetype} — plan #{res['plan_id']}")
    print(f"  lignes vues : {res['lignes_vues']}")
    print(f"  liens écrits (question_coverage) : {res['ecrits']['liens_ecrits']}")
    print(f"  mandats écrits (framework_mandates) : {res['ecrits']['mandats_ecrits']}")
    print(f"{'-'*78}\nLIENS :")
    for l in res["liens"]:
        print(f"  ✓ {l['question_id']}.{l['ingredient_id']} → entry #{l['entry_id']}")
    print("MANDATS :")
    for m in res["mandats"]:
        print(f"  ✗ {m['question_id']}.{m['ingredient_id']} [{m['origine']}] — {m['motif']}")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 3:
        print("usage: collecter_framework.py <ticker> <framework_id> <archetype> [--plan-only]")
        sys.exit(2)
    ticker, framework, archetype = args
    plan_only = "--plan-only" in sys.argv[1:]

    url = os.environ.get("DATABASE_URL") or ""
    if not url or not os.environ.get("DEEPINFRA_API_KEY"):
        print("DATABASE_URL / DEEPINFRA_API_KEY manquantes — la chaîne appelle le VRAI modèle et la "
              "VRAIE base, elle ne se simule pas.", file=sys.stderr)
        sys.exit(2)

    async def _run() -> None:
        await init_pool(url)
        try:
            await (_plan_only if plan_only else _plein)(ticker, framework, archetype)
        finally:
            await close_pool()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
