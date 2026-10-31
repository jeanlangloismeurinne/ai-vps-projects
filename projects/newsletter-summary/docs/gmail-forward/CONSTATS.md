# Constats de la phase 0 (audit du VPS, 2026-10-31)

| # | Question de la spec | Constat |
| --- | --- | --- |
| 1 | Pile | FastAPI + SQLAlchemy async + Postgres (`db_newsletter`), APScheduler. Hub : FastAPI, pages HTML générées en Python. |
| 2 | Authentification de l'interface | Hub : login + cookie `hub_session` (SameSite=lax), pas de CSRF ni de limite d'essais à l'origine. **Ajoutés par ce chantier** : jeton CSRF (HMAC du cookie de session) sur toute écriture Gmail, 429 après 5 échecs de login par IP en 10 min. Côté newsletter-summary, les routes `/api/gmail/*` exigent `HUB_API_TOKEN` (503 s'il est vide, contrairement au reste de l'API). |
| 3 | Secrets | `.env` local chmod 600, gitignored. `GMAIL_SCRIPT_SECRET` et `GMAIL_SCRIPT_URL` y vont ; jamais journalisés (filtre de log sur httpx, test G16). |
| 4 | Réception Resend | Domaine `oozeenaru.resend.app` en place ; webhook `email.received` traité par newsletter-summary, corps récupéré via le gateway. Alias = moteur d'alias existant. |
| 5 | Alertes | Via `comms_client` (gateway), comme les digests. |

Le reste (points 6 à 10 de la spec : scope de lecture des adresses de transfert, `from` au format `@domaine`, accès anonyme à l'URL, quotas, forme des erreurs Gmail, `negatedQuery` avec `OR`) **n'est pas constatable sans compte Gmail** : voir `RECETTE.md`.
