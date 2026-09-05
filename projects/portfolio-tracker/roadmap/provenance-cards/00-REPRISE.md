---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-09-05
project: portfolio-tracker
role: >
  Prompt à coller pour reprendre le chantier V2 (cartes de provenance). Contrat FIGÉ · couche 2
  DÉPLOYÉE · boucle V2 complète (décider → surveiller → sortir → apprendre, lots 7-9) · écrans
  UX-1/2/3 livrés · chaîne exercée sur NVDA, MSFT et RVMD. Le chantier courant est le **3ᵉ ticker
  RVMD**, qui sert de banc d'essai aux modes de panne du socle : 14 défauts trouvés et corrigés
  (F1→F14). État au 2026-09-05 : 1 337 assertions / 0 échec / 18 scripts, prochaine migration 034.
  Roadmap active : `roadmap/02-spec-autorite-vs-actualite.md` (autorité contre actualité).
---

# Prompt de reprise — portfolio-tracker V2 (cartes de provenance)

> **Ce fichier ne s'empile pas.** Le récit des sessions vit dans `00-REPRISE-ARCHIVE.md` (copie
> conforme, rien de résumé), les règles durables dans le `CLAUDE.md` du projet (conventions
> numérotées), les enseignements d'outillage transverses dans `../../../CHANTIER_OUTILLAGE_DEV.md`.
> Ici : **l'état atteint, ce qui reste, et les pièges à ne pas re-découvrir.** Protocole
> d'éviction : `CONTROL_SYSTEM.md` §5.

## 🎯 Roadmap active

**`roadmap/02-spec-autorite-vs-actualite.md`** (statut `figée`, ouverte le 2026-09-05) — révision du
modèle de fiabilité : **autorité contre actualité**. Six capacités dans un ordre imposé, capacité 0
en cours (co-écriture de la table de profils par champ). **Rien n'est implémenté tant que la
capacité 0 n'est pas close.**

Motif d'ouverture : sur RVMD, l'information la plus fraîche du corpus est la moins bien classée
(tier A moyen 0,931 sur des faits d'avant l'approbation FDA du 2026-08-26 · tier B+ 0,750 sur
l'information du jour), et le `readiness` prononce quand même `ready, 0 gap`. La roadmap
**absorbe** les points 1 et 2 de « Reste à faire » ci-dessous — ils y sont traités comme des
symptômes, pas comme des tâches indépendantes.

`roadmap/01-spec-v2-unifiee.md` §18 reste la roadmap de **référence** du projet (découpage en lots),
mais elle est terminée sur son périmètre courant ; la roadmap 02 est celle qui s'exécute.

## Où on en est (2026-09-05)

**Le système est exercé, pas prototypé.** La chaîne complète a tourné de bout en bout sur trois
émetteurs, et on connaît désormais ses modes de panne — c'est le principal actif du chantier.

| | NVDA (cas-pilote) | MSFT (généralité) | RVMD (banc d'essai) |
|---|---|---|---|
| Socle | 52 entries (32 A / 15 B) | 51 entries, 19/19 champs, 0 `llm_memory`, ≈ $0,19 | 27 actives (13 déterministes + 14 qualitatives) |
| Readiness | `ready`, 0 gap | `ready`, 0 dérogation | dimension `valorisation` fondée sur ses 3 champs |
| Chaîne | research → bull/bear → réfutation → synthèse = `PROCEED_AVEC_CONDITIONS` | idem, ≈ $0,018 | 7 mandats qualitatifs restants (~0,08 $) |

- **Suite hors-ligne : 1 337 assertions / 0 échec / 18 scripts** (`backend/checks/`, lancer avec
  l'env de `checks/README.md` **et** le montage `/contract_frozen` — sans lui, 4 scripts
  sous-comptent en sortant quand même à 0). Filtre : `/tmp/run_checks.sh` (une ligne par script).
- **Migrations appliquées jusqu'à 033. Prochaine : 034** — à écrire *juste avant* son lot, jamais
  en avance (§18 de la spec).
- **Déploiement : le chemin nominal est repassé** (`compose-deploy.sh`, un seul appel) après quatre
  sessions de refus du classifieur. Le repli en commandes séparées reste documenté au §12 de
  `CHANTIER_OUTILLAGE_DEV.md`, mais **re-tester le nominal en premier** à chaque session.

### RVMD — 14 défauts du socle, tous trouvés avant ou après dépense, jamais par le contrat

C'est le résultat le plus réutilisable du chantier : **onze défauts sur douze ont été trouvés à
coût de modèle nul**, en exécutant les producteurs déterministes et en **lisant leur sortie en
texte**. Aucun n'était visible dans un diff, et aucun n'a fait rougir un contrat Pydantic — leurs
nombres étaient justes, c'est le *fait énoncé* qui était faux.

| Vague | Défauts | Ce qu'ils ont coûté | Convention née |
|---|---|---|---|
| Socle EDGAR (F1→F6) | ancre de bilan, appariement des flux, tri des concepts XBRL… | 0 token | #42, #43 |
| Valorisation (F7→F9) | multiples à dénominateur négatif publiés tels quels | 0 token | #44 |
| Format (F10, F11) | montants écrasés à « 0,0 Md » ; un CA nul sauté par `if x:` | 0 token | #45, #46, #47 |
| Premier vrai modèle (F12, F13) | pas de date dans le message (le modèle datait le présent à sa coupure) ; drapeau calculé mais jamais persisté | ~0,0105 $/mandat | — |
| Péremption (F14) | `source_date` datée du flux sur un ratio de bilan | 0 token | **#48** |

### Livré cette session (2026-09-05) — le corpus a enfin une horloge

Deux commits, chemin nominal, sonde publique 200 : **`ae02af3`** (ancre matérielle + balayage) et
**`45379ee`** (F14). Aucune migration.

- **`knowledge/material_events.py` — la seconde horloge.** Les dépôts périodiques (10-K/10-Q) ne
  datent pas le monde ; un **8-K/6-K** le fait. Le search-worker reçoit désormais l'événement
  matériel le plus récent, et un avertissement explicite quand il est **postérieur** à l'ancre
  documentaire (« ce fait peut décrire un monde révolu SANS ÊTRE FAUX »).
- **`knowledge/staleness.py` — un RAPPORT, jamais un `superseded_by`.** Route
  `GET /tickers/{id}/knowledge/staleness`, **toujours 200**, `ecrit_en_base: false` (garde de check
  qui grep l'absence d'`UPDATE`/`INSERT`/`DELETE`). Sur RVMD : seuil **2026-08-27**, 27 actives →
  **24 suspectes / 2 postérieures / 1 non datée**, 7 champs touchés.
- **F14, trouvé par le balayage lui-même** dès sa première lecture en prod : l'entry #169 disait
  `fiscal_period='AU 2026-06-30'` et `source_date=2025-12-31` — **la même ligne se contredisait**.
  Corrigé par détenteur unique ; vérifié après déploiement par le comptage #43 (une seule ligne
  active par clef, #169 → #189 daté 2026-06-30, les ratios de flux inchangés à 2025-12-31).

⚠️ **Ce qui reste vrai et inconfortable** : le balayage *signale*, il ne *décide* pas. Les 24
entries suspectes de RVMD sont toujours actives, et la porte de complétude (#29) les compte comme
couvrantes. **Un corpus complet peut être périmé** — voir « Reste à faire » n°1.

## Ce qui reste à faire — dans l'ordre

⚠️ **Les points 1 et 2 sont désormais instruits par la roadmap 02** (voir en tête) : ce sont les
symptômes qui l'ont ouverte, et les traiter isolément recréerait le défaut. Ils restent listés ici
pour le contexte, pas comme des tâches à prendre telles quelles.

1. **Statuer sur les 24 entries suspectes de RVMD** (le balayage rend la liste, motivée et
   ordonnée). C'est un **jugement humain** par construction : décider qu'un fait est remplacé n'est
   pas automatisable sans donner à une heuristique de dates une voix sur ce que le corpus affirme
   (#29, `feedback_optional_schema_gate`). Point d'atterrissage : `superseded_by` écrit à la main.
   ⚠️ Quatre entries tier A affirment « aucun produit approuvé pour la vente commerciale » alors que
   **la FDA a approuvé RASONQUE le 2026-08-26** — aucune n'est fausse, toutes sont périmées.
2. **Brancher le balayage sur la porte de complétude** — arbitrage ouvert, à ne pas trancher seul :
   faut-il qu'un `readiness` compte comme *non couvert* un champ dont toutes les entries sont
   antérieures au dernier événement matériel ? Le risque symétrique est de bloquer un socle sain à
   chaque 8-K de routine (un item 9.01 « pièces jointes » n'a rien périmé).
3. **Les 7 mandats qualitatifs RVMD restants** (~0,08 $) — désormais sans risque connu : le worker
   porte la date du jour, l'ancre documentaire **et** l'ancre matérielle.
4. **`ingestion-agent`** (contrat C2, document → entries) : jamais construit, **non bloquant** tant
   que search-worker + `synthesis_feed` couvrent les champs requis.
5. **4ᵉ ticker** — aucun blocage technique. ⚠️ Ajouter son entrée dans `websearch._ISSUER_DOMAINS`
   **en même temps que le ticker** (#33) : sans elle, son IR retombe sous le plancher.

### Dettes techniques connues, assumées

- **`base_rate_ge` n'est pas câblé** dans `run_research` : `reverse_dcf.croissance_implicite_…` est
  toujours chiffré, mais son consommateur attend le `taux_base_pct` précis.
- **`BullCase.conviction ×10 si ≤1`** : coercition gardée comme filet, risque de polarité théorique
  sur le float `1.0`. Noté, pas corrigé.
- Le `tools_json` du `search-worker` en DB décrit encore `web_search` comme « SearXNG/API » :
  **cosmétique**, à corriger à la prochaine migration qui touche `agent_prompts`, pas avant.
- **`covers` multi-champs** : une entry qui couvre 3 champs les couvre *également*, alors qu'elle en
  fonde souvent un et effleure les deux autres. Limite de conception à arbitrer, pas à changer
  unilatéralement.
- **`uncovered_fields` dupliqué** entre deux calculs voisins (mineur, sans effet observé).

## Décisions structurantes (toujours actives)

- **Modèles** — métier ET ouvrier = `deepseek-ai/DeepSeek-V4-Flash-0731` (ctx 1M, $0.08 in /
  $0.18 out). Les ouvriers émettent du JSON → coût **dominé par l'output** ; le réflexe « petit
  modèle ouvrier » vient de la tarification Anthropic et **ne se transpose pas**.
- **Embeddings** — `BAAI/bge-m3` **1024d**. Corpus en **français** : `bge-base-en-v1.5` ratait les
  entrées EDGAR tier A (MRR 0.644 → **0.905**). **Ne pas « améliorer » en hybride** : la fusion RRF
  **dégrade** (0.905 → 0.655).
- **Web search** — **Exa**, débordement **Serper**. SearXNG écarté sur le **mode de panne** (captcha
  = résultats vides sans erreur), pas sur le coût. Changer de backend = une classe.
- **Contrainte VPS** (mesurée) : 3,8 Go RAM / ~2,1 Go de socle / **0 swap**, ~5 Go libres →
  pas de self-hosting gourmand. ⚠️ Vérifier le disque avant tout `docker pull` volumineux.

## Pièges à ne pas re-découvrir

- **DeepSeek + `response_format=json_object` est NON FIABLE** : collapse sur `{}` ou emballe la
  sortie. Tout passe par `run_json_agent(json_object=False)` + `extract_json`.
- **Contrats = pydantic v2** → tester dans le container backend, **pas** le python hôte (v1).
- **Migrations non auto-appliquées** : `docker cp` + `psql -f`. Le heredoc `psql << EOF` via
  `docker exec` échoue **silencieusement**.
- **asyncpg** : `$1`/`$2` (jamais `%s`) ; JSONB auto-décodé (jamais de `json.dumps` avant INSERT).
- **Déploiement** : rebuild, jamais restart. Le build part du **répertoire local** — un commit non
  poussé serait quand même déployé, donc prod et `origin/main` divergeraient en silence ; le script
  pousse d'abord, ne pas le court-circuiter. Pour portfolio, **2 conteneurs sur le domaine sont
  normaux** (backend `/api` + frontend catch-all) — exception codée en dur dans le script.
- **Règle #19** : tout changement de contrat = 3 points de synchro (prompt en DB · frontend ·
  import). Rafraîchir un prompt en DB ne demande **pas** de rebuild.
- **Un correctif de prompt ou de schéma n'est pas acquis tant qu'il n'a pas tourné contre le vrai
  modèle.** Un desserrage fait à chaud (`Optional`, `extra=ignore`) est un trou silencieux :
  durcir le prompt d'abord, re-tester, **PUIS** re-serrer.
- **Un écran ne se vérifie pas par un 200** : Next.js sert la coquille et charge côté client. La
  méthode UX-2/UX-3 reste la référence — capturer les payloads **réels** avant d'écrire du JSX (un
  nom de champ faux n'affiche pas une erreur, il affiche **du vide**), `docker build` comme seule
  vérification frontend (`node --check` est un no-op sur ESM), puis **capture headless regardée**.
- **Méthode, éprouvée 14 fois** : exécuter les producteurs déterministes et **lire leur sortie en
  texte** avant toute dépense de modèle ; après un déploiement qui remplace une vérité, ne pas
  demander « la nouvelle valeur est-elle bonne ? » mais **« combien de lignes sont actives sur
  cette clef ? »** (#43) ; un check neuf n'est livrable qu'après avoir viré au rouge **pour la
  bonne raison** (les trois faux verts : fixture non discriminante, script mort avant ses asserts,
  assert à côté du point de lecture — `CHANTIER_OUTILLAGE_DEV.md` §24).

## À lire avant de reprendre

- **`CLAUDE.md` du projet** — conventions **#22 à #49**. Les plus structurantes du chantier
  courant : #29 (la couverture se lit dans un index), #42/#43 (datation et identité d'un fait),
  #44 (calculé / non calculable / absent), #46 (détenteur unique d'une règle), #47 (un zéro est une
  valeur), **#48** (la colonne `source_date` est un porteur de la date), **#49** (la péremption est
  une seconde horloge, et elle produit un rapport).
- **Specs** : `roadmap/00-principe-directeur-v2.md` · `roadmap/01-spec-v2-unifiee.md`
  (§5 agents, §7 curator/readiness, §8 contrats, §14 migrations, §16 UX, §18 découpage).
- **Cartes de contrat** : `roadmap/provenance-cards/*_card.md` + `*_schema.py` + `prompts/`.
- **Code** : `backend/app/agents/v2/` (`worker.py` · `curator.py` · `analysis.py` · `runner.py`) ·
  `backend/app/knowledge/` (`service.py` · `websearch.py` · `edgar_feed.py` · `synthesis_feed.py` ·
  `financials_feed.py` · `valuation_feed.py` · `units.py` · **`material_events.py`** ·
  **`staleness.py`**) · `backend/app/contracts/` · `backend/checks/README.md`.
- **Historique complet** : `00-REPRISE-ARCHIVE.md`. **Outillage transverse** :
  `../../../CHANTIER_OUTILLAGE_DEV.md` (§16 délégation, §24 tests négatifs, §25 porteurs d'un fait).
- **Visuel** : https://provenance.jlmvpscode.duckdns.org

## À coller pour reprendre

> Reprise de **portfolio-tracker V2** (chantier cartes de provenance).
> Contrat figé, boucle V2 complète (décider → surveiller → sortir → apprendre), écrans livrés,
> chaîne exercée sur **NVDA, MSFT et RVMD**. Principe directeur UX → agents → données, 3 garde-fous :
> G1 schéma versionné = source unique · G2 décision contrainte par l'analyse · G3 donnée versionnée
> + scorée + figée, jamais de texte libre. DÉCISION #1 = Option C (base neutre → bull/bear isolés →
> réfutation bear→bull → synthèse).
> Le chantier courant est le **3ᵉ ticker RVMD**, banc d'essai des modes de panne du socle :
> **14 défauts (F1→F14)** trouvés et corrigés, onze à coût de modèle nul en lisant les sorties en
> texte. Le corpus a désormais **une horloge** (ancre d'événements matériels 8-K/6-K + balayage de
> péremption qui rend un rapport, jamais un `superseded_by`).
> **Roadmap active** : `roadmap/02-spec-autorite-vs-actualite.md` (figée le 2026-09-05) — *autorité
> contre actualité*. Le corpus classe son information la plus fraîche au plus bas et prononce quand
> même `ready` : un scalaire unique porte deux propriétés orthogonales et les confond. La révision
> les sépare en **trois axes jamais recombinés** (fiabilité *stockée* · actualité *calculée à la
> lecture* · nature *stockée*), et le standing devient une propriété du **couple (source × nature)**.
> **Prochain jalon = capacité 0** : la table de profils des 19 champs MVDD, à **co-écrire** —
> aucun code avant qu'elle soit close.
> LIRE D'ABORD : ce fichier, le `CLAUDE.md` du projet (conventions #22-**#49**),
> `00-REPRISE-ARCHIVE.md` si le *pourquoi* d'une décision manque.
