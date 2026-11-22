# Reprise — sous-projet CAC 40 (valeur du temps passé, version européenne)

**Créé le 2026-11-22.** Étendre la « valeur du temps passé » (`valeur.py`, livrée sur le Nasdaq) aux sociétés
du CAC 40, plus quelques valeurs hors indice que l'utilisateur détient ou suit. On fait **l'ajout le plus
simple** : on réutilise le calcul tel quel et on change seulement les sources. Une société trop compliquée
peut ne pas passer, à condition d'être listée avec sa raison.

Ce chantier est un sous-projet du sous-projet NASDAQ (`00-REPRISE-NASDAQ.md`, même dossier). Il est
**indépendant de portfolio-tracker** :
- ne jamais modifier `roadmap/V3/00-REPRISE.md` ;
- ne jamais committer `_governance/sdd/*` ;
- ne rien lire ni écrire hors des tables `nasdaq_*`.

## Objectif

**Livré quand :**
1. une page « Valeur du temps passé » propose un choix Nasdaq | CAC 40 ;
2. pour **chaque société du CAC 40**, et pour les valeurs suivies hors indice (au départ Mersen `MRN.PA` et
   Puma `PUM.DE`), elle affiche :
   - le plancher d'aujourd'hui et le rapport cours / plancher ;
   - le PER à terme ;
   - la décomposition de la hausse sur 3 ans, et sur 5 ans quand l'historique suffit ;
3. les sociétés qui ne passent pas sont listées avec leur raison.

**Hors champ (version 1) :**
- **la décomposition sur 10 ans** : il faudrait relever à la main les bénéfices 2010-2019 dans les rapports
  annuels (environ 1 séance pour 9 valeurs) ;
- **le recalibrage du multiple plancher par titre ou par secteur** ;
- **le module de chutes et les probabilités** : l'onglet « Cours » reste propre au Nasdaq.

## Sondage du 2026-11-22 (sur les 9 valeurs de l'utilisateur)

L'utilisateur détient ou suit EssilorLuxottica, Schneider, LVMH, Hermès, Kering, Saint-Gobain, Engie,
Mersen et Puma.

| Donnée | Source | Couverture constatée |
|---|---|---|
| Cours bruts, dividendes, divisions | yfinance (`auto_adjust=False, actions=True`), symboles `.PA` / `.DE` | depuis 2000, en EUR |
| PER à terme | yfinance `earnings_estimate` (+1y) | 9/9, de 5 à 24 analystes |
| Bénéfice des 12 derniers mois (contrôle croisé) | yfinance `info.trailingEps` | 9/9 |
| Bénéfice par action annuel | yfinance `income_stmt` ligne `Diluted EPS` | **2022-2025 seulement** |
| Bénéfice par action annuel | ESEF via `filings.xbrl.org` (API JSON:API, filtre `entity.name ilike`) | 2020/2021-2025 pour 8/9 ; **Puma introuvable** ; Kering indexé seulement jusqu'à 2023 |
| Fournisseur payant FMP | clef du projet | **refusé** sur Euronext (402 Payment Required / 403) : écarté |

**Pas encore vérifié** : l'extraction du bénéfice dans un dépôt ESEF n'a pas été essayée. Elle consiste à
lire le xBRL-JSON du dépôt, le concept `ifrs-full:DilutedEarningsLossPerShare` (à défaut
`BasicEarningsLossPerShare`) et un contexte sans dimension. Chaque dépôt annuel contient aussi l'exercice
N-1, ce qui devrait donner 2019 ou 2020 en plus.

## Méthode — ce qui change par rapport au Nasdaq

**Inchangé (réutilisé sans modification) :**
- `floor_series`, `decompose`, `cumulative`, `summary`, `usable` ;
- les multiples 12 / 15 / 20 ;
- la règle « caduc » : état réel < 90 % du meilleur, ou moyenne 3 ans ≤ 0 ;
- le contrôle croisé `EPS_CHECK` contre Yahoo.

**Changements :**

1. **Le bénéfice est annuel, pas trimestriel.** Les sociétés françaises publient par semestre, et l'ESEF
   ne porte que l'annuel. L'« état » est donc le dernier exercice publié.
   - Proposition à valider au premier essai : un exercice est connu **4 mois après sa clôture** (délai
     légal du rapport financier annuel). C'est prudent ; les résultats annuels sortent souvent en
     février-mars.
   - Ne pas prendre `date_added` de `filings.xbrl.org`, qui peut être très postérieur à la publication
     (rattrapages).
2. **Fusion des sources :**
   - **ESEF** d'abord : c'est le chiffre publié à l'époque ;
   - **Yahoo `income_stmt`** en repli : c'est ce qui fera passer Puma ;
   - quand les deux se recouvrent, un écart supérieur à 5 % se signale dans la note du titre.
3. **Les divisions d'actions** s'appliquent comme sur le Nasdaq : chaque valeur est ajustée selon sa propre
   date de publication (piège déjà rencontré sur le Nasdaq : ajuster après coup fabrique des « caducs »).
4. **La devise est l'euro.** Les sociétés qui publient en dollars (ArcelorMittal, STMicroelectronics) passent
   par la conversion existante (`_fx_monthly`, `_fx_at`).
5. **La barre basse est l'inflation française**, avec un mois de décalage de publication comme sur le
   Nasdaq. La série FRED `CP0000FRM086NEST` (indice des prix harmonisé, France) est à vérifier.
6. **Le coût d'opportunité est le S&P 500 dividendes réinvestis, converti en euros** (`^SP500TR` ×
   `EURUSD=X`, deux séries déjà téléchargées). Un CAC 40 dividendes réinvestis est une amélioration
   possible, à sourcer plus tard.
7. **Les périodes possibles sont 3 ans et 5 ans.** « 10 ans » et « Depuis 2010 » renvoient « historique
   insuffisant » tant que la table manuelle 2010-2019 n'existe pas.
8. **Un multiple de 15 est mal adapté** au luxe (Hermès se paie environ 50 fois ses bénéfices, donc
   « ×3 le plancher » en permanence), aux banques et aux services publics.
   - En version 1 on le garde et on l'écrit à l'écran.
   - Le recalibrage (multiple bas propre à chaque titre sur 15 ans) est un arbitrage pour plus tard.

## Univers

- **CAC 40** :
  - relever la composition **à la date du jour** sur le site d'Euronext ;
  - la figer en constante **datée** dans le code ;
  - ne pas l'écrire de mémoire : l'indice change chaque trimestre.
- **Valeurs hors indice** : une seconde constante `EXTRA` (au départ `MRN.PA`, `PUM.DE`).
- **Sociétés étrangères de l'indice** (Airbus, Stellantis, STMicroelectronics : Pays-Bas ; ArcelorMittal,
  Eurofins : Luxembourg) :
  - leur ESEF est déposé hors de France, à vérifier dans `filings.xbrl.org` ;
  - sinon, repli sur Yahoo.
- **Identification ESEF** : préférer le LEI, stable, au nom de la société. Une table code Yahoo → LEI se
  remplit une fois.

## Plan d'implémentation (le plus simple)

1. **Sondage** (½ séance) :
   - extraire le bénéfice ESEF de LVMH et de Schneider, et le comparer à Yahoo 2022-2025 ;
   - vérifier la série d'inflation France ;
   - compter combien des 40 sociétés ont un ESEF trouvable.
2. **Backend** : un nouveau fichier `backend/app/nasdaq/europe.py`, qui ne contient **que des sources**
   (aucune formule : `valeur.py` reste le détenteur unique des formules).
   - **Univers** : les constantes `CAC40` (datée) et `EXTRA`.
   - **Bénéfices** : `eps_points_esef(lei)`, puis `eps_points_yahoo(symbol)`, avec les dates de
     disponibilité et la fusion des deux sources.
   - **Inflation et référence** : `macro_eur()` donne l'inflation France et le S&P 500 en euros.
   - **Rafraîchissement** : `refresh_eu()` écrit dans les tables existantes. Il n'y a pas de migration :
     - `nasdaq_valeur_series` : clef = symbole Yahoo, sans collision avec le Nasdaq grâce au suffixe ;
       ajouter `"market": "cac40"`, `"currency": "EUR"` et les libellés (référence, inflation, source)
       dans le payload ;
     - `nasdaq_macro` : nouvelles séries `cpi_fr` et `sp500tr_eur` ;
     - `nasdaq_forward` : sans changement.
3. **Lecture** : `read_summary(period, market)` filtre par marché.
   - ⚠️ **Non-régression** : aujourd'hui, `read_summary` rend toutes les lignes de la table. Sans filtre,
     les sociétés françaises apparaîtraient dans la page Nasdaq **et dans les badges de l'accueil**.
     L'acceptation l'exige : le Nasdaq doit rester à 87 lignes, dont 72 décomposables sur 10 ans
     (mesure du 2026-11-22).
4. **API** : un paramètre `market=nasdaq|cac40` (défaut `nasdaq`) sur `/nasdaq/valeur/summary`. La
   relance se fait par `POST /nasdaq/valeur/run?market=cac40`.
5. **Planification** : le job quotidien du Nasdaq (`job.py`) appelle aujourd'hui `valeur.refresh()` dans un
   `try` isolé. Ajouter `europe.refresh_eu()` sur le même modèle, ou une fois par semaine pour ménager les
   requêtes ESEF (les comptes annuels changent une fois par an).
6. **Écrans** :
   - Dans `ValeurPanel.js`, remplacer ce qui est écrit en dur par les libellés du payload :
     - « $ » → devise ;
     - « S&P 500 » → libellé de la référence ;
     - « inflation américaine » → libellé de l'inflation ;
     - « comptes SEC » → libellé de la source.
   - Dans `pages/nasdaq/valeur.js` :
     - un choix « Nasdaq | CAC 40 » ;
     - en CAC 40, le volet de détail affiche `ValeurPanel` seul (`TickerSheet` dépend du snapshot
       Nasdaq) ;
     - une section « Non décomposables » avec les raisons (Puma attendu : en perte → pas de plancher).
   - Écrire à l'écran que **le multiple de 15 est calibré sur la technologie américaine**.
   - Pas de badge sur l'accueil Nasdaq.
7. **Garde** :
   - un `check_cac40_valeur.py` avec une **fixture copiée du réel** (un vrai dépôt ESEF réduit aux
     concepts lus, par exemple LVMH) ;
   - des asserts sur :
     - la date de disponibilité (+4 mois) ;
     - la fusion ESEF / Yahoo (priorité, signal d'écart) ;
     - la division d'actions par date de publication ;
     - le filtre par marché (non-régression Nasdaq) ;
   - un `negatif_cac40_valeur.sh` avec une mutation par règle ;
   - le bilan au format `N ok / M FAIL`.
8. **Déploiement** : `infrastructure/compose-deploy.sh portfolio-tracker`. Ensuite :
   - vérifier dans le conteneur (`docker exec portfolio-backend grep …`) ;
   - sonder l'API ;
   - faire des **captures sans interface** (`google-chrome --headless=new --screenshot=… URL`) et les
     relire avant de conclure.

## Test d'acceptation

- **Au moins 30 sociétés du CAC 40 sur 40** ont un plancher d'aujourd'hui (ou « pas de plancher : en
  perte ») et un PER à terme. Les autres sont listées avec leur raison.
- **Sur les 9 valeurs de l'utilisateur**, le résultat est cohérent avec le sondage (BPA Yahoo) :
  - Kering et Puma : **pas de plancher**, en perte ;
  - LVMH et Mersen : **caducs** (LVMH 21,9 € contre 30,3 € en 2023 ; Mersen 0,57 € contre 3,42 €) ;
  - Schneider et Hermès : planchers **valides**.
  - Si ce n'est pas le cas, chercher pourquoi avant de corriger.
- **EssilorLuxottica** : depuis la fusion d'octobre 2018, seule la période postérieure a un sens. Comme
  l'historique ESEF commence en 2020, rien n'est à faire en version 1 ; à noter pour la version sur 10 ans.
- **Non-régression Nasdaq** : 87 lignes, 72 décomposables sur 10 ans, badges inchangés.
- **Contrôles** : le check est vert et le test négatif détecte toutes ses mutations.

## Reste à faire après la version 1

- La table manuelle des bénéfices 2010-2019 (chiffre publié à l'époque, avec source et date), pour la
  décomposition sur 10 ans.
- Le recalibrage du multiple plancher par titre (multiple bas sur 15 ans) ou par secteur.
- L'arbitrage commun avec le Nasdaq : bénéfice publié ou ajusté. Il est plus pressant ici, avec les
  dépréciations d'Engie et de Kering et l'amortissement de l'acquisition chez EssilorLuxottica.
- Une référence CAC 40 dividendes réinvestis.
