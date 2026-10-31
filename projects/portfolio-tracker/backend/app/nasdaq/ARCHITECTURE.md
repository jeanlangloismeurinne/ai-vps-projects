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
