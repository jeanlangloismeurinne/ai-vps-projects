# Reprise — sous-projet CAC 40 (valeur du temps passé, version européenne)

Sous-projet du sous-projet NASDAQ (`00-REPRISE-NASDAQ.md`, même dossier). **Indépendant de portfolio-tracker** :
ne jamais modifier `roadmap/V3/00-REPRISE.md`, ne jamais committer `_governance/sdd/*`, ne rien lire ni écrire hors
des tables `nasdaq_*`. Ce qui existe et ce qui le garde : `ARCHITECTURE.md` § « CAC 40 » (même dossier).

## État (2026-11-22) — version 1 LIVRÉE

- `europe.py` (sources seules ; formules dans `valeur.py`), `valeur.MARKETS` + `select()` (filtre par marché),
  `?market=` sur l'API, rafraîchi chaque jour après le Nasdaq (`job.py`). Pas de migration.
- Page `/nasdaq/valeur?m=cac40` : choix Nasdaq | CAC 40, périodes 3 et 5 ans, détail = `ValeurPanel` en euros,
  avertissement « multiple de 15 calibré sur la technologie américaine ».
- Garde : `check_cac40_valeur.py` 36 ok (fixture réelle) + `negatif_cac40_valeur.sh` 22/22 ; Nasdaq 26 ok + 16/16.
- Déployé (commits `9ea5fec`, `035931b`, `3a8c218`, `e7c6458`), vérifié dans le conteneur, captures relues.

**Acceptation mesurée en production :**
- 39/40 du CAC 40 avec plancher (ou « pas de plancher ») et PER à terme ; 38 décomposables sur 3 et 5 ans.
  Non passé : STMicroelectronics (2025 : ESEF IFRS 0,33 $ contre Yahoo US GAAP 0,18 $ → contrôle croisé hors
  tolérance, masqué avec sa raison). Non décomposables : Renault, Stellantis, Puma (pertes), STMicro.
- 9 valeurs de l'utilisateur : LVMH et Mersen **caducs**, Schneider et Hermès **valides**, Puma **pas de
  plancher** — conformes. **Kering : caduc, pas « pas de plancher »** : son exercice 2025 est bénéficiaire
  (+0,59 €) ; le sondage lisait le bénéfice 12 mois de Yahoo (−2,98 €, qui inclut le 1er semestre 2026). C'est le
  retard propre à l'état annuel (jusqu'à 16 mois), pas un défaut.
- Nasdaq : 87 lignes, 72 décomposables sur 10 ans, 21 caducs, aucune ligne CAC — identique à la ligne de base.
- Écran (`fc6cc8d`) : une baisse du cours se dit par ce qui a reculé (`Verdict` dans `ValeurPanel.js`, à partir des
  facteurs de l'API). LVMH 5 ans → « entièrement du multiple » (bénéfices réels +14,5 %/an, multiple −25 %/an) ;
  Kering 5 ans → « des bénéfices » (multiple +49 %/an). Aucun check ne garde ce texte (affichage seul).
- Référence CAC 40 dividendes réinvestis (`1d7000a`, `899bc30`) à côté du S&P 500 en euros : champ facultatif
  `home` (macro → `assemble` → `decompose`/`cumulative` ; absent du Nasdaq). Source `europe.HOME_INDEX = "CAC.PA"`
  (fonds Amundi CAC 40 distribuant, cours ajustés, frais déduits) : Yahoo n'a pas le Gross Return (PX1GR.PA s'arrête
  en 2015) et C40.PA suit le CAC 40 ESG. Mesuré : 5 ans +6,4 %/an (indice de prix +3,0 %), 3 ans +5,8 % ; 38/38
  lignes décomposables l'ont ; Nasdaq 72 ok sur 10 ans, aucun facteur fantôme. Check 42 ok + 27/27 mutations.

## Ce que le lot a appris (choix qui s'écartent du plan initial)

- **Contrôle croisé** : ESEF contre Yahoo sur le même exercice, pas contre le bénéfice 12 mois (qui écartait Accor,
  Sanofi…). Sans exercice commun : `ok = None`, affiché.
- **Divisions** : la base d'actions d'un chiffre est celle du DÉPÔT qui le porte (un comparatif est déjà retraité :
  Air Liquide 2023).
- **Erreurs d'échelle des dépôts ESEF** (TotalEnergies 2022 ÷ 100, Capgemini 2022, Crédit Agricole 2019-2021 en
  millions, Renault 2020-2021 × 100) : facteur ≥ 10 avec le chiffre qui le répète → ce dernier ; erreur répétée
  sans chiffre sain → BPA ≥ 100 × la médiane de la série écarté. Toujours écrit dans la note.
- **filings.xbrl.org limite le débit** (~6 requêtes puis 429, fenêtre ~10 s) : client espacé de 2 s, attentes
  15/30/60 s. Passage complet ≈ 3 min (cache ESEF : seul l'index est relu).
- Bouygues ne déclare que le BPA « activités poursuivies » (repli de concept).

## Reste à faire

- **Revue Euronext du 10/12/2026** (effet 21/12) : relever la composition et mettre à jour `CAC40` + `CAC40_AS_OF`.
- Résidu connu : TotalEnergies 2020 (−0,029 $ au lieu de −2,90 $, aucun chiffre sain pour le démentir ; perte dans
  les deux cas, sans effet).
- La table manuelle des bénéfices 2010-2019 (chiffre publié à l'époque, avec source et date) → 10 ans. **Elle
  conditionne aussi le multiple plancher propre au titre** (ci-dessous) : sans elle, le CAC 40 n'a que ~3 ans de
  multiples, moins que les 3 ans d'historique exigés.
- **Multiple plancher propre au titre — ARBITRÉ le 2026-11-23, À CONSTRUIRE** (commun avec le Nasdaq). Règle :
  multiple du titre = 5ᵉ centile de son propre cours ÷ bénéfice moyen 3 ans sur les 10 années PRÉCÉDENTES (lu à
  chaque date, sans regarder l'avenir ; mois où l'état est dégradé exclus), × 0,8 de marge. **Le ×15 disparaît,
  y compris comme repère** : moins de 3 ans de multiples → pas de plancher, raison affichée (tout le CAC 40
  jusqu'à la table). « Bon marché » s'apprécie par rapport à soi ; le multiple peut changer quand l'entreprise
  change de métier (la fenêtre glissante de 10 ans le permet). Mesuré sur 58 titres Nasdaq 2010-2026 :
  percé 2,5 % des mois (×15 : 10,8 %), 1 titre percé > 20 % du temps (×15 : 9), cours à 1,8× le plancher en
  médiane (×15 : 2,0×), 6 titres à plus de 3× (×15 : 18). Tient sur 2010-2017, 2018-2026 et la baisse de 2022.
  **Par secteur écarté** : le secteur explique 8 % des écarts de multiple bas entre titres (Technologie : Micron
  5, Palo Alto 77), et la règle par secteur ne fait pas mieux que ×15. Changement de sens à faire trancher : sous
  le plancher = « payé aussi peu que ses pires jours de la décennie », plus « bon marché dans l'absolu » (Nvidia et
  Amazon y sont aujourd'hui ; Micron et GM ont un plancher à ×4). Restants percés > 10 % : eBay, Amazon, Comcast,
  Meta, Gilead.
- **Plancher propre au titre + position dans le cycle — fonctions pures LIVRÉES, non branchées (2026-11-23).**
  `valeur.own_floor` et `valeur.cycle_position` (non commitées) ; check Nasdaq 41 ok, test négatif 30/30. Mesuré sur
  la production (76 titres, 2010-2026, copie temporaire du module, rien écrit) : percé 2,0 % des mois, 3 titres
  percés > 20 %, cours à 1,72× le plancher en médiane, NVDA et AMZN sous le plancher aujourd'hui (0,92 / 0,96),
  MU et GM à ×4,5 / ×3,8 — conforme à la mesure d'arbitrage. **Reste à décider avant de brancher** : sort de la
  bande 12/15/20 (`floor_lo`/`floor_hi`), de la ligne fantôme, de « caduc » et du « PER à terme ÷ 15 » ; textes
  d'écran (`ValeurPanel.js` : « multiple plancher de 15 », ligne 244) ; le sens « payé aussi peu que ses pires
  jours ». Le CAC 40 affichera « pas de plancher » partout tant que la table 2010-2019 n'existe pas.
- **Titres cycliques — question ouverte** (2026-11-23). Mesuré (16 semi-conducteurs Nasdaq, règle ci-dessus) : le
  plancher ne casse pas (percé 1 %) mais il est lointain (cours à 2,5× contre 1,8× pour les autres) et oscille
  avec le cycle, parce que la moyenne 3 ans tombe sur un sommet ou un creux. Base « moyenne réelle sur 10 ans » :
  semis 1,9×, percé 0,2 % ; autres 1,5× mais percé 3,4 % (contre 2,1 %), et il faut 13 ans d'historique. Nvidia
  est cyclique dans ses comptes : baisses du bénéfice réel ≥ 30 % en 2011, 2018-19 (crypto), 2022-23 (−57 %) ;
  aujourd'hui bénéfice 12 mois 7,91 $ contre 2,58 $ (moyenne 3 ans) et 1,25 $ (moyenne réelle 7 ans). Pistes :
  base plus longue pour tous, base selon la cyclicité mesurée du titre, ou indicateur « position dans le cycle ».
  La mesure de cyclicité par les baisses du bénéfice PUBLIÉ est polluée par les charges exceptionnelles
  (Microsoft 2012) : lien avec le retraitement ci-dessous.
  **ARBITRÉ le 2026-11-23 : À CONSTRUIRE = l'indicateur « position dans le cycle »**, la base du plancher reste la
  moyenne 3 ans. Définition : bénéfice des 12 derniers mois ÷ moyenne réelle des 10 dernières années (chaque
  exercice ÷ inflation, remis en monnaie d'aujourd'hui), affiché « bénéfices actuels = N× leur moyenne de cycle »
  sur la fiche ; éclairage seulement, n'entre dans aucun calcul. Sans 10 ans de bénéfices : non affiché, raison
  dite (CAC 40 jusqu'à la table). Moyenne ≤ 0 : « pas de moyenne de cycle (pertes) ».
  **ROADMAP** : base du plancher dont la longueur dépend de la cyclicité MESURÉE du titre — après le retraitement
  ou la table 2010-2019, qui rendront la mesure de cyclicité propre.
- **Retraitement du bénéfice → ROADMAP** (arbitré le 2026-11-23 : on reste au bénéfice PUBLIÉ). Signaler les
  années où le retraitement change le résultat revient à calculer le bénéfice ajusté, et aucune source automatique
  ne tient : Yahoo « Normalized Income » ne couvre que 4 exercices, ne respecte pas sa propre identité (publié −
  exceptionnels + impôt) sur environ un tiers des années, et classe en exceptionnel des revenus courants (CME :
  revenus de placement → bénéfice « normalisé » négatif) ; il ignore l'amortissement d'acquisition
  (EssilorLuxottica identique au publié). L'ESEF ne porte le chiffre ajusté de la société que dans des concepts
  propres à chacune (Kering oui, Safran et EssilorLuxottica non). Voie retenue pour plus tard : relever le
  bénéfice ajusté à la main avec la table 2010-2019 (même source, le rapport annuel).
