# CLAUDE.md — bank-review

## Déploiement

- Plateforme : Coolify (http://jlmvpscode.duckdns.org:8000)
- Projet Coolify : `bank-review` (uuid `xfomht7ul2kd3iljq9xphpii`)
- App uuid : `ji9jg7ngkva7j4d2uic05d3v`
- Base Directory Coolify : `/projects/bank-review`
- Domaine production : https://bank.jlmvpscode.duckdns.org
- Réseau Docker : `coolify` (shared-postgres et shared-redis y sont connectés)

Variables d'environnement requises (configurées dans Coolify) :
- `DATABASE_URL` → `postgresql://bank:bank_secure_pwd@shared-postgres:5432/db_bank`
- `ANTHROPIC_API_KEY`
- `SECRET_KEY` (token hex 32 bytes)
- `APP_PASSWORD`

## API Coolify

Le token stocké en DB (`personal_access_tokens.token`) est un hash SHA-256 — inutilisable directement.
Pour créer un token utilisable :

```bash
NEW_TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(32))")
NEW_HASH=$(python3 -c "import hashlib; print(hashlib.sha256('$NEW_TOKEN'.encode()).hexdigest())")
docker exec coolify-db sh -c "psql -U coolify coolify -c \"INSERT INTO personal_access_tokens (tokenable_type, tokenable_id, name, token, abilities, team_id, created_at, updated_at) SELECT 'App\\\\Models\\\\User', tokenable_id, 'script', '$NEW_HASH', '[\\\"*\\\"]', 0, NOW(), NOW() FROM personal_access_tokens WHERE id=1;\""
NEW_ID=$(docker exec coolify-db sh -c "psql -U coolify coolify -t -c \"SELECT id FROM personal_access_tokens ORDER BY id DESC LIMIT 1;\"" | tr -d ' ')
echo "Bearer ${NEW_ID}|${NEW_TOKEN}"
```

Utilisation : `curl -H "Authorization: Bearer {id}|{token}" http://localhost:8000/api/v1/...`

## Dépendances sensibles

- `anthropic` doit rester à `>=0.40` : les versions <0.40 utilisent l'argument `proxies`
  supprimé dans `httpx>=0.28`, ce qui provoque un crash au démarrage du container.

## Conventions métier

### Années fiscales
Les onglets "suivi budget" (`budget_years`) sont des **années fiscales Sep 1 → Août 31**, pas des années calendaires.
Ex : `2024-2025` = 2024-09-01 → 2025-08-31. Le label suit le pattern `YYYY-YYYY`.

Toute création automatique de période doit prolonger la dernière en utilisant `end_date + 1 jour` comme `start_date`, et conserver la même durée que la période précédente.
