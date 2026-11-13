#!/usr/bin/env bash
# TEST NÉGATIF de `check_charte_modules.py` — au moins une mutation STRUCTURELLE par invariant
# [C0]…[C7], plus les cas qui DOIVENT rester verts (reprise déclarée, sous-dossier adaptateurs/,
# jeton cité dans la prose) : une garde qui rougit sur ce qu'elle autorise ne vaut pas mieux qu'une
# garde qui ne rougit pas.
#
# Trois exigences par mutation rouge : (1) exit ≠ 0 ; (2) l'assert ATTENDU, nommé, porte le FAIL ;
# (3) le script atteint son bilan. Les mutations ne dépendent d'aucun fichier d'un vrai module :
# chacune CRÉE ce qu'elle casse (module fictif `bidon`, ligne de registre ajoutée en fin de fichier,
# fichier neuf dans l'ancien code).
#
# Exécution : avec l'image du conteneur `portfolio-backend` s'il existe (mêmes montages que les
# autres negatif_*.sh), SINON avec le python3 de l'hôte, en l'annonçant — le contrôle est en
# bibliothèque standard pure, les deux exécutions sont équivalentes.
#
#   bash checks/negatif_charte_modules.sh
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_charte_modules.py"

if IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}' 2>/dev/null) && [ -n "$IMG" ]; then
  echo "exécution en conteneur : image $IMG"
else
  IMG=""
  echo "exécution sur l'hôte : pas de conteneur portfolio-backend ($(python3 --version 2>&1))"
fi

lancer_check() {  # $1 = racine tmp (contient backend/)
  if [ -n "$IMG" ]; then
    docker run --rm --network none -v "$1/backend:/app:ro" -v "$PWD/../roadmap:/roadmap:ro" \
      -w /app -e PYTHONPATH=/app --env-file checks/env.checks "$IMG" python "$CHECK" 2>&1
  else
    (cd "$1/backend" && PYTHONDONTWRITEBYTECODE=1 python3 "$CHECK" 2>&1)
  fi
}

copie() {  # bac à sable : seulement ce que le contrôle lit, sans aucun bytecode
  local t; t=$(mktemp -d)
  mkdir -p "$t/backend"
  cp -r app checks "$t/backend/" 2>/dev/null
  [ -d tools ] && cp -r tools "$t/backend/" 2>/dev/null
  find "$t/backend" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
  echo "$t"
}

# ── Briques de mutation ──────────────────────────────────────────────────────────────────────
declarer() {  # $1 = racine tmp, $2 = arguments de Module(...) — ajoute UNE entrée en fin de registre
  printf '\nMODULES = MODULES + (Module(%s),)\n' "$2" >> "$1/backend/app/modules/registre.py"
}
dossier_bidon() {  # $1 = racine tmp, $2 = nom — un module complet et conforme
  local d="$1/backend/app/modules/$2"
  mkdir -p "$d"
  echo '"""Module fictif du test négatif."""' > "$d/__init__.py"
  printf 'VERSION_CONTRAT = "1.0.0"\n\n\ndef lire():\n    return None\n' > "$d/contrat.py"
  printf 'def interne():\n    return 1\n' > "$d/travail.py"
}
bidon() {  # module fictif complet ET déclaré ; $2 = arguments supplémentaires de Module(...)
  dossier_bidon "$1" bidon
  declarer "$1" "nom=\"bidon\", rend=\"Un objet fictif.\", prefixe_tables=\"bidon_\"${2:+, $2}"
}

apply_mutation() {  # $1 = id, $2 = racine tmp
  local id="$1" t="$2" m="$2/backend/app/modules" a="$2/backend/app"
  case "$id" in
    temoin_bidon)        bidon "$t" ;;
    c0_sans_registre)    rm -f "$m/registre.py" ;;
    c0_registre_casse)   echo 'MODULES = (' >> "$m/registre.py" ;;
    c0_module_sans_python) mkdir -p "$m/bidon"; echo "# rien" > "$m/bidon/LISEZMOI.md"
                         declarer "$t" 'nom="bidon", rend="Un objet fictif."' ;;
    c1_non_declare)      dossier_bidon "$t" bidon ;;
    c1_sans_dossier)     declarer "$t" 'nom="fantome", rend="Un objet fictif."' ;;
    c1_lit_inconnu)      bidon "$t" 'lit=("inexistant",)' ;;
    c2_sans_contrat)     bidon "$t"; rm -f "$m/bidon/contrat.py" ;;
    c2_sans_version)     bidon "$t"; printf 'def lire():\n    return None\n' > "$m/bidon/contrat.py" ;;
    c2_version_non_chaine) bidon "$t"; printf 'VERSION_CONTRAT = 1\n' > "$m/bidon/contrat.py" ;;
    c3_interne)          bidon "$t"; dossier_bidon "$t" voisin
                         declarer "$t" 'nom="voisin", rend="Un objet fictif.", lit=("bidon",)'
                         echo 'from app.modules.bidon.travail import interne' > "$m/voisin/lecteur.py" ;;
    c3_interne_relatif)  bidon "$t"; dossier_bidon "$t" voisin
                         declarer "$t" 'nom="voisin", rend="Un objet fictif.", lit=("bidon",)'
                         echo 'from ..bidon import travail' > "$m/voisin/lecteur.py" ;;
    c3_paquet_entier)    bidon "$t"; dossier_bidon "$t" voisin
                         declarer "$t" 'nom="voisin", rend="Un objet fictif.", lit=("bidon",)'
                         echo 'import app.modules.bidon' > "$m/voisin/lecteur.py" ;;
    c3_non_declare)      bidon "$t"; dossier_bidon "$t" voisin
                         declarer "$t" 'nom="voisin", rend="Un objet fictif."'
                         echo 'from app.modules.bidon.contrat import lire' > "$m/voisin/lecteur.py" ;;
    vert_contrat_declare) bidon "$t"; dossier_bidon "$t" voisin
                         declarer "$t" 'nom="voisin", rend="Un objet fictif.", lit=("bidon",)'
                         printf 'from app.modules.bidon.contrat import lire\nfrom ..bidon import contrat\nfrom app.modules import registre\nfrom . import travail\n' > "$m/voisin/lecteur.py" ;;
    c4_ancien_code)      bidon "$t"; echo 'from app.knowledge import perimetre' > "$m/bidon/emprunt.py" ;;
    c4_reprise_voisine)  bidon "$t" 'reprises=("app.knowledge.perimetre",)'
                         echo 'from app.knowledge import autre_chose' > "$m/bidon/emprunt.py" ;;
    vert_reprise_declaree) bidon "$t" 'reprises=("app.knowledge.perimetre",)'
                         printf 'from app.knowledge import perimetre\nfrom app.knowledge.perimetre import vue_servie\n' > "$m/bidon/emprunt.py" ;;
    c4_registre_importe) printf '\ndef _paresseux():\n    from app import config\n    return config\n' >> "$m/registre.py" ;;
    c5_ancien_lit_interne) bidon "$t"; echo 'from app.modules.bidon.travail import interne' > "$a/zz_mutation_charte.py" ;;
    c5_ancien_lit_paquet) bidon "$t"; echo 'from app.modules import bidon' > "$a/zz_mutation_charte.py" ;;
    vert_ancien_lit_contrat) bidon "$t"; printf 'from app.modules.bidon.contrat import lire\nfrom app.modules.registre import MODULES\n' > "$a/zz_mutation_charte.py" ;;
    c6_sql_ancien)       echo 'REQUETE = "SELECT * FROM chef_etats WHERE id = $1"' > "$a/zz_mutation_charte.py" ;;
    c6_fstring_ancien)   printf 'def f(x):\n    return f"UPDATE chef_pas SET n = {x}"\n' > "$a/zz_mutation_charte.py" ;;
    c6_sql_tools)        mkdir -p "$t/backend/tools"; echo 'R = "DELETE FROM chef_etats"' > "$t/backend/tools/zz_mutation_charte.py" ;;
    c6_autre_module)     bidon "$t"; echo 'R = "SELECT 1 FROM chef_etats"' > "$m/bidon/requete.py" ;;
    c6_collision)        bidon "$t"; dossier_bidon "$t" voisin
                         declarer "$t" 'nom="voisin", rend="Un objet fictif.", prefixe_tables="bidon_archives_"' ;;
    vert_tables_chez_soi) bidon "$t"; printf '"""Parle de chef_etats en prose."""\nR = "SELECT * FROM bidon_etats"  # et non chef_etats\nN = "chef_de_dossier"\n' > "$m/bidon/requete.py" ;;
    c7_formulaire)       bidon "$t"; echo 'FORMULAIRE = "10-K"' > "$m/bidon/source.py" ;;
    c7_identifiant)      bidon "$t"; printf 'def f(cik_emetteur):\n    return cik_emetteur\n' > "$m/bidon/source.py" ;;
    c7_symbole)          bidon "$t"; echo 'ESSAI = ["NVDA"]' > "$m/bidon/source.py" ;;
    c7_symbole_adaptateur) bidon "$t"; mkdir -p "$m/bidon/adaptateurs"
                         echo 'ESSAI = "RVMD"' > "$m/bidon/adaptateurs/depots.py" ;;
    vert_adaptateur)     bidon "$t"; mkdir -p "$m/bidon/adaptateurs"
                         printf 'FORMULAIRES = ("10-K", "10-Q", "DEF 14A")\nBASE = "EDGAR"\n' > "$m/bidon/adaptateurs/depots.py" ;;
    vert_prose)          bidon "$t"; printf '"""Ce module ignore tout du 10-K et de NVDA."""\n# EDGAR est cité ici, en commentaire seulement\nX = 1\n' > "$m/bidon/source.py" ;;
    *) return 1 ;;
  esac
}

# mutation ¦ assert qui DOIT rougir — ou « VERT » : la mutation est permise, le contrôle doit le rester
mutations=(
"temoin_bidon¦VERT"
"c0_sans_registre¦[C0] registre présent"
"c0_registre_casse¦[C0] registre chargeable"
"c0_module_sans_python¦[C0] bidon : au moins un fichier Python lu"
"c1_non_declare¦[C1] dossier sur disque mais non déclaré au registre : app/modules/bidon"
"c1_sans_dossier¦[C1] module déclaré au registre mais absent du disque : fantome"
"c1_lit_inconnu¦[C1] registre incohérent : bidon : lit un module non déclaré (inexistant)"
"c2_sans_contrat¦[C2] bidon : contrat.py présent"
"c2_sans_version¦[C2] bidon : contrat.py expose VERSION_CONTRAT"
"c2_version_non_chaine¦[C2] bidon : contrat.py expose VERSION_CONTRAT"
"c3_interne¦[C3] accès interdit — app/modules/voisin/lecteur.py:1 : \`from app.modules.bidon.travail import interne\`"
"c3_interne_relatif¦[C3] accès interdit — app/modules/voisin/lecteur.py:1 : \`from app.modules.bidon import travail\`"
"c3_paquet_entier¦[C3] accès interdit — app/modules/voisin/lecteur.py:1 : \`import app.modules.bidon\`"
"c3_non_declare¦[C3] lecture non déclarée — app/modules/voisin/lecteur.py:1"
"vert_contrat_declare¦VERT"
"c4_ancien_code¦[C4] ancien code importé — app/modules/bidon/emprunt.py:1 : \`from app.knowledge import perimetre\`"
"c4_reprise_voisine¦[C4] ancien code importé — app/modules/bidon/emprunt.py:1 : \`from app.knowledge import autre_chose\`"
"vert_reprise_declaree¦VERT"
"c4_registre_importe¦[C4] le registre reste autonome — app/modules/registre.py"
"c5_ancien_lit_interne¦[C5] l'ancien code lit l'intérieur d'un module — app/zz_mutation_charte.py:1"
"c5_ancien_lit_paquet¦[C5] l'ancien code lit l'intérieur d'un module — app/zz_mutation_charte.py:1"
"vert_ancien_lit_contrat¦VERT"
"c6_sql_ancien¦[C6] table d'un autre — app/zz_mutation_charte.py:1 nomme \`chef_etats\`"
"c6_fstring_ancien¦[C6] table d'un autre — app/zz_mutation_charte.py:2 nomme \`chef_pas\`"
"c6_sql_tools¦[C6] table d'un autre — tools/zz_mutation_charte.py:1 nomme \`chef_etats\`"
"c6_autre_module¦[C6] table d'un autre — app/modules/bidon/requete.py:1 nomme \`chef_etats\`"
"c6_collision¦[C6] préfixes de tables en collision : bidon (bidon_) et voisin (bidon_archives_)"
"vert_tables_chez_soi¦VERT"
"c7_formulaire¦[C7] jeton de juridiction \`10-K\` dans app/modules/bidon/source.py"
"c7_identifiant¦[C7] jeton de juridiction \`cik\` dans app/modules/bidon/source.py"
"c7_symbole¦[C7] symbole de société \`NVDA\` dans app/modules/bidon/source.py"
"c7_symbole_adaptateur¦[C7] symbole de société \`RVMD\` dans app/modules/bidon/adaptateurs/depots.py"
"vert_adaptateur¦VERT"
"vert_prose¦VERT"
)

# ── Base : sans mutation, le contrôle doit être VERT — sinon aucune mutation ne prouve rien ────
tmp=$(copie); out=$(lancer_check "$tmp"); rc=$?; rm -rf "$tmp"
if [ "$rc" -ne 0 ] || ! printf '%s' "$out" | grep -qE 'vérifications OK, 0 échec'; then
  echo "  FAIL base : le contrôle n'est pas vert AVANT mutation — test négatif sans objet"
  printf '%s\n' "$out" | tail -8 | sed 's/^/         /'
  echo
  echo "============================================================"
  echo "0 mutations correctement détectées, 1 échec(s)"
  exit 1
fi
echo "  base : $(printf '%s' "$out" | grep -E 'vérifications OK' | tail -1)"

passes=0; verts=0; ratees=0
for mut in "${mutations[@]}"; do
  id="${mut%%¦*}"; attendu="${mut#*¦}"  # découpe par motif : indépendante de la locale de l'hôte
  tmp=$(copie)
  if ! apply_mutation "$id" "$tmp"; then
    printf '  ?? %-58.58s MUTATION INCONNUE\n' "$id"; ratees=$((ratees+1)); rm -rf "$tmp"; continue
  fi
  out=$(lancer_check "$tmp"); rc=$?
  rm -rf "$tmp"

  bilan=$(printf '%s' "$out" | grep -E 'vérifications OK' | tail -1)

  if [ "$attendu" = "VERT" ]; then
    if [ -z "$bilan" ]; then
      printf '  FAIL %-56.56s script MORT avant son bilan\n' "$id"; printf '%s\n' "$out" | tail -4; ratees=$((ratees+1))
    elif [ "$rc" -ne 0 ]; then
      printf '  FAIL %-56.56s FAUX ROUGE sur un cas permis\n' "$id"
      printf '%s\n' "$out" | grep -F 'FAIL' | head -3 | sed 's/^/         /'; ratees=$((ratees+1))
    else
      printf '  ok   %-56.56s reste vert (cas permis) · %s\n' "$id" "$bilan"; verts=$((verts+1))
    fi
    continue
  fi

  rouge=$(printf '%s' "$out" | grep -F 'FAIL' | grep -F -- "$attendu")
  if [ -z "$bilan" ]; then
    printf '  FAIL %-56.56s script MORT avant son bilan\n' "$attendu"; printf '%s\n' "$out" | tail -4; ratees=$((ratees+1))
  elif [ "$rc" -eq 0 ]; then
    printf '  FAIL %-56.56s le check reste VERT — ce critère ne garde rien\n' "$attendu"; ratees=$((ratees+1))
  elif [ -z "$rouge" ]; then
    printf '  FAIL %-56.56s rouge, mais PAS sur l'\''assert visé\n' "$attendu"
    printf '%s\n' "$out" | grep -F 'FAIL' | head -3 | sed 's/^/         /'; ratees=$((ratees+1))
  else
    printf '  ok   %-56.56s rouge sur son assert · %s\n' "$attendu" "$bilan"; passes=$((passes+1))
  fi
done

echo
echo "============================================================"
echo "$passes mutations correctement détectées, $ratees échec(s) · $verts cas permis restés verts"
[ "$ratees" -eq 0 ] || exit 1
