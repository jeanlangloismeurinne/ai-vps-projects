---
project: exploration-science
updated: 2026-10-10
role: >
  Reprise du prototype « Explorateur de systèmes » (Phase 0). Jalon 1 (schémas + contenu) livré,
  en attente de validation utilisateur avant le moteur.
---

# Prompt de reprise — exploration-science

> **Roadmap active : Phase 0, jalons de `CLAUDE.md` (inline ci-dessous).**

Lire d'abord `CLAUDE.md` du projet puis `docs/SPEC.md` (source de vérité). Brief initial : `PREMIER-MESSAGE.md`.

## Jalons Phase 0
- [x] 1. Schémas et exemples de contenu — **livré, validation utilisateur en attente**
- [ ] 2. Moteur affichant une scène de test, avec caméra contrainte
- [ ] 3. Niveau 1 Starlink complet, avec le Play
- [ ] 4. Plongée vers les niveaux 2 et 3, lentille Ondes et curseurs
- [ ] 5. Scène de contrôle (ciel bleu : ébauche déjà au format)

## État
- `schemas/` : scene, catalogue, texts, sources — format `0.2` (2026-10-10 : sous-titre distinct du texte parlé avec équations `$…$`, termes définis obligatoires, termes explorables `links`), JSON Schema 2020-12.
- `catalogue/catalogue.json` : 16 composants, 3 simulateurs (phased-array-wave, orbital-pass, rayleigh-scattering), 1 lentille (waves) — tous `planned`.
- `content/nodes/starlink-terminal/` complet (3 niveaux, intro 25 s + Play 7 étapes ≈ 154 s) ; `content/nodes/blue-sky/` en ébauche.
- `engine/src/content/validation.ts` + `tests/content.test.ts` : schémas + références croisées (catalogue, clés de texte, sources). `npm test`.
- Page de revue lisible (sans JSON) : `npm run review` → `dist-review/index.html`, générée depuis le dépôt (scripts/build-review.ts + review-template.html). Publiée en artefact : https://claude.ai/artifact/9TpKGxucXtCtH5uMRcBGPo — republier après chaque changement de contenu.
- Pas encore de déploiement (aperçu statique prévu en fin de Phase 0 ; il faudra alors un compose + entrée dans `compose-deploy.sh`).

## Reste à faire / dettes ouvertes
- Relecture du format via la page de revue en cours (commentaires sur l'artefact). Encore ouverts depuis le jalon 1 : altitude 480 km vs 550 km dans la spec, caméra « point de vue » pour le ciel bleu.
- Termes explorables : le moteur devra gérer pause / carte / « Plus tard » (spec, Briques d'interaction). Aucun nœud cible n'est encore écrit, donc aucun terme n'est cliquable.
- Sources : WebFetch/curl bloqués dans l'environnement cloud → toutes les sources sont `access: search-result`. Ouvrir les pages (starlink.com/specifications, arXiv 2310.09242, vidéo The Signal Path TSP #181) depuis un poste ouvert et passer en `opened`.
- Nombre d'éléments rayonnants et de puces : non vérifié (valeurs d'affichage).
- Identifiants Wikidata des principes : non renseignés (champ prévu dans `node.wikidata`).
- `blue-sky` : sources partielles (bornes du visible, taille des molécules, épaisseur de l'atmosphère).

## Où démarrer
Recueillir la validation du jalon 1, appliquer les ajustements de format demandés, puis attaquer le jalon 2.
