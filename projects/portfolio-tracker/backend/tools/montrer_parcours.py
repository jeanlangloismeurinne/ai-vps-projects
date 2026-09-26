"""Montre le PARCOURS DU COMITÉ d'un dossier — les trois niveaux tels que les écrans les reçoivent,
en TEXTE, sans rien dépenser (lot 6 maillon 2).

Même rôle que `montrer_qualite_info` / `montrer_memo_projete`, pour les trois niveaux : lire le
payload RÉEL avant d'écrire un pixel (« capturer les payloads réels avant d'écrire du JSX »). Aucun
appel de modèle, aucune écriture : `parcours.charger_etat_dossier` puis les `dresser_niveau*` purs.
Il n'asserte rien — `checks/check_parcours.py` juge.

    bash tools/montrer_parcours.sh RVMD                         # niveau 1 en texte (l'alerte)
    bash tools/montrer_parcours.sh RVMD --json 1                # niveau 1 en JSON
    bash tools/montrer_parcours.sh RVMD --json 2 defendabilite  # niveau 2 en JSON
    bash tools/montrer_parcours.sh RVMD --json 3 defendabilite mo_1

Codes : 0 = dressé · 2 = pas lisible.
"""
from __future__ import annotations

import asyncio
import os
import sys
import traceback

from app.agents.v2.parcours import (
    charger_etat_dossier, dresser_niveau1, dresser_niveau2, dresser_niveau3)
from app.agents.v2.projection_memo import memo_de_l_etat
from app.db.database import close_pool, get_db_session, init_pool

L = 78


def _texte(n1) -> None:
    p = n1.peut_on_decider
    print(f"\n{'─' * L}\nPEUT-ON DÉCIDER ? — {n1.ticker_id} (archétype : {n1.archetype})\n{'─' * L}")
    print(f"  {p.etat.upper()} — {p.motif}")
    for m in p.manques:
        print(f"\n  ▸ {m.libelle_framework} · {m.question_id} [{m.nature}] cause = {m.cause}")
        print(f"      « {m.enonce[:120]} »")
        print(f"      {m.explication[:300]}")
        for i in m.ingredients:
            print(f"        - {i.ingredient_id} [{i.cause}] {i.motif[:110]}")
        if m.mandat_ouvert_id:
            print(f"      repartie en recherche : mandat #{m.mandat_ouvert_id}")
    print(f"\n{'─' * L}\nNOTE DE QUALITÉ PAR MÉTHODOLOGIE\n{'─' * L}")
    for s in n1.frameworks:
        q = s.qualite
        score = "n/d" if q is None or q.score is None else f"{q.score:.2f}"
        print(f"  ▸ {s.libelle} — qualité {score} · rang moyen {q.rang_moyen if q else None} · "
              f"{s.n_applicables}/{s.n_questions} applicables · {s.n_acquittees} acquittée(s) · "
              f"{s.n_renvoyees} renvoyée(s) · {s.n_manques} manque(s)")
    print(f"\n{'─' * L}\nBILAN — niveau 1 dressé pour {n1.ticker_id} : {len(p.manques)} manque(s)\n{'─' * L}\n")


async def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    ticker_id, reste = sys.argv[1], sys.argv[2:]
    if not os.environ.get("DATABASE_URL"):
        print("DATABASE_URL manquante", file=sys.stderr)
        return 2
    await init_pool(os.environ["DATABASE_URL"])
    try:
        async with get_db_session() as conn:
            etat = await charger_etat_dossier(conn, ticker_id)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return 2
    finally:
        await close_pool()

    memo = memo_de_l_etat(etat)
    if reste[:1] == ["--json"]:
        niveau = reste[1]
        obj = (dresser_niveau1(etat, memo) if niveau == "1"
               else dresser_niveau2(etat, reste[2]) if niveau == "2"
               else dresser_niveau3(etat, reste[2], reste[3]))
        print(obj.model_dump_json(indent=2))
        return 0
    _texte(dresser_niveau1(etat, memo))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
