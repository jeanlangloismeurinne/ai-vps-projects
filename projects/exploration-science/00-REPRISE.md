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
- [x] 1. Schémas et exemples de contenu — **livré et validé (2026-10-10), format `0.2`**
- [ ] 2. Moteur affichant une scène de test, avec caméra contrainte
- [ ] 3. Niveau 1 Starlink complet, avec le Play
- [ ] 4. Plongée vers les niveaux 2 et 3, lentille Ondes et curseurs
- [ ] 5. Scène de contrôle (ciel bleu : ébauche déjà au format). À traiter ici : plan de caméra « depuis l'observateur, vers le ciel » (la caméra ne sait qu'orbiter) et barre d'échelle quand molécules agrandies et atmosphère cohabitent.

## État
- `schemas/` : scene, catalogue, texts, sources — format `0.2` (2026-10-10 : sous-titre distinct du texte parlé avec équations `$…$`, termes définis obligatoires, termes explorables `links`), JSON Schema 2020-12.
- `catalogue/catalogue.json` : 16 composants, 3 simulateurs (phased-array-wave, orbital-pass, rayleigh-scattering), 1 lentille (waves) — tous `planned`.
- `content/nodes/starlink-terminal/` complet (3 niveaux, intro 25 s + Play 7 étapes ≈ 154 s) ; `content/nodes/blue-sky/` en ébauche.
- `engine/src/content/validation.ts` + `tests/content.test.ts` : schémas + références croisées (catalogue, clés de texte, sources). `npm test`.
- Page de revue lisible (sans JSON) : `npm run review` → `dist-review/index.html`, générée depuis le dépôt (scripts/build-review.ts + review-template.html). Publiée en artefact : https://claude.ai/artifact/9TpKGxucXtCtH5uMRcBGPo — republier après chaque changement de contenu.
- Pas encore de déploiement (aperçu statique prévu en fin de Phase 0 ; il faudra alors un compose + entrée dans `compose-deploy.sh`).

## Reste à faire / dettes ouvertes
- Termes explorables : le moteur devra gérer pause / carte / « Plus tard » (spec, Briques d'interaction). Aucun nœud cible n'est encore écrit, donc aucun terme n'est cliquable.
- Sources : WebFetch/curl bloqués dans l'environnement cloud → toutes les sources sont `access: search-result`. Ouvrir les pages (starlink.com/specifications, arXiv 2310.09242, vidéo The Signal Path TSP #181) depuis un poste ouvert et passer en `opened`.
- Nombre d'éléments rayonnants et de puces : non vérifié (valeurs d'affichage).
- Identifiants Wikidata des principes : non renseignés (champ prévu dans `node.wikidata`).
- `blue-sky` : sources partielles (bornes du visible, taille des molécules, épaisseur de l'atmosphère).

## Où démarrer
Jalon 2 : moteur Three.js affichant une scène de test avec caméra contrainte (orbite, zoom, retour), chargée via `ContentSource` (fichiers statiques). Commencer par le cœur (chargement, registre de plugins, rendu) et un ou deux composants simples ; s'arrêter pour validation à la fin du jalon. Après tout changement de contenu : `npm run review` puis republier la page de revue (même URL).
