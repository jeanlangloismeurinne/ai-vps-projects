---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-10-14 (A1 NVDA ; 8-K RVMD soldé ; #125 catalogue 1.3.0) · 2026-10-13 (#124 budget de la collecte web ; #123 horloge par question ; RVMD modèle économique 4/6 ; #120 horloge du traducteur ; #121 consignes resynchronisées (054) ; #122 identité de l'émetteur lue au registre ; NVDA qf 1,00 ; RVMD qf 1,00, défendabilité refaite ; arbitrage « descriptions juridiques »)
project: portfolio-tracker
role: >
  Prompt de reprise du chantier V3 (frameworks). Il ne porte que l'ÉTAT, le PROCHAIN JALON, ce qui
  reste ouvert et les pièges. Le récit des lots livrés est dans `00-REPRISE-ARCHIVE.md` (l'état
  complet de ce fichier avant son délestage du 2026-09-25 y est copié tel quel, section
  « 2026-09-25 (4) »), les règles durables dans le `CLAUDE.md` du projet (conventions #25…#123), la
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

> **➜ PROCHAIN PAS (2026-10-14) : jalon « note d'initiation » — A2, défendabilité** (NVDA : première
> instruction ; RVMD : collecte postérieure au 30/06). **Avant**, faire trancher par l'utilisateur
> l'arbitrage « fait rappelé ≠ fait nouveau » ci-dessous.
> Fait ce jour : **A1 coché** — NVDA modèle économique (plan #248, réponses #1366-#1371) **1,00, 6/6 à jour**,
> deux réserves pour le comité (me_5 marché des seuls CPU, me_6 citation manquante — voir la roadmap) ;
> **8-K RVMD du 13/10 soldé** : note flash, qf_4/qf_7/qf_8 réémises `--sans-collecte` (#1378-#1380, tirage
> 250 M$ lu et annoté : dette brute ~1 286 M$, autonomie ~38 → ~40 mois) — qualité financière RVMD **1,00** ;
> suite **4465/0**. ⚠️ **#124 TOUJOURS PAS DÉPLOYÉ** (classifieur, 2ᵉ refus) — à lancer par l'utilisateur.
> ⚠️ **ARBITRAGE EN ATTENTE — #125, la note flash range un dépôt par ce qu'il RAPPELLE.** La note du tirage
> RVMD retient « réglementaire favorable » parce que le 8-K rappelle l'approbation FDA du 26/08 comme
> condition du tirage : me_1 RVMD est périmée à tort. Catalogue 1.3.0 (libellés « annoncé par ce dépôt ») +
> consigne : **insuffisants**, mesuré (#503 identique à #498). Options : (a) rouvrir large et laisser
> l'analyste annoter (`--sans-collecte` me_1, quelques centimes à chaque fois) ; (b) donner à la note une
> case « rappelé » par passage cité, que le code exclut des types (forme #68, contrat de la note).
>
> **Roadmap active : `roadmap/V3/05-frameworks-complets.md`** — capacité en cours : **§4 bis
> « L'atelier de valorisation »**. Les quatre frameworks manquants sont RÉDIGÉS (#92-#95) : 6 chapitres
> sur 6 ont une méthodologie. La 4 bis est OUVERTE (#96-#99, 2026-09-29) : gabarits maison, bac à
> calcul, contrat + pont + évaluation du modèle d'entreprise, SIGNATURE + registres (051), endpoints, et
> la REPRISE « un seul chiffre par dossier » (option c, #99) livrés (`app/valorisation/`,
> `api/valorisation_v2.py` ; aucun modèle en base, rien ne propose encore). **Encadré (#100), analyste
> corrigé (#101), horloge des comptes (#102) et faits postérieurs lus (#103) déployés** ; #104 (une
> seule dette nette) déployé ; #105, #106, puis #107-#110 (2026-10-03 : recette vs appariement, sœurs, « chaque
> framework ne lit que ses sujets », soldes du 10-K, prose des agrégats) déployés et rejoués sur RVMD
> qf_4/qf_6/qf_7 ; #111-#113 puis **#114 (2026-10-04, qf_4 scindée : faits / jugement) — qualité financière
> RVMD COMPLÈTE (4/4, note 1,0)** ; puis **#115 (2026-10-04) — LE SOCLE DES COMPTES** (comptes reconstitués,
> bouclés, une pièce du dossier ; l'encadré de qf_4/qf_7 lu dans le socle) ; puis **#116 (déployé 2026-10-11) — LES RATIOS
> MAISON** (gabarit 1.1.0 : capital employé, participations NVDA, bilan d'ouverture ; `ratios_maison.py` ; encadré
> de qf_1/qf_2/qf_3/qf_5 lu par le code ; autonomie non calculable sur une trésorerie générée) ; puis **#117
> (déployé 2026-10-12, `91e7cef`) — LIRE ET ANNOTER** : qualité financière NVDA instruite (8/8 répondues,
> note **0,62**) ; puis **#118 (2026-10-12) — LES DOUZE MOIS** : couverture des intérêts lue dans le socle
> sur douze mois (qf_4), qf_6 redéfinie sur douze mois et sans compensation (arbitrages utilisateur),
> « non significatif » sur un terme négatif. NVDA **0,75** (qf_4 soldée), RVMD **1,0** (socle 1.1.0, qf_4/qf_7
> réémises). ⛔ **BLOQUÉ : crédit DeepInfra épuisé (402)** — prochain : réémettre RVMD qf_6, collecter et
> réémettre NVDA qf_6, dater qf_8 NVDA, puis les nouveaux chapitres sur RVMD ET NVDA (objectif : deux cas
> très différents qui tournent juste).

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

- **Suite** `bash checks/run_all.sh` = **4463 assertions, 1 rouge ATTENDU** (`check_signature_modele_persist`, 8-K RVMD du 13/10 non lu — voir le prochain pas) — 2026-10-13 après #124 (négatif runner 5/0 neuf ; `negatif_collecte_executor.sh` 43/1, l'échec préexistant « script mort »). Avant : 4434 / 59 après #122. Avant : 4430 après #121
  (`check_prompts_exemples` neuf). Avant : 4419 / 58 après #120
  (négatif traducteur 22/0). Avant : **4398 assertions, 1 rouge ATTENDU** — 2026-10-12 après #118 :
  `check_signature_modele_persist` (RVMD qf_6 #1080 porte l'ancien encadré — se solde par sa réémission
  `--sans-collecte --questions=qf_6`, bloquée par le 402). Négatifs : contrat 56/0, analyste et référentiel
  rejoués (voir convention #118). Avant : **4389 assertions, 0 rouge** — 2026-10-12 après #117 (négatifs analyste
  62/0, contrat 52/0 ; `check_framework_persist` borné à ses analystes : la vraie réponse NVDA #1190 le
  faisait compter 3). Avant : 4381 le 2026-10-11 après #116 (négatifs des modules
  touchés tous verts : ratios maison 15/0 (neuf), socle 16/0, socle persisté 3/0, contrat 50/0, bouclage 11/0,
  référentiel **63/0** (relancé sans borne : il passe désormais au bout). Le faux vert de `negatif_bouclage.sh`
  (ligne hors scope refusée par la règle socle depuis #115, pas par la garde visée) est réparé : fixture
  discriminante + motif « HORS du scope » exigé). Avant : 4321 après #115. `negatif_collecte_executor.sh` 42/2 : les 2 échecs (mutation caduque « passe devant la consigne », script mort « aucune VALEUR de consigne ») PRÉEXISTAIENT (38/2 mesuré avant #112) — à réparer. Réconciliation : T6/T7 toujours rouges (capacité 9). Les 3 checks « live » sont hors suite par conception. Un
  check lancé à la main sans les montages de `run_all.sh` sort un faux FAIL.
- **Migrations** : **054 appliquée le 2026-10-13** (#121, consignes resynchronisées) ; la prochaine sera
  **055**. (aucune aux lots #100 et #116) : **051 appliquée** le 2026-09-29 (modèle de valorisation : versions + PV, tables
  vides) ; 052 appliquée le 2026-10-04 (période d'une ligne de plan) ; 053 appliquée le 2026-10-12 (#119). Vérifier en base avant
  d'écrire, jamais se fier à un tableau.
- **Production** : #119 n'était PAS dans le conteneur le 2026-10-13 (commité, non déployé) — déployé avec
  #120 ce jour-là (commit dans `git log`). Avant : `1adeb17` (#118 première moitié : qf_4 douze mois + `non_significatif_si_negatif`) puis le
  déploiement de fin de session (qf_6 + `facultatif` montré) — commit dans `git log`, vérifié dans le conteneur ;
  auparavant **`91e7cef`** (#117), `c55db45` (#116) ; vérifiée dans le conteneur après chaque déploiement. Chapitres `business_model`, `industry`, `management`, `valuation` : jamais collectés. **PV du comité : 0 décision.**
- **Réglage `v2_auto_enabled` = FALSE** : le passage du matin ne fait que RECENSER. Recensement réel du
  2026-09-26 : RVMD/NVDA/MSFT à jour ; AMZN 9, GOOG 9, AstraZeneca 125, Novo Nordisk 73 dépôts à lire ;
  9 titres hors EDGAR.
- **Notes flash en base** (catalogue d'événements **1.2.0**, relues le 2026-09-28 après #94) : RVMD
  #181-#186, NVDA #187-#188, MSFT #189 — mêmes types qu'en 1.1.0 (#80-#88), 0 refus, $0,0025 ; les
  lectures 1.0.0/1.1.0 restent conservées (append-only).
- **Dossier NVDA** (2026-10-13 après #121) : qualité financière **1,00** (8/8 courantes ; qf_8 **#1303**) ;
  qf_6 #1289. Avant (2026-10-12 après #118) : qualité financière **0,75** — qf_1 #1209, qf_2 #1210, qf_3 #1211,
  **qf_4 #1236** (couverture 425,8 fois sur douze mois, ne cite plus #843), qf_5 #1213, qf_7 #1214, qf_6 #1196
  (approximée, ANCIEN encadré, périmée), **qf_8 #1237** (`aucune_contrainte`, périmée : cite le prospectus du
  16/06 #845, antérieur à la clôture du 26/07) ; socle **#867** ; plan **#221** (collecte du 2026-10-12,
  19 lignes sur TOUT le framework, 12 mandats dont 3 « 402 » relançables : qf_6 ×2, qf_7 ×1).
- **Dossier RVMD** (2026-10-12 après #118) : qualité financière **1,0** — **qf_4 #1233** (dette brute 1 036,0 M$,
  trésorerie nette 2 902,0 M$, couverture « non significatif » : perte d'exploitation −1 627 M$ sur douze mois),
  **qf_7 #1235** (autonomie 38,4 mois ; #1234 « sans fondement » intermédiaire, supersédée), qf_6 #1080
  (ANCIEN encadré : à réémettre), qf_8 #1157 ; socle **#876** (1.1.0, remplace #814).
  Reste (mesure du 2026-10-03) : mo_1…mo_5, et les 24 questions des quatre nouveaux frameworks jamais collectées. Mandats 983-986 toujours ouverts.

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

**2026-10-13 — le périmètre du « bout en bout »**
« Bout en bout » = jusqu'au SUIVI de la position ; mais d'abord, faire tourner le système jusqu'à la
**note d'initiation de l'analyste** (six chapitres + fourchette de valeur) sur 3-4 titres très
différents, fonctionnement ET reproductibilité. Plan ordonné : **jalon « note d'initiation »** en tête
de `05-frameworks-complets.md` (A1…A11) — la dette « ré-analyse qui remplace une meilleure réponse »
y est avancée en prérequis du test de reproductibilité (A7).

**2026-10-13 — les descriptions juridiques (brevets, contrats)**
« À jour jusqu'au rapport annuel » : une description juridique (portefeuille de brevets, contrat de dette,
clauses) tirée du rapport annuel reste à jour jusqu'au rapport annuel suivant ou jusqu'à un fait qui la
TOUCHE (litige, nouveau brevet, nouveau financement) — comme un fonds qui revoit les brevets une fois par an.
Les faits importants qui ne la touchent pas (résultats de phase 3, comptes trimestriels) ne la périment pas.
**NON CONSTRUIT, à dessein** : mesuré le jour même sur RVMD, la règle ne rendrait à jour qu'au mieux 1 réponse
de défendabilité sur 5 — les autres sont périmées par des pièces NON juridiques (liste des concurrents du
10-K, description du coût de développement, données cliniques du 31/05). À construire quand une réponse
n'est périmée QUE par une pièce juridique. Esquisse : le référentiel déclare par ingrédient (et au besoin
par stade) qu'il est juridique et quels types d'événements le touchent ; `servir_answer` juge les pièces
juridiques contre cette horloge propre (types qui touchent + clôture publiée ≥ date + 1 an). Manque au
catalogue un type « contestation de propriété intellectuelle / litige ».

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

**⚠️ EN TÊTE — OBJECTIF DE L'UTILISATEUR (2026-09-30) : « arriver rapidement à un système qui a tourné
de façon correcte sur deux cas de figure très différents afin d'en valider la généralité » — RVMD
(biotech pré-revenus) et NVDA (mature). Ordre retenu : finir la qualité financière RVMD, puis instruire
les nouveaux chapitres sur RVMD ET NVDA (dont la qualité financière de NVDA, aucune réponse en vigueur),
AVANT l'agent qui écrit le modèle de valorisation (il n'aurait rien pour fonder ses hypothèses).**

**État RVMD qualite_financiere au 2026-10-03 (fin de session) — #107 à #110 déployés (`22c722b`)**
- Corrigé en amont et déployé : #107 (la carte d'appariement qui PROLONGE la recette du catalogue prend
  la main — trésorerie + placements ; les SŒURS d'une réponse partent avec la pièce élue ; 76 orphelines
  d'avant #106 rattachées sans modèle, trace `tools/retraits/2026-10-03_rattachement_soeurs.txt`) ; #108
  (arbitrage utilisateur : « chaque framework ne doit traiter que de ses sujets » — le dossier ne remet que
  les pièces classées sous ses points, plus de « hors index ») ; #109 (un solde du 10-K reste un instant :
  #741/#734 lisaient la trésorerie au 31/12/2025 → supersédées par #751 3,94 Md$ et #744 au 30/06 ; un
  renvoi d'analyste hors contrat devient un refus nommé) ; #110 (un agrégat déterministe se présente en
  « Relevé des dépôts SEC », plus en « Calculé »).
- 3 passages réels `executer_chaine RVMD qualite_financiere pre_revenus --questions=qf_4,qf_6,qf_7`
  (plans #186 crash au renvoi → #109 ; #189 réponses 1035-1037 ; #192 réponses **1050-1052**, en vigueur).
  Résultat : **qf_6 #1051 `repondu` A**, mais servie PÉRIMÉE ; qf_4 #1050 et qf_7 #1052 `non_fondable`.
  `check_signature_modele_persist` toujours rouge (aucune réponse RVMD reprenable).
- **#111 déployé (`d1e4701`, arbitrage utilisateur)** : chaque affirmation se cite par sa source la plus
  récente, qui REMPLACE l'ancienne dans la citation (consigne + relecture du même point). **qf_6 #1080
  `repondu` A, À JOUR** — première réponse RVMD reprenable ; suite **4150/0, tout vert**.
- **#112 déployé (`6946c55`, `b9bdea6`) — les douze mois glissants.** La grammaire dit `Concept[ttm]`
  (période de la référence, pas concept neuf) ; le producteur la lit au dépôt (exercice clos + cumul en
  cours − cumul de la même période l'an passé, reconnus par leur durée ; dernier dépôt = 10-K ⟹
  l'exercice) ; refus NOMMÉ si une lecture manque, jamais de repli sur l'exercice. Mesuré sur les vrais
  dépôts : RVMD **−1 223 M$** sur douze mois au 30/06/2026 (exercice 2025 : −898 M$) ; NVDA 134,4 Md$ ;
  MSFT = exercice (10-K dernier dépôt). Une carte qui lit le concept d'une recette sur douze mois prend
  la main sur la recette (période que la recette ne lit pas). Geste `--refaire-carte` (executer_chaine).
  Suite **4184/0**.
- **#113 / bis / ter déployés (`3a1588f`, `efba39b`, `b2e0f5f`, 2026-10-04) — qf_7 RVMD RÉPONDUE.**
  Arbitrages utilisateur du 2026-10-04 : (1) **la demande précise la période** — chaque ligne de plan
  traduite déclare `periode` (exercice clos · douze mois glissants · dernier bilan · sans période,
  migration **052**) et le code la respecte (un flux demandé sur douze mois se lit `[ttm]` quel que soit
  le choix de l'apparieur, la recette de l'exercice s'efface, une carte contraire est refusée) ;
  (2) **#774 écartée** au registre (`tools/retraits/2026-10-04_ecart_774.sql`). En chemin : l'analyste
  ne voit plus, sur une question de mesure fermée à l'approximation, les pièces d'interprétation (#789,
  la soustraction de #78 recopiée par le web) ; les pièces d'un fait postérieur lu entrent d'office dans
  la fondation. Résultat (plan #205, réponse **#1143**) : `repondu` A / mesure — trésorerie 3 935 M$ (#786),
  consommation **1 220 M$ sur douze mois** (#787 = 1 223,03 : l'analyste recopie l'arrondi « 1,22 Md$ »
  du texte — résidu de rendu), aucune échéance à douze mois (#791), baux du 8-K lus (#723/#733),
  autonomie **38,7 mois**. Qualité financière RVMD **0,33 → 0,67** (qf_4 reste `non_fondee`, clauses).
- **Résidus nommés** : (a) le rendu d'un montant en Md$ à 2 décimales fait recopier un arrondi — afficher
  le M$ exact dans la tête du fait (#45/#46) ; (b) l'analyste voit les corpus de TOUTES les questions
  dans un même appel : au 1er tour il a cité pour qf_7 une interprétation montrée sous qf_6 (le renvoi l'a
  corrigé) — une citation hors du corpus de SA question pourrait être refusée nommément avant le pont ;
  (c) cartes NVDA/MSFT écrites avant `[ttm]` et avant la période : `--refaire-carte` au prochain passage ;
  (d) `negatif_collecte_executor.sh` 42/2 (2 échecs PRÉEXISTANTS).
- **#114 déployé (`73b9cd5`, arbitrage utilisateur 2026-10-04) — qf_4 SCINDÉE « pour distinguer les faits
  et le jugement »** : qf_4 = tableau de la dette (mesure, A) ; qf_8 = revue des clauses (jugement, A, sans
  encadré). Cause : une clause est du texte, qf_4 (mesure) était infondable pour toute entreprise endettée.
  13 liens d'index déplacés (`tools/retraits/2026-10-04_scission_qf4_qf8.sql`). Plan #210 : **qf_4 #1156**
  `repondu` A/mesure `tresorerie_nette` (dette brute 487,4 M$ = valeur comptable, trésorerie 3 935,4 M$,
  dette nette −3 448 M$) ; **qf_8 #1157** `repondu` A/interprétation `contrainte_moderee`. Relu contre les
  pièces : juste. **À relire par le comité** : (i) qf_8 dit « engagements légers, aucun covenant financier »
  mais classe `contrainte_moderee` — `aucune_contrainte` serait plus cohérent avec son propre texte ;
  (ii) dette brute à la valeur comptable (487,4) plutôt qu'au nominal dû (500) — écart immatériel ici, mais
  le pont vers la valeur par action devra trancher nominal vs comptable.
- **Constat #114 (nommé, non corrigé)** : la nature d'une lecture de clause dépend de l'`entry_type` choisi
  par le collecteur (#779/#780 `fact_financial` → mesure, #712/#713 `fact_qualitative` → interprétation) —
  un texte étiqueté `fact_financial` hérite de l'autorité d'un relevé (trou latent de #51) ; #779/#780 sont
  en plus datées au 31/12/2025 pour des obligations émises en avril 2026.
- **#115 déployé (`2837d08`, 2026-10-04) — LE SOCLE DES COMPTES** (arbitrages utilisateur : « réalise le socle
  commun des comptes avant de poursuivre de RVMD vers NVDA » ; chiffres de l'encadré « repris du socle » ;
  « ce n'est pas de niveau comité d'arbitrer les choix de reconstitution des comptes »). Détail : convention
  #115. Mesuré sur les vrais dépôts (`bash tools/montrer_socle.sh RVMD NVDA MSFT`, gratuit) : 0 écart de
  bouclage sur les trois. Réémission RVMD (`--sans-collecte --questions=qf_4,qf_7`, 0 refus, relue) :
  **qf_4 #1176** dette brute **1 035,976 M$** (convertibles 487,4 + **Royalty Pharma 548,5**, reclassé en dette
  par convention maison — la note précédente l'ignorait), trésorerie et placements 3 937,969, trésorerie nette
  2 902,0 ; **qf_7 #1177** consommation sur douze mois **1 232,131 M$** (flux disponible : exploitation −
  investissements corporels, au lieu de 1 220 recopié), autonomie **38,4 mois**. Valorisation : la dette nette
  de RVMD reprise par va_1/va_2 change de −3 448 à −2 902 M$.
- **Convention PROPOSÉE à l'utilisateur, non confirmée (appliquée sauf objection)** — capital employé : la
  trésorerie, les placements et les PARTICIPATIONS sortent (leurs revenus sont hors exploitation : les
  plus-values NVDA sur participations font 9 Md$ en 2026, 30 Md$ sur douze mois) ; les écarts d'acquisition
  restent ; rendement hors écarts d'acquisition publié en second chiffre.
- **Résidus #115** : (a) 189,3 M$ d'« autres passifs non courants » RVMD au 30/06 non expliqués (visibles en
  solde) ; (b) MSFT : amortissements lus sur `Depreciation` (concept de note, sans les incorporels) et
  acquisitions sur un concept propre à MSFT (Activision tombe en « autres flux d'investissement ») ;
  (c) participations NVDA (OpenAI etc.) rangées en « autres actifs non courants » — une ligne
  `participations` est à créer AVEC les ratios maison ; (d) émetteurs hors USD / 20-F non éprouvés ;
  (e) le reclassement d'émetteur est écrit à la main (le jour venu, un agent le PROPOSE en lisant les notes,
  le directeur de la recherche le valide).
- **#116 déployé (`c55db45`, 2026-10-11 ; écrit le 2026-10-04) — LES RATIOS MAISON** (détail : convention #116). Mesuré sur les vrais dépôts,
  gratuit (`bash tools/montrer_socle.sh NVDA MSFT RVMD`) : NVDA rendement du capital employé moyen 5 ans
  **111,9 %** (2026 : 165,4 %), pente +37,9 pts/an, conversion 3 ans 87,5 %, 100 M$ par point de croissance ;
  MSFT **41,0 %**, pente **−6,3 pts/an** (le capital croît plus vite que le résultat : 57 % → 31 %), conversion
  135,2 %, 4 657 M$/pt ; RVMD : capital moyen négatif en 2024-2025 ⟹ aucun rendement (motivé). qf_7 :
  l'autonomie d'un émetteur qui génère de la trésorerie est « non calculable », dénominateur nommé (#44).
  **Conventions maison appliquées sauf objection de l'utilisateur** (non demandées, « pas de niveau
  comité ») : capital MOYEN (ouverture + clôture) ; taux d'impôt effectif borné [0 ; 1] ; droits d'utilisation
  hors du capital (le loyer est une charge) ; conversion = rapport des sommes sur 3 ans ; capital par point =
  premier → dernier exercice du socle ; résultat après impôt TEL QUE DÉPOSÉ (la normalisation reste qf_6).
  ⚠️ La pièce socle RVMD #814 est au gabarit 1.0.0 : le prochain passage de chaîne RVMD la republiera (1.1.0)
  et qf_4 #1176 / qf_7 #1177, qui la citent, seront à réémettre (`--sans-collecte --questions=qf_4,qf_7`).
- **Résidus #116** : (a) MSFT ne dépose pas `OperatingLeaseLiabilityCurrent` : ses loyers à un an restent
  dans « autres passifs courants » alors que ses droits d'utilisation (24 Md$) sortent — écart ~5 % du capital ;
  (b) `resultat_operationnel_apres_impot_normalise` (qf_1) reste RELEVÉ par l'analyste sur une question de
  mesure à plancher A — la normalisation est un jugement : forme à trancher sur la mesure NVDA ;
  (c) pas de ratios sur douze mois glissants (exercices seulement) ; (d) une ligne « mois de charges
  couverts » pour qf_7 `rentable` (sa variable) n'existe pas.
- **#117 (2026-10-12) — qualité financière NVDA instruite, puis LIRE ET ANNOTER** (convention #117). Passage
  `--refaire-carte` (plan #216, réponses 1190-1197, 0 refus) relu contre le socle : chiffres justes ; mais 8/8
  nées périmées (rachat Hugging Face 8-K 02/09, type `perimetre`, que les mesures n'avaient pas le droit de
  lire). Arbitrage utilisateur « lire et annoter » → relance `--sans-collecte` qf_1-5,7 → note 0,62.
- **#118 (2026-10-12) — les douze mois** (convention #118). qf_4 NVDA citait #843 parce que l'ingrédient
  « couverture des intérêts » n'était pas lu dans le socle : il l'est, l'encadré la calcule sur douze mois.
  **Arbitrages utilisateur du 2026-10-12 sur qf_6** : douze derniers mois (refaite à chaque publication) ;
  somme des retraitements poste par poste, sans compensation. Référentiel modifié (3 relevés + 2 calculés + 1
  lu dans le socle), suite verte sauf RVMD qf_6 à réémettre.
- **✅ CRÉDIT DEEPINFRA RÉTABLI (2026-10-12, vérifié par un appel minimal avant toute dépense) — (1) FAIT :
  RVMD qf_6 réémise `--sans-collecte --questions=qf_6`** (réponse #1256, `repondu` A, cite [784, 785, 771,
  303, 304, 305, 876], relue fidèle) — **`check_signature_modele_persist` au vert, suite 4399/0.**
  **(2) FAIT, avec incident et correctif en chemin — NVDA qf_6.**
  **Constat #118 fermé en code** (`tools/executer_chaine.py`) : `--questions=` restreint maintenant AUSSI
  la collecte (maillon 1), pas seulement l'analyse — `executer_collecte_framework`/`traduire` savaient déjà
  le faire (lot 5, bouclage), seul ce passage ne le branchait pas. Un relaunch scopé `--questions=qf_6` ne
  replanifie/recollecte plus les 8 questions du framework pour relancer une seule.
  **Incident (leçon de méthode, pas un défaut du projet)** : un premier essai (`timeout 300 | tail`) a
  semblé « Terminated » (exit 143) mais le `docker run --rm` sous-jacent a continué seul ; une relance
  nohup lancée en parallèle a produit DEUX collectes NVDA/qf_6 concurrentes (plans #227 et #228) écrivant
  dans la même base en même temps. **Toujours vérifier `ps aux`/`docker ps` avant toute relance**, et
  utiliser le `run_in_background` du Bash tool plutôt qu'un `nohup … &` imbriqué (qui double le
  backgrounding et rend le process réel introuvable). Les deux plans concurrents ont tous deux CRU réussir
  (0 mandat pour le #228) mais produit un `repondu` (#1270) avec des chiffres **FAUX**.
  **Défaut trouvé en relisant le verbatim contre la vraie pièce EDGAR** (`feedback_garde_structure_pas_sens`
  — exactement ce que le bandeau de sortie de l'outil demande de faire) : #1270 citait
  `retraitements_cumul_en_cours = 222 M$ (« cumul S1 FY2027 »)` et `retraitements_cumul_an_passe = 0 M$`.
  Vérifié contre le vrai 8-K (accession `0001045810-26-000073`, EX-99.1 `q2fy27pr.htm`, table
  « RECONCILIATION OF GAAP TO NON-GAAP… » — fetch direct `data.sec.gov`/`sec.gov`, hors de toute
  dépense modèle) : le tableau réel a CINQ colonnes (Three Months : 2026-07-26/04-26/2025-07-27 ; Six
  Months : 2026-07-26/2025-07-27) ; la ligne « Total impact of non-GAAP adjustments to operating income »
  vaut 222 / 247 / 101 / **469** / **263**. **222 est la colonne TROIS MOIS, pas SIX MOIS** (vraie valeur
  semestrielle : 469) ; **0 n'existe NULLE PART dans le tableau** (vraie valeur du comparatif N-1 : 263) —
  un chiffre sans aucun support, pas une pièce mal lue. Même famille que #78. **Retiré** —
  `tools/retraits/2026-10-12_nvda_qf6_cumul_errone.sql` (DELETE #1270, restaure #1269 `non établi`,
  honnête, courante) — suite revérifiée **4399/0** après retrait.
  **Cause ARBITRÉE et CORRIGÉE (option A choisie par l'utilisateur, 2026-10-12)** : migration **053** —
  `cumul_publie`, cinquième valeur de `PERIODES` (un cumul TEL QUE L'ÉMETTEUR LE PUBLIE, avec son
  comparatif N-1, JAMAIS recalculé — distinct de `douze_mois_glissants`, que LE SYSTÈME reconstruit).
  **Second défaut trouvé en traçant la cause** : `construire_requete_web` ne lisait JAMAIS `ligne.periode`
  — même `douze_mois_glissants` était perdu dès qu'une ligne partait au web. Corrigé : `_PHRASE_PERIODE`
  (détenteur unique, couverture de `PERIODES` vérifiée par `assert`) traduit chaque valeur en phrase
  explicite dans la requête ; le prompt du traducteur enseigne la 5ᵉ valeur et la distingue de
  `douze_mois_glissants`. Vérifié par mutation (retirer le câblage fait rougir 6 asserts nommés de
  `check_collecte_executor §5ter`). Au passage : 2 mutations de `negatif_collecte_executor.sh` réparées
  (« ni inventaire ni carte » — `\n` dans le motif, jamais converti par le harnais ; « passe devant la
  consigne » — indentation obsolète) ; 1 échec préexistant documenté et laissé tel quel (« aucune VALEUR
  de consigne » — script mort, sans rapport avec #119). Détail : convention **#119** du `CLAUDE.md`.
  Suite **4410/0 sur 56 scripts**. **✅ VÉRIFIÉ CONTRE LE VRAI MODÈLE (2026-10-12, plan #233, réponse
  #1289, solo, `ps aux`/`docker ps` vérifiés propres avant et après)** : le traducteur a choisi
  `periode="cumul_publie"` pour `ecart_publie_ajuste` (la 5ᵉ valeur est EMPLOYÉE, pas seulement
  acceptée) ; qf_6 ressort `repondu` A — mais cette fois **honnête** : « il ne donne que le
  rapprochement du seul T2 FY2027 … sans le cumul semestriel » → `retraitements_cumul_en_cours`/
  `cumul_an_passe` **non établis**, jamais un chiffre trimestriel mislabellé en semestriel comme #1270.
  **Le défaut #119 est fermé** : le système échoue maintenant PROPREMENT (silence nommé) plutôt que de
  fabriquer. **Résidu, nommé, séparé et de moindre sévérité** : le search-worker a épuisé ses 6
  itérations d'outils (« clôture sur ce qui a été collecté ») sans re-extraire la colonne Six Months du
  tableau réel (469/263, vérifiées contre EDGAR le 2026-10-12) — il a réutilisé l'entry #896 déjà en
  base (Three Months seulement). Ce n'est plus un risque de donnée fausse (l'analyste le voit et le dit),
  c'est une limite de PROFONDEUR de collecte — à reprendre un jour si le chiffre exact importe (budget
  d'itérations, ou une requête qui cible explicitement « relis la section RECONCILIATION et donne les
  DEUX colonnes Six Months »). Pas de dette bloquante : qf_6 NVDA est `repondu`, acquitté, honnête.
  **(3) INSTRUIT le 2026-10-13 — qf_8 NVDA → #120** (convention #120) : le traducteur, sans horloge,
  envoyait 19/19 lignes au 10-K « dernier exercice » ; il reçoit désormais la date du jour et la clôture des
  derniers comptes publiés. Vérifié (plan #235) : lignes ancrées sur le 10-Q du 26/07 ; pièce **#905**
  (conformité aux covenants au 26/07, citation exacte du 10-Q). **qf_8 #1296 reste PÉRIMÉE** : la ligne
  `marge_avant_declenchement` a échoué au collecteur (mandats **2612/2613** ouverts, `portee_temporelle`
  omise), #845 (16/06) y reste en vigueur. **→ #121 (même jour)** : cause = l'exemple de la consigne du
  collecteur en base portait encore `source_date` ; migration **054** + `check_prompts_exemples`. Relance
  (plan #237) : **qf_8 #1303 courante**, qualité financière NVDA **1,00**. Mandats 2612/2613 encore
  `ouvert` (la question a trouvé sa réponse — même famille que 983-986).
  **(2 bis) FAIT (2026-10-13)** : RVMD qualité financière **1,00, 4/4 courantes** — vérifié pièce par pièce
  (toutes ≥ 30/06) et contre EDGAR (rien de nouveau depuis le 01/09 hors formulaires 4/144).
  **Défendabilité RVMD refaite** (rouverte par l'approbation FDA du 26/08) : un premier passage (plan #238)
  a tourné sur l'horloge de SILEXION → **#122** (CIK lu au registre, jamais déduit du dossier ; retrait
  `tools/retraits/2026-10-13_rvmd_identite_silexion.sql`), puis relance `--sans-collecte` : réponses
  **#1316-#1321** (mo_1 `barriere_structurelle`, mo_2 approximée, mo_3 `en_elargissement`, mo_4
  approximée `duree_longue` **19 ans** = dernière expiration 2045 — le passage faussé disait 5 ans = première
  expiration 2031 : **à relire par le comité**, quelle échéance de brevet fait la durée de la barrière ?, mo_5
  `vecteur_en_mouvement` sur Silexion seul). Chiffres relus contre les pièces (#697, #923, #695). Restent
  **5/5 périmées**, pour de bonnes raisons (voir l'arbitrage ci-dessous) : remède = une collecte de
  défendabilité plus fraîche (paysage concurrentiel postérieur au 30/06), pas un correctif de règle. **(4) PAS FAIT — nouveaux chapitres sur RVMD et NVDA.**
- **Constat #118 — `executer_chaine --questions=` ne restreint PAS la collecte** : seule l'analyse est
  restreinte ; le plan #221 a porté sur les 8 questions pour qf_8 seule. Le bouclage sait déjà planifier sur un
  périmètre (pont [P] « HORS du scope ») : à brancher au maillon 1 de `executer_chaine`.
- **✅ ARBITRAGE qf_8 RENDU (2026-10-12) — les résultats trimestriels continuent de rouvrir la revue des clauses
  (vérification de routine), rien à changer.** Règle de l'utilisateur : « selon l'émetteur si la vérification
  coûte, sauf si la complexité induit un risque d'erreur ; sinon chaque trimestre ». Mesuré : coût < 1 cent
  par émetteur et par trimestre (ordre de grandeur du traducteur, $0,002 pour ~18 k jetons) ; et la règle
  conditionnelle serait une garde nourrie de sa propre réponse (un covenant manqué une fois ne serait plus
  jamais relu avant le financement suivant). Condition « accès aux financements » mesurée vraie au passage
  (3/3 repérés), utile si la question revient. qf_8 NVDA se soldera donc par sa relecture `--sans-collecte`.
- **À relire par le comité (NVDA)** : (i) qf_6 conclut « part faible, 2,6 % » sur un SOLDE net de −3 070 M$
  qui compense les rémunérations en actions (+6 386, que NVIDIA a cessé d'exclure au T1 FY2027) par des
  plus-values sur participations (≈ −10 Md$) — en brut ≈ 14 % du résultat ; une précision de la question
  (somme des retraitements en valeur absolue) serait une opération de données ; (ii) qf_1 rend désormais
  `resultat_operationnel_apres_impot_normalise` = 110 676 M$, qui est le résultat TEL QUE DÉPOSÉ du socle,
  pas un normalisé (résidu #116 b) ; (iii) coût du capital non établi : les trois estimations tierces
  (10,9 / 12 / 13 %, #833-835, tier C) sont sous le plancher A de qf_1 — **qui fixe le coût du capital du
  fonds ?** (un fonds le fixe en interne, commun au portefeuille) : arbitrage à poser avant la valorisation ;
  (iv) garanties de valeur résiduelle SB Energy jusqu'à 105 Md$ dès 2028 (8-K 17/08) : engagement hors bilan
  lu par qf_4/qf_7/qf_8, non chiffré.
- **Constat #117** : l'appariement NVDA a échoué de façon intermittente pendant le passage (rejoué seul : 20
  lignes, $0,003) ; son motif n'existait qu'au journal (niveau info) — désormais porté par la carte et
  imprimé. Aucune carte NVDA en base : le prochain passage avec collecte la construira.
- **✅ RÉSOLU (#121) —** ~~Collecteur — datation omise sur les longs passages (constaté #120, 2026-10-13)~~ : le search-worker
  rend des pièces sans `portee_temporelle` après 6 itérations d'outils (70-190 k jetons) et ne se corrige
  pas en 5 à 8 relances ; **15 mandats `echec_collecte` sur ce motif depuis le 2026-09-25** (≈ 15 % des
  échecs). La règle vit en suffixe de code (`worker.py` ~l.110), la consigne en base (`agent_prompts` id 5)
  n'en dit rien. Le contrat refuse justement (rien de faux écrit), mais la collecte se perd et des réponses
  restent périmées. Ce que ferait un fonds : un document reçu sans date n'entre pas au dossier — mais on
  redemande la date, on ne jette pas la recherche. Pistes : rappel de la règle EN FIN de conversation
  (près de la sortie), ou relance ciblée sur le seul champ manquant. À éprouver contre le vrai modèle.
- qf_4 : covenants (#712/#713) en `interpretation` (prose d'indenture) et collecte web des clauses coupée
  par le budget 180 s ; échéancier : datation hétérogène signalée. #751 garde l'ancienne prose « Calculé »
  jusqu'à sa prochaine réécriture (sans effet : #110 + la relecture).
- Résidu #107 : `rattacher_soeurs` a fait passer #664 (défendabilité mo_1) en antérieure (collecte précédente).

**⚠️ DETTE BLOQUANTE POUR LA PRODUCTION (consignée à la demande de l'utilisateur, 2026-09-29) — AVANCÉE
le 2026-10-13 en prérequis du test de reproductibilité (jalon A7 de la roadmap 05)**
- Une ré-analyse sur les MÊMES pièces peut REMPLACER une réponse instruite par une moins bonne
  (qf_6 approximée → « sans fondement » le 29/09), et un refus d'agent devient un renvoi du manager
  (« question sans réponse ») donc une demande de recherche à tort. Le seul retour arrière est un
  retrait manuel en base (SQL + sauvegardes). Inacceptable en exploitation : un fonds ne laisse pas une
  note moins bonne remplacer la note en vigueur sans que quelqu'un l'ait lue. Pistes à instruire en
  termes métier : la nouvelle réponse n'entre en vigueur que si elle est au moins aussi fondée (ou si
  le comité l'accepte) ; un refus d'agent ne se convertit jamais en demande de recherche (même famille
  que les mandats 983-986) ; un geste « retirer un passage » tracé, au lieu du SQL à la main.

**Remontés du jalon du lot 7 au 2026-09-28 (non traités, toujours vrais)**
- **Résidus #122** : (a) #695 (daté 05/08) cite un communiqué du 14/09 et l'approbation du 26/08, #697 (daté
  31/05) parle de « septembre 2026 » — pièces d'héritage à datation mêlée ; (b) mo_3/mo_5 fondent le
  « vecteur en mouvement » sur Silexion (microcapitalisation, deux avis de radiation Nasdaq) alors que le dossier
  porte Roche divarasib (phase 3 positive, 02/07) et les revues FDA du 07/10 (doutes d'efficacité, −6,3 % le
  08/10, #929-#931), non cités — à relire par le comité ; (c) la date d'ingrédient des pièces web (#929-#931)
  n'entre dans aucune horloge : un fait public non déposé à l'EDGAR ne rouvre rien (veilleur à construire).
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
3. **`CLAUDE.md` du projet** — conventions **#25 → #123** ; pour le lot 6 : #53/#54 (recalcul à la
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
> a été la première réponse RVMD reprenable ; #104-#110 (dette nette unique, autonomie prudente, lecture
> des dépôts postérieurs, sœurs, « chaque framework ne lit que ses sujets », soldes du 10-K), #111-#113, #114
> (qf_4 scindée faits / jugement, qf_8 neuve) : qualité financière RVMD COMPLÈTE (1,0) ; #115 le SOCLE DES
> COMPTES (comptes reconstitués et bouclés, encadré lu dans le socle) ; #116 les ratios maison sur le
> socle ; #117 lire et annoter (qualité financière NVDA 0,62) ; #118 les douze mois (couverture des intérêts,
> qf_6 sur douze mois et sans compensation ; NVDA 0,75, RVMD 1,0 ; RVMD qf_6 à réémettre, NVDA qf_6/qf_8 à
> dater — BLOQUÉ par le crédit DeepInfra), puis les nouveaux chapitres sur RVMD ET NVDA, l'ordre dans la chaîne d'instruction, l'agent qui écrit le modèle, l'option 1 au
> cours du jour, Greenwald, la dépendance va_1/va_2 → va_6 ; puis éprouver les six frameworks sur NVDA/MSFT/RVMD
> + un 4ᵉ titre, et décider à quel niveau vit l'adaptation à l'entreprise. Lots 0-6 de
> la spec 03 clos ; lot 7 suspendu (son reste = capacités 7-9 de la roadmap 05). Re-requêter toute
> ligne de base avant de s'en servir.
