---
id: 1787600247613
type: feature
status: open
priority: high
date: 2026-08-24T19:37:27Z
project: assistant-ia
url:
milestone: kb-visualisation
---

## ✨ Feature

**Date** : 24/08/2026 19:37
**URL** : `N/A`

### Description

Déployer **Obsidian réel dans un conteneur** accessible au navigateur (bureau web KasmVNC), monté
sur le vault en **lecture seule**, comme viewer de la KB
(`roadmap/kb-visualisation-obsidian.md` §3-4).

**1. Image** — `linuxserver/obsidian` (Obsidian dans un bureau KasmVNC, exposé en HTTP/HTTPS).
Alternative à évaluer si l'image officielle LSIO ne convient pas : `linuxserver/kasm`+Obsidian.
Fixer une version (pas `latest`).

**2. Montage du vault en lecture seule** :
- Monter `/storage/journal-vault` **en RO** dans le conteneur (`:ro`), à l'emplacement de coffre
  attendu par l'image. L'utilisateur consulte, ne peut pas éditer (décision roadmap §3 : l'agent
  host est seul à écrire).
- ⚠️ Contrairement au conteneur `assistant-ia` (qui monte `/storage/Documents` en RO et écrit le
  vault via le host), **ce conteneur ne doit avoir aucun accès en écriture au vault**.

**3. Plugins / config** :
- Activer **Bases** (plugin cœur) si la version le fournit — nécessaire pour les vues du ticket
  `1787600247612`. Sinon pré-installer **Dataview** (+ **Obsidian-Kanban** pour un rendu board
  optionnel). **Remonter au ticket `1787600247612` quels plugins sont réellement disponibles** afin
  qu'il fige le format des vues (`.base` vs Dataview).
- Config Obsidian pré-provisionnée (`.obsidian/`) : coffre pointé sur le vault, thème, plugins
  activés — pour éviter un setup manuel à chaque cold start. Attention : si le vault est RO,
  `.obsidian/` doit vivre ailleurs (volume conteneur dédié) ou être injecté en lecture — trancher et
  documenter (typiquement : config dans un volume RW propre au conteneur, vault de contenu en RO).

**4. Réseau / sécurité** :
- Port interne uniquement (`127.0.0.1:`), publié via Traefik (voir ticket Sablier `1787600247614`).
- **Jamais** exposé sans auth : le vault contient un journal `private`. L'auth est portée par le
  ticket Sablier/Traefik.
- Vérifier UFW (port interne en DENY externe) — checklist `COOLIFY_PLAYBOOK.md` § Sécurité.

**5. Ressources** : pas d'`always-on` visé — le scale-to-zero (ticket `1787600247614`) arrête le
conteneur au repos. Ici, viser un démarrage à froid raisonnable (~15-30 s) : limiter les extras du
bureau KasmVNC, ne garder qu'Obsidian.

### Vérification attendue

- Conteneur démarré → bureau Obsidian accessible en local (avant Traefik), coffre = le vault, notes
  journal + `tasks/` visibles, graphe peuplé.
- Tentative d'édition d'une note depuis Obsidian → échoue (montage RO).
- Les plugins requis par les vues sont actifs (Bases **ou** Dataview) ; l'info est remontée au
  ticket `1787600247612`.

### Notes d'implémentation

_(à compléter à la fermeture)_
