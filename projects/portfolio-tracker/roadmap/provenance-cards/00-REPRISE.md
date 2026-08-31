---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-08-31
project: portfolio-tracker
role: Prompt à coller pour reprendre le chantier V2. Contrat FIGÉ · couche 2 DÉPLOYÉE · chaîne d'analyse VALIDÉE SUR DEUX ÉMETTEURS (NVDA, MSFT). Reste : dettes A/B, généralité #3, agents 7-9, UX transverse.
---

# Prompt de reprise — portfolio-tracker V2 (cartes de provenance)

> **Ce fichier a été allégé le 2026-08-31.** Tout l'historique (journaux de sprint détaillés,
> diagnostics de bugs déjà réglés, décisions et leurs mesures) est conservé **intégralement** dans
> **`00-REPRISE-ARCHIVE.md`**, à côté. Les **conventions durables #22 à #32** vivent dans le
> **`CLAUDE.md` du projet** — c'est là qu'il faut les lire, pas ici.

## Où on en est (2026-08-31)

La chaîne complète a tourné **de bout en bout sur deux émetteurs**. Ce n'est plus un prototype :
c'est un système exercé, dont on connaît les modes de panne.

| | NVDA (cas-pilote) | MSFT (2ᵉ ticker, preuve de généralité) |
|---|---|---|
| Socle | 55+ entries | **51 entries**, 19/19 champs MVDD fondés, 44 A / 9 B, **0 `llm_memory`**, ≈ $0,19 |
| Readiness | `ready` — **1 dérogation** (`marche.croissance_marche_historique`) | **`ready`, 0 dérogation**, 0 gap |
| Chaîne | research → bull/bear → réfutation → synthèse = **PROCEED_AVEC_CONDITIONS** | idem, ≈ $0,018 |
| Déterminisme | verdict stable à corpus figé (4 tirs) | couverture **strictement identique** sur 2 tirs |

- **Code déployé** : commit `990c8f8`, deployment **#327**, un seul conteneur backend vérifié.
- **Suite hors-ligne** : **329 assertions / 0 échec** sur 8 scripts (`backend/checks/`).
- **Migrations appliquées** jusqu'à **029**. Prochaines : **030** theses_flow · **031** exit/calibration
  — à écrire **juste avant** leur lot, jamais en avance (§18).

## Ce qui reste à faire — dans l'ordre

1. **Dette B — unités de `assumptions`** (mécanique, ferme une bombe latente).
   Bull a produit `croissance_revenue: 0.15` (fraction) là où bear rendait `8.0` (pourcent) —
   facteur ~53 ; `expansion_marge_fcf` 0.0 vs -2.0. Déclarés `float` au contrat, **consommés nulle
   part en Python** aujourd'hui : donc aucun crash, et exactement le motif du `Optional` du
   reverse-DCF (cf. archive, MàJ ter). Le dépôt encode l'unité dans le nom partout (`_pct`) ; ces
   deux champs sont les seuls à l'omettre. → suffixe `_pct`, en respectant la **règle #19**.
2. **Dette A — le rationale du curator peut contredire son propre verdict.**
   Rapport #24 : verdict `ready`, mais le rationale écrit « … (tier A-), sous le plancher B+ requis
   → thin_qualitative ». Deux erreurs : l'ordre des tiers est **inversé** (A- 0.85 est *au-dessus*
   de B+ 0.75) et **un autre verdict est narré**. `_verdict_contraint` protège le GO/NO-GO, mais la
   narration n'est contrainte par rien — **et c'est elle que l'humain lit**. Le tir 2 a produit un
   rationale correct : la qualité du récit varie là où le verdict ne varie pas.
3. **Défaut de généralité #3 — les domaines IR d'émetteur sont en dur pour NVDA.**
   `nvidia.com` est dans `_REPUTABLE_SUFFIXES`, rien pour Microsoft :
   `microsoft.com/en-us/investor/…` est classé `web_search_generic` **0.50** au lieu de
   `company_ir_official` **0.90**. Impact mesuré **nul** sur le sprint MSFT (0 entry retenue depuis
   microsoft.com — le modèle a préféré sec.gov). Différé sciemment : le correctif propre demande de
   faire descendre `ticker_id` dans `classify_source_type()` (**4 sites d'appel**).
   ⚠️ **À faire avant le 3ᵉ ticker.**
4. **Re-run de contrôle NVDA**, puis **retrait de la dispense** `marche.croissance_marche_historique`
   — probablement obsolète depuis la convention #32 (les cabinets d'études sont désormais classés
   `web_search_reputable`, plafond B, donc le champ est fondable).
5. **Agents 7-9** : décision/validate (monitoring M6) → sortie/calibration → débat conviction.
   Migrations 030/031 écrites juste avant chaque lot.
6. **Passe UX transverse** (§16) : verdict dans le frontend, suivi des hypothèses H1-H5.
7. **`ingestion-agent`** (contrat C2, document → entries) : jamais construit, **non bloquant** tant
   que search-worker + `synthesis_feed` couvrent les champs requis.

### Dettes techniques connues, assumées

- **`base_rate_ge` n'est toujours pas câblé** dans `run_research` : `reverse_dcf.croissance_implicite_prix_actuel_pct`
  est désormais **toujours chiffré** (donc fiable pour ça), mais son consommateur attend le
  `taux_base_pct` précis.
- **`BullCase.conviction ×10 si ≤1`** : coercition gardée comme filet, avec un risque de polarité
  théorique sur le float `1.0`. Noté, pas corrigé.
- Le `tools_json` du `search-worker` en DB décrit encore `web_search` comme « SearXNG/API » :
  **cosmétique** (la description est agnostique côté modèle) mais périmé — à corriger à la prochaine
  migration qui touche `agent_prompts`, pas avant.

## Décisions structurantes (toujours actives)

- **Modèles** — métier ET ouvrier = `deepseek-ai/DeepSeek-V4-Flash-0731` (ctx 1M, $0.08 in / $0.18 out).
  Les ouvriers émettent du JSON → coût **dominé par l'output**. Le réflexe « petit modèle ouvrier »
  vient de la tarification Anthropic et **ne se transpose pas**. Overrides possibles par agent
  (`agent_prompts.model`).
- **Embeddings** — `BAAI/bge-m3` **1024d** via DeepInfra. Le corpus est en **français** :
  `bge-base-en-v1.5` (anglais) ratait précisément les entrées EDGAR tier A (MRR 0.644 → **0.905**,
  hit@3 4/7 → **7/7**). **Ne pas « améliorer » en hybride** : la fusion RRF **dégrade** (0.905 → 0.655).
- **Web search** — **Exa** ($10/mois de crédits renouvelables), débordement **Serper**. SearXNG écarté
  sur la **performance et le mode de panne** (captcha depuis une IP unique = résultats vides sans
  erreur), pas sur le coût. Basculer de backend = **une classe** dans `knowledge/websearch.py`.
- **Contrainte VPS** (mesurée) : 3,8 Go RAM / ~2,1 Go de socle / **0 swap**, 2 vCPU, ~5 Go libres.
  → **pas de self-hosting supplémentaire gourmand**. C'est ce qui fonde les deux décisions ci-dessus.
  ⚠️ Vérifier le disque avant tout `docker pull` volumineux.

## Pièges à ne pas re-découvrir

- **DeepSeek + `response_format=json_object` est NON FIABLE** : il collapse sur `{}` ou emballe la
  sortie dans un objet parasite. Tous les appels passent par `run_json_agent(json_object=False)` /
  prompt-only + `extract_json`. Vaut pour la chaîne d'analyse **et** le curator.
- **Contrats = pydantic v2** → tester dans le container backend, **pas** le python hôte (v1) :
  `docker run --rm --network none -v <backend>:/app:ro -w /app <image> python -c "import app.main"`
  (prévoir des valeurs factices pour les env vars requis par `Settings`).
- **Migrations non auto-appliquées** : `docker cp` + `psql -f`. Le heredoc `psql << EOF` via
  `docker exec` échoue **silencieusement** — pas d'erreur, pas de changement.
- **asyncpg** : `$1`/`$2` (jamais `%s`) ; JSONB auto-décodé (jamais de `json.dumps` avant INSERT).
- **Déploiement** : `infrastructure/deploy.sh <app> -m … -f …`. **Rebuild, jamais restart** ;
  commit + push **AVANT** (Coolify build depuis GitHub : un commit local non poussé n'est jamais
  déployé). Après chaque deploy, `docker ps | grep <app>` doit montrer **UN SEUL** conteneur —
  un orphelin fait load-balancer Traefik sur l'ancien code, silencieusement.
- **Règle #19** : tout changement de contrat = 3 points de synchro (prompt agent en DB · frontend ·
  import). Rafraîchir les prompts en DB ne demande **pas** de rebuild (`get_agent_provider` relit la
  DB à chaque appel) ; modèle de script : `db/migrations/_gen_prompt_refresh_20260830.py`.
- **Un correctif de prompt ou de schéma n'est pas acquis tant qu'il n'a pas tourné contre le vrai
  modèle.** Et un desserrage de schéma fait à chaud (`Optional`, `extra=ignore`) est un trou
  silencieux : durcir le prompt d'abord, re-tester, **PUIS** re-serrer le schéma.

## À lire avant de reprendre

- **`CLAUDE.md` du projet** — conventions **#22 à #32** (recherche knowledge, piège pgvector, le
  modèle ne qualifie pas sa source, un échec de recherche n'est pas un résultat vide, deux chemins de
  `fetch_url`, on ne tronque pas un document, provenance vérifiée, la couverture se lit dans un
  index, concept XBRL choisi par fraîcheur, pas de fait d'émetteur dans une constante globale,
  plancher inatteignable = champ infondable déguisé).
- **Specs** : `roadmap/00-principe-directeur-v2.md` · `roadmap/01-spec-v2-unifiee.md`
  (§5 agents, §7 curator/readiness, §8 contrats, §14 migrations, §16 UX, §18 découpage).
- **Cartes de contrat** : `roadmap/provenance-cards/*_card.md` + `*_schema.py` + `prompts/`.
- **Code** : `backend/app/agents/v2/` (`worker.py` · `curator.py` · `analysis.py` · `runner.py`) ·
  `backend/app/knowledge/` (`service.py` · `embeddings.py` · `websearch.py` · `edgar_feed.py` ·
  `synthesis_feed.py` · `financials_feed.py` · `valuation_feed.py`) · `backend/app/contracts/` ·
  `backend/app/api/{analysis_v2,knowledge_v2}.py` · `backend/checks/README.md`.
- **Historique complet** : `00-REPRISE-ARCHIVE.md`.
- **Visuel** : https://provenance.jlmvpscode.duckdns.org

## À coller pour reprendre

> Reprise de **portfolio-tracker V2** (chantier cartes de provenance).
> Contrat figé + chaîne d'analyse déployée et **exercée sur deux émetteurs** (NVDA, MSFT — les deux
> `ready`, les deux `PROCEED_AVEC_CONDITIONS`). Principe directeur UX → agents → données, 3
> garde-fous : G1 schéma versionné = source unique · G2 décision contrainte par l'analyse · G3 donnée
> versionnée + scorée + figée, jamais de texte libre. DÉCISION #1 = Option C (base neutre → bull/bear
> isolés → réfutation bear→bull → synthèse).
> **Prochain jalon** : dettes B (`assumptions` en `_pct`) puis A (narration du curator contrainte),
> puis la généralité #3 (domaines IR par émetteur) avant tout 3ᵉ ticker, puis agents 7-9.
> LIRE D'ABORD : ce fichier, le `CLAUDE.md` du projet (conventions #22-#32), `00-REPRISE-ARCHIVE.md`
> si le *pourquoi* d'une décision manque.
