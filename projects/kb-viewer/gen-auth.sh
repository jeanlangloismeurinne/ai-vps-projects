#!/usr/bin/env bash
# Génère docker-compose.override.yml (gitignored) portant le middleware basic-auth Traefik
# depuis .env. Le hash n'est jamais committé. Le `$` du hash apr1 est doublé (`$$`) pour
# survivre à l'interpolation Compose → Traefik reçoit le hash correct.
set -euo pipefail
cd "$(dirname "$0")"

[ -f .env ] || { echo "manque .env (copier .env.example)"; exit 1; }
set -a; . ./.env; set +a
: "${KB_AUTH_USER:?}" "${KB_AUTH_PASSWORD:?}"

HASH="$(openssl passwd -apr1 "$KB_AUTH_PASSWORD")"
HASH_ESC="${HASH//\$/\$\$}"      # $ → $$ (échappe l'interpolation Compose)

cat > docker-compose.override.yml <<EOF
# GÉNÉRÉ par gen-auth.sh — ne pas committer (contient le hash du mot de passe).
services:
  web:
    labels:
      - "traefik.http.middlewares.kbauth.basicauth.realm=KB"
      - "traefik.http.middlewares.kbauth.basicauth.users=${KB_AUTH_USER}:${HASH_ESC}"
EOF
echo "override généré pour l'utilisateur '${KB_AUTH_USER}'."
