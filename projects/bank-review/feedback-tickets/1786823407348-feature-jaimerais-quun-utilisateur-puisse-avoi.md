---
id: 1786823407348
type: feature
status: blocked
date: 2026-08-15T19:50:07.348701
project: bank-review
url: https://bank.jlmvpscode.duckdns.org/admin/users
---

## ✨ Feature

**Date** : 15/08/2026 19:50
**URL** : `https://bank.jlmvpscode.duckdns.org/admin/users`

### Description

J’aimerais qu’un utilisateur puisse avoir accès à un outil « mot de passe oublié » sur la page d’accueil si jamais il ne se souvient plus de son mot de passe. Ça veut probablement dire avoir un serveur mail sur le VPS.

### Contexte

- **User-Agent** : Mozilla/5.0 (iPad; CPU OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.5 Mobile/15E148 Safari/604.1

### Notes d'implémentation

**Bloqué (2026-08-19)** — dépend d'un choix de transport email + collecte des emails (la table
`users` n'a pas de colonne `email`). Ne pas auto-héberger un serveur mail. Décision reportée en
roadmap : `roadmap/roadmap-1786823407348-password-reset.md` (options : reset self-service par SMTP
mailbox.org vs reset par l'admin sans email). À rouvrir après arbitrage utilisateur.
