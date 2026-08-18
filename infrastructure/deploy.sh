#!/usr/bin/env bash
#
# deploy.sh — Option 1 : livraison déterministe d'un projet (commit → push → rebuild Coolify → monitor)
#
# Conçu pour être appelé en UN SEUL appel depuis l'orchestrateur Opus, en fin de session,
# une fois une feature livrée. Tout le verbeux (diff, push, logs de build) est absorbé ici et
# ne remonte PAS dans le contexte Opus — seule une ligne RESULT: finale est renvoyée.
#
# Voir DEPLOY.md (racine du repo) pour le protocole complet et le fallback option 2 (sous-agent).
#
# Usage :
#   infrastructure/deploy.sh <app> -m "<message de commit>" -f "chemin1 chemin2 ..." [-e KEY=VALUE ...]
#   infrastructure/deploy.sh <app> -m "<message>" --staged           # commite l'index déjà en place
#
#   <app>  : clé connue (voir UUID_MAP ci-dessous), ex. bank-review, portfolio-backend
#   -f     : fichiers à stager (relatifs à la racine du repo). Le script commite l'index SEUL.
#   --staged : ne stage rien, commite ce qui est déjà stagé (l'appelant a fait git add).
#   -e     : variable d'env Coolify à écrire AVANT le rebuild (répétable). Écriture AUTOMATIQUE.
#            La valeur n'est jamais affichée (secret-safe) ; seule la clé est loggée.
#
# Codes de sortie : 0 = déploiement finished. ≠0 = échec (l'appelant bascule sur l'option 2).
#   2 = rien à committer   3 = app/UUID inconnu   4 = push refusé
#   5 = échec écriture env  6 = rebuild non déclenché   7 = build en erreur/timeout

set -euo pipefail

REPO="/root/ai-vps-projects"
COOLIFY_CT="coolify"
COOLIFY_DB="coolify-db"
POLL_SECONDS=15
TIMEOUT_SECONDS=1200   # 20 min max d'attente de build

# Miroir de la table UUIDs de CLAUDE.md (§ "UUIDs des applications Coolify").
declare -A UUID_MAP=(
  [assistant-ia]="gayg5mw9jikbio2le75olq8b"
  [bank-review]="ji9jg7ngkva7j4d2uic05d3v"
  [portfolio-backend]="portfoliobackend00000000"
  [portfolio-frontend]="portfoliofrontend0000000"
  [hub]="h7dyrhas03di7jqq2wl2j72z"
  [tool-file-intake]="c57oryka5cw4scy02fi1gfzz"
  [ev-prices]="ev0prices0000000000000000"
)

fail() { echo "RESULT: failure — $2"; exit "$1"; }

# ---- parse args ---------------------------------------------------------------
[[ $# -ge 1 ]] || fail 3 "app manquante (usage: deploy.sh <app> -m ... -f ...)"
APP="$1"; shift
MSG=""; FILES=""; STAGED=0; ENVS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -m) MSG="${2:-}"; shift 2 ;;
    -f) FILES="${2:-}"; shift 2 ;;
    --staged) STAGED=1; shift ;;
    -e) ENVS+=("${2:-}"); shift 2 ;;
    *) fail 3 "argument inconnu: $1" ;;
  esac
done

UUID="${UUID_MAP[$APP]:-}"
[[ -n "$UUID" ]] || fail 3 "app inconnue: '$APP' (clés: ${!UUID_MAP[*]})"
[[ -n "$MSG" ]] || fail 2 "message de commit manquant (-m)"

cd "$REPO"

# ---- 1. staging + commit (index seul) ----------------------------------------
if [[ "$STAGED" -eq 0 ]]; then
  [[ -n "$FILES" ]] || fail 2 "aucun fichier fourni (-f) et pas de --staged"
  # shellcheck disable=SC2086
  git add -- $FILES
fi

if git diff --cached --quiet; then
  fail 2 "index vide — rien à committer pour $APP"
fi

echo "[deploy] $APP — fichiers committés :"
git diff --cached --stat

git commit -m "$MSG" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>" >/dev/null
SHA="$(git rev-parse --short HEAD)"
echo "[deploy] commit $SHA créé"

# ---- 2. push -----------------------------------------------------------------
if ! git push origin main >/tmp/deploy_push.log 2>&1; then
  echo "[deploy] --- git push stderr ---"; cat /tmp/deploy_push.log
  fail 4 "push refusé (voir sortie ci-dessus) — le commit $SHA est local"
fi
echo "[deploy] push origin main OK"

# ---- 3. env vars (automatique) + rebuild, via PHP Eloquent dans le container --
PAYLOAD="/tmp/coolify_deploy_$$.json"
{
  printf '{"uuid":"%s","envs":[' "$UUID"
  first=1
  for kv in "${ENVS[@]:-}"; do
    [[ -z "$kv" ]] && continue
    key="${kv%%=*}"; val="${kv#*=}"
    [[ "$key" == "$kv" ]] && fail 5 "format -e invalide (attendu KEY=VALUE): $key"
    [[ $first -eq 0 ]] && printf ','
    printf '{"key":%s,"value":%s}' \
      "$(printf '%s' "$key" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')" \
      "$(printf '%s' "$val" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')"
    first=0
  done
  printf ']}'
} > "$PAYLOAD"

if [[ ${#ENVS[@]} -gt 0 && -n "${ENVS[0]:-}" ]]; then
  echo "[deploy] variables d'env à écrire : $(for kv in "${ENVS[@]}"; do printf '%s ' "${kv%%=*}"; done)"
fi

PHP_SCRIPT="/tmp/coolify_deploy_$$.php"
cat > "$PHP_SCRIPT" << 'PHP'
<?php
require '/var/www/html/vendor/autoload.php';
$app = require '/var/www/html/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();

$cfg = json_decode(file_get_contents($argv[1]), true);
$application = App\Models\Application::where('uuid', $cfg['uuid'])->first();
if (!$application) { fwrite(STDERR, "APP_NOT_FOUND\n"); exit(3); }

foreach (($cfg['envs'] ?? []) as $e) {
    $ev = App\Models\EnvironmentVariable::firstOrNew([
        'resourceable_type' => 'App\\Models\\Application',
        'resourceable_id'   => $application->id,
        'key'               => $e['key'],
    ]);
    $ev->value       = $e['value'];
    $ev->is_buildtime = true;   // dispo au build
    $ev->is_runtime   = true;   // dispo au runtime
    if (!$ev->exists) { $ev->uuid = (string) \Illuminate\Support\Str::uuid(); }
    $ev->save();
    echo "ENV_SET:{$e['key']}\n";
}

$deployment = App\Models\ApplicationDeploymentQueue::create([
    'application_id'   => $application->id,
    'application_name' => $application->name,
    'server_id'        => $application->destination->server->id,
    'destination_id'   => $application->destination_id,
    'deployment_uuid'  => (string) \Illuminate\Support\Str::uuid(),  // NOT NULL obligatoire
    'git_type'         => 'commit',
    'commit'           => 'HEAD',
    'status'           => 'queued',
]);
App\Jobs\ApplicationDeploymentJob::dispatch($deployment->id)->onQueue('high');  // int, pas le modèle
echo "DEPLOY_ID:{$deployment->id}\n";
PHP

docker cp "$PAYLOAD"    "$COOLIFY_CT":/tmp/coolify_deploy.json >/dev/null
docker cp "$PHP_SCRIPT" "$COOLIFY_CT":/tmp/coolify_deploy.php  >/dev/null
rm -f "$PAYLOAD" "$PHP_SCRIPT"

PHP_OUT="$(docker exec "$COOLIFY_CT" php /tmp/coolify_deploy.php /tmp/coolify_deploy.json 2>&1)" || {
  echo "$PHP_OUT"; fail 5 "échec écriture env / création du déploiement"
}
echo "$PHP_OUT" | grep '^ENV_SET:' | sed 's/^/[deploy] /' || true

DEPLOY_ID="$(echo "$PHP_OUT" | sed -n 's/^DEPLOY_ID:\([0-9]\+\).*/\1/p')"
[[ -n "$DEPLOY_ID" ]] || { echo "$PHP_OUT"; fail 6 "rebuild non déclenché (pas de DEPLOY_ID)"; }
echo "[deploy] rebuild Coolify déclenché — deployment #$DEPLOY_ID"

# ---- 4. monitor --------------------------------------------------------------
elapsed=0
while docker exec "$COOLIFY_DB" psql -U coolify -d coolify -t -c \
  "SELECT 1 FROM application_deployment_queues WHERE id=$DEPLOY_ID AND status IN ('queued','in_progress')" \
  | grep -q 1; do
  if [[ $elapsed -ge $TIMEOUT_SECONDS ]]; then
    fail 7 "timeout ${TIMEOUT_SECONDS}s — deployment #$DEPLOY_ID toujours en cours"
  fi
  echo "[deploy] $(date +%H:%M:%S) build en cours (#$DEPLOY_ID)…"
  sleep "$POLL_SECONDS"; elapsed=$((elapsed + POLL_SECONDS))
done

STATUS="$(docker exec "$COOLIFY_DB" psql -U coolify -d coolify -t -c \
  "SELECT status FROM application_deployment_queues WHERE id=$DEPLOY_ID" | tr -d ' \n')"

if [[ "$STATUS" == "finished" ]]; then
  echo "RESULT: success — $APP déployé (commit $SHA, deployment #$DEPLOY_ID). Notif Slack auto via post_deployment_command."
  exit 0
fi
fail 7 "build #$DEPLOY_ID terminé en status='$STATUS' (attendu 'finished')"
