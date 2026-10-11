---
project: exploration-science
updated: 2026-10-11
role: >
  Reprise du prototype « Explorateur de systèmes » (Phase 0). Jalons 1 à 4 validés ; jalon 5 (scène
  de contrôle ciel bleu) livré, à valider. Termes explorables : format `summaryKey` validé, à
  implémenter avec un nœud `wave-interference` minimal (jalon 5 bis).
---

# Prompt de reprise — exploration-science

> **Roadmap active : Phase 0, jalons de `CLAUDE.md` (inline ci-dessous).**

Lire d'abord `CLAUDE.md` du projet puis `docs/SPEC.md` (source de vérité). Brief initial : `PREMIER-MESSAGE.md`.

## Jalons Phase 0
- [x] 1. Schémas et exemples de contenu — **livré et validé (2026-10-10), format `0.2`**
- [x] 2. Moteur affichant une scène de test, avec caméra contrainte — **livré et validé (2026-10-10)**
- [x] 3. Niveau 1 Starlink complet, avec le Play — **livré et validé (2026-10-10)**
- [x] 4. Plongée vers les niveaux 2 et 3, lentille Ondes et curseurs — **livré 2026-10-10, validé 2026-10-11**
- [x] 5. Scène de contrôle ciel bleu — **livré 2026-10-11, à valider**. Le format `0.2` a suffi : aucun schéma modifié.
- [ ] 5 bis. Termes explorables cliquables : champ `node.summaryKey` (validé le 2026-10-11 : la définition vit dans le nœud cible, 3 niveaux) + nœud principe `wave-interference` minimal (réutilise `phased-array-wave` et la lentille Ondes, cité 6 fois depuis Starlink). Parcours à éprouver : pause, carte, Explorer, Retour à l'étape, liste « À explorer » en fin de Play. Mettre à jour `docs/SPEC.md` (ligne Termes explorables) une fois livré.

## État
- `schemas/` : scene, catalogue, texts, sources — format `0.2`, JSON Schema 2020-12. **Inchangés aux jalons 3 et 4.**
- `catalogue/catalogue.json` : 17 composants, 3 simulateurs, 1 lentille, **tous `implemented`** depuis le jalon 5. Rôle `array` de `phased-array-wave` accepte aussi `patch-element` (la ligne de sources est centrée dessus).
- Nœuds : `starlink-terminal` (niveau 1, m) → `starlink-phased-array` (niveau 2, cm, Play 6 étapes ≈ 128 s) → `starlink-radiating-element` (niveau 3, mm, Play 5 étapes ≈ 112 s), chacun 3 niveaux de texte + sources ; `blue-sky` (statut `review`, intro 26 s, Play 5 étapes ≈ 102 s : lumière blanche, diffusion dans la loupe 450 → 700 nm, ciel vu du dehors, sans air = ciel noir, coucher). Les enfants n'ont pas de `style` (hérité) et montrent le composant du parent (test `graphErrors`).
- Contenu Starlink retouché au jalon 3 (contenu seulement, pas de schéma) : plans de caméra, accueil à 9 m, `displayRadius` 30, `spacingS` 230, satellites affichés plus grands, accélération du temps ×10 (le problème) et ×5 (le relais). Chronologie : au début du relais, sat-a ≈ 3° (presque couché), sat-b ≈ 44° ; le texte le dit.
- Moteur (`engine/src/`) :
  - `content/` : ContentSource + StaticContentSource ; `types.ts` couvre maintenant tours, actions, simulateurs, lentilles, liens, entrées de texte.
  - `core/` : registre (composants + simulateurs), sceneBuilder, `simulation.ts` (horloge simulée, timeScale, reset), `highlighter.ts` (halo pulsé, matériaux clonés), `picking.ts` (clic → entité sélectionnable la plus intérieure ; dans un boîtier ouvert, l'enfant traversé en premier gagne), CameraRig + gestes (glisser, pincer, molette, tap), `Engine` qui implémente la `Stage` du lecteur.
  - `play/player.ts` : `TourPlayer`. highlight/label valables pour l'étape ; les autres actions persistent. Tout démarrage ou saut d'étape repart de l'état initial et rejoue les étapes précédentes (temps simulé avancé d'autant) : une étape a toujours le même aspect. Pause = temps simulé gelé ; reprise = la caméra revient au plan de l'étape. Fin = scène réinitialisée, caméra laissée en place.
  - `ui/` : sous-titres KaTeX + légende des termes + phrases explorables soulignées, barre Play (⏮ ▶ ⏭, points d'étape, ✕), choix du niveau (mémorisé en localStorage), étiquettes ancrées, carte de sélection (« Plonger » actif si le lien `composedOf` est `available` et le nœud existe), bouton de lentille, curseurs du niveau courant (valeur lue dans les `outputs` du simulateur d'abord, donc l'angle déduit du déphasage suit), barre d'échelle (1-2-5 × 10ⁿ, `ui/scale.ts`), fil d'Ariane des niveaux de zoom (libellé = étiquette de la cible du plan d'accueil, unité = `metersPerUnit`).
  - Lentille `waves` (`plugins/lenses/waves.ts`) : tranche du champ dans le plan (axe des sources, normale), somme par pixel des ondes de chaque source (amplitude ∝ 1/√r), crêtes animées à 0,8 Hz ; tiges sur le faisceau et les lobes de réseau prévus par le simulateur. Contrat simulateur → lentille : canal `wave-field` (`plugins/channels.ts`, `channel()` sur l'instance de simulateur). Piège corrigé : le shader doit travailler en unités de scène (`position * uSize`), sinon ça ne marche qu'à l'échelle 1 m.
  - Ciel bleu (jalon 5) : `plugins/light.ts` (Planck, fonctions CIE 1931 de Wyman 2013, XYZ → sRGB) ; simulateur `rayleigh-scattering` : diffusion simple sur atmosphère exponentielle, τ(λ) = 0,0973·(550/λ)⁴, masse d'air Kasten-Young, ombre de la Terre sous l'horizon, solution fermée de l'intégrale (testée contre une intégration numérique) ; il place le Soleil à sa hauteur, colore chaque sommet du dôme selon la direction vue par l'observateur, teinte le Soleil et sa lumière (convention `userData.tint`, `plugins/tint.ts`), vide la loupe sans air. Canal `wave-field` étendu (champs facultatifs : `amplitude`, `colour`, `incident`, `discRadius`) : dans la loupe, onde incidente + onde renvoyée en anneaux, amplitude ∝ 1/λ², diagramme √((1+cos²Θ)/2) ; deux rayons (`from`/`towards`) : Soleil → molécule en blanc, molécule → yeux de l'observateur dans la couleur de l'onde (le plan des ondes contient les deux) ; le long de ces rayons, une onde multicolore par bandes de 400 à 700 nm (`plugins/lenses/spectralRibbon.ts`) : blanche à l'arrivée (I0), surtout bleue au départ (I0/λ⁴). Opacité des anneaux ∝ intensité renvoyée (amplitude²), curseur « Couleur de la lumière » ouvert aux 3 niveaux. Loupe toujours visible près de l'observateur, lentille libellée « Ondes lumineuses » (retours de revue du 2026-10-11).
  - Loupe : `ComponentInstance.magnifier` (échelle intérieure, rayon) — la barre d'échelle passe en « 🔍 dans la loupe : 500 nm » quand la caméra vise l'entité ; une entité `notToScale` visée masque la barre (ce que le schéma disait déjà). La bulle représente 2 µm de rayon (convention du plugin).
  - Caméra : élévation négative permise par la scène (regarder le ciel depuis le sol), mais la caméra ne passe jamais sous y = 0 (`aboveGround`). Convention « y vers le haut, sol en y = 0 » : implicite, à écrire dans la description du schéma (à soumettre).
  - Plongée : vol vers l'entité, fondu, chargement de l'enfant ; remontée par le fil d'Ariane : fondu, parent, caméra repart de tout près de l'entité d'origine (sélectionnée). Sélectionner un composant intérieur ouvre le boîtier parent qui sait faire `cutaway` et place la caméra au-dessus (≥ 55°). Régler l'angle ou le déphasage à la main coupe le suivi du satellite (plugin).
  - Arbitrages d'interaction : un geste pendant la visite d'arrivée la termine ; pendant le Play, il le met en pause ; un tap sur un composant sélectionnable le sélectionne (halo + orbite autour).
- Plugins, conventions d'affichage (pas de paramètre au catalogue) : réseau d'éléments en rectangle 3:2 ; puces au pas de 5 côtés ; passages orbitaux tous au zénith, le long de −Z, premier satellite au zénith à t = 0, train qui boucle sous l'horizon ; impulsions de données à taille fixe à l'écran.
- Tests : 99 (diffusion Rayleigh : rapport (700/450)⁴, Beer-Lambert, masse d'air, intégrale, couleurs ; schémas, graphe des nœuds, plugins, équations des simulateurs, champ de la lentille : faisceau, lobes, largeur, lecteur, barre d'échelle). `npm test`.
- Aperçu publié : https://claude.ai/artifact/1vtLmqzT4kfUU7j3q33FLo (version jalon 5, `?node=blue-sky` ou sélecteur). Republier après chaque jalon : `npm run build`, copier `dist/assets` (js, css, woff2) + page sans `<html>` vers le scratchpad, même URL, en supprimant les anciens fichiers hachés.
- Page de revue : `npm run review` → `dist-review/index.html` (4 nœuds). Publiée sur https://claude.ai/artifact/9TpKGxucXtCtH5uMRcBGPo, **mais bloquée depuis le jalon 4** : l'outil de publication la refuse (y compris à une nouvelle adresse) en la prenant pour une page « artifact-pr-review ». La version en ligne date du jalon 3.
- Dev : en mode `vite`, `window.xs` expose `engine`, `player`, `scene()`, `select`, `setLevel`, `startMainTour` (pilotage headless, captures Playwright).
- Pas encore de déploiement (aperçu statique prévu en fin de Phase 0 ; il faudra alors un compose + entrée dans `compose-deploy.sh`).

## Reste à faire / dettes ouvertes
- Termes explorables : soulignés, pas cliquables tant que le jalon 5 bis n'est pas fait.
- Publication de la page de revue bloquée (voir État).
- Plongée = vol + fondu + coupe, pas de morphing géométrique : la continuité tient au même composant affiché de part et d'autre.
- Sans valeurs déduites affichées : au niveau Approfondi, régler Δφ fait bouger le faisceau, mais θ n'est lu que dans l'angle du faisceau, pas affiché à côté.
- Niveaux 2 et 3 : espacement, nombre d'éléments et de puces, permittivité (εr ≈ 3), épaisseur du substrat, type d'élément et d'alimentation non vérifiés pour Starlink (marqués dans `sources.json`, dits dans les textes Approfondi). Les éléments sont modélisés comme des sources ponctuelles.
- Starlink niveau 1, Approfondi, étape « contact » : ~178 mots/min, juste au-dessus du seuil de 175.
- Passages orbitaux : direction et culmination fixées par le plugin. Si une scène a besoin d'un passage non zénithal, ajouter des paramètres au catalogue (à soumettre).
- Gestes tactiles et 60 i/s non vérifiés sur un vrai iPad (rendu headless logiciel seulement).
- Sources : WebFetch/curl bloqués dans l'environnement cloud → toutes les sources sont `access: search-result`. Ouvrir les pages (starlink.com/specifications, arXiv 2310.09242, vidéo The Signal Path TSP #181) depuis un poste ouvert et passer en `opened`.
- Nombre d'éléments rayonnants et de puces : non vérifié (valeurs d'affichage).
- Identifiants Wikidata des principes : non renseignés (champ prévu dans `node.wikidata`).
- `blue-sky` : sources partielles (bornes du visible, taille des molécules, épaisseur de l'atmosphère) ; τ(550 nm) = 0,0973 et coefficients CIE/Kasten-Young lus via résumés ou sources secondaires (à ouvrir).
- `blue-sky` : l'éclairage de la scène reste le préréglage `daylight` (sol clair au coucher) : seule la lumière portée par le Soleil change de couleur. Corriger demanderait que l'environnement suive l'étoile (à soumettre si gênant).
- `blue-sky` : plan « ciel vu du dehors » visé sur l'observateur, donc barre d'échelle à 100 m alors que le dôme n'est pas à l'échelle.
- Couleur du ciel : diffusion simple seulement (pas de diffusion multiple ni d'ozone) ; l'horizon blanchit moins que le vrai.

## Où démarrer
Attendre la validation du jalon 5, puis jalon 5 bis (termes explorables + `wave-interference`). Ensuite : aperçu statique déployable (compose + `compose-deploy.sh`) et tests utilisateurs. Après tout changement de contenu : `npm run review`.
