#!/usr/bin/env bash
# Rebuild du site statique KB : vault (RO) → volume kb_public (servi par nginx).
# Tourne dans un conteneur node ÉPHÉMÈRE : les scripts npm (code externe Quartz) sont
# sandboxés, jamais exécutés sur l'hôte. node_modules est mis en cache dans ./quartz.
# Idempotent ; appelé par le timer systemd kb-viewer-build.
set -euo pipefail
cd "$(dirname "$0")"

VAULT=/storage/journal-vault
[ -d quartz ] || { echo "quartz/ absent — lancer setup.sh d'abord"; exit 1; }
docker volume inspect kb_public >/dev/null 2>&1 || docker volume create kb_public >/dev/null

docker run --rm \
  -v "$PWD/quartz":/quartz -w /quartz \
  -v "$VAULT":/vault:ro \
  -v kb_public:/out \
  node:22-bookworm-slim \
  bash -lc '
    set -e
    [ -d node_modules ] || npm install --no-audit --no-fund
    # Quartz rmdir son dossier de sortie : on build en local (pas sur le point de montage),
    # puis on remplace le CONTENU de /out (jamais /out lui-même = le volume).
    rm -rf /build && npx quartz build -d /vault -o /build
    find /out -mindepth 1 -delete
    cp -aT /build /out
    # Le vault na pas dindex.md : on redirige / vers laccueil (Accueil.md du vault).
    [ -f /out/index.html ] || printf "%s" "<!doctype html><meta charset=utf-8><meta http-equiv=refresh content=\"0; url=./Accueil\">" > /out/index.html
  '
echo "build OK → volume kb_public"
