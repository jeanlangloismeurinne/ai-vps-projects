# SPEC — Implémentation feedbacks journal (mai 2026)

> À lire en début de session avant toute implémentation.
> Contexte projet : `projects/assistant-ia/` — FastAPI + Slack Bolt (Socket Mode), Python 3.12.

---

## 0. Pré-requis : persistance des tickets après redéploiement

**Problème identifié** : le container actuel a été déployé sans le volume bind-mount
`feedback-tickets`. Les tickets n'existaient que dans le container (perdus à chaque rebuild).

**Résolution déjà effectuée (17/05/2026)** :
- Les 7 tickets ont été copiés du container vers le host :
  `/root/ai-vps-projects/projects/assistant-ia/feedback-tickets/journal/`
- Le `docker-compose.yml` contient déjà la déclaration correcte du volume :
  ```yaml
  - /root/ai-vps-projects/projects/assistant-ia/feedback-tickets:/app/feedback-tickets
  ```

**Action à faire en début de session** : déclencher un rebuild Coolify (méthode PHP dans
`/root/ai-vps-projects/CLAUDE.md` section "Pièges Coolify") pour que le volume soit
activement monté sur le nouveau container.

**Vérification post-rebuild** :
```bash
CONTAINER=$(docker ps --filter "name=assistant" -q | head -1)
docker inspect $CONTAINER --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'
# Doit afficher : /root/.../feedback-tickets -> /app/feedback-tickets
```

---

## 1. Ticket #1778099799092 — Bug "objectif complete" + modification des réponses

**Source** : `feedback-tickets/journal/1778099799092-suggestion-seul-lobjectif--apprentissage--est-af.md`  
**Date** : 06/05/2026 20:36 — **Status** : open

### Description utilisateur
> Seul l'objectif « apprentissage » est affiché comme « complete » alors que j'ai rempli
> les deux objectifs le 6 mai. Est-ce parce que je n'ai pas répondu à toutes les questions ?
> J'aimerais pouvoir modifier mes réponses une fois remplies jusqu'à la fin de la journée.

### Fichiers concernés
- `app/services/journal_v2.py` — logique de complétion des objectifs
- `app/routes/journal_fill.py` — routes de remplissage + endpoint de mise à jour
- `app/routes/journal.py` — affichage et statut des objectifs

### Ce qu'il faut investiguer et corriger

**Bug A — Détection "complete"**
Identifier dans `journal_v2.py` comment un objectif est marqué complet. Vérifier si :
- La logique exige que TOUTES les questions soient répondues (y compris optionnelles)
- Il y a une distinction entre "rempli partiellement" et "complet"
- La session du 6 mai existe bien en base pour les deux objectifs

Corriger la logique de complétion pour qu'un objectif soit marqué `complete` dès lors que
toutes ses questions **obligatoires** ont reçu une réponse.

**Feature B — Modification des réponses**
Permettre à l'utilisateur de modifier ses réponses à un objectif jusqu'à 23h59 le jour même.

Règle : `session_date == today` → formulaire en mode édition (réponses pré-remplies, bouton
"Mettre à jour" au lieu de "Valider"). Après minuit → lecture seule.

Endpoint à modifier ou créer :
- `PUT /journal/fill/{objectif_id}` (ou réutiliser le POST existant en mode upsert)
- En base : `INSERT ... ON CONFLICT (objectif_id, session_date) DO UPDATE SET ...`

---

## 2. Ticket #1778099921788 — Questions journal dans Slack

**Source** : `feedback-tickets/journal/1778099921788-suggestion-jaimerais-que-lassistant-envoie-la-pre.md`  
**Date** : 06/05/2026 20:38 — **Status** : open

### Description utilisateur
> J'aimerais que l'assistant envoie la première question de chaque objectif dans la
> conversation Slack, et que l'utilisateur puisse répondre à cette question avant que
> la suivante ne lui soit posée dans la même conversation. Si la réponse est un texte
> libre, le message suffit. Sinon, le message de l'assistant contient les différentes
> options sous la forme de boutons.

### Comportement attendu (flux complet)

**Déclenchement** : le rappel Slack quotidien (job `journal_prompt.py`) envoie, pour chaque
objectif actif du jour, **un message dans `#journal`** contenant la première question
au lieu (ou en plus) du lien web actuel.

**Enchaînement des questions** :
1. Bot poste Q1 dans `#journal` (ou en thread sur le rappel)
2. L'utilisateur répond :
   - **Texte libre** → réponse directe dans le fil
   - **Question structurée** (échelle, choix, classement) → boutons Block Kit dans le message
3. Bot valide la réponse, sauvegarde en base, poste Q2 dans le même fil
4. Répétition jusqu'à la dernière question
5. Bot confirme la complétion de l'objectif

**État de session** : le bot doit mémoriser (en base ou Redis) :
- `objectif_id` en cours de remplissage
- `question_index` courant
- `thread_ts` du fil Slack associé

Structure suggérée (table PostgreSQL) :
```sql
CREATE TABLE IF NOT EXISTS journal_slack_sessions (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    objectif_id INTEGER NOT NULL,
    thread_ts TEXT NOT NULL,
    question_index INTEGER NOT NULL DEFAULT 0,
    session_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, objectif_id, session_date)
);
```

### Fichiers à créer / modifier

| Fichier | Action |
|---|---|
| `app/jobs/journal_prompt.py` | Modifier pour envoyer Q1 dans Slack au lieu du lien web seul |
| `app/slack_app.py` | Ajouter listener `message` sur `#journal` (thread replies) + handler Block Kit |
| `app/handlers/journal_slack.py` | Créer — orchestre le flux Q→R→Q |
| `app/services/journal_v2.py` | Exposer `get_questions(objectif_id)` et `save_answer(objectif_id, q_index, valeur, date)` |
| `migrations/005_journal_slack_sessions.sql` | Créer la table `journal_slack_sessions` |

### Points d'architecture

**Détection de la réponse** : dans `slack_app.py`, le listener `message` existant
filtre déjà sur `is_journal_thread`. Étendre la logique pour détecter si le message
est une réponse à une session Slack active (lookup par `thread_ts` dans
`journal_slack_sessions`).

**Boutons Block Kit** : pour les questions structurées, le bot poste un message avec
`blocks` contenant des boutons. L'action `action_id` doit encoder `objectif_id` et
`question_index` pour retrouver le contexte sans session state supplémentaire.
Exemple : `action_id = "journal_answer"`, `value = "{objectif_id}|{question_index}|{valeur}"`.

**Coexistence web/Slack** : les réponses sauvegardées via Slack doivent être lisibles
et modifiables depuis l'UI web (`/journal/fill/{objectif_id}`). Utiliser la même table
de stockage des réponses.

**Pas de double envoi** : si l'utilisateur a déjà complété l'objectif du jour (via web
ou Slack), ne pas envoyer les questions Slack. Vérifier le statut avant d'envoyer Q1.

---

## 3. Tickets antérieurs (à ne pas implémenter dans cette session)

Ces tickets restent `open` pour une session ultérieure :

| ID | Description | Priorité |
|---|---|---|
| `1777534359410` | Demander dans quel projet ajouter le feedback depuis Slack | Basse — déjà partiellement implémenté |
| `1777564821701` | Outil surveillance brevets Google Patents | Nouveau projet — hors scope |
| `1777667954741` | Afficher le feedback de l'utilisateur dans son channel | UX bot — à grouper avec refonte feedback |
| `1777668013139` | Sélecteur de projet lors d'un feedback | Doublon partiel du #1777534359410 |

---

## 4. Fermeture des tickets après implémentation

Quand chaque feature est déployée, passer `status: open` → `status: closed` et ajouter
`closed_at: {datetime ISO}` dans le frontmatter du fichier `.md` correspondant dans
`feedback-tickets/journal/`.

Pas de notification Slack immédiate — la notification se fait automatiquement lors du
prochain déploiement via `POST /webhook/deploy-complete` (voir `CLAUDE.md` racine).
