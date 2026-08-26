---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-08-25
project: portfolio-tracker
role: Prompt à coller pour reprendre le chantier V2 (couche contrat FIGÉE + couche 2 code DÉPLOYÉE + chaîne d'alimentation EXERCÉE en réel + dimension `valorisation` FONDÉE de bout en bout + dimension `financials` — ratios dérivés — CODE DÉPLOYÉ & vérifié contre l'API EDGAR, mais PAS encore persisté en prod → reste : persister financials + recompute readiness, fermer les dimensions qualitatives pour `ready`, puis lancer la chaîne d'analyse jamais exécutée).
---

> ## ⚡ MàJ 2026-08-26 — `financials` FONDÉE EN PROD (tier A, 4 champs) après correction d'un bug d'intégration ; bloc structuré COMPLET, verdict `thin_qualitative`
>
> **Le persist prod de `financials` a révélé que le chemin réel n'avait JAMAIS fonctionné** — et
> l'a corrigé. Déployé (commit `82208e5`, deployment **#296**, un seul conteneur backend vérifié
> `docker ps`, pas d'orphelin). **Aucune migration.**
>
> ### 🐛 Bug d'intégration trouvé au premier persist réel (le piège « vérifié ≠ vérifié sur le chemin réel »)
> Le dry-run prod rendait `capex_source: "cik_introuvable"` → `fcf_conversion_pct` et
> `intensite_capex_pct` restaient non fondés (seuls `levier`/`roic_pct`, purement en base, sortaient).
> **Cause racine** : `knowledge/service.py::get_current_entries()` **ne sélectionnait pas `source_url`**
> dans son SELECT. Or `financials_feed` dérive le CIK EDGAR du motif `/data/<cik>/` de l'URL d'un fait
> en base (aucune table de correspondance). Sans `source_url`, `cik_from_url()` renvoyait
> **toujours** `None` → capex jamais fetché. **Preuve en base** : les entries dérivées `financials`
> #40→#47 étaient **4 rounds de persist antérieurs** n'ayant jamais écrit que `levier`+`roic`, avec une
> `source_url` **vide** — signature exacte du bug. **Pourquoi la MàJ ter a cru que ça marchait** : la
> « vérification contre l'API EDGAR » testait `fetch_annual_value(1045810, …)` avec le CIK **en dur**,
> et `check_financials_feed.py` (32/32) construit ses entries **avec** `source_url` (asserte même
> `facts["source_url"] == URL`) — le check masquait le trou d'intégration. **Fix** : ajout de
> `source_url` au SELECT de `get_current_entries` (corrige d'un coup la dérivation du CIK **et** la
> provenance des entries dérivées, jusque-là vide). Leçon renforcée : un feed n'est acquis que quand
> son **chemin d'IO réel** a tourné en prod, pas seulement ses fonctions pures + un fetch à CIK codé.
>
> ### Persisté + vérifié en réel (2026-08-26)
> `financials-refresh` (persist, refresh) → `capex_source: edgar_fetched`, **`unfounded=[]`** : capex
> fait EDGAR #48 (réutilisable, tier A) + `levier` #49 (gearing 4,75 %, trésorerie nette positive),
> `roic_pct` #50 (77,89 %), `fcf_conversion_pct` #51 (80,52 %), `intensite_capex_pct` #52 (2,8 %).
> `POST /curator/readiness` NVDA (report #7) → **`financials` : ok=True (A)**, **bloc structuré
> `bloc_ok=true`** (business_model B+, financials A, valorisation B+). 41 entries (30 A / 6 B / 5 llm_memory).
>
> ### Verdict `thin_qualitative` — il ne reste que 2 champs qualitatifs pour `ready`
> Le bloc structuré, bloqueur historique, est **entièrement fondé**. Gaps restants (bloc qual. marché) :
>
> | dimension | ok | manque |
> |---|---|---|
> | produits | ❌ | `unit_economics` (économie unitaire : coût/GPU, coût/token — **entrée de synthèse**, pas fetch brut) |
> | marche | ❌ | `structure_5forces` (analyse Porter **structurée** — synthèse) |
> | positionnement, management_allocation, risques | ✅ | — |
>
> **Search-worker testé sur `produits.unit_economics` (2026-08-26, dry-run, `field_path` ciblé,
> `max_iterations=8`) → `not_found`, 0 entrée.** Confirme empiriquement que ces 2 champs ne sont PAS
> fondables par fetch : l'économie unitaire (ASP/coût par GPU, coût/token) n'est ni dans un dépôt EDGAR
> (NVDA ne publie pas de volumes unitaires — l'ASP n'est pas calculable des faits disclosés, contrairement
> aux ratios `financials`) ni lisible en fetch depuis le VPS (notes d'analystes paywallées, 403). Le KB a
> déjà les matériaux tier A (entries #32-35 marges/coûts consolidés pour unit_economics ; #21,22,28-31
> menace ASIC / concentration clients / AMD-Huawei / TSMC / export controls pour les 5 forces) — mais
> **aucune entrée ne les SYNTHÉTISE** au niveau que le curator exige.
>
> ### ⛔ Frontière de capacité — le prochain sprint = construire l'INGESTION-AGENT (synthèse grounded, contrat C2)
> Asymétrie clé : la **chaîne d'analyse** (research/bull/bear) est gated par `ready`, mais la **synthèse
> d'alimentation du KB** ne l'est PAS. L'outil manquant est donc l'`ingestion-agent` (étape 4 du plan,
> jamais construit), pas la chaîne. Design proposé, même patron que `valuation_feed`/`financials_feed`
> (transform testable + IO) mais LLM-composé et **grounded** : (1) charger les entries tier A/B+ citables
> pour le champ visé ; (2) un tour LLM (DeepInfra) compose la synthèse **strictement** à partir de ces
> entries, chaque assertion → `source_entry_id` (aucun fait hors-KB) ; (3) persister une entry
> `entry_type='synthesis'` avec `field_path`, `content_structured.cited_entry_ids`, tier dérivé (synthèse
> de tier A ⇒ A-/B+ selon règle), `requires_human_review=True` au départ. **NE PAS** injecter d'entrée
> non fondée pour forcer `ready` (violerait G3/#24/#25/#28 — le cœur du projet). Une fois les 2 champs
> fondés → readiness → `ready` → **lancer la CHAÎNE D'ANALYSE jamais exécutée** (research → bull/bear →
> réfutation → synthèse + `valider_pont`).
>
> ## ⚡ MàJ 2026-08-25 (ter) — dimension `financials` : alimentateur de ratios dérivés DÉPLOYÉ + vérifié contre l'API EDGAR (⚠ pas encore persisté en prod)
>
> **Déployé** (commit `9c0a818`, deployment **#295**, un seul conteneur backend vérifié `docker ps`
> — pas d'orphelin). **Aucune migration.** Même patron que `valuation_feed`/`base_rate_corpus` :
> transformation pure testable + couche IO.
>
> - **`backend/app/knowledge/financials_feed.py`** : fonde les 4 champs de `financials` —
>   `roic_pct`, `fcf_conversion_pct`, `intensite_capex_pct`, `levier`. Ce ne sont PAS des mesures mais
>   des **ratios**, donc **calculés** depuis les postes comptables. Point clé de conception : le
>   plancher de `financials` est **tier A** → un ratio issu du quant (yfinance/FMP, **B+**) ne
>   fonderait PAS le champ. On calcule donc **uniquement** à partir des `fact_financial` **EDGAR** déjà
>   en base (tier A) : un ratio dérivé de faits tier A seuls est lui-même tier A → `source_type='edgar_official'`.
>   `build_financials_entries()` (pur) ne produit une entry QUE si tous les intrants existent ; sinon le
>   champ est reporté dans `unfounded` (jamais un chiffre fabriqué, #25). `levier` = gearing dette/CP +
>   dette nette (dette nette/EBITDA **négatif** car trésorerie nette positive → le gearing est la lecture
>   pertinente, noté). `roic_pct` : NOPAT **≈ résultat net** (charge d'intérêts nette négligeable en
>   trésorerie nette), approximation **déclarée dans le content** (peut légèrement majorer).
> - **`backend/app/knowledge/edgar_facts.py`** : le seul poste absent du seed est le **capex**
>   (nécessaire à `fcf_conversion_pct` = FCF/RN avec FCF=OCF−capex, et `intensite_capex_pct` =
>   capex/CA). Il n'est ni fabriqué ni emprunté au quant : **mesuré à la source** via l'API XBRL
>   `companyconcept` d'EDGAR. **CIK dérivé de l'URL EDGAR déjà en base** (`/data/<cik>/`) — aucune table
>   de correspondance. Échec EDGAR → `EdgarUnavailable`, les 2 champs restent non fondés (#25).
> - **Route** `POST /tickers/{id}/knowledge/financials-refresh` (`persist`/`refresh`,
>   `FinancialsUnavailable`→422). **Check** `backend/checks/check_financials_feed.py` **32/32** hors-ligne.
>
> ### ⚠️ Gotcha capex — tag XBRL NVDA (vérifié contre l'API EDGAR réelle 2026-08-25)
> NVDA déclare le capex récent sous **`us-gaap:PaymentsToAcquireProductiveAssets`**, PAS sous le
> `PaymentsToAcquirePropertyPlantAndEquipment` classique (qui **s'arrête à 2012** pour NVDA — 200 mais
> données périmées). La liste `_CAPEX_TAGS` gère le **fallthrough** : le 1er tag ne matche aucun
> exercice près de la date de bilan visée → `EdgarUnavailable` → 2e tag retenu. **À garder à l'esprit
> pour d'autres tickers : le concept capex varie d'un émetteur à l'autre.**
>
> ### Vérifié CONTRE L'API EDGAR (transform pur + fetch), pas seulement hors-ligne
> Fetch réel `companyconcept` CIK 1045810 → **capex FY2026 = 6,042 Md$** (end 2026-01-25, via le 2e tag).
> Ratios calculés sur les vrais chiffres NVDA FY2026 : **`roic_pct` 77,9 %** · **`fcf_conversion_pct`
> 80,5 %** · **`intensite_capex_pct` 2,8 %** · **`levier` gearing 4,75 %** (trésorerie nette positive)
> → **0 champ non fondé**. Exactement ce qu'il faut pour que `financials.ok=True` (tier A).
>
> ### ⛔ CE QUI RESTE À FAIRE (non fait — la fondation n'est PAS encore en base)
> Le run **en prod** (persist + recompute readiness) a été **bloqué par le garde-fou de permission**
> puis reporté par l'utilisateur. Donc, contrairement aux sprints 1+2, **les entries `financials` NE
> SONT PAS écrites dans la KB NVDA et la readiness N'A PAS été recomputée**. Reste à faire, en 1er, à
> la reprise :
> 1. `POST /tickers/NVDA/knowledge/financials-refresh` (`persist:true`) — écrit le capex EDGAR (fait
>    tier A réutilisable) + les 4 ratios (supersede par tags). Vérifier `capex_source='edgar_fetched'`,
>    `unfounded=[]`, `docker ps` = 1 conteneur.
> 2. `POST /curator/readiness` NVDA — confirmer **`financials` : ok=True (A)** et le nouveau verdict
>    (attendu : bloc structuré désormais complet ; reste le bloc qualitatif → toujours `not_ready`).
>
> Après ça, gaps restants = **qualitatif** (`business_model`, `produits`, `positionnement`, `marche`)
> via le search-worker taggé `field_path` — étape 2 ci-dessous inchangée.
>
> ## ⚡ MàJ 2026-08-25 (bis) — dimension `valorisation` FONDÉE de bout en bout (sprints 1+2 déployés + vérifiés en réel)
>
> **Déployé** (commit `8fecdd5`, deployment **#294**, un seul conteneur backend vérifié). Deux
> alimentateurs déterministes, sur le modèle du search-worker (transformation pure testable + IO),
> **aucune migration** (`entry_type` est du texte libre, colonne `tags` existante) :
>
> - **Sprint 1 — `backend/app/knowledge/valuation_feed.py`** : fonde `valorisation.prix_actuel` et
>   `valorisation.relatif_multiple` depuis le quant (DataService → yfinance `.info`, `source_type='yfinance'`
>   tier **B+ 0.75** = pile le plancher). Append-only avec supersede (le prix est volatil). Route
>   `POST /tickers/{id}/knowledge/valuation-refresh` (`persist`/`refresh`, `ValuationUnavailable`→422).
>   Ticker sans symbole (privé/`PUB-`) → refus explicite, jamais une entrée vide (#25).
> - **Sprint 2 — `backend/app/knowledge/base_rate_corpus.py`** : fonde `valorisation.base_rate_anchor`
>   — qui **n'est PAS une donnée de marché** mais une **ancre de taux de base** (outside view). Une base
>   rate ne se *génère* pas au LLM (le groundedness-checker la flaggerait `base_rate_fabrique`), elle se
>   *mesure* : corpus transverse (`ticker_id IS NULL`, `entry_type='base_rate'`) **seedé depuis les
>   chiffres réels de l'Exhibit 2 du Base Rate Book** (Mauboussin/CS-HOLT 1950-2015, distribution des CAGR
>   de ventes 1/3/5/10 ans, n=53 266) + **classifieur déterministe** (taille en CA, maille du livre) +
>   **entry par-ticker** qui cite le corpus. Route `POST /tickers/{id}/knowledge/base-rate-anchor`.
>   ⚠️ Les chiffres EXACTS ne couvrent que l'univers complet ; pour une méga-cap le `taux_base_pct` est
>   marqué **borne haute** (Exhibit 4 : la persistance chute avec la taille), jamais une distribution
>   méga-cap inventée.
> - **Checks hors-ligne** (`backend/checks/check_valuation_feed.py` 20/20 · `check_base_rate_corpus.py`
>   27/27, dont l'arithmétique confrontée au livre : P(≥20 %/an sur 3 ans)=11,9 %, colonnes=100 %).
>
> **Exercé EN RÉEL sur NVDA (2026-08-25)** — vraies données yfinance servies malgré le 429 (cache
> DataService) : prix `212,39 $`, P/E TTM `32,5×`, EV/EBITDA `30,2×` → entries #36/#37 (B+) ;
> ancre méga-cap → corpus #38 + entry #39 (B+, P(≥20 %/an, 5 ans)=`8,5 %`, médiane `5,2 %`, borne haute).
> **`POST /curator/readiness` NVDA → `valorisation` : `ok=True` (B+), `champs_non_fondables=[]`.**
> La valorisation, bloqueur structurel de la MàJ précédente, **n'est plus le problème**.
>
> ### Verdict toujours `not_ready` — mais les gaps ont bougé aux AUTRES dimensions
> Couverture readiness NVDA au 2026-08-25 (36 entries : 25 A / 6 B / 5 llm_memory) :
>
> | bloc | dimension | ok | manque |
> |---|---|---|---|
> | structurée | **valorisation** | ✅ | — (fondée sprints 1+2) |
> | structurée | management_allocation, risques | ✅ | — |
> | structurée | `financials` | ❌ | `roic_pct`, `fcf_conversion_pct`, `intensite_capex_pct` (**ratios dérivés** — calculables du quant/EDGAR, comme la valo ; PAS du web) |
> | structurée | `business_model` | ❌ | `description`, `drivers_revenus`, `recurrence_pct` (qualitatif) |
> | qual. marché | `produits` | ❌ | `description`, `unit_economics` |
> | qual. marché | `positionnement` | ❌ | `moat_preuves`, `position_vs_pairs` |
> | qual. marché | `marche` | ❌ | `croissance_marche_historique`, `structure_5forces` |
>
> ### Prochaines étapes concrètes (dans l'ordre pour amener NVDA à `ready`)
> 1. **`financials` — ratios dérivés** (`roic_pct`, `fcf_conversion_pct`, `intensite_capex_pct`, `levier`) :
>    même patron que `valuation_feed` — un alimentateur déterministe qui **calcule** ces ratios depuis les
>    `fact_financial` EDGAR déjà en KB + le quant. C'est le gap structuré le plus proche, non web.
> 2. **`business_model` + qualitatif (`produits`/`positionnement`/`marche`)** : via le **search-worker**
>    (déjà exercé) en **taguant `field_path`** sur les entries pour fiabiliser le jugement par champ,
>    + entrées de **synthèse** pour `unit_economics` / `structure_5forces` (analyses, pas fetch brut).
> 3. Readiness → `ready` → **lancer la CHAÎNE D'ANALYSE** (`research` → `bull`/`bear` → réfutation →
>    `synthesis` + `valider_pont`). **Jamais exécutée à ce jour** — c'est le vrai prochain jalon une fois
>    `ready` atteint. À l'analyse, `run_research` lira `reverse_dcf.croissance_implicite_prix_actuel_pct`
>    et appellera `base_rate_corpus.base_rate_ge(seuil, horizon)` pour finaliser le `taux_base_pct` précis.
>
> **Permission** : `Bash(infrastructure/deploy.sh:*)` ajoutée dans `.claude/settings.json` (racine repo).

> ## ⚡ MàJ 2026-08-25 — premier run end-to-end réel du search-worker (le gros « jamais vérifié » est levé)
>
> **Le lot « recherche intra-document + provenance vérifiée » (commit `6ef4fa4`, deploy #283) est en
> prod et VÉRIFIÉ de bout en bout.** Checks : `check_provenance.py` **42/42** hors-ligne +
> `check_fetch_relevance.py` **2/2** live (10-K NVDA `22%`/`14%` atteints à 37,6 % du texte, `via=direct
> mode=relevance` ; CNBC `Maia` via cache Exa, `mode=whole`). La troncature est réglée contre les vraies API.
>
> **Bug infra corrigé le même jour** : le rebuild #283 n'avait PAS arrêté le conteneur #282 (`cc665e9`) —
> les DEUX portaient des labels Traefik identiques, donc Traefik load-balançait `/api` sur l'ancien ET le
> nouveau code pendant ~40 h (+ double scheduler). Orphelin stoppé+supprimé, `/api/health`→200 sur un seul
> backend. **Réflexe à garder : après tout `deploy.sh`, `docker ps | grep <app>` ne doit montrer QU'UN conteneur.**
>
> **La boucle tool-calling `run_tool_json_agent()` a enfin tourné contre DeepSeek en réel** (elle ne
> l'avait jamais fait — cf. l'ancienne section « jamais vérifié »). 7 runs `search-worker` sur NVDA,
> **~$0.10 au total**, cadence ~90–175 s/run. Résultats (provenance RÉELLEMENT vérifiée — plus aucune
> URL sec.gov fantôme comme au run C) :
>
> | dimension | entries persistées | tier | source | plancher | couvre ? |
> |---|---|---|---|---|---|
> | produits | 2 + 4 | A 0.89 / A 0.93 | IR press (cache Exa) + 10-Q MD&A | B+ | champ `unit_economics` jugé non fondé |
> | positionnement | 1 | B+ 0.735 | CNBC (cache Exa) | B+ | ✅ |
> | marche | 1 | B+ 0.73 | CNBC | B+ | champ `structure_5forces` non fondé |
> | management_allocation | 5 | A 0.92–0.944 | EDGAR DEF 14A (sec.gov réel) | A- | ✅ |
> | risques | 4 | A 0.94 | EDGAR 10-K (sec.gov réel) | B | ✅ |
>
> KB NVDA passée de **15 → 32 entries** (25 tier A, 2 tier B, 5 llm_memory). `POST /curator/readiness`
> tourne et rend un rapport cohérent. **Verdict : `not_ready`** (recomputé 3×, déterministe à données
> fixes : runs #2/#3 identiques au champ près).
>
> ### Pourquoi NVDA n'est PAS `ready` — et pourquoi le search-worker seul ne l'y amènera jamais
> Les 5 gaps restants sont **structurels**, pas un manque de recherche :
> - **`valorisation` (bloc structuré, bloquant)** : `prix_actuel` (prix marché live), `relatif_multiple`
>   (P/E, EV/EBITDA), `base_rate_anchor` (multiple historique secteur) — **aucun ne vient du web** ;
>   ils viennent du **quant/DataService (FMP)**. La recherche ne peut pas les fonder.
> - **`produits/unit_economics`** : marges consolidées (GM 73,4 %, op. margin) ajoutées via 10-Q, mais
>   le curator veut l'économie **unitaire** (coût/GPU, coût/token) → besoin d'une entrée de synthèse.
> - **`marche/structure_5forces`** : besoin d'une analyse Porter **structurée**, pas d'un fetch brut.
>
> ⚠️ **Finding sur la stabilité du curator** : le verdict a basculé `thin_qualitative` (#1, 28 entries)
> → `not_ready` (#2, 32 entries) en n'AJOUTANT que des entries `produits`. Mécanisme : la note de
> fondation **par champ** est produite par le modèle (le backend ne recompute en Python que le `ok`
> = tier_atteint≥plancher ∧ champs_requis fondés). Avec plus de contexte, le modèle a **corrigé** son
> sur-crédit de `valorisation` (#1 la disait fondée B+, à tort, car aucune entry ne porte prix/multiple).
> Donc `not_ready` est le verdict JUSTE et `thin_qualitative` était un faux positif. À retenir : la
> readiness n'est fiable que si chaque champ est réellement porté par une entry — ne pas se fier à un
> `thin_qualitative`/`ready` limite sans vérifier les `gaps`. Le curator charge jusqu'à 500 entries
> (`limit=500`), donc pas de plafond qui écrase — c'est bien le jugement par champ qui bouge.
>
> ### Prochaine étape concrète pour rendre NVDA `ready`
> 1. **Fonder `valorisation`** : écrire un petit alimentateur `fact_financial` depuis DataService/FMP
>    (`prix_actuel`, `relatif_multiple` P/E-EV/EBITDA, `base_rate_anchor` = multiple médian historique
>    semi-conducteurs) → entries tier A/B+ portant `valorisation.*`. C'est le vrai chaînon manquant.
> 2. **`produits/unit_economics` et `marche/structure_5forces`** : entrées de **synthèse** (ingestion/
>    curation), pas du fetch brut. Piste : le `search-worker` ne tague pas `field_path` sur ses entries
>    (constaté : `field=None`), le curator infère la fondation depuis le `content` — taguer `field_path`
>    fiabiliserait le jugement par champ.
> 3. Readiness → `ready` → alors seulement lancer research → bull/bear → réfutation → synthèse
>    (`POST /tickers/NVDA/research` puis `/analyses` …). **Cette chaîne d'analyse n'a toujours jamais
>    tourné** — c'est le prochain vrai jalon une fois `ready` atteint.

# Prompt de reprise — portfolio-tracker V2 (post-déploiement couche 2)

**État au 2026-08-23** : la **couche contrat est figée** (10 schémas Pydantic v2) ET la **chaîne
d'analyse runtime est écrite et déployée en production** (provider DeepInfra + curator → research →
bull/bear → réfutation → synthèse). Migrations 024/025/026/**027** appliquées.
La **recherche sémantique est opérationnelle** (bge-m3 1024d, 15/15 entrées embeddées) et le
**`search-worker` est écrit** (recherche web + fetch + entries scorées, 9 routes au total).
**Ce qui manque n'est plus du code : c'est une clé et un run.** Aucun ticker n'est encore `ready`,
donc la chaîne n'a jamais tourné de bout en bout sur un cas réel — et le seul obstacle restant est
la souscription **Exa**, sans laquelle le worker refuse (volontairement) de démarrer.

> ### ⚠️ État du déploiement — un lot committé localement, NON poussé
>
> Lot embeddings **déployé en production le 2026-08-23** (commit `f1e6a94`, deployment Coolify
> #280). Vérifié dans le container live : `EMBEDDING_MODEL=BAAI/bge-m3`, 15/15 entrées embeddées,
> `query_knowledge` renvoie `match_mode='vector'`, backfill à 0 candidat. Migration 027 appliquée.
>
> **Lot `search-worker` déployé le 2026-08-23** avec `EXA_API_KEY` posée dans Coolify (backend),
> deployment #281. Chaîne vérifiée de bout en bout : Exa répond, la boucle d'outils tourne, les
> garde-fous déterministes filtrent.
>
> **Premier run réel (NVDA, `moat`, dry-run) : `not_found` — 5 entrées produites, 5 rejetées sous le
> plancher `reliability_min=0.60`.** Diagnostic : les seules pages lisibles depuis le VPS étaient des
> blogs (`web_search_generic` = 0.50, donc structurellement sous le plancher) ; les sources
> qualifiantes étaient inaccessibles — CNBC 403 (WAF), `investor.nvidia.com` SPA vide. Corrigé par le
> second chemin de `fetch_url` (repli Exa `/contents`, convention #26). Coût du run : 99 278 tok in /
> 3 999 out = 0,0087 $, sorti sur « 6 itérations d'outils épuisées » (d'où `max_iterations` exposé
> dans le body de `POST /tickers/{id}/knowledge/search`).

Colle ceci pour reprendre :

> Reprise de **portfolio-tracker V2**. Couche contrat figée + chaîne d'analyse runtime déployée en
> prod (provider DeepInfra OpenAI-compat, modèle unifié `deepseek-ai/DeepSeek-V4-Flash-0731`).
> Principe directeur UX → agents → données, 3 garde-fous (G1 schéma versionné = source unique /
> G2 décision contrainte par l'analyse / G3 donnée versionnée+scorée+figée, jamais de texte libre).
> DÉCISION #1 = Option C (base neutre → bull/bear isolés → réfutation bear→bull → synthèse).
> **Le blocage actuel est l'alimentation de la base de connaissance**, pas la chaîne.
>
> **Étapes 1 (embeddings) et 2 (`search-worker`) FAITES.** L'étape 2 est écrite et vérifiée hors
> ligne (40 assertions, `backend/checks/`), mais **jamais exercée contre un vrai modèle** :
> il manque la clé.
> **Prochaine étape = souscrire Exa** (exa.ai, 10 $/mois de crédits renouvelables, sans carte),
> poser `EXA_API_KEY` dans Coolify, pousser + rebuild, puis faire le **premier run réel** :
> `POST /tickers/NVDA/knowledge/search` en `persist=false` d'abord, puis relancer la readiness
> jusqu'à faire passer NVDA de `thin_qualitative` à `ready`.
>
> LIRE AVANT : `roadmap/00-principe-directeur-v2.md` ; `roadmap/01-spec-v2-unifiee.md` (§5 agents,
> §7 curator/readiness, §8 contrats analyse, §14 migrations, §18 découpage) ;
> `roadmap/provenance-cards/*_card.md` + `*_schema.py` ; `roadmap/provenance-cards/prompts/` ;
> côté **code** : `backend/app/agents/providers/`, `backend/app/agents/v2/`,
> `backend/app/knowledge/` (`service.py` · `embeddings.py` · `websearch.py`),
> `backend/app/contracts/`, `backend/app/api/analysis_v2.py` + `knowledge_v2.py`,
> `backend/checks/README.md`.
> CLAUDE.md projet = conventions (dont #22 recherche knowledge, #23 piège pgvector,
> **#24 le modèle ne qualifie pas sa source**, **#25 un échec de recherche n'est pas un résultat vide**).
> Visuel : https://provenance.jlmvpscode.duckdns.org

## Ce qui est FAIT

### Couche contrat — 10 schémas Pydantic v2 (`SCHEMA_VERSION=v2.0.0`)

- **Analyse** `analysis_v2_schemas.py` : `ResearchMemo` (NEUTRE, Q2) · `BullCase`/`BearCase` (A6) ·
  `RiskMatrix` (seul verdict) · `Hypothese` (falsifiabilité). + `readiness_report_schema.py` (gate
  GO/NO-GO, `compute_verdict`, `thin_qualitative`).
- **C1** `worker_delegation_schema.py` · **C2** `ingestion_extraction_schema.py` ·
  **C3** `context_pack_schema.py` · **C4** `decision_validate_schema.py` ·
  **C5** `monitoring_mode6_schema.py` · **C6** `exit_calibration_schema.py` ·
  **C7** `debate_conviction_schema.py` · **C8** `monitoring_modes_1_5_schema.py`.

Chaque contrat a sa carte `*_card.md`. Dérivés : `readiness_derivation.md`, `groundedness_rules.md`.

### Prompts d'agent V2 (`prompts/`)

`00-preambule-commun.md` + 11 prompts (`10-ingestion` → `80-postmortem`). Ce sont le **3ᵉ point de
synchro** (règle #19) : schéma de sortie = Pydantic correspondant. Chargés en DB par la migration 025.

### Couche 2 — code runtime (écrit, déployé 2026-08-23)

| Module | Rôle |
|---|---|
| `backend/app/agents/providers/` | `AgentProvider` · `DeepInfraProvider` (OpenAI-compat) · `DustProvider` (shim V1) · factory `get_agent_provider(agent_name, flow_version)` lisant `agent_prompts` |
| `backend/app/contracts/` | **copie runtime** des contrats figés (le build context Docker est `./backend` seul → `roadmap/` absent de l'image). + `composites.py` (`SynthesisOutput` + `valider_pont()` §8.5) |
| `backend/app/knowledge/service.py` | `RELIABILITY_TABLE` · `compute_reliability()` · `store_knowledge()` (append-only A1, **embedde à l'écriture**, échec non fatal) · `query_knowledge()` (**vectoriel + repli strict**) · `snapshot_refs()` (gel entry@version + `reliability_at_use`) · `collect_refs()` |
| `backend/app/knowledge/embeddings.py` | **(2026-08-23)** client DeepInfra `/v1/openai/embeddings` · `entry_text()` = **source unique** du texte embeddé (backfill et écriture temps réel DOIVENT produire le même texte) · `to_pgvector()` (littéral casté `$n::vector`, pas de dépendance `pgvector` Python) · `backfill_embeddings()` idempotent · `_QUERY_INSTRUCTION` (bge-m3 n'en veut **pas** ; bge-*-en et e5 si) |
| `backend/app/agents/v2/runner.py` | point de passage unique : `extract_json()` tolérant, `run_json_agent()` (validation Pydantic + **1 tour de réparation**), `run_tool_agent()` (boucle outils brute) et **`run_tool_json_agent()`** = boucle d'outils + **tour de clôture JSON validé**, joué par un clone de l'agent **sans `tools`** (tant que `tools` est exposé, un modèle peut répondre par un tool_call de plus au lieu du contrat : ni sortie, ni erreur claire) |
| `backend/app/knowledge/websearch.py` | **(2026-08-23)** `SearchBackend` interchangeable (`ExaBackend` nominal · `SerperBackend` débordement) · `web_search()` · `fetch_url()` (httpx + extraction texte **stdlib `html.parser`**, aucune dépendance ajoutée) · `classify_source_type()` = qualification de source **par le domaine** |
| `backend/app/agents/v2/tools.py` | **(2026-08-23)** exécuteurs des 3 outils du `tools_json` (migration 025) : `web_search`, `fetch_url`, `query_knowledge`. Arguments du modèle traités comme entrées non fiables (`max_results` borné, `ticker_id` forcé au mandat) ; un échec est une **valeur de retour** `{"error": …}`, pas une exception |
| `backend/app/agents/v2/worker.py` | **(2026-08-23)** `search-worker` (contrat C1) : `run_search_worker()` → `WorkerExchange` validé, `persist_worker_entries()` (append-only A1). `_apply_deterministic_overrides()` recalcule source_type/score/tier/note/covers/status/exécution — cf. conventions #24 et #25 |
| `backend/app/api/knowledge_v2.py` | **(2026-08-23)** `POST /tickers/{id}/knowledge/search` (avec `persist=false` = dry-run, la base étant append-only) · `GET /knowledge/search/status` (diagnostic : la recherche est-elle réellement câblée ?). `SearchUnavailable` → **503**, distinct d'une recherche infructueuse (200 + `status='not_found'`) |
| `backend/checks/` | **(2026-08-23)** vérifications exécutables en container jetable : `check_search_worker.py` (40 assertions, hors ligne) · `check_fetch_live.py` (réseau, sans clé) |
| `backend/app/agents/v2/common.py` | `MVDD_SPEC` (8 dimensions, champs requis + tier plancher) · `count_tiers()` · `format_entries_for_prompt()` (ordre déterministe = discipline de cache §5.3) |
| `backend/app/agents/v2/curator.py` | gate GO/NO-GO. **Tout ce qui est dérivé est recalculé en Python** (`_apply_deterministic_overrides`) : `entries_par_tier`, `ok` par dimension, `bloc_ok`, verdict. `conviction`/`marge_securite` forcés à `None` (A3). Produit le `context_pack` **uniquement si `ready`** |
| `backend/app/agents/v2/analysis.py` | `run_research` · `run_bull`/`run_bear` (contextes isolés) · `run_rebuttal` (round 2 supersede round 1) · `run_synthesis`. `_load_ready_context()` lève `NotReadyError` si pas de readiness `ready` |
| `backend/app/api/analysis_v2.py` | 7 routes (§15). `NotReadyError`→409 · `AgentNotFoundError`→404 · reste→502 |

### Socle données — migrations appliquées

- **024** Knowledge Platform : `knowledge_documents`, `knowledge_entries` (append-only A1),
  `analysis_knowledge_refs`, `eu_ir_scrapers`, `knowledge_curator_reports`, pgvector + HNSW
  `vector(768)`, vue `knowledge_federation_export`.
- **025** Agents/Provider : `agent_prompts += provider, model, tools_json, flow_version` ;
  unicité `(agent_name, flow_version)` ; **12 agents V2** insérés. Générateur `_gen_025.py`.
- **026** Analyses : `research_memos`, `research_messages`, `investment_analyses`.
  ⚠️ **`analysis_knowledge_refs.analysis_id` est POLYMORPHE** (discriminé par `analysis_kind`) — la
  note de 024 « FK ajoutée en 026 » est **amendée** : pas de FK dure vers `investment_analyses` seul.
- **027** Embeddings : `embedding vector(768)` → **`vector(1024)`** + index HNSW reconstruit
  (`vector_cosine_ops`, donc opérateur `<=>` inchangé) + index **partiel** `..._unembedded` sur
  `embedding IS NULL` (la passe de rattrapage de `query_knowledge` doit rester bon marché).
  ⚠️ **Piège pgvector** : `atttypmod` porte la dimension **telle quelle**, sans le `+4` (VARHDRSZ)
  des types natifs. Un `atttypmod - 4` réflexe lit 1020 pour un `vector(1024)` — la garde
  d'idempotence ne reconnaît pas l'état cible et la migration rejouée **efface tout le corpus
  d'embeddings**. Constaté en test. La garde compare désormais `format_type(...)`.
- **Séquence** : collision 023 → décalage +1, puis 027 pris par les embeddings →
  reste **028 theses_flow · 029 exit/calibration**.

Seed NVDA (`backend/app/db/seeds/nvda_v2_knowledge_seed.sql`) : 10 `fact_financial` Tier A EDGAR
+ 5 qualitatifs `llm_memory` → readiness **`thin_qualitative`** (struct_ok ∧ ¬qual_ok).

### Infra / secrets

- `DEEPINFRA_API_KEY` déployée dans **Coolify** (app `portfolio-backend` id=8, env 123 prod + 124
  preview, chiffrée Laravel, round-trip vérifié). Jamais committée.
- Risques DeepInfra **levés** par test API réel : model_id valide · JSON strict propre · tool-calling
  OpenAI conforme (`finish_reason=tool_calls`).

## Décisions arrêtées

### Modèles (2026-08-21)

**Métier ET ouvrier = `deepseek-ai/DeepSeek-V4-Flash-0731`** (13B/284B, ctx 1M, $0.08 in / $0.18 out).
Les ouvriers émettent du JSON → coût **dominé par l'output**, et DeepSeek V4 Flash a l'output le moins
cher du catalogue. Le réflexe « petit modèle ouvrier » vient de la tarification Anthropic (Haiku≪Opus)
et **ne se transpose pas**. Le « tier ouvrier » reste une **réalité d'orchestration** (délégation,
`execution.tier`, batch), pas un modèle distinct.

Overrides possibles (`agent_prompts.model` est par agent) : ingestion de masse EDGAR →
`google/gemma-4-26B-A4B-it` ($0.07/$0.34, 256k) ; fallback tool-calling → `zai-org/GLM-4.7-Flash`.

### Embeddings — DÉCISION #4, 3ᵉ révision (2026-08-23) : `BAAI/bge-m3`, 1024d — **FAIT ET VALIDÉ**

**Ollama abandonné** (~1 Go de RAM sur un VPS 2 vCPU saturé) → API DeepInfra, clé déjà déployée.
Coût : corpus pilote ≈ **$0,00004**, < **$0,10/an** à pleine échelle. Le coût n'arbitre rien.

⚠️ **`bge-base-en-v1.5` (768d) a été essayé puis ÉCARTÉ** : ce modèle est entraîné sur l'**anglais
seul**, or **100 % du corpus est en français** (`lang='fr'` sur 15/15 entrées, et les sources EU le
resteront). Bench sur le corpus NVDA réel (7 requêtes FR sémantiques, 15 entrées) :

| configuration | MRR | hit@1 | hit@3 |
|---|---|---|---|
| ILIKE lexical seul (l'ex-implémentation) | 0.352 | 1/7 | 3/7 |
| bge-base-en-v1.5 768d, vectoriel | 0.644 | 4/7 | 4/7 |
| **bge-m3 1024d, vectoriel** | **0.905** | **6/7** | **7/7** |

Le 768d anglais échouait précisément sur les requêtes **financières** (rentabilité, cash,
endettement) — donc sur les entrées **EDGAR Tier A**, les plus fiables : rangs 5, 6, 7 sur 15.
Mode de panne **silencieux** : l'agent reçoit des entrées pleines mais hors-sujet, le curator conclut
à une dimension non couverte (readiness faux négatif) et le garde-fou A2 ne voit rien puisque les
refs citées existent. Aucun modèle multilingue en 768d chez DeepInfra (404 sur
`multilingual-e5-base`, `gte-multilingual-base`) → la montée en dimension n'était pas évitable.

**Ne PAS « améliorer » en recherche hybride sans re-mesurer** : la fusion RRF du lexical et du
vectoriel **dégrade** (0.905 → 0.655), le signal lexical français étant trop faible. Le texte est un
**repli strict**, jamais un co-classement. La normalisation des accents ne change rien.

### Web search (2026-08-23) — Exa, SearXNG écarté

⚠️ **Brave a supprimé son palier gratuit en février 2026** — toute note antérieure citant
« Brave 2000 req/mois gratuit » est **périmée**.

**Choix : Exa** ($10/mois de crédits renouvelables sans carte ≈ 4 000 recherches). Débordement payant :
**Serper** (~$1/1000, $50 = 50 000 requêtes ≈ 25 mois). Tavily en option si on veut le contenu extrait
plutôt que des liens (économise des `fetch_url`).

**SearXNG écarté sur la performance, pas sur le coût** : latence médiane ~0,83 s (dont 0,74–0,89 s
d'agrégation multi-moteurs) contre ~180–450 ms pour Exa ; et surtout, **depuis une IP unique la
plupart des moteurs captcha** (Google 0 résultat parsable, Brave/Startpage suspendus, seul DuckDuckGo
répond). Pour le `search-worker` c'est le pire mode de panne possible : **des résultats vides sans
erreur explicite**, exactement ce que le garde-fou A2 (groundedness) est censé empêcher.

**Point rassurant, désormais vérifié dans le code** : `knowledge/websearch.py` isole le backend
derrière `SearchBackend` — basculer Exa ↔ Serper ↔ autre = **une classe**, sans toucher au
`tools_json` en DB, au prompt du worker, ni à la boucle tool-calling. `SEARCH_PROVIDER` choisit.

⚠️ Le `tools_json` du `search-worker` en DB décrit encore `web_search` comme « recherche web
(SearXNG/API) ». C'est **cosmétique** (la description est agnostique côté modèle) mais périmé — à
corriger à la prochaine migration qui touche `agent_prompts`, pas avant (§18 : pas de migration en
avance).

## Contrainte infra VPS (mesurée 2026-08-23)

`3 819 Mo RAM totale / ~2 100 Mo de socle permanent / 0 swap` · disque `38 G, 84% utilisé, 5,8 G
libres` · **2 vCPU**. ~5,2 Go récupérables (images Docker obsolètes 4,2 Go + journald 0,8 Go + divers)
mais **non nettoyés** — les images obsolètes sont les rollbacks Docker locaux.

Conséquence : **pas de self-hosting de service supplémentaire gourmand**. C'est ce qui fonde les deux
décisions ci-dessus (embeddings API, web search API).

## Prochaine étape — alimenter la connaissance (le blocage réel)

1. ~~**Embeddings**~~ — ✅ **FAIT le 2026-08-23** (non déployé, voir « État du déploiement » ci-dessous).
   `backend/app/knowledge/embeddings.py` (client DeepInfra `/v1/openai/embeddings`, `bge-m3`) ·
   migration 027 · 15/15 entrées NVDA backfillées en 1024d · `query_knowledge()` bascule sur
   `embedding <=> $vec::vector` avec repli texte strict. Mesuré en conditions réelles à travers
   l'index HNSW : **MRR 0.905, hit@3 7/7**.
2. ~~**`search-worker`**~~ — ✅ **FAIT + EXERCÉ EN RÉEL le 2026-08-25** (Exa déployée, 7 runs NVDA,
   provenance vérifiée sur sources réelles EDGAR/IR). Voir MàJ 2026-08-25 en tête.
3. ~~**Fonder `valorisation` depuis le quant (DataService/FMP)**~~ — ✅ **FAIT + VÉRIFIÉ EN RÉEL le
   2026-08-25** (sprints 1+2, deployment #294). `prix_actuel`/`relatif_multiple` via `valuation_feed.py`
   (yfinance, B+) ; `base_rate_anchor` via `base_rate_corpus.py` (corpus Base Rate Book + classifieur
   par taille). `valorisation` → `ok=True` en readiness NVDA. Voir MàJ 2026-08-25 (bis) en tête.
3bis. **Fonder `financials` (ratios dérivés)** — ⏳ **CODE DÉPLOYÉ le 2026-08-25 (deployment #295,
   commit `9c0a818`) + vérifié contre l'API EDGAR, mais PAS encore persisté en prod.** `financials_feed.py`
   calcule `roic_pct`/`fcf_conversion_pct`/`intensite_capex_pct`/`levier` depuis les faits EDGAR tier A
   (le quant B+ est volontairement écarté : plancher A), capex fetché à la source (`edgar_facts.py`).
   **Reste à lancer en prod** : `financials-refresh` (persist) + recompute readiness — cf. MàJ (ter) en
   tête. Puis le qualitatif.
4. **`ingestion-agent`** — doc → entries (contrat C2), anti-hallucination financière.
5. **Premier run end-to-end de la CHAÎNE D'ANALYSE** : une fois NVDA `ready`,
   research → bull/bear → réfutation → synthèse (+ `valider_pont`). **Jamais fait à ce jour** — la
   partie alimentation (readiness) est désormais exercée, l'analyse reste à lancer.
5. Agents 7→9 (migrations 027/028) : décision/validate → monitoring m6 → sortie/calibration.
6. Passe UX transverse finale (§16).

**Piège migrations (§18)** : écrire chaque migration **juste avant** son lot, jamais en avance.

## Ce qui n'a JAMAIS été vérifié (à ne pas supposer acquis)

- ~~**La boucle tool-calling n'a jamais tourné contre un modèle.**~~ ✅ **LEVÉ le 2026-08-25** :
  `run_tool_json_agent()` a bouclé contre DeepSeek sur 7 runs `search-worker` NVDA — tour de clôture
  sans `tools`, réparation JSON et respect du contrat `WorkerResponse` observés en réel ; la
  combinaison `tools` + `response_format` (via le clone sans outils) fonctionne. `search-worker`,
  `persist_worker_entries`, `_apply_deterministic_overrides` (worker) et le curator (`run_readiness`,
  `_apply_deterministic_overrides`, readiness → rapport `not_ready` cohérent) sont exercés contre un
  vrai modèle. Voir la MàJ 2026-08-25 en tête.
- **La chaîne d'ANALYSE, elle, n'a toujours jamais tourné.** `run_research`, `run_bull`/`run_bear`,
  `run_rebuttal`, `run_synthesis` et surtout `valider_pont()` (§8.5) n'ont jamais vu de sortie de
  modèle réelle : aucun ticker n'a encore atteint `ready`, et `_load_ready_context()` lève
  `NotReadyError` tant que la readiness n'est pas `ready`. Bloqué en amont par la fondation de
  `valorisation` (feed quant, cf. MàJ 2026-08-25), pas par la chaîne elle-même.
- La validation faite : `py_compile` + import complet en container jetable + round-trip
  `ReadinessReport` sous pydantic 2.13.4 → `thin_qualitative` cohérent avec `compute_verdict`.

**Exception — les garde-fous déterministes du search-worker SONT vérifiés** (`backend/checks/`,
40 assertions en container, 0 échec) : sortie de modèle hostile (source surqualifiée, score gonflé,
mauvais `entry_type`, doublons, dépassement de `max_entries`, `llm_memory` non déclarée) intégralement
rabattue ; troncature Pareto sur les mieux notées ; `not_found` explicite quand tout est écarté (A6) ;
`WorkerExchange` valide après correction. Et `fetch_url` est exercé sur des URL réelles.

⚠️ **Trouvé en exerçant `fetch_url`** : `investor.nvidia.com` renvoie **HTTP 200, un `<title>` correct
et 0 caractère de texte** — la page est rendue en JavaScript. Rendre ce vide comme un succès aurait
fait conclure au modèle que la page ne dit rien. `fetch_url` lève désormais une erreur explicite
(page volumineuse → < 200 car. extraits). **Conséquence pour l'ingestion** : beaucoup de pages IR
seront inaccessibles sans rendu JS ; privilégier communiqués, EDGAR, et le `text` que **Exa** rapporte
directement (il évite en plus un tour de `fetch_url`).

**Exception — le lot embeddings (027), lui, EST vérifié en conditions réelles** : backfill 15/15,
recherche vectorielle exercée à travers l'index HNSW via `query_knowledge` (MRR 0.905, hit@3 7/7),
rattrapage d'une entrée non embeddée, repli texte clé absente, idempotence du backfill et de la
migration. Reste non exercé : le comportement sous un corpus de plusieurs milliers d'entrées
(qualité du rappel HNSW, `ef_search` laissé au défaut).

## Rappels techniques (CLAUDE.md projet)

- Contrats ciblent **pydantic v2** → tester dans le container backend, **pas** le python hôte (v1).
  Astuce sans secret : `docker run --rm --network none -v <backend>:/app:ro -w /app <image> python -c "import app.main"`
  (nécessite des valeurs factices pour les 8 env vars requis par `Settings`).
- asyncpg `$1` (pas `%s`) ; JSONB auto-décodé (pas de `json.dumps`) ; migrations **appliquées
  manuellement** via `docker cp` + `psql -f` (heredoc `docker exec` échoue **silencieusement**).
- Déploiement : `infrastructure/deploy.sh <app> -m … -f …` (cf. DEPLOY.md). Rebuild, jamais restart ;
  commit+push AVANT. Coolify build **depuis GitHub** → un commit local non poussé n'est jamais déployé.
- Règle #19 : tout changement de contrat = 3 points de synchro (prompt agent · frontend · import).
- Viz servie par un container nginx **hors Coolify** (`provenance-viz`, bind-mount) ; éditer le HTML
  suffit (live).
