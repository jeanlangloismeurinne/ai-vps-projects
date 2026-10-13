"""Régénère les fixtures du socle des comptes (`checks/fixtures/socle_comptes/<TICKER>.json`) — COPIÉES DU RÉEL.

Une fixture écrite à la main est un check aveugle au vert (`feedback_fixture_copiee_du_reel`) : celles-ci
sont l'inventaire `companyfacts` de la SEC, restreint aux concepts que le gabarit maison et les
reclassements de l'émetteur peuvent lire, et aux dépôts de l'exercice fiscal 2020 et suivants (ou sans
exercice fiscal déclaré). Réseau public (data.sec.gov), NI base NI modèle.

    bash tools/fixtures_socle.sh RVMD NVDA MSFT          # écrit les trois fichiers
    bash tools/fixtures_socle.sh NVDA --ecart            # n'écrit rien : dit ce qui changerait

Une fixture régénérée se RELIT (les valeurs attendues des checks ont été relues contre les dépôts) :
l'option `--ecart` imprime les concepts ajoutés, retirés et les points dont la valeur diffère.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

from app.knowledge.edgar_facts import fetch_company_facts
from app.knowledge.edgar_feed import resolve_cik
from app.knowledge.socle_comptes import charger_gabarit, charger_reclassements

FIX = Path(__file__).resolve().parent.parent / "checks" / "fixtures" / "socle_comptes"
FY_MIN = 2020


def concepts_lisibles(cik: int) -> set[str]:
    gab = charger_gabarit()
    out = {c for l in gab.lignes.values() for r in l.recettes for c in r}
    out |= {c for r in charger_reclassements(cik, gab) for c in r.concepts}
    return out


async def un(ticker: str, ecart: bool) -> int:
    cik = await resolve_cik(ticker)
    faits = await fetch_company_facts(cik)
    gab = charger_gabarit()
    garder = concepts_lisibles(cik)
    restreint = {c: [p for p in pts if p.get("fy") is None or p["fy"] >= FY_MIN]
                 for c, pts in sorted(faits.items()) if c in garder}
    # Un concept DÉPOSÉ mais sans point dans la fenêtre reste présent, vide : « l'émetteur le dépose,
    # pas sur ces exercices » n'est pas « l'émetteur ne le dépose pas ».
    chemin = FIX / f"{ticker}.json"
    if ecart:
        avant = json.loads(chemin.read_text(encoding="utf-8"))["faits"] if chemin.exists() else {}
        cle = lambda p: (p.get("end"), p.get("start"), p.get("accn"), p.get("unit"))  # noqa: E731
        print(f"══ {ticker} : {len(avant)} → {len(restreint)} concepts")
        print("  ajoutés :", sorted(set(restreint) - set(avant)))
        print("  retirés :", sorted(set(avant) - set(restreint)))
        diff = 0
        for c in set(avant) & set(restreint):
            a = {cle(p): p["val"] for p in avant[c]}
            n = {cle(p): p["val"] for p in restreint[c]}
            diff += sum(1 for k in a.keys() & n.keys() if a[k] != n[k])
            diff += len(a.keys() ^ n.keys())
        print(f"  points différents sur les concepts communs : {diff}")
        return 0
    # La raison sociale se reprend de la fixture précédente (le registre SEC n'est pas relu pour un libellé).
    nom = None
    if chemin.exists():
        src = json.loads(chemin.read_text(encoding="utf-8")).get("source", "")
        nom = src.split("(", 1)[1].split(")", 1)[0] if "(" in src else None
    chemin.write_text(json.dumps({
        "source": (f"data.sec.gov companyfacts CIK {cik} ({nom or ticker}), téléchargé le {date.today()} ; "
                   f"restreint aux concepts du gabarit {gab.version} et des reclassements d'émetteur, dépôts "
                   f"fy>={FY_MIN}"),
        "cik": cik,
        "faits": restreint,
    }, ensure_ascii=False), encoding="utf-8")
    print(f"BILAN fixture — {ticker} : {len(restreint)} concepts, "
          f"{sum(len(v) for v in restreint.values())} points → {chemin.name}")
    return 0


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tickers", nargs="+")
    ap.add_argument("--ecart", action="store_true")
    a = ap.parse_args()
    code = 0
    for t in a.tickers:
        try:
            code |= await un(t, a.ecart)
        except Exception as e:   # pré-requis manquant : sortie ≠ 0, jamais un saut silencieux
            print(f"BILAN fixture — {t} : ÉCHEC ({type(e).__name__}: {e})")
            code = 1
    return code


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
