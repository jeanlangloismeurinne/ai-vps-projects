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
La lecture elle-même vit dans `note_flash.lire_les_depots_en_attente` (détenteur unique) : c'est la
même que celle du passage du matin et du passage de la chaîne (arbitrage 2026-09-26, option c).

Codes : 0 = parcours terminé (refus compris, nommés) · 2 = pas exécutable (env, titre inconnu).
"""
from __future__ import annotations

import asyncio
import os
import sys
import traceback
from datetime import date

from app.agents.v2.frameworks import load_frameworks
from app.agents.v2.note_flash import FENETRE, LIMITE_PAR_PASSAGE, lire_les_depots_en_attente
from app.db.database import close_pool, get_db_session, init_pool


def _args(argv: list[str]) -> tuple[str, bool, date, int]:
    ticker = argv[0]
    ecrire = "--ecrire" in argv
    depuis = date.today() - FENETRE
    limite = LIMITE_PAR_PASSAGE
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
    await init_pool(os.environ["DATABASE_URL"])
    try:
        async with get_db_session() as conn:
            lecture = await lire_les_depots_en_attente(
                conn, ticker_id, ecrire=ecrire, depuis=depuis, limite=limite, apercu=True,
                fichier=load_frameworks())
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return 2
    finally:
        await close_pool()
    print(lecture.texte())
    if lecture.hors_flux:
        return 2
    print("\n⚠️ LE VERDICT EST À LA LECTURE : relire chaque passage contre son dépôt.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
