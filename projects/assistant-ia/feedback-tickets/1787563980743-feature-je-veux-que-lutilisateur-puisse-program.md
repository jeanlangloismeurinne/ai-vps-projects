---
id: 1787563980743
type: feature
status: closed
priority: medium
date: 2026-08-24T09:33:00.743346
project: assistant-ia
url: 
milestone: agent-outillage
closed_at: 2026-08-24T19:12:25+00:00
---

## ✨ Feature

**Date** : 24/08/2026 09:33
**URL** : `N/A`

### Description

Je veux que l'utilisateur puisse programmer l'envoi de rappels ou messages en utilisant l'assistant. Le classifieur doit donc détecter si le message demande un rappel et le programmer en confirmant succinctement. L'utilisateur doit pouvoir accéder à une page web sur laquelle sont présents tous les rappels qu'il a fixé pour pouvoir les éditer. Le projet Kanban est une bonne base pour constituer ce registre de tâches / ce lieu de visualisation ou édition. Charge à l'assistant d'organiser le Kanban de façon cohérente.

### Notes d'implémentation

- **2026-08-24 — clarifié en séance, puis décomposé.** Ce ticket devient l'**ombrelle** du volet
  « rappels » ; il se ferme quand ses dérivés sont livrés.
- **Ce qui existe déjà** : `cards.due_date` + `reminder_sent_at` (`migrations/001_initial.sql:40`),
  le job d'envoi (`app/jobs/task_reminder.py`, cron chaque minute), et la page web d'édition
  demandée — c'est `/kanban` (`app/routes/kanban.py:47`). **Rien à construire de ce côté.**
- **Ce qui manque** : la détection d'intention et l'écriture depuis l'agent. Or programmer un rappel
  = **créer une carte en base** = un effet de bord, ce que le modèle de sécurité v1 exclut
  (`agent_chat.py:130` — « l'agent n'a aucun outil en v1 »). Le ticket franchit donc la même limite
  que l'accès web `#1787575860968` → roadmap commune : **`roadmap/agent-outillage.md`**.
- **Garde-fou tranché en séance** : *action codée + confirmation a posteriori*. Le modèle n'extrait
  que `title` + une expression de date sous JSON schema strict ; board, colonne et canal sont fixés
  en Python. Confirmation courte dans le fil avec bouton « annuler ». Justification du régime
  (vs. approbation préalable pour les diffs de doc) : roadmap §3.3.
- **Défaut trouvé au passage** : `get_cards_due_now()` (`app/services/kanban.py:156`) ne regarde que
  la minute courante — un rappel dû pendant un redéploiement est **perdu définitivement**. Extrait
  en `#1787579840500`, à corriger avant de bâtir dessus.
- Dérivés : `1787579840500` · `1787579840503` · `1787579840504` · `1787579840505`
  (prérequis boucle : `1787579840501` → `1787579840502`).
