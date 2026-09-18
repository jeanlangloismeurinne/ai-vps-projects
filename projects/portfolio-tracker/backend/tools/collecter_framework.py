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
    poste_retenu,
    router_source,
)
from app.agents.v2.collecteur import ligne_aveugle
from app.agents.v2.traducteur import traduire
from app.db.database import close_pool, init_pool


async def _plan_only(ticker: str, framework: str, archetype: str) -> None:
    run, plan = await traduire(ticker, framework, archetype)
    edgar = web = inobtenable = 0
    # Les DEUX façons dont un poste nommé peut ne pas aboutir. Les compter séparément est ce qui rend
    # le prompt diagnosticable : un `veto` élevé dit que le traducteur nomme des postes sur des
    # dérivées (à durcir dans le prompt) ; un `source` élevé dit qu'il nomme le bon poste mais
    # pressent une source non réglementaire (à arbitrer, pas forcément un défaut).
    veto = source_non_sec = 0
    print(f"\nPLAN {ticker} · {framework} · {archetype} (v{plan.framework_version}) — "
          f"{len(plan.items)} ligne(s)\n{'-'*78}")
    for it in plan.items:
        if it.statut == "inobtenable":
            inobtenable += 1
            print(f"  [inobtenable] {it.question_id}.{it.ingredient_id} — {it.motif}")
            continue
        voie = router_source(ligne_aveugle(it, plan.ticker_id))
        retenu = poste_retenu(it.poste, it.metrique)
        if voie == "edgar":
            edgar += 1
        else:
            web += 1
            if it.poste and retenu is None:
                veto += 1
            elif retenu is not None:
                source_non_sec += 1
        detail = ""
        if it.poste:
            detail = f" → poste {it.poste}" + ("" if retenu else " [VÉTO]")
        print(f"  [{voie:5}] {it.question_id}.{it.ingredient_id} · « {it.metrique} » "
              f"· src={it.source_pressentie!r}{detail}")
    print(f"{'-'*78}\nDISPATCH : {edgar} edgar · {web} web · {inobtenable} inobtenable "
          f"· dont {veto} poste(s) vétoés (dérivée/hors catalogue) et {source_non_sec} "
          f"poste(s) écartés par la source pressentie "
          f"· coût traducteur ≈ ${getattr(run, 'cost_usd', 0) or 0:.4f}")


async def _plein(ticker: str, framework: str, archetype: str) -> None:
    res = await executer_collecte_framework(ticker, framework, archetype)
    print(f"\nCOLLECTE {ticker} · {framework} · {archetype} — plan #{res['plan_id']}")
    # L'état de la carte se LIT : « fraiche » et « non_reverifiable » servent toutes deux une carte
    # stockée, et seule cette ligne dit laquelle a été revérifiée contre une date mesurée (#70).
    print(f"  carte d'appariement : {res['carte_etat']} · {res['carte_lignes']} ligne(s) "
          f"· dépôt courant {res['carte_depot_courant'] or '(non mesuré)'} "
          f"· coût apparieur ≈ ${res['apparieur_cost_usd']:.4f}")
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
