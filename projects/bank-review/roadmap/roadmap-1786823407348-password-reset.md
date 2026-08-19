---
id: roadmap-1786823407348
status: to-refine
created: 2026-08-19T10:25:00Z
project: bank-review
source_ticket: 1786823407348
---

## Mot de passe oublié (self-service reset)

### Direction / Feature (utilisateur)
Sur la page d'accueil (login), offrir un outil « mot de passe oublié » : un utilisateur qui
ne se souvient plus de son mot de passe peut le réinitialiser lui-même. L'utilisateur note que
« ça veut probablement dire avoir un serveur mail sur le VPS ».

### Décision de session (2026-08-19)
**Reporté en roadmap** — feature non priorisée et transverse (dépend d'un transport email).
Ticket #1786823407348 passé `blocked`. Aucune implémentation cette session.

### Contexte technique (état actuel)
- Auth multi-tenant : table `users(id, username UNIQUE, password_hash, db_name, is_admin,
  is_active, created_at)` dans `db_bank` — voir `create_users_table()` dans `services/database.py`.
- Login par **username** + bcrypt (`routes/auth.py`). **Pas de colonne `email`** aujourd'hui.
- Petit nombre d'utilisateurs de confiance (2–5), cf. roadmap multi-tenant.

### Points à trancher avant de générer des tickets

1. **Transport email — ne PAS auto-héberger un serveur mail.**
   Monter un Postfix/serveur SMTP sur le VPS est disproportionné pour 2–5 utilisateurs :
   gestion SPF/DKIM/DMARC, réputation IP, risque de finir en spam, surface d'attaque.
   Reco : **relais SMTP d'un compte existant** (mailbox.org, déjà utilisé comme backend de
   connaissance selon le CLAUDE.md racine) via `smtplib` + STARTTLS, ou un provider
   transactionnel (Resend/Mailgun) si on veut découpler.
   → Décision utilisateur requise : quel compte/relais SMTP, quelle adresse expéditrice.

2. **Collecte des emails.** La table `users` n'a pas d'email. Prérequis : ajouter une colonne
   `email` (migration idempotente, admin) + saisie de l'email dans l'admin `/admin/users`
   (et/ou un écran « renseignez votre email » au premier login). Sans email vérifié par compte,
   le reset est impossible.

3. **Alternative sans email (à considérer).** Vu le très petit nombre d'utilisateurs de confiance,
   un **reset par l'admin** (bouton « réinitialiser le mot de passe » dans `/admin/users` qui
   génère un mot de passe temporaire communiqué hors-bande) couvre 80 % du besoin sans aucune
   infra email. À arbitrer avec l'utilisateur : self-service email vs reset admin.

### Esquisse de flux (si self-service email retenu)
```
Login → lien « Mot de passe oublié ? »
  → saisie email → lookup users.email
  → génère token aléatoire (secrets.token_urlsafe), stocké hashé en DB avec TTL (~30 min)
     table password_reset_tokens(user_id, token_hash, expires_at, used_at)
  → email via SMTP (STARTTLS) contenant lien /reset?token=…
  → page /reset : vérifie token non expiré/non utilisé → nouveau mot de passe (bcrypt) → marque used_at
Sécurité : réponse identique que l'email existe ou non (anti-énumération) ; rate-limit ;
tokens à usage unique ; invalider les autres tokens du user au succès.
```

### Prochaine étape
Session dédiée : trancher points 1–3 avec l'utilisateur, puis générer les tickets
(migration email, transport SMTP, endpoints /forgot + /reset, page login, sécurité/rate-limit).
