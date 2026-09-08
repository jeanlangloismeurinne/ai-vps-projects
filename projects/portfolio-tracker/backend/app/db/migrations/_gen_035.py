"""Générateur de `035_v2_poste_kind_backfill.sql` — F16 : un fait porte lui-même sa nature de poste.

LE DÉFAUT, MESURÉ (2026-09-08)
------------------------------
La clef d'identité d'un fait (#43) dépend du type de poste : un **flux** s'identifie par
`(metric, period_end)` — le CA de FY2024 et celui de FY2025 sont deux faits légitimes qui
coexistent — tandis qu'un poste de **bilan** s'identifie par `metric` SEUL, parce qu'il n'y a qu'un
bilan courant et qu'un instant plus ancien est *périmé*, pas *historique*.

`_current_fact_ids` applique cette règle correctement, mais il tient le discriminant de la **spec du
producteur**, qui le connaît. Un **LECTEUR** du corpus, lui, ne dispose que de la ligne stockée — et
`content_structured.poste_kind` est absent de **tout le socle NVDA et MSFT**, écrit avant le
correctif F4. Mesuré : **19 des 43 faits financiers courants** ne sont pas keyables par un lecteur.

C'est le mode de panne de #48 transposé : la règle est juste dans le producteur, mais son porteur
n'est pas dans la ligne. Toute garantie du type « une seule vérité chiffrée à un instant donné »
serait donc **silencieusement aveugle sur deux émetteurs sur trois** — et une garantie aveugle est
pire qu'une garantie absente, parce qu'elle rassure.

⚠️ Le premier outil de mesure de ce défaut le fabriquait : en coerçant un `poste_kind` absent en
`stock`, il lisait les trois exercices de CA de NVDA comme trois réponses à une même question et
sortait deux collisions imaginaires. Un rouge fabriqué coûte aussi cher qu'un vert fabriqué
(#44/#53 : l'indécidable est un troisième état, jamais un repli sur l'un des deux autres).

POURQUOI UN GÉNÉRATEUR PLUTÔT QU'UN `UPDATE ... CASE WHEN`
----------------------------------------------------------
Écrire `CASE WHEN metric IN ('stockholders_equity', …)` en SQL ré-implémenterait `POSTES[].flow`
dans un second langage — exactement le jumeau que ce chantier passe son temps à supprimer (#46).
La règle n'existe qu'une fois, dans `edgar_feed.POSTES` ; le SQL produit ne contient que des listes
d'ids, qui se relisent et se comptent.

CE QUE LE BACKFILL NE TOUCHE PAS, ET POURQUOI C'EST VOULU
----------------------------------------------------------
Seuls les **postes du socle EDGAR** (ceux de `POSTES`) sont concernés. Les métriques dérivées
(`roic`, `levier`, `fcf_conversion`, `cash_burn`, `intensite_capex`) et les données de marché
(`prix_actuel`, `relatif_multiple`, source `yfinance`) ne relèvent PAS de la clef #43 : ce sont des
grandeurs *calculées* ou *d'actualité*, pas la vérité réglementaire déposée. Leur `poste_kind`, quand
il existe, est écrit par leur propre producteur (`financials_feed` le pose déjà sur `levier`, #42).
Les inventer ici leur donnerait une identité réglementaire qu'elles n'ont pas.

Le backfill couvre en revanche **toutes** les lignes, courantes ET superseded : une entry superseded
reste lue par `analysis_knowledge_refs` (snapshot figé A1/A2), et un lecteur qui remonte une lignée
doit pouvoir la keyer comme le reste.

REPRODUCTIBILITÉ
----------------
Le générateur ne parle pas à la base : il lit un instantané `psql -tA` (séparateur `|`), ce qui le
rend rejouable hors ligne et rend l'instantané citable dans la revue.

    cd projects/portfolio-tracker/backend
    docker exec shared-postgres psql -U admin -d db_portfolio -tAc \
      "SELECT id, source_type, coalesce(content_structured->>'metric',''), \
              coalesce(content_structured->>'poste_kind','') \
       FROM knowledge_entries WHERE entry_type='fact_financial' \
         AND content_structured->>'metric' IS NOT NULL ORDER BY id" > /tmp/facts_035.tsv
    IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
    docker run --rm --network none -v "$PWD:/app:ro" -v /tmp/facts_035.tsv:/tmp/f.tsv:ro \
      -w /app -e PYTHONPATH=/app --env-file checks/env.checks $IMG \
      python app/db/migrations/_gen_035.py /tmp/f.tsv > app/db/migrations/035_v2_poste_kind_backfill.sql
"""
from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict

from app.knowledge.edgar_feed import POSTES

# Détenteur unique de « ce poste est-il un flux ou un bilan ? » — importé, jamais recopié (#46).
KIND_PAR_METRIC = {p.metric: ("flow" if p.flow else "stock") for p in POSTES}
SOURCE_REGLEMENTAIRE = "edgar_official"


def main(path: str) -> None:
    a_ecrire: dict[str, list[int]] = defaultdict(list)
    deja: Counter[str] = Counter()
    hors_perimetre: Counter[tuple[str, str]] = Counter()
    incoherences: list[tuple[int, str, str, str]] = []

    with open(path, newline="") as fh:
        for row in csv.reader(fh, delimiter="|"):
            if not row or not row[0]:
                continue
            entry_id, source_type, metric, kind_stocke = int(row[0]), row[1], row[2], row[3]

            attendu = KIND_PAR_METRIC.get(metric)
            if source_type != SOURCE_REGLEMENTAIRE or attendu is None:
                hors_perimetre[(source_type, metric)] += 1
                continue

            if not kind_stocke:
                a_ecrire[attendu].append(entry_id)
            elif kind_stocke != attendu:
                # Une ligne qui porte DÉJÀ un `poste_kind` contredisant `POSTES` serait un défaut
                # d'un tout autre ordre — le producteur et la table divergeraient. On ne l'écrase
                # pas en silence : on refuse d'émettre la migration.
                incoherences.append((entry_id, metric, kind_stocke, attendu))
            else:
                deja[attendu] += 1

    if incoherences:
        for eid, metric, stocke, attendu in incoherences:
            print(f"INCOHÉRENCE #{eid} {metric} : stocké `{stocke}`, POSTES dit `{attendu}`",
                  file=sys.stderr)
        sys.exit("035 non émise — le producteur et POSTES divergent, ce backfill ne peut pas trancher.")

    total = sum(len(v) for v in a_ecrire.values())
    out = sys.stdout.write

    out("-- 035 — V2 : F16, un fait financier porte lui-même sa nature de poste (`poste_kind`).\n")
    out("--       GÉNÉRÉ par `_gen_035.py`, ne pas éditer à la main : le backfill est calculé par\n")
    out("--       `edgar_feed.POSTES`, détenteur unique de la règle flux/bilan (#46).\n")
    out("--\n")
    out("-- POURQUOI. La clef d'identité d'un fait (#43) dépend du type de poste. `_current_fact_ids`\n")
    out("-- le tient de la spec du PRODUCTEUR ; un LECTEUR du corpus n'a que la ligne. Mesuré avant\n")
    out("-- migration : 19 des 43 faits financiers courants (tout le socle NVDA et MSFT, écrit avant\n")
    out("-- F4) ne portaient pas leur `poste_kind` — donc toute garantie « une seule vérité chiffrée\n")
    out("-- à un instant donné » y était silencieusement aveugle.\n")
    out("--\n")
    out("-- PÉRIMÈTRE. Postes du socle EDGAR uniquement. Les métriques dérivées (roic, levier,\n")
    out("-- fcf_conversion…) et les données de marché (yfinance) ne relèvent pas de la clef #43 :\n")
    out("-- ce sont des grandeurs calculées ou d'actualité, pas la vérité réglementaire déposée.\n")
    out("--\n")
    out(f"-- Lignes écrites : {total}")
    out("".join(f" · {k}={len(v)}" for k, v in sorted(a_ecrire.items())))
    out(f"\n-- Lignes déjà conformes (laissées intactes) : {sum(deja.values())}")
    out("".join(f" · {k}={v}" for k, v in sorted(deja.items())))
    out(f"\n-- Lignes hors périmètre (aucune identité réglementaire) : {sum(hors_perimetre.values())}\n")
    for (st, metric), n in sorted(hors_perimetre.items()):
        out(f"--     {st}/{metric or '<sans metric>'} : {n}\n")
    out("\nBEGIN;\n\n")

    for kind, ids in sorted(a_ecrire.items()):
        if not ids:
            continue
        out(f"-- {len(ids)} fait(s) de type `{kind}`\n")
        out("UPDATE knowledge_entries\n")
        out(f"   SET content_structured = content_structured || '{{\"poste_kind\": \"{kind}\"}}'::jsonb\n")
        out(f" WHERE id = ANY(ARRAY[{','.join(str(i) for i in ids)}]::int[])\n")
        # Garde d'idempotence : un rejeu ne doit rien réécrire, et surtout ne doit pas écraser un
        # `poste_kind` qu'un producteur aurait posé entre-temps.
        out("   AND NOT (content_structured ? 'poste_kind');\n\n")

    out("-- Vérification NOMMÉE, dans la transaction : si un poste du socle reste sans `poste_kind`,\n")
    out("-- la migration échoue au lieu de laisser le trou se refermer en silence sur un COMMIT vert.\n")
    out("DO $$\n")
    out("DECLARE restants INT;\n")
    out("BEGIN\n")
    out("  SELECT count(*) INTO restants FROM knowledge_entries\n")
    out("   WHERE entry_type = 'fact_financial' AND source_type = 'edgar_official'\n")
    out(f"     AND content_structured->>'metric' = ANY(ARRAY[{','.join(repr(m) for m in sorted(KIND_PAR_METRIC))}])\n")
    out("     AND NOT (content_structured ? 'poste_kind');\n")
    out("  IF restants > 0 THEN\n")
    out("    RAISE EXCEPTION '035 : % poste(s) du socle EDGAR sans poste_kind après backfill', restants;\n")
    out("  END IF;\n")
    out("END $$;\n\n")
    out("COMMIT;\n")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
