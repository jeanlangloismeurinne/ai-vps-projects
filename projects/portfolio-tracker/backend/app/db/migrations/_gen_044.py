"""Générateur de `044_v2_nature_derivations_annoncees.sql` — REJEU de `derive_nature` après
l'entrée de `content` dans la règle (garde du guichet, #78).

POURQUOI UN GÉNÉRATEUR PLUTÔT QU'UN `UPDATE … WHERE content ILIKE '%…%'`. Le SQL naïf serait ici
particulièrement tentant : le vocabulaire de marqueurs ressemble à une clause `ILIKE`. Ce serait
ré-implémenter `annonce_une_derivation` dans un second langage — la règle vivrait à deux endroits,
et le jour où un marqueur s'ajoute ou s'écarte, la base et le code diraient deux choses (#46).
Ici la règle n'existe qu'une fois : le SQL produit ne contient que des listes d'ids, qui se
relisent et se comptent.

⚠️ ET SURTOUT, LE SQL NAÏF SERAIT **FAUX**, pas seulement mal rangé. `derive_nature` n'est pas la
recherche d'un marqueur : le filtre `_NON_MEASURING_SOURCES` passe AVANT, et `declared` arbitre
APRÈS. Un `ILIKE` rétrograderait des entries qui étaient déjà `interpretation` (sans effet, mais il
les compterait) et surtout il manquerait l'ordre de priorité. On rejoue donc la fonction entière,
ligne par ligne, et on n'émet QUE les lignes dont la nature CHANGE.

REPRODUCTIBILITÉ. Le générateur ne parle pas à la base : il lit un instantané produit par `psql`,
ce qui le rend rejouable hors ligne et rend l'instantané citable dans la revue.

⚠️ Le format est **JSON par ligne**, et pas le `psql -tA` (séparateur `|`) des générateurs 034/035 :
`content` est de la prose multi-lignes qui contient des `|` et des retours chariot, donc tout format
à délimiteur la découperait en silence — une ligne tronquée perdrait son marqueur et se lirait
« cette entry n'est pas une dérivation ». Un faux vert par format, exactement le mode de panne que
`feedback_fixture_copiee_du_reel` décrit.

    cd projects/portfolio-tracker/backend
    docker exec shared-postgres psql -U admin -d db_portfolio -tAc \
      "SELECT json_build_object('id',id,'entry_type',entry_type,'source_type',source_type,\
       'content',content,'nature',nature)::text FROM knowledge_entries ORDER BY id" \
      > /tmp/entries_044.json
    IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
    docker run --rm --network none -v "$PWD:/app:ro" -v /tmp/entries_044.json:/tmp/e.json:ro \
      -w /app -e PYTHONPATH=/app --env-file checks/env.checks $IMG \
      python app/db/migrations/_gen_044.py /tmp/e.json \
      > app/db/migrations/044_v2_nature_derivations_annoncees.sql

⚠️ Le rejeu couvre TOUTES les lignes, pas seulement les courantes — même raison qu'en 034 : une
entry superseded reste lue par `analysis_knowledge_refs` (snapshot figé A1/A2), et la colonne est
NOT NULL. Une entry qui mentait sur son statut ne cesse pas d'avoir menti parce qu'elle a été
remplacée.

⚠️ CE QUE LA MIGRATION NE FAIT PAS : elle ne touche NI `reliability_tier`, NI `reliability_score`.
La fiabilité est une propriété de la SOURCE, la nature une propriété de l'ASSERTION (#50). Le dépôt
reste un dépôt tier A ; c'est la phrase qu'on en a tirée qui n'est pas un relevé. Confondre les deux
axes ici serait le geste que toute la doctrine des trois axes interdit.
"""
from __future__ import annotations

import json
import sys
from collections import Counter

from app.agents.v2.common import annonce_une_derivation, derive_nature


def main(path: str) -> None:
    changements: list[tuple[int, str, str, str]] = []  # (id, avant, apres, marqueur)
    par_marqueur: Counter[str] = Counter()
    total = 0
    inchangees = 0
    total_mesure = 0  # ce que la RÈGLE prédit, pas ce que la base contient aujourd'hui

    with open(path, encoding="utf-8") as fh:
        for ligne in fh:
            ligne = ligne.strip()
            if not ligne:
                continue
            row = json.loads(ligne)
            total += 1
            avant = row["nature"]
            # La règle ENTIÈRE est rejouée, pas seulement sa nouvelle branche : c'est ce qui rend
            # la migration un REJEU et non un correctif ponctuel. `declared` n'est pas passé — il
            # n'est pas stocké, donc il n'est pas rejouable, et la 034 avait déjà tranché ainsi.
            apres, _motif = derive_nature(
                entry_type=row["entry_type"],
                source_type=row["source_type"],
                content=row["content"],
            )
            if apres == "mesure":
                total_mesure += 1
            if apres == avant:
                inchangees += 1
                continue
            marqueur = annonce_une_derivation(row["content"]) or "—"
            changements.append((row["id"], avant, apres, marqueur))
            par_marqueur[marqueur] += 1

    out = sys.stdout.write
    out("-- 044 — V2 : rejeu de `derive_nature` après l'entrée de `content` dans la règle\n")
    out("--       (garde du guichet, #78). GÉNÉRÉ par `_gen_044.py`, ne pas éditer à la main :\n")
    out("--       la requalification est calculée par `derive_nature`, détenteur unique (#46).\n")
    out("--\n")
    out("-- CE QUE CETTE MIGRATION CORRIGE, et pourquoi c'était invisible. Un producteur qui\n")
    out("-- CALCULE un chiffre à partir de chiffres déposés le rangeait sous `fact_financial` ×\n")
    out("-- source officielle, donc sous `mesure`, donc sous l'autorité du dépôt. Les entries\n")
    out("-- concernées sont HONNÊTES dans leur prose — elles écrivent leur calcul en toutes\n")
    out("-- lettres. C'est le tampon qui était faux, pas le texte : rien ne pouvait le voir, et\n")
    out("-- une réponse fondée dessus (#475, supprimée le 2026-09-21) passait les quatre\n")
    out("-- contrôles du manager.\n")
    out("--\n")
    out(f"-- Lignes examinées : {total} · inchangées : {inchangees} · "
        f"REQUALIFIÉES : {len(changements)}\n")
    for marqueur, n in par_marqueur.most_common():
        out(f"--   marqueur « {marqueur} » : {n}\n")
    out("--\n")
    out("-- ⚠️ `reliability_tier` et `reliability_score` ne sont PAS touchés : la fiabilité est\n")
    out("-- une propriété de la SOURCE, la nature une propriété de l'ASSERTION (#50).\n")
    out("\n")

    if not changements:
        out("-- Aucune ligne à requalifier : la règle et la base sont déjà d'accord.\n")
        out("-- (Ce n'est PAS un succès muet — le bloc de vérification ci-dessous rougirait si\n")
        out("--  des lignes étaient requalifiables et que ce fichier les avait oubliées.)\n")

    out("BEGIN;\n\n")

    for nature in sorted({c[2] for c in changements}):
        ids = [c[0] for c in changements if c[2] == nature]
        out(f"-- → `{nature}` ({len(ids)} lignes)\n")
        for entry_id, avant, _apres, marqueur in changements:
            if _apres != nature:
                continue
            out(f"--   #{entry_id} : `{avant}` → `{nature}` (« {marqueur} »)\n")
        out(f"UPDATE knowledge_entries SET nature = '{nature}', updated_at = NOW()\n")
        out(f" WHERE id IN ({', '.join(str(i) for i in ids)});\n\n")

    # GARDE ÉPROUVÉE EN NÉGATIF AVANT APPLICATION (#65 appliqué au SQL).
    #
    # ⚠️ La première forme écrite ici comptait les lignes de la liste `id IN (…)` devenues
    # `interpretation`. Elle ne pouvait RIEN attraper : l'`UPDATE` juste au-dessus vient de les
    # écrire, donc elle ne rougissait que si l'`UPDATE` lui-même avait échoué — une garde nourrie
    # de sa PROPRE écriture, le mode de panne de `feedback_controle_au_point_de_lecture`. Surtout,
    # elle était aveugle au seul défaut qui compte ici : un générateur qui OUBLIE des lignes.
    #
    # La forme retenue est un invariant GLOBAL : le nombre total de `mesure` en base après la
    # transaction doit être exactement celui que le rejeu de la règle prédit. Une ligne oubliée le
    # fait dépasser ; un `UPDATE` trop large le fait manquer. Et le compte attendu ne vient pas
    # d'un décompte de corpus, interdit comme cible (#0.6) — il est DÉRIVÉ du rejeu de la règle sur
    # l'instantané, donc il se recalcule au lieu de se maintenir à la main.
    out("-- Garde : invariant GLOBAL, pas un accusé de réception de l'UPDATE ci-dessus.\n")
    out("-- Le total de `mesure` en base doit être celui que le rejeu de la règle prédit : une\n")
    out("-- ligne oubliée le fait dépasser, un UPDATE trop large le fait manquer.\n")
    out("DO $$\n")
    out("DECLARE n int;\n")
    out("BEGIN\n")
    out("  SELECT count(*) INTO n FROM knowledge_entries WHERE nature = 'mesure';\n")
    out(f"  IF n <> {total_mesure} THEN\n")
    out(f"    RAISE EXCEPTION '044 : % entries `mesure` en base, {total_mesure} prédites par le "
        "rejeu de derive_nature — des lignes ont été oubliées ou requalifiées à tort', n;\n")
    out("  END IF;\n")
    out("END $$;\n\n")
    out("COMMIT;\n")


if __name__ == "__main__":
    main(sys.argv[1])
