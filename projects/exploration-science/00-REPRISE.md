---
project: exploration-science
updated: 2026-10-10
role: >
  Reprise du prototype « Explorateur de systèmes » (Phase 0). Jalons 1 validé, jalon 2 (moteur +
  caméra contrainte) livré, en attente de validation utilisateur.
---

# Prompt de reprise — exploration-science

> **Roadmap active : Phase 0, jalons de `CLAUDE.md` (inline ci-dessous).**

Lire d'abord `CLAUDE.md` du projet puis `docs/SPEC.md` (source de vérité). Brief initial : `PREMIER-MESSAGE.md`.

## Jalons Phase 0
- [x] 1. Schémas et exemples de contenu — **livré et validé (2026-10-10), format `0.2`**
- [x] 2. Moteur affichant une scène de test, avec caméra contrainte — **livré 2026-10-10, à valider**
- [ ] 3. Niveau 1 Starlink complet, avec le Play
- [ ] 4. Plongée vers les niveaux 2 et 3, lentille Ondes et curseurs
- [ ] 5. Scène de contrôle (ciel bleu : ébauche déjà au format). À traiter ici : plan de caméra « depuis l'observateur, vers le ciel » (la caméra ne sait qu'orbiter) et barre d'échelle quand molécules agrandies et atmosphère cohabitent.

## État
- `schemas/` : scene, catalogue, texts, sources — format `0.2` (2026-10-10 : sous-titre distinct du texte parlé avec équations `$…$`, termes définis obligatoires, termes explorables `links`), JSON Schema 2020-12.
- `catalogue/catalogue.json` : 16 composants, 3 simulateurs (phased-array-wave, orbital-pass, rayleigh-scattering), 1 lentille (waves) — tous `planned`.
- `content/nodes/starlink-terminal/` complet (3 niveaux, intro 25 s + Play 7 étapes ≈ 154 s) ; `content/nodes/blue-sky/` en ébauche.
- `engine/src/content/validation.ts` + `tests/content.test.ts` : schémas + références croisées (catalogue, clés de texte, sources). `npm test`.
- Page de revue lisible (sans JSON) : `npm run review` → `dist-review/index.html`, générée depuis le dépôt (scripts/build-review.ts + review-template.html). Publiée en artefact : https://claude.ai/artifact/9TpKGxucXtCtH5uMRcBGPo — republier après chaque changement de contenu.
- Moteur (`engine/src/`) : `content/` (ContentSource + StaticContentSource via `import.meta.glob`, chunks par nœud), `core/` (registre de plugins, sceneBuilder, palette de thème, éclairages, CameraRig + gestes souris/tactile, Engine), `plugins/components/` (terrain, house, flat-panel-terminal, leo-satellite, cable, data-link), `ui/overlay.ts` (question, Retour, sélecteur de nœud). La scène de test est la vraie `starlink-terminal` ; un composant sans plugin est dessiné en repère rose et listé à l'écran. Validation Ajv en dev uniquement (absente du bundle).
- Contrats internes du cœur : un plugin rend `{ object, anchor?, resolve?, update?, dispose? }` — `anchor` = où s'attachent les entités enfants (panneau incliné), `resolve` = passe après création pour les params `x-ref: entity`. Paramètres reçus déjà complétés par les `default` du catalogue ; longueurs en m converties via `ctx.metres()`.
- Caméra : azimut depuis +Z vers +X, élévation au-dessus de l'horizontale, bornée à ±89° et aux contraintes de la scène (y compris pour les plans du Play). Transitions : azimut par l'arc court, distance interpolée en log. Toute action utilisateur interrompt un vol.
- Aperçu publié (build Vite) : https://claude.ai/artifact/1vtLmqzT4kfUU7j3q33FLo — republier après chaque jalon (`npm run build`, copier `dist/assets` + page sans `<html>` vers le scratchpad, même URL).
- Pas encore de déploiement (aperçu statique prévu en fin de Phase 0 ; il faudra alors un compose + entrée dans `compose-deploy.sh`).

## Reste à faire / dettes ouvertes
- Terrain carré de 400 m : son bord se voit au zoom maximal (180). À traiter au jalon 3 (terrain plus grand/disque, ou brume).
- Plan d'accueil Starlink (az 35°, él 25°, 4 m) : le toit remplit l'écran. À reconsidérer avec le contenu du jalon 3.
- Gestes tactiles non testés sur un vrai iPad (pointer events + pinch, `touch-action: none`).
- Termes explorables : le moteur devra gérer pause / carte / « Plus tard » (spec, Briques d'interaction). Aucun nœud cible n'est encore écrit, donc aucun terme n'est cliquable.
- Sources : WebFetch/curl bloqués dans l'environnement cloud → toutes les sources sont `access: search-result`. Ouvrir les pages (starlink.com/specifications, arXiv 2310.09242, vidéo The Signal Path TSP #181) depuis un poste ouvert et passer en `opened`.
- Nombre d'éléments rayonnants et de puces : non vérifié (valeurs d'affichage).
- Identifiants Wikidata des principes : non renseignés (champ prévu dans `node.wikidata`).
- `blue-sky` : sources partielles (bornes du visible, taille des molécules, épaisseur de l'atmosphère).

## Où démarrer
Attendre la validation du jalon 2, puis jalon 3 : niveau 1 Starlink complet avec le Play — composants restants (antenna-element-array, ic-chip-grid, electronics-module, wifi-router, ground-station, datacenter), lecteur de visite (actions highlight/label/show/hide/reveal cutaway), sous-titres KaTeX, sélection d'un composant, simulateur orbital-pass pour faire défiler les satellites. Après tout changement de contenu : `npm run review` puis republier la page de revue (même URL).
