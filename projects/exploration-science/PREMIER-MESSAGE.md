Lis `CLAUDE.md`, puis `docs/SPEC.md` en entier. Nous démarrons la Phase 0, jalon 1 : les schémas. Pas de code de rendu à ce stade.

1. Initialise le dépôt : Vite, TypeScript, Three.js, Vitest, Ajv, et l'arborescence prévue dans `CLAUDE.md`.
2. Propose les trois schémas : `scene.schema.json`, `catalogue.schema.json`, `texts.schema.json`.
3. Écris en entier le nœud de niveau 1 du terminal Starlink : `scene.json`, `texts.fr.json` (les trois niveaux, les 7 étapes du Play décrites dans la spec) et `sources.json`. Vérifie les chiffres (altitude, vitesse, bande de fréquence) par une recherche et cite les pages consultées.
4. Écris une ébauche du nœud « ciel bleu », pour vérifier que le format tient aussi pour un phénomène et pas seulement pour un objet.
5. Remplis `catalogue.json` avec les plugins nécessaires à Starlink (composants, simulateur d'ondes, lentille Ondes) et leurs paramètres.
6. Ajoute un test qui valide toutes les scènes et tous les textes contre les schémas.

Ensuite, explique-moi en quelques lignes les choix structurants du format de scène et les alternatives écartées. Arrête-toi là pour validation avant d'écrire le moteur.
