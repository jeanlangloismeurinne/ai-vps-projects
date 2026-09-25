---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-09-25
project: portfolio-tracker
role: >
  Prompt de reprise du chantier V3 (frameworks). Il ne porte que l'ÉTAT, le PROCHAIN JALON, ce qui
  reste ouvert et les pièges. Le récit des lots livrés est dans `00-REPRISE-ARCHIVE.md` (l'état
  complet de ce fichier avant son délestage du 2026-09-25 y est copié tel quel, section
  « 2026-09-25 (4) »), les règles durables dans le `CLAUDE.md` du projet (conventions #25…#82), la
  PREUVE de ce qui existe dans `backend/checks/` — qu'on exécute.
---

# Prompt de reprise — portfolio-tracker V3

> **LIRE D'ABORD `roadmap/V3/PRINCIPES-FONDATEURS.md`** — à chaque reprise, sans exception.
> Deux principes y gouvernent toute la conduite du chantier : (1) toute demande d'arbitrage se
> formule en **termes métier**, jamais techniques ni fonctionnels ; (2) chaque décision s'éclaire
> par la pratique d'un **vrai fonds d'investissement**.

> **Ce fichier ne s'empile pas.** Récit → `00-REPRISE-ARCHIVE.md` (copie conforme) ; durable →
> `CLAUDE.md` du projet ; outillage transverse → `../../../CHANTIER_OUTILLAGE_DEV.md`. Protocole
> d'éviction : `CONTROL_SYSTEM.md` §5. Le prochain pas n'est écrit qu'à **un seul endroit** :
> ▶ PROCHAIN JALON.

---

## 🎯 Roadmap active — `roadmap/V3/03-spec-frameworks.md` (ouverte le 2026-09-09)

**Le diagnostic d'origine, en une phrase** : le système rangeait la connaissance dans une grille
fermée de 19 champs identique pour tout émetteur, et écartait en silence tout ce qui n'y entrait
pas. La V3 la remplace par des **frameworks stables à variables par entreprise** (référentiel
inerte `app/frameworks/frameworks.yaml`), chacun garanti par un **manager**, avec la chaîne
**traducteur → collecteur → apparieur → analyste → manager → projection du mémo**.

### État des lots (spec §10)

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
| **6** | **Le parcours : `qualite_info` dérivée · 3 niveaux de drill-down · acquitter/renvoyer tracés (A7)** | 🔄 **maillons 1-2 livrés** (déployé `7af7276`) |
| 7 | Second pilote complet · acceptation T1-T8 · réconciliation à 0/0 (état terminal) | ⬜ |

Détail de chaque lot : archive (entrées datées) + conventions #57 → #82 du `CLAUDE.md`.

### Mesures courantes — à RE-REQUÊTER avant de s'en servir

(`feedback_ligne_de_base_est_une_mesure` : aucun de ces chiffres ne se cite sans être re-mesuré.)

- **Suite** `bash checks/run_all.sh` = **3276 assertions / 0 échec sur 45 scripts** (2026-09-25,
  après le maillon 2 ; re-mesuré 3200 au départ, la reprise disait 3194). Montage `/frontend` ajouté.
  Les 3 checks « live » (`check_fetch_live`, `check_fetch_relevance`, `check_cours_cote_live`)
  sont hors suite par conception. Un check lancé à la main sans les montages de `run_all.sh`
  (`/roadmap`, `/contract_frozen`) sort un faux FAIL.
- **Migrations** : **047 appliquée** (cause d'un manque de collecte) ; la prochaine écrite sera
  **048** (trace A7). Vérifier en base avant
  d'écrire, jamais se fier à un tableau.
- **Production** : stack sur **`7af7276`** (backend) / **`75fe521`** (frontend), vérifiée par
  `docker exec … grep` et capture headless des 3 écrans (image `ev-prices` = Playwright).
- **Chaîne réelle** : allée de bout en bout sur RVMD × `qualite_financiere` (2026-09-21) et RVMD ×
  `defendabilite` (2026-09-25). `qualite_info` mesurée RVMD : `defendabilite` **0,00** (5 non
  fondables → à collecter) · `qualite_financiere` **0,00** (2 réponses applicables, périmées → à
  rafraîchir ; rang moyen A− publié). Aucun investissement produit : **normal**, l'aval vient après.

---

## ▶ PROCHAIN JALON — LOT 6, LE PARCOURS DU COMITÉ (spec §8)

**Ce que le lot doit donner au comité** : pouvoir descendre d'un verdict jusqu'à la pièce qui le
fonde, et **agir** sur chaque réponse — l'accepter telle quelle ou la renvoyer en recherche — avec
une trace de chaque décision humaine.

1. ✅ **`qualite_info` dérivée** (2026-09-25, conv. **#82**, aucune migration) — la note de qualité
   d'un dossier cesse d'être une appréciation du modèle et devient une mesure recalculée à la
   lecture, une par (framework, version). Quatre arbitrages du fonds rendus. Gardes :
   `check_qualite_info` 26/0 + négatif 6/0 · lecture gratuite `bash tools/montrer_qualite_info.sh RVMD`.
2. ✅ **Les 3 niveaux de drill-down** (2026-09-25, conv. **#83**, migration **047**) — `parcours.py`
   détenteur unique de l'assemblage (note projetée et note de qualité y passent) ; `GET
   /v2/tickers/:id/dossier` · `/frameworks/:fid` · `/frameworks/:fid/q/:qid` ; alerte « peut-on
   décider ? » EN TÊTE de `/v2/tickers/:id`, chaque manque avec sa cause (déclarée par le
   collecteur) ; niveau 3 en bijection `data-champ` ↔ contrat. Gardes : `check_parcours` 63/0 +
   négatif 21/0 · `negatif_047.sh` 3/0 · lecture gratuite `bash tools/montrer_parcours.sh RVMD`.
3. 🔜 **PROCHAIN — Acquitter / renvoyer tracés (A7, spec §8.2)** — « renvoyer » emprunte **le même canal**
   que le renvoi du manager (`framework_mandates`, origine `comite`, déjà ouverte par la 043 ;
   bouclage `bouclage.py` déjà en prod) : un seul détenteur. « Acquitter » demande une **trace**
   de la décision humaine → table de trace, migration **048**, écrite juste avant son maillon.
   Les boutons se posent sur l'écran de niveau 3 (`pages/v2/tickers/[ticker_id]/frameworks/
   [framework_id]/q/[question_id].js`) ; l'alerte du niveau 1 devra lire l'acceptation (une question
   acceptée par le comité cesse d'être un manque tant qu'aucun fait important ne la fait tomber —
   même `ancre_substantielle` que l'actualité, déjà câblée dans `charger_etat_dossier`).
   Ordre imposé : contrat → agent → données.

**✅ ARBITRAGES DU COMITÉ RENDUS PAR L'UTILISATEUR (2026-09-25)** — posés en termes de fonds
(principes 1 et 2). Ils cadrent les maillons 2 et 3 :
1. **Procès-verbal COMPLET quand le comité accepte une réponse faible** : qui, quand, sur quelle
   **version du dossier**, avec une **justification écrite obligatoire**. Un vrai comité écrit
   pourquoi il passe outre une faiblesse, pour qu'on puisse relire la décision six mois plus tard
   dans son contexte. ⟹ la trace A7 (migration 047) porte l'auteur, l'instant, la version du
   dossier (framework + version + réponse) et un motif non vide.
2. **Une acceptation TOMBE dès qu'un fait important est publié après elle** (résultats,
   approbation réglementaire, acquisition), et la question repasse devant le comité ; une
   information de routine ne la remet pas en cause. ⟹ la validité d'une acceptation se
   **recalcule à la lecture** contre l'ancre matérielle (`ancre_substantielle`, #53/#54 — un 8-K
   de pure forme ne périme rien), jamais figée à l'écriture.
3. **La page d'un titre répond d'abord à « peut-on décider ? »** — avec une nuance de fond :
   le processus est conçu pour que le système aille **lui-même** chercher ce qui manque avant de
   présenter le dossier ; un dossier complet est donc l'état **normal**. Quand ce n'est pas le
   cas, **l'utilisateur veut le savoir** : l'incomplétude s'affiche comme une **alerte**, en tête,
   qui nomme ce qui manque et **pourquoi le système n'a pas pu l'obtenir** (recherche épuisée,
   source indisponible, question sans source possible) — jamais comme un simple compteur parmi
   d'autres. Ensuite viennent la note de qualité de chaque méthodologie, puis leurs conclusions.

---

## Arbitrages de l'utilisateur qui commandent la suite

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

## Ce qui reste ouvert — hors lot 6

**Dettes à décider (chacune est un lot en soi, à arbitrer en termes métier)**
- ⚠️ **Confusion d'émetteur dans le plan `defendabilite` RVMD** (plan 103, 2026-09-25) : mo_1/mo_5
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
2. Ce fichier, puis **`roadmap/V3/03-spec-frameworks.md`** (§1 ce qui n'est PAS défait · §8 le
   parcours, cœur du lot 6 · §10 les lots).
3. **`CLAUDE.md` du projet** — conventions **#25 → #82** ; pour le lot 6 : #53/#54 (recalcul à la
   lecture), #76/#77 (manager, mandat), #82 (`qualite_info`), et `feedback_controle_au_point_de_lecture`.
4. `roadmap/V3/principe-directeur.md` (constitution) · `doctrine-trois-axes.md` (close) ·
   `benchmark-methodologies.md` (matière des frameworks) · `METHODE-TEST.md` (choix de la méthode
   de test) · `ARCHITECTURE-CIBLE.md` + un `ARCHITECTURE.md` par module (cible ; le réalisé = les
   checks) · `provenance-cards/` (contrats figés, maquette niveau 3).
5. Code du flux : `backend/app/agents/v2/` (`traducteur`, `collecte_executor`, `apparieur`,
   `dossier`, `analyste`, `manager`, `manager_persist`, `bouclage`, `projection_memo`,
   `qualite_info`) · `backend/app/contracts/` · `backend/checks/README.md`.
6. `00-REPRISE-ARCHIVE.md` si le *pourquoi* d'une décision manque.

---

## À coller pour reprendre

> Reprise de **portfolio-tracker V3**. Lis d'abord `roadmap/V3/PRINCIPES-FONDATEURS.md` (arbitrages
> en termes métier ; chaque décision éclairée par la pratique d'un vrai fonds), puis
> `roadmap/V3/00-REPRISE.md`. Roadmap active : `roadmap/V3/03-spec-frameworks.md`. Lots 0 à 5 clos ;
> **lot 6 (le parcours du comité) en cours** : `qualite_info` (#82) et les 3 niveaux de
> drill-down (#83, migration 047) livrés et déployés ; reste acquitter/renvoyer tracés (A7,
> migration 048). Ordre imposé contrat → agent → données. Re-requêter toute ligne de base avant
> de s'en servir.
