---
id: 1786799400000
type: feature
status: open
priority: high
date: 2026-08-15T00:00:00Z
project: bank-review
milestone: multi-tenant
---

## ✨ Feature — Multi-tenant étape 2 : pool DB par utilisateur

### Description

Modifier la couche d'accès DB pour utiliser la base de l'utilisateur connecté au lieu de `DATABASE_URL` global :
- `get_pool(db_url)` accepte une URL optionnelle, garde un pool par URL
- Middleware FastAPI qui injecte `request.state.db_url` depuis la session
- Toutes les routes existantes lisent `request.state.db_url` pour acquérir leur connexion
- `bank_formats` reste dans `db_bank` (base centrale) — connexion séparée via `DATABASE_URL`

### Fichiers à modifier
- `app/services/database.py` — pool dict keyed par db_url, `get_pool(db_url=None)`
- `app/main.py` — ajouter middleware session → request.state.db_url
- `app/routes/*.py` — passer `request.state.db_url` aux appels DB (ou via dépendance FastAPI)

### Notes d'implémentation
- Pattern pool : `_pools: dict[str, asyncpg.Pool] = {}` avec `_pools.setdefault(db_url, await create_pool(...))`
- Alternative plus propre : dépendance FastAPI `get_db_url(request: Request)` injectée dans les routes
- Ne pas créer de pool pour les routes non-authentifiées (login, feedback)
