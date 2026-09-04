# checks/ — vérifications exécutables des agents V2

Scripts autonomes, hors image de production (le build ne copie que `app/`). Ils tournent dans un
container jetable bâti sur l'image backend, seul endroit où pydantic est en **v2** (le python hôte
est en v1).

```bash
cd projects/portfolio-tracker/backend
# ⚠️ Le conteneur s'appelle `portfolio-backend` depuis la migration Coolify → compose du
# 2026-09-03 ; l'ancien `grep portfoliobackend` (nom généré par Coolify) ne matche plus rien et
# faisait échouer `docker inspect` avec « requires at least 1 argument ».
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')

# Les 7 variables factices exigées par `Settings` vivent désormais dans `checks/env.checks`
# (versionné, aucun secret). Elles ne sont plus recopiées à la main à chaque appel : la commande
# cessait d'être lisible et étalait des identifiants V1 dans des vérifications 100 % V2.
ENV="--env-file checks/env.checks"

# garde-fous déterministes du search-worker — hors ligne, aucun appel modèle
docker run --rm --network none -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app $ENV $IMG \
  python checks/check_search_worker.py

# fetch_url en conditions réelles — réseau ouvert, aucune clé requise
docker run --rm -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app $ENV $IMG \
  python checks/check_fetch_live.py

# provenance vérifiée + recherche intra-document — hors ligne, déterministe
docker run --rm --network none -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app $ENV $IMG \
  python checks/check_provenance.py

# socle EDGAR (sélection de concept XBRL par fraîcheur) — hors ligne
docker run --rm --network none -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app $ENV $IMG \
  python checks/check_edgar_feed.py

# ratios dérivés financials (arithmétique + fondation partielle honnête) — hors ligne
docker run --rm --network none -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app $ENV $IMG \
  python checks/check_financials_feed.py

# synthèse grounded (dérivation de tier + grounding vérifié) — hors ligne, aucun appel modèle
docker run --rm --network none -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app $ENV $IMG \
  python checks/check_synthesis_feed.py

# curator : couverture recomputée depuis l'index `covers` — hors ligne, aucun appel modèle
docker run --rm --network none -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app $ENV $IMG \
  python checks/check_readiness_recompute.py

# contrat d'analyse (bull/bear) : unités dans le nom, champs requis, extra='forbid' — hors ligne.
# Le montage /contract_frozen active EN PLUS la comparaison contrat figé <-> copie runtime (#19) ;
# sans lui le check tourne quand même, en ANNONÇANT que la comparaison n'a pas eu lieu.
docker run --rm --network none -v "$PWD:/app:ro" \
  -v "$PWD/../roadmap/provenance-cards:/contract_frozen:ro" \
  -w /app -e PYTHONPATH=/app $ENV $IMG \
  python checks/check_analysis_contract.py

# acte de décision V2 (§9, lot 7) : les 17 garde-fous du contrat ThesisValidation + G2 STRUCTUREL.
# Même montage /contract_frozen que ci-dessus (règle #19). Hors ligne, aucun appel modèle.
docker run --rm --network none -v "$PWD:/app:ro" \
  -v "$PWD/../roadmap/provenance-cards:/contract_frozen:ro" \
  -w /app -e PYTHONPATH=/app $ENV $IMG \
  python checks/check_decision_validate.py

# monitoring V2 (§10-§11, lot 8) : le PONT inter-objets, que le contrat ne peut pas porter.
# Même montage /contract_frozen (règle #19). Hors ligne, aucun appel modèle.
docker run --rm --network none -v "$PWD:/app:ro" \
  -v "$PWD/../roadmap/provenance-cards:/contract_frozen:ro" \
  -w /app -e PYTHONPATH=/app $ENV $IMG \
  python checks/check_monitoring_v2.py

# sortie / calibration / débat V2 (§11-§12/A5 + §9-C, lot 9) : les PONTS inter-objets, et surtout
# le trou H7 transposé — le contrat accepte un seuil d'invalidation falsifié, le rétablissement
# depuis la thèse figée le refuse. Même montage /contract_frozen. Hors ligne, aucun appel modèle.
docker run --rm --network none -v "$PWD:/app:ro" \
  -v "$PWD/../roadmap/provenance-cards:/contract_frozen:ro" \
  -w /app -e PYTHONPATH=/app $ENV $IMG \
  python checks/check_exit_debate.py

# route GET /v2/theses (listing + détail enrichi) — hors ligne, aucun appel modèle.
docker run --rm --network none -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app $ENV $IMG \
  python checks/check_theses_v2_listing.py

# analyse statique f-strings : noms non résolus dans backend/app/ — hors ligne, aucun appel modèle.
# Vise le NameError silencieux en prod (commentaire SQL avec accolades, Convention #39).
docker run --rm --network none -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app $ENV $IMG \
  python checks/check_fstring_sql.py
```

> **Base de référence au 2026-09-04 (2) : 1195 assertions / 0 échec** sur les 17 scripts hors-ligne
> (`search_worker` 52, `provenance` 50, `edgar_feed` 77, `financials_feed` 69, `synthesis_feed` 56,
> `readiness_recompute` 77, `analysis_contract` 21, `decision_validate` 54, `base_rate_corpus` 27,
> `monitoring_v2` 116, `exit_debate` 175, `theses_v2_listing` 52, `tickers_v2_listing` 162,
> `knowledge_entries_listing` 100, `runner_telemetry` 49, `valuation_feed` **38** (+18 : F7, un
> multiple négatif n'est pas un multiple — §6/§7), `fstring_sql` 20).
> Les deux scripts réseau (`fetch_live`, `fetch_relevance`) portent le total à **19 scripts**.
>
> ⚠️ **Quatre scripts comptent MOINS si on oublie le montage `/contract_frozen`.** Sans
> `-v "$PWD/../roadmap/provenance-cards:/contract_frozen:ro"`, `analysis_contract`,
> `decision_validate`, `monitoring_v2` et `exit_debate` sautent leur section de synchro contrat
> figé ↔ copie runtime (#19) et rendent 17 / 45 / 98 / 156 — **en sortant quand même à 0**. Le
> saut est annoncé sur stdout, mais une boucle scriptée qui ne lit que le code de sortie lit une
> couverture partielle comme une couverture pleine. Constaté en direct : la mesure incomplète a
> failli écraser des chiffres corrects dans ce README. Un total ne se recopie pas — mais il ne se
> re-mesure valablement qu'avec l'invocation complète documentée ci-dessus.
> ⚠️ Trois scripts n'écrivent **pas** la même ligne de résumé
> (`50 OK / 0 KO`, `47 ok / 0 FAIL`) : un `grep` sur « vérifications OK » les rend **silencieux**, ce
> qui se lit comme un succès. Lire le code de sortie ou la dernière ligne, pas un motif unique.

Le seul check qui exige des **clés réelles** (Exa + embeddings DeepInfra) est `check_fetch_relevance.py` :
il n'est donc pas jouable dans un conteneur jetable sans exposer les secrets. On le lance **dans le
conteneur backend en prod**, dont l'env porte déjà les clés — elles restent confinées :

```bash
docker cp checks/check_fetch_relevance.py portfolio-backend:/tmp/ && \
docker exec -w /app portfolio-backend python /tmp/check_fetch_relevance.py; \
docker exec portfolio-backend rm -f /tmp/check_fetch_relevance.py
```

⚠️ **`EXA_API_KEY` n'est pas optionnelle pour ce check, réseau ou pas.** Joué avec le réseau mais
sans la clé, il **échoue** (exit 1) sur le volet CNBC : la page rend `403` en direct, le repli
`search_backend_cache` de la convention #26 passe par Exa, donc pas de clé = pas de repli = pas de
passage. Vérifié le 2026-09-04, **au HEAD avant toute modification** (`git archive HEAD`) : rouge
sans la clé, vert avec — ce n'est donc pas une régression, c'est une pré-condition qui n'était
écrite nulle part. Le lancer dans `portfolio-backend` est le chemin correct **parce que** son env
porte la clé, pas seulement par commodité réseau.

| Script | Ce qu'il éprouve | Réseau / clés |
|---|---|---|
| `check_search_worker.py` | `_apply_deterministic_overrides` face à une sortie de modèle **hostile** (source surqualifiée, score gonflé, mauvais `entry_type`, doublons, dépassement de `max_entries`, `llm_memory` non déclarée) + `classify_source_type` + extraction HTML + échec explicite sans clé de recherche. 40 assertions. | aucun (`--network none`) |
| `check_provenance.py` | `canonical_url`, `RetrievalLog` (profondeur monotone), `_verify_provenance` (rétrogradation `llm_memory` si l'URL n'a jamais été lue), `_cited_documents` (une entrée = un document), `document_search.select_relevant` (passage cible atteint, repli lexical déclaré, budget respecté), §8 `classify_source_type` confronté au plancher effectif du champ — un cabinet d'études doit pouvoir atteindre le plancher B de `marche.croissance_marche_historique`, sans que la liste réputée devienne un passe-droit (cf. convention #32). 50 assertions. | aucun (`--network none`) |
| `check_edgar_feed.py` | Alimentateur du **socle EDGAR** (postes comptables bruts, amorçage d'un ticker au corpus vide) : `select_concept` — le concept XBRL se choisit par **fraîcheur**, pas par convention (`Revenues` répond 200 pour MSFT avec un dernier point de **2010** ; `PaymentsToAcquirePropertyPlantAndEquipment` s'arrête en **2012** pour NVDA) ; garde-fou de durée (un point `fp=FY` trimestriel ne passe pas pour un flux annuel) ; alignement sur un exercice unique ; `filing_url` relisible par `cik_from_url` ; poste ou jambe de composite manquante = `unfounded`, jamais estimé ; et la **boucle refermée** — `extract_edgar_facts()` relit les specs produites. **§8 (RVMD, 3ᵉ ticker)** : une dette long terme **non déposée** n'est ni un zéro ni une raison de perdre la trésorerie du même poste composite — `long_term_debt=None` + `long_term_debt_status='aucun_concept_depose'`, cash conservé, mention dans `unfounded`. C'est #30 transposé aux composites : la famille de concepts de dette décrivait des emprunts de société mature, alors qu'un émetteur en développement se finance en **obligations convertibles** (RVMD dépose 487,4 M$ en `ConvertibleLongTermNotesPayable`). ⚠️ Le message du commit 2eff706 se trompe sur le chiffrage : à l'ancre FY2025, RVMD n'avait **pas** de dette long terme déposée (le seul point au 2025-12-31, issu d'un 10-Q, vaut 0) — les 487,4 M$ de convertibles datent du **2026-06-30**. L'enjeu du composite n'était donc pas un signe inversé mais l'assiette : sur l'ancre périmée, `levier` était simplement infondé. **§9-§10 (F4/F5)** : un poste de BILAN est daté d'un INSTANT, pas d'un exercice — le socle ne lisait que les dépôts annuels, donc il était aveugle à tout trimestre publié depuis le dernier 10-K (RVMD : trésorerie 383,7 → 815,4 M$, capitaux propres 1 631,3 → 2 606,2 M$, actif 2 354,5 → 4 323,3 M$, dette convertible 0 → 487,4 M$, sur une position **détenue**). Un instantané se reconnaît à l'absence de `start`, **jamais** à `fp` (RVMD tague `fp=Q2` un point au 2026-03-31). §10 est le corollaire trouvé EN PROD après le correctif : la clé d'identité d'un fait dépend elle aussi du type de poste — un flux vaut par `(metric, exercice)`, un stock par `metric` seul. Apparier un stock sur l'égalité des dates faisait qu'un changement d'ancre **ajoutait** la vérité sans retirer le périmé : deux capitaux propres actifs et contradictoires dans le corpus, sans aucun ratio faux pour le signaler. 77 assertions. | aucun (`--network none`) |
| `check_financials_feed.py` | Alimentateur `financials` : `extract_edgar_facts` (choix d'exercice, poste composite, capex absent = None), `build_financials_entries` (arithmétique des 4 ratios sur NVDA FY2026, fondation partielle honnête sans capex, tout en `edgar_official`), helpers EDGAR (`cik_from_url`, appariement annuel). **§6 (RVMD, 3ᵉ ticker) — un ratio valide un calcul, jamais son sens** : sur un émetteur déficitaire, FCF ÷ résultat net rend `+80,8 %` (deux négatifs), arithmétiquement exact, contrat satisfait, sens **inversé** — une entreprise qui brûle 914 M$/an était publiée en Tier A comme excellente convertisseuse de cash. `fcf_conversion_pct` devient `None`, la métrique devient `cash_burn`. Plus les libellés de `_miss` : « absent », « nul » et « non calculable » sont trois choses distinctes (un chiffre d'affaires **déposé à 0** n'est pas un intrant manquant). **§7-§8 (F4/F6)** : `extract_edgar_facts` apparie sur DEUX ancres — apparier les flux sur l'ancre de bilan les viderait tous en silence, chaque ratio devenant « non fondé » sans qu'aucune erreur ne sorte. §8 est le pendant côté SORTIE, constaté en prod : un ratio se date par les postes qui le composent. `levier` n'est fait que de postes de bilan et sortait étiqueté « FY2025 » — tous ses nombres justes, le fait faux, donc rien d'arithmétique ne pouvait le voir. Un ratio MIXTE (ROIC : flux au numérateur, bilan au dénominateur) reste licite mais le DÉCLARE, en structuré et en toutes lettres. Plus le doublon de capex : ce module et le socle EDGAR écrivaient le même fait sous deux jeux de tags (`fact` en écart), deux `capital_expenditure` FY2025 courants en même temps — l'identité d'un fait est ce qu'il MESURE, pas le vocabulaire du module qui l'écrit. 69 assertions. | aucun (`--network none`) |
| `check_synthesis_feed.py` | Alimentateur de **synthèse grounded** (ingestion-agent mode synthèse) : `derive_synthesis_reliability` (règle « un cran sous la plus faible entry citée » — jamais de surévaluation), `validate_grounding` (citation hors corpus / assertion non sourcée = violation), contrat `GroundedSynthesis` (≥1 citation/claim, union des ids), `build_content_structured` (traçabilité), registre des cibles + `citable_tiers`, et les **descripteurs agnostiques de l'émetteur** (#31) : aucune `query`/`guidance` ne nomme un acteur en dur, toutes sont paramétrées par `{company}` et `resolve()` les spécialise sans laisser de placeholder. 56 assertions. | aucun (`--network none`) |
| `check_readiness_recompute.py` | **Curator — couverture pilotée par l'index `covers`** (029) : `_tier_ge`/`_plancher_for` (plancher par champ, dégradé `croissance=B`), `_covers_index` (multi-champ, entry non taguée absente), `recompute_coverage` (le plancher MORD ; l'index DÉCOUVRE une entry que le LLM n'a pas citée ; une citation LLM sans tag ne fonde plus rien ; `produits.description` ne fonde pas `business_model.description`), `_exigences` (le LLM peut resserrer les champs requis / le plancher, jamais les desserrer), `reconcile_gaps` (bijection), et le **déterminisme** : même corpus + `fondations` LLM différentes → couverture strictement identique. Plus la **dispense par émetteur** (#31) : un ticker sans dispense écrite n'hérite d'aucun passe-droit — `recurrence_pct` bloque pour MSFT là où il est dispensé pour NVDA, et le libellé NVDA ne fuit pas dans les incertitudes d'un autre émetteur. Plus la **narration contrainte** (dette A) : une phrase du `rationale` qui nomme un verdict autre que celui recomputé est retirée et le retrait déclaré, l'en-tête factuel porte verdict + blocs + champs non fondés, et `already`/`not_ready` ne sont pas lus comme `ready`. 77 assertions. | aucun (`--network none`) |
| `check_analysis_contract.py` | **Contrat d'analyse** (bull/bear) — le check qui manquait quand le reverse-DCF a été desserré à chaud : `croissance_implicite_prix_actuel_pct` REQUIS (jamais `null`), `Assumptions` fermé aux 3 clés (`extra='forbid'`, pas de `taux_actualisation` inventé), et surtout les **unités dans le nom** — les anciens `croissance_revenue`/`expansion_marge_fcf` nus sont désormais REJETÉS, pas ignorés (bull rendait `0.15`, bear `8.0` pour la même grandeur). Négatifs licites (décroissance, compression de marge), `horizon_ans ≥ 5` (A4), et §6 la synchro contrat figé ↔ copie runtime (#19). 21 assertions. | aucun (`--network none`) |
| `check_decision_validate.py` | **Acte de décision V2** (§9, lot 7) — le contrat `ThesisValidation`, là où G2 s'exerce le plus fort : verdict actionnable (`PASS`/`WATCH` refusés), **bijection** `risk_acks` ↔ `risques_acceptes` (manquant / fantôme / doublon / `accepted=False`), pré-mortem, pont risques → hypothèses (falsifiabilité), cap Kelly et **override tracé A7** (un override sans motif, ou perçant `pct_max`, est rejeté ; un sizing « prudent » non tracé aussi — ce n'est pas de la prudence, c'est du hors-contrat), `valuation_range` ordonnée, contrat fermé (`extra='forbid'`). **§8 = la vérification la plus importante du fichier** : elle inspecte `ValidateV2Body.model_fields` pour prouver que le corps HTTP **n'expose aucun champ de jugement** (`verdict`, sizing, conditions, hypothèses, valuation, synthèse) — un contrat de décision ne vaut que par ce qu'il refuse de recevoir (#36). §9 la dérivation de la fourchette depuis le research memo (jamais une moyenne inventée), §10 la synchro contrat figé ↔ copie runtime (#19). 54 assertions. | aucun (`--network none`) |
| `check_monitoring_v2.py` | **Monitoring V2** (modes 1-6, lot 8) — et surtout **§3, le pont inter-objets**, qui est la raison d'être du fichier : il prouve d'abord que `Mode2QuarterlyReview` **ACCEPTE** une escalade sur une hypothèse `H7` inexistante (contrat pleinement satisfait, anti-churn contourné), puis que `_valider_pont_hypotheses` la **REFUSE** — montrer le refus seul ne prouverait pas que le trou existait (#37). Plus : §1/§2 contrats mode 6 et anti-churn 1-5, §4 champs dérivés forcés côté code (`mode`, `thesis_id`, `pair_ticker`, `source_mode`, `next_review_date`), §5 colonnes de routage ↔ domaines des CHECK de la migration 031, **§6 les seuils figés en lecture seule** (une revue ne peut pas abaisser le seuil qu'elle vient de franchir), §7 `MonitoringRunBody` n'expose aucun champ de jugement (#36), §8 `EventRouterV2` inspecté en source — INNER JOIN, pas de garde `synced`, `v2_auto_enabled`, rattrapage du seul mode 6 (#38) ; la docstring du module est **retirée avant grep**, sinon l'explication des défauts V1 se lirait comme les défauts eux-mêmes. §9 migration ↔ code, §10 synchro contrat figé (#19). 116 assertions. | aucun (`--network none`) |
| `check_theses_v2_listing.py` | **Route GET /v2/theses** (listing + détail enrichi) — shape null nominaux (position/session/exit_plan/post_mortem absents = null, pas {}), `valuation_range_figee` lu depuis `validation_json` et **délibérément différente** de `valuation_range` (fixtures distinctes, sinon le test est aveugle), agrégats `nb_hypotheses`/`hypotheses_par_statut`, enrichissements additifs de `GET /v2/theses/{id}` (SELECT * conservé, 5 clés ajoutées), isolation V1/V2 prouvée par inspection de la table source, filtre `?ticker_id=`, surface HTTP (#36). 52 assertions. | aucun (`--network none`) |
| `check_fstring_sql.py` | **Analyse statique f-strings** — parcourt les 104 fichiers de `backend/app/` par `ast`, vérifie que chaque nom référencé dans un champ de remplacement `{expr}` est résolvable dans sa portée (args, variables locales, cibles de `for`/`with`/`except` async inclus, compréhensions, imports, builtins). Vise le `NameError` silencieux en prod de Convention #39 : un commentaire SQL `{statut: count}` dans une f-string → 500 en prod, 0 échec hors-ligne. 20 assertions. | aucun (`--network none`) |
| `check_runner_telemetry.py` | **Télémétrie d'un abandon du runner** (#41) — le seul check qui exécute le VRAI `run_json_agent` / `run_tool_json_agent` de bout en bout, contre un `AgentProvider` bouchonné dont les réponses sont scriptées (donc du code réellement joué, pas des fixtures relues). §3 la somme **exacte** des tokens des deux tentatives portée par `AgentOutputInvalid` ; §4 `raw_content` = le texte fautif du dernier tour ; §5 `isinstance(e, RuntimeError)` — si elle tombe, les 6 sites d'appel qui font `except RuntimeError` cassent ; §6 les **noms** attendus par les `_persister_echec` **et leurs types** (`int`/`int`/`float` : colonnes INTEGER/NUMERIC, et une `DataError` de binding serait avalée par leur `except Exception`) ; **§7 le cas qui motive tout** — boucle d'outils réussie puis clôture ratée, le coût de la boucle doit être reporté par `add_upstream()` ; §8 `__str__` recalculé après report ; §1/§2/§9 non-régression du chemin nominal. **Éprouvé par test négatif** : report supprimé → 3 échecs en §7, `3850` attendus contre `850` reçus. 49 assertions. | aucun (`--network none`) |
| `check_fetch_live.py` | `fetch_url` sur des URL réelles (IR client-rendu, EDGAR, page statique) et ses erreurs attendues (URL vide, non-http, 404, `web_search` sans clé). | réseau, pas de clé |
| `check_fetch_relevance.py` | Fin de la troncature : `fetch_url(url, query=…)` rapporte l'info même quand elle est loin dans le document — 10-K NVDA (`22%`/`14%` à 37,6 %, `via=direct mode=relevance`) et article CNBC (`Maia` à 71,5 %, `via=search_backend_cache mode=whole`). | réseau **+ Exa + DeepInfra** → run in-container |

Les trois premiers n'ont pas besoin de secret : ils vérifient ce qui doit être vrai **avant** qu'une
clé soit posée. Le run réel de bout en bout (search-worker → entries → readiness `ready`) reste à
faire une fois une session de recherche complète jouée sur un ticker.
