# nasdaq — suivi NASDAQ (spec du 2026-10-26)

Module indépendant du reste du portfolio-tracker (tables `nasdaq_*`, migration `nasdaq_01_suivi.sql`,
page `/nasdaq`). Aucune dépendance vers les agents, la KB ou les tickers V1/V2.

| Fichier | Rôle |
|---|---|
| `universe.py` | univers = `nasdaqlisted.txt` (hors ETF/test) + screener Nasdaq (capitalisation) ; filtre warrants/droits/préférentielles ; une ligne par entreprise (la plus liquide) |
| `indicators.py` | fonctions pures : ancienneté du cours (première date où le cours a touché le niveau du jour), multiple 10 ans, nettoyage des aberrations ; `series_tail` = les mêmes indicateurs à chacune des ~260 dernières séances (vectorisé, même définition) |
| `job.py` | job quotidien (17h30 New York, lun-ven) : cours yfinance ajustés `period=max` par lots → `nasdaq_prices` → instantané `nasdaq_indicators` ; dégradé ⟹ aucun instantané écrit, la veille reste servie + avertissement |
| `../api/nasdaq.py` | `GET /nasdaq/snapshot`, `/status`, `/history/{ticker}`, `/series`, `/series/{ticker}?range=1y|5y|max` (fiche), `/watchlist` (GET, PUT/DELETE `/{t}`), `/search?q=`, `/proba/{ticker}?years=`, `/proba-calib`, `POST /nasdaq/run` |

Décisions prises à la place des « points à confirmer » (§9) : alerte active tant que ≥ 12 mois ; ATL = alerte,
badge « ATL », bulle posée à la valeur maximale de l'axe X ; capitalisation minimale par défaut 1 Md$.
Idempotence : un instantané est clé par la dernière séance US couverte ; relancer le même jour le remplace.

Seuil d'analyse : `MIN_MARKET_CAP_USD` (job.py, 50 Md$) — seules les entreprises au-dessus sont téléchargées et calculées ; capitalisation inconnue = exclue. Le filtre de la page ne peut que relever ce seuil.

Suivi dans le temps : `/series` reconstitue, depuis les cours déjà stockés (rien de nouveau en base), l'ancienneté et le multiple de chaque titre à chaque séance récente ; il est mis en cache par instantané. Le front en tire le **saut** = ancienneté du jour − ancienneté d'il y a N séances − temps écoulé (mois ; 0 pour un titre stable), la traînée du graphique (position d'il y a 1 sem./1 mois/3 mois), le classement « plus fortes hausses » et la fiche par titre (`TickerSheet.js`). Les filtres de capitalisation de la page sont des filtres d'affichage ; l'analyse reste bornée par `MIN_MARKET_CAP_USD`.

## Probabilité de nouveau plus haut à 12 mois (`proba.py`)

Régression logistique unique (IRLS numpy, ridge 1) sur six variables connues à la date : distance au plus haut, temps depuis ce plus haut, momentum 6 et 12 mois, volatilité 12 mois, ancienneté de cotation. Une observation par mois et par titre, résultat = nouveau plus haut dans les 252 séances suivantes.

- **Passé seul** : le modèle de l'année Y n'apprend que des observations dont `day_end` (date où le résultat est connu) ≤ 1ᵉʳ janvier de Y (assert dans `fit_all`) ; avant le premier modèle viable, pas de courbe. Gardé par `checks/check_nasdaq_proba.py` (p(t) identique sur la série tronquée en t ; test négatif avec une variable qui regarde l'avenir). Fuite connue et négligeable : `clean_series` juge une pointe isolée avec la séance suivante.
- **Résultat par point** (`outcomes`) : 1 atteint / 0 manqué (fenêtre complète) / null en cours ; vert, rouge, gris côté front.
- **Tables** (`nasdaq_02_watchlist_proba.sql`, à appliquer à la main) : `nasdaq_watchlist`, `nasdaq_proba_model` (un modèle par année), `nasdaq_proba_calib` (AUC, fiabilité, taux de réussite par seuil, hors échantillon).
- **Cycle** : `ensure_models()` en fin de `run_daily` réapprend si aucun modèle n'existe pour l'année en cours (échec isolé : ne fait pas échouer le job).
- **Front** : `pages/nasdaq/index.js` (accueil : cartes de la liste + recherche + « Explorer »), `pages/nasdaq/explorer.js` (graphiques, segmentation capitalisation par défaut) ; `SlidePanes.js` fait glisser la page vers la fiche (`?t=` en routage superficiel, le retour navigateur referme la fiche) ; `ProbaChart.js`, `ProbaPanel.js`, `WatchButton.js`.

## Valeur du temps passé (`valeur.py`, 2026-11-22)

Question : d'où vient la hausse du cours (inflation, croissance réelle des bénéfices, multiple, dividendes), et à combien de fois son « plancher » le titre se paie-t-il. Détenteur UNIQUE des formules (docstring du module) ; les écrans ne font que dessiner.

- **Données** (rafraîchies en fin de `run_daily`, échec isolé) : BPA dilué déposé à la SEC (`companyfacts`, première publication, T4 = exercice − 9 mois, divisions d'actions ajustées valeur par valeur à SA date de dépôt), cours BRUTS mensuels yfinance (`auto_adjust=False` : un cours ajusté des dividendes abaisse le passé et fabrique des percées), inflation CPI (décalée d'un mois de publication), S&P 500 dividendes réinvestis, consensus +1 an (photo hebdomadaire `nasdaq_forward`). Contrôle croisé : bénéfice des 12 derniers mois comparé à celui de Yahoo (`EPS_CHECK`) → note « incohérent » (certificats de dépôt, devise, élément exceptionnel).
- **Tables** (`nasdaq_03_valeur.sql`, appliquée le 2026-11-22) : `nasdaq_valeur_series` (une ligne par titre, payload mensuel), `nasdaq_macro`, `nasdaq_forward`.
- **Choix mesurés** (mémoire `project_nasdaq_valeur_temps_passe`) : plancher = moyenne 3 ans × multiple des pires jours (5ᵉ centile des multiples des 10 ans précédents × 0,8, bande = marge 0,7-0,9 ; remplace ×12/15/20 le 2026-11-23, percé 2 % des mois sur 76 titres) ; CAC 40 au multiple provisoire fixe de 8 jusqu'à la table 2010-2019 ; « meilleur état des 10 ans » seulement en ligne fantôme ; décomposition et PER sur les 12 derniers mois ; bénéfice PUBLIÉ (arbitré le 2026-11-23 ; le retraitement est en roadmap, `00-REPRISE-CAC40.md`).
- **API** : `/nasdaq/valeur/summary?period=3y|5y|10y|2010`, `/nasdaq/valeur/{t}`, `/nasdaq/valeur-status`, `POST /nasdaq/valeur/run`.
- **Front** : onglet « Valeur » de la fiche (`ValeurPanel.js` : phrase, cascade, cours face au plancher, rapport au plancher, PER à terme, aire empilée repliée), badge des cartes (`ValeurBadge.js`, `?v=valeur` ouvre l'onglet), page comparative `pages/nasdaq/valeur.js`.
- **Garde** : `checks/check_nasdaq_valeur.py` (fixture réelle Nvidia : deux divisions, dont une au milieu d'un exercice) + `negatif_nasdaq_valeur.sh` (16 mutations).

## Valeur du temps passé — CAC 40 (`europe.py`, 2026-11-22)

Sous-projet `00-REPRISE-CAC40.md`. `europe.py` ne porte que des SOURCES ; les formules restent dans `valeur.py`.
- **Univers** : `CAC40` (composition datée, relevée le 2026-11-22 ; prochaine revue Euronext le 10/12/2026) + `EXTRA` (Mersen, Puma), chacun avec ISIN et LEI (GLEIF par l'ISIN ; ArcelorMittal : LEI de la mère).
- **Bénéfice** : BPA dilué ANNUEL, connu 4 mois après la clôture. ESEF d'abord (`filings.xbrl.org` par LEI ; concept dilué → de base → « activités poursuivies » ; fin de période xBRL-JSON EXCLUSIVE), chiffre du plus ancien dépôt qui le porte, divisions ajustées selon la publication du DÉPÔT source (un comparatif est déjà retraité) ; Yahoo `income_stmt` comble (déjà retraité des divisions). Erreur d'échelle (facteur ≥ 10 entre deux chiffres d'un exercice : TotalEnergies 2022 ÷ 100, Capgemini 2022) → le chiffre qui le répète.  Erreur répétée sans chiffre sain (Crédit Agricole 2019-2020, en millions) : un BPA ≥ 100 × la médiane de la série tombe. Écart > 5 % → note. Cache ESEF dans le payload (`esef.ids`) : rien n'est retéléchargé tant que la liste des dépôts ne change pas ; un index injoignable garde le cache et le dit.
- **Contrôle croisé** : ESEF contre Yahoo sur le dernier exercice COMMUN (`EPS_CHECK`), pas contre le bénéfice 12 mois de Yahoo (le semestre suivant y entre). Sans exercice commun : `ok = None`, affiché.
- **Macro** : inflation France (FRED `CP0000FRM086NEST`, +1 mois), S&P 500 dividendes réinvestis ÷ EURUSD, et la référence nationale `home` = CAC 40 dividendes réinvestis (`HOME_INDEX` = fonds Amundi `CAC.PA` en cours ajustés : Yahoo n'a pas le Gross Return) → `nasdaq_macro` série `valeur_cac40`. `home` est facultatif : absent (Nasdaq), aucun facteur ni courbe. Pas de migration.
- **Marchés** (`valeur.MARKETS`) : macro, devise, libellés, périodes (CAC 40 : 3 et 5 ans ; 10 ans → « historique insuffisant »). `select()` filtre par `payload.market` (absent = Nasdaq) : la page Nasdaq et ses badges ne voient pas le CAC 40.
- **API** : `?market=nasdaq|cac40` sur `/nasdaq/valeur/summary`, `/valeur-status`, `POST /valeur/run` ; `/nasdaq/valeur/{t}` déduit le marché de la ligne. Rafraîchi chaque jour après le Nasdaq (`job.py`, échec isolé).
- **Front** : choix Nasdaq | CAC 40 sur `pages/nasdaq/valeur.js` (`?m=cac40`), détail = `ValeurPanel` seul ; libellés venus de l'API.
- **Garde** : `checks/check_cac40_valeur.py` (fixture réelle : Air Liquide, Bouygues, LVMH, TotalEnergies, Capgemini, Kering) + `negatif_cac40_valeur.sh` (27 mutations).
