"""Montre la QUALITÉ D'INFORMATION d'un dossier telle qu'elle se mesure — en TEXTE, sans rien dépenser.

POURQUOI CET OUTIL EXISTE
--------------------------
Même raison que `montrer_dossier` / `montrer_memo_projete`, un cran plus loin : une mesure qui
n'apparaît que comme un nombre dans un blob n'est pas lue, et surtout pas CONTESTABLE
(`feedback_controle_au_point_de_lecture`). Le comité doit voir POURQUOI la qualité d'info vaut ce
qu'elle vaut : combien de questions s'appliquent, combien sont périmées, sur quelles sources. Cet
outil imprime la décomposition telle qu'elle part au niveau 1 du parcours.

C'est la frontière gratuite du lot (`feedback_frontiere_gratuite_avant_depense_modele`) : aucun appel
de modèle, aucune écriture. Lecture de `framework_answers` + `knowledge_entries`, puis
`qualite_info.servir_qualite_info()` (qui SERT les réponses — actualité recalculée — avant de
dériver). À rejouer après CHAQUE correctif, pas une seule fois au début.

⚠️ CE QU'IL N'EST PAS. Il n'asserte rien : c'est `checks/check_qualite_info.py` qui juge. Un outil
qui montre ET qui juge finit par ne montrer que ce qu'il sait juger.

    bash tools/montrer_qualite_info.sh RVMD

Codes : 0 = mesure dressée et imprimée · 2 = pas mesurable.
"""
from __future__ import annotations

import asyncio
import os
import sys
import traceback

from app.agents.v2.qualite_info import servir_qualite_info
from app.db.database import close_pool, get_db_session, init_pool

LARGEUR = 78


def _imprimer(ticker_id: str, mesures) -> None:
    print(f"\n{'─' * LARGEUR}")
    print(f"QUALITÉ D'INFORMATION (recalculée à la lecture) — {ticker_id}")
    print(f"{'─' * LARGEUR}")

    if not mesures:
        print("\n  aucune réponse de framework pour cet émetteur — rien à mesurer.")
        print(f"{'─' * LARGEUR}\n")
        return

    for m in mesures:
        titre = (f"{m.score:.2f}" if m.etat == "mesure" else "n/d")
        print(f"\n  ▸ {m.framework_id} (réf. {m.framework_version}) — score {titre}")
        if m.etat != "mesure":
            print("      ce cadre ne s'applique pas à cet émetteur "
                  "(toutes les questions sont hors objet) — pas un « 0 %», un état.")
        print(f"      base {m.base} question(s) applicable(s) : "
              f"{m.n_repondu} répondu · {m.n_approxime} approximé · {m.n_non_fondable} non fondable")
        print(f"      hors base : {m.n_sans_objet} sans objet")
        if m.n_repondu + m.n_approxime:
            print(f"      actualité des réponses fondées : {m.n_courante} courante(s) · "
                  f"{m.n_perimee} périmée(s) · {m.n_indeterminable} non vérifiable(s)")
            print(f"      solidité des sources (publiée, non fondue dans le score) : "
                  f"rang moyen {m.rang_moyen}")

    # Un bilan reconnaissable à sa forme (`feedback_bilan_par_sa_forme`) : son absence est un échec.
    print(f"\n{'─' * LARGEUR}")
    print(f"BILAN — {len(mesures)} framework(s) mesuré(s) pour {ticker_id}")
    print(f"{'─' * LARGEUR}\n")


async def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    ticker_id = sys.argv[1]

    url = os.environ.get("DATABASE_URL") or ""
    if not url:
        print("DATABASE_URL manquante — la mesure n'est pas lisible, elle ne se devine pas.",
              file=sys.stderr)
        return 2

    await init_pool(url)
    try:
        async with get_db_session() as conn:
            mesures = await servir_qualite_info(conn, ticker_id)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return 2
    finally:
        await close_pool()

    _imprimer(ticker_id, mesures)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
