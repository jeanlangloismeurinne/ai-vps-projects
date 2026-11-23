# Reprise — sous-projet CAC 40 (valeur du temps passé, version européenne)

Sous-projet du sous-projet NASDAQ (`00-REPRISE-NASDAQ.md`, même dossier). **Indépendant de portfolio-tracker** :
ne jamais modifier `roadmap/V3/00-REPRISE.md`, ne jamais committer `_governance/sdd/*`, ne rien lire ni écrire hors
des tables `nasdaq_*`. Ce qui existe et ce qui le garde : `ARCHITECTURE.md` § « CAC 40 » (même dossier).

## État (2026-11-23) — version 1 LIVRÉE, multiple des pires jours livré

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

## Lot du 2026-11-23 — multiple des pires jours LIVRÉ (commits `40e143d`, `650298d`)

- **Règle** (arbitrée le 2026-11-23, commune avec le Nasdaq) : multiple des pires jours = 5ᵉ centile des multiples
  cours ÷ bénéfice moyen 3 ans des 120 mois PRÉCÉDENTS (mois courant exclu, mois à état dégradé exclus) × 0,8 ;
  plancher = ce multiple × moyenne 3 ans. Moins de 36 multiples → pas de plancher, raison dite (`why`). Le ×15 a
  disparu partout (plancher, fantôme, PER à terme).
- **Bande** = sensibilité de la marge : 0,7 et 0,9 au lieu de 0,8 (`OWN_SENS`). **PER à terme ÷ ce multiple.**
  Fantôme = meilleur état réel des 10 ans × le même multiple. « Caduc » inchangé (il juge les bénéfices).
- **CAC 40 : multiple provisoire FIXE de 8** (`MARKETS.cac40.fixed_mult`, `mult_kind = "provisoire"`), bande 7-9,
  à retirer quand la table 2010-2019 existera. Choisi sur la mesure : multiples du CAC 40 depuis 2023 (40 titres,
  1 538 mois), 5ᵉ centile 7,1, 10ᵉ 8,4 ; percé 8,7 % des mois à 8 (16 % à 10, 39 % à 15). Banques, automobile,
  acier et pétrole s'y paient durablement moins : c'est ce que le multiple propre corrigera.
- **Position dans le cycle** : bénéfice 12 mois ÷ moyenne des 10 derniers exercices en monnaie d'aujourd'hui, sur la
  fiche, éclairage seul. CAC 40 : « non affichée — moins de 10 ans de bénéfices ».
- Garde : `check_nasdaq_valeur.py` 46 ok + 36/36 mutations ; `check_cac40_valeur.py` 44 ok + 30/30. Suite 7 167
  assertions, rouge connu seul.
- **Production** : Nasdaq 55/87 avec plancher, 5 sous le plancher (Nvidia 0,92, Amazon 0,96), médiane ×1,72 ;
  CAC 40 38/42, 1 sous le plancher (Crédit Agricole 0,92), médiane ×2,58.
- **À surveiller** : 17 titres Nasdaq n'ont pas de plancher faute de 36 multiples, souvent parce que leurs mois
  « caducs » sont exclus (certains en ont 0 à 3 sur 10 ans). Avant, ils avaient un plancher ×15, souvent marqué « caduc ».
  À juger : est-ce le bon message (« pas de plancher ») ou faut-il garder ces mois ?

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
  conditionne aussi le multiple des pires jours** : à sa livraison, retirer `fixed_mult` du CAC 40.
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
