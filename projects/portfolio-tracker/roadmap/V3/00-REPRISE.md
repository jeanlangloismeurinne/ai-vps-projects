---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-10-19 (points 10 et 12 construits ; point 9 en arbitrage ; mesure (e)) ; 2026-10-19 (ré-analyse qui dégrade, point 13, `6760090`) ; 2026-10-18 (demandes de recherche closes à la livraison, point 14, `8af6f4a` ; causes du point 13) ; 2026-10-18 (fraîcheur sujet par sujet, point 15, `331aa7c`) ; 2026-10-18 (changement de stade + classement par le comité, #139) ; 2026-10-18 (« pas encore observable », #138) ; 2026-10-17 (relance bornée + réinitialisation, `c2bc1af`) ; 2026-10-17 (séance d'arbitrages #137) ; 2026-10-16 (allègement : état complet copié dans 00-REPRISE-ARCHIVE.md, section « 2026-10-16 — COPIE CONFORME »)
project: portfolio-tracker
role: >
  Prompt de reprise du chantier V3. Ne porte que l'ÉTAT, le PROCHAIN PAS et les pointeurs. Récit →
  `00-REPRISE-ARCHIVE.md` ; règles durables → `CONVENTIONS.md` (index dans `CLAUDE.md`) ; preuve →
  `backend/checks/`. CE FICHIER NE S'EMPILE PAS : garder sous ~8 Ko, sortir le récit à chaque fin de lot.
---

# Prompt de reprise — portfolio-tracker V3

> **Lire d'abord `roadmap/V3/PRINCIPES-FONDATEURS.md`** (arbitrages en termes MÉTIER ; chaque décision
> éclairée par la pratique d'un VRAI fonds ; un raffinement se débraye vers la règle simple).

## ➜ Prochain pas

Ordre de `07-avant-comite.md` : (1) la matière — **close** ; (2) arbitrages — **rendus** (#137) ; (3) **tenue du
dossier** — (a) relance bornée ✅ `c2bc1af` ; (b) fraîcheur sujet par sujet ✅ `331aa7c` ; (c) mandats clos ✅
`8af6f4a` et ré-analyse qui dégrade ✅ `6760090` ; (d) données : **ma_2 reformulée (12) ✅ et taux exigé 10 %
(10) ✅ le 2026-10-19** (CONVENTIONS #137 « CONSTRUIT le 2026-10-19 ») ; **me_5 → tableau des marchés (9) : ABSORBÉ
par le modèle de l'entreprise (ci-dessous)** ; (e) « répondu sans le chiffre-objet » (11) **mesuré le 2026-10-19** ; puis (4) valorisation, (5) test.
**Jalon 1 = NVDA + RVMD** ; code générique. Modèle : Opus pour la conception, Sonnet délégué pour les mesures et
l'exécution bien spécifiée.
**PROCHAIN PAS : concevoir LE MODÈLE DE L'ENTREPRISE** (orientation de l'utilisateur, 2026-10-19, qui
englobe le point 9 — page d'analyse : https://claude.ai/artifact/54kCtG66c9i5GNjL8gDWig) : « un outil unique,
le modèle de l'entreprise, avec autant d'onglets que nécessaire pour une modélisation complète ; chaque question
de chaque framework y inscrit les informations pertinentes ; il sert à la fin à la valorisation ; il se remplit
dans le BON ORDRE car les questions ultérieures dépendent de décisions de structuration prises en amont (5 blocs
de marché ⟹ taille, croissance… par bloc ; coûts variables/marge par segment ; coûts fixes transverses) ;
vérification qualité ad hoc à chaque étape ; puis signature globale du tableau, voire analyse de sensibilité ».
À faire : SPEC soumise AVANT tout code — onglets et leur ordre de remplissage (structuration → données par
segment → transverse), ce que chaque question écrit / lit, la garde qualité par étape, raccordement aux comptes
reconstitués (socle) et aux décisions du fonds, signature globale, sensibilité (±1 pt du taux exigé déjà
décidé). Réutiliser : contrat `modele_valorisation_schema` (segments, hypothèses à 3 origines, jugement ancré),
bac à calcul, signature #98, socle #115, `parametres_du_fonds`.
**Mesure (e)** (16 réponses en vigueur à encadré) : 6 chiffres absents légitimes (n.s./n.c. : RVMD qf_2-5, NVDA
qf_7) ; 2 coûts du capital vides (fermés par le point 10 au prochain passage) ; 1 vrai cas NVDA qf_6 #1289 (« part
faible » sans aucun chiffre) ; 1 neuf : RVMD qf_6 #1679 rend ABSENTS des retraitements qui valent ZÉRO (l'émetteur
ne publie aucune mesure ajustée, #47). Remède à concevoir : `sens_lu_sur` ne lit aujourd'hui que des chiffres du
socle (`chiffres_du_socle`) — qf_6 porte sur un chiffre relevé, il faudrait une garde APRÈS rédaction (pont).
Le comité devra lire la baisse NVDA ma_1 (elle était juste : acquitter ou renvoyer). Dettes nommées :
`negatif_collecte_executor.sh` 43/44 (`FormuleInexecutable` non capturée autour de `recette_retenue`) ;
`synthesis_feed` titré par le modèle (sans appelant V3) ; l'outil d'acceptation ne remet pas le socle ni les
lectures ; `tools/acceptation_frameworks.py` (hors suite) a pour témoin `qf_1.cout_du_capital`, retiré le
2026-10-19 — choisir un nouveau témoin (un essentiel qu'aucune source déterministe ne sert) ; sensibilité ±1 pt du
taux et alerte de décision du fonds échue : au lot de la valorisation. Récits : archive.

## Où on en est (mesuré le 2026-10-16/17 — RE-REQUÊTER avant de s'en servir)

- **Jalon** (réduit le 2026-10-17 : **NVDA + RVMD** d'abord, puis financière US, puis étranger, MSFT en
  contrôle de reproduction) : note d'initiation (6 chapitres + fourchette), fonctionnement
  ET reproductibilité ; roadmap active `05-frameworks-complets.md` (A1-A3 cochés, A4 en cours).
- **Chapitres instruits** (`bash backend/tools/montrer_parcours.sh <TICKER>`, gratuit) :
  NVDA qualité financière 1,00 · défendabilité 0,17 · modèle économique 0,83 · secteur 0,50 ·
  management **2/7** (ma_6, ma_7 répondues — plan #270, réponses #1499-#1505 ; ma_4 #1506) · valorisation :
  rien. RVMD : qualité financière 1,00, défendabilité/modèle économique/secteur/management partiels.
  **MSFT : aucune réponse en vigueur.** Beaucoup de réponses sont « standard antérieur » (#127) : refaites
  à la reconstruction (premier passage du test), pas relues d'ici là.
- **Suite** `bash backend/checks/run_all.sh` verte (2026-10-19, après le point 13 : 66 checks, 5041 assertions).
- **Production** : dernier déploiement `6760090` (point 13, backend + frontend), vérifié dans le conteneur et par l'API (baisse NVDA servie). Migration 060 appliquée. Mandats : 1 manager ouvert (2918).
- **Prochaine migration : 061** (060 = geste `retablir` au PV ; 059 = classement décidé par le comité ; 058 = geste `reinitialiser` au PV ; 056/057 = prompt search-worker v5/v6). Catalogue d'événements **1.7.0** ; notes flash 1.7.0 : RVMD #730-#739,
  NVDA #740-#745, MSFT #746-#750.
- **Réglage `v2_auto_enabled` = FALSE** (le matin ne fait que recenser). Crédit DeepInfra : vérifier par
  un appel minimal avant toute grosse dépense.

## Arbitrages récents

Le détail : `CONVENTIONS.md` #129-#139 ; séance du 2026-10-17 : `08-seance-arbitrages.md` ; liste du 2026-10-16
au 2026-10-18 : archive, section « 2026-10-19 — sortis de la reprise (arbitrages récents) ».

## Outils (tous dans `backend/tools/`, gratuits sauf mention)

- `montrer_parcours.sh TICKER` (dossier, manques, notes de qualité) · `montrer_socle.sh TICKER…` (comptes
  reconstitués) · `recouper_nombres.sh TICKER framework` (chaque nombre d'une réponse retrouvé dans ses
  pièces ; même règle que le contrôle #136) · `acceptation_analyste.sh --admissibilite` avec `ACCEPTATION_CAS=TICKER:framework:archetype`
  (ce que le corpus permet, sans appel modèle).
- Payants : `executer_chaine.sh TICKER framework archetype [--questions=…] [--sans-collecte]` (ÉCRIT en
  prod, ~1 h par chapitre, imprime l'inventaire de ses écrits) · `mesurer_ligne_web.sh PLAN LIGNE…`
  (rejoue une ligne de collecte à blanc, ~0,01 $) · `acceptation_traducteur.sh TICKER:framework:archetype`.
- Retraits en base : `tools/retraits/*.sql` (un fichier daté par retrait, avec sa trace).

## Pièges à ne pas re-découvrir

- Producteurs déterministes exécutés et lus **en texte** avant toute dépense ; `LE VERDICT EST À LA
  LECTURE` : relire chaque réponse contre ses pièces (les contrôles gardent la structure, jamais le sens).
- `ps aux` / `docker ps` avant toute relance ; lancer en arrière-plan avec l'outil, jamais `nohup … &`.
- Un check neuf n'est livrable qu'après avoir viré au rouge pour la bonne raison (`negatif_*.sh`) ;
  fixtures copiées du réel ; une garde déléguée se mute chez son détenteur.
- Ne jamais induire les frameworks de la base ; une question se pose en substance économique.

## Ce qui est fermé (ne pas rouvrir)

Grille MVDD / `SYNTHESIS_TARGETS` supprimés · hybridation RRF interdite · tout levier du modèle sur
l'exigence (plancher, nature, champs requis) · dégrader le tier d'une source selon l'émetteur ·
« capacité 5 barreau 4 » (l'agent propose une méthode d'approximation).

## À lire selon le besoin

`05-frameworks-complets.md` (roadmap active) · `07-avant-comite.md` (inventaire) · `03-spec-frameworks.md`
§1/§2/§4 (spec, tableaux des questions) · `06-regle-fraicheur.md` (fraîcheur) · `04-taxonomie-evenements.md`
· `principe-directeur.md` · `doctrine-trois-axes.md` · `METHODE-TEST.md` · `ARCHITECTURE-CIBLE.md` + les
`ARCHITECTURE.md` de module · `00-REPRISE-ARCHIVE.md` quand le *pourquoi* manque.
