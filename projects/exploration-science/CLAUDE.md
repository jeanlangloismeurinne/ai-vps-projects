# Explorateur de systèmes — instructions pour Claude Code

## Le projet

Outil pédagogique immersif : l'utilisateur pose une question sur un système technique ou un phénomène scientifique, et explore une scène 3D continue, de l'objet entier jusqu'à la physique fondamentale. Référence visuelle : la chaîne Branch Education.

`docs/SPEC.md` est la source de vérité. Lis-la en entier avant toute décision structurante. Si une demande contredit la spec, signale-le avant d'agir.

## Phase en cours : Phase 0 (prototype)

Objectif : une expérience Starlink complète, écrite à la main, jouée par le vrai moteur. Elle doit permettre de tester l'adhésion auprès d'une dizaine de personnes et de figer le format de scène v1.

**Dans le périmètre**
- Schémas JSON : format de scène v0, catalogue v0, textes v0.
- Moteur Three.js : affichage d'une scène, caméra contrainte (orbite, zoom, retour), plongée d'un niveau à l'autre avec transitions, sélection d'un composant, lecteur Play avec sous-titres, barre d'échelle.
- Plugins : composants Starlink paramétriques, simulateur d'ondes calculé, lentille Ondes avec curseurs.
- Contenu : 3 niveaux Starlink écrits à la main (scènes et textes Découverte, Essentiel, Approfondi), puis une scène de contrôle très différente (ciel bleu ou moteur thermique, à confirmer avec moi).
- Un aperçu statique déployable, utilisable sur ordinateur et iPad (Safari).

**Hors périmètre en Phase 0**
- Backend, base de données, appels LLM, générateur, comptes utilisateurs, audio.
- Le multilingue au-delà de la structure (les textes sont déjà séparés par langue, seul le français est rédigé).

## Stack

- Front : TypeScript, Vite, Three.js. Pas de framework UI tant qu'un besoin n'est pas démontré ; l'interface superposée (sous-titres, curseurs, menu au clic, barre d'échelle) reste en TypeScript et DOM.
- Schémas : JSON Schema comme source de vérité, validés avec Ajv. Le choix de JSON Schema est volontaire : le backend futur sera en Python et validera les mêmes fichiers.
- Tests : Vitest.
- Plus tard (pas en Phase 0) : backend Python (FastAPI, Pydantic AI), Postgres avec pgvector, déploiement via Coolify sur un VPS Hetzner.

## Arborescence cible

```
docs/SPEC.md
schemas/            scene.schema.json, catalogue.schema.json, texts.schema.json
catalogue/          catalogue.json (composants, simulateurs, lentilles et leurs paramètres)
content/nodes/<id>/ scene.json, texts.fr.json, sources.json
engine/src/
  core/             chargement, rendu, caméra, transitions, registre de plugins
  plugins/          components/, simulators/, lenses/
  play/             lecteur de visite guidée
  ui/               sous-titres, curseurs, menu, barre d'échelle
  content/          interface ContentSource et implémentation fichiers statiques
tests/
```

## Règles de conception (non négociables)

1. Le moteur n'affiche que ce qu'un fichier de scène décrit. Aucune logique propre à Starlink dans le cœur.
2. Tout composant, simulateur ou lentille est un plugin, déclaré dans le catalogue avec le schéma de ses paramètres. Ajouter un plugin ne modifie pas le cœur.
3. Les scènes ne contiennent aucun texte, seulement des clés. Les textes sont dans `texts.<langue>.json`, par niveau.
4. Les phénomènes physiques sont simulés à partir des vraies équations, jamais dessinés à la main. Un test vérifie au moins un résultat de chaque simulateur (par exemple, la direction du faisceau correspond à Δφ = 2π·d·sin θ / λ).
5. Pas de schéma 2D : de la 3D stylisée.
6. Chaque scène est validée contre son schéma par un test automatique.
7. Le format de scène porte un champ `formatVersion`. Toute modification d'un schéma m'est soumise avant implémentation.
8. Le moteur charge le contenu via une interface `ContentSource`. En Phase 0, elle lit des fichiers statiques ; en Phase 1, elle appellera l'API, sans autre changement.
9. Un nœud enfant hérite de la géométrie et du style du composant parent, pour garantir la continuité visuelle entre échelles.

## Contraintes d'expérience

- Ordinateur et iPad : gestes tactiles, 60 images par seconde visées, budget de détail par scène (objets éloignés simplifiés, détails chargés à l'approche).
- Caméra contrainte : pas de vol libre.
- À l'arrivée sur une scène, visite automatique de 20 à 30 secondes, puis la main passe à l'utilisateur.
- Textes écrits pour être lus à voix haute (l'audio viendra plus tard).

## Exactitude

Tout chiffre technique d'une scène (altitude, vitesse, fréquence, dimensions) est sourcé dans le `sources.json` du nœud. Un chiffre non vérifié est marqué comme tel. En cas de doute, préfère un ordre de grandeur sourcé à une valeur précise inventée.

Toute équation, dans un texte comme dans le catalogue, définit chacun de ses termes (symbole, signification, unité), y compris dans la version lue à voix haute.

## Façon de travailler

- Avance par jalons, et arrête-toi pour validation à chacun :
  1. Schémas et exemples de contenu.
  2. Moteur affichant une scène de test, avec caméra contrainte.
  3. Niveau 1 Starlink complet, avec le Play.
  4. Plongée vers les niveaux 2 et 3, lentille Ondes et curseurs.
  5. Scène de contrôle.
- À chaque jalon : ce qui est fait, comment le voir, ce qui reste ouvert. Court.
- Code, identifiants et commits en anglais ; contenu pédagogique et échanges avec moi en français.
- Commits petits et fréquents, messages explicites.
- Ne crée pas de fichier de documentation supplémentaire sans me le demander ; mets à jour `docs/SPEC.md` seulement si je valide une évolution.
