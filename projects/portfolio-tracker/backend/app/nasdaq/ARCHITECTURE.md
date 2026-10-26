# nasdaq — suivi NASDAQ (spec du 2026-10-26)

Module indépendant du reste du portfolio-tracker (tables `nasdaq_*`, migration `nasdaq_01_suivi.sql`,
page `/nasdaq`). Aucune dépendance vers les agents, la KB ou les tickers V1/V2.

| Fichier | Rôle |
|---|---|
| `universe.py` | univers = `nasdaqlisted.txt` (hors ETF/test) + screener Nasdaq (capitalisation) ; filtre warrants/droits/préférentielles ; une ligne par entreprise (la plus liquide) |
| `indicators.py` | fonctions pures : ancienneté du cours (première date où le cours a touché le niveau du jour), multiple 10 ans, nettoyage des aberrations |
| `job.py` | job quotidien (17h30 New York, lun-ven) : cours yfinance ajustés `period=max` par lots → `nasdaq_prices` → instantané `nasdaq_indicators` ; dégradé ⟹ aucun instantané écrit, la veille reste servie + avertissement |
| `../api/nasdaq.py` | `GET /nasdaq/snapshot`, `/status`, `/history/{ticker}`, `POST /nasdaq/run` |

Décisions prises à la place des « points à confirmer » (§9) : alerte active tant que ≥ 12 mois ; ATL = alerte,
badge « ATL », bulle posée à la valeur maximale de l'axe X ; capitalisation minimale par défaut 1 Md$.
Idempotence : un instantané est clé par la dernière séance US couverte ; relancer le même jour le remplace.

Seuil d'analyse : `MIN_MARKET_CAP_USD` (job.py, 50 Md$) — seules les entreprises au-dessus sont téléchargées et calculées ; capitalisation inconnue = exclue. Le filtre de la page ne peut que relever ce seuil.
