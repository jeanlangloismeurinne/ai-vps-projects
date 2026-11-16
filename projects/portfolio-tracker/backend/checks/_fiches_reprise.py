"""Fixture des checks de l'ancien code qui qualifient une source : les fiches RÉELLES.

Le fichier de reprise (`app/db/seeds/emetteurs_reprise_2026-11-13.json`, importé en production le
2026-11-16) est joué par les gestes du module M1 dans un dépôt en mémoire, puis le système admet les
pages de relations investisseurs des autres sociétés, comme `tools/emetteurs.sh pages-investisseurs`
l'a fait en production le même jour sur les adresses des pièces (une adresse par société admise).
Une fixture se copie du réel : plus favorable que la production, elle rendrait les checks aveugles.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.knowledge.fiche_emetteur import fiche_vide
from app.modules.emetteurs import contrat as C

REPRISE = Path(__file__).resolve().parent.parent / "app" / "db" / "seeds" / "emetteurs_reprise_2026-11-13.json"
PAGES_INVESTISSEURS_ADMISES = (
    "https://investor.lilly.com/news-releases/x",
    "https://investor.nvidia.com/news/x",
    "https://investors.amgen.com/node/x",
    "https://investor.tsmc.com/english/x",
    "https://investor.verastem.com/news-releases/x",
    "https://ir.amd.com/news-events/x",
    "https://ir.immuneering.com/news-releases/x",
    "https://ir.revmed.com/news-releases/x",
)


async def _charger() -> dict[str, C.Fiche]:
    doc = json.loads(REPRISE.read_text(encoding="utf-8"))
    depot = C.DepotMemoire()
    for f in doc["fiches"]:
        await C.etablir_fiche(depot, f["emetteur"], raison_sociale=f["raison_sociale"], auteur=f["auteur"],
                              motif=f["motif"], le=f["le"], pays=f["pays"],
                              cotations=[tuple(x) for x in f["cotations"]],
                              references=[tuple(x) for x in f["references"]],
                              lieux=[tuple(x) for x in f["lieux"]], specialite=f["specialite"])
    for s in doc["sources"]:
        await C.admettre_source(depot, source=s["source"], portee=s["portee"], natures=s["natures"],
                                niveau=s["niveau"], auteur=s["auteur"], motif=s["motif"], le=s["le"],
                                critere=s["critere"])
    await C.admettre_pages_investisseurs(depot, PAGES_INVESTISSEURS_ADMISES, le="2026-11-16")
    return {e: await C.lire_fiche(depot, e) for e in await depot.emetteurs()}


# Lues une fois, à l'import : un check peut ensuite demander une fiche depuis une boucle en cours.
FICHES: dict[str, C.Fiche] = asyncio.run(_charger())


def fiche(emetteur: str | None) -> C.Fiche:
    """La fiche de la reprise ; la fiche vide pour un émetteur qui n'en a pas (comme en production)."""
    code = (emetteur or "").strip().upper()
    return FICHES.get(code) or fiche_vide(code or None)
