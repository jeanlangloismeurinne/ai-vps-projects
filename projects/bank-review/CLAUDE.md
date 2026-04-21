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

## Développement local

```bash
# Tunnel SSH pour accéder au serveur depuis son poste
ssh -L 8080:localhost:8080 root@204.168.250.110

# Démarrer le serveur (sur le VPS)
cd /root/ai-vps-projects/projects/bank-review
/root/bank-venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Le venv Python est à `/root/bank-venv/` sur le VPS.

## Architecture

```
app/
  main.py              # FastAPI, montage des routers
  templates_env.py     # Instance Jinja2 PARTAGÉE — voir section pièges
  routes/
    auth.py            # Login/logout, session itsdangerous
    upload.py          # Upload Excel/CSV + aperçu
    analyze.py         # Analyse Claude sur fichier uploadé
    import_route.py    # Pipeline import mensuel
    budget.py          # Suivi budget + tous les endpoints /api/budget/* et /api/transactions/*
  services/
    classifier.py      # Règles + Claude (Haiku) avec prompt caching
    deduplicator.py    # Normalisation label/montant, calcul dedup_key
    database.py        # Pool asyncpg, helpers DB
    importer.py        # Orchestration pipeline import
    format_checker.py  # Vérification/remapping colonnes CSV entrant
    budget.py          # Agrégation actuals, vue budget, CRUD catégories
  templates/
    base.html          # Layout commun, nav, toggle dark/light
    budget.html        # Tableau budget + modals drill-down et catégories
    ...
```

## Stack

- Python 3.12 / FastAPI / uvicorn
- asyncpg (PostgreSQL `db_bank` sur `shared-postgres:5432`)
- Jinja2 (templates SSR)
- pandas / openpyxl (parsing fichiers)
- Anthropic SDK — modèle `claude-haiku-4-5-20251001` avec prompt caching
- Auth : session cookie via `itsdangerous` (pas de JWT)

## Base de données

Tables principales :
- `transactions` — toutes les opérations bancaires, source de vérité
- `budget_lines` — budget mensuel par catégorie et par année fiscale
- `budget_years` — années fiscales Sep→Août
- `categories` — référentiel des noms de catégories (**FK source**)
- `accounts` — comptes bancaires

`dedup_key` = `date_op[:10]|normalized_label|amount` — contrainte UNIQUE sur `transactions`.

## Conventions métier

### Années fiscales
Les onglets "suivi budget" (`budget_years`) sont des **années fiscales Sep 1 → Août 31**, pas des années calendaires.
Ex : `2024-2025` = 2024-09-01 → 2025-08-31. Le label suit le pattern `YYYY-YYYY`.

Toute création automatique de période doit prolonger la dernière en utilisant `end_date + 1 jour` comme `start_date`, et conserver la même durée que la période précédente.

### Normalisation des labels
Les exports CSV ont le format `"Libellé lisible | CANONICAL_MAJUSCULES"`.
**La partie normalisée est toujours celle APRÈS le pipe.** C'est critique pour que les dedup_key correspondent entre exports et données historiques.

Autres transformations dans `deduplicator.normalize_label()` : suppression `CARTE DD/MM/YY`, `PRLV SEPA`, `VIR INST`, suffixe `CB*XXXX`, passage en majuscules.

### Catégories — contrainte FK critique
`transactions.category` a une FK vers `categories(name)`.  
**Ne jamais modifier `budget_lines.category` directement.** Un renommage doit passer par `budget.rename_budget_category()` qui cascade en transaction : `categories` → `budget_lines` (toutes années) → `transactions`. Faire autrement viole la contrainte FK ou laisse des transactions orphelines.

### Classifier Claude
- Modèle : `claude-haiku-4-5-20251001` — ne pas passer à Sonnet sans évaluer le coût token.
- L'historique est transmis comme index compact `{catégorie: [marchands]}`, pas comme lignes CSV brutes.
- Prompt caching activé sur le bloc statique (`cache_control: {"type": "ephemeral"}`).
- Réponse compacte attendue : `{"c": catégorie, "p": confiance}`.

## Pièges connus

### Jinja2 — instance partagée obligatoire
Toutes les routes importent `templates` depuis `app/templates_env.py`.  
**Ne pas créer une nouvelle instance `Jinja2Templates()` dans un route.** La fonction globale `m_status` (utilisée dans `budget.html`) est enregistrée sur cette instance unique — une nouvelle instance ne l'aurait pas.

### `onclick` et `tojson` en Jinja2
`{{ value|tojson }}` produit des guillemets doubles `"` qui cassent un attribut `onclick="..."`.  
**Pattern correct** : utiliser des attributs `data-*` et les lire via `this.dataset.*` dans le handler JS.

```html
<!-- ✗ Casse l'attribut HTML -->
onclick="openDrillDown({{ cat.category|tojson }}, {{ m.month|tojson }})"

<!-- ✓ Correct -->
data-cat="{{ cat.category|e }}" data-month="{{ m.month }}"
onclick="openDrillDown(this.dataset.cat, this.dataset.month)"
```

### asyncpg et pandas NaT
`pandas.NaT` passé à asyncpg provoque un crash. Toujours vérifier `if pd.isna(d): return None` avant d'insérer une date issue d'un DataFrame.

### Montants avec espace comme séparateur de milliers
`normalize_amount()` doit gérer `-1 442.00` (espace) et `-1 442,00` (virgule + espace).
Le `.replace(" ", "").replace("\u00a0", "")` doit précéder le `.replace(",", ".")`.

## Workflow de déploiement production

Le repo source Coolify est **GitHub** (`jeanlangloismeurinne/ai-vps-projects`, branche `main`).
Un rebuild Coolify sans push GitHub préalable redéploie l'ancienne version.

Ordre obligatoire :
1. `git push origin main`
2. Déclencher le rebuild via l'API Coolify :

```bash
curl -s -X POST "http://localhost:8000/api/v1/applications/ji9jg7ngkva7j4d2uic05d3v/start" \
  -H "Authorization: Bearer {id}|{token}"
```

Attendre `status: finished` avant de valider en prod.

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

## Données historiques

`scripts/migrate_historical.py` a déjà été exécuté (4 413 lignes → 4 366 insérées, 47 doublons ignorés). **Ne pas le relancer** — provoquerait des tentatives d'insertion dupliquées (bloquées par ON CONFLICT, mais inutile).
