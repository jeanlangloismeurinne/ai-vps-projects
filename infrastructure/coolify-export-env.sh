#!/usr/bin/env bash
# coolify-export-env.sh — extrait les variables d'environnement stockées (chiffrées) dans Coolify
# et les écrit en fichiers .env en clair, un par application.
#
# POURQUOI CE SCRIPT EXISTE
#   Les valeurs vivent chiffrées (Laravel Crypt, clé APP_KEY du conteneur `coolify`) dans la table
#   `environment_variables` de `coolify-db`. Elles sont donc illisibles sans Coolify debout.
#   Ce script est le pont : il tourne TANT QUE Coolify est démarré, et matérialise les valeurs
#   sur disque pour le déploiement en docker compose standalone.
#
#   Il reste utile après la migration : c'est lui qui permet de re-vérifier qu'un .env local
#   correspond bien à ce que Coolify avait, si on rebascule un jour.
#
# VALIDATION (2026-09-03) : sortie comparée à `docker inspect` de l'app ev-prices qui tournait
#   → hash SHA-256 identique sur les 4 clés. Les deux sources concordent.
#
# NOTES D'IMPLÉMENTATION
#   - Les valeurs sont sérialisées PHP : il faut Crypt::decrypt() (qui désérialise),
#     PAS Crypt::decryptString() qui rendrait `s:85:"..."` brut.
#   - `resourceable_type` vaut littéralement `App\Models\Application` (un seul antislash) :
#     attention à l'échappement shell → PHP.
#   - Filtrer `is_preview = false` : les déploiements de preview dupliquent chaque clé.
#
# USAGE
#   infrastructure/coolify-export-env.sh [<app> ...]     # défaut : toutes les apps
#   Sortie : /root/secrets/coolify-env-backup/<app>.env  (chmod 600)

set -euo pipefail

OUT_DIR="${OUT_DIR:-/root/secrets/coolify-env-backup}"

if ! docker ps --format '{{.Names}}' | grep -qx coolify; then
  echo "ERREUR : le conteneur 'coolify' n'est pas démarré — impossible de déchiffrer (APP_KEY)." >&2
  echo "         Redémarrez-le (docker start coolify) puis relancez." >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
chmod 700 "$OUT_DIR"

if [ $# -gt 0 ]; then
  APPS=("$@")
else
  mapfile -t APPS < <(docker exec coolify-db psql -U coolify -d coolify -tAc \
    "SELECT name FROM applications ORDER BY name")
fi

for app in "${APPS[@]}"; do
  dest="$OUT_DIR/${app}.env"
  # Le PHP est passé en argument (pas d'interpolation shell dans le corps) pour éviter
  # toute mauvaise surprise d'échappement sur les valeurs.
  docker exec -e EXPORT_APP="$app" coolify php -r '
    require "/var/www/html/vendor/autoload.php";
    $a = require "/var/www/html/bootstrap/app.php";
    $a->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();
    $rows = Illuminate\Support\Facades\DB::select(
      "SELECT e.key, e.value FROM environment_variables e
         JOIN applications a ON e.resourceable_id = a.id
        WHERE e.resourceable_type = ? AND a.name = ? AND e.is_preview = false
        ORDER BY e.key",
      ["App\\Models\\Application", getenv("EXPORT_APP")]
    );
    foreach ($rows as $r) {
      $v = Illuminate\Support\Facades\Crypt::decrypt($r->value);
      // Une valeur multiligne casserait le format .env : on la rend sur une seule ligne quotée.
      if (strpos($v, "\n") !== false) {
        echo $r->key . "=\"" . str_replace(["\\", "\"", "\n"], ["\\\\", "\\\"", "\\n"], $v) . "\"\n";
      } else {
        echo $r->key . "=" . $v . "\n";
      }
    }
  ' > "$dest"
  chmod 600 "$dest"
  echo "$app : $(wc -l < "$dest") variables -> $dest"
done
