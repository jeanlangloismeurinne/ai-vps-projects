#!/usr/bin/env bash
# Lanceur de l'agent ARCHITECTE (`tools/architecte.py`) — lot M3.
#
#   bash tools/architecte.sh NVDA --matiere-seule          # GRATUIT, lecture seule
#   bash tools/architecte.sh NVDA                           # à blanc, payant ~centimes, rien écrit
#   bash tools/architecte.sh RVMD --hors-porte --sortie /tmp/rvmd.json
#   bash tools/architecte.sh NVDA --ecrire                  # réservé à Opus après lecture à blanc
#
# ⚠️ Appelle DeepSeek (DeepInfra) sauf `--matiere-seule`, et lit la base — réseau `coolify` + le
# vrai `.env`. Ordre des `--env-file` load-bearing (`checks/env.checks` porte une DATABASE_URL
# bidon que le vrai `.env` doit écraser).
#
# ⚠️ Jamais dans `portfolio-backend` : instance NEUVE de son image, code monté en lecture seule.
# Vérifier `docker ps`/`ps aux` avant toute relance (deux passages concurrents ont déjà écrit en
# même temps sur d'autres outils de ce projet).
cd "$(dirname "$0")/.." || exit 2
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')

# `--sortie FICHIER` écrit un JSON : `/app` est monté EN LECTURE SEULE, donc le fichier de sortie a
# besoin de son PROPRE montage, en écriture, au MÊME chemin hôte/conteneur (sinon il naît et meurt
# dans le conteneur éphémère). Détecté ici, jamais recopié dans `architecte.py`.
EXTRA=()
args=("$@")
for i in "${!args[@]}"; do
  if [[ "${args[$i]}" == "--sortie" && -n "${args[$((i+1))]:-}" ]]; then
    DEST="${args[$((i+1))]}"
    case "$DEST" in /*) ;; *) DEST="$PWD/$DEST" ;; esac
    # Un chemin avec `..` ne se monte pas tel quel dans le conteneur (mesuré le 2026-10-23) : forme canonique.
    DEST=$(realpath -m "$DEST"); args[$i+1]="$DEST"
    DIR=$(dirname "$DEST")
    mkdir -p "$DIR"
    EXTRA=(-v "$DIR:$DIR")
  fi
done

exec docker run --rm --network coolify -v "$PWD:/app:ro" "${EXTRA[@]}" \
  -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env "$IMG" python tools/architecte.py "${args[@]}"
