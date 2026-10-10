---
project: exploration-science
updated: 2026-10-10
role: >
  Reprise du prototype « Explorateur de systèmes » (Phase 0). Jalons 1 et 2 validés, jalon 3
  (niveau 1 Starlink complet avec le Play) livré, en attente de validation utilisateur.
---

# Prompt de reprise — exploration-science

> **Roadmap active : Phase 0, jalons de `CLAUDE.md` (inline ci-dessous).**

Lire d'abord `CLAUDE.md` du projet puis `docs/SPEC.md` (source de vérité). Brief initial : `PREMIER-MESSAGE.md`.

## Jalons Phase 0
- [x] 1. Schémas et exemples de contenu — **livré et validé (2026-10-10), format `0.2`**
- [x] 2. Moteur affichant une scène de test, avec caméra contrainte — **livré et validé (2026-10-10)**
- [x] 3. Niveau 1 Starlink complet, avec le Play — **livré 2026-10-10, à valider**
- [ ] 4. Plongée vers les niveaux 2 et 3, lentille Ondes et curseurs
- [ ] 5. Scène de contrôle (ciel bleu : ébauche déjà au format). À traiter ici : plan de caméra « depuis l'observateur, vers le ciel » (la caméra ne sait qu'orbiter) et barre d'échelle quand molécules agrandies et atmosphère cohabitent.

## État
- `schemas/` : scene, catalogue, texts, sources — format `0.2`, JSON Schema 2020-12. **Inchangés au jalon 3.**
- `catalogue/catalogue.json` : 16 composants, 3 simulateurs, 1 lentille. Plugins écrits : les 12 composants Starlink, `orbital-pass`, `phased-array-wave`. Restent : `star`, `atmosphere-layer`, `molecule-cloud`, `observer`, `rayleigh-scattering` (jalon 5), lentille `waves` (jalon 4).
- `content/nodes/starlink-terminal/` complet (3 niveaux, intro 25 s + Play 7 étapes ≈ 163 s) ; `content/nodes/blue-sky/` en ébauche (repères roses).
- Contenu Starlink retouché au jalon 3 (contenu seulement, pas de schéma) : plans de caméra, accueil à 9 m, `displayRadius` 30, `spacingS` 230, satellites affichés plus grands, accélération du temps ×10 (le problème) et ×5 (le relais). Chronologie : au début du relais, sat-a ≈ 3° (presque couché), sat-b ≈ 44° ; le texte le dit.
- Moteur (`engine/src/`) :
  - `content/` : ContentSource + StaticContentSource ; `types.ts` couvre maintenant tours, actions, simulateurs, lentilles, liens, entrées de texte.
  - `core/` : registre (composants + simulateurs), sceneBuilder, `simulation.ts` (horloge simulée, timeScale, reset), `highlighter.ts` (halo pulsé, matériaux clonés), `picking.ts` (clic → entité sélectionnable la plus intérieure ; dans un boîtier ouvert, l'enfant traversé en premier gagne), CameraRig + gestes (glisser, pincer, molette, tap), `Engine` qui implémente la `Stage` du lecteur.
  - `play/player.ts` : `TourPlayer`. highlight/label valables pour l'étape ; les autres actions persistent. Tout démarrage ou saut d'étape repart de l'état initial et rejoue les étapes précédentes (temps simulé avancé d'autant) : une étape a toujours le même aspect. Pause = temps simulé gelé ; reprise = la caméra revient au plan de l'étape. Fin = scène réinitialisée, caméra laissée en place.
  - `ui/` : sous-titres KaTeX + légende des termes + phrases explorables soulignées, barre Play (⏮ ▶ ⏭, points d'étape, ✕), choix du niveau (mémorisé en localStorage), étiquettes ancrées (empilées si elles se chevauchent, masquées pendant les vols, cliquables), carte de sélection (titre, description du niveau, « Plonger » grisé).
  - Arbitrages d'interaction : un geste pendant la visite d'arrivée la termine ; pendant le Play, il le met en pause ; un tap sur un composant sélectionnable le sélectionne (halo + orbite autour).
- Plugins, conventions d'affichage (pas de paramètre au catalogue) : réseau d'éléments en rectangle 3:2 ; puces au pas de 5 côtés ; passages orbitaux tous au zénith, le long de −Z, premier satellite au zénith à t = 0, train qui boucle sous l'horizon ; impulsions de données à taille fixe à l'écran.
- Tests : 69 (schémas, références croisées, plugins, équations des simulateurs, lecteur, pointage). `npm test`.
- Aperçu publié : https://claude.ai/artifact/1vtLmqzT4kfUU7j3q33FLo (version jalon 3). Republier après chaque jalon : `npm run build`, copier `dist/assets` (js, css, woff2) + page sans `<html>` vers le scratchpad, même URL, en supprimant les anciens fichiers hachés.
- Page de revue : `npm run review` → `dist-review/review.html`, publiée sur https://claude.ai/artifact/9TpKGxucXtCtH5uMRcBGPo — republier après chaque changement de contenu.
- Dev : en mode `vite`, `window.xs` expose `engine`, `player`, `scene()`, `select`, `setLevel`, `startMainTour` (pilotage headless, captures Playwright).
- Pas encore de déploiement (aperçu statique prévu en fin de Phase 0 ; il faudra alors un compose + entrée dans `compose-deploy.sh`).

## Reste à faire / dettes ouvertes
- Étape « orienter le faisceau » : le simulateur calcule l'angle, mais rien ne se voit avant la lentille Ondes (jalon 4). L'action `lens` est acceptée et ignorée.
- Termes explorables : affichés soulignés, pas cliquables. La carte de la spec demande une « définition en une phrase » que le format ne porte pas (ni le nœud cible, pas encore écrit) → proposition de format à soumettre avec le jalon 4.
- Barre d'échelle : pas faite (jalon 4, avec la plongée).
- Passages orbitaux : direction et culmination fixées par le plugin. Si une scène a besoin d'un passage non zénithal, ajouter des paramètres au catalogue (à soumettre).
- Gestes tactiles et 60 i/s non vérifiés sur un vrai iPad (rendu headless logiciel seulement).
- Sources : WebFetch/curl bloqués dans l'environnement cloud → toutes les sources sont `access: search-result`. Ouvrir les pages (starlink.com/specifications, arXiv 2310.09242, vidéo The Signal Path TSP #181) depuis un poste ouvert et passer en `opened`.
- Nombre d'éléments rayonnants et de puces : non vérifié (valeurs d'affichage).
- Identifiants Wikidata des principes : non renseignés (champ prévu dans `node.wikidata`).
- `blue-sky` : sources partielles (bornes du visible, taille des molécules, épaisseur de l'atmosphère).

## Où démarrer
Attendre la validation du jalon 3, puis jalon 4 : nœuds enfants niveaux 2 et 3 (au moins `starlink-phased-array`), transition de plongée (héritage de géométrie et de style, règle 9), lentille Ondes (champ calculé par `phased-array-wave`, lobes de réseau visibles au-delà de d/λ = 0,5), curseurs par niveau, barre d'échelle, et la proposition de format pour la carte des termes explorables. Après tout changement de contenu : `npm run review` puis republier la page de revue (même URL).
