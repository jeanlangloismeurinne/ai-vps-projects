#!/usr/bin/env bash
# TEST BIDIRECTIONNEL des critères T1 / T1bis / T2 de `tools/acceptation_frameworks.py` (spec §9.2),
# réécrits au lot 2b.
#
#   bash checks/negatif_acceptation_frameworks.sh            # les 7 cas
#   bash checks/negatif_acceptation_frameworks.sh D          # un seul cas (A…F), ou `sat`
#
# Le second usage n'est pas un confort : il existe parce qu'un cas isolé est le seul moyen de
# relire l'INTÉGRALITÉ de la sortie d'acceptation sous une mutation donnée. Le bilan agrégé dit
# QUE l'assert visé a rougi, pas ce que le script a imprimé autour.
#
# POURQUOI CE FICHIER EXISTE. `tools/acceptation_frameworks.py` rougit sur ses 8 critères, et c'est
# voulu : il est écrit AVANT la capacité. Mais un rouge, seul, ne distingue pas « le critère est
# exigeant » de « le critère est impossible » — un test qui ne peut pas virer au vert n'est pas une
# exigence, c'est un décor. D'où les DEUX sens
# (`feedback_acceptation_rouge_bidirectionnelle`) :
#
#   · SATISFIABILITÉ — sur une base où les artefacts des lots 2c-4 existent, T1/T1bis/T2 virent
#     au VERT. Sans ça, la discrimination ci-dessous ne prouverait rien.
#   · DISCRIMINATION — une mutation PAR CRITÈRE, et c'est l'assert VISÉ qui rougit, les autres
#     restant verts. Un rouge qui déborde sur trois asserts ne dit pas lequel discrimine (3ᵉ faux
#     vert : l'assert à côté de son point de lecture) — chaque mutation déclare donc ce qui doit
#     rougir ET ce qui doit rester vert.
#
# T1bis est la raison d'être de ce harnais. Un critère qui exige qu'il MANQUE quelque chose est le
# plus facile à satisfaire par accident : n'importe quelle collecte incomplète rend « ≥ 1 » vrai.
# C'est pourquoi il NOMME son témoin (`qf_1.cout_du_capital`), et pourquoi la mutation [D] sert ce
# témoin-là en laissant tous les autres trous ouverts — le premier assert reste vert, le second
# rougit. Aucune autre mutation ne sépare ces deux clauses.
#
# LA FIXTURE EST COPIÉE DU RÉEL (`feedback_fixture_copiee_du_reel`) : la scratch est un `pg_dump`
# de `db_portfolio`, la 036 y est appliquée, et le corpus est remis depuis `archive_v2`. Les liens
# de couverture désignent des entries réelles par sous-requête, jamais un id en dur. Aucune ligne
# de production n'est touchée.
#
# ⚠️ Jamais dans le conteneur `portfolio-backend` : il porte le code déployé, qui peut précéder ce
# qu'on éprouve. On monte le dépôt en lecture seule dans une instance neuve de son image.
# ⚠️ Jamais `psql << EOF` via `docker exec` : ça échoue EN SILENCE. `docker cp` + `psql -f`.
set -u
cd "$(dirname "$0")/.." || exit 1
CAS="${1:-}"          # vide = les 7 ; `sat` = la satisfiabilité seule ; `A`…`F` = une mutation

PG=shared-postgres
SRC=db_portfolio
TPL=db_accfw_tpl
SCRATCH=db_accfw_neg
SQL=app/db/migrations/036_v2_archive_devocabularisation.sql
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}') || exit 1

[ -f "$SQL" ] || { echo "ERREUR : $SQL absent — lancer \`bash app/db/migrations/_gen_036.sh\`"; exit 1; }

psql_adm() { docker exec "$PG" psql -U admin -d postgres -v ON_ERROR_STOP=1 -q "$@"; }
run_sql()  { docker cp "$1" "$PG:/tmp/accfw.sql" >/dev/null &&
             docker exec "$PG" psql -U admin -d "$SCRATCH" -v ON_ERROR_STOP=1 -q -f /tmp/accfw.sql; }

# L'URL de la scratch : la vraie, base substituée. Le rôle applicatif est conservé — jouer
# l'acceptation en `admin` masquerait une permission manquante que la production rencontrerait.
URL_SCRATCH=$(grep -m1 '^DATABASE_URL=' .env | cut -d= -f2- | sed "s#/${SRC}\$#/${SCRATCH}#")
case "$URL_SCRATCH" in
  */$SCRATCH) ;;
  *) echo "ERREUR : DATABASE_URL ne se termine pas par /$SRC — substitution impossible"; exit 1;;
esac

# ── Le gabarit : une copie du réel, faite UNE fois ────────────────────────────────────────────
# `CREATE DATABASE … TEMPLATE` exige zéro connexion active sur le modèle ; `db_portfolio` en a.
echo "── fixture : copie de $SRC vers le gabarit $TPL"
psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" -c "DROP DATABASE IF EXISTS $TPL;" \
         -c "CREATE DATABASE $TPL;" || exit 1
docker exec "$PG" sh -c "pg_dump -U admin -d $SRC | psql -U admin -q -d $TPL" >/dev/null 2>&1 || {
  echo "ERREUR : la restauration du gabarit a échoué"; exit 1; }

# Les deux SQL générés — essentiels et substitutions lus chez leurs détenteurs, jamais recopiés.
GEN=$(mktemp -d)
docker run --rm -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app --env-file checks/env.checks "$IMG" \
  python checks/_seed_acceptation_frameworks.py corpus > "$GEN/corpus.sql" || {
  echo "ERREUR : génération du corpus scratch"; cat "$GEN/corpus.sql"; exit 1; }
docker run --rm -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app --env-file checks/env.checks "$IMG" \
  python checks/_seed_acceptation_frameworks.py > "$GEN/seed.sql" || {
  echo "ERREUR : génération de la fixture"; cat "$GEN/seed.sql"; exit 1; }
echo "   gabarit prêt · fixture $(wc -l < "$GEN/seed.sql") lignes de SQL"

# ── Reconstruit la scratch : 036 + corpus + fixture + mutation éventuelle ──────────────────────
preparer() {
  local mutation="${1:-}"
  psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" \
           -c "CREATE DATABASE $SCRATCH TEMPLATE $TPL;" >/dev/null 2>&1 || return 1
  docker cp "$SQL" "$PG:/tmp/accfw.sql" >/dev/null
  docker exec "$PG" psql -U admin -d "$SCRATCH" -v ON_ERROR_STOP=1 -q -f /tmp/accfw.sql \
    >/dev/null 2>&1 || { echo "     (036 a échoué sur la scratch)"; return 1; }
  run_sql "$GEN/corpus.sql" >/dev/null 2>&1 || { echo "     (corpus scratch)"; return 1; }
  run_sql "$GEN/seed.sql"   >/dev/null 2>&1 || { echo "     (fixture)"; return 1; }
  # Le rôle applicatif doit voir les tables neuves : la 036 et la fixture les créent en `admin`.
  # Jouer l'acceptation en `admin` masquerait une permission manquante que la prod rencontrerait.
  docker exec "$PG" psql -U admin -d "$SCRATCH" -q \
    -c "GRANT USAGE ON SCHEMA public, archive_v2 TO portfolio_user;" \
    -c "GRANT ALL ON ALL TABLES IN SCHEMA public, archive_v2 TO portfolio_user;" \
    -c "GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO portfolio_user;" >/dev/null 2>&1
  if [ -n "$mutation" ]; then
    printf '%s\n' "$mutation" > "$GEN/mut.sql"
    run_sql "$GEN/mut.sql" >/dev/null 2>&1 || { echo "     (mutation refusée par la base)"; return 1; }
  fi
}

jouer() {
  docker run --rm --network coolify -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app \
    --env-file checks/env.checks --env-file .env -e "DATABASE_URL=$URL_SCRATCH" \
    "$IMG" python tools/acceptation_frameworks.py 2>/dev/null
}

# Le statut d'un assert NOMMÉ. `ok` / `FAIL` / vide si l'assert n'a pas été imprimé du tout —
# ce troisième cas est un échec, pas un vert : un critère non atteint n'est pas un critère tenu.
statut() { printf '%s\n' "$1" | grep -F "$2" | grep -oE '^ +(ok|FAIL)' | tr -d ' ' | head -1; }

L_T1="T1 — zéro ingrédient essentiel ni servi ni mandaté"
L_T1B="T1bis — au moins un essentiel non servi ET mandaté"
L_TEM="est de ceux-là"
L_T2="T2 — zéro question auto-fondée"

echo
echo "══ SENS 1 — SATISFIABILITÉ : sur la fixture, T1/T1bis/T2 PEUVENT virer au vert ══"
sat_ok=0; sat_ko=0
sat() { if [ "$2" = "$3" ]; then sat_ok=$((sat_ok+1)); printf '  ok   %-56.56s %s\n' "$1" "$2"
        else sat_ko=$((sat_ko+1)); printf '  FAIL %-56.56s %s (attendu %s)\n' "$1" "$2" "$3"; fi; }

if [ -n "$CAS" ] && [ "$CAS" != "sat" ]; then
  echo "  (sautée : cas \`$CAS\` demandé — la satisfiabilité a son propre appel, \`sat\`)"
elif ! preparer ""; then
  echo "  FAIL la fixture ne se pose pas — inutile d'éprouver la discrimination"
  sat_ko=$((sat_ko+1)); sortie=""
else
  sortie=$(jouer)
  bilan=$(printf '%s\n' "$sortie" | grep -cE '^[0-9]+ vérifications OK, [0-9]+ échec')
  sat "le script atteint son bilan (forme, pas \`tail -1\`)" "$bilan" "1"
  sat "T1 vert"                "$(statut "$sortie" "$L_T1")"  "ok"
  sat "T1bis vert (il manque, et c'est réclamé)" "$(statut "$sortie" "$L_T1B")" "ok"
  sat "T1bis vert sur son TÉMOIN nommé" "$(statut "$sortie" "$L_TEM")" "ok"
  sat "T2 vert"                "$(statut "$sortie" "$L_T2")"  "ok"
  # Une fixture qui ne servirait rien rendrait T2 vert par dégénérescence : il doit voir des
  # questions `repondu`, sinon « 0 auto-fondée » serait vrai sur zéro ligne.
  sat "T2 a de la matière (questions \`repondu\` > 0)" \
      "$(printf '%s\n' "$sortie" | grep -oE 'questions `repondu` : [0-9]+' | grep -oE '[0-9]+')" "2"
fi

echo
echo "══ SENS 2 — DISCRIMINATION : une mutation par critère, sur l'assert VISÉ ══"
echo "   Chaque mutation déclare ce qui doit ROUGIR et ce qui doit rester VERT. Les mutations"
echo "   abîment l'état que les critères lisent — jamais le code des critères."

# ⚠️ SQL sur UNE ligne : `read` s'arrête au premier saut de ligne, et une injection tronquée
# passerait pour une mutation posée. Une mutation muette est un cas négatif qui ne prouve rien.
# libellé ¦ asserts attendus ROUGES (séparés par ~) ¦ asserts attendus VERTS ¦ SQL
_V="(SELECT framework_version FROM question_coverage LIMIT 1)"
_E1="(SELECT e.id FROM knowledge_entries e WHERE e.ticker_id = m.ticker_id AND e.superseded_by IS NULL AND e.entry_type = 'fact_financial' ORDER BY e.id LIMIT 1)"
_E2="(SELECT e.id FROM knowledge_entries e WHERE e.ticker_id = t AND e.superseded_by IS NULL AND e.entry_type = 'fact_financial' ORDER BY e.id LIMIT 1)"
_COLS="INSERT INTO question_coverage (framework_id, framework_version, question_id, ingredient_id, entry_id)"

mutations=(
"[A] T1 — un essentiel n'est ni servi ni mandaté¦$L_T1¦$L_T1B~$L_TEM~$L_T2¦DELETE FROM framework_mandates WHERE question_id='qf_3' AND ingredient_id='investissement_de_maintien';"

"[B] T1 — un mandat FERMÉ ne ferme rien¦$L_T1¦$L_T1B~$L_TEM~$L_T2¦UPDATE framework_mandates SET statut='clos' WHERE question_id='qf_4' AND ingredient_id='clauses_de_sauvegarde';"

"[C] T1bis — couverture à 100 %, le pilote DOIT échouer¦$L_T1B~$L_TEM¦$L_T1~$L_T2¦$_COLS SELECT m.framework_id, $_V, m.question_id, m.ingredient_id, $_E1 FROM framework_mandates m ON CONFLICT DO NOTHING;"

"[D] T1bis — le témoin servi, les autres trous intacts¦$L_TEM¦$L_T1~$L_T1B~$L_T2¦$_COLS SELECT 'qualite_financiere', $_V, 'qf_1', 'cout_du_capital', $_E2 FROM unnest(ARRAY['NVDA','MSFT','RVMD']) AS t ON CONFLICT DO NOTHING;"

"[E] T2 — la question fondée par une synthèse d'elle-même¦$L_T2¦$L_T1~$L_T1B~$L_TEM¦UPDATE question_coverage SET entry_id = (SELECT id FROM knowledge_entries WHERE ticker_id='NVDA' AND entry_type='agent_synthesis' AND superseded_by IS NULL ORDER BY id LIMIT 1) WHERE question_id='qf_2' AND ingredient_id='resultat_net';"

"[F] T2 — plus aucune question \`repondu\` : vrai sur zéro ligne¦$L_T2¦$L_T1~$L_T1B~$L_TEM¦UPDATE framework_answers SET statut='non_fondable' WHERE statut='repondu';"
)

passes=0; ratees=0
for m in "${mutations[@]}"; do
  IFS='¦' read -r libelle rouges verts injection <<< "$m"
  case "$CAS" in "") ;; sat) continue ;; *) [ "${libelle:1:1}" = "$CAS" ] || continue ;; esac
  if ! preparer "$injection"; then
    printf '  FAIL %-52.52s la mutation ne se pose pas sur la base\n' "$libelle"
    ratees=$((ratees+1)); continue
  fi
  s=$(jouer)
  if ! printf '%s\n' "$s" | grep -qE '^[0-9]+ vérifications OK, [0-9]+ échec'; then
    printf '  FAIL %-52.52s le script est MORT avant son bilan\n' "$libelle"
    ratees=$((ratees+1)); continue
  fi
  probleme=""
  IFS='~' read -ra liste <<< "$rouges"
  for a in "${liste[@]}"; do
    lu=$(statut "$s" "$a")
    [ "$lu" = "FAIL" ] || probleme="$probleme"$'\n'"         · attendu ROUGE, lu '${lu:-ASSERT ABSENT}' → $a"
  done
  IFS='~' read -ra liste <<< "$verts"
  for a in "${liste[@]}"; do
    lu=$(statut "$s" "$a")
    [ "$lu" = "ok" ] || probleme="$probleme"$'\n'"         · attendu VERT, lu '${lu:-ASSERT ABSENT}' → $a"
  done
  if [ -z "$probleme" ]; then
    printf '  ok   %-52.52s rouge sur l’assert visé, les autres verts\n' "$libelle"
    passes=$((passes+1))
  else
    printf '  FAIL %-52.52s%s\n' "$libelle" "$probleme"
    ratees=$((ratees+1))
  fi
done

psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" -c "DROP DATABASE IF EXISTS $TPL;" >/dev/null 2>&1
rm -rf "$GEN"

echo
echo "============================================================"
echo "satisfiabilité : $sat_ok ok / $sat_ko FAIL · discrimination : $passes ok / $ratees FAIL"
[ "$sat_ko" -eq 0 ] && [ "$ratees" -eq 0 ] || exit 1
