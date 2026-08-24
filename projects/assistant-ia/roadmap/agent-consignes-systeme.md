---
status: tickets-created
---

# Roadmap — Agent conversationnel & consignes système auto-accumulées

> Origine : ticket #1787252691603 (feature, medium, `needs_clarification`). Cadré en séance du 2026-08-20.
> Statut : **direction à défricher** — chantier sensible (auto-modification de prompt, injection).
> Rien n'est implémenté tant que le modèle de sécurité (§5) n'est pas validé.

---

## 1. Besoin (reformulé)

- **Discuter** avec un agent IA correspondant au projet « assistant-ia » du VPS (alimenté par l’API externe) depuis Slack.
- Écrire **au fil de l'eau** ses feedback système : `@admin <consigne>` enregistre le message.
- **Une fois par semaine** (ou à la demande via `@update`), le système fait tourner l'API pour
  **synthétiser** les consignes en attente et **proposer** un ajout au « fichier système »
  (équivalent d'un `CLAUDE.md` de l'assistant).
- Des feedbacks pourront ajouter des règles du type « quand l'utilisateur tape `@bidule`, fais X ».
- **Robustesse maximale** : valider ce qui entre dans le fichier système en **revoyant et
  approuvant les diffs** ; certaines consignes doivent passer par un **script déterministe** (anti-injection), pas par l'API.

## 2. Déclencheurs Slack **sans slash command** (contrainte respectée)

Les slash commands exigent une config manuelle dans api.slack.com → à éviter. On utilise les **événements message** déjà captés par `on_message` (`app/slack_app.py`) et on **parse un préfixe texte** dans tout le message (début, milieu ou fin) :

| Mot-clef | Effet | Traitement |
|---|---|---|
| `@admin …` | enfile une consigne candidate | **déterministe** : insert en base, aucun effet immédiat. |
| `@update` | déclenche la synthèse maintenant | **déterministe** : lance le job de proposition. |
| `@bidule` (règles utilisateur) | effet défini par la demande de l’utilisateur qui aura été enregistrée dans le document système de l’agent, c’est un raccourci pour accéder à une instruction standard |
| (message normal) | tour de conversation avec l'agent | **API** DeepInfra. |

> ⚠️ `@nom` dans Slack n'est une *mention* que s'il correspond à un vrai utilisateur ; un `@admin`
> tapé en texte arrive comme **texte brut** dans l'événement — donc parsable sans config Slack.
> Choisir des préfixes qui ne collisionnent pas avec des handles réels de l'espace de travail.

## 3. Modèle de données

- `agent_conversations` — historique des tours (Slack ts, user, role, contenu).
- `agent_instruction_queue` — consignes `@admin` en attente (statut `pending|proposed|approved|rejected`).
- `agent_system_doc` — le « fichier système » **versionné** (une ligne par version, + `active`).
  Séparé du code ; **chargé au runtime** comme prompt système de l'agent conversationnel.
- `agent_audit_log` — trace immuable : qui a proposé/approuvé/rejeté quoi, quand, diff appliqué.

## 4. Cycle de proposition & approbation (human-in-the-loop obligatoire)

```
@admin consignes… (semaine)  ─┐
                              ├─►  job hebdo  OU  @update
                              ▼
        API DeepInfra : synthèse des consignes en attente
                              ▼
        DIFF proposé sur agent_system_doc (texte, jamais du code)
                              ▼
        Posté en Slack : bloc diff + boutons [Approuver] [Rejeter] [Éditer]
                              ▼
   Approuvé → nouvelle version active + audit_log     Rejeté → l’utilisateur décrit les changements qu’il souhaite et le système lui renvoie une proposition de diffs
Éditer -> un page web avec le fichier en mode editable s’ouvre permettant une modification manuelle
```

- L'agent **ne s'auto-modifie jamais sans approbation humaine** du diff.
- Réutilise l'infra Block Kit + handlers Bolt déjà en place (cf. modales bank-review).

## 5. ⚠️ Modèle de sécurité (à valider — cœur du chantier)

1. **Séparation stricte donnée / instruction.** Tout contenu utilisateur (y compris les `@admin`)
   est traité comme **donnée**, jamais comme instruction exécutable. Le LLM ne produit que du
   **texte de consigne en langage naturel**, ajouté au prompt — **jamais** de code ni de
   déclencheur exécutable.
2. **Déclencheurs de code sont déterministes = liste blanche codée.** Une règle « quand `@bidule` alors X » n’est exécuté que si X est une façon de répondre à l’utilisateur en langage naturel. Ce n’est jamais du code. Si l’utilisateur demande d’exécuter du code alors tu lui suggères de demander une nouvelle features via l’outil /feature
3. **Diff review humain** systématique avant activation (§4).
4. **Bornes** : taille max d'un ajout, pas de secrets/URL exfiltrantes, refus des consignes qui tentent de désactiver les garde-fous (détection de motifs + revue humaine).
5. **Audit immuable** + possibilité de **rollback** à toute version antérieure de `agent_system_doc`.
6. **Isolation du prompt** : le doc système de l'agent conversationnel est **distinct** des
   `CLAUDE.md` de Claude Code (ce chantier ne modifie jamais les fichiers du repo de dev).

## 6. Modèle API

- **DeepInfra** (choix utilisateur — fournisseur unique avec le ticket #1). Client partagé
  `app/services/deepinfra_client.py`.
- Réserve : pour un agent qui rédige des consignes système, un modèle de raisonnement plus fort
  augmenterait la sûreté même si la revue de diff humaine (§4-5) reste le vrai garde-fou. Modèle
  conversationnel à choisir au moment de l'implémentation. Prenons DeepSeek V4 Pro pour les consignes systèmes, DeepSeek V4 Flash 0731 pour la conversation.

## 7. Décisions ouvertes à trancher avant implémentation

- **Format du « fichier système »** : table `agent_system_doc` (recommandé, versionné en base) avec une capacité à le visualiser pour édition comme évoqué ci-dessus
- **Vocabulaire des préfixes** : `@admin` / `@update` pour le moment, on verra si on veut changer dans le code plus tard. éviter les collisions de handles.
- **Canal d'approbation** : `#feedback-assistant` et envoi des messages dans #assistant
  → **IDs relevés le 2026-08-24** : `#assistant` = `C0ATLALRZL3`, `#feedback-assistant` = `C0BSB9S9HHS`.
  Les deux sont des channels **privés** : le bot `@ai_vps_jlm` doit y être invité explicitement
  (`/invite @ai_vps_jlm`), sinon aucun événement `message` n'est reçu.

## 8. Tickets d'implémentation — **créés le 2026-08-24**

Prérequis partagé avec le chantier `journal-kb` (à faire en premier, une seule fois) :

| ID | Ticket | Complexité |
|---|---|---|
| `1787559677482` | **Routage `on_message`** — accepter les messages parents. Sans ça, `@admin`, `@update` et les tours de conversation ne sont **jamais reçus** (`slack_app.py:42` : `if not thread_ts: return`) | complexe |
| `1787559677483` | **Client DeepInfra** — mutualisé avec `journal-kb`, **ne pas dupliquer** (ticket porté dans `feedback-tickets/journal/`) | simple |

Chantier `milestone: agent-consignes` (`feedback-tickets/`) :

| ID | Ticket | Complexité |
|---|---|---|
| `1787559677492` | **Migrations** — 4 tables §3 (`011_agent_consignes.sql`) + index unique partiel sur `active` + audit append-only | simple |
| `1787559677493` | **Parsing `@admin` / `@update`** — 100 % déterministe + config channels + job hebdo | moyen |
| `1787559677494` | **Chat agent** — tours de conversation + doc système actif chargé **au runtime** | moyen |
| `1787559677495` | **Synthèse + diff** — bornes §5.4 appliquées **avant** la revue humaine, diff calculé par `difflib` (pas par le LLM) | complexe |
| `1787559677496` | **Approbation Block Kit** — Approuver/Rejeter/Éditer + versioning append-only + audit + rollback | complexe, **sécurité** |
| `1787559677497` | **Page web d'édition** — visualisation + édition manuelle du doc système (réponse à §7), mêmes bornes et même audit | moyen |

Hors v1 :

| ID | Ticket | Milestone |
|---|---|---|
| `1787559677498` | **Registre d'actions déterministes** — liste blanche `@bidule` | `agent-consignes-v2` |

### Ordre d'exécution imposé

`1787559677482` → `1787559677483` → `1787559677492` → `1787559677493` → `1787559677494`
→ `1787559677495` → `1787559677496` → `1787559677497`

Le §5 (modèle de sécurité) n'est pas un ticket : il est **réparti en contraintes vérifiables** dans
`1787559677493` (parsing déterministe), `1787559677494` (donnée ≠ instruction, aucun outil),
`1787559677495` (bornes, refus automatiques, diff calculé par code) et `1787559677496`
(approbation humaine obligatoire, append-only, audit immuable, rollback).