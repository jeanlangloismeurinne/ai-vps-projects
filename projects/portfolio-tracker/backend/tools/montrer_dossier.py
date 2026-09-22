"""Montre le DOSSIER tel qu'il part chez l'analyste — en TEXTE, avant toute dépense.

POURQUOI CET OUTIL EXISTE
--------------------------
Le rendu d'un inventaire est un PRODUCTEUR : ce qu'il omet se lit comme une propriété du sujet
(`feedback_rendu_est_un_producteur`). Un dossier qui coupe une pièce fait lire « le corpus ne fonde
pas » là où c'est le plafond qui a tranché. La seule façon de le savoir est de lire le contexte
**tel qu'il part**, en texte, et non de déduire ce qu'il devrait contenir.

Aucun appel de modèle, aucune écriture : lecture de `knowledge_entries` et de `question_coverage`,
puis `assembler_dossier`. C'est la frontière gratuite du lot
(`feedback_frontiere_gratuite_avant_depense_modele`) — à rejouer après CHAQUE correctif, pas une
seule fois au début.

    bash tools/montrer_dossier.sh RVMD qualite_financiere v3.0.0 [plafond]

Codes : 0 = dossier assemblé et imprimé · 1 = un invariant de lecture est rouge · 2 = pas mesurable.
"""
from __future__ import annotations

import asyncio
import os
import sys
import traceback

from app.agents.v2.dossier import charger_dossier
from app.db.database import close_pool, get_db_session, init_pool

PLAFOND_DEFAUT = int(os.environ.get("DOSSIER_PLAFOND", "40"))


async def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    ticker_id, framework_id, framework_version = sys.argv[1], sys.argv[2], sys.argv[3]
    plafond = int(sys.argv[4]) if len(sys.argv) > 4 else PLAFOND_DEFAUT

    url = os.environ.get("DATABASE_URL") or ""
    if not url:
        print("DATABASE_URL manquante — la mesure n'est pas faisable, elle ne se devine pas.",
              file=sys.stderr)
        return 2

    await init_pool(url)
    try:
        async with get_db_session() as conn:
            dossier = await charger_dossier(
                conn,
                ticker_id=ticker_id,
                framework_id=framework_id,
                framework_version=framework_version,
                plafond=plafond,
            )
    finally:
        await close_pool()

    print(f"\n{'─' * 78}")
    print(f"DOSSIER — {ticker_id} · {framework_id} {framework_version} · plafond {plafond}")
    print(f"{'─' * 78}\n")

    print("CHEMISES — un point de la liste du comité par chemise")
    if not dossier.chemises:
        print("   (aucune — aucun lien de couverture pour ce framework sur ce ticker)")
    for ch in dossier.chemises:
        e = dossier.entries[ch.en_vigueur]
        marque = "  " if ch.profondeur == 1 else "≡ "
        print(
            f" {marque}{ch.question_id}.{ch.ingredient_id}\n"
            f"      en vigueur  #{ch.en_vigueur}  {e.get('source_date')}  "
            f"{e.get('reliability_tier')}  {e.get('nature')}  "
            f"{str(e.get('content') or '')[:88].replace(chr(10), ' ')}"
        )
        for anc in ch.anterieures:
            print(f"      antérieure  #{anc}  (en base, non remise)")

    print(f"\nHORS INDEX — {len(dossier.hors_index_retenues)} pièce(s) retenue(s)")
    for i in dossier.hors_index_retenues[:12]:
        e = dossier.entries[i]
        print(
            f"      #{i}  {e.get('source_date')}  {e.get('reliability_tier')}  "
            f"{str(e.get('title') or e.get('content') or '')[:76].replace(chr(10), ' ')}"
        )
    if len(dossier.hors_index_retenues) > 12:
        print(f"      … et {len(dossier.hors_index_retenues) - 12} autre(s)")

    print(f"\n{dossier.bilan()}\n")

    # Invariants de LECTURE — ils portent sur le dossier assemblé, pas sur le code qui l'assemble.
    # Chacun tourne au rouge sur un état réel possible, et aucun n'est un décompte du corpus (§0.6).
    echecs: list[str] = []
    if dossier.plafond_insuffisant:
        echecs.append(
            f"plafond insuffisant : {len(dossier.chemises)} chemise(s) pour un plafond de {plafond}"
        )
    coupees_en_vigueur = {c.en_vigueur for c in dossier.chemises} - set(dossier.entries)
    if coupees_en_vigueur:
        echecs.append(f"pièce(s) en vigueur absente(s) du dossier remis : {sorted(coupees_en_vigueur)}")
    if dossier.total_courantes and not dossier.entries:
        echecs.append("dossier vide alors que le corpus ne l'est pas — un vide n'est jamais un résultat (#25)")

    print(f"{3 - len(echecs)} vérification(s) OK, {len(echecs)} échec(s)")
    for e in echecs:
        print(f"  FAIL {e}")
    return 1 if echecs else 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except Exception:
        traceback.print_exc()
        print("\n0 vérification(s) OK, 1 échec(s)")
        print("  FAIL dossier non mesurable — la panne est dite, elle ne se lit pas « rien à voir »")
        sys.exit(2)
