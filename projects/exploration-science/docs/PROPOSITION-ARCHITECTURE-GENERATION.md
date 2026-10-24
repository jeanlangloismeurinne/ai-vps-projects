---
statut: proposition — non validée, aucun arbitrage définitif
date: 2026-10-24
origine: demande de l'utilisateur après les scènes V2 « Starlink » et « Safran dans l'espace »
revue: à reprendre avec l'ensemble des fichiers de conception lors du déploiement du système de pilotage (MISSION.md en cours de validation)
---

# Proposition d'architecture : de la question à la scène

Cette proposition décrit comment passer d'une question (« comment fonctionne Starlink ? », « quels sont les produits de Safran Espace ? ») ou d'un nom de système ou de composant (« PPS 5000 », « station sol ») à une scène du niveau de qualité des deux scènes V2.

Elle s'appuie sur ce que ces deux scènes ont appris. Chaque choix est une option à discuter, pas un arbitrage. Elle ne modifie ni la SPEC ni les schémas : toute évolution de schéma qui en découlerait sera soumise avant implémentation.

## 1. Le principe : peu de formats partagés, des formats libres pour le reste

Les modules ne partagent pas leurs formats de sortie. Ils partagent une colonne vertébrale de quatre registres communs, et chacun reste libre de son format interne.

1. **Registre des identifiants.** Il contient les nœuds (`telecom-satellite`), leurs parties exposées (`telecom-satellite/pps-west/channel`) et leurs points d'accroche (`dish`, `fibre`).
   - C'est le seul vrai point de jonction.
   - Une fiche, une étape de visite ou une étiquette ne connaît du design qu'un identifiant.
   - C'est ce qui rend le contenu cliquable sans le rendre dépendant de la façon dont l'objet est modélisé.
2. **Base de faits.** Chaque fait a un énoncé, un statut (vérifié, calculé, non vérifié) et ses sources.
   - Dans les deux scènes, tout la cite déjà : fiches, visite, modèles (`diorama-scale`, `pps-exploded-model`).
   - C'est le seul module que tous consomment.
3. **Charte de style.** Palette, matériaux, conventions d'échelle (diorama), règles de lisibilité.
4. **Règles de validation.** Chaque module apporte ses propres validateurs ; l'intégration vérifie seulement que les identifiants référencés existent.

Tout le reste (une fiche, un script audio, un quiz, un modèle Blender, une illustration 2D) est une **charge libre** dans une enveloppe commune :

```
{ id, kind: "card" | "audio-script" | "quiz" | "asset" | …, version, targets: [ids], facts: [factIds], payload: … }
```

L'application affiche chaque `kind` avec un afficheur enregistré, selon le même principe de plugins que le catalogue de la SPEC. Ajouter un nouveau format de contenu ne touche ni au design ni à la scène.

## 2. Les modules

```
0 Cadrage ─► 1 Faits ⇄ 2 Structure ─► 3 Sélection et storyboard
                                         │
                       ┌─────────────────┼──────────────────┐
                       ▼                 ▼                  ▼
                  4 Design         5 Contenu          (librairie)
                  (par nœud)       (par nœud)
                       └────────┬────────┘
                                ▼
                       6 Composition de scène ─► 7 Visite guidée ─► 8 Validation d'intégration
```

### 0. Cadrage

- **Rôle** : transformer l'entrée en intention.
- **Sortie** : le type de question, le public, l'angle, le point d'entrée dans le graphe.
- **Sous-modules** :
  - typage : fonctionnement (« comment marche Starlink »), portefeuille (« les produits de Safran »), composant (« PPS 5000 »), phénomène ;
  - recherche de doublon ou de nœud proche ;
  - demande de précision si la question est vague.
- **Pourquoi c'est important** : le type décide de la grammaire de la scène, et nos deux scènes en sont la preuve.
  - Starlink est une **chaîne fonctionnelle** : un signal qui traverse des objets.
  - Safran est un **catalogue** : des produits sans lien entre eux, que seuls des flux réunissent.
  - Une entrée par composant (PPS 5000) demande en plus un **contexte d'usage**. Un moteur seul sur un socle n'explique rien ; il faut le satellite qu'il pousse. Il faut donc une étape « dans quoi vit ce composant ? ».

### 1. Base de faits

- **Rôle** : alimenter tous les autres modules en faits sourcés.
- **Sortie** : faits et sources (le `sources.json` actuel, enrichi).
- **Sous-modules** :
  - collecte (pages réellement ouvertes) ;
  - extraction des énoncés ;
  - faits calculés, avec leur formule (≈ 31 g) ;
  - contre-vérification par un second modèle.
- **À discuter** : elle **dialogue** avec la structure, au lieu de la précéder.
  - On ne sait quoi chercher qu'une fois la structure connue.
  - Mais la structure dépend des faits : c'est la page Safran qui a donné les quatre domaines.
  - Concrètement, on ferait deux ou trois allers-retours.

### 2. Structure

- **Rôle** : décrire ce qui existe, de façon neutre, sans encore choisir ce qu'on montrera.
- **Sortie** : un **graphe** plutôt qu'une simple arborescence.
  - Les nœuds, avec leurs liens « se compose de ».
  - Les **flux** : signaux, trajectoire, carburant, données. La scène Safran tient par ses flux, pas par sa composition.
  - Pour chaque nœud :
    - ce qui le rend reconnaissable ;
    - son ordre de grandeur ;
    - la question « qu'y a-t-il dedans d'intéressant ? ». C'est ce qui désigne les candidats à une vue éclatée.
  - Les **parties exposées** : celles qu'on pourra cliquer ou étiqueter. C'est le contrat que le design devra honorer.
- **Ce qui est contesté dans le découpage initial** : « la liste des systèmes et sous-systèmes » mélange deux choses.
  - Ce qui existe : Safran fait aussi des horloges atomiques et de la surveillance de l'espace.
  - Ce qu'on montre : nous les avons écartées.
  - La structure (exhaustive et neutre) est donc séparée de la sélection (module 3).

### 3. Sélection et storyboard

- **Rôle** : choisir ce qu'on montre et poser l'intention de récit.
- **Sortie** :
  - les nœuds retenus, ceux écartés et pourquoi ;
  - les nœuds qui auront une vue éclatée ;
  - un storyboard d'intentions (« montrer que la poussée est faible mais économe »), **sans texte final**.
- **Pourquoi si tôt** : la proposition initiale plaçait la visite en dernier. L'intention de récit doit venir tôt, et la visite rédigée tard.
  - Branch Education part du script, et la mise en scène en découle.
  - Chez nous, des choix de design venaient en fait du récit : la fenêtre du télescope ouverte vers la caméra, le mât d'Ariane placé derrière, la cathode montée au-dessus.
  - Si le récit n'arrive qu'à la fin, il hérite d'une scène qui ne le sert pas.
- **Point de contrôle humain recommandé ici** : c'est le choix le moins coûteux à corriger et le plus coûteux à rater.

### 4. Design (par nœud)

- **Rôle** : produire le modèle 3D de chaque nœud.
- **Sous-modules** :
  1. **Fiche de design** :
     - références réelles et dimensions sourcées ;
     - éléments de silhouette indispensables ;
     - parties exposées à livrer.
  2. **Recherche dans la librairie** : réemploi tel quel (les sapins), variante paramétrée (le socle « base spatiale », satellite télécom ou observation), ou création.
  3. **Modèle intrinsèque** : la géométrie dans son propre repère, paramétrée, sans rien savoir de la scène.
  4. **Variantes de détail** : vue éclatée, coupe. Elles réutilisent le même constructeur, comme `_pps` sert à la fois l'enveloppe et le détail.
  5. **Contrôles géométriques** : pièces flottantes, surfaces fermées, appuis.
  6. **Revue visuelle** : captures puis critique. C'est là que la qualité s'est gagnée, avec trois retouches sur Safran.
- **Sortie** : un modèle et sa **carte des parties** (noms, points d'accroche, couches).
- **À discuter : le design n'est pas aussi indépendant de la scène que le découpage initial le suppose.**
  - L'échelle (1:13,5 au sol, 1:5 pour les satellites), l'occlusion ambiante cuite dans le modèle, l'orientation choisie selon la caméra et les découpes tournées vers elle dépendent toutes de la mise en scène.
  - Proposition de coupe en deux :
    - le **modèle intrinsèque**, réutilisable d'une scène à l'autre ;
    - la **préparation pour la scène** (échelle, orientation, découpes vers la caméra, cuisson de l'occlusion), qui revient au module 6.
  - Aujourd'hui ces deux couches sont mélangées dans les scripts (`art/assets/*.py`), et c'est ce qui limite le réemploi.

### 5. Contenu (par nœud)

- **Rôle** : produire ce qu'on affiche ou lit pour présenter chaque nœud.
- **Sortie** : des enveloppes de formats libres :
  - fiche ;
  - étiquettes de parties ;
  - niveaux Découverte, Essentiel et Approfondi ;
  - script à lire à voix haute ;
  - quiz ;
  - traduction.
- **Seules contraintes** :
  - cibler des identifiants du registre ;
  - citer des identifiants de faits.
- **Il peut tourner en parallèle du design.** Les seuls ponts sont explicites :
  - les étiquettes de la vue éclatée visent les couches déclarées par la structure ;
  - un chiffre affiché qui contraint le modèle (la parabole de 13,5 m) passe par la base de faits, jamais directement d'un module à l'autre.

### 6. Composition de scène

- **Rôle** : assembler les modèles en une scène lisible.
- **Sous-modules** :
  - disposition sur le socle ;
  - échelles ;
  - préparation des modèles pour la scène (voir module 4) ;
  - style des liaisons et des flux ;
  - décor ;
  - plans de caméra ;
  - budget de performance (96 appels de dessin aujourd'hui, pour un budget de 80).
- **Sortie** : ce que contiennent aujourd'hui `content/v2/systems/*.json` et `content/v2/render/*.json`, mais **sans la structure**.
  - Le `systems/*.json` actuel mélange les deux : les objets et leurs liaisons d'un côté, leurs positions de l'autre.
  - Séparer les deux est une évolution de schéma, à soumettre avant toute implémentation.

### 7. Visite guidée

- **Rôle** : rédiger la visite à partir du storyboard.
- **Entrée** : le storyboard (intentions), les plans de caméra et les textes disponibles.
- **Sortie** : les étapes (plan, objet visé, clé de texte) et le minutage.
- **Contrôles** :
  - le rythme de lecture ;
  - la durée totale. La scène Safran est à 41 s pour une cible de 20 à 30 s, et ce dépassement serait détecté ici.
- **Autre forme possible** : la visite peut devenir un format de contenu parmi d'autres, comme un parcours « enfant » ou « expert ».

### 8. Validation d'intégration

- **Rôle** : vérifier que les modules s'emboîtent.
- **Contrôles** :
  - les références croisées entre identifiants ;
  - les captures sur les quatre formats ;
  - la sélection par clic ;
  - les transitions ;
  - le chevauchement des étiquettes.

Chaque module garde ses propres validateurs. Celui-ci ne vérifie que les jointures.

## 3. Ce que cette proposition conteste d'elle-même

- **Le registre des identifiants, point de jonction unique, est aussi un point de rigidité.** Renommer une partie casse le contenu qui la vise. Il faudra des alias, ou des identifiants stables distincts des noms.
- **Les formats libres coûtent cher en afficheurs.** Chaque nouveau `kind` demande un afficheur, et sans discipline on obtient vingt formats à moitié maintenus. Départ suggéré : 3 formats.
- **La structure neutre et exhaustive peut coûter cher pour rien** sur une question de portefeuille. Variante plus économique : ne structurer que ce que la sélection garde, et noter le reste en une ligne.
- **La revue visuelle est le vrai goulot.** Les contrôles automatiques passent du premier coup, mais c'est l'œil qui a vu que les jets ressemblaient à des cornets. Automatiser la critique visuelle par un modèle multimodal est possible, mais pas encore démontré ici.

## 4. Rapport avec l'existant

- **Pipeline de la SPEC (7 étapes)** : normalisation, recherche dans le graphe, sources, plan pédagogique, description de scène, validation, publication.
  - Cette proposition en reprend l'esprit : chaque étape prend un JSON, rend un JSON, et peut être faite par un humain.
  - Elle découpe autrement le cœur : le « plan pédagogique » devient structure, puis sélection et storyboard ; la « description de scène » devient design, contenu, composition et visite.
- **Générateur de Phase 1 (`generator/`, `roadmap/phase1-generator.md`)** : son étape `node` écrit la scène et ses textes en un seul appel.
  - C'est l'inverse du découpage proposé ici.
  - Le socle d'exécution, lui, se réutilise tel quel : contrat d'étape, exécuteurs `anthropic`, `manual` et `replay`, journal des runs, boucle de réparation.
- **Ce qui serait concerné dans le format de scène V2** :
  - la séparation entre structure et placement dans `systems/*.json` ;
  - le registre des parties exposées, aujourd'hui implicite dans les noms de nœuds glTF et les couches ;
  - l'enveloppe des contenus, aujourd'hui des fiches à format fixe dans `texts/*.fr.json`.

## 5. L'ordre des coûts, d'après ce qu'on a mesuré

- Le design 3D domine : environ 400 lignes de scripts Blender pour la scène Safran, plus les retouches.
- Le contenu est bon marché : environ 20 Ko.
- La librairie est donc le levier économique (`art/lib/xs/parts.py`, scripts paramétrés). Chaque scène devrait sortir avec plus de pièces partagées qu'elle n'en a consommé.
- Cela plaide pour faire du module 4 le plus outillé, et des modules 5 et 7 les plus automatisés.

## 6. Points de contrôle humain proposés

1. Après la sélection et le storyboard.
2. Après la fiche de design de chaque nouvel objet, avant de le modéliser.
3. Après les captures.

Le reste peut tourner sans intervention.

## 7. Pour trancher sans figer

Test proposé : rejouer un troisième sujet par **entrée composant**, par exemple « la station sol » ou « le PPS 5000 » en scène racine.

- Chaque module produirait un fichier à part, écrit à la main ou par un modèle.
- On noterait chaque endroit où un module a besoin d'en savoir plus que les identifiants et les faits.

Ces fuites montreront où les frontières sont mal placées.
