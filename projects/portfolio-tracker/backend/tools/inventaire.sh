#!/usr/bin/env bash
# Lanceur du maillon 1 du découpage — l'INVENTAIRE (`tools/inventaire.py`), plan B4g, 2026-10-24.
#
#   bash tools/inventaire.sh NVDA --pieces-seules            # GRATUIT : le dossier tel que le modèle le lira
#   bash tools/inventaire.sh NVDA --lectures 3 --sortie F    # 3 lectures INDÉPENDANTES (mesure de stabilité)
#
# ⚠️ Appelle DeepSeek-V4.1-Flash (DeepInfra) sauf `--pieces-seules`, et LIT la base — réseau `coolify` +
# le vrai `.env`. Ordre des `--env-file` load-bearing (`checks/env.checks` porte une DATABASE_URL bidon que
# le vrai `.env` doit écraser). N'écrit RIEN en base. Jamais dans `portfolio-backend` (code déployé).
# `--sortie` : écrit dans `roadmap/` (monté en écriture SEULEMENT pour ce dossier-là).
cd "$(dirname "$0")/.." || exit 2
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
EXTRA=()
args=("$@")
for i in "${!args[@]}"; do
  if [[ "${args[$i]}" == "--sortie" && -n "${args[$((i+1))]:-}" ]]; then
    DEST="${args[$((i+1))]}"
    case "$DEST" in /*) ;; *) DEST="$PWD/$DEST" ;; esac
    DEST=$(realpath -m "$DEST"); args[$i+1]="$DEST"   # même forme canonique que tools/architecte.sh
    DIR=$(dirname "$DEST"); mkdir -p "$DIR"
    EXTRA=(-v "$DIR:$DIR")
  fi
done
exec docker run --rm --network coolify -v "$PWD:/app:ro" "${EXTRA[@]}" \
  -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env "$IMG" python tools/inventaire.py "${args[@]}"
