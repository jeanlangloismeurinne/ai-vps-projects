"""Montre le SOCLE DES COMPTES d'un émetteur, reconstitué depuis ses dépôts — EN TEXTE.

C'est la frontière gratuite du socle (`feedback_frontiere_gratuite_avant_depense_modele`) : il ne lit
que l'inventaire public `companyfacts` de la SEC, NI base NI modèle, et il se relit avant tout
branchement sur les questions. On y lit trois choses, dans cet ordre :

  1. les ÉCARTS de bouclage — une équation de contrôle dont les deux côtés sont déposés et diffèrent ;
  2. les lignes « par différence » d'un montant inattendu — ce que le gabarit ne nomme pas ;
  3. les cellules `non_depose` d'une ligne qui devrait exister pour ce profil d'émetteur.

Usage (réseau public) :
    bash tools/montrer_socle.sh RVMD NVDA MSFT
    bash tools/montrer_socle.sh NVDA --provenance resultat_exploitation
    bash tools/montrer_socle.sh --fichier /chemin/companyfacts.json   # inventaire déjà téléchargé

Sortie 0 = socle reconstitué (avec ou sans écart : un écart est une information, il est imprimé).
Sortie 1 = pré-requis manquant (émetteur injoignable, aucune période). Le bilan `BILAN socle — …`
est imprimé pour chaque émetteur ; son absence est un échec.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from app.knowledge.edgar_facts import fetch_company_facts
from app.knowledge.edgar_feed import resolve_cik
from app.knowledge.socle_comptes import (
    SocleComptes, charger_gabarit, charger_reclassements, reconstituer,
)

_MARQUE = {"depose": " ", "par_difference": "≈", "par_somme": "Σ", "calcule": "ƒ",
           "compte_zero": "0", "non_depose": "·"}


def _m(v: Any) -> str:
    return "" if v is None else f"{v / 1e6:,.1f}".replace(",", " ")


def imprimer(nom: str, socle: SocleComptes, provenance: list[str]) -> None:
    gab = charger_gabarit()
    print(f"\n══════ {nom} — gabarit {socle.version_gabarit} — dernier dépôt lu {socle.dernier_depot}")
    for r in socle.reclassements:
        print(f"  RECLASSEMENT → {r.ligne} : {', '.join(r.concepts)} — {r.motif[:90]}…")
    for r in socle.refus:
        print(f"  REFUS : {r}")
    for etat_id, libelle, cadrage in gab.etats:
        ps = [p for p in socle.periodes if p.cadrage == cadrage]
        print(f"\n  {libelle} (M$)   [≈ par différence · Σ par somme · ƒ calculé · 0 compté zéro · · non déposé]")
        print("  " + " " * 46 + "".join(f"{p.id:>15}" for p in ps))
        for l in gab.lignes_de(etat_id):
            cells = [socle.cellules[(l.id, p.id)] for p in ps]
            txt = "".join(f"{_m(c.valeur):>13} {_MARQUE[c.etat]}" for c in cells)
            print(f"  {l.libelle[:46]:<46}{txt}")
    ecarts = socle.ecarts()
    print(f"\n  Contrôles : {len(socle.controles)} dont {len(ecarts)} écart(s)")
    for c in ecarts:
        print(f"    ÉCART {c.periode} : {c.equation} — gauche {_m(c.gauche)} / droite {_m(c.droite)}"
              f" / écart {_m(c.ecart)} M$")
    for ligne in provenance:
        for p in socle.periodes:
            c = socle.cellules.get((ligne, p.id))
            if c is None:
                continue
            print(f"  PROVENANCE {ligne} {p.id} [{c.etat}] {_m(c.valeur)} — "
                  f"{c.equation or ''} {('absorbe ' + ','.join(c.absorbe)) if c.absorbe else ''}")
            for lect in c.lectures:
                print(f"      {lect}")
    nb = {e: sum(1 for c in socle.cellules.values() if c.etat == e) for e in _MARQUE}
    print(f"\nBILAN socle — {nom} : {len(socle.periodes)} périodes, {len(socle.cellules)} cellules "
          f"({', '.join(f'{k} {v}' for k, v in nb.items())}), {len(socle.controles)} contrôles, "
          f"{len(ecarts)} écart(s), {len(socle.refus)} refus")


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tickers", nargs="*")
    ap.add_argument("--fichier", action="append", default=[])
    ap.add_argument("--provenance", action="append", default=[])
    a = ap.parse_args()
    code = 0
    for f in a.fichier:
        payload = json.load(open(f))
        faits = {c: [{**p, "unit": u} for u, s in b["units"].items() for p in s]
                 for c, b in payload["facts"]["us-gaap"].items()}
        socle = reconstituer(faits, reclassements=charger_reclassements(
            payload.get("cik"), charger_gabarit()))
        imprimer(payload.get("entityName", f), socle, a.provenance)
        code |= 0 if socle.periodes else 1
    for t in a.tickers:
        try:
            cik = await resolve_cik(t)
            faits = await fetch_company_facts(cik)
        except Exception as e:   # pré-requis manquant : sortie ≠ 0, jamais un saut silencieux
            print(f"BILAN socle — {t} : ÉCHEC pré-requis ({e})")
            code = 1
            continue
        socle = reconstituer(faits, reclassements=charger_reclassements(cik, charger_gabarit()))
        imprimer(t, socle, a.provenance)
        code |= 0 if socle.periodes else 1
    return code


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
