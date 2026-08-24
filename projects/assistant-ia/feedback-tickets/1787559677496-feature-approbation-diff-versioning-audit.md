---
id: 1787559677496
type: feature
status: closed
priority: high
date: 2026-08-24T08:21:17+00:00
closed_at: 2026-08-24T12:40:00+00:00
project: assistant-ia
url: 
milestone: agent-consignes
---

## ✨ Feature

**Date** : 24/08/2026 08:21
**URL** : `N/A`

### Description

**Ticket sécurité — human-in-the-loop.** C'est le garde-fou qui rend tout le chantier acceptable
(roadmap §4 et §5.3). Dépend de #1787559677495.

Poster la proposition dans **`#feedback-assistant` (`C0BSB9S9HHS`)** : bloc diff + trois boutons
Block Kit (patron existant : modales bank-review dans `app/slack_app.py`).

| Bouton | Effet |
|---|---|
| **Approuver** | crée une **nouvelle version** de `agent_system_doc`, la passe `active`, désactive la précédente, consignes `proposed` → `approved`, entrée d'audit |
| **Rejeter** | consignes → `rejected`, entrée d'audit. L'utilisateur décrit ce qu'il veut changer et le système renvoie une nouvelle proposition (roadmap §4) |
| **Éditer** | ouvre la page web d'édition manuelle (#1787559677497) |

Règles non négociables :

- **L'agent ne s'auto-modifie jamais sans approbation humaine d'un diff (§4, §5.3).** Aucun chemin
  de code ne doit pouvoir activer une version sans passer par ce handler.
- **Append-only** : approuver crée une ligne (`version = max + 1`, `parent_version` renseigné) —
  on ne modifie jamais une version existante. L'index unique partiel sur `active` garantit
  l'unicité ; l'activation doit être **transactionnelle** (désactivation + activation dans la même
  transaction, sinon l'index rejette).
- **Rollback (§5.5)** : pouvoir réactiver n'importe quelle version antérieure, avec entrée d'audit.
  Prévoir le chemin dès ce ticket, pas plus tard.
- **Audit immuable (§5.5)** : chaque action écrit dans `agent_audit_log` (qui, quoi, quand, diff,
  `from_version` → `to_version`). Jamais d'UPDATE ni de DELETE sur cette table.
- **Autorisation** : vérifier que l'utilisateur qui clique est bien autorisé à approuver — ne pas
  se reposer sur le seul fait que le channel est privé. Enregistrer l'`actor` réel du clic.
- **Idempotence** : un double-clic sur *Approuver*, ou un clic sur une proposition déjà tranchée,
  ne doit pas créer deux versions. Vérifier l'état de la proposition avant d'agir.
- `ack()` sous 3 s puis traitement en tâche de fond ; le message Slack est mis à jour pour refléter
  la décision (boutons retirés).

### Vérification attendue

Parcours réel complet : proposition → *Approuver* → version 2 active, version 1 conservée, audit
écrit, le chat (#1787559677494) reflète la nouvelle consigne **sans redémarrage**. Puis rollback
vers la version 1 → active, audit écrit. Puis double-clic sur *Approuver* d'une proposition déjà
traitée → aucun effet, pas d'erreur visible pour l'utilisateur.

### Notes d'implémentation

`app/services/agent_versioning.py` (toute la logique transactionnelle), `app/handlers/agent_approval.py`
(Block Kit + décision), handlers `agent_doc_approve` / `agent_doc_reject` / `agent_doc_edit` dans
`slack_app.py` (ack immédiat puis tâche de fond, message réécrit sans boutons après décision).

`agent_versioning` est le **seul** module du projet qui écrit `active = true` : c'est ce qui garantit
qu'aucun chemin de code ne peut activer une version sans clic humain. Désactivation et activation
sont dans la même transaction, avec `SELECT … FOR UPDATE` sur la proposition et sur la ligne active —
sans quoi deux clics simultanés se croiseraient et l'index unique partiel rejetterait l'opération à
mi-chemin. Le rollback ne crée ni ne supprime aucune ligne : il déplace le drapeau `active`.

**Autorisation** : nouvelle variable `AGENT_APPROVERS` (Slack user IDs, séparés par des virgules).
Deny-by-default — le ticket demande explicitement de ne pas se reposer sur la confidentialité du
channel. Aucun ID n'étant connu en base, le refus affiche l'ID du cliqueur et la variable à
renseigner, pour que la configuration soit auto-suffisante au premier clic.

Vérification (43 assertions avec 495) : approbation → v2 active, v1 conservée avec `parent_version=1`,
une seule ligne active, consignes → `approved`, audit `approved` complet (`actor`, `from_version`,
`to_version`) ; relecture à chaud confirmée (le chat verrait la nouvelle consigne sans redémarrage) ;
**double-clic → aucune 2ᵉ version, message non alarmant** ; rollback v2→v1 → v1 active, audit
`rollback` écrit, aucune version créée ni supprimée, rollback vers la version déjà active = no-op ;
utilisateur non autorisé → `NotAuthorized`, doc inchangé, refus expliqué.

⚠️ Reste à faire après déploiement : renseigner `AGENT_APPROVERS` (sinon aucune approbation possible)
et rejouer le parcours réel de bout en bout dans `#feedback-assistant`.
