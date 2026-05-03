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
    analyze.py         # Analyse Claude ad-hoc sur fichier uploadé (Sonnet)
    import_route.py    # Pipeline import mensuel
    budget.py          # Suivi budget + tous les endpoints /api/budget/* et /api/transactions/*
    feedback.py        # Tickets bug/feature/suggestion → feedback-tickets/*.md + TICKETS.md
  services/
    classifier.py      # Règles + Claude (Haiku) avec prompt caching
    deduplicator.py    # Normalisation label/montant, calcul dedup_key
    database.py        # Pool asyncpg, helpers DB
    importer.py        # Orchestration pipeline import
    format_checker.py  # Vérification/remapping colonnes CSV entrant
    file_parser.py     # Lecture Excel/CSV via pandas
    budget.py          # Agrégation actuals, vue budget, CRUD catégories
    claude_service.py  # Analyse libre de DataFrame via Sonnet (routes/analyze.py)
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
- Anthropic SDK — deux usages distincts :
  - `classifier.py` : `claude-haiku-4-5-20251001` avec prompt caching (classification batch)
  - `claude_service.py` : `claude-sonnet-4-6` sans caching (analyse ad-hoc depuis `analyze.py`)
- Auth : session cookie via `itsdangerous` (pas de JWT)

## Base de données

Tables principales :
- `transactions` — toutes les opérations bancaires, source de vérité
- `budget_lines` — budget mensuel par catégorie et par année fiscale
- `budget_years` — années fiscales Sep→Août
- `categories` — référentiel des noms de catégories (référence soft, plus de FK)
- `accounts` — comptes bancaires
- `classification_rules` — **obsolète, conservée uniquement pour migration initiale** (lue une seule fois par `migrate_classifier_tables()`)
- `classifier_rules` — règles du classifieur : stage (0/2/3), keywords (JSONB array), match_mode (AND/OR), sort_order, is_active, source
- `classifier_snapshots` — versions archivées du classifieur (snapshot_data JSONB), créées avant chaque import et manuellement
- `import_sessions` — une ligne par import confirmé ; `transactions.import_session_id` FK vers cette table

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

### Catégories — pas de FK, renommage isolé par année

`transactions.category` **n'a plus de FK** vers `categories(name)` (supprimée en avril 2026).
`categories` reste une table de référence soft utilisée par le classifier.

**Renommage** : passer par `budget.rename_budget_category(line_id, new_name)`.
Cette fonction est **isolée par année** : elle ne touche qu'aux `budget_lines` de l'année concernée
et aux `transactions` dont `date_op` est dans la plage de cette année.
Les autres années et leurs transactions sont intactes.
Ne jamais faire un UPDATE direct sur `budget_lines.category` sans passer par cette fonction.

### Classifieur — pipeline à étages (depuis mai 2026)

Les règles sont stockées en DB dans `classifier_rules` (plus rien de hardcodé dans `classifier.py`).
La table `classification_rules` (ancienne) est conservée — elle sert uniquement à la migration initiale. Ne pas la supprimer.

Pipeline :
- **Étage 0** (stage=0) : priorités absolues, bypass détection vacances
- **Étage 1** : détection vacances (code fixe dans `classifier.py`)
- **Étage 2** (stage=2) : règles utilisateur
- **Étage 3** (stage=3) : règles prédéfinies (NAVIGO, EDF, LECLERC…)
- **Étage 4** : mapping catégories bancaires (dict `BANK_TO_USER` dans `classifier.py`)
- **Étage 5** : fallback Claude Haiku

Le bouton ⚡ "Toujours classifier ainsi" crée en **étage 0** (source='auto') — intentionnel.

Migration idempotente : `migrate_classifier_tables()` est appelée au startup (`main.py`). Elle ne fait rien si `classifier_rules` n'est pas vide. Snapshots automatiques créés avant chaque import.

### Classifier Claude
- Modèle : `claude-haiku-4-5-20251001` — ne pas passer à Sonnet sans évaluer le coût token.
- L'historique est transmis comme index compact `{catégorie: [marchands]}`, pas comme lignes CSV brutes.
- Prompt caching activé sur le bloc statique (`cache_control: {"type": "ephemeral"}`).
- Réponse compacte attendue : `{"c": catégorie, "p": confiance}`.

## Tickets feedback

Les retours utilisateur sont dans `feedback-tickets/*.md` (un fichier par ticket) et `TICKETS.md` (index auto-généré).

**`TICKETS.md` est regénéré automatiquement** à chaque `POST /api/feedback`. Lire ce fichier en début de session pour voir les bugs/features ouverts. Ne jamais l'éditer manuellement — il sera écrasé.

Fermer un ticket : passer `status: open` → `status: closed` dans le fichier `.md` correspondant dans `feedback-tickets/`, puis appeler `_regenerate_tickets_md()` (ou laisser le prochain POST le régénérer).

## Pièges connus

### Jinja2 — instance partagée obligatoire
Toutes les routes importent `templates` depuis `app/templates_env.py`.  
**Ne pas créer une nouvelle instance `Jinja2Templates()` dans un route.** Les globals et filtres (`m_status`, `fmtnum`, `urlencode`) sont enregistrés sur cette instance unique — une nouvelle instance ne les aurait pas.

`m_status(m, is_income)` retourne la classe CSS de colorisation d'une cellule budget :
- `""` si mois futur ou actual == 0
- `"cell-green"` si variance ≥ 0
- `"cell-yellow"` si variance ≥ -20 % du budget
- `"cell-red"` sinon

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

### Migrations SQL sur shared-postgres

Les fichiers `.sql` locaux ne sont **pas accessibles** dans le container via `-f`. Utiliser `-c` avec le SQL inline.

Les opérations DDL (`ALTER TABLE`, `CREATE TABLE`, `GRANT`) doivent être exécutées en tant qu'`admin`, pas `bank` (bank n'est pas propriétaire des tables) :

```bash
docker exec shared-postgres psql -U admin db_bank -c "ALTER TABLE ..."
# Après CREATE TABLE, penser à :
# GRANT ALL ON new_table TO bank;
# GRANT USAGE, SELECT ON SEQUENCE new_table_id_seq TO bank;
```

### asyncpg — codec JSONB et double encodage

Le pool asyncpg est configuré avec un codec JSONB automatique (`_init_conn` dans `database.py`) :
```python
await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
```

**Règle critique** : ne jamais appeler `json.dumps()` soi-même avant de passer une valeur pour une colonne JSONB. Le codec encode déjà — passer une string JSON produit un double encodage silencieux (la liste est stockée comme une string JSON au lieu d'un array JSON).

```python
# ✗ Double encodage → keywords stockés comme string dans JSONB
await conn.execute("INSERT ... VALUES ($1)", json.dumps(["MOT"]))

# ✓ Correct — passer la liste Python directement
await conn.execute("INSERT ... VALUES ($1)", ["MOT"])
```

### Annotation des transactions avec les règles du classifieur

Toutes les routes qui affichent des transactions avec badge ⚡ utilisent `_annotate_with_rules(txs, rules)` défini dans `routes/budget.py`. Ce helper gère le matching multi-mots-clés AND/OR.

Ne pas recréer le pattern inline — l'ancien `rules_upper = [(r["keyword"]…)]` est obsolète (format single-keyword) et ne doit pas être réintroduit.

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
