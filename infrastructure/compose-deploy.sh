#!/usr/bin/env bash
#
# compose-deploy.sh — livraison déterministe d'un projet (commit → push → build → up → vérif).
#
# Remplace `deploy.sh` depuis la migration Coolify → docker compose du 2026-09-03.
# MÊME CONTRAT D'APPEL ET MÊMES CODES DE SORTIE : conçu pour être appelé en UN SEUL appel depuis
# l'orchestrateur Opus en fin de session. Tout le verbeux (diff, push, logs de build) est absorbé
# ici et ne remonte PAS dans le contexte — seule une ligne `RESULT:` finale est renvoyée.
#
# Usage :
#   infrastructure/compose-deploy.sh <app> -m "<message>" -f "chemin1 chemin2 …" [-e KEY=VALUE …]
#   infrastructure/compose-deploy.sh <app> -m "<message>" --staged        # commite l'index en place
#   infrastructure/compose-deploy.sh <app> --rebuild-only [-e KEY=VALUE …] # rebuild sans committer
#
#   -f   fichiers à stager (relatifs à la racine du repo). Le script commite l'index SEUL.
#   -e   variable à écrire dans le `.env` de l'app AVANT le build (répétable).
#        La valeur n'est JAMAIS affichée ; seule la clé est loggée. Le fichier reste en 600.
#
# Codes de sortie : 0 = déployé et vérifié. ≠0 = échec.
#   2 = rien à committer     3 = app inconnue        4 = push refusé
#   5 = échec écriture env   6 = compose invalide    7 = build en erreur/timeout
#   8 = build OK mais l'app ne répond pas (NOUVEAU — voir § vérification)
#
# ─── CE QUI A CHANGÉ PAR RAPPORT À deploy.sh ──────────────────────────────────────────────────
#   • Le build est SYNCHRONE. Plus de file de déploiement à sonder, donc plus de boucle de
#     monitoring ni de « poll en échec ≠ build terminé ». Le build parle par son code de retour.
#   • Les variables d'env vont dans le `.env` du projet, plus dans la base Coolify chiffrée.
#   • Les `post_deployment_command` (notif Slack, rattachement réseau) n'existent plus : le
#     rattachement réseau est déclaré dans le compose, la notif Slack est faite ici (§ 6).
#   • Une vérification post-déploiement est FAITE, pas supposée. `deploy.sh` renvoyait success
#     dès que Coolify disait `finished` — un conteneur qui démarre puis meurt en boucle passait.
#
# ─── LE PIÈGE QUE CE SCRIPT DÉSAMORCE ─────────────────────────────────────────────────────────
# Deux conteneurs portant les mêmes labels Traefik = le proxy répartit le trafic entre ancien et
# nouveau code, sans rien signaler. `compose up` remplace le conteneur en place, mais un vestige
# (conteneur Coolify, essai manuel, service renommé) peut subsister : § 5 refuse de conclure au
# succès tant que le domaine n'est pas servi par exactement un conteneur.

set -euo pipefail

REPO="/root/ai-vps-projects"
BUILD_TIMEOUT=1200        # 20 min max de build
PROBE_TIMEOUT=120         # 2 min max pour que l'app réponde après démarrage
BUILD_LOG="/tmp/compose_deploy_build_$$.log"

fail() { echo "RESULT: failure — $2"; exit "$1"; }

# ─── Table des apps ───────────────────────────────────────────────────────────────────────────
# app → dossier de la stack | service compose ('-' = toute la stack) | fichier .env | sonde
# `portfolio-backend` / `portfolio-frontend` restent des clés valides : c'étaient deux apps
# Coolify, c'est désormais une seule stack à deux services, et on peut n'en rebuilder qu'un.
declare -A STACK_DIR=(
  [ev-prices]=projects/ev-prices
  [bank-review]=projects/bank-review
  [hub]=projects/hub
  [assistant-ia]=projects/assistant-ia
  [tool-file-intake]=projects/tool-file-intake
  [comms-gateway]=projects/comms-gateway
  [portfolio-tracker]=projects/portfolio-tracker
  [portfolio-backend]=projects/portfolio-tracker
  [portfolio-frontend]=projects/portfolio-tracker
)
declare -A SERVICE=(
  [ev-prices]=- [bank-review]=- [hub]=- [assistant-ia]=- [tool-file-intake]=-
  [comms-gateway]=- [portfolio-tracker]=-
  [portfolio-backend]=backend [portfolio-frontend]=frontend
)
declare -A ENV_FILE=(
  [ev-prices]=projects/ev-prices/.env
  [bank-review]=projects/bank-review/.env
  [hub]=projects/hub/.env
  [assistant-ia]=projects/assistant-ia/.env
  [tool-file-intake]=projects/tool-file-intake/.env
  [comms-gateway]=projects/comms-gateway/.env
  [portfolio-backend]=projects/portfolio-tracker/backend/.env
  [portfolio-frontend]=projects/portfolio-tracker/frontend/.env
  # portfolio-tracker : volontairement absent — la stack a DEUX .env, il faut viser le service.
)
# Sonde de vitalité. On teste ce que voit un utilisateur — donc via le domaine public quand il y
# en a un, c'est-à-dire la chaîne complète Traefik + TLS + app, pas seulement le process.
# `net:<conteneur>:<port><chemin>` = sonde interne pour un service sans route publique : l'IP du
# conteneur est résolue au moment de la sonde et appelée depuis l'hôte (les réseaux bridge sont
# routables depuis l'hôte). On ne sonde PAS via `docker exec curl` : rien ne garantit qu'une image
# embarque curl — l'image Node du gateway ne l'a pas, et l'échec ressemblait à une app morte.
declare -A PROBE=(
  [ev-prices]=https://ev.jlmvpscode.duckdns.org/
  [bank-review]=https://bank.jlmvpscode.duckdns.org/
  [hub]=https://jlmvpscode.duckdns.org/
  [assistant-ia]=https://assistant.jlmvpscode.duckdns.org/health
  [tool-file-intake]=http://127.0.0.1:8020/health     # service interne, aucun domaine public
  [comms-gateway]=net:comms-gateway:8000/health   # seul /webhooks est routé publiquement
  [portfolio-tracker]=https://portfolio.jlmvpscode.duckdns.org/api/health
  [portfolio-backend]=https://portfolio.jlmvpscode.duckdns.org/api/health
  [portfolio-frontend]=https://portfolio.jlmvpscode.duckdns.org/
)
# Code ATTENDU, pas « code non catastrophique ».
# Un « tout sauf 5xx » avait laissé passer un 404 sur /api/health : pendant la recréation du
# conteneur backend, Traefik n'a plus de route /api et c'est le catch-all frontend qui répond —
# un 404 de Next.js, indiscernable d'un succès si on ne regarde que la classe du code.
declare -A EXPECT=(
  [ev-prices]='^(200|302)$'
  [bank-review]='^200$'
  [hub]='^(200|302)$'
  [assistant-ia]='^200$'
  [tool-file-intake]='^200$'
  [comms-gateway]='^200$'
  [portfolio-tracker]='^200$'
  [portfolio-backend]='^200$'
  [portfolio-frontend]='^200$'
)
# Conteneurs à attendre « running (et healthy si un healthcheck est déclaré) » avant de sonder.
declare -A CONTAINERS=(
  [ev-prices]="ev-prices"
  [bank-review]="bank-review"
  [hub]="homepage"
  [assistant-ia]="assistant-ia"
  [tool-file-intake]="tool-file-intake"
  [comms-gateway]="comms-gateway"
  [portfolio-tracker]="portfolio-backend portfolio-frontend"
  [portfolio-backend]="portfolio-backend"
  [portfolio-frontend]="portfolio-frontend"
)
# Domaine servi, pour le contrôle d'unicité du § 5 ('-' = pas d'exposition publique).
declare -A DOMAIN=(
  [ev-prices]=ev.jlmvpscode.duckdns.org
  [bank-review]=bank.jlmvpscode.duckdns.org
  [hub]=jlmvpscode.duckdns.org
  [assistant-ia]=assistant.jlmvpscode.duckdns.org
  [tool-file-intake]=-
  [comms-gateway]=comms.jlmvpscode.duckdns.org
  [portfolio-tracker]=portfolio.jlmvpscode.duckdns.org
  [portfolio-backend]=portfolio.jlmvpscode.duckdns.org
  [portfolio-frontend]=portfolio.jlmvpscode.duckdns.org
)
# Notifications Slack de fin de déploiement. Reprend à l'identique ce que faisait le
# `post_deployment_command` de Coolify (cf. CLAUDE.md § Notification de déploiement) : un
# service = un channel, la liste des tickets fermés depuis le dernier déploiement.
declare -A NOTIFY=(
  [bank-review]="bank-review"
  [assistant-ia]="journal kanban"
)
DEPLOY_HOOK="https://assistant.jlmvpscode.duckdns.org/webhook/deploy-complete"

# ─── 0. Arguments ─────────────────────────────────────────────────────────────────────────────
[[ $# -ge 1 ]] || fail 3 "app manquante (usage: compose-deploy.sh <app> -m … -f …)"
APP="$1"; shift
MSG=""; FILES=""; STAGED=0; REBUILD_ONLY=0; ENVS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -m) MSG="${2:-}"; shift 2 ;;
    -f) FILES="${2:-}"; shift 2 ;;
    --staged) STAGED=1; shift ;;
    --rebuild-only) REBUILD_ONLY=1; shift ;;
    -e) ENVS+=("${2:-}"); shift 2 ;;
    *) fail 3 "argument inconnu: $1" ;;
  esac
done

DIR="${STACK_DIR[$APP]:-}"
[[ -n "$DIR" ]] || fail 3 "app inconnue: '$APP' (clés: ${!STACK_DIR[*]})"
[[ "$REBUILD_ONLY" -eq 1 || -n "$MSG" ]] || fail 2 "message de commit manquant (-m)"

cd "$REPO"
[[ -f "$DIR/docker-compose.yml" ]] || fail 3 "$DIR/docker-compose.yml introuvable"

# ─── 1. Commit ────────────────────────────────────────────────────────────────────────────────
if [[ "$REBUILD_ONLY" -eq 1 ]]; then
  SHA="$(git rev-parse --short HEAD)"
  echo "[deploy] --rebuild-only — pas de commit/push, rebuild du HEAD actuel ($SHA)"
else
  if [[ "$STAGED" -eq 0 ]]; then
    [[ -n "$FILES" ]] || fail 2 "aucun fichier fourni (-f) et pas de --staged"
    # shellcheck disable=SC2086
    git add -- $FILES
  fi
  git diff --cached --quiet && fail 2 "index vide — rien à committer pour $APP"

  echo "[deploy] $APP — fichiers committés :"
  git diff --cached --stat

  git commit -m "$MSG" -m "Co-Authored-By: Claude <noreply@anthropic.com>" >/dev/null
  SHA="$(git rev-parse --short HEAD)"
  echo "[deploy] commit $SHA créé"

  # ─── 2. Push ────────────────────────────────────────────────────────────────────────────────
  # `~/.netrc` fait échouer le push en 403 malgré un token valide. Le contournement connu est
  # d'isoler HOME. On tente d'abord normalement, et si le repli sert, on le DIT — pour ne pas
  # masquer une vraie panne d'identifiants derrière un succès silencieux.
  if git push origin main >/tmp/deploy_push_$$.log 2>&1; then
    echo "[deploy] push origin main OK"
  else
    mkdir -p /tmp/githome
    if HOME=/tmp/githome git push origin main >>/tmp/deploy_push_$$.log 2>&1; then
      echo "[deploy] push OK — via le contournement HOME=/tmp/githome (~/.netrc renvoie 403)"
    else
      echo "[deploy] --- git push stderr ---"; tail -20 /tmp/deploy_push_$$.log
      rm -f /tmp/deploy_push_$$.log
      fail 4 "push refusé — le commit $SHA est local, rien n'a été déployé"
    fi
  fi
  rm -f /tmp/deploy_push_$$.log
fi

# ─── 3. Variables d'environnement ─────────────────────────────────────────────────────────────
if [[ ${#ENVS[@]} -gt 0 && -n "${ENVS[0]:-}" ]]; then
  EF="${ENV_FILE[$APP]:-}"
  [[ -n "$EF" ]] || fail 5 "'$APP' porte deux .env (backend/frontend) — viser portfolio-backend ou portfolio-frontend"
  [[ -f "$EF" ]] || fail 5 "$EF introuvable"
  echo "[deploy] variables à écrire dans $EF : $(for kv in "${ENVS[@]}"; do printf '%s ' "${kv%%=*}"; done)"

  TMP_ENV="$(mktemp)"; chmod 600 "$TMP_ENV"
  cp "$EF" "$TMP_ENV"
  for kv in "${ENVS[@]}"; do
    [[ -z "$kv" ]] && continue
    key="${kv%%=*}"
    [[ "$key" == "$kv" ]] && { rm -f "$TMP_ENV"; fail 5 "format -e invalide (attendu KEY=VALUE): $key"; }
    [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || { rm -f "$TMP_ENV"; fail 5 "nom de variable invalide: $key"; }
    # Réécriture par python : la valeur n'est jamais interprétée par le shell ni journalisée.
    KV="$kv" TARGET="$TMP_ENV" python3 - <<'PY' || { rm -f "$TMP_ENV"; fail 5 "échec de réécriture de $key"; }
import os
kv = os.environ["KV"]; key, _, val = kv.partition("=")
path = os.environ["TARGET"]
lines = open(path).read().splitlines()
out, done = [], False
for line in lines:
    if line.split("=", 1)[0].strip() == key and not line.lstrip().startswith("#"):
        if not done:
            out.append(f"{key}={val}"); done = True
    else:
        out.append(line)
if not done:
    out.append(f"{key}={val}")
open(path, "w").write("\n".join(out) + "\n")
PY
  done
  # Remplacement en place : on préserve les permissions du fichier d'origine (600).
  cat "$TMP_ENV" > "$EF"
  rm -f "$TMP_ENV"
  echo "[deploy] $EF mis à jour (${#ENVS[@]} variable(s), valeurs non journalisées)"
fi

# ─── 4. Build + démarrage ─────────────────────────────────────────────────────────────────────
SVC="${SERVICE[$APP]}"
COMPOSE_TARGET=()
[[ "$SVC" != "-" ]] && COMPOSE_TARGET=("$SVC")

cd "$REPO/$DIR"
docker compose config -q 2>/tmp/compose_cfg_$$.log \
  || { echo "[deploy] --- compose config ---"; cat /tmp/compose_cfg_$$.log; rm -f /tmp/compose_cfg_$$.log; \
       fail 6 "docker-compose.yml invalide pour $APP"; }
rm -f /tmp/compose_cfg_$$.log

# `--remove-orphans` uniquement sur la stack entière : c'est là qu'un service supprimé du compose
# peut laisser un conteneur debout avec ses anciens labels Traefik.
ORPHANS=()
[[ "$SVC" == "-" ]] && ORPHANS=(--remove-orphans)

echo "[deploy] build + up ($APP${SVC:+, service $SVC}) — jusqu'à ${BUILD_TIMEOUT}s…"
if ! timeout "$BUILD_TIMEOUT" docker compose up -d --build "${ORPHANS[@]}" "${COMPOSE_TARGET[@]}" \
      >"$BUILD_LOG" 2>&1; then
  rc=$?
  echo "[deploy] --- 40 dernières lignes du build ---"; tail -40 "$BUILD_LOG"
  rm -f "$BUILD_LOG"
  [[ $rc -eq 124 ]] && fail 7 "timeout ${BUILD_TIMEOUT}s pendant le build de $APP"
  fail 7 "build/up en échec pour $APP (code $rc)"
fi
echo "[deploy] conteneur(s) démarré(s)"
rm -f "$BUILD_LOG"

# ─── 5. Vérification — l'app répond, et une seule sert le domaine ─────────────────────────────
DOM="${DOMAIN[$APP]}"
if [[ "$DOM" != "-" ]]; then
  # Inspection en un seul appel, dépouillée en python : les templates Go `{{range $k,$v := …}}`
  # sur des labels sont une source d'erreurs de parsing, et un `grep` qui ne matche pas ferait
  # sortir le script sous `set -e` avant même d'avoir conclu.
  SERVING="$(docker ps --format '{{.Names}}' | xargs -r docker inspect 2>/dev/null \
    | DOM="$DOM" python3 -c '
import json, os, sys
dom = "Host(`%s`)" % os.environ["DOM"]
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
for c in data:
    labels = (c.get("Config") or {}).get("Labels") or {}
    if any(dom in str(v) for v in labels.values()):
        print(c["Name"].lstrip("/"))
' || true)"
  COUNT="$(printf '%s' "$SERVING" | grep -c . || true)"
  if [[ "${COUNT:-0}" -gt 1 ]]; then
    # Deux conteneurs sur le même Host() : c'est le double routage. On le dit plutôt que de
    # renvoyer un succès qui « marche » une requête sur deux.
    echo "[deploy] conteneurs portant Host(\`$DOM\`) : $(printf '%s ' $SERVING)"
    # Toléré pour portfolio : backend et frontend partagent le domaine, séparés par PathPrefix.
    [[ "$DOM" == "portfolio.jlmvpscode.duckdns.org" && "$COUNT" -le 2 ]] \
      || fail 8 "$COUNT conteneurs servent $DOM — double routage Traefik, trafic réparti entre deux codes"
  fi
  echo "[deploy] $COUNT conteneur(s) sert $DOM — pas de double routage"
fi

# 5a. Attendre que le conteneur soit prêt AVANT de sonder. Sans cette attente, la sonde court
#     contre la reconfiguration de Traefik et lit une réponse qui n'est pas celle de l'app.
for ct in ${CONTAINERS[$APP]}; do
  waited=0
  while [[ $waited -lt $PROBE_TIMEOUT ]]; do
    state="$(docker inspect "$ct" --format '{{.State.Status}}:{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' 2>/dev/null || echo "absent:none")"
    case "$state" in
      running:healthy|running:none) break ;;
      running:starting) : ;;
      *) : ;;
    esac
    sleep 3; waited=$((waited + 3))
  done
  echo "[deploy] $ct — état: ${state:-inconnu}"
  [[ "$state" == running:* ]] || fail 8 "$ct n'est pas 'running' après ${PROBE_TIMEOUT}s (état: $state)"
  [[ "$state" == running:unhealthy ]] && fail 8 "$ct démarre mais son healthcheck échoue"
done

# 5b. Sonde applicative, jusqu'à obtenir le code ATTENDU (pas « un code acceptable »).
URL="${PROBE[$APP]}"; WANT="${EXPECT[$APP]}"
echo "[deploy] sonde $URL — attendu $WANT (jusqu'à ${PROBE_TIMEOUT}s)…"
CODE=""; waited=0
while [[ $waited -lt $PROBE_TIMEOUT ]]; do
  TARGET="$URL"
  if [[ "$URL" == net:* ]]; then
    rest="${URL#net:}"; ct="${rest%%:*}"; portpath="${rest#*:}"
    ip="$(docker inspect "$ct" --format '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' 2>/dev/null | awk '{print $1}')"
    [[ -n "$ip" ]] || { sleep 5; waited=$((waited + 5)); continue; }
    TARGET="http://$ip:$portpath"
  fi
  CODE="$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "$TARGET" 2>/dev/null || echo 000)"
  [[ "$CODE" =~ $WANT ]] && break
  sleep 5; waited=$((waited + 5))
done
if ! [[ "$CODE" =~ $WANT ]]; then
  echo "[deploy] --- 30 dernières lignes de log applicatif ---"
  docker compose logs --tail 30 ${COMPOSE_TARGET[@]+"${COMPOSE_TARGET[@]}"} 2>&1 | tail -30
  fail 8 "build OK mais $URL répond '$CODE' (attendu $WANT) après ${PROBE_TIMEOUT}s — déploiement non vivant"
fi
echo "[deploy] sonde OK (HTTP $CODE)"

# ─── 6. Notification Slack de déploiement ─────────────────────────────────────────────────────
NOTIFIED=""
for svc in ${NOTIFY[$APP]:-}; do
  if curl -sf -X POST "$DEPLOY_HOOK" -H 'Content-Type: application/json' \
       --max-time 20 -d "{\"service\":\"$svc\"}" >/dev/null 2>&1; then
    NOTIFIED="$NOTIFIED$svc "
  else
    echo "[deploy] ⚠ notif Slack '$svc' non délivrée (le déploiement, lui, est bon)"
  fi
done

SUFFIX=""
[[ -n "$NOTIFIED" ]] && SUFFIX=", notif Slack: ${NOTIFIED% }"
echo "RESULT: success — $APP déployé et vérifié (commit $SHA, HTTP $CODE$SUFFIX)."
