#!/usr/bin/env bash
# TEST NÉGATIF de la migration 036 — éprouvé AVANT application (spec §12, piège 11).
#
#   bash checks/negatif_036.sh
#
# POURQUOI CE TEST EXISTE. La 036 déplace 15 tables et 494 lignes. Elle porte 7 gardes
# `RAISE EXCEPTION` (K1…K7) qui la font échouer en bloc plutôt que laisser un trou se refermer sur
# un COMMIT vert. Mais une garde n'est éprouvée qu'après avoir viré au ROUGE au moins une fois
# (`feedback_test_negatif_obligatoire`) : sept `IF … THEN RAISE` jamais déclenchés se lisent comme
# un dispositif et ne sont qu'un décor.
#
# LES DEUX SENS, JAMAIS UN SEUL (`feedback_acceptation_rouge_bidirectionnelle`) :
#   · SATISFIABILITÉ — la 036 non mutée passe, et l'état d'après est celui annoncé. Sans ça, sept
#     rouges prouveraient seulement qu'elle ne marche jamais.
#   · DISCRIMINATION — une mutation PAR GARDE, et c'est la garde VISÉE qui rougit, nommée dans le
#     message. Un rouge sur une autre garde ne prouve rien de celle qu'on croyait éprouver
#     (3ᵉ faux vert : l'assert à côté de son point de lecture).
#
# LA FIXTURE EST COPIÉE DU RÉEL (`feedback_fixture_copiee_du_reel`) : la base de rejeu est un
# `pg_dump` de `db_portfolio`, pas un schéma fabriqué. Une fixture plus simple que la prod serait
# un test aveugle au vert — c'est précisément sur les 4 arêtes FK entrantes et sur la vue de
# fédération que la migration a des chances de casser, et aucune des deux ne s'invente.
#
# ⚠️ Jamais `psql << EOF` via `docker exec` : ça échoue EN SILENCE. `docker cp` + `psql -f`.
set -u
cd "$(dirname "$0")/.." || exit 1

PG=shared-postgres
SRC=db_portfolio
TPL=db_036_tpl
SCRATCH=db_036_neg
SQL=app/db/migrations/036_v2_archive_devocabularisation.sql

[ -f "$SQL" ] || { echo "ERREUR : $SQL absent — lancer d'abord \`bash app/db/migrations/_gen_036.sh\`"; exit 1; }

psql_adm() { docker exec "$PG" psql -U admin -d postgres -v ON_ERROR_STOP=1 -q "$@"; }
psql_neg() { docker exec "$PG" psql -U admin -d "$SCRATCH" -tA "$@"; }

# ── Le gabarit : une copie du réel, faite UNE fois ────────────────────────────────────────────
# `CREATE DATABASE … TEMPLATE` exige zéro connexion active sur le modèle ; `db_portfolio` en a
# (le pool de `portfolio-backend`). D'où le détour par un gabarit inerte, restauré depuis un dump.
echo "── fixture : copie de $SRC vers le gabarit $TPL"
psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" -c "DROP DATABASE IF EXISTS $TPL;" -c "CREATE DATABASE $TPL;" || exit 1
docker exec "$PG" sh -c "pg_dump -U admin -d $SRC | psql -U admin -q -d $TPL" >/dev/null 2>&1 || {
  echo "ERREUR : la restauration du gabarit a échoué"; exit 1; }

lignes_src=$(docker exec "$PG" psql -U admin -d "$TPL" -tAc \
  "SELECT count(*) FROM knowledge_entries")
echo "   gabarit prêt · knowledge_entries = $lignes_src lignes"
[ "$lignes_src" -gt 0 ] || { echo "ERREUR : gabarit VIDE — un test sur zéro ligne est vert par dégénérescence"; exit 1; }

# ── Applique le SQL (éventuellement muté) sur une base scratch neuve ──────────────────────────
appliquer() {
  local fichier="$1"
  psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" -c "CREATE DATABASE $SCRATCH TEMPLATE $TPL;" >/dev/null 2>&1
  docker cp "$fichier" "$PG:/tmp/036_neg.sql" >/dev/null
  docker exec "$PG" psql -U admin -d "$SCRATCH" -v ON_ERROR_STOP=1 -f /tmp/036_neg.sql 2>&1
}

echo
echo "══ SENS 1 — SATISFIABILITÉ : la 036 non mutée passe, et l'état d'après est celui annoncé ══"
sat_ok=0; sat_ko=0
sat() {  # libellé ¦ valeur obtenue ¦ valeur attendue
  if [ "$2" = "$3" ]; then sat_ok=$((sat_ok+1)); printf '  ok   %-62.62s %s\n' "$1" "$2"
  else sat_ko=$((sat_ko+1)); printf '  FAIL %-62.62s %s (attendu %s)\n' "$1" "$2" "$3"; fi
}

sortie=$(appliquer "$SQL"); rc=$?
if [ "$rc" -ne 0 ]; then
  echo "  FAIL la 036 non mutée ÉCHOUE — inutile d'éprouver la discrimination :"
  printf '%s\n' "$sortie" | grep -Ei 'error|erreur|EXCEPTION' | head -5 | sed 's/^/         /'
  sat_ko=$((sat_ko+1))
else
  sat "la 036 non mutée passe (COMMIT)" "0" "0"
  sat "tables dans archive_v2" \
      "$(psql_neg -c "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='archive_v2' AND c.relkind='r' AND c.relname <> 'liens_entrants'")" "15"
  sat "lignes de corpus préservées dans l'archive" \
      "$(psql_neg -c "SELECT count(*) FROM archive_v2.knowledge_entries")" "$lignes_src"
  sat "public.knowledge_entries est VIDE" \
      "$(psql_neg -c "SELECT count(*) FROM public.knowledge_entries")" "0"
  sat "public.knowledge_entries porte 27 colonnes (35 - 8)" \
      "$(psql_neg -c "SELECT count(*) FROM information_schema.columns WHERE table_schema='public' AND table_name='knowledge_entries'")" "27"
  sat "liens hors-grappe tracés, non perdus" \
      "$(psql_neg -c "SELECT count(*) FROM archive_v2.liens_entrants")" "3"
  sat "les 4 arêtes FK entrantes pointent la table NEUVE" \
      "$(psql_neg -c "SELECT count(*) FROM pg_constraint c JOIN pg_class t ON t.oid=c.confrelid JOIN pg_namespace n ON n.oid=t.relnamespace WHERE c.contype='f' AND n.nspname='public' AND c.conname IN ('calendar_events_session_v2_id_fkey','calendar_events_thesis_v2_id_fkey','portfolio_positions_thesis_v2_id_fkey','price_alerts_exit_plan_id_fkey')")" "4"
  # ⚠️ LE point que §3 de l'inventaire ne voyait pas : la vue lit-elle la table NEUVE ou l'archive ?
  # Elle est vide dans les deux cas au moment du test — donc on interroge son OID source, pas son
  # contenu. Un contrôle qui se contenterait de « la vue répond » serait vert sur l'archive.
  sat "la vue de fédération lit le schéma public, pas l'archive" \
      "$(psql_neg -c "SELECT n.nspname FROM pg_depend d JOIN pg_rewrite r ON r.oid=d.objid JOIN pg_class v ON v.oid=r.ev_class JOIN pg_class t ON t.oid=d.refobjid JOIN pg_namespace n ON n.oid=t.relnamespace WHERE v.relname='knowledge_federation_export' AND t.relname='knowledge_entries' AND t.relkind='r' LIMIT 1")" "public"
  sat "la séquence reprend au-delà de l'archive" \
      "$(psql_neg -c "SELECT (last_value > $lignes_src)::int FROM public.knowledge_entries_id_seq")" "1"
  sat "question_coverage existe" \
      "$(psql_neg -c "SELECT (to_regclass('public.question_coverage') IS NOT NULL)::int")" "1"
fi

echo
echo "══ SENS 2 — DISCRIMINATION : une mutation par garde, sur la garde VISÉE ══"
echo "   Les mutations s'insèrent juste AVANT le bloc de gardes : elles abîment l'état que les"
echo "   gardes lisent, pas les gardes elles-mêmes. Une mutation qui éditerait le \`IF\` prouverait"
echo "   seulement qu'on sait commenter une ligne."
MARQUEUR='-- ══ K. Gardes NOMMÉES, dans la transaction ══'

# ── garde visée ¦ SQL injecté avant le bloc de gardes ──────────────────────────────────────────
mutations=(
"036/K1¦ALTER TABLE archive_v2.eu_ir_scrapers RENAME TO eu_ir_scrapers_ailleurs;"
"036/K2¦INSERT INTO public.knowledge_entries (entry_type, content, source_type, reliability_score, reliability_tier, nature) VALUES ('fact_financial', 'mutation K2', 'edgar_official', 1.0, 'A', 'mesure');"
"036/K3¦ALTER TABLE public.knowledge_entries ADD COLUMN is_deleted boolean DEFAULT false;"
"036/K4¦ALTER TABLE public.knowledge_entries DROP COLUMN model_cutoff;"
"036/K5¦ALTER TABLE public.question_coverage DROP CONSTRAINT question_coverage_entry_id_fkey;"
"036/K6¦ALTER TABLE public.knowledge_curator_reports DROP CONSTRAINT knowledge_curator_reports_report_type_check; ALTER TABLE public.knowledge_curator_reports ADD CONSTRAINT knowledge_curator_reports_report_type_check CHECK (report_type IN ('mvdd', 'readiness', 'lint'));"
# Le CHECK EXISTE et ne refuse RIEN : c'est le mode de panne que « la contrainte est bien là » ne
# détecte jamais. K6 reste vert (aucun jeton dans son texte), seul K7 peut mordre.
"036/K7¦ALTER TABLE public.knowledge_entries DROP CONSTRAINT knowledge_entries_entry_type_check; ALTER TABLE public.knowledge_entries ADD CONSTRAINT knowledge_entries_entry_type_check CHECK (entry_type IS NOT NULL);"
# Le miroir : un CHECK qui refuse TOUT passerait le 1er volet de K7. Le vocabulaire RETENU doit
# passer, sinon la dévocabularisation aurait juste cassé l'écriture.
"036/K7¦ALTER TABLE public.knowledge_entries DROP CONSTRAINT knowledge_entries_entry_type_check; ALTER TABLE public.knowledge_entries ADD CONSTRAINT knowledge_entries_entry_type_check CHECK (entry_type IN ('agent_synthesis', 'analysis', 'fact_financial', 'fact_qualitative'));"
)

passes=0; ratees=0
for m in "${mutations[@]}"; do
  IFS='¦' read -r garde injection <<< "$m"
  tmp=$(mktemp -d); mute="$tmp/036.sql"

  python3 -c "
import sys, pathlib
src, dst, marqueur, inj = sys.argv[1:5]
s = pathlib.Path(src).read_text(encoding='utf-8')
if marqueur not in s:
    print('MARQUEUR INTROUVABLE'); sys.exit(1)
pathlib.Path(dst).write_text(s.replace(marqueur, inj + chr(10) + marqueur, 1), encoding='utf-8')
" "$SQL" "$mute" "$MARQUEUR" "$injection" || {
    printf '  ??   %-10s MUTATION CADUQUE (marqueur absent du SQL)\n' "$garde"
    ratees=$((ratees+1)); rm -rf "$tmp"; continue; }

  sortie=$(appliquer "$mute"); rc=$?
  rm -rf "$tmp"
  vise=$(printf '%s' "$sortie" | grep -F "$garde")
  reste=$(psql_neg -c "SELECT (to_regclass('archive_v2.knowledge_entries') IS NOT NULL)::int" 2>/dev/null)

  if [ "$rc" -eq 0 ]; then
    printf '  FAIL %-10s la migration COMMIT malgré la mutation — cette garde ne garde rien\n' "$garde"
    ratees=$((ratees+1))
  elif [ -z "$vise" ]; then
    printf '  FAIL %-10s rouge, mais PAS sur la garde visée :\n' "$garde"
    printf '%s\n' "$sortie" | grep -Ei 'ERROR|EXCEPTION' | head -2 | sed 's/^/         /'
    ratees=$((ratees+1))
  elif [ "$reste" = "1" ]; then
    # Une garde qui rougit sans que la transaction reparte en arrière laisserait la base à
    # mi-chemin : l'archive créée, le corpus déplacé, et rien pour le dire.
    printf '  FAIL %-10s rouge sur sa garde, mais la transaction N-A PAS ÉTÉ ANNULÉE\n' "$garde"
    ratees=$((ratees+1))
  else
    printf '  ok   %-10s %s\n' "$garde" "$(printf '%s' "$vise" | head -1 | cut -c1-96)"
    passes=$((passes+1))
  fi
done

psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" -c "DROP DATABASE IF EXISTS $TPL;" >/dev/null 2>&1

echo
echo "============================================================"
echo "satisfiabilité : $sat_ok ok / $sat_ko FAIL · discrimination : $passes ok / $ratees FAIL"
[ "$sat_ko" -eq 0 ] && [ "$ratees" -eq 0 ] || exit 1
