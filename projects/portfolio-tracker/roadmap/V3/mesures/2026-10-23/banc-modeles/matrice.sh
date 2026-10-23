#!/usr/bin/env bash
# usage : RUN=n matrice.sh [MODELES...]
cd /root/ai-vps-projects/projects/portfolio-tracker/backend
export S=/tmp/claude-0/-root/01282319-7163-42ce-9edb-8ac74c729411/scratchpad
export IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
export RUN=${RUN:-1}
MODELES=${@:-deepseek-ai/DeepSeek-V4-Flash-0731 deepseek-ai/DeepSeek-V4-Pro-0813 moonshotai/Kimi-K3 Qwen/Qwen3.8-Max zai-org/GLM-5.3 anthropic/claude-sonnet-5}
un() {
  M=$1; T=$2; AN=$3
  tag=$(echo "$M" | sed 's|.*/||')_${T}_anon${AN}_r${RUN}
  [ -f "$S/banc/$tag.json" ] && exit 0
  timeout 900 docker run --rm --network coolify -v "$PWD:/app:ro" -v "$S:/s" -w /app -e PYTHONPATH=/app -e ANON=$AN \
    --env-file checks/env.checks --env-file .env "$IMG" python /s/banc_modeles.py $T $M /s/banc/$tag.json > $S/banc/$tag.log 2>&1
  grep BILAN $S/banc/$tag.log || echo "ECHEC $tag"
}
export -f un
for M in $MODELES; do for T in NVDA RVMD; do for AN in 0 1; do echo "$M $T $AN"; done; done; done | xargs -P 3 -L 1 bash -c 'un $0 $1 $2'
echo FIN
