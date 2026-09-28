---
status: figée
created: 2026-09-28
project: portfolio-tracker
role: >
  Décide l'ordre dans lequel on écrit les quatre frameworks qui manquent au mémo de comité, puis
  comment on les éprouve sur des cas réels pour trancher à quel niveau vit l'adaptation à
  l'entreprise. Remplace la suite du lot 7 de `03-spec-frameworks.md` (maillons 3-4 repoussés ici).
---

# Les frameworks complets — rédiger, éprouver, puis décider où vit l'adaptation

## Pourquoi cette roadmap (arbitrage de l'utilisateur, 2026-09-28)

Le maillon 3 du lot 7 posait la question : vers quelle grille reclasser Revolution Medicines après
l'approbation de RASONQUE (26/08) ? La réponse de l'utilisateur a déplacé le problème :

> « Il me semblait que les frameworks étaient agnostiques à l'entreprise mais peut-être qu'on a
> découvert que ce n'était en réalité jamais possible et donc qu'il faut un agent pour adapter le
> framework à l'entreprise voire même à son stade de maturité. Ou bien peut-être qu'on complète
> simplement le framework « marché » une fois que les produits sont commercialisés […]. Il me semble
> que nous allons rapidement avoir besoin de rédiger l'ensemble des frameworks prévus par la spec et
> de les tester sur des cas concrets pour voir s'il faut des adaptations par entreprise et à quel
> niveau les mettre dans notre architecture. »

**Ce qu'on sait déjà (mesuré sur NVDA / MSFT / RVMD)** : les 13 questions des deux pilotes ont servi
aux trois titres sans réécriture — le framework est agnostique **au niveau de la question**.
L'adaptation vit à deux étages : le **stade** (`archetypes`, 3 valeurs écrites à la main, une
variable par question) et l'**entreprise** (le traducteur écrit le plan de collecte titre par titre).
L'approbation RVMD montre que l'étage « stade » est une **liste fermée** : le défaut de la grille de
19, un étage plus haut.

**Ce que ferait un vrai fonds** : le directeur de la recherche fixe les grilles de couverture par
stade (acte rare, validé) ; l'analyste les adapte à chaque entreprise à l'initiation (travail
courant). Les questions « prix de lancement, parts de marché, réaction des concurrents » appartiennent
aux frameworks non écrits : une fois là, le passage en phase commerciale **rend applicables** des
questions existantes au lieu d'exiger une grille neuve.

## Principe directeur

- **Ajouter une méthodologie est une opération de DONNÉES** (arbitrage du 2026-09-24) : chaque
  framework s'écrit dans `app/frameworks/frameworks.yaml`, sans une ligne de Python. Si un framework
  exige du code, c'est un constat à consigner, pas un détour à prendre en silence.
- **Co-écrit question par question avec l'utilisateur**, en termes de fonds (PRINCIPES-FONDATEURS
  §1) ; chaque question déclare ce qui la rouvre (`rouverte_par`, requis) et sa variable par stade.
- **Les questions dérivent de la méthodologie** (benchmark Partie B), jamais de ce que la base
  contient (§0.6 de la spec 03).
- **Information attendue ≠ information manquante** (arbitrage du 2026-09-28) : une donnée
  légitimement pas encore publiée (les premières ventes d'un produit tout juste approuvé) est
  recherchée, mais ne bloque pas le dossier et ne déclenche ni alerte ni revue de position.
- **On ne décide pas du niveau d'adaptation avant d'avoir mesuré** (capacité 6). Pas d'agent
  « concepteur de grille » par anticipation.
- Lecture automatique des communiqués **coupée** (`v2_auto_enabled = FALSE`, arbitrage du
  2026-09-28) : on construit le système de bout en bout sur les exemples ; les autres titres du
  portefeuille viendront une fois le système conçu.

## Capacités (ordre imposé)

**Pourquoi cet ordre** : le modèle économique est l'étape 3 du processus canonique, la première de
l'analyse. Tout le reste s'y adosse. Secteur et concurrence vient ensuite parce que c'est lui qui
porte les questions de marché révélées par RVMD et, plus tard, les événements extérieurs à
l'émetteur. Le management se juge sur l'allocation d'un capital dont les frameworks précédents
disent le rendement. La valorisation vient en dernier, parce qu'elle consomme tous les autres. On
n'éprouve qu'une fois les quatre écrits, pour mesurer l'adaptation sur l'ensemble, pas sur un
framework isolé.

### 1. Framework « Modèle économique » (étape 3, bloc `business_model`) · contexte partagé : `frameworks.yaml`, contrat `framework_definition_schema.py`, benchmark Partie B
- [ ] Questions proposées en termes de fonds, validées une à une par l'utilisateur
- [ ] Écrit en YAML : énoncé, ingrédients, `rouverte_par`, `sens_admis`, variable par stade
- [ ] `bash checks/run_all.sh` vert, dont `check_frameworks_definitions` et `check_memo_projete`
- **Acceptation** : le chapitre `business_model` du mémo projeté passe de l'état
  `pas_de_methodologie_approuvee` à `sans_acquittement` (« aucune réponse au dossier ») pour NVDA,
  MSFT et RVMD ; `git diff --stat` du lot ne
  touche **aucun** `.py` sous `app/` (la méthodologie est une donnée).

### 2. Framework « Secteur et concurrence » (étape 7, bloc `industry`) · même contexte
- [ ] Questions validées une à une (structure du secteur, position face aux pairs, cycle, menaces)
- [ ] Déclare les questions que rouvrent les événements des concurrents : c'est la matière du sprint
  de design « événements extérieurs à l'émetteur »
- [ ] Suite verte
- **Acceptation** : identique à la capacité 1, sur le bloc `industry`.

### 3. Framework « Management et allocation du capital » (étape 6, bloc `management`) · même contexte
- [ ] Questions validées une à une (grille Thorndike : réinvestissement, rachats au bon prix,
  acquisitions, incitations)
- [ ] Suite verte
- **Acceptation** : identique à la capacité 1, sur le bloc `management`. Le type d'événement
  `gouvernance` rouvre enfin quelque chose (aujourd'hui `portee: aucune`, faute de méthodologie).

### 4. Framework « Valorisation » (étape 8, bloc `valuation`) · même contexte
- [ ] Questions validées une à une (fourchette de valeur, ce que le prix suppose, marge de sécurité)
- [ ] Nommer ce qui dépend du cours coté, daté (#81)
- [ ] Suite verte
- **Acceptation** : identique à la capacité 1, sur le bloc `valuation`.

### 5. Éprouver les six frameworks sur les cas réels · contexte partagé : chaîne `executer_chaine`, parcours, `tools/montrer_parcours.sh`
- [ ] Chaîne complète sur NVDA, MSFT, RVMD pour les quatre nouveaux frameworks (le rachat de
  données en test n'est pas une dépense à éviter, arbitrage du 22/09)
- [ ] Un 4ᵉ titre d'un stade non encore représenté (`financiere` : aucun des trois ne l'est) —
  penser à `websearch._ISSUER_DOMAINS` et `source_registry._TICKER_SECTEURS`
- [ ] Table de mesure versionnée : par (titre × framework), questions sans objet, variables que le
  traducteur a dû écrire pour l'entreprise, matière « attendue, pas encore publiée »
- **Acceptation** : la table existe, produite par un mesureur versionné (jamais à la main), et
  chaque case est un compte ou un état nommé — aucune case vide.

### 6. Décider à quel niveau vit l'adaptation · contexte partagé : la table de la capacité 5, spec 03 §9.3
- [ ] Appliquer le critère de la spec 03 §9.3 (≥ 5 titres, > ⅓ de sans objet pour un même stade)
- [ ] Présenter à l'utilisateur, en termes de fonds, les deux ou trois organisations possibles
  (stades écrits à la main · agent concepteur de grille validé par le comité · frameworks par stade)
- **Acceptation** : l'arbitrage de l'utilisateur est consigné (convention du `CLAUDE.md` projet),
  avec la mesure qui l'a fondé.

### 7. RVMD passe en phase commerciale — le reclassement proposé au comité (ex-maillon 3) · contexte partagé : `note_flash`, `ticker_archetypes` (046), `comite`, `parcours`
- [ ] Une note flash distingue l'**autorisation de mise sur le marché** d'un simple succès d'essai
  (sur RVMD : #80 seule, pas #83/#84/#85)
- [ ] Le système **propose** le changement de stade ; le comité valide ou écarte, motif écrit
- [ ] État « attendu, pas encore publié » : recherché, sans alerte ni blocage
- **Acceptation** : sur RVMD, une seule proposition (celle de l'approbation du 26/08) ; écartée par
  le comité, elle ne revient pas ; validée, le stade change à la date de la décision et les questions
  nouvellement applicables sont « attendues », pas « manquantes » dans l'alerte « peut-on décider ? ».

### 8. Position détenue sous revue (ex-maillon 4, arbitrage Q5) · contexte partagé : thèse V2, hypothèses et seuils
- [ ] Une question rouverte qui porte une hypothèse de la thèse met la position sous revue
- **Acceptation** : sur une thèse de test, rouvrir la question sous-jacente fait passer la position
  sous revue ; rouvrir une question sans hypothèse n'y change rien (test négatif).

### 9. Acceptation T1-T8 et réconciliation à 0/0 sur l'ensemble (ex-fin du lot 7)
- [ ] `tools/acceptation_frameworks.py` sur les six frameworks
- **Acceptation** : T1-T8 verts ; réconciliation des vocabulaires à 0/0.
