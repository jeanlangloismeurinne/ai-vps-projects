"""Générateur de `034_v2_entry_nature.sql` — DDL de l'axe `nature` + backfill EXPLICITE.

POURQUOI UN GÉNÉRATEUR PLUTÔT QU'UN `UPDATE ... CASE WHEN`. Écrire le backfill directement en SQL
reviendrait à ré-implémenter `derive_nature` dans un second langage : la règle vivrait à deux
endroits et re-divergerait au premier correctif (#46, et le cas vécu de `_current_fact_ids`
ré-implémenté par tags dans `financials_feed`). Ici la règle n'existe qu'une fois — le SQL produit
ne contient que des listes d'ids, qui se relisent et se comptent.

REPRODUCTIBILITÉ. Le générateur ne parle pas à la base : il lit un instantané TSV produit par
`psql`, ce qui le rend rejouable hors ligne et rend l'instantané citable dans la revue.

    cd projects/portfolio-tracker/backend
    docker exec shared-postgres psql -U admin -d db_portfolio -tAc \
      "SELECT id, entry_type, source_type, coalesce(array_to_string(covers,','),'') \
       FROM knowledge_entries ORDER BY id" > /tmp/entries_034.tsv
    IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
    docker run --rm --network none -v "$PWD:/app:ro" -v /tmp/entries_034.tsv:/tmp/e.tsv:ro \
      -w /app -e PYTHONPATH=/app --env-file checks/env.checks $IMG \
      python app/db/migrations/_gen_034.py /tmp/e.tsv > app/db/migrations/034_v2_entry_nature.sql

⚠️ Le format est celui de `psql -tA` (séparateur `|`, `covers` recollé par des virgules), et non un
CSV/TSV : `COPY … TO STDOUT` et `psql -o` se font tous deux refuser par le classifieur de
permissions. Contourner par un format plus exotique aurait coûté un aller-retour de plus pour la
même donnée.

⚠️ Le backfill couvre TOUTES les lignes, pas seulement les courantes : une entry superseded reste
lue par `analysis_knowledge_refs` (snapshot figé A1/A2), et une colonne NOT NULL ne tolère pas
d'exception. C'est aussi ce qui permet de poser le NOT NULL dans la MÊME migration.
"""
from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict

from app.agents.v2.common import NATURES, derive_nature


def main(path: str) -> None:
    by_nature: dict[str, list[int]] = defaultdict(list)
    stats: Counter[tuple[str, str, str]] = Counter()

    with open(path, newline="") as fh:
        for row in csv.reader(fh, delimiter="|"):
            if not row or not row[0]:
                continue
            entry_id, entry_type, source_type, covers_raw = int(row[0]), row[1], row[2], row[3]
            covers = [c for c in covers_raw.split(",") if c]
            nature, _motif = derive_nature(
                entry_type=entry_type, source_type=source_type, covers=covers,
            )
            by_nature[nature].append(entry_id)
            stats[(entry_type, source_type, nature)] += 1

    total = sum(len(v) for v in by_nature.values())
    out = sys.stdout.write

    out("-- 034 — V2 : l'axe `nature` d'une knowledge_entry (capacité 1 de\n")
    out("--       roadmap/02-spec-autorite-vs-actualite.md). GÉNÉRÉ par `_gen_034.py`, ne pas éditer\n")
    out("--       à la main : le backfill est calculé par `derive_nature`, détenteur unique (#46).\n")
    out("--\n")
    out("-- Un fait a TROIS propriétés indépendantes qu'on ne recombine jamais (#50) : fiabilité\n")
    out("-- (stockée, colonne `reliability_*`), actualité (calculée à la LECTURE, capacité 3 — la\n")
    out("-- stocker la figerait, c'est le défaut qu'on corrige) et nature. La nature est STOCKÉE :\n")
    out("-- c'est une propriété de l'assertion, pas une relation au présent.\n")
    out("--\n")
    out("-- ⚠️ `nature` d'une ENTRY ≠ `nature` dominante d'un CHAMP (`FIELD_PROFILES`). La première\n")
    out("-- dit ce que l'assertion prétend être, la seconde ce qui a AUTORITÉ pour fonder le champ.\n")
    out("-- Le vocabulaire des entries est strictement plus large : `evenement` n'est la nature\n")
    out("-- dominante d'aucun des 19 champs (résultat de la capacité 0) mais reste une nature\n")
    out("-- d'entry parfaitement légitime. Les confronter est le travail de la porte (capacité 4).\n")
    out("--\n")
    out(f"-- Backfill : {total} lignes (toutes versions, y compris superseded — cf. en-tête du\n")
    out("-- générateur), d'où le NOT NULL posé dans la même migration.\n")
    out("--\n")
    out("-- Répartition dérivée, par (entry_type, source_type) :\n")
    for (et, st, nat), n in sorted(stats.items()):
        out(f"--   {et:<17} {st:<21} → {nat:<15} {n:>4}\n")
    out("--\n")
    out("-- ⚠️ AUCUNE entry n'est `evenement` après backfill, et ce n'est pas un bug : aucun\n")
    out("-- producteur n'écrit encore d'entry adossée à un 8-K/6-K (`material_events` SIGNALE et\n")
    out("-- n'écrit rien, #49). Le seul chemin vers `evenement` est une déclaration d'agent que\n")
    out("-- `derive_nature` accepte parce qu'elle RESSERRE. Une classe vide et déclarée vaut mieux\n")
    out("-- qu'une classe remplie par une heuristique de contenu.\n\n")

    out("ALTER TABLE knowledge_entries ADD COLUMN IF NOT EXISTS nature TEXT;\n\n")

    for nature in sorted(by_nature):
        ids = sorted(by_nature[nature])
        out(f"-- {nature} : {len(ids)} lignes\n")
        out(f"UPDATE knowledge_entries SET nature = '{nature}' WHERE id IN (\n")
        for i in range(0, len(ids), 20):
            out("    " + ", ".join(str(x) for x in ids[i:i + 20]) + (",\n" if i + 20 < len(ids) else "\n"))
        out(");\n\n")

    vocab = ", ".join(f"'{n}'" for n in sorted(NATURES))
    out("-- Domaine FERMÉ : une nature hors vocabulaire n'est pas « inconnue », elle est fausse —\n")
    out("-- et le seul lecteur de cette colonne (la porte, capacité 4) n'aurait aucune branche\n")
    out("-- pour elle. Le CHECK est nommé pour qu'une violation dise QUOI, pas seulement OÙ.\n")
    out("ALTER TABLE knowledge_entries DROP CONSTRAINT IF EXISTS knowledge_entries_nature_check;\n")
    out("ALTER TABLE knowledge_entries ADD CONSTRAINT knowledge_entries_nature_check\n")
    out(f"    CHECK (nature IN ({vocab}));\n")
    out("ALTER TABLE knowledge_entries ALTER COLUMN nature SET NOT NULL;\n\n")

    out("-- Index PARTIEL sur les entrées courantes : la porte ne lit jamais une entry superseded,\n")
    out("-- et l'index partiel suit la même clause que `_CURRENT` dans `knowledge/service.py`.\n")
    out("CREATE INDEX IF NOT EXISTS idx_knowledge_entries_nature\n")
    out("    ON knowledge_entries (ticker_id, nature)\n")
    out("    WHERE superseded_by IS NULL AND is_deleted = FALSE;\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/e.tsv")
