# checks/ — vérifications exécutables des agents V2

Scripts autonomes, hors image de production (le build ne copie que `app/`). Ils tournent dans un
container jetable bâti sur l'image backend, seul endroit où pydantic est en **v2** (le python hôte
est en v1).

```bash
cd projects/portfolio-tracker/backend
IMG=$(docker inspect $(docker ps --format '{{.Names}}' | grep portfoliobackend) --format '{{.Config.Image}}')
ENV="-e DUST_API_KEY=x -e DUST_RESEARCH_AGENT_ID=x -e DUST_PORTFOLIO_AGENT_ID=x \
     -e DATABASE_URL=postgresql://u:p@h:5432/d -e SLACK_BOT_TOKEN=x -e SLACK_APP_TOKEN=x \
     -e SLACK_PORTFOLIO_CHANNEL_ID=x -e FMP_API_KEY=x"

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
```

> **Base de référence au 2026-09-01 : 759 assertions / 0 échec** sur les 12 scripts hors-ligne
> (`search_worker` 52, `provenance` 50, `edgar_feed` 47, `financials_feed` 32, `synthesis_feed` 56,
> `readiness_recompute` 77, `analysis_contract` 21, `decision_validate` 54, `base_rate_corpus` 27,
> `monitoring_v2` 116, `exit_debate` 175, `theses_v2_listing` 52). ⚠️ Trois scripts n'écrivent **pas** la même ligne de résumé
> (`50 OK / 0 KO`, `47 ok / 0 FAIL`) : un `grep` sur « vérifications OK » les rend **silencieux**, ce
> qui se lit comme un succès. Lire le code de sortie ou la dernière ligne, pas un motif unique.

Le seul check qui exige des **clés réelles** (Exa + embeddings DeepInfra) est `check_fetch_relevance.py` :
il n'est donc pas jouable dans un conteneur jetable sans exposer les secrets. On le lance **dans le
conteneur backend en prod**, dont l'env porte déjà les clés — elles restent confinées :

```bash
CT=$(docker ps --format '{{.Names}}' | grep portfoliobackend)
docker cp checks/check_fetch_relevance.py "$CT":/tmp/ && \
docker exec -w /app "$CT" python /tmp/check_fetch_relevance.py; \
docker exec "$CT" rm -f /tmp/check_fetch_relevance.py
```

| Script | Ce qu'il éprouve | Réseau / clés |
|---|---|---|
| `check_search_worker.py` | `_apply_deterministic_overrides` face à une sortie de modèle **hostile** (source surqualifiée, score gonflé, mauvais `entry_type`, doublons, dépassement de `max_entries`, `llm_memory` non déclarée) + `classify_source_type` + extraction HTML + échec explicite sans clé de recherche. 40 assertions. | aucun (`--network none`) |
| `check_provenance.py` | `canonical_url`, `RetrievalLog` (profondeur monotone), `_verify_provenance` (rétrogradation `llm_memory` si l'URL n'a jamais été lue), `_cited_documents` (une entrée = un document), `document_search.select_relevant` (passage cible atteint, repli lexical déclaré, budget respecté), §8 `classify_source_type` confronté au plancher effectif du champ — un cabinet d'études doit pouvoir atteindre le plancher B de `marche.croissance_marche_historique`, sans que la liste réputée devienne un passe-droit (cf. convention #32). 50 assertions. | aucun (`--network none`) |
| `check_edgar_feed.py` | Alimentateur du **socle EDGAR** (postes comptables bruts, amorçage d'un ticker au corpus vide) : `select_concept` — le concept XBRL se choisit par **fraîcheur**, pas par convention (`Revenues` répond 200 pour MSFT avec un dernier point de **2010** ; `PaymentsToAcquirePropertyPlantAndEquipment` s'arrête en **2012** pour NVDA) ; garde-fou de durée (un point `fp=FY` trimestriel ne passe pas pour un flux annuel) ; alignement sur un exercice unique ; `filing_url` relisible par `cik_from_url` ; poste ou jambe de composite manquante = `unfounded`, jamais estimé ; et la **boucle refermée** — `extract_edgar_facts()` relit les specs produites. 47 assertions. | aucun (`--network none`) |
| `check_financials_feed.py` | Alimentateur `financials` : `extract_edgar_facts` (choix d'exercice, poste composite, capex absent = None), `build_financials_entries` (arithmétique des 4 ratios sur NVDA FY2026, fondation partielle honnête sans capex, tout en `edgar_official`), helpers EDGAR (`cik_from_url`, appariement annuel). 32 assertions. | aucun (`--network none`) |
| `check_synthesis_feed.py` | Alimentateur de **synthèse grounded** (ingestion-agent mode synthèse) : `derive_synthesis_reliability` (règle « un cran sous la plus faible entry citée » — jamais de surévaluation), `validate_grounding` (citation hors corpus / assertion non sourcée = violation), contrat `GroundedSynthesis` (≥1 citation/claim, union des ids), `build_content_structured` (traçabilité), registre des cibles + `citable_tiers`, et les **descripteurs agnostiques de l'émetteur** (#31) : aucune `query`/`guidance` ne nomme un acteur en dur, toutes sont paramétrées par `{company}` et `resolve()` les spécialise sans laisser de placeholder. 56 assertions. | aucun (`--network none`) |
| `check_readiness_recompute.py` | **Curator — couverture pilotée par l'index `covers`** (029) : `_tier_ge`/`_plancher_for` (plancher par champ, dégradé `croissance=B`), `_covers_index` (multi-champ, entry non taguée absente), `recompute_coverage` (le plancher MORD ; l'index DÉCOUVRE une entry que le LLM n'a pas citée ; une citation LLM sans tag ne fonde plus rien ; `produits.description` ne fonde pas `business_model.description`), `_exigences` (le LLM peut resserrer les champs requis / le plancher, jamais les desserrer), `reconcile_gaps` (bijection), et le **déterminisme** : même corpus + `fondations` LLM différentes → couverture strictement identique. Plus la **dispense par émetteur** (#31) : un ticker sans dispense écrite n'hérite d'aucun passe-droit — `recurrence_pct` bloque pour MSFT là où il est dispensé pour NVDA, et le libellé NVDA ne fuit pas dans les incertitudes d'un autre émetteur. Plus la **narration contrainte** (dette A) : une phrase du `rationale` qui nomme un verdict autre que celui recomputé est retirée et le retrait déclaré, l'en-tête factuel porte verdict + blocs + champs non fondés, et `already`/`not_ready` ne sont pas lus comme `ready`. 74 assertions. | aucun (`--network none`) |
| `check_analysis_contract.py` | **Contrat d'analyse** (bull/bear) — le check qui manquait quand le reverse-DCF a été desserré à chaud : `croissance_implicite_prix_actuel_pct` REQUIS (jamais `null`), `Assumptions` fermé aux 3 clés (`extra='forbid'`, pas de `taux_actualisation` inventé), et surtout les **unités dans le nom** — les anciens `croissance_revenue`/`expansion_marge_fcf` nus sont désormais REJETÉS, pas ignorés (bull rendait `0.15`, bear `8.0` pour la même grandeur). Négatifs licites (décroissance, compression de marge), `horizon_ans ≥ 5` (A4), et §6 la synchro contrat figé ↔ copie runtime (#19). 21 assertions. | aucun (`--network none`) |
| `check_decision_validate.py` | **Acte de décision V2** (§9, lot 7) — le contrat `ThesisValidation`, là où G2 s'exerce le plus fort : verdict actionnable (`PASS`/`WATCH` refusés), **bijection** `risk_acks` ↔ `risques_acceptes` (manquant / fantôme / doublon / `accepted=False`), pré-mortem, pont risques → hypothèses (falsifiabilité), cap Kelly et **override tracé A7** (un override sans motif, ou perçant `pct_max`, est rejeté ; un sizing « prudent » non tracé aussi — ce n'est pas de la prudence, c'est du hors-contrat), `valuation_range` ordonnée, contrat fermé (`extra='forbid'`). **§8 = la vérification la plus importante du fichier** : elle inspecte `ValidateV2Body.model_fields` pour prouver que le corps HTTP **n'expose aucun champ de jugement** (`verdict`, sizing, conditions, hypothèses, valuation, synthèse) — un contrat de décision ne vaut que par ce qu'il refuse de recevoir (#36). §9 la dérivation de la fourchette depuis le research memo (jamais une moyenne inventée), §10 la synchro contrat figé ↔ copie runtime (#19). 54 assertions. | aucun (`--network none`) |
| `check_monitoring_v2.py` | **Monitoring V2** (modes 1-6, lot 8) — et surtout **§3, le pont inter-objets**, qui est la raison d'être du fichier : il prouve d'abord que `Mode2QuarterlyReview` **ACCEPTE** une escalade sur une hypothèse `H7` inexistante (contrat pleinement satisfait, anti-churn contourné), puis que `_valider_pont_hypotheses` la **REFUSE** — montrer le refus seul ne prouverait pas que le trou existait (#37). Plus : §1/§2 contrats mode 6 et anti-churn 1-5, §4 champs dérivés forcés côté code (`mode`, `thesis_id`, `pair_ticker`, `source_mode`, `next_review_date`), §5 colonnes de routage ↔ domaines des CHECK de la migration 031, **§6 les seuils figés en lecture seule** (une revue ne peut pas abaisser le seuil qu'elle vient de franchir), §7 `MonitoringRunBody` n'expose aucun champ de jugement (#36), §8 `EventRouterV2` inspecté en source — INNER JOIN, pas de garde `synced`, `v2_auto_enabled`, rattrapage du seul mode 6 (#38) ; la docstring du module est **retirée avant grep**, sinon l'explication des défauts V1 se lirait comme les défauts eux-mêmes. §9 migration ↔ code, §10 synchro contrat figé (#19). 116 assertions. | aucun (`--network none`) |
| `check_theses_v2_listing.py` | **Route GET /v2/theses** (listing + détail enrichi) — shape null nominaux (position/session/exit_plan/post_mortem absents = null, pas {}), `valuation_range_figee` lu depuis `validation_json` et **délibérément différente** de `valuation_range` (fixtures distinctes, sinon le test est aveugle), agrégats `nb_hypotheses`/`hypotheses_par_statut`, enrichissements additifs de `GET /v2/theses/{id}` (SELECT * conservé, 5 clés ajoutées), isolation V1/V2 prouvée par inspection de la table source, filtre `?ticker_id=`, surface HTTP (#36). 52 assertions. | aucun (`--network none`) |
| `check_fetch_live.py` | `fetch_url` sur des URL réelles (IR client-rendu, EDGAR, page statique) et ses erreurs attendues (URL vide, non-http, 404, `web_search` sans clé). | réseau, pas de clé |
| `check_fetch_relevance.py` | Fin de la troncature : `fetch_url(url, query=…)` rapporte l'info même quand elle est loin dans le document — 10-K NVDA (`22%`/`14%` à 37,6 %, `via=direct mode=relevance`) et article CNBC (`Maia` à 71,5 %, `via=search_backend_cache mode=whole`). | réseau **+ Exa + DeepInfra** → run in-container |

Les trois premiers n'ont pas besoin de secret : ils vérifient ce qui doit être vrai **avant** qu'une
clé soit posée. Le run réel de bout en bout (search-worker → entries → readiness `ready`) reste à
faire une fois une session de recherche complète jouée sur un ticker.
