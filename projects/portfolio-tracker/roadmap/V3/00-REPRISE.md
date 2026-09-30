---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-09-30
project: portfolio-tracker
role: >
  Prompt de reprise du chantier V3 (frameworks). Il ne porte que l'ÉTAT, le PROCHAIN JALON, ce qui
  reste ouvert et les pièges. Le récit des lots livrés est dans `00-REPRISE-ARCHIVE.md` (l'état
  complet de ce fichier avant son délestage du 2026-09-25 y est copié tel quel, section
  « 2026-09-25 (4) »), les règles durables dans le `CLAUDE.md` du projet (conventions #25…#103), la
  PREUVE de ce qui existe dans `backend/checks/` — qu'on exécute.
---

# Prompt de reprise — portfolio-tracker V3

> **LIRE D'ABORD `roadmap/V3/PRINCIPES-FONDATEURS.md`** — à chaque reprise, sans exception.
> Deux principes y gouvernent toute la conduite du chantier : (1) toute demande d'arbitrage se
> formule en **termes métier**, jamais techniques ni fonctionnels ; (2) chaque décision s'éclaire
> par la pratique d'un **vrai fonds d'investissement**.

> **Ce fichier ne s'empile pas.** Récit → `00-REPRISE-ARCHIVE.md` (copie conforme) ; durable →
> `CLAUDE.md` du projet ; outillage transverse → `../../../CHANTIER_OUTILLAGE_DEV.md`. Protocole
> d'éviction : `CONTROL_SYSTEM.md` §5. Le prochain pas n'est écrit qu'à **un seul endroit** : la
> checklist de la roadmap active (première case non cochée).

---

## 🎯 Roadmap active — `roadmap/V3/05-frameworks-complets.md` (ouverte le 2026-09-28)

> **Roadmap active : `roadmap/V3/05-frameworks-complets.md`** — capacité en cours : **§4 bis
> « L'atelier de valorisation »**. Les quatre frameworks manquants sont RÉDIGÉS (#92-#95) : 6 chapitres
> sur 6 ont une méthodologie. La 4 bis est OUVERTE (#96-#99, 2026-09-29) : gabarits maison, bac à
> calcul, contrat + pont + évaluation du modèle d'entreprise, SIGNATURE + registres (051), endpoints, et
> la REPRISE « un seul chiffre par dossier » (option c, #99) livrés (`app/valorisation/`,
> `api/valorisation_v2.py` ; aucun modèle en base, rien ne propose encore). **Encadré (#100), analyste
> corrigé (#101), horloge des comptes (#102) et faits postérieurs lus (#103) déployés** : RVMD a sa
> première réponse reprenable (qf_4 #963). Prochain geste : trancher le défaut de prose de #963, puis
> qf_6 (re-collecte) et qf_7 (correction en amont) — voir « Ce qui reste ouvert », en tête.

**Pourquoi elle a pris la place du lot 7 de la spec 03 (arbitrage du 2026-09-28).** Interrogé sur la
grille vers laquelle reclasser RVMD après l'approbation de RASONQUE, l'utilisateur a déplacé la
question : les frameworks sont-ils vraiment agnostiques à l'entreprise, ou faut-il un agent qui les
adapte à l'entreprise et à son stade ? Réponse de méthode retenue : **rédiger les quatre frameworks qui
manquent au mémo** (modèle économique, secteur et concurrence, management, valorisation), **les éprouver
sur les cas réels**, et seulement alors décider à quel niveau vit l'adaptation. Détail et ordre justifié
dans la roadmap. La spec 03 reste la référence de conception (§1 ce qui n'est pas défait, §2 l'objet
framework, §9.3 le critère de déclenchement des frameworks par archétype).

**Ce que la mesure dit déjà** : les 13 questions des deux pilotes ont servi à NVDA, MSFT et RVMD sans
réécriture ; l'adaptation vit au **stade** (`archetypes`, liste fermée de 3, écrite à la main) et à
l'**entreprise** (le traducteur). L'approbation RVMD montre que l'étage « stade » est fermé.

### Spec 03 — état des lots (§10)

| Lot | Contenu | État |
|---|---|---|
| 0 | Ligne de base (mesureurs versionnés) | ✅ 2026-09-09 |
| 1 | Contrat `FrameworkAnswer` / `FrameworkMandate` + pont relationnel | ✅ 2026-09-09 |
| 2a | Référentiel : 2 pilotes, 13 questions en données inertes | ✅ 2026-09-10 |
| 2b | Archivage `archive_v2`, dévocabularisation, `question_coverage` | ✅ migrations 036-038 |
| 2c | Chaîne de collecte : traducteur, collecteur, exécuteur réel | ✅ 2026-09-12, migration 039 |
| 3 | Analyste, `framework_answers`, suppression de la grille MVDD, appariement par ticker, collecte neuve NVDA/MSFT/RVMD | ✅ migrations 040-042 |
| 4 | Manager (4 contrôles, renvoi → mandat) + ses données | ✅ 2026-09-21, migration 043 |
| 5 | Mémo projeté, chaîne de bout en bout sur les 2 pilotes, bouclage comité → collecte | ✅ 2026-09-25 (déployé `3588d23`) |
| 6 | Le parcours : `qualite_info` dérivée · 3 niveaux de drill-down · acquitter/renvoyer tracés (A7) · la note reprend le retenu (arbitrage A) | ✅ 2026-09-26 (déployé `4316222`, #82-#85) |
| 7 | Second pilote complet · acceptation T1-T8 · réconciliation à 0/0 | ⏸ suspendu le 2026-09-28 après #86-#91 (identité de l'émetteur, pièces Ryvu écartées, jugement fondé sur des faits, horloge par question, note flash branchée) — son reste (maillons 3-4, T1-T8, 0/0) est repris en capacités 7-9 de `05-frameworks-complets.md` |

Détail de chaque lot : archive (entrées datées) + conventions #57 → #91 du `CLAUDE.md`.

### Mesures courantes — à RE-REQUÊTER avant de s'en servir

(`feedback_ligne_de_base_est_une_mesure` : aucun de ces chiffres ne se cite sans être re-mesuré.)

- **Suite** `bash checks/run_all.sh` = **4066 assertions sur 55 scripts, 0 rouge** (2026-09-30, après
  #103 et l'écriture de #963) : `check_signature_modele_persist` a reverdi pour la bonne raison (qf_4 #963
  reprenable). Réconciliation (`tools/reconcilier_vocabulaires.sh`) : 6/6 chapitres adossés, T6/T7 toujours
  rouges (30 champs / 37 questions — capacité 9). Les 3 checks « live » sont hors suite par conception. Un
  check lancé à la main sans les montages de `run_all.sh` sort un faux FAIL.
- **Migrations** (aucune au lot #100) : **051 appliquée** le 2026-09-29 (modèle de valorisation : versions + PV, tables
  vides) ; la prochaine sera **052**. Vérifier en base avant
  d'écrire, jamais se fier à un tableau.
- **Production** : stack sur **`4e117fa`** (#103 : faits postérieurs lus ; avant `de4abf2`, #102) — vérifié
  dans le conteneur : dossier / niveau 2 / niveau 3 qf_4 / valorisation RVMD en 200 ; niveau 3 qf_4
  « À jour » avec la ligne « faits lus depuis les comptes », capture headless regardée. `GET
  /v2/tickers/RVMD/valorisation` → `aucun_modele_propose`. Chapitres `business_model`, `industry`,
  `management`, `valuation` : `sans_acquittement` sur NVDA/MSFT/RVMD (capacité 5). **PV du comité : 0 décision.**
- **Réglage `v2_auto_enabled` = FALSE** : le passage du matin ne fait que RECENSER. Recensement réel du
  2026-09-26 : RVMD/NVDA/MSFT à jour ; AMZN 9, GOOG 9, AstraZeneca 125, Novo Nordisk 73 dépôts à lire ;
  9 titres hors EDGAR.
- **Notes flash en base** (catalogue d'événements **1.2.0**, relues le 2026-09-28 après #94) : RVMD
  #181-#186, NVDA #187-#188, MSFT #189 — mêmes types qu'en 1.1.0 (#80-#88), 0 refus, $0,0025 ; les
  lectures 1.0.0/1.1.0 restent conservées (append-only).
- **Dossier RVMD** (`bash tools/montrer_parcours.sh RVMD`, 2026-09-30) : 31 manques — qf_6 (périmée par
  #345), qf_7 (périmée par les baux du 27/08, non lus : réponse #925), mo_1…mo_5 (approbation FDA LUE), et
  les 24 questions des quatre nouveaux frameworks jamais collectées. **qf_4 #963 tient** (qualité
  financière 0,33). Mandats 983-986 toujours ouverts sur des questions répondues (voir « Reste ouvert »).

---

## Arbitrages de l'utilisateur qui commandent la suite

**2026-09-28 — construire le système avant de l'étendre**
1. **Lecture automatique des communiqués : on reste en l'état** (`v2_auto_enabled = FALSE`). « La
   priorité est de construire le système de bout en bout en utilisant des exemples pour piloter son
   architecture de façon à ce qu'il soit réplicable sur tout titre. On gérera les autres titres en
   portefeuille une fois le système conçu. » ⟹ l'arriéré AZN/NVO/AMZN/GOOG n'est pas à résorber.
2. **Information attendue ≠ information manquante.** Après un changement de stade (RVMD approuvée), le
   système va chercher la matière nouvelle même si elle n'est vraisemblablement pas encore publiée ;
   son absence ne bloque pas et ne déclenche ni alerte ni revue de position.
3. **Rédiger d'abord tous les frameworks prévus, les éprouver sur des cas concrets, puis décider où vit
   l'adaptation** (stade, entreprise, agent concepteur de grille) — roadmap `05-frameworks-complets.md`,
   ordre validé : modèle économique → secteur et concurrence → management → valorisation.
4. **Événements chez les concurrents (option A, #93)** : déclarés au catalogue (origine `exterieur`),
   ils rouvrent les questions du secteur qui les citent, jamais tout le dossier ; le veilleur qui les
   repère reste à construire.
5. **Une levée de fonds est un acte d'allocation (#94)** : elle rouvre aussi le jugement sur le
   management (usage du capital, prix des émissions) — extension de la règle du 26/09 ; et la
   valeur PAR ACTION (va_1/va_2/va_4/va_6, #95).
6. **Valorisation (#95)** : option 1 (ce qui dépend du cours est recalculé à la lecture au dernier
   cours coté daté, la fourchette ne bouge que sur un fait nouveau) ; la valorisation s'instruit
   APRÈS les frameworks dont elle reprend les chiffres ; **le calcul n'est pas fait par le modèle** —
   base commune de calculs + capacités d'exécution de code PROPRES À CHAQUE ENTREPRISE (« le CA futur
   de RVMD s'apprécie sur le portefeuille de molécules […] pas du tout la même méthodologie pour
   NVDA »).

**2026-09-29 — l'atelier de valorisation (#96)**
1. L'agent **propose** la méthodologie propre à l'entreprise, **segmentation du marché comprise** (à
   compléter quand de nouveaux produits sont lancés) ; le **comité signe**.
2. Mécanique **libre** (la typologie des entreprises est trop large), mais **décrite** par l'agent ; le
   comité juge un **tableau d'hypothèses chiffrées et sourcées** ; exécution dans un bac à calcul
   Python très simple.
3. Mécanique refondue sur **changement de stade** ou **demande du comité** ; un nouveau produit repéré
   en revue trimestrielle peut être ajouté par le système — comme NOUVELLE VERSION proposée (point 6).
4. **Jugement ancré** (#97) : une hypothèse sans pièce est admise, étiquetée, adossée à un taux de base
   sourcé, écart justifié.
5. **La forme de la fourchette dépend de l'entreprise** (#97) : scénarios nommés (incertitude continue)
   ou arbre d'événements probabilisé (incertitude binaire), choisie par l'agent, signée par le comité.
6. **Après signature, seuls les chiffres repris bougent seuls** (#97) ; un jugement changé ou un produit
   ajouté = nouvelle version proposée, la signée reste affichée jusqu'à la décision du comité.
7. **Signature (#98) — choix pris comme un vrai fonds, À CONFIRMER** : motif obligatoire pour signer
   comme pour écarter ; la fourchette signée est au PV ; seule la dernière proposition attend (une plus
   récente remplace l'autre) ; on ne signe pas un modèle qui ne tient plus contre le dossier du jour ;
   un modèle signé qui ne tient plus est « à revoir » mais sa fourchette signée reste affichée.
8. **Un seul chiffre par dossier — option (c)** (#99) : la valorisation REPREND la réponse qui tient ; elle
   porte son propre chiffre (pièce ou jugement ancré, signé par le comité) SEULEMENT si la question est sans
   objet pour ce titre (le coût du capital de RVMD, pour qui qf_1 est sans objet) ; sinon elle attend.
9. **L'encadré de chiffres clés** (instruit le 2026-09-29, CONSTRUIT le même jour — #100 ; réémission à refaire) : chaque réponse rend des chiffres
   nommés déclarés par question ; le résultat normalisé vient de qf_1, le nombre d'actions dilué du cours
   coté, la dilution de qf_4 ; les réponses existantes sont réémises au nouveau format sur les mêmes pièces
   — « pas de dette » (l'utilisateur a écarté l'option de les garder valides sans chiffre).

**2026-09-22 — l'ordre du chantier**
1. **On finit l'AMONT** (faire tourner la V3 complète sur un cas sans difficulté), **ensuite
   seulement** l'aval/suivi. Les questions d'obsolescence entre deux analyses ne s'instruisent pas
   avant.
2. **La spec gagnera une partie MONITORING** : on n'écrase pas, on **empile** l'historique, mais le
   système répond sur la donnée la plus récente. `dossier.py` est la moitié LECTURE ; la moitié
   ÉCRITURE reste à spécifier.
3. **Prose ancienne** : le système juge si elle est toujours d'actualité (web ou EDGAR) ; si
   périmée, on l'archive pour la trace et on la remplace.
4. **Publication trimestrielle = revue complète de la thèse** ; position ouverte = actualisations
   régulières dans les deux sens.
5. **Périmètre : EDGAR uniquement** pour l'instant (européennes / non cotées = version ultérieure).
6. **À l'initialisation et en test, on rachète tout** : le rachat de données n'est pas une dépense
   à éviter ; le coût web se borne par budget, pas en aveuglant la collecte.

**2026-09-24 — la croissance du système**
« On fait tourner de bout en bout sur les 2 frameworks construits ; ensuite il suffira de
compléter les frameworks. » ⟹ **ajouter une méthodologie est une opération de DONNÉES, jamais de
code** (lien framework → chapitre du mémo déclaré dans `frameworks.yaml`, prouvé par un framework
fictif ajouté en YAML seul — `check_memo_projete` §4). Ne publier que l'instruit ; un chapitre non
instruit est un **état nommé**, jamais un bloc vide.

**Arbitrages « comme un vrai fonds »** déjà rendus : datation des pièces (#79), cours coté (#81),
note de qualité (#82), rang d'une approximation « un cran sous la plus faible pièce citée »
(`project_synthesis_tier_rule`), avis du manager recalculé et seul le mandat conservé (#77).

---

## Ce qui reste ouvert

**⚠️ EN TÊTE — RVMD a UNE réponse reprenable : qf_4 #963 (2026-09-30, #102/#103)**
- #102 : un communiqué de résultats ne périme plus les comptes qu'il publie (seuil = clôture du 10-Q/10-K
  déposé avec lui). #103 : un fait postérieur aux comptes, LU dans le dépôt et chiffré par l'analyste, ne
  périme plus la réponse (`faits_posterieurs`, pont [P]). Passage `executer_chaine … --sans-collecte
  --questions=qf_4` : #963 à jour (lit les baux du 27/08 dans #296), acquittée, 0 mandat.
- **Défaut de #963 — DIAGNOSTIQUÉ le 2026-09-30 : c'est un défaut AMONT, pas de rédaction** (non retiré,
  aucune règle de prose ajoutée — l'utilisateur préfère corriger en amont). Sa prose dit « dette nette
  −328 M$ », son encadré −3 450,54. Le −328 = dette − trésorerie SEULE (815,4), sans les 3 122,5 M$ de
  titres de placement. Il vient du système lui-même : `financials_feed.py` (bloc « levier ») calcule
  `net_debt = debt - cash` avec `cash` = `CashAndCashEquivalents` seul, alors que le référentiel (qf_4,
  `frameworks.yaml`) définit la dette nette « moins trésorerie ET placements ». Pièces tier A publiées
  ainsi : RVMD #661 (−328), **MSFT #584 (+10,1 Md de dette nette, alors que 31,1 − 76,8 = −45,7 Md de
  trésorerie nette : SIGNE INVERSÉ)**, NVDA #623 (+9,9 Md ; le poste `marketable_securities` n'est même
  pas relevé pour NVDA — à mesurer). La pièce d'héritage #296 (search-worker, 12/09) recopie le même
  −328 à côté du bon total 3 937,969 ; l'analyste l'a repris fidèlement. Même définition étroite dans le
  capital investi du ROIC (`invested = equity + debt - cash`). Correction : le producteur prend
  trésorerie + placements (poste déjà relevé par `edgar_feed`) et nomme ses composantes ; republier ;
  #296 tombe avec la re-collecte prévue pour qf_6 ; puis `--questions=qf_4,qf_6`. Une garde « la prose
  ne contredit pas l'encadré » n'est à reconsidérer QUE si la contradiction revient après correction.
- **qf_6** : périmée par la seule pièce #345 (héritage daté 2025-12-31, contenu au 30/06) — désormais la
  re-collecte AIDE (#102 rend à jour un fait au 30/06) : re-collecter le dossier RVMD qualite_financiere
  (payant, autorisé en test le 22/09) puis `--questions=qf_6`.
- **qf_7** : 0/3 sur 3 passages (refus [E], la guidance #312 — interprétation — citée à côté des relevés ;
  1/3 au #101). À corriger en amont avant toute réémission ; ne JAMAIS la réémettre avec le framework entier
  (le refus ouvrirait un mandat à tort — utiliser `--questions`).
- Écran niveau 3 : l'effet du fait lu est affiché deux fois (motif de fraîcheur + ligne « faits lus ») —
  cosmétique.
- #103 vaut aussi pour la défendabilité (mo_* rouvertes par l'approbation FDA LUE) : les faits à lire
  leur seront montrés dès qu'une pièce TIRÉE du 8-K du 26/08 sera au corpus.

**⚠️ DETTE BLOQUANTE POUR LA PRODUCTION (consignée à la demande de l'utilisateur, 2026-09-29) — à
traiter quand la V3 sera quasiment finalisée**
- Une ré-analyse sur les MÊMES pièces peut REMPLACER une réponse instruite par une moins bonne
  (qf_6 approximée → « sans fondement » le 29/09), et un refus d'agent devient un renvoi du manager
  (« question sans réponse ») donc une demande de recherche à tort. Le seul retour arrière est un
  retrait manuel en base (SQL + sauvegardes). Inacceptable en exploitation : un fonds ne laisse pas une
  note moins bonne remplacer la note en vigueur sans que quelqu'un l'ait lue. Pistes à instruire en
  termes métier : la nouvelle réponse n'entre en vigueur que si elle est au moins aussi fondée (ou si
  le comité l'accepte) ; un refus d'agent ne se convertit jamais en demande de recherche (même famille
  que les mandats 983-986) ; un geste « retirer un passage » tracé, au lieu du SQL à la main.

**Remontés du jalon du lot 7 au 2026-09-28 (non traités, toujours vrais)**
- **Mandats manager 983-986** (« question sans aucune réponse », ouverts avant #88) restent `ouvert`
  alors que mo_1/3/4/5 sont répondus et acquittés — le parcours affiche encore « repartie en
  recherche : mandat #983 ». `persist_review` n'en ferme aucun sur un acquittement. Un fonds clôt la
  demande de recherche quand la question a trouvé sa réponse ; relire #77 et le bouclage (#71/lot 5)
  avant de choisir le geste.
- **À relire par le comité** : MSFT #88 a lu la présentation des nouveaux segments (7.01 du 02/09) comme
  de la routine — défendable, mais un changement de segments change la comparabilité ; si le comité
  juge qu'il doit rouvrir la qualité financière, c'est une précision du libellé `routine` (donnée).
- **Événements extérieurs à l'émetteur — le VEILLEUR reste à construire** : les 4 types
  (`concurrent_offensive`, `concurrent_revers`, `concurrent_rapprochement`, `regulation_du_secteur`)
  sont déclarés et rouvrent les `se_*` qui les listent (#93), mais rien ne les repère : en pratique ils
  ne rouvrent rien. Et `mo_3`/`mo_5` ne les listent pas (réécriture d'une question existante, #64) —
  à trancher sur la mesure de la capacité 5.


**Dettes à décider (chacune est un lot en soi, à arbitrer en termes métier)**
- **Chaîne complète vs acceptation du comité** (#84) : `executer_chaine` → `persist_review` ne consulte
  pas le PV ; un re-run refait l'analyse (l'acceptation tombe, « analyse refaite ») et peut rouvrir un
  mandat que le comité avait arrêté. Honnête (le dossier a changé) mais coûteux — lié à l'arbitrage B.
- ✅ (corrigé #86 ; pièces écartées #87, 2026-09-26) **Confusion d'émetteur dans le plan `defendabilite` RVMD** (plan 103, 2026-09-25) : mo_1/mo_5
  cherchent « inhibiteur de CDK8/19 » et « révatiglimab (RVU120) » — c'est **Ryvu Therapeutics**,
  pas Revolution Medicines (inhibiteurs RAS). Ces « recherches épuisées » portent sur la MAUVAISE
  société ; le traducteur n'a aucune garde d'identité de l'émetteur. Rendu visible par l'alerte.
- **12 ingrédients `source_indisponible`** sur RVMD (budget 180 s ×9, sortie non conforme ×3) :
  relançables tels quels — c'est ce que l'alerte recommande au comité.
- **`mo_2` applicable à une pré-revenus** alors que ses 4 ingrédients sont « sans source possible »
  (marges, parts de marché, rétention, coût d'acquisition) : référentiel à revoir pour
  `pre_revenus` (opération de données dans `frameworks.yaml`).
- **128 pièces d'héritage sans datation** (écrites par le search-worker avant la 045) : le rejeu
  des producteurs déterministes ne les soldera **jamais** ; les solder coûte des appels modèle. On
  re-collecte, on ne date **jamais** a posteriori par modèle. 5 chemises RVMD × `qualite_financiere`
  restent à datation hétérogène.
- **Résiduel #80** : une note produite par le fonds ne dit pas **selon quelle version des
  frameworks** elle a lu ses pièces (`grep framework_version` = 0 dans `curator.py`,
  `synthesis_feed.py`, `base_rate_corpus.py`).
- **FMP rend 403 sur `analyst-estimates`** (MSFT/NVDA/RVMD) : estimations d'analystes absentes,
  lues à tort comme une propriété de l'émetteur. Réparer la clé ou nommer l'état.
- **`check_cours_cote_live`** : vert mais **non exercé** (0/3) — ne pas lire comme « #81 prouvé en
  réel ».
- **Moat RVMD `non_fondable`** : le web n'a pas ramené de preuves de barrière à l'entrée (limite
  de collecte, pas défaut).
- **Bouclage comité → collecte** : prouvé en ROLLBACK, jamais exercé en prod (0 renvoi ouvert).
  Ne **pas** fabriquer un renvoi pour le verdir (`feedback_fixture_pollue_le_reel`).
- **Lignée des pièces jumelles** (#280/#296, même dette au même jour, non clefables) : backfill
  `poste_kind`/`metric` (lignée 035) pour les pièces hors index de couverture.
- **Coût web non instrumenté** et **wall-clock ≈ 1 h sur MSFT** : le garde #73 borne l'infini, pas
  la lenteur (budget global / parallélisme = chantier distinct).

**Backlog demandé par l'utilisateur**
- **(2026-09-10 a)** Des pièces étiquetées « pairs » ne prouvent pas qu'une analyse
  concurrentielle a eu lieu — ne jamais câbler « tag présent ⇒ couvert ».
- **(2026-09-10 b)** Une affirmation peu fiable **et** déterminante pour la décision doit être
  vérifiée par le système ; le déclencheur est le **couple** (fiabilité basse × poids), et le poids
  reste à définir.
- **24 pièces suspectes RVMD** à statuer à la main (dont 4 tier A « aucun produit approuvé »,
  périmées par l'approbation FDA du 2026-08-26). Le volet « faux » est clos (#656 → #662).
- **FDA / EMA en régulateur A−** — décidé, non commencé ; **prérequis du pilote biotech**.
- **File de propositions de sources** : le système recommande, l'utilisateur admet (acte humain).
- **Module « réalisé vs annoncé »** : qualité des prévisions du management, à partir de
  `periode_visee` (#79).
- **Interface d'audit des agents** (2026-09-11) : règles en dur vs prompt + variables, en termes
  non techniques.
- **Évaluation des plans par un juge sur beaucoup de tickers** (2026-09-11) : signal, pas porte.
- **4ᵉ ticker** (nouvel archétype) — penser à `websearch._ISSUER_DOMAINS` et
  `source_registry._TICKER_SECTEURS` en même temps.
- `ingestion-agent` (document → pièces), jamais construit, non bloquant ; N analystes par
  framework (contrat prêt, jamais de moyenne).

- **`negatif_acceptation_frameworks.sh` est MORT depuis la 036** (constaté le 2026-09-26) : il rejoue la
  036 sur une copie de la prod, qui l'a déjà (`schema "archive_v2" already exists`) — satisfiabilité et
  6 mutations en FAIL. Hors `run_all.sh`, donc invisible. À refaire sur un état pré-036 ou à retirer.

**Dettes techniques connues, assumées**
- `base_rate_ge` non câblé dans `run_research` ; `BullCase.conviction ×10 si ≤1` (filet) ;
  `tools_json` du search-worker en DB décrit encore « SearXNG » (cosmétique) ; `uncovered_fields`
  dupliqué ; `symbole_de_marche` a 2 appelants, 3 jumeaux de la règle #11 subsistent.
- `get_db_session()` n'ouvre **aucune** transaction (#35) : toute écriture multi-table est
  explicitement `async with conn.transaction():`.

---

## Ce que la V3 ferme explicitement (ne pas rouvrir)

- **Capacité 5, barreau 4** (l'agent propose une méthode d'approximation) : hors périmètre,
  réfutée 4 fois ; c'était un défaut de rangement.
- **Grille MVDD de 19 champs, `SYNTHESIS_TARGETS`, `DECLARED_NONBLOCKING_GAPS`** : supprimés.
- **Hybridation RRF de la recherche** : interdite (MRR 0,905 → 0,655).
- **Le corpus en base comme point de départ** : interdit (§0.6) — il sert à éprouver, jamais à
  concevoir.
- **Tout levier du modèle sur l'exigence** (plancher, nature attendue, champs requis).
- **Dégrader le tier d'une source selon l'émetteur** : c'est de l'actualité, pas de la fiabilité.

## Doctrine acquise (roadmap 02, close)

Trois axes **jamais recombinés en un scalaire** (#50) : fiabilité (propriété de la source,
stockée) · nature (propriété de l'assertion, stockée, #51) · actualité (relation fait ↔ ancre,
**calculée à la lecture, jamais persistée**, #53). Porte de complétude à trois états et deux
remèdes (#54). Un verdict persisté n'est pas un verdict servi : on rejoue à la lecture.

## Décisions structurantes

- **Modèle** métier et ouvrier = `deepseek-ai/DeepSeek-V4-Flash-0731` (coût dominé par l'output).
- **Embeddings** `BAAI/bge-m3` 1024d (corpus français) ; ne pas hybrider.
- **Web** : Exa, débordement Serper (SearXNG écarté sur son mode de panne).
- **Option C** (base neutre → bull/bear isolés → réfutation → synthèse, seul verdict) ; sortie
  thèse-driven.
- **VPS** : 3,8 Go RAM, 0 swap, ~5 Go libres — vérifier le disque avant tout `docker pull`.

---

## Pièges à ne pas re-découvrir

- **Ne pas induire les frameworks de la base** ; une question se pose en **substance
  économique**, jamais en artefact comptable ; le hors-sujet (`sans_objet` motivé) est un signal,
  pas une panne.
- **DeepSeek + `response_format=json_object` non fiable** : `run_json_agent(json_object=False)` +
  `extract_json`. Contrats = pydantic v2 → tester **dans le conteneur**, pas sur l'hôte.
- **Migrations** : `docker cp` + `psql -f` (le heredoc via `docker exec` échoue en silence) ;
  écrites juste avant leur lot ; garde `RAISE EXCEPTION` éprouvée en négatif avant application.
  Une colonne `NOT NULL` neuve met le déploiement en dette jusqu'au rebuild.
- **asyncpg** : `$1`, JSONB auto-décodé ; retirer `+asyncpg` de `DATABASE_URL` pour une connexion
  directe.
- **Déploiement** : `compose-deploy.sh` en premier (re-tester le nominal à chaque session), repli
  §12 de `CHANTIER_OUTILLAGE_DEV.md` ; rebuild jamais restart ; vérifier DANS le conteneur ; 2
  conteneurs sur le domaine sont normaux.
- **Règle #19 / #39** : tout changement de contrat = prompt en DB + exemple JSON + frontend +
  import ; rejouer `run_all.sh` **en entier** après tout ajout de champ à un contrat partagé.
- **Un écran ne se vérifie pas par un 200** : payloads réels avant le JSX, capture headless
  regardée ; le point de lecture fait partie de la capacité.
- **Méthode** : producteurs déterministes exécutés et lus **en texte** avant toute dépense ;
  « combien de lignes actives sur cette clef ? » après toute écriture qui remplace ; un check neuf
  n'est livrable qu'après avoir viré au rouge **pour la bonne raison** — six faux verts connus
  (fixture non discriminante · script mort avant ses asserts · assert à côté du point de lecture ·
  assert écrit depuis sa propre constante · `all()` sur liste vide · garde qu'aucune mutation
  n'atteint) ; une garde déléguée se mute chez son détenteur.
- **Fixtures copiées du réel**, jamais écrites à la main ; un grep d'interdit se fait sur le code
  **dépouillé** de sa prose ; un bilan se reconnaît à sa **forme** ; mesureurs versionnés, jamais
  `/tmp`, **jamais exécutés dans `portfolio-backend`** ; un test négatif qui mute la base = quatre
  appels séparés ; un `__pycache__` périmé fabrique un faux vert.

---

## À lire avant de reprendre

1. **`roadmap/V3/PRINCIPES-FONDATEURS.md`** — toujours en premier.
2. Ce fichier, puis **`roadmap/V3/05-frameworks-complets.md`** (la roadmap active), puis
   `roadmap/V3/03-spec-frameworks.md` §1 (ce qui n'est PAS défait), §2 (l'objet framework), §9.3.
3. **`CLAUDE.md` du projet** — conventions **#25 → #103** ; pour le lot 6 : #53/#54 (recalcul à la
   lecture), #76/#77 (manager, mandat), #82 (`qualite_info`), #83 (parcours), #84 (registre du
   comité), et `feedback_controle_au_point_de_lecture`.
4. `roadmap/V3/principe-directeur.md` (constitution) · `doctrine-trois-axes.md` (close) ·
   `benchmark-methodologies.md` (matière des frameworks) · `METHODE-TEST.md` (choix de la méthode
   de test) · `ARCHITECTURE-CIBLE.md` + un `ARCHITECTURE.md` par module (cible ; le réalisé = les
   checks) · `provenance-cards/` (contrats figés, maquette niveau 3).
5. Code du flux : `backend/app/agents/v2/` (`traducteur`, `collecte_executor`, `apparieur`,
   `dossier`, `analyste`, `manager`, `manager_persist`, `bouclage`, `projection_memo`,
   `qualite_info`, `parcours`, `comite`, `note_flash`) · `backend/app/valorisation/` (gabarits, bac,
   modèle, signature) · `backend/app/contracts/` · `backend/checks/README.md`.
6. `00-REPRISE-ARCHIVE.md` si le *pourquoi* d'une décision manque.

---

## À coller pour reprendre

> Reprise de **portfolio-tracker V3**. Lis d'abord `roadmap/V3/PRINCIPES-FONDATEURS.md` (arbitrages
> en termes métier ; chaque décision éclairée par la pratique d'un vrai fonds), puis
> `roadmap/V3/00-REPRISE.md`. Roadmap active : `roadmap/V3/05-frameworks-complets.md` — les quatre
> frameworks manquants sont rédigés (#92-#95) ; capacité en cours **4 bis, l'atelier de valorisation**
> — gabarits, bac à calcul, contrat + pont + évaluation du modèle, signature + registres 051 livrés
> + reprise « un seul chiffre par dossier » (option c) (#96-#99) + encadré de chiffres clés (#100, déployé)
> + analyste corrigé en amont (#101) + horloge des comptes (#102) + faits postérieurs lus (#103) : qf_4 #963
> est la première réponse RVMD reprenable ; reste : trancher le défaut de prose de #963 (−328 vs encadré),
> qf_6 (re-collecte) et qf_7 (correction en amont) — en tête de « Ce qui reste ouvert » —, l'ordre dans la chaîne d'instruction, l'agent qui écrit le modèle, l'option 1 au
> cours du jour, Greenwald, la dépendance va_1/va_2 → va_6 ; puis éprouver les six frameworks sur NVDA/MSFT/RVMD
> + un 4ᵉ titre, et décider à quel niveau vit l'adaptation à l'entreprise. Lots 0-6 de
> la spec 03 clos ; lot 7 suspendu (son reste = capacités 7-9 de la roadmap 05). Re-requêter toute
> ligne de base avant de s'en servir.
