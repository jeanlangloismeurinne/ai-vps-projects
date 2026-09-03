#!/usr/bin/env bash
#
# shoot.sh — capture d'écran headless d'une ou plusieurs pages (vérification visuelle post-déploiement).
#
# Un HTTP 200 ne prouve rien sur l'affichage : docker build / curl ne voient ni un badge de
# statut dupliqué sans étiquette, ni un bandeau qui n'apparaît qu'après un clic. C'est ce que
# la capture voit. Voir CHANTIER_OUTILLAGE_DEV.md §4.
#
# Usage :
#   infrastructure/shoot.sh <base-url> <chemin1> [chemin2 ...]
#   infrastructure/shoot.sh https://portfolio.jlmvpscode.duckdns.org /portfolio /watchlist-v2
#
# Sortie : une capture PNG par chemin dans /tmp/shoot_<horodatage>/<chemin-normalisé>.png
# Les chemins des fichiers écrits sont imprimés sur stdout, un par ligne.
#
# ⚠️ LIMITE — la capture est NON AUTHENTIFIÉE. Sur une app protégée (hub, bank-review,
# kb-viewer en basic-auth) le script rend l'écran de connexion, pas la page visée, et le PNG
# obtenu paraît parfaitement valide : bonne taille, vrai rendu, exit 0. Un succès de shoot.sh
# ne prouve donc PAS qu'on a vu la bonne page — il faut REGARDER l'image. Pour les pages
# derrière login il faudrait passer un cookie ou des identifiants : non implémenté à ce jour.

set -euo pipefail

[[ $# -ge 2 ]] || { echo "usage: shoot.sh <base-url> <chemin1> [chemin2 ...]" >&2; exit 1; }

BASE_URL="$1"; shift
OUT_DIR="/tmp/shoot_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT_DIR"

for path in "$@"; do
  slug="$(echo "$path" | tr '/' '_' | sed 's/^_//; s/^$/root/')"
  out="$OUT_DIR/${slug}.png"
  google-chrome --headless --disable-gpu --no-sandbox --hide-scrollbars \
    --window-size=1440,2400 --virtual-time-budget=12000 \
    --screenshot="$out" "${BASE_URL%/}${path}" >/dev/null 2>&1
  echo "$out"
done
