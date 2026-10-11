---
status: figée
role: >
  Amorcer la Phase 1 (générateur de nœuds) pendant que la Phase 0 attend ses tests utilisateurs,
  sans rien construire qui dépende du verdict des tests ni du format v1.
---

# Phase 1 — amorce du générateur

## Principe directeur

- **Le générateur est du code qui appelle l'API Claude, jamais une session Claude Code.** Ce que
  Claude Code produit à la main pendant le développement n'est qu'un exécuteur `manual` parmi
  d'autres, enregistré et marqué non reproductible. Une sortie ne compte comme résultat du
  générateur que si elle vient de l'exécuteur `anthropic` (ou de son rejeu).
- **Tout appel est enregistré** (prompt, modèle, paramètres, réponse, usage, coût) et **rejouable** :
  le rejeu refuse si le prompt a changé. C'est ce qui rend une génération reproductible et son
  coût mesurable.
- **Chaque étape prend un JSON et rend un JSON** (spec, Pipeline) ; un humain peut la remplacer.
- **Le moteur, le catalogue et les schémas sont la référence** : le générateur n'utilise que ce
  que le catalogue déclare, et sa sortie passe par le même validateur que le contenu fait main.
- **Rien qui fige le format v1** : les scènes sont stockées et validées telles quelles ; un
  changement de format après les tests coûte une mise à jour du prompt, pas une réécriture.
- Hors périmètre : questions libres, signalements, administration, quotas (Phase 2).

Ordre : le socle reproductible d'abord (sans lui, aucun essai n'est mesurable) ; puis l'essai sur
un nœud existant, qui renseigne le gel du format v1 ; puis le banc qui juge les essais ; le
backend ensuite (le générateur peut écrire des fichiers tant qu'il n'existe pas) ; les étapes
amont en dernier, parce qu'elles exigent l'accès web du VPS.

## Capacités (ordre imposé)

### 1. Socle reproductible du générateur · contexte partagé : `generator/`, spec § Pipeline
- [x] Paquet Python `generator/` : contrat d'étape (entrée JSON → sortie JSON, modèle et effort par étape)
- [x] Exécuteurs `anthropic` (SDK officiel, streaming), `manual` (demande écrite sur disque, réponse fournie par un humain), `replay` (réponse enregistrée, refus si le prompt diffère)
- [x] Journal de chaque appel dans `generator/runs/<run>/` : requête, empreinte, réponse, usage, coût, exécuteur
- [x] Validation de la sortie par le validateur existant (CLI Node) ; boucle de réparation bornée (erreurs renvoyées au modèle)
- **Acceptation** : `pytest` vert ; un run enregistré rejoué avec `--runner replay` redonne des fichiers identiques octet pour octet ; modifier le prompt fait échouer le rejeu avec un message qui le dit ; `--runner anthropic` sans clé échoue avec un message explicite (pas une trace).

### 2. Essai de génération sur `starlink-phased-array` · contexte partagé : catalogue, schémas, nœud parent
- [x] Étape `node` : à partir de la question, du nœud parent et de l'entité visée, écrire `scene.json` + `texts.fr.json` (sources fournies en entrée, l'étape « sources » n'existant pas encore)
- [x] Un run `manual` à l'aveugle (sous-agent qui ne voit que la demande écrite), enregistré
- [ ] Un run `anthropic` sur le VPS (clé dans le `.env`), enregistré, avec son coût
- [x] Rapport : ce que le modèle a su écrire, ce qui a cassé, ce que ça dit du format v1
- **Acceptation** : le nœud généré passe le validateur (0 erreur) et s'affiche dans le moteur (capture headless) ; le rapport liste les écarts avec la référence faite main.

### 3. Banc de non-régression · contexte partagé : nœuds faits main = référence
- [ ] Contrôles automatiques par nœud : validation, rendu headless, mots/min, termes d'équation définis, chiffres sourcés
- [ ] Grille de comparaison avec la référence, notée par un second modèle (appels enregistrés comme le reste)
- [ ] Commande unique qui note un nœud généré contre sa référence
- **Acceptation** : la commande note les 5 nœuds faits main contre eux-mêmes au maximum, et un nœud volontairement abîmé (texte retiré, chiffre faux) en dessous.

### 4. Socle backend · contexte partagé : spec § Architecture
- [ ] Postgres (`db_exploration_science` sur shared-postgres) : nœuds, versions, liens, textes, sources, file de tâches (`SKIP LOCKED`)
- [ ] API FastAPI en lecture ; import des nœuds faits main ; validation Python contre les mêmes schémas JSON
- [ ] `ApiContentSource` côté moteur (règle 8 : aucun autre changement)
- **Acceptation** : le moteur ouvert avec la source API affiche les 5 nœuds comme avec les fichiers ; un fichier invalide est refusé à l'import par Python avec la même erreur que le validateur Node.

### 5. Étapes amont · contexte partagé : spec § Pipeline 1 à 4
- [ ] Normalisation de la question, recherche dans le graphe (doublon / proche / nouveau / vague)
- [ ] Sources : recherche et ouverture des pages (outils web du serveur API), seules les pages ouvertes sont citées
- [ ] Plan pédagogique
- **Acceptation** : depuis la seule question « Comment le réseau d'antennes de Starlink oriente-t-il son faisceau ? », le pipeline complet produit un nœud qui passe le banc (capacité 3).
