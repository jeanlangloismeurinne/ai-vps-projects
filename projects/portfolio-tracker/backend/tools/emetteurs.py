"""Outil du module M1 « Fiche de l'émetteur et sources » — passe par le CONTRAT du module, jamais
par ses tables.

  importer FICHIER [--a-blanc]   joue les fiches et les admissions d'un fichier de reprise par les
                                 gestes du module (mêmes refus qu'à l'écran). Rejouable : ce qui est
                                 déjà en place est compté, pas réécrit. `--a-blanc` : rien n'est gardé.
  montrer [EMETTEUR]             la liste des émetteurs et le journal des sources, ou une fiche.
  comparer EMETTEUR TITRE        ligne A14 de l'acceptation : pour chaque adresse des pièces déjà
                                 collectées sous TITRE (ancien système), le niveau que rend l'ancien
                                 code et celui que rend la fiche ; liste chaque écart. Lecture seule.
  signaler EMETTEUR TITRE        les pièces déjà collectées qui s'appuient sur une source révoquée.

Base : variable `DATABASE_URL`. Lancement sur le VPS : `bash tools/emetteurs.sh …`.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncpg  # noqa: E402

from app.modules.emetteurs import contrat as C  # noqa: E402


async def _connexion():
    url = os.environ.get("DATABASE_URL", "").replace("+asyncpg", "")
    if "@" not in url:
        sys.exit("DATABASE_URL absente : rien ne serait lu ni écrit")
    return await asyncpg.connect(url)


async def importer(fichier: str, a_blanc: bool) -> int:
    doc = json.loads(Path(fichier).read_text(encoding="utf-8"))
    conn = await _connexion()
    faits = deja = refus = 0
    tr = conn.transaction()
    await tr.start()
    try:
        depot = C.depot_base(conn)
        for f in doc.get("fiches", []):
            try:
                async with conn.transaction():
                    r = await C.etablir_fiche(
                        depot, f["emetteur"], raison_sociale=f["raison_sociale"], auteur=f["auteur"],
                        motif=f["motif"], le=f["le"], pays=f.get("pays", ""),
                        cotations=[tuple(x) for x in f.get("cotations", [])],
                        references=[tuple(x) for x in f.get("references", [])],
                        lieux=[tuple(x) for x in f.get("lieux", [])], specialite=f.get("specialite", ""))
                faits += 1
                print(f"  fiche    {f['emetteur']:<12} révision {r.revision}")
            except C.ActeRefuse as e:
                if "déjà exactement" in str(e):
                    deja += 1
                    print(f"  fiche    {f['emetteur']:<12} déjà en place")
                else:
                    refus += 1
                    print(f"  REFUS    fiche {f['emetteur']} : {e}")
        for s in doc.get("sources", []):
            try:
                async with conn.transaction():
                    rang = await C.admettre_source(
                        depot, source=s["source"], portee=s["portee"], natures=s["natures"],
                        niveau=s["niveau"], auteur=s["auteur"], motif=s["motif"], le=s["le"],
                        critere=s.get("critere", ""))
                faits += 1
                print(f"  source   {s['source']:<28} {s['portee']:<30} {s['niveau']:<3} rang {rang}")
            except C.ActeRefuse as e:
                if "déjà admise à l'identique" in str(e):
                    deja += 1
                    print(f"  source   {s['source']:<28} déjà en place")
                else:
                    refus += 1
                    print(f"  REFUS    source {s['source']} ({s['portee']}) : {e}")
    finally:
        if a_blanc or refus:
            await tr.rollback()
        else:
            await tr.commit()
        await conn.close()
    etat = "RIEN N'EST GARDÉ (à blanc)" if a_blanc else ("RIEN N'EST GARDÉ (au moins un refus)" if refus else "enregistré")
    print(f"\n{faits} acte(s) joué(s), {deja} déjà en place, {refus} refus — {etat}")
    return 1 if refus else 0


async def montrer(emetteur: str | None) -> int:
    conn = await _connexion()
    try:
        vue = await C.vue_ecran(C.depot_base(conn), emetteur)
    except C.FicheAbsente as e:
        print(e)
        return 2
    finally:
        await conn.close()
    if emetteur is None:
        print(f"{len(vue['emetteurs'])} émetteur(s)")
        for e in vue["emetteurs"]:
            print(f"  {e['emetteur']:<12} {e['raison_sociale']:<40} {e['specialite'] or 'généraliste':<20} "
                  f"révision {e['revision']} du {e['le']}")
        print(f"\nJournal des sources — {len(vue['journal_des_sources'])} acte(s)")
        for a in vue["journal_des_sources"]:
            marque = "en vigueur" if a["en_vigueur"] else ("          " if a["acte"] == C.ADMETTRE else "RÉVOQUE   ")
            print(f"  {a['rang']:>3} {a['le']} {marque} {a['source']:<28} {a['portee']:<30} "
                  f"{a['niveau']:<3} {','.join(a['natures']):<34} {a['auteur']}")
        return 0
    f = vue["fiche"]
    print(f"{f['emetteur']} — {f['raison_sociale']} — pays : {f['pays'] or 'non renseigné'} — "
          f"{f['specialite'] or 'parcours généraliste'}")
    print(f"  révision {f['revision']} du {f['le']} par {f['auteur']} : {f['motif']}")
    for c in f["cotations"]:
        print(f"  cotation : {c['place']} {c['symbole']}")
    for r in f["references"]:
        print(f"  référence : {r['registre']} = {r['valeur']}")
    for l in f["lieux"]:
        print(f"  publie : {l['genre']:<24} {l['adresse']}")
    print(f"  {len(f['sources'])} source(s) admise(s), {len(f['revocations'])} révoquée(s)")
    for s in f["sources"]:
        print(f"    {s['niveau']:<3} {s['source']:<28} {','.join(s['natures']):<34} {s['portee']} ({s['le']}, {s['auteur']})")
    for r in f["revocations"]:
        print(f"    RÉVOQUÉE {r['source']} le {r['le']} par {r['auteur']} : {r['motif']}")
    return 0


async def _pieces(conn, titre: str):
    return await conn.fetch(
        "SELECT id, source_url, nature, source_type FROM knowledge_entries "
        "WHERE ticker_id = $1 AND source_url IS NOT NULL AND btrim(source_url) <> '' ORDER BY id", titre)


async def comparer(emetteur: str, titre: str) -> int:
    # L'ANCIEN code, lu ici comme témoin (un outil a le droit ; un module ne l'aurait pas).
    from app.knowledge.service import RELIABILITY_TABLE
    from app.knowledge.source_registry import admissions_pour
    from app.knowledge.websearch import classify_source_type

    conn = await _connexion()
    try:
        fiche = await C.lire_fiche(C.depot_base(conn), emetteur)
        pieces = await _pieces(conn, titre)
    finally:
        await conn.close()
    if not pieces:
        print(f"aucune pièce avec adresse sous « {titre} » : rien n'est comparé (pas un accord)")
        return 2
    vus: dict[tuple[str, str], list[int]] = {}
    for p in pieces:
        vus.setdefault((p["source_url"], p["nature"]), []).append(p["id"])
    ecarts = 0
    for (adresse, nature), ids in sorted(vus.items()):
        ancien_type = classify_source_type(adresse, titre)
        if ancien_type == "web_search_generic" and any(nature in s.natures for s in admissions_pour(adresse, titre)):
            ancien_type = "web_search_reputable"
        ancien = RELIABILITY_TABLE[ancien_type][0]
        q = C.qualifier(fiche, adresse, nature)
        if ancien != q.niveau:
            ecarts += 1
            print(f"  ÉCART {ancien:<3} → {q.niveau:<3} {nature:<15} {adresse}\n"
                  f"        ancien : {ancien_type} ; fiche : {q.motif} ; pièces {ids[:5]}")
    print(f"\n{len(vus)} couple(s) adresse × nature sur {len(pieces)} pièce(s) de « {titre} » — {ecarts} écart(s)")
    return 1 if ecarts else 0


async def signaler(emetteur: str, titre: str) -> int:
    conn = await _connexion()
    try:
        fiche = await C.lire_fiche(C.depot_base(conn), emetteur)
        pieces = await _pieces(conn, titre)
    finally:
        await conn.close()
    signalees = C.pieces_a_signaler(fiche, [C.Origine(str(p["id"]), p["source_url"], p["nature"]) for p in pieces])
    for s in signalees:
        print(f"  pièce {s.piece:<8} {s.nature:<15} {s.adresse}\n"
              f"        s'appuie sur {s.source}, révoquée le {s.revoquee_le} : {s.motif}")
    print(f"\n{len(signalees)} pièce(s) à relire sur {len(pieces)} — {date.today().isoformat()}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "importer":
        return asyncio.run(importer(argv[1], "--a-blanc" in argv[2:]))
    if argv and argv[0] == "montrer" and len(argv) <= 2:
        return asyncio.run(montrer(argv[1] if len(argv) == 2 else None))
    if len(argv) == 3 and argv[0] in ("comparer", "signaler"):
        return asyncio.run({"comparer": comparer, "signaler": signaler}[argv[0]](argv[1], argv[2]))
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
