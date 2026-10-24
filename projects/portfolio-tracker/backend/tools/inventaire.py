"""Maillon 1 du découpage — l'INVENTAIRE, à blanc (plan B4g, 2026-10-24). N'écrit rien en base.

    python tools/inventaire.py NVDA --pieces-seules           # gratuit : le dossier rendu, sa taille
    python tools/inventaire.py NVDA --lectures 3 --sortie F   # N lectures INDÉPENDANTES + comparaison

La comparaison entre lectures est la MESURE qui décide s'il faut un vote (arbitrage du 2026-10-24 :
« une seule lecture devrait suffire » — à prouver). Lanceur : `tools/inventaire.sh`.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

from app.agents.v2.dossier import charger_dossier
from app.agents.v2.frameworks import load_frameworks
from app.agents.v2.preparation import piece_du_classement_de
from app.db.database import close_pool, get_db_session, init_pool
from app.knowledge.edgar_feed import identite_de_l_emetteur
from app.modele_entreprise.inventaire import (
    FRAMEWORK_DU_DOSSIER, MODELE_INVENTAIRE, cle_de_fiche, relever_inventaire, rendre_pieces)

PLAFOND = 40  # même plafond que l'acceptation de l'analyste (`tools/acceptation_analyste.py`)


def _arg(nom: str, defaut=None):
    return sys.argv[sys.argv.index(nom) + 1] if nom in sys.argv else defaut


def _ligne(f) -> str:
    j = lambda x: f"{x.libelle} ({x.date or 'non daté'})" if x else "—"  # noqa: E731
    return (f"  · {f.nom} × {f.marche_vise or '(aucun marché nommé)'} — stade {f.stade or '—'} ; "
            f"dernier : {j(f.dernier_jalon)} ; prochain : {j(f.prochain_jalon)} ; {f.origine} ; pièces {f.pieces}")


async def main() -> int:
    ticker = sys.argv[1]
    lectures = int(_arg("--lectures", "1"))
    sortie = _arg("--sortie")
    await init_pool(os.environ["DATABASE_URL"])
    try:
        fichier = load_frameworks()
        async with get_db_session() as conn:
            piece = await piece_du_classement_de(conn, ticker)
            dossier = await charger_dossier(conn, ticker_id=ticker, framework_id=FRAMEWORK_DU_DOSSIER,
                                            framework_version=fichier.schema_version, plafond=PLAFOND,
                                            joindre=[piece] if piece is not None else [])
            emetteur = await identite_de_l_emetteur(conn, ticker)
        print(dossier.bilan())
        texte = rendre_pieces(dossier.entries)
        print(f"pièces rendues : {len(dossier.entries)} · {len(texte)} caractères (~{len(texte) // 4} jetons)")
        if "--pieces-seules" in sys.argv:
            print(f"numéros : {sorted(dossier.entries)}")
            return 0
        print(f"modèle : {MODELE_INVENTAIRE} · {lectures} lecture(s) indépendante(s)")
        resultats = []
        for n in range(1, lectures + 1):
            inv = await relever_inventaire(ticker, emetteur.raison_sociale, dossier.entries)
            r = inv.run
            print(f"\n── lecture {n} : {len(inv.fiches)} fiche(s) admise(s), {len(inv.ecartees)} écartée(s) · "
                  f"{r.tokens_in} in / {r.tokens_out} out · {r.cost_usd:.4f} $ · {r.attempts} tentative(s)")
            for f in inv.fiches:
                print(_ligne(f))
            for e in inv.ecartees:
                print(f"  ✗ {e.fiche.nom} × {e.fiche.marche_vise} — {e.motif}")
            for sg in inv.signaux:
                print(f"  ⚠ {sg}")
            if inv.non_nommes:
                print(f"  · non nommés : {inv.non_nommes.nombre} (pièces {inv.non_nommes.pieces})")
            resultats.append(inv)
        if lectures > 1:
            cles = [{cle_de_fiche(f) for f in inv.fiches} for inv in resultats]
            union = set().union(*cles)
            commun = set.intersection(*cles)
            print(f"\n── comparaison : union {len(union)} · présentes dans TOUTES les lectures {len(commun)}")
            for c in sorted(union):
                presence = "".join("■" if c in k else "□" for k in cles)
                print(f"  {presence}  {c[0]} × {c[1] or '(aucun marché nommé)'}")
        print(f"\nBILAN inventaire {ticker} : {lectures} lecture(s), fiches admises "
              f"{[len(i.fiches) for i in resultats]}, écartées {[len(i.ecartees) for i in resultats]}, "
              f"coût {sum(i.run.cost_usd for i in resultats):.4f} $")
        if sortie:
            with open(sortie, "w", encoding="utf-8") as fh:
                json.dump([{"fiches": [f.model_dump(mode="json") for f in i.fiches],
                            "ecartees": [{"fiche": e.fiche.model_dump(mode="json"), "motif": e.motif}
                                         for e in i.ecartees],
                            "signaux": i.signaux,
                            "non_nommes": i.non_nommes.model_dump(mode="json") if i.non_nommes else None,
                            "brut": i.run.raw_content} for i in resultats], fh, ensure_ascii=False, indent=2)
            print(f"JSON écrit dans {sortie}")
        return 0
    finally:
        await close_pool()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
