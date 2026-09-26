#!/usr/bin/env bash
# TEST NÉGATIF de `check_collecte_executor.py` — BIDIRECTIONNEL.
#   0. SATISFIABILITÉ (le check non muté est vert) ; puis une MUTATION PAR GARDE, chacune exigeant
#      exit≠0 + FAIL sur l'assert NOMMÉ + ligne de bilan atteinte.
#   bash checks/negatif_collecte_executor.sh
set -u
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
SRC="app/agents/v2/collecte_executor.py"
CHECK="checks/check_collecte_executor.py"

run_check() { docker run --rm --network none -v "$1:/app:ro" -w /app -e PYTHONPATH=/app \
    --env-file checks/env.checks "$IMG" python "$CHECK" 2>&1; }

base=$(run_check "$PWD"); base_rc=$?
if [ "$base_rc" -ne 0 ] || printf '%s' "$base" | grep -q 'FAIL'; then
  echo "  FAIL satisfiabilité — le check rougit AVANT toute mutation"
  printf '%s\n' "$base" | grep -F 'FAIL' | head -5; exit 1
fi
printf '  ok   satisfiabilité · %s\n\n' "$(printf '%s' "$base" | grep -E 'vérifications OK')"

# Chaque mutation désarme UNE garde ; l'assert nommé (attendu) doit rougir.
mutations=(
# §2 ─ le véto `_est_derivee` : le retirer laisse FCF mapper sur operating_cash_flow → edgar
"$SRC¦    if _est_derivee(_norm(metrique)):¦    if False:  # mutation: supprime le véto dérivée¦FCF ≠ OCF"
# §1 ─ le filtre source SEC : le retirer laisse un communiqué aller chez EDGAR
'app/agents/v2/collecte_executor.py¦    if not _FORME_SEC.search(_norm(ligne.source_pressentie)):\n        return "web"¦    if False:  # mutation: supprime le filtre source SEC\n        return "web"¦le poste est juste, mais la source pressentie'
# §1 ─ le filtre catalogue POSTES : le retirer laisse `ebitda` (inventé) aller chez EDGAR
"$SRC¦    if not poste or poste not in _TOUS_POSTES:¦    if not poste:  # mutation: retire le filtre catalogue¦hors catalogue"
# §4 ─ la déduction de type d'entry : la supprimer → tout devient fact_qualitative
"$SRC¦    if any(j in n for j in _JETONS_FINANCIERS):¦    if False:¦trimestrielle (cash burn)"
# §5 ─ reliability_min permissif : le durcir → le check detect la violation
"$SRC¦        reliability_min=0.40,¦        reliability_min=0.85,¦le collecteur ne juge pas la valeur"
# §5 ─ field_path absent : en injecter un → ré-ancrerait la question
"$SRC¦        output_schema=OutputSchema(entry_type=entry_type_pour_metrique(ligne.metrique)),¦        output_schema=OutputSchema(entry_type=entry_type_pour_metrique(ligne.metrique), field_path=\"qf_1.revenue\"),¦ancrerait la question"
# §6 ─ la porte d'erreur générique : la restreindre → l'exception propage
"$SRC¦    except Exception as e:  # sortie non conforme / réseau → #25, jamais un crash¦    except KeyboardInterrupt as e:  # sortie non conforme / réseau → #25, jamais un crash¦jamais une exception qui tue le lot"
# §7 ─ le câblage carte : court-circuiter le check `indisponible` → la carte est ignorée
'app/agents/v2/collecte_executor.py¦        return "web" if carte_statut == "indisponible" else "edgar"¦        return "edgar"  # mutation: ignore carte_statut indisponible¦l'"'"'inventaire n'"'"'a pas le concept'
# §7 ─ le câblage carte : court-circuiter la branche `carte_statut is not None` avec `if False:`
# → repli sur poste_retenu() même avec une carte `exact` → le check rougit (pas de poste passé)
'app/agents/v2/collecte_executor.py¦    if carte_statut is not None:¦    if False:  # mutation: désactive la branche carte_statut¦court-circuite poste_retenu'
# §8 ─ le câblage dans COLLECTER_UN : retirer carte_statut du router_source → le chemin de production
# ignore la carte. Une ligne `indisponible` part à EDGAR au lieu du web — §8 rougit.
"$SRC¦    route = router_source(ligne, carte_statut=carte_statut)¦    route = router_source(ligne)  # mutation: carte_statut non passé à router_source¦carte \`indisponible\` : la même ligne prend le chemin WEB"
# §9 ─ LA RÉGRESSION QU'ON VIENT DE CORRIGER, REFABRIQUÉE À L'IDENTIQUE : l'exécuteur repuise la
# date de revérification dans la table de la carte et la repasse à `lire_carte`. La comparaison
# devient `X < X`, donc toujours fausse — le code REDEVIENT vert fonctionnellement, aucun test de
# routage ne bouge, et c'est exactement pour ça que la garde doit être STRUCTURELLE. Deux mutations,
# parce que les deux moitiés se réintroduisent séparément : la sentinelle remplacée par une date lue,
# et le `SELECT` qui la fournit.
"$SRC¦            depot_courant=_SANS_REVERIFICATION,¦            depot_courant=\"2026-06-30\",  # mutation: une date plausible au lieu de l'aveu¦sentinelle \`_SANS_REVERIFICATION\` est encore employée"
"$SRC¦        carte = await lire_carte(¦        await conn.fetchrow(\"SELECT dernier_depot_vu FROM appariement_cartes WHERE ticker_id = \$1\", plan.ticker_id)\n        carte = await lire_carte(¦n'émet AUCUN \`SELECT\` sur \`appariement_cartes\`"
# §9 ─ la sentinelle dégradée en date plausible : elle cesse d'avouer, et `<` peut redevenir vraie.
"$SRC¦_SANS_REVERIFICATION = \"0000-00-00 (aucune date de dépôt courante : âge non revérifié ici)\"¦_SANS_REVERIFICATION = \"1970-01-01\"¦plus petite que toute date ISO"

# ── MUTATIONS DU 2026-09-18 — le producteur, et la garde d'âge devenue ATTEIGNABLE ────────────────
# §9 ─ LA MÊME RÉGRESSION, UN CRAN PLUS HAUT, ET C'EST LA PLUS INSTRUCTIVE DU FICHIER : la date
# opposée à la carte n'est plus MESURÉE sur l'inventaire, c'est une constante — et on choisit
# exprès la constante ÉGALE à la vraie date du 2026-09-18. Tous les asserts de comportement (§10)
# RESTENT VERTS : le routage est identique, la carte fraîche est reconnue fraîche, la périmée est
# reconstruite. Seul l'assert STRUCTUREL rougit. C'est la démonstration, dans le test négatif
# lui-même, qu'une garde de comportement ne peut pas tenir cet interdit-là (#70).
"$SRC¦        depot_courant = dernier_depot_vu(facts)¦        depot_courant = \"2026-06-30\"  # mutation: une date posée, jamais mesurée¦est PRODUIT par"
# §9 ─ le chemin nominal renonce à revérifier : il repasse la sentinelle, donc la branche « périmée »
# redevient inatteignable. C'est l'état exact d'avant ce lot, et il ne doit plus pouvoir revenir.
"$SRC¦            depot_courant=depot_courant,¦            depot_courant=_SANS_REVERIFICATION,  # mutation: le nominal cesse de revérifier¦oppose une AUTRE référence que la sentinelle"
# §9 ─ le PRODUCTEUR retiré : `apparier` n'est plus appelé. Sans cet assert, tout le reste de la
# garde d'âge resterait vert sur une table vide — l'état mesuré en base le 2026-09-18.
"$SRC¦        res = await apparier(plan, facts)¦        raise AppariementRefuse(\"mutation: producteur retiré\")¦sont appelés dans le code de production"
# §10 ─ la carte est reconstruite à CHAQUE exécution : fonctionnellement correct, et il paie une
# carte par run. Un coût qui ne rougit nulle part est un coût qu'on ne voit jamais.
"$SRC¦    if carte is not None:¦    if False:  # mutation: la carte fraîche n'est jamais reconnue¦carte à jour → état"
# §10 ─ la reconstruction ne PERSISTE pas : la carte est refaite, payée, puis jetée. Le run suivant
# la refait. Seul un assert sur l'appel à `persister_carte` le voit.
"$SRC¦    row_id = await persister_carte(conn, res.carte)¦    row_id = 0  # mutation: la carte reconstruite n'est pas persistée¦appelés une fois"
# §10 ─ LA CONFUSION QUE #70 A PRODUITE UNE FOIS : une carte servie sans pouvoir la dater se déclare
# `fraiche`. Rien ne change au routage ; c'est le RÉCIT qui devient faux, et l'aval ne peut plus
# distinguer « vérifié à jour » de « pas vérifiable ».
"$SRC¦    return CarteCourante(_statuts(carte), \"non_reverifiable\", None,¦    return CarteCourante(_statuts(carte), \"fraiche\", None,  # mutation: l'aveu effacé¦inventaire injoignable"
# §10 ─ le repli nommé cesse de se distinguer : `statuts` vide au lieu de None. L'aval retombe bien
# sur `poste_retenu()`, mais « carte sans aucune ligne » et « aucune carte » se confondent.
"$SRC¦            plan.ticker_id, plan.framework_id, plan.framework_version, motif)\n        return CarteCourante(None, \"aucune\", None)¦            plan.ticker_id, plan.framework_id, plan.framework_version, motif)\n        return CarteCourante({}, \"aucune\", None)  # mutation: repli indistinct¦ni inventaire ni carte"
# §10 ─ un refus définitif du modèle se maquille en reconstruction réussie : on servirait une carte
# vide en la présentant comme neuve.
"$SRC¦        return await _servir_le_stock(conn, plan, motif=f\"appariement REFUSÉ après réparation : {e}\",\n                                      inventaire=inventaire)¦        return CarteCourante(None, \"reconstruite\", depot_courant)  # mutation: le refus maquillé¦appariement REFUSÉ après réparation"
# §10 ─ LE CÂBLAGE : `assurer_carte` est parfaite et personne ne l'appelle. C'est littéralement
# l'état dans lequel `apparier()`/`persister_carte()` ont vécu tout le maillon 4bis.
"$SRC¦        carte = await assurer_carte(plan, conn=conn)¦        carte = CarteCourante(None, \"aucune\", None)  # mutation: le producteur débranché¦OBTIENT la carte quand l'appelant n'en fournit pas"

# ── MUTATIONS DU MAILLON 4 — LE SYMBOLE OPPOSÉ À EDGAR ────────────────────────────────────────────
# §9 ─ LE BUG RÉEL QUI DORMAIT ICI, REFABRIQUÉ : le symbole EST l'identifiant interne. Sur RVMD,
# NVDA ou MSFT les deux coïncident, donc TOUT reste vert — y compris §10 si on l'avait écrit avec un
# `ticker_id` égal au symbole. C'est la raison pour laquelle la fixture §10 utilise `PUB-4F2A9C10` :
# une fixture plus favorable que la prod aurait rendu les deux gardes aveugles d'un coup.
"$SRC¦        symbole = await symbole_de_marche(conn, plan.ticker_id)¦        symbole = plan.ticker_id  # mutation: l'id interne tient lieu de symbole¦est PRODUIT par \`symbole_de_marche(...)\`"
# §9 ─ la même chose sans passer par une variable : l'id part directement à EDGAR, et la provenance
# du symbole cesse d'être lisible à l'AST.
"$SRC¦        cik = await resolve_cik(symbole)¦        cik = await resolve_cik(plan.ticker_id)  # mutation: l'id interne part chez EDGAR¦passe son argument par un NOM"
# §10 ─ l'inventaire remonte l'ID au lieu du SYMBOLE : le CIK est juste, mais la provenance écrite
# par l'exécution d'un appariement nommerait un identifiant qui n'existe pas chez la SEC.
"$SRC¦    inventaire = InventaireTicker(symbole=symbole, cik=cik, facts=facts)¦    inventaire = InventaireTicker(symbole=plan.ticker_id, cik=cik, facts=facts)  # mutation: provenance interne¦l'inventaire remonté porte le symbole"
# §10 ─ l'absence de symbole cesse d'être un repli NOMMÉ : la carte stockée n'est plus servie, tout
# devient « aucune ». Une société sans symbole n'est pas une panne, et perdre sa carte le dit mal.
"$SRC¦        return await _servir_le_stock(conn, plan, motif=f\"inventaire EDGAR injoignable : {e}\")¦        return CarteCourante(None, \"aucune\", None)  # mutation: le repli perd son nom¦société sans symbole de marché"

# ── MUTATIONS DU MAILLON 4 — L'EXÉCUTION DE L'APPARIEMENT ─────────────────────────────────────────
# §11 ─ L'ÉTAT D'AVANT CE LOT, REFABRIQUÉ : la carte route vers EDGAR, et l'exécuteur n'exécute que
# les recettes du catalogue. Tout reste vert côté routage — c'est précisément le piège de #71 : le
# gain de ROUTAGE existait déjà, la collecte non. Les 10 approximations de RVMD repartent au web.
"$SRC¦        if consigne is not None and inventaire is not None:¦        if False:  # mutation: la consigne n'est jamais exécutée¦est appelé UNE fois et son entry est rendue"
# §11 ─ l'ordre inversé : la consigne passe devant la recette du catalogue. Fonctionnellement ça
# « marche » — et ça écrit deux producteurs actifs pour un même fait (#43), en perdant le choix par
# fraîcheur entre concepts candidats (#30).
"$SRC¦        poste = poste_retenu(ligne.poste, ligne.metrique)¦        poste = None  # mutation: la recette ne passe plus devant¦passe devant la consigne"
# §11 ─ le refus perd son motif : l'echec ne nomme plus ni la cause ni l'expression. La ligne devient
# un mandat illisible, et l'analyste lira « le dépôt ne porte pas ce nombre » là où l'ancre manquait.
"$SRC¦                    echec=f\"appariement « {consigne.expression} » inexécutable sur le dépôt : {e}\",¦                    echec=\"collecte impossible\",  # mutation: le refus perd son motif¦NOMME la cause et l'expression"
# §11 ─ LA FUITE DU COUPLE DANS LA VALEUR : l'ingrédient voyage avec la consigne. Le collecteur cesse
# d'être aveugle par CONSTRUCTION (#58) et peut réancrer l'entry sur la question.
"$SRC¦            expression = str(it.concepts[0])      # le contrat garantit qu'il y en a exactement un¦            expression = f\"{it.ingredient_id}: {it.concepts[0]}\"  # mutation: le couple fuit¦aucune VALEUR de consigne ne contient un fragment"
# §11 ─ un `indisponible` produit une consigne : on tenterait d'exécuter un MOTIF comme une formule,
# et le web — seul chemin légitime pour ces lignes — ne serait plus emprunté.
"$SRC¦        else:\n            continue¦        else:\n            expression = str(it.motif)  # mutation: l'indisponible devient exécutable¦ne produit AUCUNE consigne"
# §11 ─ LE CÂBLAGE AMONT DÉBRANCHÉ : `collecter_un` ne reçoit plus la consigne. §11 reste vert en
# appelant la fonction directement — seul l'assert structurel voit que personne ne la lui passe.
"$SRC¦            consigne=consigne, inventaire=carte.inventaire, emetteur=emetteur)¦            emetteur=emetteur)  # mutation: la consigne n'atteint jamais le collecteur¦en lui passant \`consigne\` ET \`inventaire\`"

# ── MUTATION DU 2026-09-19 — LE CHIEN DE GARDE PAR LIGNE WEB (#25) ─────────────────────────────────
# §6bis ─ le garde retiré : une ligne web qui SE BLOQUE fige toute la collecte (mesuré >18 min sur
# RVMD). Aucun assert de COMPORTEMENT ne bouge — sans borne, `collecter_un` ne rend jamais, donc il
# n'y a rien à tester ; c'est le wait_for du CHECK lui-même qui LÈVE et rougit §6bis. La preuve, dans
# le test négatif, qu'un blocage n'est pas une exception et n'est attrapable que par une borne.
"$SRC¦        exchange = await asyncio.wait_for(\n            run_search_worker(req), timeout=settings.WEB_LINE_BUDGET_S)¦        exchange = await run_search_worker(req)  # mutation: garde par ligne retiré¦est BORNÉ par le garde de prod"
# Lot 6 maillon 2 — la CAUSE déclarée par l'exécuteur (arbitrage du comité n°3). Une mutation par cause.
"$SRC¦cause=\"source_indisponible\")  # cause: temps épuisé¦cause=\"recherche_epuisee\")¦temps épuisé = \`source_indisponible\`"
"$SRC¦cause=\"source_indisponible\")  # cause: worker en erreur¦cause=\"recherche_epuisee\")¦collecte web qui LÈVE = \`source_indisponible\`"
"$SRC¦cause=\"recherche_epuisee\")  # cause: not_found¦cause=\"source_indisponible\")¦\`not_found\` → echec de cause"
"$SRC¦cause=\"recherche_epuisee\")  # cause: appariement inexécutable¦cause=\"source_indisponible\")¦appariement inexécutable = \`recherche_epuisee\`"
# ── l'identité de l'émetteur dans la requête web (lot 7, 2026-09-26 — RVMD cherché chez Ryvu) ─────
"$SRC¦            f\"Pour l'entreprise {emetteur.raison_sociale} (symbole {emetteur.symbole}, CIK SEC \"¦            f\"Pour l'entreprise {emetteur.symbole} (symbole {emetteur.symbole}, SEC \"¦NOMME l'entreprise (raison sociale + CIK SEC)"
"$SRC¦    if emetteur is None:\n        return ResultatCollecte(¦    if False:\n        return ResultatCollecte(¦identité NON RÉSOLUE → echec nommé"
)

passes=0; ratees=0
for m in "${mutations[@]}"; do
  IFS='¦' read -r fichier vieux neuf attendu <<< "$m"
  tmp=$(mktemp -d)
  cp -r . "$tmp/backend" 2>/dev/null
  rm -rf "$tmp/backend/.git" 2>/dev/null
  find "$tmp/backend" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null

  if ! python3 -c "
import sys, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_text(encoding='utf-8')
vieux = sys.argv[2].replace('\\\\n', chr(10))
neuf  = sys.argv[3].replace('\\\\n', chr(10))
if vieux not in s:
    print('MOTIF INTROUVABLE'); sys.exit(1)
p.write_text(s.replace(vieux, neuf, 1), encoding='utf-8')
" "$tmp/backend/$fichier" "$vieux" "$neuf"; then
    printf '  ?? %-58.58s MUTATION CADUQUE (motif absent du source)\n' "$attendu"
    ratees=$((ratees + 1)); rm -rf "$tmp"; continue
  fi

  out=$(run_check "$tmp/backend"); rc=$?
  rm -rf "$tmp"
  bilan=$(printf '%s' "$out" | grep -E 'vérifications OK')
  rouge=$(printf '%s' "$out" | grep -F 'FAIL' | grep -F "$attendu")

  if [ -z "$bilan" ]; then
    printf '  FAIL %-56.56s script MORT avant son bilan\n' "$attendu"
    printf '%s\n' "$out" | tail -4; ratees=$((ratees + 1))
  elif [ "$rc" -eq 0 ]; then
    printf '  FAIL %-56.56s le check reste VERT — ce critère ne garde rien\n' "$attendu"; ratees=$((ratees + 1))
  elif [ -z "$rouge" ]; then
    printf '  FAIL %-56.56s rouge, mais PAS sur l'\''assert visé\n' "$attendu"
    printf '%s\n' "$out" | grep -F 'FAIL' | head -3 | sed 's/^/         /'; ratees=$((ratees + 1))
  else
    printf '  ok   %-56.56s rouge sur son assert · %s\n' "$attendu" "$bilan"; passes=$((passes + 1))
  fi
done

echo; echo "============================================================"
echo "$passes mutations correctement détectées, $ratees échec(s)"
[ "$ratees" -eq 0 ] || exit 1
