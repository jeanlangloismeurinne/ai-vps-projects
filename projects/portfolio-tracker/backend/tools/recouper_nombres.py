"""Recoupe CHAQUE nombre d'une réponse rédigée avec le texte des pièces qu'elle cite — en lecture
seule, sans modèle (méthode de relecture des jalons A3/A4 de `05-frameworks-complets.md`).

Pourquoi un outil : les quatre contrôles du manager gardent la STRUCTURE, jamais le sens (#78) ; un
`repondu` peut porter un chiffre calculé ou tiré d'une pièce NON citée (D-me6). Relire à la main
chaque nombre contre chaque pièce ne se refait pas deux fois de la même façon ; cet outil le refait
à l'identique (A10/A11 : comparer deux passages).

    bash tools/recouper_nombres.sh RVMD management_capital          # réponses courantes du chapitre
    bash tools/recouper_nombres.sh RVMD management_capital --ids 1451,1452

La règle n'est PAS ici : elle vit dans `app.agents.v2.recoupement` (#136), le détenteur unique que lisent
aussi l'analyste (la remarque renvoyée une fois) et le point de lecture (le signalement au comité).
L'outil n'ajoute que la lecture : pour chaque chiffre « ABSENT des pièces citées », l'id des pièces
COURANTES du titre qui le portent (signe d'une citation manquante — jamais une citation à rattacher :
un chiffre porté par plusieurs pièces ne dit pas laquelle le fonde).

⚠️ Il n'asserte rien : un ABSENT est une ligne À LIRE, pas un verdict. Codes : 0 = recoupé · 2 = pas lisible.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

from app.agents.v2.recoupement import pieces_citees, pieces_qui_portent, recouper


async def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    ticker, fw = sys.argv[1], sys.argv[2]
    ids = None
    if "--ids" in sys.argv:
        ids = [int(x) for x in sys.argv[sys.argv.index("--ids") + 1].split(",")]
    import asyncpg

    url = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg", "postgresql")
    if not url:
        print("DATABASE_URL manquante", file=sys.stderr)
        return 2
    conn = await asyncpg.connect(url)
    try:
        if ids:
            rows = await conn.fetch(
                "SELECT id, question_id, statut, answer_json FROM framework_answers "
                "WHERE id = ANY($1) ORDER BY question_id", ids)
        else:
            rows = await conn.fetch(
                "SELECT id, question_id, statut, answer_json FROM framework_answers "
                "WHERE ticker_id=$1 AND framework=$2 AND superseded_by IS NULL ORDER BY question_id",
                ticker, fw)
        corpus = {r["id"]: dict(r) for r in await conn.fetch(
            "SELECT id, title, content FROM knowledge_entries WHERE ticker_id=$1 AND superseded_by IS NULL",
            ticker)}
        n_abs = n_tot = n_enc = n_calc = n_lib = 0
        for row in rows:
            a = row["answer_json"]
            if isinstance(a, str):
                a = json.loads(a)
            cites = pieces_citees(a)
            print(f"\n── #{row['id']} {row['question_id']} [{row['statut']}] cite {cites}")
            manq = [c for c in cites if c not in corpus]
            if manq:
                print(f"   ⚠ pièces citées hors du corpus courant du titre : {manq}")
            r = recouper(a, corpus)
            for motif in r.calculs_refuses:
                print(f"   CALCUL ÉCARTÉ — {motif}")
            for c in r.sans_piece:
                ailleurs = pieces_qui_portent(c.jeton, corpus, exclure=cites)
                note = f" — porté par #{', #'.join(map(str, ailleurs[:4]))} (non citée)" if ailleurs else ""
                print(f"   ABSENT [{c.lieu}] {c.jeton!r}{note}\n          « …{c.extrait}… »")
            n_tot += r.n_recoupes
            n_abs += len(r.sans_piece)
            n_enc += r.n_encadre
            n_calc += r.n_calcul
            n_lib += r.n_libelle
        print(f"\nBILAN — {len(rows)} réponse(s), {n_tot} nombre(s) recoupé(s), {n_abs} absent(s) des pièces "
              f"citées ({n_enc} repris de l'encadré, {n_calc} calcul(s) montré(s), {n_lib} libellé(s) ou "
              "date(s) — non comptés absents)")
    finally:
        await conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
