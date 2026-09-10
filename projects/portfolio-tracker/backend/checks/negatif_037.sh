#!/usr/bin/env bash
# TEST NÉGATIF de la migration 037 — éprouvé AVANT application.
#
#   bash checks/negatif_037.sh          # les 3 cas
#   bash checks/negatif_037.sh sat      # la satisfiabilité seule
#   bash checks/negatif_037.sh A        # un seul cas de discrimination (A, B)
#
# POURQUOI CE TEST EXISTE. La 037 ne déplace aucune donnée : elle réécrit DEUX prompts. Son enjeu
# n'est pas le volume, c'est que la panne qu'elle évite est TOTALE et MUETTE — un `ingestion-agent`
# qui enseigne encore `"entry_type": "risk"` voit 100 % de sa production rejetée par un contrat
# `extra="forbid"`, sans qu'aucun check hors ligne ne rougisse (leurs fixtures sont déjà conformes).
# Une migration dont l'échec est silencieux doit porter des gardes, et une garde n'est éprouvée
# qu'après avoir viré au ROUGE au moins une fois (`feedback_test_negatif_obligatoire`).
#
# LES DEUX SENS (`feedback_acceptation_rouge_bidirectionnelle`) :
#   · SATISFIABILITÉ — la 037 non mutée passe, et l'état d'après est celui annoncé (les deux prompts
#     réécrits, aucun motif retiré en base). Sans ça, deux rouges prouveraient qu'elle ne marche
#     jamais, pas qu'elle discrimine.
#   · DISCRIMINATION — une mutation PAR GARDE, et c'est la garde VISÉE qui rougit, nommée dans son
#     message (`037/K1`, `037/K2`). Un rouge sur l'autre garde ne prouve rien de celle qu'on croyait
#     éprouver — 3ᵉ faux vert, l'assert à côté de son point de lecture.
#
# ⚠️ K2 CHERCHE LA FORME D'ÉMISSION, PAS LE MOT. Les prompts corrigés PARLENT de `covers` et de
# `question_status` — la nouvelle règle est « plus de `covers` ni de `question_status` ». Une garde
# qui grepperait le mot rougirait sur l'énonciation de son propre interdit
# (`feedback_grep_interdit_lit_sa_propre_enonciation`) : un faux ROUGE, qui pousse à supprimer la
# phrase qui protège. D'où `"covers":` avec ses guillemets et ses deux-points. Le cas [B] éprouve
# que cette distinction MORD : il injecte la forme d'émission, pas le mot.
#
# LA FIXTURE EST COPIÉE DU RÉEL (`feedback_fixture_copiee_du_reel`) : la base de rejeu est un
# `pg_dump` de `db_portfolio`. Les prompts d'avant sont ceux que les agents lisent vraiment.
#
# ⚠️ Jamais `psql << EOF` via `docker exec` : ça échoue EN SILENCE. `docker cp` + `psql -f`.
set -u
cd "$(dirname "$0")/.." || exit 1

CAS="${1:-}"
PG=shared-postgres
SRC=db_portfolio
TPL=db_037_tpl
SCRATCH=db_037_neg
SQL=app/db/migrations/037_v2_prompt_sync_devocabularisation.sql

[ -f "$SQL" ] || { echo "ERREUR : $SQL absent — le générer d'abord avec _gen_037.py"; exit 2; }

psql_adm() { docker exec "$PG" psql -U admin -d postgres -v ON_ERROR_STOP=1 -q "$@"; }

echo "── fixture : copie de $SRC vers le gabarit $TPL"
psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" -c "DROP DATABASE IF EXISTS $TPL;" \
         -c "CREATE DATABASE $TPL;" || exit 2
docker exec "$PG" sh -c "pg_dump -U admin -d $SRC | psql -U admin -q -d $TPL" >/dev/null 2>&1 || {
  echo "ERREUR : la restauration du gabarit a échoué"; exit 2; }

n_v2=$(docker exec "$PG" psql -U admin -d "$TPL" -tAc \
  "SELECT count(*) FROM agent_prompts WHERE flow_version='v2'")
echo "   gabarit prêt · prompts v2 = $n_v2"
[ "${n_v2:-0}" -gt 0 ] || {
  echo "ERREUR : zéro prompt v2 — la 037 serait vraie par dégénérescence"; exit 2; }

# Applique une mutation SQL optionnelle (UNE ligne), puis la 037. Rend la sortie de psql.
appliquer() {
  local mutation="${1:-}"
  psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" -c "CREATE DATABASE $SCRATCH TEMPLATE $TPL;" >/dev/null 2>&1
  if [ -n "$mutation" ]; then
    docker exec "$PG" psql -U admin -d "$SCRATCH" -v ON_ERROR_STOP=1 -q -c "$mutation" >/dev/null || {
      echo "MUTATION ÉCHOUÉE — le cas ne prouve rien"; return 9; }
  fi
  docker cp "$SQL" "$PG:/tmp/037_neg.sql" >/dev/null
  docker exec "$PG" psql -U admin -d "$SCRATCH" -v ON_ERROR_STOP=1 -f /tmp/037_neg.sql 2>&1
}

interroger() { docker exec "$PG" psql -U admin -d "$SCRATCH" -tA -c "$1"; }

sat_ok=0; sat_ko=0; passes=0; ratees=0
sat() {  # libellé ¦ obtenu ¦ attendu
  if [ "$2" = "$3" ]; then sat_ok=$((sat_ok+1)); printf '  ok   %-58.58s %s\n' "$1" "$2"
  else sat_ko=$((sat_ko+1)); printf '  FAIL %-58.58s %s (attendu %s)\n' "$1" "$2" "$3"; fi
}

echo
echo "══ SENS 1 — SATISFIABILITÉ : la 037 non mutée passe, et l'état d'après est celui annoncé ══"
if [ -n "$CAS" ] && [ "$CAS" != "sat" ]; then
  echo "  (sautée : cas \`$CAS\` demandé — la satisfiabilité a son propre appel, \`sat\`)"
else
  sortie=$(appliquer); rc=$?
  if [ "$rc" -ne 0 ] || printf '%s' "$sortie" | grep -q "^ERROR"; then
    echo "  FAIL la 037 non mutée ÉCHOUE — inutile d'éprouver la discrimination :"
    printf '%s\n' "$sortie" | sed 's/^/       /'
    exit 1
  fi
  sat "la 037 non mutée va jusqu'au COMMIT" \
      "$(printf '%s' "$sortie" | grep -c '^COMMIT')" "1"
  # Le point de lecture des agents, c'est la BASE — pas le fichier. On y relit.
  sat "les 2 prompts visés ont été réécrits (version +1)" \
      "$(interroger "SELECT count(*) FROM agent_prompts WHERE flow_version='v2'
                      AND agent_name IN ('ingestion-agent','search-worker') AND version >= 2")" "2"
  sat "aucun prompt v2 ne porte encore la clef \`\"covers\":\`" \
      "$(interroger "SELECT count(*) FROM agent_prompts WHERE flow_version='v2'
                      AND prompt_text LIKE '%\"covers\":%'")" "0"
  sat "aucun prompt v2 ne porte encore \"entry_type\": \"risk\"" \
      "$(interroger "SELECT count(*) FROM agent_prompts WHERE flow_version='v2'
                      AND prompt_text LIKE '%\"entry_type\": \"risk\"%'")" "0"
  # ⚠️ La 037 ne doit PAS avoir touché l'ancrage probabiliste des 10 autres prompts : `base_rate`
  # y est un CHAMP de contrat (règle 2), homonyme de l'`entry_type` renommé. Le confondre aurait
  # retiré le garde-fou central de la règle 2 — ce test le dit en positif.
  sat "l'ancrage \`base_rate\` (règle 2) est INTACT ailleurs" \
      "$(interroger "SELECT count(*) FROM agent_prompts WHERE flow_version='v2'
                      AND agent_name IN ('bull-agent','bear-agent','thesis-agent','debate-agent')
                      AND prompt_text LIKE '%base_rate%'")" "4"
fi

echo
echo "══ SENS 2 — DISCRIMINATION : une mutation par garde, sur la garde VISÉE ══"
# ⚠️ Chaque mutation tient sur UNE ligne : `read` s'arrête au premier saut de ligne, et une
# mutation tronquée est un cas négatif qui ne prouve rien.
#
# libellé ¦ garde attendue ¦ mutation SQL
CAS_LIST=(
"[A] K1 — la cible n'existe plus, l'UPDATE ne mord pas¦037/K1¦UPDATE agent_prompts SET agent_name='search-worker-renomme' WHERE agent_name='search-worker' AND flow_version='v2';"
"[B] K2 — un AUTRE prompt v2 porte la forme d'émission¦037/K2¦UPDATE agent_prompts SET prompt_text = prompt_text || E'\n\"covers\": \"moat.preuves\"' WHERE agent_name='research-agent' AND flow_version='v2';"
)

for ligne in "${CAS_LIST[@]}"; do
  IFS='¦' read -r libelle garde mutation <<< "$ligne"
  code="${libelle:1:1}"
  [ -n "$CAS" ] && [ "$CAS" != "$code" ] && continue
  sortie=$(appliquer "$mutation")
  if printf '%s' "$sortie" | grep -q "$garde"; then
    passes=$((passes+1)); printf '  ok   %-52.52s rouge sur %s\n' "$libelle" "$garde"
  else
    ratees=$((ratees+1))
    # ⚠️ Message construit en clair, pas dans un `${var:-…}` : une apostrophe dans le défaut d'une
    # expansion casse l'analyse syntaxique de bash — le script mourait AVANT ses asserts, 2ᵉ faux vert.
    autre=$(printf '%s' "$sortie" | grep -oE '037/K[0-9]' | head -1)
    if [ -n "$autre" ]; then motif="rouge sur $autre — la mauvaise garde"
    else motif="aucune garde n a rougi : la 037 a COMMIT"; fi
    printf '  FAIL %-52.52s %s\n' "$libelle" "$motif"
  fi
done

psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" -c "DROP DATABASE IF EXISTS $TPL;" >/dev/null 2>&1

echo
echo "============================================================"
echo "satisfiabilité : $sat_ok ok / $sat_ko FAIL · discrimination : $passes ok / $ratees FAIL"
[ "$sat_ko" -eq 0 ] && [ "$ratees" -eq 0 ] || exit 1
exit 0
