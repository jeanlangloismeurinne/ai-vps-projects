"""La REPRISE est-elle « à l'identique » ? — ligne A14 de l'acceptation de M1, part prouvable sans
base (`roadmap/V3/M1-fiche-emetteur.md`). Le fichier de reprise est joué par les gestes du module,
puis, sur un panel d'adresses, le niveau rendu par la FICHE est confronté à celui que rend l'ANCIEN
code (exécuté, pas recopié), pour les trois titres et les trois natures d'information.

  [R1] le fichier de reprise passe en entier par les gestes du module, sans un refus
  [R2] il reprend TOUT ce que l'ancien code portait (chaque domaine des cinq listes, chaque titre)
  [R3] sur le panel, la fiche rend le même niveau que l'ancien code
  [R4] écart VOULU, et TRANSITOIRE : l'ancien code tenait pour « relations investisseurs » toute
       adresse dont la forme y ressemble, de n'importe quelle société ; la fiche nomme celles de
       l'émetteur, et le système admet lui-même celles des autres sociétés (arbitrage du 2026-11-14) :
       une fois son acte au journal, le niveau redevient celui de l'ancien code
  [R5] écart VOULU : un sous-domaine d'un site de dépôts officiels est couvert, comme pour toute
       autre source ; l'ancien code n'en reconnaissait que trois adresses exactes

CE CONTRÔLE EST PROVISOIRE : il lit `websearch` et `source_registry`, que l'acceptation de M1
supprime. Il part avec eux.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Bilan  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.knowledge import source_registry as ANCIEN_REGISTRE  # noqa: E402
from app.knowledge import websearch as ANCIEN_WEB  # noqa: E402
from app.knowledge.service import RELIABILITY_TABLE  # noqa: E402
from app.modules.emetteurs import contrat as C  # noqa: E402

REPRISE = BACKEND / "app" / "db" / "seeds" / "emetteurs_reprise_2026-11-13.json"
NATURES = ("mesure", "evenement", "interpretation")


def ancien_niveau(adresse: str, titre: str, nature: str) -> str:
    t = ANCIEN_WEB.classify_source_type(adresse, titre)
    if t == "web_search_generic" and any(nature in s.natures for s in ANCIEN_REGISTRE.admissions_pour(adresse, titre)):
        t = "web_search_reputable"
    return RELIABILITY_TABLE[t][0]


async def charger(depot) -> int:
    doc = json.loads(REPRISE.read_text(encoding="utf-8"))
    refus = 0
    for f in doc["fiches"]:
        try:
            await C.etablir_fiche(depot, f["emetteur"], raison_sociale=f["raison_sociale"], auteur=f["auteur"],
                                  motif=f["motif"], le=f["le"], pays=f["pays"],
                                  cotations=[tuple(x) for x in f["cotations"]],
                                  references=[tuple(x) for x in f["references"]],
                                  lieux=[tuple(x) for x in f["lieux"]], specialite=f["specialite"])
        except C.ActeRefuse as e:
            refus += 1
            print(f"  refus fiche {f['emetteur']} : {e}")
    for s in doc["sources"]:
        try:
            await C.admettre_source(depot, source=s["source"], portee=s["portee"], natures=s["natures"],
                                    niveau=s["niveau"], auteur=s["auteur"], motif=s["motif"], le=s["le"],
                                    critere=s["critere"])
        except C.ActeRefuse as e:
            refus += 1
            print(f"  refus source {s['source']} : {e}")
    return refus


def main() -> int:
    b = Bilan()
    depot = C.DepotMemoire()
    doc = json.loads(REPRISE.read_text(encoding="utf-8"))
    b.check(asyncio.run(charger(depot)) == 0, "[R1] la reprise passe par les gestes du module sans un refus")

    titres = sorted(ANCIEN_WEB._ISSUER_DOMAINS)
    b.check(sorted(f["emetteur"] for f in doc["fiches"]) == titres and len(titres) >= 1,
            "[R2] chaque titre de l'ancien code a sa fiche, et aucun autre")
    listes = [d[4:] if d.startswith("www.") else d for d in (
        list(ANCIEN_WEB._OFFICIAL_DOMAINS) + list(ANCIEN_WEB._EU_REGULATOR_SUFFIXES)
        + list(ANCIEN_WEB._PRESS_DOMAINS) + list(ANCIEN_WEB._REPUTABLE_SUFFIXES)
        + [s.domain for s in ANCIEN_REGISTRE._ADMISES])]
    repris = {s["source"] for s in doc["sources"]}
    manquants = sorted(set(listes) - repris)
    b.check(len(listes) >= 30 and not manquants,
            f"[R2] chaque domaine des listes de l'ancien code est repris ({len(set(listes))} domaines)"
            + (f" — manquants : {manquants}" if manquants else ""))
    b.check(not sorted(repris - set(listes)), "[R2] la reprise n'admet rien que l'ancien code n'admettait pas")
    fiches = {t: asyncio.run(C.lire_fiche(depot, t)) for t in titres}
    for t in titres:
        b.check(fiches[t].specialite == ANCIEN_REGISTRE._TICKER_SECTEURS.get(t, "")
                and {l.adresse for l in fiches[t].lieux if l.genre == "site"} == set(ANCIEN_WEB._ISSUER_DOMAINS[t]),
                f"[R2] {t} : spécialité et site repris tels que l'ancien code les écrit")

    panel: list[str] = []
    for d in sorted(set(listes)):
        panel += [f"https://{d}/article/1", f"https://www.{d}/", f"https://sous.{d}/x?y=1"]
    for t in titres:
        for d in ANCIEN_WEB._ISSUER_DOMAINS[t]:
            panel += [f"https://{d}/", f"https://www.{d}/produits/x", f"https://blog.{d}/billet"]
        panel += [f"https://{l.adresse}/communique.pdf" for l in fiches[t].lieux if l.genre == "relations_investisseurs"]
    panel += ["https://inconnu.example/x", "https://medium.com/@quelquun/billet", "https://fauxreuters.com/x",
              "https://sec.gov.pirate.example/x", "pas une adresse", "https://www.sec.gov/Archives/edgar/data/1/x.htm"]
    ecarts = []
    for t in titres:
        for adresse in panel:
            for n in NATURES:
                a, q = ancien_niveau(adresse, t, n), C.qualifier(fiches[t], adresse, n)
                if a != q.niveau:
                    ecarts.append((t, adresse, n, a, q.niveau))
    # Deux familles d'écarts sont VOULUES et nommées ([R4], [R5]) ; tout autre écart est un défaut.
    officiels = {d[4:] if d.startswith("www.") else d for d in ANCIEN_WEB._OFFICIAL_DOMAINS}

    def famille(e) -> str:
        t, adresse, _, ancien, neuf = e
        hote = adresse.split("//", 1)[-1].split("/", 1)[0]
        if ancien == "A" and neuf == "C+" and ANCIEN_WEB._IR_HOST_PATTERN.match(hote) \
                and not any(hote == d or hote.endswith("." + d) for d in ANCIEN_WEB._ISSUER_DOMAINS[t]):
            return "R4"
        if ancien == "C+" and neuf == "A" and any(hote.endswith("." + d) for d in officiels) \
                and hote.removeprefix("www.") not in officiels:
            return "R5"
        return "autre"

    par_famille = {"R4": [], "R5": [], "autre": []}
    for e in ecarts:
        par_famille[famille(e)].append(e)
    for e in par_famille["autre"][:10]:
        print(f"  écart {e[0]} {e[2]:<15} ancien {e[3]:<3} fiche {e[4]:<3} {e[1]}")
    b.check(len(panel) >= 100, f"[R3] le panel est non vide ({len(panel)} adresses × {len(titres)} titres × 3 natures)")
    b.check(not par_famille["autre"],
            f"[R3] hors des deux écarts voulus, la fiche rend le même niveau que l'ancien code "
            f"({len(par_famille['autre'])} écart(s) ; voulus : {len(par_famille['R4'])} [R4], {len(par_famille['R5'])} [R5])")
    b.check(len(par_famille["R5"]) >= 1,
            "[R5] écart voulu constaté : un sous-domaine d'un site de dépôts officiels est couvert par la "
            "fiche (comme pour toute autre source), l'ancien code n'en reconnaissait que trois adresses exactes")

    # L'écart voulu : la forme d'une adresse ne fait pas une page de relations investisseurs.
    etranger = "https://investors.une-autre-societe.example/resultats"
    t0 = titres[0]
    b.check(ancien_niveau(etranger, t0, "mesure") == "A"
            and C.qualifier(fiches[t0], etranger, "mesure").niveau == "C+",
            "[R4] une page « investors.* » d'une AUTRE société : niveau A dans l'ancien code, non admise par la fiche "
            "tant que le système ne l'a pas admise")
    asyncio.run(C.admettre_pages_investisseurs(depot, [etranger], le="2026-11-14"))
    apres = asyncio.run(C.lire_fiche(depot, t0))
    b.check(all(C.qualifier(apres, etranger, n).niveau == ancien_niveau(etranger, t0, n) for n in NATURES),
            "[R4] une fois admise par le système, la page de l'autre société retrouve le niveau de l'ancien code")
    return b.summary()


if __name__ == "__main__":
    sys.exit(main())
