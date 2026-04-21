# CLAUDE.md — ai-vps-projects

## Contexte global
Repo multi-projets sur VPS Hetzner (204.168.250.110).
Domaine : jlmvpscode.duckdns.org
Déploiement : Coolify — chaque projet est une application séparée.

## Infrastructure partagée
- PostgreSQL 16 : shared-postgres (port 5432)
  Bases : db_assistant (projet assistant-ia)
- Redis 7 : shared-redis (port 6379)
- Réseau Docker : infra-net

## Projets actifs
- projects/assistant-ia/ : bot Slack + résumé newsletters
- projects/bank-review/ : analyse de relevés bancaires (upload Excel/CSV + analyse Claude) — Python 3.12, FastAPI, pandas
- projects/feedback-module/ : microservice feedback (port 3333) — widget flottant + API + stockage Markdown

## Feedback utilisateur

Les tickets (bugs, suggestions, features) sont stockés dans le dossier
`feedback-tickets/` de chaque projet concerné, au format Markdown.

Pour bank-review : `projects/bank-review/feedback-tickets/`

Chaque fichier = un ticket. Champ `status: open` = en attente de traitement.
Marquer `status: closed` une fois résolu.

## Ajouter un projet
1. Créer projects/nouveau-projet/
2. Créer la base : docker exec shared-postgres psql -U admin -c 'CREATE DATABASE db_nouveau;'
3. Créer une app Coolify avec Base Directory = projects/nouveau-projet
4. Documenter ici

## Stack commune
Node.js 20, TypeScript strict, Fastify, Docker
