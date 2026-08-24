---
id: 1787559677497
type: feature
status: closed
priority: low
date: 2026-08-24T08:21:17+00:00
closed_at: 2026-08-24T11:55:00+00:00
project: assistant-ia
url: 
milestone: agent-consignes
---

## ✨ Feature

**Date** : 24/08/2026 08:21
**URL** : `N/A`

### Description

Page web d'**édition manuelle** du doc système — cible du bouton *Éditer* (roadmap §4, ligne
« Éditer → une page web avec le fichier en mode editable s'ouvre permettant une modification
manuelle ») et réponse à la décision ouverte §7 (« table versionnée **avec une capacité à le
visualiser pour édition** »).

Route dans `app/routes/` (patron `journal_settings.py`) :

- `GET /agent/system-doc` — affiche la version active, l'historique des versions et leurs diffs.
- `GET /agent/system-doc/edit/{version}` — éditeur texte (textarea) pré-rempli.
- `POST /agent/system-doc` — enregistre le texte édité comme **nouvelle version active**, avec
  entrée d'audit (`event: edited`, actor = utilisateur web).

Contraintes :

- **Authentifié** — réutiliser `app/routes/auth.py`. Cette page modifie le prompt système de
  l'agent : elle ne doit jamais être publique.
- Passe par la **même couche de versioning et d'audit** que l'approbation Slack
  (#1787559677496) — pas de chemin d'écriture parallèle qui contournerait l'append-only ou l'audit.
- Les **bornes de sécurité §5.4** (taille max, pas de secrets/URL exfiltrantes, refus des
  consignes qui désactivent les garde-fous) s'appliquent **aussi** à l'édition manuelle. Une
  édition humaine n'est pas une raison de désactiver les contrôles.
- Permettre le **rollback** depuis cette page (réactiver une version antérieure).

Mettre à jour la landing page (`_LANDING_HTML` dans `app/main.py`) avant déploiement, comme
l'impose le workflow du `CLAUDE.md` du projet.

### Vérification attendue

Édition manuelle → nouvelle version active + audit, le chat reflète le changement. Accès non
authentifié → refusé. Édition contenant un motif interdit → rejetée avec message explicite.

### Notes d'implémentation

`app/routes/agent_doc.py` (4 routes, routeur entier sous `Depends(require_auth)`), routeur enregistré
dans `app/main.py`. La page n'a **aucun chemin d'écriture propre** : édition et rollback appellent
`agent_versioning.create_manual_version()` / `rollback_to_version()`, c'est-à-dire la même couche
append-only + audit que l'approbation Slack. `create_manual_version` exécute `agent_guardrails` avant
toute persistance — une édition humaine n'est pas une raison de désactiver les bornes §5.4. Le
rollback web passe par un `preauthorized=True` documenté : `AGENT_APPROVERS` contient des Slack user
IDs et ne peut pas trancher pour une session web, déjà authentifiée par le cookie hub.

Deux corrections issues des tests : le retour après refus pointait `edit/1` en dur (faux dès que la
version active n'est plus la 1) et les messages passaient non encodés dans l'en-tête `Location`.
Bouton *Éditer* de #1787559677496 réaligné sur `/agent/system-doc`. `_LANDING_HTML` mis à jour
(sections Agent et Base de connaissance).

Vérification (37 assertions) : accès anonyme aux 4 routes → redirigé vers le login, **zéro écriture** ;
édition → v_n+1 active avec `parent_version` correct et `created_by='web'`, version précédente
conservée intacte, une seule ligne active, audit `edited` complet ; `agent_doc.get_active_doc()` voit
la nouvelle version **sans redémarrage** ; édition contenant un motif interdit → refusée avec le motif
nommé dans le message, aucune version ni entrée d'audit créée, doc actif inchangé ; rollback → version
antérieure réactivée, **aucune ligne créée ni supprimée**, audit `rollback` écrit ; rollback vers la
version déjà active → no-op signalé ; état de la base restauré à l'identique en fin de test.
