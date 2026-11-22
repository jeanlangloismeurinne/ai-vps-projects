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
- Écran (hérité du Nasdaq) : quand le cours baisse, la phrase dit « hausse entièrement méritée : le multiple n'a pas
  augmenté » (LVMH 5 ans) — à reformuler pour une baisse.
- La table manuelle des bénéfices 2010-2019 (chiffre publié à l'époque, avec source et date) → 10 ans.
- Le recalibrage du multiple plancher par titre (multiple bas sur 15 ans) ou par secteur.
- L'arbitrage commun avec le Nasdaq : bénéfice publié ou ajusté (dépréciations d'Engie, de Kering ; amortissement
  d'acquisition chez EssilorLuxottica ; IFRS contre US GAAP chez STMicro).
- Une référence CAC 40 dividendes réinvestis.
