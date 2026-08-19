# COOLIFY_PLAYBOOK.md — Pièges Coolify & sécurité infra

> Playbook de déploiement et de dépannage Coolify. Chargé **à la demande** (déploiement,
> diagnostic infra) — référencé depuis `CLAUDE.md` et `DEPLOY.md`. Ne pas charger en permanence.

## Pièges Coolify

### Volumes bind-mount : une seule option `-v` dans `custom_docker_run_options`
Coolify n'applique pas plusieurs flags `-v` dans `custom_docker_run_options`.
Pour plusieurs volumes, utiliser le mode `dockercompose` (build_pack = dockercompose) —
les volumes définis dans `docker-compose.yml` sont alors tous montés correctement.

### Mode `dockercompose` : chemin du fichier compose
`docker_compose_location` est relatif à `base_directory`. Mettre `/docker-compose.yml`,
pas le chemin complet — Coolify les concatène et double le chemin sinon.

### `env_file` dans docker-compose.yml
En mode `dockercompose`, ne pas mettre `env_file: .env` — le fichier `.env` est gitignored
et absent du build. Coolify injecte ses variables directement dans le service.

### Mode `dockerfile` multi-services : deux apps séparées

Pour un projet avec backend + frontend sur le même domaine (ex: `/api` et `/`), créer **deux apps Coolify distinctes** en mode `dockerfile` plutôt qu'une seule app `dockercompose`. Raison : Coolify génère `infra-net: null` lors du re-processing YAML multi-services, cassant la résolution DNS interne.

Coolify ajoute automatiquement un middleware `stripprefix` quand le fqdn contient un path (ex: `https://domain.com/api`). Le backend FastAPI doit donc déclarer ses routes **sans le préfixe** (ex: `/positions` et non `/api/positions`).

### `custom_labels` en mode `dockerfile` : remplace les labels Traefik auto-générés

Quand `custom_labels` est renseigné dans Coolify (champ DB base64), Coolify **remplace entièrement** les labels Traefik auto-générés par ces custom_labels. Le container n'a alors que ce label → "no available server".

**Règle :** si un `custom_labels` est nécessaire (ex: `traefik.docker.network=coolify`), il faut y inclure aussi **tous** les labels Traefik de routage. Mettre à jour en DB :

```bash
NEW_B64=$(printf 'traefik.docker.network=coolify\ntraefik.enable=true\n...' | base64 -w 0)
docker exec coolify-db psql -U coolify -d coolify -c \
  "UPDATE applications SET custom_labels='$NEW_B64' WHERE uuid='{UUID}';"
```

Puis rebuild. Voir `custom_labels` du frontend portfolio comme exemple complet.

### Mode `dockercompose` : labels Traefik obligatoires

**Coolify n'injecte PAS les labels Traefik pour les apps `dockercompose`** (contrairement au mode nixpacks où ils sont auto-générés). Sans ces labels, Traefik ignore le container → "no available server".

Il faut les déclarer explicitement dans `docker-compose.yml` :

```yaml
services:
  mon-service:
    labels:
      - "traefik.enable=true"
      - "traefik.http.middlewares.gzip.compress=true"
      - "traefik.http.middlewares.redirect-to-https.redirectscheme.scheme=https"
      - "traefik.http.routers.http-0-{UUID}.entryPoints=http"
      - "traefik.http.routers.http-0-{UUID}.middlewares=redirect-to-https"
      - "traefik.http.routers.http-0-{UUID}.rule=Host(`{domaine}`) && PathPrefix(`/`)"
      - "traefik.http.routers.http-0-{UUID}.service=http-0-{UUID}"
      - "traefik.http.routers.https-0-{UUID}.entryPoints=https"
      - "traefik.http.routers.https-0-{UUID}.middlewares=gzip"
      - "traefik.http.routers.https-0-{UUID}.rule=Host(`{domaine}`) && PathPrefix(`/`)"
      - "traefik.http.routers.https-0-{UUID}.service=https-0-{UUID}"
      - "traefik.http.routers.https-0-{UUID}.tls=true"
      - "traefik.http.routers.https-0-{UUID}.tls.certresolver=letsencrypt"
      - "traefik.http.services.http-0-{UUID}.loadbalancer.server.port=8000"
      - "traefik.http.services.https-0-{UUID}.loadbalancer.server.port=8000"
```

Remplacer `{UUID}` par l'UUID Coolify de l'app et `{domaine}` par le FQDN.

### Créer une app dockercompose dans Coolify via DB

L'API `/api/v1/applications` retourne 404 pour les apps dockercompose. Contournement : insertion directe en base, en 3 étapes obligatoires — une manquante = crash silencieux au déploiement.

**Étape 1 — Créer l'application** (voir scripts précédents dans l'historique git)

**Étape 2 — Corriger source_type** (sinon : "disable_build_cache on null")
```sql
UPDATE applications SET source_type='App\Models\GithubApp', source_id=0 WHERE uuid='{UUID}';
```

**Étape 3 — Créer ApplicationSettings** (sinon : "Cannot assign null to property $disableBuildCache")
```sql
INSERT INTO application_settings (application_id, created_at, updated_at)
SELECT id, NOW(), NOW() FROM applications WHERE uuid='{UUID}';
```

Puis dispatcher le premier déploiement via `php artisan tinker` :
```php
$app = \App\Models\Application::where('uuid', '{UUID}')->first();
\App\Jobs\ApplicationDeploymentJob::dispatch(application_deployment_queue_id: $deploymentId, ...);
```

### Playwright sur Debian Trixie (Python 3.12-slim)

`playwright install-deps chromium` échoue sur Debian 13 Trixie — les paquets `ttf-unifont` et `ttf-ubuntu-font-family` ont été renommés. **Ne pas utiliser `install-deps`**.

À la place, installer manuellement les dépendances Chromium avec les noms Trixie corrects (suffixe `t64` pour les libs 64-bit, `fonts-unifont` et `fonts-liberation`). Voir le Dockerfile de `projects/ev-prices/` comme référence.

### UUIDs des applications Coolify

| Application | UUID |
|---|---|
| assistant-ia | `gayg5mw9jikbio2le75olq8b` |
| bank-review | `ji9jg7ngkva7j4d2uic05d3v` |
| portfolio-backend | `portfoliobackend00000000` |
| portfolio-frontend | `portfoliofrontend0000000` |
| hub (homepage) | `h7dyrhas03di7jqq2wl2j72z` |
| tool-file-intake | `c57oryka5cw4scy02fi1gfzz` |
| ev-prices | `ev0prices0000000000000000` |

### Déclencher un rebuild — méthode fiable (PHP script)

**Méthode directe sans token API** — fonctionne toujours, vérifié 2026-05-03.

Créer un fichier `/tmp/deploy.php` et l'exécuter dans le container Coolify :

```bash
cat > /tmp/deploy.php << 'EOF'
<?php
require '/var/www/html/vendor/autoload.php';
$app = require '/var/www/html/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();

// Remplacer par les UUIDs voulus (voir table UUIDs ci-dessus)
$uuids = ['portfoliofrontend0000000', 'portfoliobackend00000000'];

foreach ($uuids as $uuid) {
    $application = App\Models\Application::where('uuid', $uuid)->first();
    if (!$application) { echo "Not found: $uuid\n"; continue; }

    $deployment = App\Models\ApplicationDeploymentQueue::create([
        'application_id'   => $application->id,
        'application_name' => $application->name,
        'server_id'        => $application->destination->server->id,
        'destination_id'   => $application->destination_id,
        'deployment_uuid'  => \Illuminate\Support\Str::uuid(), // obligatoire, NOT NULL
        'git_type'         => 'commit',
        'commit'           => 'HEAD',  // ou le SHA git exact
        'status'           => 'queued',
    ]);

    // dispatch() prend l'ID (int), PAS le modèle
    App\Jobs\ApplicationDeploymentJob::dispatch($deployment->id)->onQueue('high');
    echo "Queued: {$application->name} => deployment #{$deployment->id}\n";
}
EOF

docker cp /tmp/deploy.php coolify:/tmp/deploy.php
docker exec coolify php /tmp/deploy.php
```

**Pièges critiques :**
- `deployment_uuid` est `NOT NULL` — l'omettre crash silencieusement
- `ApplicationDeploymentJob::dispatch()` prend un **int** (l'ID), pas le modèle — sinon `TypeError`
- `onQueue('high')` est obligatoire pour que le job soit pris en charge

### Surveiller le déploiement (sans token API)

```bash
# Récupérer les IDs retournés par deploy.php, puis :
until ! docker exec coolify-db psql -U coolify -d coolify -t -c \
  "SELECT 1 FROM application_deployment_queues WHERE id IN (92,93) AND status IN ('queued','in_progress')" \
  | grep -q "1"; do
  echo "$(date +%H:%M:%S) — en cours..."; sleep 15
done

docker exec coolify-db psql -U coolify -d coolify -c \
  "SELECT id, application_name, status FROM application_deployment_queues WHERE id IN (92,93);"
# status = "finished" ✅ | "error" / "failed" ❌
```

### Méthode alternative — API avec token généré

**Pourquoi les tokens en DB ne fonctionnent pas directement :**
Les valeurs dans `personal_access_tokens.token` sont des hash SHA-256. Le format Bearer
attendu par l'API est `{id}|{raw_token}` (jamais le hash brut).

Pour créer un token valide :
```bash
NEW_TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(32))")
NEW_HASH=$(python3 -c "import hashlib; print(hashlib.sha256('$NEW_TOKEN'.encode()).hexdigest())")
docker exec coolify-db sh -c "psql -U coolify coolify -c \"INSERT INTO personal_access_tokens \
  (tokenable_type, tokenable_id, name, token, abilities, team_id, created_at, updated_at) \
  SELECT 'App\\\\Models\\\\User', tokenable_id, 'script', '$NEW_HASH', '[\\\"*\\\"]', 0, NOW(), NOW() \
  FROM personal_access_tokens WHERE id=1;\""
NEW_ID=$(docker exec coolify-db sh -c \
  "psql -U coolify coolify -t -c \"SELECT id FROM personal_access_tokens ORDER BY id DESC LIMIT 1;\"" \
  | tr -d ' ')
TOKEN="${NEW_ID}|${NEW_TOKEN}"
echo "Bearer $TOKEN"
```

Puis utiliser ce token :
```bash
# Déclencher un rebuild
curl -s -X GET "http://localhost:8000/api/v1/deploy?uuid={uuid}&force=false" \
  -H "Authorization: Bearer $TOKEN"
# Retourne : {"deployments":[{"deployment_uuid":"..."}]}

# Vérifier le statut
curl -s "http://localhost:8000/api/v1/deployments/{deployment_uuid}" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status'))"
# "finished" ✅ | "failed" ❌
```

**Note :** Préférer la méthode PHP (plus haut) — elle ne dépend pas de la génération d'un token.

## Sécurité — règles obligatoires

### Docker : exposition des ports
Les services internes (BDD, cache, queues) ne doivent JAMAIS être publiés sur `0.0.0.0`.
Toujours préfixer par `127.0.0.1` dans docker-compose.yml :
```yaml
ports:
  - '127.0.0.1:6379:6379'   # ✅ localhost uniquement
  - '6379:6379'              # ❌ exposé sur Internet
```

### Authentification obligatoire
- Redis : toujours démarrer avec `command: redis-server --requirepass ${REDIS_PASSWORD}`
- PostgreSQL : remplacer `CHANGE_ME_STRONG_PASSWORD` avant tout déploiement
- Ne jamais committer de credentials réels — utiliser `.env` (hors git)

### Pare-feu (UFW)
Après tout ajout de service réseau, vérifier que le port n'est pas ouvert :
```bash
ufw status | grep <PORT>
```
Les ports internes (5432, 6379, etc.) doivent avoir une règle `DENY` explicite.

### `convertDockerRunToCompose` — patch `-v` volumes (2026-05-31)

La fonction `convertDockerRunToCompose` dans `/var/www/html/bootstrap/helpers/docker.php`
ignore les flags `-v host:container` (seuls les flags `--` longs sont gérés).

**Patch appliqué** — ajout avant le `return $compose_options->toArray()` :
```php
// Handle -v / --volume (not covered by the -- mapping above)
preg_match_all('/-v\s+(\S+)/', $custom_docker_run_options ?? '', $vol_matches);
if (! empty($vol_matches[1])) {
    $existing = $compose_options->get('volumes', []);
    $compose_options->put('volumes', array_merge($existing, $vol_matches[1]));
}
```

**Risque** : une mise à jour de Coolify écrase ce fichier. Après toute update, vérifier :
```bash
docker exec coolify grep "Handle -v / --volume" /var/www/html/bootstrap/helpers/docker.php
```
Si absent, ré-appliquer le patch (copier le fichier hors du container, éditer, recopy).

**Impact actuel** : `portfolio-backend` utilise `-v .../feedback-tickets:/app/feedback-tickets`
dans `custom_docker_run_options` (DB Coolify). Sans ce patch, le volume n'est pas monté.

### `coolify-realtime` — image patchée manuellement

L'image `coolify-realtime` (soketi) contient des vulnérabilités npm (mysql2, basic-ftp,
form-data, systeminformation). Elle a été patchée le 2026-04-23 :
- Image committée : `ghcr.io/coollabsio/coolify-realtime:1.0.13-patched`
- Référencée dans `/data/coolify/source/docker-compose.prod.yml`

**Risque** : Une mise à jour de Coolify écrase `docker-compose.prod.yml` et rétablit
l'image originale vulnérable. Après toute update Coolify, vérifier :
```bash
grep "coolify-realtime" /data/coolify/source/docker-compose.prod.yml
```
Si l'image est repassée à `1.0.13` (sans `-patched`), relancer le patch ou attendre
une image upstream corrigée.

### Modifier `post_deployment_command` via l'API

Toujours utiliser Python pour construire le payload JSON — curl échoue silencieusement
si la commande contient des guillemets (le JSON est tronqué sans erreur) :

```python
import urllib.request, json

TOKEN = "..."
payload = json.dumps({"post_deployment_command": "ma commande ici"}).encode()
req = urllib.request.Request(
    "http://localhost:8000/api/v1/applications/{uuid}",
    data=payload,
    headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    method="PATCH",
)
with urllib.request.urlopen(req) as r:
    print(json.loads(r.read()))
```

### Checklist avant déploiement d'un service réseau
- [ ] Port bindé sur `127.0.0.1` si usage interne uniquement
- [ ] Authentification configurée
- [ ] UFW : port bloqué ou justification documentée si ouvert
- [ ] Pas de mot de passe placeholder dans les fichiers committés
