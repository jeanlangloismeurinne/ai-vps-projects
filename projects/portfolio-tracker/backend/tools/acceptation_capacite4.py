"""Acceptation de la capacité 4 — le DELTA de verdict, mesuré sur le corpus réel, sans modèle.

CE QU'IL PROUVE, ET POURQUOI IL N'EST PAS `mesure_gate_capacite4.py`
--------------------------------------------------------------------
`mesure_gate_capacite4.py` répond à « combien de champs basculeraient ». Il croise l'index, les
planchers et l'axe d'actualité **sans passer par la porte** — c'est délibéré : il est le
contre-calcul indépendant de la porte, et sa divergence serait un signal.

Ce script-ci répond à l'autre moitié, qui est le test central de la révision :

    « NVDA et MSFT passent de `ready, 0 gap` à `not_ready` avec cause `péremption`, en nommant les
      champs concernés, SANS les compter comme lacunes de collecte. »

Un delta de VERDICT ne se déduit pas d'un compte de champs : le verdict est une fonction des
`bloc_ok`, la cause est dérivée de la coverage, et les gaps sont réconciliés. Les recalculer ici à
la main referait une seconde porte (#46). On appelle donc la fonction de production elle-même,
`curator._apply_deterministic_overrides` — exactement ce que `run_readiness` exécute une fois le
JSON du modèle revenu. La seule chose qu'on n'exécute pas est l'appel au modèle, et c'est la seule
chose que la capacité 4 ne touche pas : la porte est déterministe de bout en bout.

LA LIGNE DE BASE EST LUE EN BASE, JAMAIS ÉCRITE ICI
---------------------------------------------------
L'état de départ est le `report_json` PERSISTÉ du dernier rapport `readiness` de chaque émetteur —
celui qui affiche aujourd'hui `ready, 0 gap` à l'utilisateur. Le fabriquer en fixture le rendrait
non discriminant (`feedback_ligne_de_base_est_une_mesure`) : c'est ce faux vert persisté, et lui
seul, que la capacité 4 doit faire tomber. RVMD n'a **aucun** rapport readiness en base — il n'est
donc pas un porteur du delta, mais le témoin de SÉPARATION : ses lacunes de collecte ne doivent
jamais être comptées comme des péremptions.

CE QU'IL N'ÉCRIT PAS
--------------------
Rien. Aucun UPDATE, aucun INSERT : le rapport rejoué reste en mémoire. L'actualité ne se persiste
pas (#53) — un outil d'acceptation qui la figerait en base contredirait la capacité qu'il vérifie.

Usage (réseau `coolify` pour la base, sortie internet pour EDGAR) :

    docker run --rm --network coolify -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app \
      --env-file checks/env.checks -e DATABASE_URL="$DATABASE_URL" \
      portfolio-backend-image python tools/acceptation_capacite4.py
"""
from __future__ import annotations

import asyncio
import copy
import json
import sys
from typing import Any, Optional

import os

from app.agents.v2.curator import _apply_deterministic_overrides
from app.db.database import close_pool, get_db_session, init_pool
from app.knowledge.material_events import ancre_substantielle, material_anchor_for_ticker
from app.knowledge.service import get_current_entries

PORTEURS = ["NVDA", "MSFT"]     # les deux `ready, 0 gap` persistés — le faux vert à faire tomber
TEMOIN = "RVMD"                 # aucun rapport : témoin de séparation lacune / péremption

ok = fail = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


_SQL_DERNIER = """
    SELECT id, verdict, report_json, created_at
      FROM knowledge_curator_reports
     WHERE ticker_id = $1 AND report_type = 'readiness'
     ORDER BY created_at DESC, id DESC
     LIMIT 1
"""


def _champs(coverage: dict[str, Any], clef: str) -> list[str]:
    """Les champs QUALIFIÉS (`dimension.champ`) portés par `clef` dans les deux blocs."""
    out: list[str] = []
    for bloc in ("structuree", "qualitative_marche"):
        for d in (coverage.get(bloc) or {}).get("dimensions") or []:
            out += [f"{d.get('dimension')}.{c}" for c in (d.get(clef) or [])]
    return sorted(out)


async def rejouer(conn, ticker_id: str) -> Optional[dict[str, Any]]:
    """Rejoue la moitié déterministe de `run_readiness` sur le corpus courant. Rien n'est écrit."""
    ligne_de_base = await conn.fetchrow(_SQL_DERNIER, ticker_id)
    if ligne_de_base is None:
        return None

    stocke = ligne_de_base["report_json"]
    if isinstance(stocke, str):        # ceinture : sans codec JSONB, on lirait une chaîne
        stocke = json.loads(stocke)

    # Mêmes appels que `run_readiness`, dans le même ordre, avec les mêmes paramètres.
    entries = await get_current_entries(conn, ticker_id, min_reliability=0.0, limit=500)
    ancre = ancre_substantielle(await material_anchor_for_ticker(conn, ticker_id))

    avant = copy.deepcopy(stocke)
    apres = _apply_deterministic_overrides(copy.deepcopy(stocke), entries,
                                           ancre=ancre, ticker_id=ticker_id)
    return {
        "report_id": ligne_de_base["id"],
        "verdict_avant": ligne_de_base["verdict"],
        "gaps_avant": len(avant.get("gaps") or []),
        "cause_avant": avant.get("cause_non_ready"),
        "verdict_apres": apres.get("verdict"),
        "cause_apres": apres.get("cause_non_ready"),
        "gaps": apres.get("gaps") or [],
        "perimes": _champs(apres.get("coverage") or {}, "champs_perimes"),
        "non_fondables": _champs(apres.get("coverage") or {}, "champs_non_fondables"),
        "ancre": ancre,
        "n_entries": len(entries),
    }


async def main() -> int:
    # ⚠️ `get_db_session()` n'ouvre RIEN par lui-même : il puise dans un pool qu'`init_pool` crée au
    # démarrage de l'app, et c'est ce pool qui installe les codecs JSONB. Sans cette ligne, `_pool`
    # est None et le script meurt sur un `AttributeError` — mais s'ouvrir un `asyncpg.connect()` nu
    # pour contourner serait pire : `content_structured` reviendrait en CHAÎNE, aucune citation ne
    # serait vue, et les synthèses sortiraient `indeterminable` là où la porte lit `perimee`. Le
    # mesureur doit ouvrir sa connexion comme la production, pas comme il l'arrange.
    url = os.environ.get("DATABASE_URL") or ""
    if not url:
        print("DATABASE_URL manquant — l'acceptation se MESURE sur le corpus réel.", file=sys.stderr)
        return 2
    await init_pool(url)
    try:
        async with get_db_session() as conn:
            rejeux = {t: await rejouer(conn, t) for t in PORTEURS + [TEMOIN]}
    finally:
        await close_pool()

    for ticker in PORTEURS:
        r = rejeux[ticker]
        print(f"\n=== {ticker} — rapport #{r['report_id']}, {r['n_entries']} entries courantes ===")
        a = r["ancre"]
        print(f"  ancre : {a.status}" + (f" · {a.event.form} du {a.event.event_date}"
                                         f" (items {'/'.join(a.event.items) or '—'})"
                                         if a.event else ""))
        print(f"  AVANT (persisté) : {r['verdict_avant']}, {r['gaps_avant']} gap(s), "
              f"cause={r['cause_avant']}")
        print(f"  APRÈS (rejoué)   : {r['verdict_apres']}, {len(r['gaps'])} gap(s), "
              f"cause={r['cause_apres']}")
        for c in r["perimes"]:
            print(f"      périmé   {c}")
        for c in sorted(set(r["non_fondables"]) - set(r["perimes"])):
            print(f"      lacune   {c}")

        # Le delta lui-même — c'est la phrase de la spec, assertée mot pour mot.
        check(f"[{ticker}] ligne de base persistée = ready, 0 gap",
              r["verdict_avant"] == "ready" and r["gaps_avant"] == 0,
              f"→ {r['verdict_avant']}, {r['gaps_avant']} gap(s) : le faux vert n'est plus là, "
              f"le delta ne prouve plus rien")
        check(f"[{ticker}] la porte fait tomber le faux vert", r["verdict_apres"] == "not_ready",
              f"→ {r['verdict_apres']}")
        check(f"[{ticker}] la cause est la PÉREMPTION, pas la lacune",
              r["cause_apres"] == "peremption", f"→ {r['cause_apres']}")
        check(f"[{ticker}] les champs périmés sont NOMMÉS", bool(r["perimes"]),
              "→ un not_ready sans champ nommé n'est pas actionnable")

        # « sans les compter comme lacunes de collecte » : le point où les deux remèdes se séparent.
        cibles_collecte = {c for g in r["gaps"] if g.get("remede") != "rafraichissement"
                           for c in (g.get("champs_cibles") or [])}
        qualifiees = {f"{g.get('dimension')}.{c}" for g in r["gaps"]
                      if g.get("remede") != "rafraichissement"
                      for c in (g.get("champs_cibles") or [])}
        check(f"[{ticker}] aucun champ périmé n'est envoyé en collecte",
              not (qualifiees & set(r["perimes"])),
              f"→ {sorted(qualifiees & set(r['perimes']))} paieraient une recherche complète")
        check(f"[{ticker}] chaque périmé porte un mandat de RAFRAÎCHISSEMENT",
              set(r["perimes"]) <= {f"{g.get('dimension')}.{c}" for g in r["gaps"]
                                    if g.get("remede") == "rafraichissement"
                                    for c in (g.get("champs_cibles") or [])},
              f"→ périmés sans mandat, cibles collecte vues : {sorted(cibles_collecte)}")

    # ── Témoin de séparation ────────────────────────────────────────────────────
    t = rejeux[TEMOIN]
    print(f"\n=== {TEMOIN} — témoin de séparation ===")
    check(f"[{TEMOIN}] n'a aucun rapport readiness persisté", t is None,
          "→ il en a un : il devient un porteur, et la ligne de base ci-dessus est à refaire")
    if t is not None:
        print(f"  ⚠️ {TEMOIN} porte désormais le rapport #{t['report_id']} — relire la spec.")

    print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
