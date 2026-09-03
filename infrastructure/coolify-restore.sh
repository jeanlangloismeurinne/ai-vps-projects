#!/usr/bin/env bash
# coolify-restore.sh — REBASCULER de docker compose standalone vers Coolify.
#
# Contrepartie de la migration du 2026-09-03. Conçu pour être lancé sans réfléchir le jour où le
# setup compose ne convient plus, ou pour remonter un serveur de production piloté par Coolify.
#
# ─── CE QUI A ÉTÉ PRÉSERVÉ POUR RENDRE CE RETOUR POSSIBLE ─────────────────────────────────────
#   /data/coolify/                  config, certificats, sources, .env (APP_KEY !) — intact
#   volume docker `coolify-db`      les 8 applications, leurs domaines, leurs 66 variables
#                                   d'environnement chiffrées, l'historique de déploiement
#   volume docker `coolify-redis`   file de jobs — intact
#   coolify-proxy (Traefik)         JAMAIS arrêté : c'est lui qui sert les apps aujourd'hui
#   /root/secrets/coolify-rollback-2026-09-03/
#       coolify-db.sql · data-coolify.tar.gz · labels-avant-migration.json · applications.csv
#
# Seuls des conteneurs et des images ont été supprimés. Les images se re-téléchargent, SAUF une
# (voir § soketi plus bas). Aucune donnée Coolify n'a été détruite.
#
# ─── POURQUOI `docker compose` ET PAS `docker start` ──────────────────────────────────────────
# Docker refuse de supprimer une image encore référencée par un conteneur, même arrêté. Retirer
# les images imposait donc de retirer les conteneurs : il n'y a plus rien à `docker start`. On
# recrée depuis les fichiers d'installation de Coolify, qui rattachent les volumes nommés
# existants — la base repart telle quelle, sans restauration de dump.
#
# ─── DEUX ÉPINGLAGES QUI COMPTENT ─────────────────────────────────────────────────────────────
# 1. coolify : `docker-compose.prod.yml` résout `${LATEST_IMAGE:-latest}`, et `.env` ne définit
#    PAS LATEST_IMAGE. Un `up -d` nu tirerait donc `:latest` sur un volume de base créé par
#    4.0.0-beta.473 : Coolify jouerait ses migrations au démarrage, et ce n'est pas réversible.
#    D'où COOLIFY_VERSION ci-dessous, figé sur ce qui tournait. Pour mettre à jour Coolify,
#    c'est un acte délibéré et séparé (`/data/coolify/source/upgrade.sh`), pas un effet de bord
#    de ce script.
# 2. soketi : voir coolify-restore.override.yml. Le tag `1.0.13-patched` n'existe pas sur
#    ghcr.io ; l'image locale a été conservée et est ré-épinglée si elle est toujours là.
#
# ─── USAGE ────────────────────────────────────────────────────────────────────────────────────
#   infrastructure/coolify-restore.sh                 # relance le plan de contrôle seul
#   infrastructure/coolify-restore.sh <app> [<app>…]  # + rend la main à Coolify sur ces apps
#   infrastructure/coolify-restore.sh --all           # + rend la main sur les 8 apps migrées
#
# ─── L'ORDRE COMPTE ───────────────────────────────────────────────────────────────────────────
# Une app ne doit JAMAIS tourner en double (stack compose + conteneur Coolify) : les deux portent
# les mêmes règles Traefik, et le proxy répartirait le trafic entre l'ancien et le nouveau code,
# silencieusement et par intermittence. Ce script coupe donc TOUJOURS la stack compose avant de
# redonner l'app à Coolify.

set -euo pipefail

REPO=/root/ai-vps-projects
SRC=/data/coolify/source
OVERRIDE="$REPO/infrastructure/coolify-restore.override.yml"
BK=/root/secrets/coolify-rollback-2026-09-03

# Version figée au moment de la migration (cf. § épinglages).
COOLIFY_VERSION=4.0.0-beta.473
PATCHED_REALTIME=ghcr.io/coollabsio/coolify-realtime:1.0.13-patched

# Les 8 apps migrées : nom du dossier sous projects/. Sert à `--all` et au message final.
MIGRATED_APPS=(ev-prices bank-review hub assistant-ia tool-file-intake comms-gateway portfolio-tracker)
# portfolio-tracker = 2 apps côté Coolify (portfolio-backend + portfolio-frontend), une seule
# stack compose ici : `docker compose down` sur le dossier coupe bien les deux.

die() { echo "ERREUR: $*" >&2; exit 1; }

[ -f "$SRC/docker-compose.yml" ] || die "$SRC/docker-compose.yml absent — l'installation Coolify a été supprimée. Repartir de $BK (data-coolify.tar.gz + coolify-db.sql)."
[ -f "$SRC/.env" ] || die "$SRC/.env absent — APP_KEY perdue, les variables d'env chiffrées seraient illisibles. Restaurer depuis $BK/data-coolify.tar.gz."

APPS=("$@")
if [ "${1:-}" = "--all" ]; then APPS=("${MIGRATED_APPS[@]}"); fi

echo "== 1. Vérification des prérequis =="
docker volume inspect coolify-db >/dev/null 2>&1 \
  && echo "   volume coolify-db présent — la base Coolify repart en l'état" \
  || echo "   ⚠  volume coolify-db ABSENT — il faudra recharger $BK/coolify-db.sql après le démarrage"
docker ps --format '{{.Names}}' | grep -qx coolify-proxy \
  && echo "   coolify-proxy en service — les apps restent servies pendant l'opération" \
  || echo "   ⚠  coolify-proxy à l'arrêt — plus rien n'est servi en HTTPS"

COMPOSE_ARGS=(-f "$SRC/docker-compose.yml" -f "$SRC/docker-compose.prod.yml")
if docker image inspect "$PATCHED_REALTIME" >/dev/null 2>&1; then
  COMPOSE_ARGS+=(-f "$OVERRIDE")
  echo "   image soketi patchée présente — ré-épinglée via coolify-restore.override.yml"
else
  echo "   ⚠  $PATCHED_REALTIME introuvable : soketi repartira sur l'image UPSTREAM 1.0.17."
  echo "      Le correctif npm du 2026-04-23 n'y est pas. Re-scanner l'image avant de la garder"
  echo "      (COOLIFY_PLAYBOOK.md § coolify-realtime)."
fi
COMPOSE_ARGS+=(--env-file "$SRC/.env" -p coolify)

echo
echo "== 2. Démarrage du plan de contrôle Coolify (v$COOLIFY_VERSION) =="
echo "   Les images manquantes se re-téléchargent (~1,1 Go) — comptez quelques minutes."
LATEST_IMAGE="$COOLIFY_VERSION" docker compose "${COMPOSE_ARGS[@]}" up -d 2>&1 | sed 's/^/   /'

echo
echo "== 3. Attente de la disponibilité de Coolify =="
ready=0
for _ in $(seq 1 90); do
  if curl -sf http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
    echo "   Coolify répond sur http://localhost:8000"; ready=1; break
  fi
  sleep 2
done
[ "$ready" = 1 ] || echo "   ⚠  pas de réponse après 3 min — 'docker logs coolify' pour comprendre."

if [ ${#APPS[@]} -eq 0 ]; then
  cat <<EOF

Plan de contrôle relancé. Les apps continuent de tourner en docker compose : rien n'a bougé
côté trafic, et vous pouvez vous arrêter là si vous ne vouliez que l'UI.

Pour rendre une app à Coolify :  $0 <app> [<app>…]
Pour les rendre toutes :         $0 --all
Apps migrées : ${MIGRATED_APPS[*]}
EOF
  exit 0
fi

echo
echo "== 4. Restitution des apps à Coolify =="
for app in "${APPS[@]}"; do
  echo "-- $app"
  [ -d "$REPO/projects/$app" ] || { echo "     dossier inconnu, ignoré"; continue; }
  # On coupe la stack compose AVANT que Coolify ne redéploie : pas de double routage.
  (cd "$REPO/projects/$app" && docker compose down 2>&1 | sed 's/^/     /') || true
  echo "     stack compose arrêtée → déclenchez le rebuild depuis l'UI Coolify."
  echo "     L'app, son domaine et ses variables d'env y sont intacts (rien n'a été supprimé)."
done

cat <<'EOF'

⚠  Après chaque redéploiement Coolify, vérifier qu'UN SEUL conteneur sert le domaine :
      docker ps --format '{{.Names}}\t{{.Image}}'
   Un conteneur orphelin resté debout porterait les mêmes labels Traefik que le nouveau, et le
   proxy alternerait entre ancien et nouveau code sans rien signaler.

Deux points que la migration a corrigés et que Coolify ne réappliquera pas tout seul :
   - `traefik.docker.network=coolify` sur les conteneurs multi-réseaux (assistant-ia, ev-prices) :
     à remettre en custom label Coolify, sinon gateway timeout intermittent.
   - les middlewares `gzip` / `redirect-to-https` globaux redeviennent disponibles une fois
     Coolify relancé — les stacks compose, elles, déclarent les leurs (hubgzip, asgzip, …).
EOF
