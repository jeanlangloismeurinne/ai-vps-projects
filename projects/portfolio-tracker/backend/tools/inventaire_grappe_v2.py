"""Inventaire de la grappe V2 — ce que la migration 036 doit déplacer, et ce qu'elle doit couper.

CE QU'IL MESURE, ET POURQUOI AVANT D'ÉCRIRE LA MIGRATION
--------------------------------------------------------
Le lot 2b archive la grappe V2 entière (`CREATE SCHEMA archive_v2` + `ALTER TABLE … SET SCHEMA`),
puis la recrée vide et amaigrie. Trois questions décident du contenu exact de la 036, et aucune ne
se répond de mémoire :

  1. **Quelles tables** composent la grappe ? Une liste écrite à la main serait un jumeau du vrai
     détenteur (#46) et divergerait au premier ajout. Elle est **dérivée** ici : une table V2 est
     une table créée par une migration nommée `*_v2_*.sql`. Le fichier de migration est le
     producteur de la table ; c'est donc lui qui sait.
  2. **Quelles arêtes FK ENTRENT** dans la grappe depuis une table qui reste (V0/V1) ? Ce sont
     elles, et elles seules, qui font du travail : un `SET SCHEMA` emporte la contrainte avec la
     table, donc une FK entrante continuerait de pointer vers l'archive, et la table recréée dans
     `public` serait inatteignable par ses référents.
  3. **Quelles LIGNES hors-grappe** référencent effectivement la grappe ? La spec §5.3 les nomme
     (une position MSFT, 2 `calendar_events`) et tranche : ce sont des artefacts de recette du
     lot 7, ils partent à l'archive avec le reste. Encore faut-il que le décompte soit celui
     d'aujourd'hui et non celui du jour où la spec a été écrite
     (`feedback_ligne_de_base_est_une_mesure`).

CE QU'IL N'EST PAS
------------------
Ce n'est pas un test d'acceptation : il n'y a pas de valeur cible. C'est une **mesure**, au sens de
`tools/ligne_de_base_frameworks.py`. Les asserts qu'il porte ne jugent pas la v3 — ils gardent la
MESURE elle-même contre les faux verts : une grappe vide, une dérivation qui ne mord plus, un
décompte fait sur zéro ligne. Un pré-requis manquant sort en **erreur**, jamais en saut de section
(`feedback_check_degrade_en_sortant_a_zero`).

⚠️ Les §5 à §7 mesurent ce que la 036 doit RETIRER. Ils sont écrits pour rougir aujourd'hui et
virer au vert une fois la migration appliquée — un vert avant la 036 est un défaut du mesureur,
pas une bonne nouvelle (`feedback_test_negatif_obligatoire`).

Usage :

    bash tools/inventaire_grappe_v2.sh

⚠️ Jamais dans `portfolio-backend` : il porte le code déployé, qui peut précéder ce qu'on mesure.
"""
from __future__ import annotations

import ast
import os
import pathlib
import re
import sys

from app.db.database import close_pool, get_db_session, init_pool

MIGRATIONS = pathlib.Path("app/db/migrations")
BACKEND = pathlib.Path("app")

# Les 7 colonnes de `knowledge_entries` mesurées à ZÉRO écriture sur 180 lignes (spec §0.6). Elles
# ne sont pas devinées : la 036 les supprime, donc la liste EST le périmètre du lot et doit être
# lisible ici. Ce que le script vérifie, c'est qu'elles sont bien mortes — en base ET dans le code.
COLONNES_MORTES = [
    "question_status",
    "question_priority",
    "resolves_entry_id",
    "conflict_entry_id",
    "has_conflict",
    "reviewed_by_user",
    "is_deleted",
]

# Les jetons MÉTHODOLOGIQUES à retirer des deux vocabulaires (écarts V6/V7 de l'audit du
# 2026-09-10) : `entry_type` doit nommer ce que l'assertion EST, `report_type` ce que le rapport
# EST — ni l'un ni l'autre n'a à nommer un livre de méthode (`base_rate` = Base Rate Book,
# `mvdd` = la grille de 19) ou un thème (`risk`).
#
# ⚠️ Les deux n'ont PAS le même détenteur, et c'est ce que la 1ʳᵉ version de ce mesureur avait
# manqué : `report_type` est tenu par une contrainte CHECK, `entry_type` par personne en SQL — il
# est écrit librement par ses producteurs et lu par `_MEASURING_ENTRY_TYPES`. Chercher un CHECK
# pour les deux rendait « retiré du CHECK » sur `base_rate`, c'est-à-dire un VERT sur un jeton
# parfaitement présent (assert à côté de son point de lecture,
# `feedback_controle_au_point_de_lecture`).
JETONS_METHODOLOGIQUES = {"base_rate", "risk", "mvdd"}

ok = fail = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


def _titre(n: int | str, texte: str) -> None:
    print(f"\n{'─' * 78}\n§{n} — {texte}\n")


# ══════════════════════════════════════════════════════════════════════════════
# §1 — la grappe, DÉRIVÉE des migrations qui la produisent
# ══════════════════════════════════════════════════════════════════════════════
# ⚠️ Le schéma est CAPTURÉ, pas ignoré. La 1ʳᵉ version s'arrêtait au 1ᵉʳ identifiant, donc
# `CREATE TABLE archive_v2.liens_entrants` rendait la table « archive_v2 » et
# `CREATE TABLE public.question_coverage` rendait la table « public » — deux noms de schéma pris
# pour des tables, qui partaient ensuite en options `-t` de `pg_dump`.
_CREATE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    r"(?:(?P<schema>[a-z_][a-z0-9_]*)\.)?(?P<table>[a-z_][a-z0-9_]*)", re.I)

# Une migration qui ARCHIVE la grappe n'est pas une migration qui la CRÉE. Sans ce filtre, la 036
# — qui recrée les 15 tables depuis un dump et s'appelle `036_v2_…` — se donnait en entrée à la
# dérivation qui la produit : le générateur fabriquait la liste qu'il lisait. Le discriminant est
# le CONTENU (« cette migration déplace-t-elle vers l'archive ? »), pas un numéro écrit à la main.
_ARCHIVE = re.compile(r"SET\s+SCHEMA\s+archive_v2", re.I)


def grappe_v2() -> tuple[list[str], dict[str, str]]:
    """Rend les tables créées par une migration `*_v2_*.sql`, et leur migration d'origine.

    Le nom du fichier est le discriminant, pas son contenu : c'est ce qui rend la dérivation
    stable quand une migration V2 se contente d'ALTER une table existante (027-029, 034, 035).
    Deux exclusions, toutes deux dérivées : les tables d'un autre schéma que `public` (l'archive
    n'est pas la grappe) et les migrations d'archivage (elles recréent, elles n'introduisent pas).
    """
    tables: dict[str, str] = {}
    for f in sorted(MIGRATIONS.glob("*_v2_*.sql")):
        source = f.read_text(encoding="utf-8")
        if _ARCHIVE.search(source):
            continue
        for m in _CREATE.finditer(source):
            if (m["schema"] or "public").lower() != "public":
                continue
            tables.setdefault(m["table"].lower(), f.name)
    return sorted(tables), tables


# ══════════════════════════════════════════════════════════════════════════════
# §5 — une colonne morte l'est en base ET dans le code
# ══════════════════════════════════════════════════════════════════════════════
def _source_depouillee(p: pathlib.Path) -> str:
    """Rend la source SANS ses commentaires ni ses docstrings.

    Sans ce dépouillement, un grep d'interdit lit sa propre énonciation : `is_deleted` est cité
    dans la docstring qui explique qu'on ne l'écrit plus, et le fichier se déclarerait coupable
    (convention #56, `feedback_grep_interdit_lit_sa_propre_enonciation`).
    """
    try:
        arbre = ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError:
        return ""
    for noeud in ast.walk(arbre):
        if isinstance(noeud, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            corps = noeud.body
            if corps and isinstance(corps[0], ast.Expr) and isinstance(corps[0].value, ast.Constant) \
                    and isinstance(corps[0].value.value, str):
                corps[0].value.value = ""
    return ast.unparse(arbre)


# Une écriture, c'est un INSERT qui NOMME la colonne ou un UPDATE qui l'affecte. Une simple lecture
# (`WHERE is_deleted = false`) n'en est pas une : le lot 2b supprime la colonne, donc les lectures
# sont à retirer aussi, mais ce sont deux travaux distincts et deux décomptes distincts (#54).
def sites_d_ecriture(colonne: str) -> list[str]:
    ecriture = re.compile(
        rf"(INSERT\s+INTO[^;]*?\b{colonne}\b)|(UPDATE[^;]*?\bSET\b[^;]*?\b{colonne}\s*=)",
        re.I | re.S,
    )
    trouves = []
    for p in sorted(BACKEND.rglob("*.py")):
        if "/migrations/" in str(p):
            continue  # une migration ÉCRIT la colonne par construction — ce n'est pas un appelant
        if ecriture.search(_source_depouillee(p)):
            trouves.append(str(p))
    return trouves


def sites_de_lecture(colonne: str) -> list[str]:
    """Tout fichier dont le CODE nomme la colonne — `app/`, `checks/` et `tools/`.

    Les trois comptent : un check qui nomme une colonne supprimée échoue à la requête, et un
    mesureur aussi. Ce script s'exclut lui-même — il énumère les colonnes mortes par nécessité,
    et se compterait sinon dans sa propre surface.
    """
    lecture = re.compile(rf"\b{colonne}\b")
    trouves = []
    for racine in (BACKEND, pathlib.Path("checks"), pathlib.Path("tools")):
        for p in sorted(racine.rglob("*.py")):
            if "/migrations/" in str(p) or p.name == "inventaire_grappe_v2.py":
                continue
            if lecture.search(_source_depouillee(p)):
                trouves.append(str(p))
    return trouves


# ══════════════════════════════════════════════════════════════════════════════
async def main() -> int:
    url = os.environ.get("DATABASE_URL") or ""
    if not url:
        print("DATABASE_URL manquant — l'inventaire se REQUÊTE sur la base réelle "
              "(`feedback_ligne_de_base_est_une_mesure`).", file=sys.stderr)
        return 2
    if not MIGRATIONS.is_dir():
        print(f"{MIGRATIONS} introuvable — lancer depuis `backend/` (cf. le lanceur).",
              file=sys.stderr)
        return 2

    tables, origine = grappe_v2()

    _titre(1, "la grappe V2, dérivée des migrations `*_v2_*.sql` qui la créent")
    for t in tables:
        print(f"  {t:28} ← {origine[t]}")
    check("[1] la grappe dérivée est non vide", bool(tables),
          "→ la regex CREATE TABLE ne mord plus : tout le reste serait vrai sur zéro table")

    await init_pool(url)
    try:
        async with get_db_session() as conn:
            # ── §2 — ce qui part réellement, ligne par ligne ────────────────────
            _titre(2, "lignes par table de la grappe — ce que `SET SCHEMA` emporte")
            presentes, total_lignes = [], 0
            for t in tables:
                existe = await conn.fetchval(
                    "SELECT to_regclass($1) IS NOT NULL", f"public.{t}")
                if not existe:
                    print(f"  {t:28} ABSENTE de public — migration non appliquée ?")
                    continue
                n = await conn.fetchval(f"SELECT count(*) FROM public.{t}")
                presentes.append(t)
                total_lignes += n
                print(f"  {t:28} {n:6} ligne(s)")
            print(f"\n  → {len(presentes)} tables, {total_lignes} lignes au total")
            check("[2] toutes les tables dérivées existent en base",
                  len(presentes) == len(tables),
                  f"→ {sorted(set(tables) - set(presentes))} absentes : la dérivation nomme des "
                  f"tables que la base ne porte pas")

            # ── §3 — les arêtes ENTRANTES : le seul vrai travail de la 036 ──────
            _titre(3, "arêtes FK ENTRANTES (hors-grappe → grappe) — ce que l'archivage CASSE")
            print("  Un `SET SCHEMA` emporte la contrainte avec la table. Une FK entrante\n"
                  "  continuerait donc de pointer vers `archive_v2`, et la table recréée dans\n"
                  "  `public` serait inatteignable par ses référents.\n")
            entrantes = await conn.fetch("""
                SELECT c.conname, c.conrelid::regclass::text AS src, a.attname AS col,
                       c.confrelid::regclass::text AS dst
                  FROM pg_constraint c
                  JOIN LATERAL unnest(c.conkey) k(n) ON true
                  JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.n
                 WHERE c.contype = 'f'
                   AND c.confrelid::regclass::text = ANY($1::text[])
                   AND NOT (c.conrelid::regclass::text = ANY($1::text[]))
                 ORDER BY 2, 3
            """, tables)
            for e in entrantes:
                print(f"  {e['src']}.{e['col']:24} → {e['dst']:24} ({e['conname']})")
            check("[3] au moins une arête entrante est trouvée", bool(entrantes),
                  "→ zéro arête entrante rendrait la §4 vraie sur zéro ligne, alors que la spec "
                  "§5.3 en nomme trois")

            # ── §4 — les LIGNES hors-grappe qui référencent la grappe ───────────
            _titre(4, "lignes hors-grappe qui référencent la grappe (« faits du monde », #34)")
            print("  Spec §5.3 : ce sont des artefacts de recette du lot 7, le système n'étant\n"
                  "  en usage réel sur aucun périmètre (§0.6). Ils partent à l'archive.\n")
            total_ref = 0
            for e in entrantes:
                n = await conn.fetchval(
                    f"SELECT count(*) FROM public.{e['src']} WHERE {e['col']} IS NOT NULL")
                total_ref += n
                marque = "  ← à traiter" if n else ""
                print(f"  {e['src']}.{e['col']:24} {n:4} ligne(s) non NULL{marque}")
            print(f"\n  → {total_ref} lignes hors-grappe à archiver avec elle")

            # ── §5 — les 7 colonnes mortes ──────────────────────────────────────
            _titre(5, "les 7 colonnes de `knowledge_entries` à ZÉRO écriture (spec §0.6)")
            print("  Une colonne que personne n'écrit n'est pas une option ouverte : c'est une\n"
                  "  garantie apparente, qui se lit comme un dispositif en place (#50).\n")
            existantes = set(await conn.fetchval("""
                SELECT coalesce(array_agg(column_name), '{}')
                  FROM information_schema.columns
                 WHERE table_schema='public' AND table_name='knowledge_entries'
            """) or [])
            total_ke = await conn.fetchval("SELECT count(*) FROM knowledge_entries")
            print(f"  {total_ke} lignes dans `knowledge_entries`.\n")
            for col in COLONNES_MORTES:
                if col not in existantes:
                    print(f"  {col:20} SUPPRIMÉE de la table")
                    continue
                nonvide = await conn.fetchval(
                    f"SELECT count(*) FROM knowledge_entries "
                    f"WHERE {col} IS NOT NULL AND {col}::text NOT IN ('false','0','')")
                ecr = sites_d_ecriture(col)
                lec = sites_de_lecture(col)
                print(f"  {col:20} {nonvide:4} ligne(s) porteuse(s) · "
                      f"{len(ecr)} site(s) d'écriture · {len(lec)} fichier(s) la mentionnant")
                for f in ecr:
                    print(f"      ⚠ écrit par {f}")
            restantes = [c for c in COLONNES_MORTES if c in existantes]
            check("[5] les 7 colonnes mortes sont supprimées de `knowledge_entries`",
                  not restantes,
                  f"→ {len(restantes)} encore présentes : {restantes} — ROUGE ATTENDU avant la 036")

            # ── §6 — `covers`, la rigidité de framework (écart V5) ──────────────
            _titre(6, "`covers` sur `knowledge_entries` (écart V5) — la couverture est relationnelle")
            if "covers" in existantes:
                porteuses = await conn.fetchval(
                    "SELECT count(*) FROM knowledge_entries WHERE covers IS NOT NULL "
                    "AND cardinality(covers) > 0")
                chemins = await conn.fetchval(
                    "SELECT count(DISTINCT c) FROM knowledge_entries, unnest(covers) c")
                print(f"  {porteuses} entries portent un `covers` non vide, "
                      f"{chemins} chemins distincts.")
                print("  Ces chemins appartiennent à UNE méthodologie : les stocker sur l'entry\n"
                      "  signifie qu'en changer invalide le corpus (#57).")
            else:
                print("  `covers` SUPPRIMÉE de `knowledge_entries`.")
            qc = await conn.fetchval("SELECT to_regclass('public.question_coverage') IS NOT NULL")
            print(f"  `question_coverage` : {'créée' if qc else 'ABSENTE'}")
            check("[6] `covers` a disparu de `knowledge_entries` au profit de `question_coverage`",
                  "covers" not in existantes and bool(qc),
                  "→ ROUGE ATTENDU avant la 036 (écart V5, convention #57)")

            # ── §7 — les vocabulaires à dévocabulariser (V6/V7) ─────────────────
            _titre(7, "jetons méthodologiques dans les deux vocabulaires (écarts V6/V7)")
            print("  `entry_type` doit nommer ce que l'assertion EST, `report_type` ce que le\n"
                  "  rapport EST. Un livre de méthode (`base_rate`, `mvdd`) ou un thème (`risk`)\n"
                  "  n'est ni l'un ni l'autre — même famille que V5, en plus bénin.\n")
            residus = []

            # `entry_type` — aucun CHECK ne le tient. Ses détenteurs de fait sont ses producteurs
            # (ce que la base porte) et `_MEASURING_ENTRY_TYPES`, qui décide de la nature (#51).
            valeurs = await conn.fetch(
                "SELECT entry_type, count(*) n FROM knowledge_entries GROUP BY 1 ORDER BY 2 DESC")
            print("  knowledge_entries.entry_type — aucun CHECK, vocabulaire de FAIT :")
            for r in valeurs:
                methodo = r["entry_type"] in JETONS_METHODOLOGIQUES
                if methodo:
                    residus.append(f"entry_type='{r['entry_type']}'")
                print(f"    {r['entry_type']:18} {r['n']:4} ligne(s)"
                      f"{'   ← méthodologie/thème, pas une nature' if methodo else ''}")
            from app.agents.v2.common import _MEASURING_ENTRY_TYPES
            mesurants = sorted(_MEASURING_ENTRY_TYPES)
            fautifs = sorted(set(mesurants) & JETONS_METHODOLOGIQUES)
            print(f"\n  `_MEASURING_ENTRY_TYPES` (détenteur de la nature, #51) = {mesurants}")
            if fautifs:
                residus.append(f"_MEASURING_ENTRY_TYPES ⊇ {fautifs}")
                print(f"    ⚠ {fautifs} y donnent autorité de MESURE à un nom de méthode : le\n"
                      f"      remplaçant devra y entrer, sinon les entries de taux de base\n"
                      f"      retomberaient en `interpretation` sans que rien ne le dise.")

            # `report_type` — tenu, lui, par une contrainte CHECK.
            src = await conn.fetchval("""
                SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c
                 WHERE c.conrelid = 'knowledge_curator_reports'::regclass AND c.contype = 'c'
                   AND pg_get_constraintdef(c.oid) ILIKE '%report_type%' LIMIT 1
            """)
            print(f"\n  knowledge_curator_reports.report_type — CHECK : {src}")
            for jeton in sorted(JETONS_METHODOLOGIQUES):
                if src and f"'{jeton}'" in src:
                    n = await conn.fetchval(
                        "SELECT count(*) FROM knowledge_curator_reports WHERE report_type=$1",
                        jeton)
                    residus.append(f"report_type='{jeton}'")
                    print(f"    ⚠ '{jeton}' admis par le CHECK · {n} ligne(s)")
            check("[7] aucun jeton méthodologique dans `entry_type` / `report_type`",
                  not residus, f"→ {residus} — ROUGE ATTENDU avant la 036 (V6/V7)")

            # ── §8 — les planchers que l'archivage va faire tomber ──────────────
            _titre(8, "planchers de la suite hors-ligne que l'archivage vide")
            print("  ⚠️ La tentation sera de les baisser (`feedback_optional_schema_gate`).\n"
                  "  INTERDIT : rejouer les producteurs déterministes, coût modèle NUL.\n")
            print("  Les deux requêtes ci-dessous sont COPIÉES du point de lecture des checks,\n"
                  "  pas reconstruites : la 1ʳᵉ version comptait `fact_financial` courants (43) là\n"
                  "  où §12bis compte le socle EDGAR sans filtre de supersedage (84), et annonçait\n"
                  "  donc un plancher déjà franchi qui ne l'était pas.\n")
            from app.knowledge.edgar_feed import POSTES
            socle = await conn.fetchval("""
                SELECT count(*) FROM knowledge_entries
                 WHERE entry_type = 'fact_financial' AND source_type = 'edgar_official'
                   AND content_structured->>'metric' = ANY($1)
            """, sorted(p.metric for p in POSTES))
            rvmd = await conn.fetchval("""
                SELECT count(*) FROM knowledge_entries
                 WHERE ticker_id = 'RVMD' AND superseded_by IS NULL AND is_deleted = FALSE
                   AND entry_type IN ('fact_financial', 'base_rate')
            """)
            print(f"  check_edgar_feed §12bis    plancher >= 50   aujourd'hui {socle}")
            print(f"  check_entry_nature §7      plancher == 13   aujourd'hui {rvmd}")
            check("[8] le socle EDGAR est au-dessus de son plancher AVANT archivage",
                  socle >= 50,
                  f"→ {socle} < 50 : la mesure de départ est déjà sous le plancher, l'après-"
                  f"archivage ne serait pas comparable")
            check("[8] RVMD porte bien ses 13 entries déterministes AVANT archivage",
                  rvmd == 13, f"→ {rvmd}")

            # ── §8bis — les VUES adossées à la grappe ───────────────────────────
            # ⚠️ AJOUTÉE le 2026-09-10, après coup : §3 ne mesurait que les arêtes de clef
            # étrangère, et une vue n'en est pas une. Elle dépend de la table par OID — donc
            # `ALTER TABLE … SET SCHEMA` la laisse dans `public` en la faisant pointer, en
            # SILENCE, sur la table archivée. La vue continue de répondre, sur un corpus gelé
            # pour toujours. C'est `feedback_controle_au_point_de_lecture` : le point de
            # lecture n'est pas celui qu'on a migré.
            _titre("8bis", "vues adossées à la grappe — la dépendance que §3 ne voit pas")
            vues = await conn.fetch("""
                SELECT DISTINCT v.relname AS vue, t.relname AS source
                  FROM pg_depend d
                  JOIN pg_rewrite r ON r.oid = d.objid
                  JOIN pg_class v ON v.oid = r.ev_class
                  JOIN pg_class t ON t.oid = d.refobjid
                 WHERE d.classid = 'pg_rewrite'::regclass
                   AND d.refclassid = 'pg_class'::regclass
                   AND v.relkind = 'v' AND t.relkind = 'r' AND v.relname <> t.relname
                   AND t.relname = ANY($1)
                 ORDER BY 1, 2
            """, tables)
            a_recreer = []
            for v in vues:
                corps = await conn.fetchval("SELECT pg_get_viewdef($1::regclass, true)", v["vue"])
                nommees = sorted(c for c in COLONNES_MORTES + ["covers"]
                                 if re.search(rf"\b{c}\b", corps))
                a_recreer.append(v["vue"])
                print(f"  {v['vue']} → {v['source']}")
                if nommees:
                    print(f"      ⚠ nomme {nommees} — la vue doit être RECRÉÉE par la 036, sinon\n"
                          f"        le DROP COLUMN échoue (dépendance) ou la vue sert l'archive.")
            check("[8bis] aucune vue n'est adossée à la grappe sans être recréée par la 036",
                  not a_recreer,
                  f"→ {a_recreer} — ROUGE ATTENDU avant la 036 : elle doit les DROP puis les "
                  f"recréer sur les tables neuves")

            # ── §9 — la surface de code que la 036 oblige à toucher ─────────────
            _titre(9, "surface de code nommant une colonne supprimée — le vrai coût du lot")
            print("  Une colonne supprimée dont le nom survit dans une requête SQL fait échouer\n"
                  "  la requête, pas le déploiement : c'est la DETTE de #17 transposée à un DROP.\n")
            for col in ["is_deleted", "covers"] + [c for c in COLONNES_MORTES if c != "is_deleted"]:
                sites = sites_de_lecture(col)
                if not sites:
                    continue
                autres = [s for s in sites if not s.startswith("tools/")]
                print(f"  {col:20} {len(sites):3} fichier(s) — dont {len(autres)} dans `app/`")
                for s in autres:
                    print(f"      · {s}")
    finally:
        await close_pool()

    print(f"\n{'=' * 78}\n{ok} vérifications OK, {fail} échec(s)")
    if fail:
        print("\nROUGE ATTENDU avant la migration 036 : les §5/§6/§7 mesurent ce qu'elle doit\n"
              "retirer. Un vert ici AVANT la 036 est un défaut du mesureur, pas un acquis.",
              file=sys.stderr)
    return 1 if fail else 0


if __name__ == "__main__":
    import asyncio
    raise SystemExit(asyncio.run(main()))
