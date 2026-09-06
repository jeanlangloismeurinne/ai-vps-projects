"""Récupère dans le vault les tours qui ont été dits mais jamais écrits.

Deux pertes distinctes, mesurées le 2026-09-06 :

- **Les 4 « Note de lecture Safran » du 2026-08-24** (15:09 → 15:31). Elles précèdent la capacité 2 :
  `capture_note` n'existait pas, l'agent a répondu en conversation et rien n'a atteint le coffre.
- **La suite « Mémoires de Charles de Gaulle » du 2026-09-06 11:03.** Celle-ci est pire : B1 a bien
  routé le tour jusqu'à l'agent, qui a répondu « Noté. Cette analyse est ajoutée à votre note de
  lecture » — sans appeler un seul outil. Accusé de réception mensonger, zéro octet écrit.

Le seul domicile de ces textes est `agent_conversations`. Ce script les rejoue par le **chemin réel
de l'agent** (classifieur → `write_entry` → index) plutôt que d'écrire des fichiers à la main : une
note récupérée doit être indiscernable d'une note captée, sinon on rejoue le défaut qu'on répare —
des fichiers du coffre dont l'origine ne se lit nulle part.

Les dates et les `slack_ts` d'origine sont conservés : une note de lecture du 24 août n'a rien à
faire dans `notes/2026/2026-09-06-*`. Idempotent par le `content_hash` de l'index (un second passage
ne réécrit rien) — vérifié par `--dry-run`.

Usage (depuis l'hôte) :
    docker cp checks/recover_lost_captures.py assistant-ia:/app/checks/
    docker exec -w /app -e PYTHONPATH=/app assistant-ia python checks/recover_lost_captures.py --dry-run
    docker exec -w /app -e PYTHONPATH=/app assistant-ia python checks/recover_lost_captures.py
"""

import argparse
import asyncio
import sys

from app.db import get_pool
from app.services import journal_kb_classifier, journal_kb_index, journal_vault

NOTES_SUBDIR = "notes"

# Les `slack_ts` des tours à récupérer. Une liste explicite, pas un `WHERE content ILIKE`  : la
# requête large attraperait la note De Gaulle du 06:51 (déjà captée) et tout tour futur contenant
# « note de lecture ». Ce qu'on récupère est un incident daté, pas une catégorie.
A_RECUPERER = [
    "1787584183.445949",   # 08-24 15:09 — stations sol / antennes Safran
    "1787584752.474419",   # 08-24 15:19 — optique vs radar
    "1787585425.343049",   # 08-24 15:30 — EU Space Act comme levier commercial
    "1787585482.055389",   # 08-24 15:31 — propulsion électrique comme service
    "1788692599.025349",   # 09-06 11:03 — suite De Gaulle, perdue malgré B1
]


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="classe et affiche, n'écrit ni dans le coffre ni dans l'index")
    args = parser.parse_args()

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT slack_ts, created_at, content
              FROM agent_conversations
             WHERE role = 'user' AND slack_ts = ANY($1::text[])
             ORDER BY created_at
            """,
            A_RECUPERER,
        )

    manquants = set(A_RECUPERER) - {r["slack_ts"] for r in rows}
    if manquants:
        # Un tour introuvable est un échec, pas un saut de section : le texte n'existe alors nulle
        # part et le silence ferait croire la récupération complète.
        print(f"ECHEC — tours introuvables dans agent_conversations : {sorted(manquants)}")
        return 1

    print(f"{len(rows)} tour(s) à récupérer\n" + "=" * 70)
    ecrites, deja, echecs = 0, 0, 0

    for row in rows:
        contenu = row["content"].replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")
        apercu = contenu[:70].replace("\n", " ")
        print(f"\n— {row['created_at']:%Y-%m-%d %H:%M}  {apercu}…")

        hash_ = journal_kb_index.content_hash(contenu)
        existant = await journal_kb_index.find_duplicate(hash_)
        if existant:
            print(f"  déjà dans l'index : {existant}")
            deja += 1
            continue

        classe = await journal_kb_classifier.classify(contenu)
        print(f"  titre    : {classe.title!r}")
        print(f"  contexte : {classe.contexte} · nature : {classe.nature}")
        print(f"  tags     : {classe.tags}" + ("  [FALLBACK]" if classe.is_fallback else ""))

        if args.dry_run:
            continue

        try:
            entry = await journal_vault.write_entry(
                title=classe.title,
                body=contenu,
                contexte=classe.contexte,
                nature=classe.nature,
                tags=classe.tags,
                created_at=row["created_at"],
                slack_ts=row["slack_ts"],
                subdir=NOTES_SUBDIR,
            )
            await journal_kb_index.upsert(
                doc_id=entry.doc_id,
                uri=entry.relative_path,
                title=classe.title,
                body=contenu,
                contexte=classe.contexte,
                nature=classe.nature,
                tags=classe.tags,
                hash_=hash_,
                slack_ts=row["slack_ts"],
            )
            print(f"  écrite   : {entry.relative_path}")
            ecrites += 1
        except Exception as exc:
            print(f"  ECHEC    : {exc}")
            echecs += 1

    print("\n" + "=" * 70)
    print(f"BILAN — écrites={ecrites} déjà_présentes={deja} échecs={echecs}")
    return 1 if echecs else 0


sys.exit(asyncio.run(main()))
