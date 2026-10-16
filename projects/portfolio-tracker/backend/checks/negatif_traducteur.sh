#!/usr/bin/env bash
# TEST NÉGATIF de `check_traducteur.py` — BIDIRECTIONNEL (moitié déterministe du traducteur).
#
#   0. SATISFIABILITÉ — le check non muté est vert ;
#   puis une MUTATION PAR GARDE, chacune exigeant : (1) exit ≠ 0, (2) le FAIL sur l'assert NOMMÉ,
#   (3) la ligne de bilan atteinte (mêmes trois conditions que les autres négatifs).
#
#   bash checks/negatif_traducteur.sh
set -u
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
SRC="app/agents/v2/traducteur.py"
CHECK="checks/check_traducteur.py"

run_check() {  # $1 = racine backend à monter
  docker run --rm --network none -v "$1:/app:ro" \
    -w /app -e PYTHONPATH=/app --env-file checks/env.checks \
    "$IMG" python "$CHECK" 2>&1
}

base=$(run_check "$PWD"); base_rc=$?
if [ "$base_rc" -ne 0 ] || printf '%s' "$base" | grep -q 'FAIL'; then
  echo "  FAIL satisfiabilité — le check rougit AVANT toute mutation : rien ne peut être prouvé"
  printf '%s\n' "$base" | grep -F 'FAIL' | head -5
  exit 1
fi
printf '  ok   satisfiabilité · %s\n\n' "$(printf '%s' "$base" | grep -E 'vérifications OK')"

# fichier ¦ motif remplacé ¦ remplaçant ¦ assert (fragment de LABEL) qui rougit — backticks échappés
mutations=(
"$SRC¦.mode == \"variable\"]¦.mode in (\"variable\", \"sans_objet\")]¦qf_1 (rendement du capital) est ABSENT"
"$SRC¦                \"variable_archetype\": q.variables_par_archetype[archetype].variable,¦                \"variable_archetype\": q.variables_par_archetype[archetype].variable,\n                \"plancher_tier\": q.plancher_tier,¦ne contient pas \`plancher_tier\`"
"$SRC¦    items: list[CollectionPlanItem] = Field(min_length=1)¦    items: list[CollectionPlanItem] = Field(min_length=1)\n    ticker_id: str = \"x\"¦n'a QUE"
"$SRC¦        framework_version=fichier.schema_version,¦        framework_version=archetype,¦pose lui-même"
"$SRC¦    if archetype not in set(fichier.archetypes):¦    if False:¦[O-tôt] archétype inconnu"
"$SRC¦    valider_pont_collection_plan(plan, fichier=fichier, questions=questions)¦    None  # pont retiré¦passe le plan au pont"
# ── l'identité de l'émetteur (lot 7, 2026-09-26 — le plan RVMD rédigé sur Ryvu) ──────────────────
"$SRC¦            \"raison_sociale\": emetteur.raison_sociale,¦            \"raison_sociale\": emetteur.symbole,¦porte la raison sociale ET le CIK"
"$SRC¦    *, emetteur: IdentiteEmetteur, horloge:¦    *, emetteur: IdentiteEmetteur = IdentiteEmetteur(\"?\", 0, \"?\"), horloge:¦REFUSE de se construire sans identité"
"$SRC¦JAMAIS CELLE QUE SUGGÈRE LE \"¦\"¦la consigne dit que l'entreprise"
"$SRC¦        emetteur = await identite_de_l_emetteur(conn, ticker_id)¦        emetteur = IdentiteEmetteur(ticker_id, 0, ticker_id)¦AVANT la dépense modèle"
"$SRC¦        fichier, framework_id, archetype, ticker_id, emetteur=emetteur,¦        fichier, framework_id, archetype, ticker_id, emetteur=IdentiteEmetteur(ticker_id, 0, ticker_id),¦et la passe au contexte"
"app/knowledge/edgar_feed.py¦    return await resolve_identite(await symbole_de_marche(conn, ticker_id))¦    return await resolve_identite(ticker_id)¦passe par \`symbole_de_marche\`"
# #113 — la consigne ne dit plus que « quatre derniers trimestres » ⟹ douze_mois_glissants.
"$SRC¦\`douze_mois_glissants\` — jamais \`exercice_clos\`.¦\`douze_mois_glissants\`.¦ENSEIGNE la période"
# #120 — l'horloge du traducteur (plan #221 : 19/19 lignes ancrées sur le 10-K, qf_8 née périmée).
"$SRC¦                horloge.derniere_cloture.isoformat() if horloge.derniere_cloture else None),¦                None),¦porte la clôture des derniers comptes publiés"
"$SRC¦            \"date_du_jour\": horloge.date_du_jour.isoformat(),¦            \"date_du_jour\": None,¦porte la date du jour"
"$SRC¦\"Clôture des derniers comptes publiés INCONNUE du système¦\"Clôture des derniers comptes publiés pas connue du système¦clôture inconnue : la clé"
"$SRC¦    *, emetteur: IdentiteEmetteur, horloge: HorlogeDuPlan,¦    *, emetteur: IdentiteEmetteur, horloge: HorlogeDuPlan = HorlogeDuPlan(date(2000, 1, 1), None, {}),¦REFUSE de se construire sans horloge"
"$SRC¦    \"RÈGLE DE FRAÎCHEUR — tu n'as¦    \"RÈGLE — tu n'as¦consigne enseigne la RÈGLE"
"$SRC¦Cela vaut AUSSI pour une clause¦Cela vaut pour une clause¦consigne enseigne la RÈGLE"
"$SRC¦        horloge = await horloge_du_plan(conn, ticker_id, fichier)¦        horloge = HorlogeDuPlan(date.today(), None)¦lit l'horloge AVANT"
"$SRC¦emetteur=emetteur, horloge=horloge,¦emetteur=emetteur, horloge=HorlogeDuPlan(date.today(), None),¦contexte du modèle (#120)"
"$SRC¦derniere_cloture=derniere_cloture_publiee(ancre),¦derniere_cloture=None,¦l'horloge du plan est celle"
# Jalon A (2026-10-13) — la fraîcheur PAR QUESTION (modèle économique : NVDA au 10-K du 26/01, RVMD
# « non commercialisé » après l'approbation du 26/08).
"$SRC¦FraicheurQuestion(\"fait_important\", pese.seuil, pese.resume(), a_lire)¦FraicheurQuestion(\"fait_important\", pese.event_date, pese.resume(), a_lire)¦date minimale = la CLÔTURE publiée"
"$SRC¦                lus = faits_a_lire(lk, cloture=cloture)¦                lus = []¦un fait À LIRE, nommé"
"$SRC¦                reste = [e for e in lk.recents if id(e) not in lus_ids]¦                reste = list(lk.recents)¦le financement postérieur est À LIRE"
"$SRC¦            elif lk.status == \"none\":¦            elif lk.status in (\"none\", \"unavailable\"):¦flux illisible"
"$SRC¦rouvrent=types_qui_rouvrent(fichier, q.id),¦rouvrent=frozenset(t.id for t in fichier.types_evenement),¦me_6 (ni accord ni incident"
"$SRC¦                \"fraicheur\": _lecture_fraicheur(horloge.fraicheur[q.id]),¦                \"fraicheur\": {},¦porte la date minimale de me_2"
"$SRC¦_lecture_fraicheur(horloge.fraicheur[q.id])¦_lecture_fraicheur(horloge.fraicheur.get(q.id, FraicheurQuestion(\"aucun_fait\", None, \"?\")))¦SANS horloge fait refuser"
"$SRC¦situation AVANT le {fq.depuis.isoformat()} naîtra¦situation AVANT ce fait naîtra¦porte la date minimale de me_2"
"$SRC¦l'effet — ils ne périment PAS les pièces¦l'effet — ils périment les pièces¦nomme l'approbation comme fait À LIRE"
"$SRC¦            \"date_minimale_des_pieces\": fq.depuis.isoformat() if fq.depuis else None,¦            **({\"date_minimale_des_pieces\": fq.depuis.isoformat()} if fq.depuis else {}),¦clé présente, jamais omise"
"$SRC¦elle PRIME sur la clôture¦elle complète la clôture¦date minimale PRIME"
"$SRC¦fraicheur=fraicheur_des_questions(ancre, notes, fichier),¦fraicheur=fraicheur_des_questions(ancre, {}, fichier),¦lue sur l'ancre ET les notes"
# Jalon A — la garde `exercice_clos`
"$SRC¦        if annuelle is None or fq.depuis > annuelle:¦        if annuelle is not None and fq.depuis > annuelle:¦clôture = un trimestre"
"$SRC¦        if annuelle is None or fq.depuis > annuelle:¦        if annuelle is None or fq.depuis >= annuelle:¦la dernière clôture EST l'exercice"
"$SRC¦        if it.statut != \"traduit\" or it.periode != \"exercice_clos\":¦        if it.statut != \"traduit\":¦pas \`cumul_publie\`"
"$SRC¦        if fq is None or fq.depuis is None:¦        if fq is None:¦pas une question sans date minimale"
"$SRC¦    fautives = lignes_exercice_clos_perimees(plan, horloge, fichier=fichier)¦    fautives = []¦renvoie UNE fois"
"$SRC¦        if par_duree and ing is not None and not (ing.duree_de_vie == \"chiffre_courant\"¦        if False and (ing.duree_de_vie == \"chiffre_courant\"¦historiques et description annuelle à l'exercice clos"
"$SRC¦    par_duree = fichier is not None and fichier.fraicheur_par_duree_de_vie¦    par_duree = fichier is not None¦témoin ordre 0"
"$SRC¦                                  cost_usd=run.cost_usd + second.cost_usd,¦                                  cost_usd=second.cost_usd,¦coûte les DEUX appels"
"$SRC¦                horloge.derniere_cloture_annuelle.isoformat()¦                None and horloge.derniere_cloture_annuelle.isoformat()¦clôture du dernier exercice, datée"
"$SRC¦                         derniere_cloture_annuelle=derniere_cloture_annuelle_publiee(ancre))¦                         derniere_cloture_annuelle=None)¦lit la clôture d'exercice sur le flux"
)

passes=0; ratees=0
for m in "${mutations[@]}"; do
  IFS='¦' read -r fichier vieux neuf attendu <<< "$m"
  tmp=$(mktemp -d)
  cp -r . "$tmp/backend" 2>/dev/null
  rm -rf "$tmp/backend/.git" 2>/dev/null
  find "$tmp/backend" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
  cible="$tmp/backend/$fichier"

  if ! python3 -c "
import sys, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_text(encoding='utf-8')
vieux, neuf = sys.argv[2], sys.argv[3].replace('\\\\n', chr(10))
if vieux not in s:
    print('MOTIF INTROUVABLE'); sys.exit(1)
p.write_text(s.replace(vieux, neuf, 1), encoding='utf-8')
" "$cible" "$vieux" "$neuf"; then
    printf '  ?? %-58.58s MUTATION CADUQUE (motif absent du source)\n' "$attendu"
    ratees=$((ratees + 1)); rm -rf "$tmp"; continue
  fi

  out=$(run_check "$tmp/backend"); rc=$?
  rm -rf "$tmp"

  bilan=$(printf '%s' "$out" | grep -E 'vérifications OK')
  rouge=$(printf '%s' "$out" | grep -F 'FAIL' | grep -F "$attendu")

  if [ -z "$bilan" ]; then
    printf '  FAIL %-56.56s script MORT avant son bilan (2ᵉ faux vert)\n' "$attendu"
    printf '%s\n' "$out" | tail -4
    ratees=$((ratees + 1))
  elif [ "$rc" -eq 0 ]; then
    printf '  FAIL %-56.56s le check reste VERT — ce critère ne garde rien\n' "$attendu"
    ratees=$((ratees + 1))
  elif [ -z "$rouge" ]; then
    printf '  FAIL %-56.56s rouge, mais PAS sur l'\''assert visé\n' "$attendu"
    printf '%s\n' "$out" | grep -F 'FAIL' | head -3 | sed 's/^/         /'
    ratees=$((ratees + 1))
  else
    printf '  ok   %-56.56s rouge sur son assert · %s\n' "$attendu" "$bilan"
    passes=$((passes + 1))
  fi
done

echo
echo "============================================================"
echo "$passes mutations correctement détectées, $ratees échec(s)"
[ "$ratees" -eq 0 ] || exit 1
