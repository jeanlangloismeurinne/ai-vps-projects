"""Générateur de `036_v2_archive_devocabularisation.sql` — lot 2b, spec §5.1-§5.3 et §10.

CE QUE LA 036 FAIT, EN UNE PHRASE
---------------------------------
Elle **archive** la grappe V2 entière (rien n'est détruit), la **recrée vide**, retire de
`knowledge_entries` les **8 colonnes** qui n'y ont pas leur place, crée `question_coverage`, et
**dévocabularise** `entry_type` / `report_type`.

POURQUOI UN GÉNÉRATEUR, ET QUE FAIT-IL EXACTEMENT
--------------------------------------------------
Recréer 15 tables suppose leur DDL. Le réécrire à la main serait un **jumeau** de la table (#46) :
un `NOT NULL` oublié, un index dont le nom change, et la table « recréée » n'est plus la même — sans
que rien ne le dise, puisqu'elle est vide et que rien ne s'y casse avant la première écriture.

Le détenteur du DDL, c'est `pg_dump --schema-only`. Le générateur ne l'écrit donc pas : il le
**relit et le modifie mécaniquement**, par des règles qui portent toutes sur un NOM :

  · une ligne de colonne dont le nom est dans `COLONNES_RETIREES` → retirée du `CREATE TABLE` ;
  · un index dont le prédicat porte `is_deleted = false` → le conjoint est retiré. C'est
    **exactement** préservateur de sémantique : sans la colonne, toute ligne est « non supprimée »,
    donc le conjoint est vrai partout ;
  · un index qui, APRÈS ce retrait, nomme encore une colonne retirée → supprimé en entier, et
    **listé** dans l'en-tête du SQL produit. Un index qui disparaît en silence est une performance
    qu'on perd sans jamais l'apprendre ;
  · une clef étrangère portée par une colonne retirée → supprimée ;
  · le CHECK de `report_type` → réécrit sans `'mvdd'` ; un CHECK neuf ferme `entry_type`.

Et il **échoue** si une règle ne mord pas : une colonne annoncée mais introuvable, un CHECK
`report_type` non trouvé, une grappe qui ne correspond pas au dump. Une règle qui ne trouve rien
n'est pas une règle satisfaite, c'est une règle qui n'a pas été appliquée
(`feedback_check_degrade_en_sortant_a_zero`).

LES DEUX PIÈGES QUE `SET SCHEMA` TEND, MESURÉS SUR BASE SONDE LE 2026-09-10
---------------------------------------------------------------------------
1. **Ce qui suit la table** : ses index, ses contraintes et sa **séquence possédée** partent avec
   elle dans `archive_v2`. Leurs noms sont donc LIBRES dans `public`, et le DDL de pg_dump se
   rejoue tel quel. Vérifié : `arc.t`, `arc.t_id_seq`, `arc.t_pkey`, `arc.i_t`.
2. **Ce qui NE suit PAS** : une **vue**. Elle reste dans `public` et pointe sur la table archivée
   **par OID**, donc en silence. Sonde : après le déplacement, `public.vv` rendait encore `v=7`
   (la ligne archivée) pendant que `public.t` neuve portait `v=99`. Une vue qui répond sur un
   corpus gelé pour toujours est le mode de panne de `feedback_controle_au_point_de_lecture` — le
   point de lecture n'est pas celui qu'on a migré. Le mesureur ne le voyait pas non plus : §3 de
   `inventaire_grappe_v2.py` ne comptait que les arêtes FK, et une vue n'en est pas une (§8bis
   ajoutée après coup). La 036 les DROP avant l'archivage et les recrée sur les tables neuves.

L'ARBITRAGE DE VOCABULAIRE (écart V6), TRANCHÉ AVEC L'UTILISATEUR LE 2026-09-10
-------------------------------------------------------------------------------
`entry_type` doit nommer ce qu'une assertion EST. Deux valeurs n'en étaient pas :

  · `base_rate` (7 lignes) nommait un **livre de méthode**. Ce que ces entries portent réellement,
    c'est une fréquence observée sur une **classe de référence** — des pairs, pas l'émetteur. C'est
    une connaissance d'une autre nature que « ce que fait cette entreprise », et l'utilisateur a
    tranché pour une **étiquette distincte** : `fact_statistical`.

    ⚠️ **Réserve explicite de l'utilisateur, à ne pas perdre** : l'existence d'entries portant cette
    étiquette ne fondera **PAS** la règle « une analyse concurrentielle a eu lieu ». Cette règle
    sera plus compliquée, et relèvera d'un futur framework « analyse concurrentielle » — voire d'un
    passage du concurrent dans le système complet sans ouverture de position. Écrire ici que
    l'étiquette suffit serait un test inperdable de plus.

  · `risk` (1 ligne, `llm_memory`, « Risques principaux (à vérifier) ») nommait un **thème**.
    L'utilisateur l'a rangée dans les **constats sur l'entreprise** — `fact_qualitative` — **avec
    une fiabilité basse**, sa source étant une mémoire de modèle sans référence.

    Réserve associée, portée au backlog : le système devra aller **chercher des sources** pour
    vérifier ou infirmer les assertions à fiabilité basse qui pèsent lourd dans le jugement final.
    Aujourd'hui elles restent au corpus sans que rien ne les rappelle.

`entry_type` n'avait **aucun** CHECK — c'est du texte libre écrit par les producteurs. La 036 en
pose un. Le vocabulaire fermé est celui des valeurs que les producteurs ÉCRIVENT, pas celui des
valeurs que du code LIT : `quote` et `lesson_learned` sont nommés par des filtres de lecture de
`synthesis_feed` / `_INTERPRETING_ENTRY_TYPES` sans qu'aucun producteur ne les émette. Les admettre
« au cas où » serait rouvrir une option que personne n'exerce, c'est-à-dire #50 à l'envers.

⚠️ `fact_statistical` doit ENTRER dans `_MEASURING_ENTRY_TYPES`, sinon les entries de taux de base
retombent en `interpretation` sans que rien ne le dise — leur autorité changerait par effet de
bord d'un renommage. C'est du ressort du balayage de code, pas du SQL, mais la garde §J le vérifie
depuis la base autant qu'elle le peut.

Usage : `bash app/db/migrations/_gen_036.sh` (il produit les trois instantanés et écrit le .sql).
"""
from __future__ import annotations

import argparse
import re
import sys

from tools.inventaire_grappe_v2 import COLONNES_MORTES, grappe_v2

# ── Les règles, toutes portées par un NOM, toutes importées ou dérivées ─────────────────────────

# Les 7 colonnes à zéro écriture (détenteur : l'inventaire) + `covers`. `covers` n'est pas morte —
# 111 entries la portent — elle est MAL PLACÉE : la couverture est une propriété de la RELATION
# entry ↔ question, elle va en table de liaison versionnée (#57, écart V5).
COLONNES_RETIREES = list(COLONNES_MORTES) + ["covers"]

# Écart V6. La substitution ne s'applique à AUCUNE ligne (l'archivage vide les tables) : elle
# s'applique au VOCABULAIRE. Elle est ici pour être lisible dans le diff et citable par le
# balayage de code, qui doit faire la même chose côté Python.
SUBSTITUTIONS_ENTRY_TYPE = {"base_rate": "fact_statistical", "risk": "fact_qualitative"}

# Dérivé des sites d'ÉCRITURE (`grep` sur les littéraux `entry_type=` dans `app/`, 2026-09-10) :
# agent_synthesis · analysis · base_rate · fact_financial · fact_qualitative · risk — puis
# substitution. Cinq valeurs.
VOCABULAIRE_ENTRY_TYPE = sorted(
    {"agent_synthesis", "analysis", "fact_financial", "fact_qualitative"}
    | set(SUBSTITUTIONS_ENTRY_TYPE.values())
)

# Écart V7 — `mvdd` est le nom d'un framework dans une contrainte de base. 0 ligne le porte.
VOCABULAIRE_REPORT_TYPE = ["readiness", "lint"]

SCHEMA = "archive_v2"

_ENTETE = re.compile(r"^-- Name: (?P<nom>.+?); Type: (?P<type>[A-Z ]+); Schema: (?P<sch>\S+);")
# `pg_dump` parenthèse ses prédicats d'index, `pg_get_viewdef(…, true)` ne les parenthèse pas :
# la même clause s'écrit `AND (is_deleted = false)` ici et `AND is_deleted = false` là. Une règle
# qui ne connaîtrait qu'une des deux formes laisserait passer l'autre, et le SQL produit
# échouerait à l'exécution sur une colonne inexistante — ou, pire, la vue serait muettement
# supprimée. Les deux ordres du conjoint sont couverts pour la même raison.
_CONJOINT_IS_DELETED = re.compile(
    r"\s+AND\s+\(?is_deleted\s*=\s*false\)?"
    r"|\(?is_deleted\s*=\s*false\)?\s+AND\s+",
    re.I)


class Bloc:
    def __init__(self, nom: str, type_: str) -> None:
        self.nom, self.type = nom, type_
        self.lignes: list[str] = []

    @property
    def sql(self) -> str:
        return "".join(self.lignes).strip()


def lire_ddl(path: str) -> list[Bloc]:
    """Découpe le dump en blocs. pg_dump les émet DÉJÀ dans l'ordre de dépendance."""
    blocs: list[Bloc] = []
    courant: Bloc | None = None
    for ligne in open(path, encoding="utf-8"):
        if ligne.startswith("\\restrict") or ligne.startswith("\\unrestrict"):
            continue
        m = _ENTETE.match(ligne)
        if m:
            courant = Bloc(m["nom"], m["type"].strip())
            blocs.append(courant)
            continue
        if courant is not None:
            if ligne.startswith("--"):
                continue
            courant.lignes.append(ligne)
    return blocs


def nomme(sql: str, colonne: str) -> bool:
    return re.search(rf"\b{colonne}\b", sql) is not None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ddl", required=True)
    ap.add_argument("--fk", required=True)
    ap.add_argument("--vues", required=True)
    args = ap.parse_args()

    tables, _origine = grappe_v2()
    blocs = lire_ddl(args.ddl)

    # ── Garde d'entrée : le dump porte-t-il EXACTEMENT la grappe dérivée ? ──────────────────────
    # Sans elle, un instantané pris sur un autre périmètre produirait une migration qui archive
    # 14 tables sur 15 et n'en dirait rien.
    dumpees = sorted(b.nom for b in blocs if b.type == "TABLE")
    if dumpees != tables:
        sys.exit(f"036 non émise — l'instantané porte {dumpees}, la grappe dérivée est {tables}. "
                 f"Manquantes : {sorted(set(tables) - set(dumpees))} · "
                 f"En trop : {sorted(set(dumpees) - set(tables))}")

    fk_entrantes = [l.strip().split("|") for l in open(args.fk, encoding="utf-8") if l.strip()]
    vues = [l.rstrip("\n").split("\t", 1) for l in open(args.vues, encoding="utf-8") if l.strip()]
    if not fk_entrantes:
        sys.exit("036 non émise — zéro arête FK entrante mesurée. L'inventaire en comptait 4 : "
                 "un instantané vide ferait passer pour « rien à faire » ce qui est « rien mesuré ».")

    # ── Transformation du DDL ──────────────────────────────────────────────────────────────────
    retirees_vues: list[str] = []
    index_supprimes: list[str] = []
    fk_supprimees: list[str] = []
    colonnes_vues: set[str] = set()
    sortie: list[str] = []

    for b in blocs:
        sql = b.sql

        if b.type == "TABLE" and b.nom == "knowledge_entries":
            gardees = []
            for ligne in sql.splitlines(keepends=True):
                col = re.match(r"\s{4}([a-z_][a-z0-9_]*)\s", ligne)
                if col and col.group(1) in COLONNES_RETIREES:
                    colonnes_vues.add(col.group(1))
                    continue
                gardees.append(ligne)
            sql = "".join(gardees)
            # Une virgule orpheline si la dernière colonne retirée précédait la parenthèse.
            sql = re.sub(r",(\s*\n\);)", r"\1", sql)

        if b.type == "TABLE" and b.nom == "knowledge_curator_reports":
            avant = sql
            sql = re.sub(
                r"CHECK \(\(report_type = ANY \(ARRAY\[[^\]]*\]\)\)\)",
                "CHECK ((report_type = ANY (ARRAY["
                + ", ".join(f"'{v}'::text" for v in VOCABULAIRE_REPORT_TYPE) + "])))",
                sql)
            if sql == avant:
                sys.exit("036 non émise — le CHECK `report_type` est introuvable dans le dump. "
                         "L'écart V7 serait passé sans que rien ne rougisse.")

        if b.type == "INDEX":
            sql_net = _CONJOINT_IS_DELETED.sub("", sql)
            # `WHERE ((a) AND (b))` devenu `WHERE ((a))` reste valide ; c'est le cas restant qui
            # compte : un index encore adossé à une colonne retirée n'a plus de sens du tout.
            reste = [c for c in COLONNES_RETIREES if nomme(sql_net, c)]
            if reste:
                index_supprimes.append(f"{b.nom} (portait {', '.join(reste)})")
                continue
            if sql_net != sql:
                colonnes_vues.add("is_deleted")
            sql = sql_net

        if b.type == "FK CONSTRAINT":
            porte = [c for c in COLONNES_RETIREES if nomme(sql, c)]
            if porte:
                fk_supprimees.append(f"{b.nom} (sur {', '.join(porte)})")
                continue

        sortie.append(sql)

    manquantes = sorted(set(COLONNES_RETIREES) - colonnes_vues)
    if manquantes:
        sys.exit(f"036 non émise — {manquantes} annoncée(s) mais introuvable(s) dans le DDL de "
                 f"`knowledge_entries`. Une colonne qu'on croit supprimer et qui n'était pas là "
                 f"est une règle qui n'a pas mordu, pas une règle satisfaite.")

    # ══════════════════════════════════════════════════════════════════════════════════════════
    out = sys.stdout.write
    out("-- 036 — V2 : archivage de la grappe V2 et dévocabularisation (lot 2b, spec §5.1-§5.3).\n")
    out("--       GÉNÉRÉ par `_gen_036.py` / `_gen_036.sh`, NE PAS ÉDITER À LA MAIN : le DDL des\n")
    out("--       tables recréées est celui de `pg_dump --schema-only`, détenteur unique (#46).\n")
    out("--\n")
    out("-- RIEN N'EST DÉTRUIT. `CREATE SCHEMA archive_v2` + `ALTER TABLE … SET SCHEMA` déplacent\n")
    out("-- le graphe EN BLOC : index, contraintes et séquences possédées suivent leur table. Le\n")
    out("-- corpus reste interrogeable comme fixture, et le retour est une commande.\n")
    out("--\n")
    out("-- POURQUOI PAS UN BACKFILL des `covers` vers les `question_id` : une correspondance\n")
    out("-- relue à la main est une correspondance construite pour tomber juste sur les données\n")
    out("-- d'hier. Elle rendrait T1 bon PAR CONSTRUCTION et le défaut indétectable (spec §5.3).\n")
    out("--\n")
    out(f"-- Grappe archivée : {len(tables)} tables · {', '.join(tables)}\n")
    out(f"-- Arêtes FK entrantes traitées : {len(fk_entrantes)}\n")
    out(f"-- Colonnes retirées de `knowledge_entries` : {len(COLONNES_RETIREES)} · "
        f"{', '.join(COLONNES_RETIREES)}\n")
    out("--\n")
    out("-- ⚠️ INDEX SUPPRIMÉS avec leur colonne — listés parce qu'un index qui disparaît en\n")
    out("--    silence est une performance qu'on perd sans jamais l'apprendre :\n")
    for i in index_supprimes or ["(aucun)"]:
        out(f"--      · {i}\n")
    out("-- ⚠️ CLEFS ÉTRANGÈRES supprimées avec leur colonne :\n")
    for f in fk_supprimees or ["(aucune)"]:
        out(f"--      · {f}\n")
    out("-- Les index dont le prédicat portait `is_deleted = false` sont CONSERVÉS, le conjoint\n")
    out("-- retiré : sans la colonne, toute ligne est « non supprimée », le retrait préserve donc\n")
    out("-- exactement la sémantique.\n")
    out("--\n")
    out(f"-- Vocabulaire `entry_type` FERMÉ (il ne l'était pas) : {VOCABULAIRE_ENTRY_TYPE}\n")
    out(f"-- Substitutions (écart V6, arbitrage métier du 2026-09-10) : {SUBSTITUTIONS_ENTRY_TYPE}\n")
    out(f"-- Vocabulaire `report_type` (écart V7, `mvdd` retiré) : {VOCABULAIRE_REPORT_TYPE}\n")
    out("\nBEGIN;\n")

    # ── A ──────────────────────────────────────────────────────────────────────────────────────
    out(f"\n-- ══ A. Le schéma d'archive ══\nCREATE SCHEMA {SCHEMA};\n")

    # ── B ──────────────────────────────────────────────────────────────────────────────────────
    out("\n-- ══ B. Les vues adossées à la grappe ══\n")
    out("-- Une vue NE SUIT PAS sa table : elle reste dans `public` et pointe sur la table\n")
    out("-- archivée par OID, donc EN SILENCE. Mesuré sur base sonde le 2026-09-10 : après le\n")
    out("-- déplacement, `public.vv` rendait encore la ligne archivée (v=7) pendant que la table\n")
    out("-- neuve en portait une autre (v=99). Elles sont donc coupées ICI, avant l'archivage,\n")
    out("-- et recréées en §I sur les tables neuves.\n")
    for nom, _def in vues:
        retirees_vues.append(nom)
        out(f"DROP VIEW public.{nom};\n")
    if not vues:
        out("-- (aucune vue adossée à la grappe dans l'instantané)\n")

    # ── C ──────────────────────────────────────────────────────────────────────────────────────
    out("\n-- ══ C. Les arêtes FK ENTRANTES ══\n")
    out("-- Ce sont les SEULES que l'archivage casse : un `SET SCHEMA` emporte la contrainte avec\n")
    out("-- la table, donc une FK venue du dehors continuerait de pointer sur l'archive et la\n")
    out("-- table recréée serait inatteignable par ses référents.\n")
    out("-- Spec §5.3 : les lignes derrière ces arêtes (1 position MSFT, 2 `calendar_events`) sont\n")
    out("-- des artefacts de recette du lot 7 — le système n'est en usage réel sur aucun périmètre,\n")
    out("-- il n'y a donc AUCUN fait du monde (#34) à préserver. Elles partent à l'archive avec le\n")
    out("-- reste. La convention #34 redeviendra contraignante le jour où une position réelle\n")
    out("-- existera : d'où la trace, plutôt qu'un simple NULL.\n")
    out(f"CREATE TABLE {SCHEMA}.liens_entrants (\n"
        "    table_source text        NOT NULL,\n"
        "    colonne      text        NOT NULL,\n"
        "    id_source    integer     NOT NULL,\n"
        "    valeur       integer     NOT NULL,\n"
        "    table_cible  text        NOT NULL,\n"
        "    archive_le   timestamptz NOT NULL DEFAULT now()\n"
        ");\n")
    for src, col, contrainte, cible in fk_entrantes:
        out(f"INSERT INTO {SCHEMA}.liens_entrants (table_source, colonne, id_source, valeur, table_cible)\n"
            f"SELECT '{src}', '{col}', id, {col}, '{cible}' FROM public.{src} WHERE {col} IS NOT NULL;\n"
            f"UPDATE public.{src} SET {col} = NULL WHERE {col} IS NOT NULL;\n"
            f"ALTER TABLE public.{src} DROP CONSTRAINT {contrainte};\n")

    # ── D ──────────────────────────────────────────────────────────────────────────────────────
    out("\n-- ══ D. L'archivage lui-même ══\n")
    for t in tables:
        out(f"ALTER TABLE public.{t} SET SCHEMA {SCHEMA};\n")

    # ── E ──────────────────────────────────────────────────────────────────────────────────────
    out("\n-- ══ E. Les tables recréées VIDES ══\n")
    out("-- DDL de `pg_dump --schema-only`, modifié par des règles qui portent toutes sur un NOM.\n")
    out("-- Les noms d'index, de contraintes et de séquences sont ceux d'avant : ils ont été\n")
    out("-- libérés dans `public` par le déplacement de leur table.\n\n")
    out("\n\n".join(sortie))
    out("\n")

    # ── F ──────────────────────────────────────────────────────────────────────────────────────
    out("\n-- ══ F. Les séquences reprennent où l'archive s'arrête ══\n")
    out("-- Pas de redémarrage à 1 : le corpus neuf et le corpus archivé seront LUS CÔTE À CÔTE\n")
    out("-- (comparaison avec la ligne de base du 2026-09-09). Deux entries #42 rendraient toute\n")
    out("-- citation ambiguë, et l'ambiguïté ne se découvre qu'au moment où elle a déjà trompé.\n")
    for t in tables:
        out(f"SELECT setval('public.{t}_id_seq',\n"
            f"       (SELECT coalesce(max(id), 0) + 1 FROM {SCHEMA}.{t}), false);\n")

    # ── G ──────────────────────────────────────────────────────────────────────────────────────
    out("\n-- ══ G. Les arêtes entrantes, rebranchées sur les tables NEUVES ══\n")
    for src, col, contrainte, cible in fk_entrantes:
        out(f"ALTER TABLE public.{src} ADD CONSTRAINT {contrainte}\n"
            f"    FOREIGN KEY ({col}) REFERENCES public.{cible}(id);\n")

    # ── H ──────────────────────────────────────────────────────────────────────────────────────
    out("\n-- ══ H. `question_coverage` — la couverture est une RELATION ══\n")
    out("-- 4ᵉ axe de la doctrine (#50/#51/#53/#57) : la fiabilité est une propriété de la SOURCE,\n")
    out("-- la nature une propriété de l'ASSERTION, l'actualité une propriété de la RELATION\n")
    out("-- fait ↔ ancre, et la couverture une propriété de la RELATION entry ↔ question. Les deux\n")
    out("-- dernières dépendent d'un second terme que l'entry ne connaît pas ; les stocker sur\n")
    out("-- l'entry fige un verdict qui a changé depuis.\n")
    out("--\n")
    out("-- ⚠️ `framework_version` n'est pas décoratif : sans lui, réécrire l'énoncé de `qf_1`\n")
    out("-- rendrait rétroactivement « couvertes » des entries collectées pour une AUTRE question.\n")
    out("--\n")
    out("-- ⚠️ Aucun ON DELETE CASCADE sur `entry_id`, et c'est délibéré : une entry ne se supprime\n")
    out("-- pas (append-only + supersede — c'est même pourquoi `is_deleted` s'en va). Un CASCADE\n")
    out("-- serait un chemin de suppression silencieux d'une FONDATION. Supprimer une entry citée\n")
    out("-- doit ÉCHOUER bruyamment.\n")
    out("--\n")
    out("-- ⚠️ L'ABSENCE de ligne n'est pas une erreur : c'est le cas par DÉFAUT. Une entry sans\n")
    out("-- lien est stockée, embeddée, retrouvée et citable — elle ne compte simplement pas comme\n")
    out("-- fondation (spec §5.1, conséquence 2). C'est la latitude ticker par ticker.\n")
    out("--\n")
    out("-- `question_id` / `ingredient_id` n'ont PAS de clef étrangère : leur détenteur est\n")
    out("-- `app/frameworks/frameworks.yaml`, données inertes et versionnées avec le code (§5.2).\n")
    out("-- La validation vit donc en Python, au SITE D'ÉCRITURE UNIQUE de l'aiguilleur (§3.6), et\n")
    out("-- elle LÈVE sur un inconnu. C'est le silence qui était le défaut de `covers`, pas\n")
    out("-- l'absence de contrainte.\n")
    out("CREATE TABLE public.question_coverage (\n"
        "    id                integer     GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,\n"
        "    framework_id      text        NOT NULL,\n"
        "    framework_version text        NOT NULL,\n"
        "    question_id       text        NOT NULL,\n"
        "    ingredient_id     text        NOT NULL,\n"
        "    entry_id          integer     NOT NULL REFERENCES public.knowledge_entries(id),\n"
        "    created_at        timestamptz NOT NULL DEFAULT now(),\n"
        "    CONSTRAINT question_coverage_unique\n"
        "        UNIQUE (framework_id, framework_version, question_id, ingredient_id, entry_id)\n"
        ");\n")
    out("CREATE INDEX idx_question_coverage_entry ON public.question_coverage (entry_id);\n")
    out("CREATE INDEX idx_question_coverage_question\n"
        "    ON public.question_coverage (framework_id, framework_version, question_id);\n")

    # ── I ──────────────────────────────────────────────────────────────────────────────────────
    out("\n-- ══ I. Les vues recréées sur les tables neuves ══\n")
    out("-- Leur corps est REPRIS de l'instantané, amputé des colonnes retirées. `is_deleted` dans\n")
    out("-- un `WHERE` disparaît (toute ligne est « non supprimée ») ; `has_conflict` dans un\n")
    out("-- `jsonb_build_object` disparaît de la clef exportée — un consommateur de fédération qui\n")
    out("-- la lisait lisait `false` depuis toujours.\n")
    for nom, corps in vues:
        corps_net = _CONJOINT_IS_DELETED.sub("", corps)
        corps_net = re.sub(r"\s*'has_conflict',\s*has_conflict\s*,?", "", corps_net)
        corps_net = re.sub(r",\s*\)", ")", corps_net)
        reste = [c for c in COLONNES_RETIREES if nomme(corps_net, c)]
        if reste:
            sys.exit(f"036 non émise — la vue `{nom}` nomme encore {reste} après nettoyage. "
                     f"La recréer telle quelle la ferait échouer à l'exécution ; ne pas la "
                     f"recréer du tout la ferait disparaître en silence. Corriger la règle.")
        out(f"CREATE VIEW public.{nom} AS {corps_net.strip().rstrip(';')};\n")
    if not vues:
        out("-- (aucune)\n")

    # ── J ──────────────────────────────────────────────────────────────────────────────────────
    out("\n-- ══ J. Dévocabularisation (écarts V6 / V7) ══\n")
    out("-- `entry_type` n'avait AUCUN CHECK : c'était du texte libre écrit par les producteurs,\n")
    out("-- ce qui rendait `base_rate` et `risk` indétectables par une lecture du schéma. Le\n")
    out("-- vocabulaire est fermé sur ce que les producteurs ÉCRIVENT — pas sur ce que du code\n")
    out("-- LIT : `quote` et `lesson_learned` sont nommés par des filtres de lecture sans qu'aucun\n")
    out("-- producteur ne les émette, les admettre serait rouvrir une option que personne\n")
    out("-- n'exerce.\n")
    out("ALTER TABLE public.knowledge_entries\n"
        "    ADD CONSTRAINT knowledge_entries_entry_type_check\n"
        "    CHECK (entry_type IN ("
        + ", ".join(f"'{v}'" for v in VOCABULAIRE_ENTRY_TYPE) + "));\n")

    # ── K ──────────────────────────────────────────────────────────────────────────────────────
    out("\n-- ══ K. Gardes NOMMÉES, dans la transaction ══\n")
    out("-- Une garde qui sort en `RAISE NOTICE` laisse le trou se refermer sur un COMMIT vert.\n")
    out("-- Chacune dit QUOI, pas seulement OÙ. Éprouvées EN NÉGATIF avant application (spec §12,\n")
    out("-- piège 11 ; `feedback_test_negatif_obligatoire`).\n")
    out("DO $$\n")
    out("DECLARE n INT; v TEXT;\n")
    out("BEGIN\n")

    out("  -- K1 — la grappe est bien PARTIE de `public` et bien ARRIVÉE dans l'archive.\n")
    out("  SELECT count(*) INTO n FROM pg_class c JOIN pg_namespace ns ON ns.oid = c.relnamespace\n")
    out(f"   WHERE ns.nspname = '{SCHEMA}' AND c.relkind = 'r' AND c.relname = ANY(ARRAY[")
    out(", ".join(f"'{t}'" for t in tables))
    out("]);\n")
    out(f"  IF n <> {len(tables)} THEN\n")
    out(f"    RAISE EXCEPTION '036/K1 : % tables sur {len(tables)} dans {SCHEMA}', n;\n")
    out("  END IF;\n\n")

    out("  -- K2 — les tables recréées sont VIDES. Une table non vide signifierait que le\n")
    out("  --      `SET SCHEMA` n'a pas eu lieu et qu'on est en train d'écrire un CHECK sur le\n")
    out("  --      corpus qu'on croyait avoir archivé.\n")
    for t in tables:
        out(f"  SELECT count(*) INTO n FROM public.{t};\n")
        out(f"  IF n <> 0 THEN RAISE EXCEPTION '036/K2 : public.{t} porte % lignes', n; END IF;\n")
    out("\n")

    out("  -- K3 — les 8 colonnes ont disparu de `knowledge_entries`.\n")
    out("  SELECT count(*) INTO n FROM information_schema.columns\n")
    out("   WHERE table_schema = 'public' AND table_name = 'knowledge_entries'\n")
    out("     AND column_name = ANY(ARRAY[")
    out(", ".join(f"'{c}'" for c in COLONNES_RETIREES))
    out("]);\n")
    out("  IF n <> 0 THEN RAISE EXCEPTION '036/K3 : % colonne(s) retirée(s) encore présente(s)', n; END IF;\n\n")

    out("  -- K4 — la garde MIROIR de K3 : ce qui DEVAIT rester est resté. Sans elle, une règle\n")
    out("  --      trop gourmande (un `\\b` mal placé) viderait la table et K3 serait VERTE.\n")
    out("  --      C'est le 1er faux vert : un assert satisfait par une mesure dégénérée.\n")
    out("  SELECT count(*) INTO n FROM information_schema.columns\n")
    out("   WHERE table_schema = 'public' AND table_name = 'knowledge_entries';\n")
    nb_attendu = 35 - len(COLONNES_RETIREES)
    out(f"  IF n <> {nb_attendu} THEN\n")
    out(f"    RAISE EXCEPTION '036/K4 : knowledge_entries porte % colonnes, {nb_attendu} attendues "
        f"(35 avant moins {len(COLONNES_RETIREES)})', n;\n")
    out("  END IF;\n\n")

    out("  -- K5 — `question_coverage` existe ET sa FK sur `entry_id` MORD. Une table de liaison\n")
    out("  --      sans clef étrangère réelle serait `covers` avec un nom neuf (#57).\n")
    out("  SELECT count(*) INTO n FROM pg_constraint\n")
    out("   WHERE conrelid = 'public.question_coverage'::regclass AND contype = 'f'\n")
    out("     AND confrelid = 'public.knowledge_entries'::regclass;\n")
    out("  IF n <> 1 THEN RAISE EXCEPTION '036/K5 : question_coverage sans FK réelle vers knowledge_entries'; END IF;\n\n")

    out("  -- K6 — les deux vocabulaires ne portent plus de jeton méthodologique. Le CHECK est lu\n")
    out("  --      dans son TEXTE : c'est lui le point de lecture, pas la liste qu'on a écrite.\n")
    for jeton in sorted({*SUBSTITUTIONS_ENTRY_TYPE, "mvdd"}):
        out(f"  SELECT string_agg(conname, ', ') INTO v FROM pg_constraint\n")
        out(f"   WHERE contype = 'c' AND connamespace = 'public'::regnamespace\n")
        out(f"     AND pg_get_constraintdef(oid) ~ '''{jeton}'''\n")
        out(f"     AND conrelid IN ('public.knowledge_entries'::regclass,\n")
        out(f"                      'public.knowledge_curator_reports'::regclass);\n")
        out(f"  IF v IS NOT NULL THEN\n")
        out(f"    RAISE EXCEPTION '036/K6 : le jeton ''{jeton}'' survit dans %', v;\n")
        out("  END IF;\n")
    out("\n")

    out("  -- K7 — le CHECK `entry_type` MORD vraiment. Vérifier qu'il EXISTE ne prouve rien : un\n")
    out("  --      CHECK peut exister et ne rien refuser. On lui présente une valeur du\n")
    out("  --      vocabulaire retiré et on exige qu'il la rejette — test négatif inclus dans la\n")
    out("  --      migration (`feedback_test_negatif_obligatoire`).\n")
    out("  BEGIN\n")
    out("    INSERT INTO public.knowledge_entries\n")
    out("           (entry_type, content, source_type, reliability_score, reliability_tier, nature)\n")
    out(f"    VALUES ('{sorted(SUBSTITUTIONS_ENTRY_TYPE)[0]}', 'sonde 036/K7', 'edgar_official', 1.0, 'A', 'mesure');\n")
    out("    RAISE EXCEPTION '036/K7 : le CHECK entry_type a ACCEPTÉ un jeton retiré — il existe mais ne mord pas';\n")
    out("  EXCEPTION WHEN check_violation THEN\n")
    out("    NULL;  -- attendu : c'est la preuve que la contrainte est vivante\n")
    out("  END;\n")
    out("  -- Le miroir : le vocabulaire retenu passe. Un CHECK qui refuse TOUT serait vert en K7.\n")
    out("  BEGIN\n")
    out("    INSERT INTO public.knowledge_entries\n")
    out("           (entry_type, content, source_type, reliability_score, reliability_tier, nature)\n")
    out(f"    VALUES ('{SUBSTITUTIONS_ENTRY_TYPE['base_rate']}', 'sonde 036/K7', 'edgar_official', 1.0, 'A', 'mesure');\n")
    out("  EXCEPTION WHEN OTHERS THEN\n")
    out("    RAISE EXCEPTION '036/K7 : le CHECK entry_type REFUSE le vocabulaire retenu (%)', SQLERRM;\n")
    out("  END;\n")
    out("  DELETE FROM public.knowledge_entries WHERE content = 'sonde 036/K7';\n")
    # ⚠️ `PERFORM`, pas `SELECT` : en PL/pgSQL un `SELECT` sans `INTO` échoue en « query has no
    # destination for result data ». Le défaut n'est PAS sorti des 8 mutations — chacune rougissait
    # avant d'atteindre cette ligne. Il n'est sorti que du volet SATISFIABILITÉ, et c'est
    # exactement ce que `feedback_acceptation_rouge_bidirectionnelle` annonce : huit rouges bien
    # placés sur une migration qui ne s'applique jamais.
    out(f"  PERFORM setval('public.knowledge_entries_id_seq',\n"
        f"         (SELECT coalesce(max(id), 0) + 1 FROM {SCHEMA}.knowledge_entries), false);\n")
    out("END $$;\n")

    out("\nCOMMIT;\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
