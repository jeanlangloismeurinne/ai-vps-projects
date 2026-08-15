---
id: 1786799500000
type: feature
status: closed
closed_at: 2026-08-15T00:00:00Z
priority: medium
date: 2026-08-15T00:00:00Z
project: bank-review
milestone: multi-tenant
---

## ✨ Feature — Multi-tenant étape 3 : création de compte + interface admin

### Description

Interface admin minimale pour créer/gérer les comptes utilisateurs :
- Route `/admin/users` pour les utilisateurs avec la responsabilité d’administrateur (Jean uniquement pour commencer)
- Création de compte : choisir username + mot de passe → créer DB PostgreSQL + migrations + entrée users table
- Liste des comptes existants avec date de création et nom de DB

### Comportement de création de compte
1. Valider username (alphanumérique, pas déjà pris)
2. `CREATE DATABASE db_bank_{username} OWNER bank;` (connexion admin)
3. Exécuter migrations complètes dans la nouvelle DB (toutes les CREATE TABLE)
4. Insérer dans `users` table (db_bank) avec hash bcrypt du mot de passe

### Fichiers à créer/modifier
- `app/routes/admin.py` (nouveau) — routes `/admin/users` GET + POST
- `app/templates/admin_users.html` (nouveau) — formulaire + liste
- `app/main.py` — monter le router admin

### Notes d'implémentation
- si un utilisateur est admin il accède à la vue admin à travers son propre compte 
- Les migrations sont dans `app/main.py` (startup) — extraire en fonction `run_all_migrations(db_url)` réutilisable
- Les mots de passe admin DB (pour créer la DB et l'user PG) sont dans `POSTGRES_ADMIN_URL` (nouvelle env var)