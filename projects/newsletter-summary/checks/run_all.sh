#!/usr/bin/env bash
# Suite complète (chaque check sur base jetable) + bilan. Le lanceur vit ici, versionné.
#   checks/run_all.sh          → BILAN checks : N/N verts   (exit ≠ 0 si un check rougit)
# Ne cherche PAS le dernier mot d'un tail : le bilan se reconnaît à sa forme (grep -E).
cd "$(dirname "$0")/.."
pass=0; total=0
for f in checks/check_golden_newsletter.py checks/check_alias_routing.py checks/check_prompt_scope.py \
         checks/check_migration.py checks/check_engine.py checks/check_urlfetch.py checks/check_kb_alias.py \
         checks/check_webhook_event_filter.py; do
  total=$((total+1))
  out=$(checks/run.sh "$f" 2>&1); code=$?
  if [ $code -eq 0 ] && echo "$out" | grep -qE '^OK'; then pass=$((pass+1)); echo "VERT   $f"; else echo "ROUGE  $f"; echo "$out" | grep -E 'Error|assert' | head -3; fi
done
echo "BILAN checks : $pass/$total verts"
[ $pass -eq $total ]
