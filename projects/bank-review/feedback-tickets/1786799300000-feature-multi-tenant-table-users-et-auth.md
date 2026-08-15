---
id: 1786799300000
type: feature
status: open
priority: high
date: 2026-08-15T00:00:00Z
project: bank-review
milestone: multi-tenant
---

## ✨ Feature — Multi-tenant étape 1 : table users + auth multi-comptes

### Description

Remplacer l'authentification mono-utilisateur (`APP_PASSWORD`) par un système multi-comptes :
- Table `users` dans `db_bank` avec `username`, `password_hash` (bcrypt), `db_name`
- Formulaire de login modifié : champ `username` + `password`
- Session cookie existant (itsdangerous) étendu avec `user_id` et `db_url`
- Variables d'env : `APP_PASSWORD` devient `ADMIN_PASSWORD` pour l'interface admin

### Fichiers à modifier
- `app/routes/auth.py` — login handler + vérification session
- `app/templates/login.html` — ajouter champ username
- `app/services/database.py` — requête lookup users table
- `app/main.py` — migration startup pour créer table users si absente

### Migration SQL
```sql
-- dans db_bank
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    db_name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);
```

### Notes d'implémentation
- Utiliser `bcrypt` (ajouter au requirements.txt) ou `passlib[bcrypt]`
- La session doit stocker `{"user_id": X, "db_url": "postgresql://bank_jean:pwd@shared-postgres:5432/db_bank_jean"}`
- L'utilisateur initial (Jean) est créé via `ADMIN_PASSWORD` lors du premier lancement si aucun user n'existe
