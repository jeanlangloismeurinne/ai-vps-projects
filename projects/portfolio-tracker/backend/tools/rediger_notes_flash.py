"""Rédige les NOTES FLASH des dépôts d'un émetteur que la forme ne qualifie pas (V3 lot 7, maillon 2).

    bash tools/rediger_notes_flash.sh RVMD                      # LECTURE GRATUITE : rien n'est envoyé au modèle
    bash tools/rediger_notes_flash.sh RVMD --ecrire             # le modèle lit, le pont valide, la base garde
    bash tools/rediger_notes_flash.sh RVMD --depuis 2025-06-01 --limite 5 [--ecrire]

Sans `--ecrire`, l'outil fait tout ce qui ne coûte rien — il liste les dépôts `a_qualifier` non encore
lus, télécharge leur soumission EDGAR et imprime EN TEXTE ce que le modèle lirait (types et tailles des
documents, début du texte). C'est la frontière gratuite (`feedback_frontiere_gratuite_avant_depense_modele`).

Avec `--ecrire`, chaque dépôt est lu par le modèle, validé par le pont, et PERSISTÉ (`notes_flash`,
append-only, migration 050). L'outil imprime chaque note en texte (types, passages cités, motif) et
l'INVENTAIRE NOMMÉ des ids écrits. ⚠️ LE VERDICT EST À LA LECTURE : une note bien formée peut classer
un dépôt dans le mauvais type en citant un vrai passage — relire chaque note contre son dépôt.

Un dépôt refusé (pont, EDGAR) n'écrit RIEN : il reste `a_qualifier`, donc il rouvre tout (Q3).
Codes : 0 = parcours terminé (refus compris, nommés) · 2 = pas exécutable (env, titre inconnu).
"""
from __future__ import annotations

import asyncio
import os
import sys
import traceback
from datetime import date, timedelta

from app.agents.v2.frameworks import load_frameworks
from app.agents.v2.note_flash import (
    NoteFlashImpossible, NoteFlashRefusee, depots_a_lire, extraire_documents, persister_note,
    qualifications_de_l_emetteur, rediger_note_flash, telecharger_soumission)
from app.db.database import close_pool, get_db_session, init_pool
from app.knowledge.edgar_feed import identite_de_l_emetteur
from app.knowledge.material_events import material_anchor_for_ticker

L = 78
_PAUSE_EDGAR_S = 0.3   # accès équitable à EDGAR : jamais deux soumissions dans la même seconde


def _args(argv: list[str]) -> tuple[str, bool, date, int]:
    ticker = argv[0]
    ecrire = "--ecrire" in argv
    depuis = date.today() - timedelta(days=400)
    limite = 50
    if "--depuis" in argv:
        depuis = date.fromisoformat(argv[argv.index("--depuis") + 1])
    if "--limite" in argv:
        limite = int(argv[argv.index("--limite") + 1])
    return ticker, ecrire, depuis, limite


async def main() -> int:
    if not sys.argv[1:]:
        print(__doc__)
        return 2
    ticker_id, ecrire, depuis, limite = _args(sys.argv[1:])
    if not os.environ.get("DATABASE_URL"):
        print("DATABASE_URL manquante", file=sys.stderr)
        return 2
    if ecrire and not os.environ.get("DEEPINFRA_API_KEY"):
        print("DEEPINFRA_API_KEY manquante — refus AVANT toute écriture", file=sys.stderr)
        return 2
    fichier = load_frameworks()
    await init_pool(os.environ["DATABASE_URL"])
    ecrits: list[tuple[int, str, tuple[str, ...]]] = []
    refus: list[tuple[str, str]] = []
    cout = 0.0
    try:
        async with get_db_session() as conn:
            emetteur = await identite_de_l_emetteur(conn, ticker_id)
            flux = await material_anchor_for_ticker(conn, ticker_id)
            if flux.status != "found" or flux.cik is None:
                print(f"flux EDGAR {flux.status} pour {ticker_id} : {flux.raison or 'aucun dépôt'}")
                return 2
            deja = await qualifications_de_l_emetteur(conn, flux.cik, fichier)
            a_lire = depots_a_lire(flux, deja, depuis=depuis)[:limite]
            print(f"{'─' * L}\nNOTES FLASH — {emetteur.raison_sociale} ({ticker_id}, CIK {flux.cik}) · "
                  f"catalogue d'événements {fichier.types_evenement_version}\n  {len(a_lire)} dépôt(s) à lire depuis le "
                  f"{depuis} · {len(deja)} déjà lu(s) · mode {'ÉCRITURE' if ecrire else 'lecture gratuite'}"
                  f"\n{'─' * L}")
            for e in a_lire:
                print(f"\n▸ {e.resume()}  [{e.accession}]")
                try:
                    soum = await telecharger_soumission(flux.cik, e.accession)
                    await asyncio.sleep(_PAUSE_EDGAR_S)
                    docs = extraire_documents(soum)
                    for d in docs:
                        print(f"    {d.type:<8} {d.nom:<28} {d.taille:>6} car."
                              f"{' (TRONQUÉ)' if d.tronque else ''}")
                    if not ecrire:
                        if docs:
                            print(f"    « {docs[0].texte[:420].replace(chr(10), ' ')} »")
                        continue
                    red = await rediger_note_flash(e, ticker_id=ticker_id, cik=flux.cik,
                                                   emetteur=emetteur, fichier=fichier, soumission=soum)
                    cout += sum(r.cost_usd for r in red.runs)
                    n = red.note
                    if n.lisible:
                        for el in n.elements:
                            cause = f" · cause {el['cause']}" if el.get("cause") else ""
                            print(f"    → {el['type']}{cause} : « {el['passage'][:220]} »")
                            if el.get("passage_cause"):
                                print(f"        cause citée : « {el['passage_cause'][:200]} »")
                    else:
                        print(f"    → ILLISIBLE : {n.motif}")
                    async with conn.transaction():
                        i = await persister_note(conn, red)
                    ecrits.append((i, e.accession, n.types))
                    print(f"    ✔ note #{i} — types retenus : {', '.join(n.types)}"
                          f"{' (après une correction)' if len(red.runs) > 1 else ''}")
                except (NoteFlashImpossible, NoteFlashRefusee) as ex:
                    refus.append((e.accession, f"{type(ex).__name__} : {ex}"))
                    print(f"    ✘ {type(ex).__name__} : {ex} — le dépôt reste à qualifier")
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return 2
    finally:
        await close_pool()

    print(f"\n{'─' * L}\nINVENTAIRE — {len(ecrits)} note(s) écrite(s), {len(refus)} refus, "
          f"coût modèle ${cout:.4f}\n{'─' * L}")
    for i, acc, types in ecrits:
        print(f"  notes_flash #{i}  {acc}  {', '.join(types)}")
    for acc, motif in refus:
        print(f"  REFUS  {acc}  {motif[:160]}")
    print("\n⚠️ LE VERDICT EST À LA LECTURE : relire chaque passage contre son dépôt.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
