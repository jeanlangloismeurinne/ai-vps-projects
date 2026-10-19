# QUALITY_BAR.md — Exigences de qualité visuelle de la v0

> Contrat d'acceptation de la V2 v0, fourni par l'utilisateur le 2026-10-19 (texte reproduit tel quel).
> Roadmap qui l'applique : `roadmap/v2.md`.

## 1. Objectif

Construire une application web 3D interactive présentant des systèmes techniques complexes dans un univers visuel de qualité professionnelle, comparable à une illustration 3D éditoriale haut de gamme.

Le niveau cible minimal est une illustration 3D premium (niveau B). Une scène simplement fonctionnelle, constituée de primitives géométriques génériques, n'est pas acceptable comme résultat final.

L'application doit combiner :

* une vue globale du système, immédiatement lisible ;
* des objets 3D reconnaissables et visuellement soignés ;
* une direction artistique homogène ;
* des flux et des relations animés ;
* des transitions fluides entre vue globale et exploration détaillée ;
* une interface d'information intégrée à l'environnement 3D.

## 2. Contraintes techniques non négociables

### Aucune API externe dans la v0

* Ne pas utiliser d'API distante de génération 3D, d'images, de textures ou de scènes.
* Ne pas dépendre de Tripo, Meshy ou d'un service équivalent.
* Ne pas utiliser de service externe de rendu 3D.
* Ne pas introduire de clé API, de compte fournisseur ou de facturation liée à ces services.
* Ne pas rendre le fonctionnement de l'application dépendant d'un service distant.
* Ne pas remplacer une fonctionnalité attendue par une intégration externe sans autorisation explicite.

Claude Code doit produire le code, les scripts, les modèles procéduraux et les fichiers nécessaires directement dans le dépôt.

Les bibliothèques de programmation installées localement sont autorisées. Les bibliothèques d'assets 3D préexistantes sont facultatives ; tout asset externe utilisé doit être téléchargé manuellement ou intégré localement, avec une licence vérifiée. La v0 doit rester fonctionnelle sans eux.

### Pile technique privilégiée

* Blender piloté par Python pour construire et exporter les modèles 3D.
* React et TypeScript pour l'application.
* Three.js via React Three Fiber pour le rendu interactif.
* GLB/glTF pour les modèles 3D exportés.
* JSON pour décrire les systèmes, les objets, les connexions, les flux et les parcours narratifs.
* Scripts locaux pour automatiser la génération, les contrôles et la construction.

Les choix peuvent être adaptés si le dépôt existant justifie une autre solution, mais aucun changement majeur d'architecture ne doit être fait silencieusement.

## 3. Direction artistique obligatoire

### Style général

Produire une illustration 3D stylisée, isométrique ou en perspective axonométrique, avec une esthétique industrielle contemporaine, épurée et pédagogique.

Le résultat doit évoquer une illustration réalisée par un designer 3D spécialisé, et non une scène de démonstration technique ou un assemblage brut de modèles.

### Composition

* Vue globale permettant de comprendre immédiatement l'organisation spatiale du système.
* Hiérarchie visuelle explicite entre les composants principaux et secondaires.
* Silhouettes distinctes et proportions crédibles.
* Espacement maîtrisé, sans objets qui se chevauchent involontairement.
* Caméra, cadrage et échelle cohérents entre les différentes vues.
* Espace suffisant pour les panneaux d'information et les libellés.
* Arrière-plan discret, ne détournant pas l'attention du système.

### Géométrie

* Les objets principaux doivent être reconnaissables par leur silhouette, leurs proportions et leurs détails caractéristiques.
* Les objets complexes doivent présenter plusieurs niveaux de détail géométrique.
* Les primitives simples sont acceptables comme éléments constitutifs, mais pas comme substituts permanents aux objets principaux.
* Les détails doivent être hiérarchisés selon leur importance visuelle et leur distance à la caméra.
* Les répétitions doivent être cohérentes et les assemblages géométriques propres.
* Aucun défaut évident : intersections involontaires, surfaces manquantes, proportions absurdes ou éléments flottants.

### Matériaux et éclairage

* Palette limitée et cohérente, dominée par des tons neutres avec des couleurs d'accent fonctionnelles.
* Matériaux différenciés selon la nature des surfaces : métal, verre, plastique, sol, végétation ou surfaces techniques.
* Éclairage doux et homogène, avec ombres lisibles et occlusion ambiante maîtrisée.
* Contraste suffisant pour détacher les objets du fond.
* Reflets et effets spéculaires limités aux endroits où ils améliorent la lisibilité.
* Éviter le plastique uniforme, les matériaux par défaut et l'apparence de maquette brute.
* Privilégier une qualité visuelle stable plutôt que des effets photoréalistes coûteux.

### Finition

* Aucun objet principal ne doit sembler être un simple bloc de test.
* Les contours, les raccords, les détails et les ombres doivent rester propres à la résolution cible.
* Les éléments d'interface HTML doivent être alignés, typographiquement cohérents et visuellement intégrés à la scène.
* Les animations doivent renforcer la compréhension du système, sans distraire.
* Le rendu final doit être évalué dans le navigateur, pas uniquement dans Blender.

## 4. Exigences fonctionnelles et visuelles

La v0 doit présenter au minimum :

* Un système technique complet dans une vue globale.
* Quatre objets principaux distincts et reconnaissables.
* Des connexions visuellement identifiables entre les objets.
* Au moins un flux animé indiquant une direction.
* Une sélection d'objet qui affiche une fiche contextuelle.
* Une transition entre vue globale et vue détaillée d'un objet.
* Un retour à la vue globale sans perte de contexte.
* Une visite guidée présentant le système global avant un objet particulier.
* Une représentation détaillée qui illustre le fonctionnement interne, et non une simple duplication de l'enveloppe extérieure.

Le premier démonstrateur doit utiliser un système de communication par satellite comprenant une maison, une antenne, un satellite et une station sol. Les liaisons doivent être cohérentes avec le fonctionnement représenté.

## 5. Architecture des assets

Séparer explicitement :

1. Les données décrivant le système.
2. Les modèles 3D et leurs matériaux.
3. Les paramètres de rendu et de caméra.
4. Les interactions et animations.
5. Les contenus narratifs et les fiches d'information.

Chaque objet doit posséder un identifiant stable et pouvoir être associé à plusieurs représentations visuelles.

Les scripts Blender doivent être reproductibles : une même configuration doit générer les mêmes assets, sous réserve des variations techniques documentées.

Le pipeline doit pouvoir être exécuté par commande, sans manipulation obligatoire de l'interface Blender.

## 6. Critères d'acceptation

La v0 n'est considérée comme terminée que si les conditions suivantes sont satisfaites :

### Qualité visuelle

* La scène présente une direction artistique identifiable et cohérente.
* Les quatre objets principaux sont reconnaissables sans lire leurs libellés.
* Les matériaux, l'éclairage et les ombres donnent du volume aux objets.
* La composition globale permet de comprendre les relations entre les composants.
* Aucun défaut géométrique ou visuel majeur n'est visible à la résolution cible.
* La scène ne ressemble pas à un prototype composé uniquement de cubes, de sphères et de cylindres.
* Les panneaux d'interface ne masquent pas les informations spatiales essentielles.

### Qualité interactive

* Les objets sont sélectionnables et leurs fiches correspondent aux bonnes données.
* Les connexions et flux sont compréhensibles.
* Les transitions de caméra sont maîtrisées.
* La navigation est utilisable à la souris et au tactile.
* Les erreurs de chargement ne laissent pas l'application dans un état incohérent.

### Qualité technique

* L'application se construit et démarre à partir des instructions documentées.
* Les assets sont générés et exportés par le pipeline prévu.
* Aucun appel à une API externe interdite n'est nécessaire.
* Les ressources sont optimisées pour le navigateur.
* Les performances et la mémoire sont mesurées sur un appareil représentatif, en particulier un iPad utilisant Safari.

## 7. Méthode de validation

Ne pas considérer une tâche comme terminée simplement parce que le code compile.

Pour chaque étape importante :

1. Générer les assets.
2. Lancer l'application.
3. Capturer des vues de référence : vue globale, vue rapprochée de chaque objet principal, vue détaillée et état avec panneaux d'information.
4. Inspecter les captures et identifier les défauts visuels.
5. Corriger les défauts les plus importants.
6. Répéter jusqu'à satisfaire les critères d'acceptation.
7. Vérifier que les interactions fonctionnent et que les performances restent acceptables.

Si un critère n'est pas satisfait, signaler explicitement ce qui manque et proposer une correction concrète. Ne jamais déclarer la qualité premium atteinte sans vérification visuelle.

## 8. Priorité de développement

En cas d'arbitrage, respecter cet ordre :

1. Lisibilité et cohérence de la scène.
2. Qualité visuelle des objets principaux.
3. Qualité des matériaux et de l'éclairage.
4. Clarté des connexions et de la narration.
5. Fluidité de la navigation.
6. Optimisation des performances.
7. Enrichissement des détails secondaires.

La priorité est une scène restreinte, mais visuellement aboutie, plutôt qu'un monde vaste, détaillé en apparence, mais de qualité inégale.

## 9. Règle de décision

Avant d'introduire une nouvelle dépendance, un service externe ou une complexité architecturale, privilégier la solution locale la plus simple qui permette de satisfaire les critères visuels et fonctionnels.

Si la qualité cible ne peut pas être atteinte avec l'approche choisie, ne pas masquer la limite par une simplification silencieuse : expliquer le compromis et proposer une alternative compatible avec les contraintes de la v0.
