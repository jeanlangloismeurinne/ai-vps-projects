---
id: roadmap-1780900000000
status: tickets-created
created: 2026-08-15T00:00:00Z
project: bank-review
source_ticket: 1777667797438
---

## Multi-tenant : comptes isolés par utilisateur

### Direction / Feature (utilisateur)
Créer plusieurs comptes avec identifiant / mot de passe pour accéder au service, chacun avec sa base de données, ses règles, etc. Bref une instance de l'outil pour chaque utilisateur.

### Contraintes connues
- Personnes de confiance uniquement (2–5 utilisateurs) — pas une plateforme publique
- Bases de données isolées par utilisateur (formulation explicite de l'utilisateur)
- L'architecture doit pouvoir se répliquer pour d'autres services (horizon-scan, etc.)

---

### Spec générée (session 2026-08-15)

#### Décision d'architecture retenue

**Option retenue : databases séparées sur shared-postgres.**

Chaque utilisateur dispose de sa propre base PostgreSQL (`db_bank_jean`, `db_bank_alice`) sur le container `shared-postgres` existant. L'authentification est centralisée dans une table `users` dans `db_bank` (la base actuelle).

*Pourquoi pas les schemas ?* L'utilisateur a explicitement formulé "bases de données isolées". Des schemas séparés sur la même DB sont techniquement équivalents mais moins intuitifs à maintenir, à sauvegarder et à réinitialiser indépendamment.

*Pourquoi pas plusieurs instances Coolify ?* Trop lourd à maintenir pour 2–5 personnes.

#### Architecture détaillée

**Table `users` (dans `db_bank`, schema `public`) :**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,     -- bcrypt, $2b$12$...
    db_name TEXT NOT NULL,           -- ex: db_bank_jean
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);
```

**Par utilisateur, au moment de la création du compte :**
1. `CREATE DATABASE db_bank_{username};`
2. `CREATE USER bank_{username} WITH PASSWORD '...';`
3. `GRANT ALL PRIVILEGES ON DATABASE db_bank_{username} TO bank_{username};`
4. Exécuter toutes les migrations (CREATE TABLE) dans `db_bank_{username}`

**Authentification (auth.py) :**
- Remplacer la vérification `APP_PASSWORD` (single-user) par lookup `users` table
- Formulaire de login : ajouter champ `username`
- Session cookie (itsdangerous existant) : ajouter `user_id` + `db_url` dans le payload

**Connexion DB par requête :**
- `database.py` : `get_pool()` doit accepter un `db_url` optionnel
- Chaque requête authentifiée utilise le pool de sa base (`request.state.db_url`)
- Middleware FastAPI pour injecter `db_url` depuis la session dans `request.state`
- `bank_formats` (table globale de formats) reste dans `db_bank` — accès via connexion admin séparée

#### Migrations

Les migrations existantes (`migrate_classifier_tables()` au startup) doivent être exécutées dans la DB de chaque utilisateur, pas seulement dans `db_bank`.

Solution : créer une fonction `run_migrations(db_url)` appelée lors de la création de compte.

#### Création de compte

Interface admin simple (`/admin/users`) accessible uniquement avec un `ADMIN_PASSWORD` env var séparé.
- Formulaire : username, password, confirmation
- Crée la DB, crée l'utilisateur PG, exécute les migrations
- Pas de self-registration

#### Hors-scope (pour cette itération)
- Transfer de données entre comptes
- Partage de formats (`bank_formats`) entre utilisateurs (ils auront chacun leur table)
- Récupération de mot de passe (mot de passe admin peut le réinitialiser)
- Rate limiting / protection brute-force

### Tickets créés
- `#1786799300000` — étape 1 : table users + auth multi-comptes (priority: high)
- `#1786799400000` — étape 2 : pool DB par utilisateur (priority: high)
- `#1786799500000` — étape 3 : création de compte + interface admin (priority: medium)
