"""Mesureur d'UNE ligne web de la collecte : où passe le temps du search-worker (jalon A1 bis).

    bash tools/mesurer_ligne_web.sh <plan_id> <item_id> [<item_id> …] [--plafond=600]

Pourquoi : le chien de garde #73 coupe une ligne web à `WEB_LINE_BUDGET_S` (180 s) et la convertit en
mandat `source_indisponible`. Sur RVMD × modèle économique (plan #242), 12 lignes sur 19 l'ont été.
Le garde dit QU'une ligne a été coupée, jamais OÙ le temps est passé — tours de modèle (latence, jetons
d'entrée), outils (recherche, lecture de page), clôture. Corriger sans cette mesure serait choisir un
remède (budget, itérations, parallélisme, requête) à l'aveugle (`feedback_decision_figee_a_remesurer`).

Ce que l'outil fait : rebâtit la requête EXACTE de la ligne (`ligne_aveugle` → `construire_requete_web`,
les détenteurs de production, jamais une copie), lance `run_search_worker` SANS le garde de 180 s mais
sous un plafond de mesure (défaut 600 s), et chronomètre chaque appel modèle et chaque outil.

⚠️ N'ÉCRIT RIEN en base : `run_search_worker` ne persiste pas (c'est `persist_worker_entries`, que
l'outil n'appelle pas). Il lit la base (ancre, `query_knowledge`) et DÉPENSE des appels modèle et web
(quelques centimes par ligne).
⚠️ Jamais dans `portfolio-backend` (code déployé) : instance neuve de l'image, dépôt en lecture seule.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from typing import Any

from app.agents.providers import ResolvedAgent
from app.agents.v2 import worker as worker_mod
from app.agents.v2.collecte_executor import construire_requete_web
from app.agents.v2.collecteur import ligne_aveugle
from app.config import settings
from app.contracts.collection_plan_schema import CollectionPlanItem
from app.db.database import get_db_session, init_pool
from app.knowledge.edgar_feed import identite_de_l_emetteur

_JOURNAL: list[dict[str, Any]] = []
_T0 = [0.0]


def _horodater() -> float:
    return round(time.monotonic() - _T0[0], 1)


_complete_orig = ResolvedAgent.complete


async def _complete_mesure(self: ResolvedAgent, messages, **kw):  # type: ignore[no-untyped-def]
    debut = time.monotonic()
    taille = sum(len(json.dumps(m, ensure_ascii=False)) for m in messages)
    res = await _complete_orig(self, messages, **kw)
    _JOURNAL.append({
        "t": _horodater(), "quoi": "cloture" if self.tools is None else "modele",
        "duree_s": round(time.monotonic() - debut, 1),
        "jetons_entree": res.tokens_in, "jetons_sortie": res.tokens_out,
        "caracteres_envoyes": taille, "appels_outils": len(res.tool_calls or []),
        "cout_usd": round(res.cost_usd, 5),
    })
    return res


ResolvedAgent.complete = _complete_mesure  # type: ignore[method-assign]

_build_orig = worker_mod.build_tool_executors


def _build_mesure(**kw):  # type: ignore[no-untyped-def]
    execs = _build_orig(**kw)

    def _envelopper(nom, fn):  # type: ignore[no-untyped-def]
        async def _exec(args):  # type: ignore[no-untyped-def]
            debut = time.monotonic()
            try:
                res = await fn(args)
                etat = "ok"
            except Exception as e:  # noqa: BLE001 — mesuré puis relevé tel quel
                etat, res = f"leve {type(e).__name__}", None
                raise
            finally:
                taille = len(json.dumps(res, ensure_ascii=False, default=str)) if res is not None else 0
                _JOURNAL.append({
                    "t": _horodater(), "quoi": nom, "duree_s": round(time.monotonic() - debut, 1),
                    "etat": etat, "caracteres_rendus": taille,
                    "arg": (args.get("query") or args.get("url") or "")[:90]
                           + (f"  ⟨chercher : {args['chercher'][:80]}⟩" if args.get("chercher") else ""),
                })
            return res
        return _exec

    return {nom: _envelopper(nom, fn) for nom, fn in execs.items()}


worker_mod.build_tool_executors = _build_mesure  # type: ignore[assignment]


async def _mesurer(plan_id: int, item_id: int, plafond: int) -> None:
    async with get_db_session() as conn:
        row = await conn.fetchrow(
            "SELECT i.*, p.ticker_id FROM collection_plan_items i JOIN collection_plans p "
            "ON p.id = i.plan_id WHERE i.plan_id = $1 AND i.id = $2", plan_id, item_id)
        if row is None:
            print(f"ligne {item_id} absente du plan {plan_id}")
            return
        champs = set(CollectionPlanItem.model_fields)
        item = CollectionPlanItem.model_validate({k: row[k] for k in champs if k in row.keys()})
        emetteur = await identite_de_l_emetteur(conn, row["ticker_id"])
    req = construire_requete_web(ligne_aveugle(item, row["ticker_id"]), emetteur=emetteur)
    _JOURNAL.clear()
    _T0[0] = time.monotonic()
    issue, fiches = "rendu", []
    try:
        ex = await asyncio.wait_for(worker_mod.run_search_worker(req), timeout=plafond)
        detail = f"status={ex.response.status} entries={len(ex.response.entries)}"
        fiches = ex.response.entries
    except (asyncio.TimeoutError, TimeoutError):
        issue, detail = "plafond_de_mesure", f"> {plafond} s"
    except Exception as e:  # noqa: BLE001
        issue, detail = "leve", f"{type(e).__name__}: {str(e)[:1500]}"
    total = _horodater()
    print(f"\n=== ligne {item_id} ({row['question_id']}.{row['ingredient_id']}, période {row['periode']})")
    print(f"    métrique : {row['metrique'][:110]}")
    for j in _JOURNAL:
        if j["quoi"] in ("modele", "cloture"):
            print(f"  t={j['t']:>6}  {j['quoi']:<8} {j['duree_s']:>6} s  entrée {j['jetons_entree']:>7} j  "
                  f"sortie {j['jetons_sortie']:>5} j  outils demandés {j['appels_outils']}  ${j['cout_usd']}")
        else:
            print(f"  t={j['t']:>6}  {j['quoi']:<15} {j['duree_s']:>5} s  {j['etat']:<8} "
                  f"{j['caracteres_rendus']:>8} car.  {j['arg']}")
    # Le verdict est à la LECTURE : chaque fiche, sa source et ses extraits, tels que le serveur les a admis.
    for k, e in enumerate(fiches, 1):
        print(f"  fiche {k} [{e.source_type}] {e.source_url or '—'}")
        print(f"      titre : {(e.title or '')[:150]}")
        for x in (getattr(e, "extraits", None) or [])[:4]:
            print(f"      « {' '.join(x.split())[:200]} »")
    mod = [j for j in _JOURNAL if j["quoi"] in ("modele", "cloture")]
    out = [j for j in _JOURNAL if j["quoi"] not in ("modele", "cloture")]
    print(f"  BILAN ligne {item_id} : issue={issue} ({detail}) · total {total} s · "
          f"{len(mod)} appels modèle = {round(sum(j['duree_s'] for j in mod), 1)} s · "
          f"{len(out)} outils = {round(sum(j['duree_s'] for j in out), 1)} s · "
          f"jetons d'entrée cumulés {sum(j['jetons_entree'] for j in mod)} · "
          f"coût ${round(sum(j['cout_usd'] for j in mod), 4)} · dépasse le budget de {settings.WEB_LINE_BUDGET_S} s : {'OUI' if total > settings.WEB_LINE_BUDGET_S else 'non'}")


async def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    plafond = next((int(a.split("=", 1)[1]) for a in sys.argv[1:] if a.startswith("--plafond=")), 600)
    if len(args) < 2:
        print(__doc__)
        return 2
    url = os.environ.get("DATABASE_URL", "").replace("+asyncpg", "")
    if not url or not os.environ.get("DEEPINFRA_API_KEY"):
        print("DATABASE_URL ou DEEPINFRA_API_KEY manquante.", file=sys.stderr)
        return 2
    await init_pool(url)
    plan_id = int(args[0])
    for item_id in map(int, args[1:]):
        await _mesurer(plan_id, item_id, plafond)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
