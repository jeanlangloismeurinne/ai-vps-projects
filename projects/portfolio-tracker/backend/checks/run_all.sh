#!/usr/bin/env bash
# Suite hors-ligne complète — une ligne par script, plus un total d'assertions.
#
# POURQUOI CE FICHIER EST VERSIONNÉ. Il vivait dans `/tmp`, donc il était réécrit à chaque session
# et ses défauts revenaient avec lui. Le dernier en date coûtait 47 assertions : le bilan était lu
# par `tail -1` sur stdout ET stderr fusionnés, or `check_runner_telemetry` émet une ligne de LOG
# après sa ligne de bilan — le filtre lisait donc « … après 2 essais — 850/170 tokens » et comptait
# **2** au lieu de **49**. Le total restait plausible (1 464 au lieu de 1 511), c'est-à-dire
# invisible. Le bilan est désormais reconnu par sa FORME, jamais par sa position.
#
#   bash checks/run_all.sh
#
# ⚠️ Les deux montages ne sont pas optionnels :
#   · `/contract_frozen` (= `roadmap/provenance-cards`) — sans lui, 4 scripts sous-comptent en
#     sortant quand même à 0 (cf. checks/README.md) ;
#   · `/roadmap` — `check_frameworks_definitions` §7 y confronte le référentiel aux tables §4.1.1 /
#     §4.2.1 de la spec. La spec est PARSÉE, jamais recopiée dans le check : sans le montage, la
#     section sort en ÉCHEC plutôt que de se sauter.
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
total=0
worst=0
for f in checks/check_*.py; do
  n=$(basename "$f" .py)
  # Les deux checks « live » sortent du périmètre hors-ligne : ils appellent le réseau ouvert.
  case "$n" in check_fetch_live|check_fetch_relevance) continue ;; esac

  # Trois checks lisent l'ÉTAT persisté, pas seulement la règle : `check_entry_nature` §7
  # (acceptation de la capacité 1), `check_edgar_feed` §12bis (F16 — un fait porte lui-même sa
  # nature de poste) et `check_collecte_persist` (lot 2c — le plan/les liens/les mandats s'écrivent
  # vraiment, dans une transaction ROLLBACK, sans résidu). Ils exigent le réseau `coolify` + la
  # vraie URL de base. Sans elles ils SORTENT EN ÉCHEC au lieu de sauter la section — une mesure
  # incomplète ne doit jamais passer pour un 0 (`feedback_check_degrade_en_sortant_a_zero`).
  net=none; extra=()
  case "$n" in
    check_entry_nature|check_edgar_feed|check_collecte_persist)
      net=coolify
      extra=(-e "CHECK_DB_URL=$(grep -m1 '^DATABASE_URL=' .env | cut -d= -f2-)")
      ;;
  esac

  out=$(docker run --rm --network "$net" -v "$PWD:/app:ro" \
        -v "$PWD/../roadmap/provenance-cards:/contract_frozen:ro" \
        -v "$PWD/../roadmap:/roadmap:ro" \
        -w /app -e PYTHONPATH=/app --env-file checks/env.checks "${extra[@]}" "$IMG" python "$f" 2>&1)
  rc=$?

  # Le bilan se reconnaît à sa forme (trois dialectes historiques), pas à sa place dans la sortie.
  bilan=$(printf '%s' "$out" | grep -E 'vérifications OK|[0-9]+ ok / [0-9]+ FAIL|[0-9]+ OK / [0-9]+ KO' | tail -1)
  if [ -z "$bilan" ]; then
    printf '%-34s exit=%d  *** AUCUNE LIGNE DE BILAN — script mort avant ses asserts ? ***\n' "$n" "$rc"
    worst=1
    printf '%s\n' "$out" | tail -5
    continue
  fi
  nb=$(printf '%s' "$bilan" | grep -oE '[0-9]+' | head -1)
  total=$((total + nb))
  printf '%-34s exit=%d  %s\n' "$n" "$rc" "$bilan"
  if [ "$rc" -ne 0 ]; then
    worst=1
    printf '%s\n' "$out" | grep -E 'FAIL|KO|Traceback|Error' | head -10
  fi
done
echo "TOTAL assertions = $total"
exit $worst
