"""Montre la VENTILATION PUBLIÉE d'un émetteur, relevée depuis ses dépôts — EN TEXTE (lot M2).

Même frontière gratuite que `montrer_socle.py` : NI base NI modèle par défaut, un relevé qui se lit
avant tout branchement. `--publier` écrit (réservé à Opus après vérification, cf. le lot).

Usage (réseau public) :
    bash tools/montrer_ventilation.sh NVDA RVMD JPM
    bash tools/montrer_ventilation.sh NVDA --publier    # ÉCRIT — réservé

Sortie 0 = ventilation relevée (ventilée, secteur unique ou sans ventilation : trois constats, pas
des échecs). Sortie 1 = pré-requis manquant (EDGAR injoignable, aucun 10-K). Un bilan `BILAN
ventilation <TICKER> : …` est imprimé pour chaque émetteur ; son absence est un échec.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

from app.knowledge.edgar_facts import fetch_company_facts
from app.knowledge.edgar_feed import resolve_identite
from app.knowledge.socle_comptes import charger_gabarit, charger_reclassements, reconstituer, structure_du_socle
from app.knowledge.ventilation import charger_referentiel, relever, rendre_ventilation, structure_de_ventilation
from app.knowledge.ventilation_feed import VentilationIndisponible, assurer_ventilation, lire_depots


def _bilan(ticker: str, v) -> str:
    raccords_total = [r for r in v.raccords if r.niveau == "total"]
    b = sum(1 for r in raccords_total if r.statut == "boucle")
    nv = sum(1 for r in raccords_total if r.statut == "non_ventile")
    dc = sum(1 for r in raccords_total if r.statut == "decoupage_change")
    ec = sum(1 for r in v.raccords if r.niveau == "emboitement" and r.statut == "ecart")
    st = sum(1 for r in raccords_total if r.statut == "sans_total")
    return (f"BILAN ventilation {ticker} : {v.statut} — {len(v.axes)} axes, {len(v.cellules)} cellules, "
            f"raccords {b} bouclés / {nv} non ventilés / {dc} découpages changés / {ec} écarts / {st} sans total")


async def un(ticker: str, *, publier: bool) -> int:
    gabarit = charger_gabarit()
    referentiel = charger_referentiel()
    try:
        identite = await resolve_identite(ticker)
        faits = await fetch_company_facts(identite.cik)
        socle = reconstituer(faits, gabarit, reclassements=charger_reclassements(identite.cik, gabarit))
        structure_socle = structure_du_socle(socle)
        depots = await lire_depots(identite.cik)
    except VentilationIndisponible as e:
        print(f"BILAN ventilation {ticker} : ÉCHEC pré-requis ({e})")
        return 1
    except Exception as e:  # pré-requis manquant : sortie ≠ 0, jamais un saut silencieux
        print(f"BILAN ventilation {ticker} : ÉCHEC pré-requis ({type(e).__name__}: {e})")
        return 1

    v = relever(depots, gabarit, referentiel, structure_socle)
    structure = structure_de_ventilation(
        v, version_referentiel=referentiel.version, version_gabarit=gabarit.version, depots=tuple(depots))
    print(f"\n══════ {ticker} — {identite.raison_sociale} ══════")
    print(rendre_ventilation(structure, raison_sociale=identite.raison_sociale))
    if v.conflits:
        print(f"\nCONFLITS de hiérarchie ({len(v.conflits)}) :")
        for c in v.conflits[:10]:
            print(f"  {c}")
    print(f"\n{_bilan(ticker, v)}")

    if publier:
        import asyncpg
        url = os.environ.get("DATABASE_URL") or ""
        if "@" not in url:
            print("  --publier ÉCHEC : DATABASE_URL absente — réservé à Opus, après vérification de la "
                  "sortie à blanc ci-dessus")
            return 1
        conn = await asyncpg.connect(url.replace("postgresql+asyncpg://", "postgresql://"))
        try:
            res = await assurer_ventilation(conn, ticker)
            print(f"  --publier : statut={res.statut} entry_id={res.entry_id} motif={res.motif}")
        finally:
            await conn.close()

    return 0 if v.statut in ("ventilee", "secteur_unique", "sans_ventilation") else 1


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tickers", nargs="+")
    ap.add_argument("--publier", action="store_true")
    a = ap.parse_args()
    code = 0
    for t in a.tickers:
        code |= await un(t, publier=a.publier)
    return code


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
