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
- [x] Questions proposées en termes de fonds, validées une à une par l'utilisateur
- [x] Écrit en YAML : énoncé, ingrédients, `rouverte_par`, `sens_admis`, variable par stade
- [x] `bash checks/run_all.sh` vert, dont `check_frameworks_definitions` et `check_memo_projete`
- **Acceptation** : le chapitre `business_model` du mémo projeté passe de l'état
  `pas_de_methodologie_approuvee` à `sans_acquittement` (« aucune réponse au dossier ») pour NVDA,
  MSFT et RVMD ; `git diff --stat` du lot ne
  touche **aucun** `.py` sous `app/` (la méthodologie est une donnée).

- ✅ **Livré le 2026-09-28** : `me_1`…`me_6` (spec 03 §4.3). Acceptation mesurée par
  `tools/montrer_memo_projete.sh` : `business_model` en `sans_acquittement` sur NVDA/MSFT/RVMD ;
  contre-essai avec le référentiel d'avant → `pas_de_methodologie_approuvee`. Diff : YAML, spec,
  checks — aucun `.py` sous `app/`. Suite 3556/0 sur 51.

### 2. Framework « Secteur et concurrence » (étape 7, bloc `industry`) · même contexte
- [x] Questions validées une à une (structure du secteur, position face aux pairs, cycle, menaces)
- [x] Déclare les questions que rouvrent les événements des concurrents : c'est la matière du sprint
  de design « événements extérieurs à l'émetteur »
- [x] Suite verte
- **Acceptation** : identique à la capacité 1, sur le bloc `industry`.

- ✅ **Livré le 2026-09-28** : `se_1`…`se_6` (spec 03 §4.4), validées d'un bloc par l'utilisateur,
  recoupement `se_3`/`mo_2` accepté. **Option A** : 4 types d'événement d'origine `exterieur`
  déclarés (#93) — ⚠️ l'acceptation « aucun `.py` sous `app/` » ne tient PAS pour cette capacité, par
  décision annoncée (champ `origine` au contrat, garde [R], filtre de la note flash). Acceptation
  mesurée par `tools/montrer_memo_projete.sh` : `industry` en `sans_acquittement` sur NVDA/MSFT/RVMD ;
  contre-essai avec le référentiel d'avant → `pas_de_methodologie_approuvee`. Suite 3564/0 sur 51,
  `negatif_frameworks_definitions.sh` 31/31, 3 gardes neuves mutées au rouge. Aucun veilleur ne
  repère encore les événements extérieurs.

### 3. Framework « Management et allocation du capital » (étape 6, bloc `management`) · même contexte
- [x] Questions validées une à une (grille Thorndike : réinvestissement, rachats au bon prix,
  acquisitions, incitations)
- [x] Suite verte
- **Acceptation** : identique à la capacité 1, sur le bloc `management`. Le type d'événement
  `gouvernance` rouvre enfin quelque chose (était `portee: aucune`, faute de méthodologie).

- ✅ **Livré le 2026-09-28** : `ma_1`…`ma_6` (spec 03 §4.5), validées d'un bloc. `gouvernance` rouvre
  `ma_4`/`ma_5`/`ma_6` (catalogue 1.2.0, 9 notes relues) ; `financement` rouvre aussi `ma_1`/`ma_3`
  (arbitrage). Acceptation mesurée par `tools/montrer_memo_projete.sh` : `management` en
  `sans_acquittement` sur NVDA/MSFT/RVMD (`valuation`, non écrit, reste `pas_de_methodologie_approuvee`
  dans le même passage). Aucun `.py` sous `app/`. Suite 3566/0 sur 51, négatif 31/31 ; garde
  `gouvernance` mutée au rouge (check_evenements + check_frameworks_definitions).

### 4. Framework « Valorisation » (étape 8, bloc `valuation`) · même contexte
- [x] Questions validées une à une (fourchette de valeur, ce que le prix suppose, marge de sécurité)
- [x] Nommer ce qui dépend du cours coté, daté (#81)
- [x] Suite verte
- **Acceptation** : identique à la capacité 1, sur le bloc `valuation`.

- ✅ **Livré le 2026-09-28** (questions seulement, par découpage validé) : `va_1`…`va_6` (spec 03 §4.6).
  Deux groupes : ce que VAUT l'entreprise (va_1-3) et ce que le PRIX suppose (va_4-6, dépendants du
  cours coté daté). Ingrédients « repris de qf_x/mo_x/me_x/se_x » écrits en données ; le mécanisme de
  reprise n'existe pas (4 bis). Acceptation : `valuation` en `sans_acquittement` sur NVDA/MSFT/RVMD
  (`pas_de_methodologie_approuvee` au passage précédent) ; **6 chapitres sur 6** adossés à une
  méthodologie. Aucun `.py` sous `app/`. Suite 3566/0, négatif 31/31.

### 4 bis. L'atelier de valorisation (inséré le 2026-09-28) · contexte partagé : `framework_answer_schema`, `analyste`, `manager`, `traducteur`/`collecteur`, `formule_grammaire` (#72, précédent du calcul fermé), `analysis_v2_schemas.Valuation`

**Pourquoi** : sans lui, éprouver la valorisation (capacité 5) mesurerait surtout les erreurs de calcul
d'un modèle de langage — instable d'un passage à l'autre, mesuré.

**Arbitrages de l'utilisateur (2026-09-28)**
- **Option 1** : ce qui dépend du cours (va_4-6) n'est jamais figé — recalculé à la lecture au dernier
  cours coté, daté ; la fourchette (va_1-3) ne bouge que sur un fait nouveau.
- **La valorisation s'instruit APRÈS** les frameworks dont elle reprend les chiffres.
- **Une base commune de calculs, ET des capacités d'exécution de code propres à chaque entreprise** :
  « le CA futur de RVMD s'apprécie sur le portefeuille de molécules et leur potentiel. Ce n'est pas du
  tout la même méthodologie pour NVDA. »

**Ce que ferait un vrai fonds** : des gabarits maison (DCF, valeur sans croissance, ce que suppose le
prix, valeur des programmes pondérée par probabilité de succès) ; et, à l'initiation, un MODÈLE PROPRE
à l'entreprise construit par l'analyste (somme des programmes pour une biotech, modèle par segment
pour NVDA), revu par le directeur de la recherche, puis CONSERVÉ d'une révision à l'autre — ce sont les
hypothèses qui changent, pas la mécanique. Le comité peut rouvrir le modèle et changer une hypothèse.

**Instruit avec l'utilisateur le 2026-09-29 (convention #96)** : l'agent PROPOSE la méthodologie
(dont la segmentation du marché, qu'il complète quand de nouveaux produits sont lancés), le comité
SIGNE ; mécanique LIBRE mais DÉCRITE par l'agent, le comité jugeant un tableau d'hypothèses chiffrées
et sourcées ; exécution dans un bac à calcul Python très simple ; la mécanique est refondue sur
changement de stade ou à la demande du comité, et un nouveau produit repéré en revue trimestrielle
peut y être ajouté (choix non questionné, à confirmer : marqué « ajouté, non encore revu » jusqu'à la
séance suivante).

- [ ] Reprise des réponses acquittées : un ingrédient « repris de » n'est jamais recollecté ; une seule
  valeur par dossier (le coût du capital de va_1 EST celui de qf_1, même pièce)
- [ ] Ordonnancement : la valorisation n'est instruite qu'après les frameworks dont elle reprend
- [x] Base commune de calculs fermés et testés (valeur sans croissance, DCF à trois scénarios, croissance
  implicite dans le prix, valeur pondérée par probabilité, dilution, marge de sécurité) — ✅ 2026-09-29,
  `app/valorisation/calculs.py`, #96
- [x] Le bac à calcul où s'exécute la mécanique d'une entreprise (sous-ensemble de Python interprété,
  tableau signé gelé, frontière de sécurité) — ✅ 2026-09-29, `app/valorisation/bac_a_calcul.py`, #96 ;
  `check_bac_a_calcul.py` 255/0, négatif 26/0
- [ ] Modèle propre à l'entreprise, exécutable, versionné, validé : le CONTRAT (mécanique décrite en
  prose + segmentation + tableau d'hypothèses sourcées + code + version + signature du comité), sa
  persistance (migration 051), l'agent qui l'écrit, l'acte de signature du comité
- [ ] Réponse à PLUSIEURS nombres (le contrat de réponse n'en porte qu'un) — correspondance avec
  `Valuation` (§4.6 de la spec)
- [ ] Option 1 : va_4-6 recalculés à la lecture au dernier cours coté daté (#81)
- [ ] Règle de Greenwald tenue par le manager (la croissance ne vaut que si qf_1 crée de la valeur et
  que la barrière tient)
- [ ] Dépendance entre questions : rouvrir va_1/va_2 rouvre va_6 (aujourd'hui simulé par un
  `rouverte_par` large)
- **Acceptation** : sur RVMD et NVDA, deux modèles d'entreprise DIFFÉRENTS (somme des programmes /
  segments) donnent chacun une fourchette ; changer une hypothèse recalcule sans appel modèle ; le
  coût du capital de va_1 est celui de qf_1 ; au cours du jour, va_6 change sans que va_2 bouge.

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
- [ ] **Dette relevée le 2026-09-28 (#95)** : le suivi (`monitoring.py`) RÉESTIME la fourchette de
  valeur de la thèse (`valuation_range_updated`) — contraire à l'option 1 : la valeur ne bouge que sur
  un fait nouveau passé par l'analyste et le manager ; le suivi ne recalcule que ce qui dépend du cours
- **Acceptation** : sur une thèse de test, rouvrir la question sous-jacente fait passer la position
  sous revue ; rouvrir une question sans hypothèse n'y change rien (test négatif).

### 9. Acceptation T1-T8 et réconciliation à 0/0 sur l'ensemble (ex-fin du lot 7)
- [ ] `tools/acceptation_frameworks.py` sur les six frameworks
- [ ] **Constat du 2026-09-28 (#95)** : 6 chapitres sur 6 adossés, mais T6/T7 restent rouges (30 champs
  / 37 questions) — il manque le lien question → champ du mémo, et le raccordement du mémo projeté
  (texte) à bull/bear → décision → suivi → sortie, qui lisent l'ancien mémo CHIFFRÉ. Aucun chapitre
  n'est raccordé ; la valorisation est celle où le manque se voit le plus
- **Acceptation** : T1-T8 verts ; réconciliation des vocabulaires à 0/0.
