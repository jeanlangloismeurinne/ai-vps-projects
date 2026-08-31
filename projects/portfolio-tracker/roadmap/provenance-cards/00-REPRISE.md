---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-08-31
project: portfolio-tracker
role: Prompt à coller pour reprendre le chantier V2. Contrat FIGÉ · couche 2 DÉPLOYÉE · chaîne d'analyse VALIDÉE SUR DEUX ÉMETTEURS (NVDA, MSFT) · dettes A/B fermées · généralité #3 fermée · LOT 7 LIVRÉ (acte de décision, `theses_v2`, migration 030, dry-run réel MSFT). Reste : lot 8 (monitoring V2), lot 9 (sortie/débat), UX transverse, ingestion-agent.
---

# Prompt de reprise — portfolio-tracker V2 (cartes de provenance)

> **Ce fichier a été allégé le 2026-08-31.** Tout l'historique (journaux de sprint détaillés,
> diagnostics de bugs déjà réglés, décisions et leurs mesures) est conservé **intégralement** dans
> **`00-REPRISE-ARCHIVE.md`**, à côté. Les **conventions durables #22 à #32** vivent dans le
> **`CLAUDE.md` du projet** — c'est là qu'il faut les lire, pas ici.

> ## ⚡ MàJ 2026-08-31 (ter) — LOT 7 : l'acte de décision (`theses_v2`, migration 030)
>
> **Le flux V2 sait maintenant conclure.** Déploiement **#331** (`a128005`), un seul conteneur
> vérifié. Suite hors-ligne : **436 assertions / 0 échec** (382 avant, **+54** —
> `check_decision_validate.py`). Dry-run réel joué de bout en bout sur MSFT : **12 vérifications
> supplémentaires, 0 échec.**
>
> **Décision d'architecture (tranchée par l'utilisateur) : `theses_v2` + route `/v2/…`.** La carte
> figée `decision_validate_card.md` disait « `theses += colonnes` » et `POST /theses/{id}/validate` —
> elle **précède d'un jour** le principe de disjonction V1/V2. Deux raisons dirimantes : `theses` est
> le pivot V1 (scheduler, monitoring, débat), et la route **existe déjà** en V1
> (`api/thesis_v2.py:733`, où « v2 » désigne la 2ᵉ version du fichier V1). La carte est **amendée
> avec un bloc daté** ; **le contrat JSON lui-même (`ThesisValidation`, 17 garde-fous) est
> INCHANGÉ** — seuls le support de persistance et le chemin bougent.
>
> **Principe dégagé, plus général que ce lot — et c'est lui qu'il faut retenir :**
> **les JUGEMENTS sont disjoints, les FAITS DU MONDE sont partagés.** `theses` | `theses_v2` sont
> deux espaces de jugement séparés ; `tickers`, `portfolio_positions`, `cash_movements`,
> `calendar_events` décrivent le monde réel — dupliquer le portefeuille signifierait **deux soldes de
> trésorerie sur de l'argent réel**. D'où une colonne discriminante `thesis_v2_id` (sœur nullable de
> `thesis_id`) + CHECK d'exclusivité `thesis_id IS NULL OR thesis_v2_id IS NULL`.
>
> **⚠ Danger silencieux trouvé en le vérifiant, pas en le supposant.** J'avais écrit dans la
> migration que le scheduler V1 « filtre sur `thesis_id`, donc ignore nativement les lignes V2 ».
> **Faux.** Les 4 requêtes de `_daily_check_v1` font `LEFT JOIN theses … AND th.status='active'` —
> un LEFT JOIN **rend la ligne même sans thèse jointe**, et aucun garde `thesis_json IS NULL` en
> aval. Le routeur V1 aurait donc appelé l'**agent Dust V1 sur une thèse inexistante**, en silence et
> avec **dépense réelle**. Corrigé : `AND ce.thesis_v2_id IS NULL` sur les 4 requêtes. **Mesuré sur
> les vrais événements du dry-run : 2 lignes vues sans le filtre, 0 avec.**
>
> **G2 s'exerce structurellement, pas par convention.** `ValidateV2Body` n'expose QUE `risk_acks`,
> `pre_mortem_acked` et les faits d'exécution (titres, prix, date). `verdict`, `position_sizing_pct`,
> `conditions_entree`, `hypotheses`, `valuation_range`, `synthesis` sont **lus en base** — les
> accepter du client rendrait le contrat décoratif (il suffirait d'envoyer une synthèse complaisante).
> `risk_matrix_acked` est **dérivé** (la bijection des acquittements en tient lieu), jamais demandé.
> Un sizing autre que le recommandé ne se passe pas au validate : il se trace **en amont** dans la
> synthèse (`position_sizing.override_utilisateur`, A7). `check_decision_validate.py` **§8 inspecte
> `model_fields`** pour l'assurer — c'est la vérification la plus importante du fichier.
>
> **Atomicité réelle.** `get_db_session()` n'ouvre **aucune** transaction (il *acquiert* une
> connexion, chaque `execute` est en autocommit) : la validation V1, documentée « atomique »
> (convention #13), **ne l'est pas**. La V2 ouvre un `conn.transaction()` explicite, appels réseau
> (FX, calendrier) faits **avant** pour ne pas tenir de verrou pendant un aller-retour yfinance. V1
> délibérément non touchée (hors périmètre, risque de régression).
>
> **Dry-run réel MSFT (thèse V2 #4, synthèse #11, memo #4)** — refus d'abord, tous sans écriture :
> acquittement incomplet 3/4 → **400**, pré-mortem non acquitté → **400**, acquittement fantôme
> index 9 → **400**, thèse inexistante → **404**, et la thèse **toujours en `draft`** après les
> quatre. Puis validation : verdict `PROCEED_AVEC_CONDITIONS` et sizing **3,0 %** repris de
> l'analyse, fourchette **250 / 450 / 700 dérivée du memo** (`iv_range` + `dcf_scenarios.base`,
> jamais une moyenne inventée), 4 hypothèses figées, rejeu → **409**. Chemin réseau réellement
> exercé : FX **400 € → 464,79 $** et date de résultats **2026-10-28** obtenue de DataService.
>
> **⚠ Ligne de test conservée sur décision de l'utilisateur.** Le dry-run a créé de vraies lignes :
> `theses_v2` **#4**, `portfolio_positions` **#8** (1 MSFT), `cash_movements` **#9** (400 €),
> `calendar_events` **#65** (quarterly 2026-10-28) et **#66** (annual_review 2027-08-31). Elles sont
> **gardées** comme premier cas V2 de bout en bout. **Conséquence à connaître** : la page portefeuille
> V1 (`portfolio_v2.py:142`) lit **toutes** les positions ouvertes et **tous** les mouvements de cash,
> sans filtre de flux — MSFT y apparaît donc **deux fois** (position V1 #1 + position V2 #8) et le
> solde de trésorerie est **400 € plus bas**. Ce n'est pas un bug de la migration (le CHECK
> d'exclusivité est **par ligne**, pas par ticker, à dessein) mais **une question pour la passe UX** :
> filtrer sur `thesis_v2_id IS NULL` côté V1, ou afficher les deux avec un marqueur de flux.
>
> **Les événements de calendrier V2 sont posés mais PAS routés** — le scheduler V1 les exclut
> volontairement et le routeur V2 arrive au **lot 8**. C'est **annoncé** dans la réponse de l'API
> (champ `note`) pour ne pas se lire comme un bug. L'événement #65 tombe le **2026-10-28** : le lot 8
> aura un vrai événement à router.

> ## ⚡ MàJ 2026-08-31 (bis) — généralité #3 fermée + dispense NVDA retirée
>
> **Les deux premiers items du reste-à-faire sont clos.** Deux déploiements : **#329** (`1b8497f`,
> domaines IR) et **#330** (`90fc6d3`, dispense). Un seul conteneur vérifié après chacun. Suite
> hors-ligne : **382 assertions / 0 échec** (367 avant, +15).
>
> **Généralité #3 — domaines IR par émetteur.** `nvidia.com` était en dur dans
> `_REPUTABLE_SUFFIXES` (fait d'émetteur dans une constante globale, #31) et Microsoft n'avait rien.
> Effet réel, plus grave qu'annoncé : `microsoft.com/en-us/investor/…` sortait en
> `web_search_generic` **0.50**, donc **sous `reliability_min=0.60`** — l'entry était **rejetée**, pas
> seulement mal notée. Le champ paraissait infondable alors que la source était la meilleure possible.
> Cause : Microsoft publie son IR sur un **chemin**, pas un sous-domaine `ir.`.
> → `classify_source_type(url, ticker_id)` + `issuer_domains_for(ticker_id)` (défaut **vide**), à deux
> niveaux : domaine émetteur **+ chemin IR** → `company_ir_official` 0.90 ; domaine émetteur hors IR →
> `web_search_reputable` B. `_IR_HOST_PATTERN` reste **générique à dessein** (le restreindre ferait
> tomber `ir.<concurrent>.com` de 0.90 à 0.50 — un faux trou créé par le correctif, cf. #32).
> *Vérifié contre le vrai modèle* (dry-run MSFT) : `microsoft.com/en-us/investor/earnings/FY-2026-…`
> → **`company_ir_official`, tier A, 0.895**. Convention **#33** écrite dans le `CLAUDE.md`.
>
> **Le « 4 sites d'appel » redouté n'existait pas** : `build_tool_executors` recevait déjà `ticker_id`.
> Il est fermé dans `web_search`/`fetch_url` comme `query` et `log` — un fait du run, pas un argument
> du modèle (#28). `check_search_worker.py` **§2bis teste le CÂBLAGE** (backend bouchonné, on lit le
> `source_type_max` réellement annoncé) : une table juste ne sert à rien si le ticker n'arrive pas.
>
> **Piste morte, à ne pas re-tenter** : EDGAR `submissions` expose `website` et `investorWebsite`,
> **les deux vides** — vérifié sur NVDA, AAPL, MSFT, GOOGL, AMZN. Le registre est écrit à la main.
> ⚠️ **Ajouter l'entrée `_ISSUER_DOMAINS` en même temps que le ticker.**
>
> **Dispense NVDA `marche.croissance_marche_historique` — retirée.** Elle disait « aucune source
> accessible à un tier suffisant » : vrai de la **table de domaines**, pas du monde. Depuis #32 les
> cabinets sont `web_search_reputable` (plafond B) = exactement le plancher dégradé du champ ; les
> deux garde-fous se contredisaient. Retirée **sur preuve** : un mandat NVDA a rendu **3 entries
> tier B** (Omdia 0.630, IDC 0.605, TechInsights 0.602 → **117-119**), comme MSFT en avait 3
> (Synergy/Canalys, 109-111). *Vérifié contre le vrai modèle* — rapport **#27**, NVDA :
> **`ready`, 0 gap, 0 dérogation sur ce champ**, `marche` fondée par `{croissance: [117,118,119],
> structure_5forces: [21,22,30,56]}`. Une vraie fondation, pas un saut. Coût $0.0013.
> `business_model.recurrence_pct` **reste** dispensé (fait NVIDIA toujours vrai).
> Le retrait **resserre** le gate : `check_readiness_recompute.py` §10 vérifie qu'une entry **C+ ne
> fonde pas** le champ.
>
> **Le 3ᵉ ticker n'est plus bloqué.**

> ## ⚡ MàJ 2026-08-31 — sprint dettes B + A (un seul déploiement)
>
> **Les deux dettes sont fermées, vérifiées contre le vrai modèle.** Commit `4be04ed`,
> deployment **#328**, un seul conteneur backend. Suite hors-ligne : **367 assertions / 0 échec**
> (329 + 17 curator + **21 d'un check neuf**).
>
> **Dette B — unités de `assumptions`.** Les trois clés portent l'unité dans le nom
> (`croissance_revenue_pct`, `expansion_marge_fcf_pct`, `multiple_sortie`), dans le contrat figé
> **et** la copie runtime, avec la consigne explicite « 12 %/an s'écrit `12.0`, jamais `0.12` » dans
> les prompts bull/bear rafraîchis en DB. **Origine trouvée** : `roadmap/01-spec-v2-unifiee.md`
> l.373 juxtaposait, dans le même objet d'exemple, `croissance_implicite_prix_actuel_pct: 14` (en
> pourcent) et `croissance_revenue: 0.10` (en fraction) — le modèle recopiait fidèlement une spec
> incohérente. Exemple corrigé. **Pas de coercition ×100** délibérément : le nom + le prompt + le
> contrat strict suffisent, et un filet de plus serait un 2ᵉ risque de polarité (cf. `conviction ×10`).
> *Vérifié contre le modèle* (MSFT, memo #4) : bull `12.0` / bear `5.0` %/an, **même échelle** —
> là où le run précédent donnait `0.15` contre `8.0`, facteur ~53. `expansion_marge_fcf_pct` bear
> à `-8.0` (compression, négatif licite).
>
> **Dette A — narration du curator.** Traitée à **trois** niveaux, parce que la cause n'était pas
> celle décrite : l'exemple de `rationale` **du prompt lui-même** se terminait par « … →
> thin_qualitative ». *Le prompt enseignait le défaut du rapport #24.* (1) exemple corrigé,
> (2) garde-fou 7 interdisant de nommer un verdict + rappel de l'ordre des tiers
> (**A > A- > B+ > B > C+ > C**), (3) `constrain_rationale()` en Python : en-tête factuel dérivé des
> booléens recomputés, et toute phrase nommant un verdict **autre** que le recomputé est retirée,
> **le retrait étant déclaré** dans le texte (jamais de coupe muette).
> *Vérifié contre le modèle* — rapport **#26**, MSFT : verdict `ready`, en-tête
> `[Verdict recomputé : ready — bloc structuré fondé, bloc qualitatif-marché fondé ; 0 champ(s) non
> fondé(s). …]`, **aucune phrase à retirer** — le garde-fou de prompt a tenu en amont, le filet
> Python n'a servi à rien. C'est le résultat voulu.
>
> **Check neuf `check_analysis_contract.py` (21 assertions)** — celui qui manquait le jour où le
> reverse-DCF a été desserré à chaud : les anciens noms nus sont désormais **rejetés** (pas ignorés),
> `croissance_implicite_prix_actuel_pct` est requis, `Assumptions` est fermé (`extra='forbid'`), et
> §6 compare **contrat figé ↔ copie runtime** (règle #19) — l'absence du montage `/contract_frozen`
> est **annoncée**, jamais silencieuse.
>
> **Résidu observé, non bloquant** : le rationale #26 écrit encore « seule une synthèse agent (A-)
> existe, sans source primaire de tier B+ ou supérieur » — l'ordre des tiers reste mal lu par le
> modèle sur une phrase qui **ne nomme aucun verdict**, donc que `constrain_rationale` laisse passer.
> Le verdict, lui, est juste. À revoir si ça se répète : la contrainte porte sur les verdicts nommés,
> pas sur les comparaisons de tiers.
>
> **Ce fichier a été allégé le même jour** → `00-REPRISE-ARCHIVE.md` (821 lignes, rien de résumé).

## Où on en est (2026-08-31)

La chaîne complète a tourné **de bout en bout sur deux émetteurs**. Ce n'est plus un prototype :
c'est un système exercé, dont on connaît les modes de panne.

| | NVDA (cas-pilote) | MSFT (2ᵉ ticker, preuve de généralité) |
|---|---|---|
| Socle | **52 entries** (32 A / 15 B / 5 llm_memory) | **51 entries**, 19/19 champs MVDD fondés, 44 A / 9 B, **0 `llm_memory`**, ≈ $0,19 |
| Readiness | **`ready`, 0 gap** (rapport #27) — dispense `croissance_marche_historique` **retirée**, champ réellement fondé (117-119) | **`ready`, 0 dérogation**, 0 gap |
| Chaîne | research → bull/bear → réfutation → synthèse = **PROCEED_AVEC_CONDITIONS** | idem, ≈ $0,018 |
| Déterminisme | verdict stable à corpus figé (4 tirs) | couverture **strictement identique** sur 2 tirs |

- **Code déployé** : commit `a128005`, deployment **#331**, un seul conteneur backend vérifié.
- **Suite hors-ligne** : **436 assertions / 0 échec** sur 10 scripts (`backend/checks/`).
- **Migrations appliquées** jusqu'à **030** (theses_flow). Prochaine : **031** exit/calibration
  — à écrire **juste avant** son lot, jamais en avance (§18).
- **L'acte de décision est livré et exercé en réel** (lot 7) : la chaîne va désormais de la recherche
  jusqu'à l'entrée en position.

## Ce qui reste à faire — dans l'ordre

1. **Lot 8 — monitoring V2 (mode 6 + routeur)**. **C'est le prochain jalon.** Les événements posés
   par le lot 7 sont **planifiés mais non routés** : `calendar_events` #65 (2026-10-28) et #66
   (2027-08-31) attendent un routeur V2. Contexte largement partagé avec le lot 7 (même migration
   030, mêmes tables `theses_v2`/`hypotheses`).
2. **Lot 9 — sortie/calibration + débat conviction** (migration 031, nouvelles tables, autre agent) :
   périmètre quasi disjoint du lot 7-8 → **à faire dans une conversation neuve**.
3. **Passe UX transverse** (§16) : verdict dans le frontend, suivi des hypothèses H1-H5.
   ⚠️ **Y traiter le double comptage MSFT** signalé dans la MàJ (ter) — la page portefeuille V1
   ne filtre pas les positions du flux V2.
3. **`ingestion-agent`** (contrat C2, document → entries) : jamais construit, **non bloquant** tant
   que search-worker + `synthesis_feed` couvrent les champs requis.
4. **3ᵉ ticker** — plus aucun blocage technique. ⚠️ Penser à ajouter son entrée dans
   `websearch._ISSUER_DOMAINS` **en même temps que le ticker** (cf. convention #33) : sans elle, son
   IR sur chemin (à la Microsoft) retombe en `web_search_generic` 0.50, donc sous plancher.

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

- **`CLAUDE.md` du projet** — conventions **#22 à #33** (recherche knowledge, piège pgvector, le
  modèle ne qualifie pas sa source, un échec de recherche n'est pas un résultat vide, deux chemins de
  `fetch_url`, on ne tronque pas un document, provenance vérifiée, la couverture se lit dans un
  index, concept XBRL choisi par fraîcheur, pas de fait d'émetteur dans une constante globale,
  plancher inatteignable = champ infondable déguisé, **#33 domaines d'émetteur à deux niveaux —
  et on ne resserre pas la règle générique en ajoutant la spécifique**).
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
> Dettes A et B **fermées** le 2026-08-31 (déploiement #328). Le même jour : **généralité #3
> fermée** (domaines IR clefés par émetteur, convention #33 — MSFT IR vérifié à 0.895 tier A,
> déploiement #329) et **dispense NVDA `croissance_marche_historique` retirée sur preuve**
> (entries 117-119 tier B ; rapport #27 `ready`, 0 gap, déploiement #330). Tout est vérifié contre
> le vrai modèle. **Le 3ᵉ ticker n'est plus bloqué.**
> **Prochain jalon** : **agents 7-9** (décision/validate → sortie/calibration → débat conviction),
> avec les migrations **030** theses_flow / **031** exit-calibration écrites juste avant leur lot.
> LIRE D'ABORD : ce fichier, le `CLAUDE.md` du projet (conventions #22-**#33**),
> `00-REPRISE-ARCHIVE.md` si le *pourquoi* d'une décision manque.
