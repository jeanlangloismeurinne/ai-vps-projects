# checks/ — vérifications exécutables des agents V2

Scripts autonomes, hors image de production (le build ne copie que `app/`). Ils tournent dans un
container jetable bâti sur l'image backend, seul endroit où pydantic est en **v2** (le python hôte
est en v1).

## Tout jouer d'un coup

```bash
cd projects/portfolio-tracker/backend
bash checks/run_all.sh          # une ligne par script + « TOTAL assertions = … », exit ≠ 0 si un échec
```

C'est le **chemin recommandé** : il porte les invocations correctes (montage `/contract_frozen`,
réseau et `CHECK_DB_URL` pour `check_entry_nature`) et il reconnaît le bilan de chaque script à sa
**forme**, pas à sa position. ⚠️ Ce lanceur a longtemps vécu dans `/tmp`, réécrit de mémoire à
chaque session : sa dernière version sous-comptait **47 assertions** en silence (elle lisait
`tail -1` sur stdout+stderr fusionnés, or `check_runner_telemetry` émet un LOG *après* son bilan →
2 comptées au lieu de 49, total 1 464 au lieu de 1 511, `exit 0`). Il est versionné pour que ce
défaut ne revienne pas ; **ne pas le réécrire ailleurs**. Détail dans son en-tête.

## Un script à la fois

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

# axe `nature` d'une entry (capacité 1 de la roadmap 02, convention #51) : dérivation déterministe
# + ÉTAT PERSISTÉ. §7 lit la vraie base → réseau `coolify` ET `CHECK_DB_URL` obligatoires. Sans eux
# le script SORT EN ÉCHEC (il ne saute pas la section) : une mesure incomplète ne doit jamais
# passer pour un 0. La variable vient du `.env` du projet — ne pas la recopier en clair ici.
docker run --rm --network coolify -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app $ENV \
  -e "CHECK_DB_URL=$(grep -m1 '^DATABASE_URL=' .env | cut -d= -f2-)" $IMG \
  python checks/check_entry_nature.py
```

> **Base de référence au 2026-09-08 : 1 798 assertions / 0 échec / 22 scripts**, mesurées par
> `bash checks/run_all.sh`. Détail des apports depuis 1216 : `field_profiles` **193** (capacité 0,
> table de profils des 19 champs — #50), `entry_nature` **52** (capacité 1, axe `nature` — #51),
> `source_registry` **78** (capacité 2, registre nominatif — #52), `actualite` **66** (capacité 3,
> axe `actualité` — #53), `readiness_recompute` **131** (capacité 4, la porte de complétude à trois
> états — #54), `material_events` **81** (dont 18 pour la réévaluation à la lecture, cf. sa ligne),
> plus les correctifs F12→F15 sur les scripts existants. Les deux scripts
> réseau (`fetch_live`, `fetch_relevance`) sont **exclus** du lanceur et ne sont pas dans ce total.
>
> ⚠️ **Ce total ne se recopie pas** : il se re-mesure par `run_all.sh`, jamais par une boucle
> improvisée. Et quand une re-mesure diverge du chiffre écrit ici, l'hypothèse à tester **en
> premier** est « ma mesure est incomplète », pas « le README a dérivé » — c'est vrai plus souvent,
> et c'est moins cher à vérifier (les deux pièges ci-dessous l'ont chacun démontré une fois).
>
> ⚠️ **Quatre scripts comptent MOINS si on oublie le montage `/contract_frozen`.** Sans
> `-v "$PWD/../roadmap/provenance-cards:/contract_frozen:ro"`, `analysis_contract`,
> `decision_validate`, `monitoring_v2` et `exit_debate` sautent leur section de synchro contrat
> figé ↔ copie runtime (#19) et rendent 17 / 45 / 98 / 156 — **en sortant quand même à 0**. Le
> saut est annoncé sur stdout, mais une boucle scriptée qui ne lit que le code de sortie lit une
> couverture partielle comme une couverture pleine. Constaté en direct : la mesure incomplète a
> failli écraser des chiffres corrects dans ce README. Un total ne se recopie pas — mais il ne se
> re-mesure valablement qu'avec l'invocation complète documentée ci-dessus.
> ⚠️ **Trois dialectes de ligne de bilan cohabitent** (`… vérifications OK`, `47 ok / 0 FAIL`,
> `50 OK / 0 KO`) : un `grep` sur un seul motif rend les autres **silencieux**, ce qui se lit comme
> un succès. Et un `tail -1` ne marche pas non plus — `check_runner_telemetry` émet une ligne de LOG
> *après* son bilan. La règle : reconnaître le bilan par sa **forme** (les trois motifs), puis
> prendre le dernier de **ces** lignes-là ; et traiter l'absence totale de bilan comme un **échec**
> (script mort avant ses asserts), jamais comme un zéro. `run_all.sh` fait exactement ça.

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

## Ce qui vit dans `tools/` et pas ici

Deux scripts mesurent la porte de complétude **contre le corpus réel**. Ils ne sont pas dans
`checks/` et ne sont pas dans `run_all.sh` : un check est hors ligne et déterministe, eux lisent la
base et interrogent EDGAR. Chacun a son lanceur versionné, pour la raison de `run_all.sh` —
l'invocation fait partie du test, et l'ordre des `--env-file` y est load-bearing.

```bash
bash tools/mesure_gate.sh          # « combien de champs basculeraient » — contre-calcul indépendant
bash tools/acceptation_gate.sh     # le DELTA de verdict — la porte elle-même, sur les rapports persistés
```

Ils sont **complémentaires et volontairement redondants**. `mesure_gate_capacite4.py` croise
l'index, les planchers et l'axe d'actualité *sans passer par la porte* : sa divergence d'avec elle
serait le signal que la porte a cessé d'être le détenteur unique (#46). `acceptation_capacite4.py`
appelle au contraire la fonction de production, `curator._apply_deterministic_overrides`, sur le
`report_json` **persisté** de chaque émetteur — c'est-à-dire sur le faux vert `ready, 0 gap` que
l'utilisateur voit encore aujourd'hui. Aucun des deux n'écrit quoi que ce soit, et aucun n'appelle
de modèle : la porte est déterministe de bout en bout, donc son acceptation l'est aussi.

⚠️ **Ne pas les jouer dans `portfolio-backend`**, contrairement à `check_fetch_live.py`. Ce
conteneur porte le code **déployé**, qui peut être antérieur à la capacité qu'on vérifie — mesuré
le 2026-09-08, son curator ne connaissait pas `champs_perimes`. Les lanceurs montent donc le dépôt
en lecture seule dans une instance neuve de l'image.

Résultat au 2026-09-08 (`bash tools/acceptation_gate.sh`, **13 vérifications OK / 0 échec**) :
NVDA (#27) et MSFT (#26) passent tous deux de `ready, 0 gap` **persisté** à `not_ready` avec cause
`peremption`, 9 champs périmés nommés chacun, 7 mandats — et **aucun champ périmé n'est envoyé en
collecte**. RVMD reste le témoin de séparation : aucun rapport readiness en base, donc pas un
porteur du delta. **Éprouvé par test négatif** : `champs_perimes` forcé à `[]` dans le curator →
4 FAIL nommés, et le bilan chiffre l'enjeu — le dossier sort alors `not_ready (lacune)`, soit
9 champs par émetteur envoyés en recherche complète là où un rafraîchissement suffisait.

⚠️ **Le tableau ci-dessous avait dérivé, et le trou était muet.** Au 2026-09-07 il décrivait 14
scripts sur 22 : `base_rate_corpus`, `exit_debate`, `knowledge_entries_listing`, `material_events`,
`source_registry`, `tickers_v2_listing`, `valuation_feed` avaient été livrés avec leur ligne de
total mise à jour mais **sans** leur ligne de tableau. Un tableau incomplet se lit comme un
inventaire complet — c'est `feedback_check_degrade_en_sortant_a_zero` transposé à la doc. Les huit
lignes sont ajoutées ci-dessous ; la garde est la boucle
`for f in checks/check_*.py; do grep -q "\`$(basename $f)\`" checks/README.md || echo ABSENT; done`,
à passer avant de clore un lot qui ajoute un script.

| Script | Ce qu'il éprouve | Réseau / clés |
|---|---|---|
| `check_actualite.py` | **Axe `actualité`** (capacité 3 de `02-spec-autorite-vs-actualite.md`, convention #53) — le seul des trois axes qui ne soit **pas** stocké : le persister reproduirait la cause n°2 du diagnostic (un score figé à l'écriture, donc un corpus qui ne vieillit jamais). §1 vocabulaire fermé **et atteignable** (#32), chaque état vérifié par son nom depuis une entrée réelle ; **§2 l'acceptation de la capacité** — la MÊME entry, lue avant et après l'arrivée d'un 8-K postérieur, change d'état sans qu'aucun `UPDATE` soit émis et sans que la ligne lue soit mutée ; §3 `indeterminable` n'est pas `courante`, ses deux causes nommées et cumulables ; §4 propagation de la panne ; §5 `none` ≠ `unavailable` (#25) ; §6 le seuil est le `reportDate`, jamais le `filingDate` — le cas **discriminant** est un fait daté *entre* l'événement (27/08) et son dépôt (01/09), seul intervalle où les deux règles divergent ; §7 détenteur unique (#46) par grep sur `staleness`, qui **traduit** l'axe au lieu de le ré-implémenter ; §8 jamais persisté ; **§9 F15** — la partition du rapport, où le défaut est d'abord **reproduit** (deux prédicats indépendants) avant d'être montré fermé ; §10 la capacité 4 n'est pas anticipée. ⚠️ Deux filets, `axe()` et `_balayage()`, transforment une exception du module en **FAIL nommé** : sans eux le cas négatif n°1 tuait le script avant son bilan (deuxième des trois faux verts, §24 du `CHANTIER_OUTILLAGE_DEV.md`). ⚠️ Le grep de §8/§10 **retire la docstring** du module avant de chercher : elle énonce les interdits, donc la laisser fait lire chaque prohibition comme sa propre violation — 4 FAIL sur du code conforme à la première exécution. **Éprouvé par test négatif, 5/5** : propagation de la panne retirée (63/4) · entry non datée rendue courante (57/14) · seuil pris sur le dépôt (61/5) · frontière inversée (61/5) · partition ré-implémentée dans `staleness` (62/4, qui réaffiche le symptôme de prod : 4 classes pour 3 entries). 66 assertions. | aucun (`--network none`) |
| `check_material_events.py` | **La seconde horloge** (convention #49) — 8-K/6-K + balayage de péremption, charges utiles EDGAR copiées conformes. Le seuil est la date de l'**ÉVÉNEMENT** (`reportDate`), pas du dépôt ; trois états jamais confondus (`found`/`none`/`unavailable`) ; le module **n'écrit rien**, il produit un rapport. ⚠️ Sa §2bis utilise une fixture **construite** (deux 8-K dont l'ordre s'inverse selon la clef de tri) parce que le flux RVMD réel, pourtant copié fidèlement, donne le **même gagnant** avec les deux tris : une fixture peut être aveugle en étant *non discriminante*, pas seulement en étant plus favorable que la prod (#47). Ses **§13/§14** gardent la *réévaluation à la lecture* : le cache d'ancre mémorise la **réponse brute** et jamais un état d'actualité (sinon l'actualité redevient persistante, à l'échelle du TTL), jamais un **échec** (la mise en cache est la dernière instruction nominale — asserté par découpe de la source autour de `_ancre_cache[cik] =`), et le GET readiness **n'écrit pas**. **Éprouvé par test négatif, 2/2** (4 FAIL nommés, bilan atteint) : mise en cache déplacée AVANT le `raise` → l'échec mémorisé cache `{}`, qui se **parse en « aucun événement matériel »**, donc ancre `none`, donc aucune péremption, donc `ready` rendu pendant une heure sur tous les émetteurs — le faux vert que la capacité 4 vient de tuer, ressuscité par un hoquet EDGAR ; `UPDATE` du rapport rejoué ajouté dans le GET → les 9 champs périmés par émetteur se figent dans la ligne, l'actualité redevient stockée (cause n°2 du #50). 81 assertions. | aucun (`--network none`) |
| `check_source_registry.py` | **Registre nominatif des sources** (capacité 2, convention #52) — un **desserrage**, donc gardé plus serré que le reste. §2 est l'assert central : une source est admise pour un **COUPLE** (source × nature), et c'est l'ordre `nature` PUIS `registre` qui rend cette phrase vraie — le premier câblage repliait la promotion dans `classify_source_type`, donc la condition ne s'appliquait plus jamais. §1 atteignabilité (#32), §1bis portée réelle du desserrage, §3 hors registre → 0,50, §4 jamais de démotion, §6 détenteur unique (#46), §7 plafond ≠ qualification, §9 gabarit sans acteur nommé (#31). ⚠️ **§1bis a viré au vert de lui-même le 2026-09-08** : `_DESSERRAGE_NON_CABLE` est désormais **vide**, la capacité 4 ayant câblé le desserrage de #50 à la porte — l'assert « la liste des écarts ne survit pas à leur câblage » était écrit pour ce jour-là, et il éprouve maintenant que `_plancher_for` applique bien le desserrage champ par champ. ⚠️ Pas de section « état persisté », et c'est écrit dans la docstring : la capacité n'écrit rien, une section SQL serait verte sur zéro ligne. **Éprouvé par test négatif, 5/5.** 78 assertions. | aucun (`--network none`) |
| `check_base_rate_corpus.py` | Corpus de taux de base + ancre `valorisation.base_rate_anchor`, arithmétique confrontée aux chiffres **exacts** de l'Exhibit 2. §7-§10 (#45) : un libellé qualifie la maille **réellement mesurée** — « small-cap (CA < 1 Md$) » annoncé pour un émetteur capitalisé 44,8 Md$, tous les nombres justes et le fait faux ; quand les deux mailles divergent l'entry le **déclare**. §11-§12 (#47) : `0.0` est une **valeur**, pas une absence — `if rev:` sautait un CA légitimement nul et publiait un chiffre vieux de deux exercices, en contradiction directe avec l'entry EDGAR tier A du même corpus. ⚠️ La fixture portait des chiffres **plus favorables que la production** — une fixture qui embellit le réel est un check qui ne peut pas voir le défaut. **Éprouvé par test négatif (9 FAIL).** 65 assertions. | aucun (`--network none`) |
| `check_valuation_feed.py` | Alimentateur `valorisation` — transformation pure sur un m1 réel (NVDA) et un m1 à multiples négatifs (RVMD). §4/§6/§7 (#44) : un ratio à dénominateur négatif n'est pas un niveau, c'est une perte — `pe_ntm=-35,95×` n'ordonne rien et n'est pas monotone (une perte plus lourde fait paraître l'émetteur « moins cher »). Trois états jamais confondus : **calculé** · **non calculable** (écarté à `None` **avec son motif**) · **absent**. Les clefs restent présentes à `None` (une clef manquante se lirait comme un oubli du producteur), et `fcf_yield_pct` **traverse le tri sans être écarté** — c'est un rendement, monotone et vrai même négatif ; uniformiser la règle supprimerait une information juste. 38 assertions. | aucun (`--network none`) |
| `check_exit_debate.py` | **Sortie / calibration / débat V2** (§11/§12/A5 + §9-C, lot 9) — le seul lot où une sortie de modèle se traduit en **vente d'actions réelle**, donc le plus gros check de la suite. Pré-conditions d'ÉTAT refusées **avant** toute dépense de tokens (#40 : un état vivant seulement dans le pont fait payer un appel complet pour apprendre ce qu'on savait déjà — 409 sans ligne `failed`, contre 422 pour un pont qui juge la sortie). CHECK anti-complaisance du débat (pas de `closed_proceed` quand une invalidation est franchie), index unique partiel interdisant deux plans ouverts sur une thèse, registre prédit/réalisé. 175 assertions. | aucun (`--network none`) |
| `check_tickers_v2_listing.py` | **Route `GET /v2/tickers`** — le fil conducteur AMONT du flux V2 : elle donne à voir l'avancement de chaque ticker dans la chaîne. Shapes nulles nominales, agrégats, tri, et l'absence de fabrication d'un état « prêt » depuis des colonnes vides. 162 assertions. | aucun (`--network none`) |
| `check_knowledge_entries_listing.py` | **Route `GET /knowledge/entries/{entry_id}`** — pure, hors ligne, sans DB ni modèle : shape de réponse, champs de provenance reportés tels quels, et distinction entrée absente / entrée superseded (une entry retirée n'est pas une entry inexistante). 100 assertions. | aucun (`--network none`) |
| `check_search_worker.py` | `_apply_deterministic_overrides` face à une sortie de modèle **hostile** (source surqualifiée, score gonflé, mauvais `entry_type`, doublons, dépassement de `max_entries`, `llm_memory` non déclarée) + `classify_source_type` + extraction HTML + échec explicite sans clé de recherche. 40 assertions. | aucun (`--network none`) |
| `check_provenance.py` | `canonical_url`, `RetrievalLog` (profondeur monotone), `_verify_provenance` (rétrogradation `llm_memory` si l'URL n'a jamais été lue), `_cited_documents` (une entrée = un document), `document_search.select_relevant` (passage cible atteint, repli lexical déclaré, budget respecté), §8 `classify_source_type` confronté au plancher effectif du champ — un cabinet d'études doit pouvoir atteindre le plancher B de `marche.croissance_marche_historique`, sans que la liste réputée devienne un passe-droit (cf. convention #32). 50 assertions. | aucun (`--network none`) |
| `check_edgar_feed.py` | Alimentateur du **socle EDGAR** (postes comptables bruts, amorçage d'un ticker au corpus vide) : `select_concept` — le concept XBRL se choisit par **fraîcheur**, pas par convention (`Revenues` répond 200 pour MSFT avec un dernier point de **2010** ; `PaymentsToAcquirePropertyPlantAndEquipment` s'arrête en **2012** pour NVDA) ; garde-fou de durée (un point `fp=FY` trimestriel ne passe pas pour un flux annuel) ; alignement sur un exercice unique ; `filing_url` relisible par `cik_from_url` ; poste ou jambe de composite manquante = `unfounded`, jamais estimé ; et la **boucle refermée** — `extract_edgar_facts()` relit les specs produites. **§8 (RVMD, 3ᵉ ticker)** : une dette long terme **non déposée** n'est ni un zéro ni une raison de perdre la trésorerie du même poste composite — `long_term_debt=None` + `long_term_debt_status='aucun_concept_depose'`, cash conservé, mention dans `unfounded`. C'est #30 transposé aux composites : la famille de concepts de dette décrivait des emprunts de société mature, alors qu'un émetteur en développement se finance en **obligations convertibles** (RVMD dépose 487,4 M$ en `ConvertibleLongTermNotesPayable`). ⚠️ Le message du commit 2eff706 se trompe sur le chiffrage : à l'ancre FY2025, RVMD n'avait **pas** de dette long terme déposée (le seul point au 2025-12-31, issu d'un 10-Q, vaut 0) — les 487,4 M$ de convertibles datent du **2026-06-30**. L'enjeu du composite n'était donc pas un signe inversé mais l'assiette : sur l'ancre périmée, `levier` était simplement infondé. **§9-§10 (F4/F5)** : un poste de BILAN est daté d'un INSTANT, pas d'un exercice — le socle ne lisait que les dépôts annuels, donc il était aveugle à tout trimestre publié depuis le dernier 10-K (RVMD : trésorerie 383,7 → 815,4 M$, capitaux propres 1 631,3 → 2 606,2 M$, actif 2 354,5 → 4 323,3 M$, dette convertible 0 → 487,4 M$, sur une position **détenue**). Un instantané se reconnaît à l'absence de `start`, **jamais** à `fp` (RVMD tague `fp=Q2` un point au 2026-03-31). §10 est le corollaire trouvé EN PROD après le correctif : la clé d'identité d'un fait dépend elle aussi du type de poste — un flux vaut par `(metric, exercice)`, un stock par `metric` seul. Apparier un stock sur l'égalité des dates faisait qu'un changement d'ancre **ajoutait** la vérité sans retirer le périmé : deux capitaux propres actifs et contradictoires dans le corpus, sans aucun ratio faux pour le signaler. 77 assertions. | aucun (`--network none`) |
| `check_financials_feed.py` | Alimentateur `financials` : `extract_edgar_facts` (choix d'exercice, poste composite, capex absent = None), `build_financials_entries` (arithmétique des 4 ratios sur NVDA FY2026, fondation partielle honnête sans capex, tout en `edgar_official`), helpers EDGAR (`cik_from_url`, appariement annuel). **§6 (RVMD, 3ᵉ ticker) — un ratio valide un calcul, jamais son sens** : sur un émetteur déficitaire, FCF ÷ résultat net rend `+80,8 %` (deux négatifs), arithmétiquement exact, contrat satisfait, sens **inversé** — une entreprise qui brûle 914 M$/an était publiée en Tier A comme excellente convertisseuse de cash. `fcf_conversion_pct` devient `None`, la métrique devient `cash_burn`. Plus les libellés de `_miss` : « absent », « nul » et « non calculable » sont trois choses distinctes (un chiffre d'affaires **déposé à 0** n'est pas un intrant manquant). **§7-§8 (F4/F6)** : `extract_edgar_facts` apparie sur DEUX ancres — apparier les flux sur l'ancre de bilan les viderait tous en silence, chaque ratio devenant « non fondé » sans qu'aucune erreur ne sorte. §8 est le pendant côté SORTIE, constaté en prod : un ratio se date par les postes qui le composent. `levier` n'est fait que de postes de bilan et sortait étiqueté « FY2025 » — tous ses nombres justes, le fait faux, donc rien d'arithmétique ne pouvait le voir. Un ratio MIXTE (ROIC : flux au numérateur, bilan au dénominateur) reste licite mais le DÉCLARE, en structuré et en toutes lettres. Plus le doublon de capex : ce module et le socle EDGAR écrivaient le même fait sous deux jeux de tags (`fact` en écart), deux `capital_expenditure` FY2025 courants en même temps — l'identité d'un fait est ce qu'il MESURE, pas le vocabulaire du module qui l'écrit. 69 assertions. | aucun (`--network none`) |
| `check_synthesis_feed.py` | Alimentateur de **synthèse grounded** (ingestion-agent mode synthèse) : `derive_synthesis_reliability` (règle « un cran sous la plus faible entry citée » — jamais de surévaluation), `validate_grounding` (citation hors corpus / assertion non sourcée = violation), contrat `GroundedSynthesis` (≥1 citation/claim, union des ids), `build_content_structured` (traçabilité), registre des cibles + `citable_tiers`, et les **descripteurs agnostiques de l'émetteur** (#31) : aucune `query`/`guidance` ne nomme un acteur en dur, toutes sont paramétrées par `{company}` et `resolve()` les spécialise sans laisser de placeholder. 56 assertions. | aucun (`--network none`) |
| `check_readiness_recompute.py` | **Curator — couverture pilotée par l'index `covers`** (029) : `_tier_ge`/`_plancher_for` (plancher par champ, dégradé `croissance=B`), `_covers_index` (multi-champ, entry non taguée absente), `recompute_coverage` (le plancher MORD ; l'index DÉCOUVRE une entry que le LLM n'a pas citée ; une citation LLM sans tag ne fonde plus rien ; `produits.description` ne fonde pas `business_model.description`), `_exigences` (le LLM peut resserrer les champs requis / le plancher, jamais les desserrer), `reconcile_gaps` (bijection), et le **déterminisme** : même corpus + `fondations` LLM différentes → couverture strictement identique. Plus la **dispense par émetteur** (#31) : un ticker sans dispense écrite n'hérite d'aucun passe-droit — `recurrence_pct` bloque pour MSFT là où il est dispensé pour NVDA, et le libellé NVDA ne fuit pas dans les incertitudes d'un autre émetteur. Plus la **narration contrainte** (dette A) : une phrase du `rationale` qui nomme un verdict autre que celui recomputé est retirée et le retrait déclaré, l'en-tête factuel porte verdict + blocs + champs non fondés, et `already`/`not_ready` ne sont pas lus comme `ready`. **§15-19 = la porte de complétude à TROIS états** (capacité 4 de `02-spec-autorite-vs-actualite.md`, convention #54) : §15 `couvert` / `couvert_perime` / `non_couvert` jamais confondus, `champs_perimes` ⊆ `champs_non_fondables`, le contraste décisif étant la MÊME entry sous la MÊME ancre sur deux champs dont un seul a `actualite_bloquante` — c'est le PROFIL qui périme, pas l'âge ; `indeterminable` fait tomber le champ comme `perimee` mais son motif nomme la **vraie** cause (non datable, ou flux injoignable), les confondre ferait chercher une source plus récente là où il faut une source datable (#53) ; **§16 l'acceptation** — le même corpus, non muté (comparaison `deepcopy` avant/après), passe de `ready` à `not_ready (peremption)` à l'arrivée d'un 8-K postérieur, les champs basculés sont **exactement** les champs bloquants du profil, et la porte ne contient ni `UPDATE`, ni `INSERT`, ni `await` (grep sur le CORPS, docstrings retirées) ; §17 **deux manques, deux remèdes** — un gap de collecte ne porte jamais un champ périmé (le modèle décrirait une absence sur un champ que la base couvre), le gap de rafraîchissement est **synthétisé par le code** avec le motif nommant l'entry, et la bijection tient ; §18 `cause_non_ready` dérivée (`peremption` / `lacune` / `mixte` / `None`), portée jusqu'au rapport validé et jusqu'à l'en-tête que l'humain lit ; §19 **fixture construite** — un 8-K item 9.01 seul ne fournit aucune ancre et ne périme personne, un 6-K **sans item** en fournit une (« sans item » ≠ « sans substance »), et un assert de **discriminance** montre que la même date non filtrée périmerait bien (une copie du flux réel serait verte sans rien éprouver — `feedback_fixture_copiee_du_reel`). ⚠️ Le helper `_seul()` transforme une liste de gaps vide en gabarit : un `gaps[0]` nu tuait le script avant son bilan dans le cas négatif même que §17 existe pour attraper. ⚠️ Les entries de fixture sont **datées par défaut** — une entry sans `source_date` est `indeterminable`, donc laisser le défaut à `None` transformait en silence les 14 sections antérieures en tests d'actualité. **Éprouvé par test négatif, 6/6** : `indeterminable` traité comme fondant (2 FAIL) · `champs_perimes` non déclaré (19) · gaps du LLM non rabotés (3) · filtre des dépôts formels retiré (2) · cause figée à `lacune` (4) · retour au plancher de dimension (7) — chacun rouge sur ses asserts **nommés**, le script atteignant son bilan à chaque fois. 131 assertions. | aucun (`--network none`) |
| `check_field_profiles.py` | **Table de profils par champ** (capacité 0 de `02-spec-autorite-vs-actualite.md`, convention #50) — la doctrine des trois axes *nature · plancher · actualité bloquante* sur les 19 champs MVDD. Elle est **câblée à la porte** depuis la capacité 4 : `curator._plancher_for` la lit, et c'est ce check qui le prouve. §1 couverture, où chaque champ est vérifié **par son nom** avec un `.get()` — retirer une ligne doit produire un FAIL qui **nomme** le champ, jamais un `KeyError` qui tuerait le script avant ses autres sections ; §3 atteignabilité (#32) — un plancher qu'aucun `source_type` n'atteint est un champ infondable déguisé en lacune ; **§4 détenteur unique (#46)** — la table EST le plancher que la porte applique, et aucune SECONDE table ne subsiste dans le curator ; il vérifiait auparavant l'**accord** avec `FIELD_PLANCHER_OVERRIDES`, mais deux tables d'accord restent deux tables : c'est la seconde qui a empêché le desserrage de #50 d'atteindre la porte, et qui rendait §5 circulaire ; le plancher de dimension passé à `_plancher_for` y est volontairement **absurde** (`C`), sans quoi l'assert serait vert sur un champ que la table ne desserre pas ; **§5 tout desserrage est DÉCLARÉ**, mesuré contre le socle MVDD et non contre une table que le fichier contrôlé peut bouger — c'est ce changement d'ancrage qui a fait apparaître le desserrage B+ → B **non déclaré** de `marche.croissance_marche_historique`, tacite depuis le 2026-08-31 et invisible à l'assert écrit pour attraper les desserrages tacites ; §6 un `motif` est un **gabarit** qui ne nomme ni émetteur ni juridiction (#31), sans quoi la doctrine casse au premier émetteur non américain ; §7 aucun scalaire agrégé — la porte lira un **triplet**, trois nombres recombinés reproduiraient le défaut au premier arrondi. **Éprouvé par test négatif, 5/5** : ligne retirée · desserrage tacite · motif nommant un émetteur · profil orphelin · score composite, chacun rouge sur son assert nommé **et** le script allant jusqu'à sa ligne de bilan. 193 assertions. | aucun (`--network none`) |
| `check_entry_nature.py` | **Axe `nature` d'une entry** (capacité 1 de `02-spec-autorite-vs-actualite.md`, convention #51) — `derive_nature()` est le **détenteur unique** de la règle (#46), câblé au seul chemin d'écriture `store_knowledge`. §1 vocabulaire fermé **et atteignable** (#32) ; **§2 les deux vocabulaires**, qui sont la raison d'être du fichier : la nature d'une *entry* n'est pas la nature dominante d'un *champ* — `valorisation.base_rate_anchor` est un champ d'`interpretation` rempli par une entry `base_rate` de `mesure` (une fréquence empirique **est** relevée), et symétriquement une entry `analysis` qui couvre le champ de `mesure` `produits.unit_economics` reste une `interpretation` ; §3 `mesure` n'est **jamais** accordée par défaut (entry_type inconnu, `covers` vide, `covers` **hétérogènes**, ordre indifférent, chemin hors vocabulaire) ; §4 le `source_type` bat l'`entry_type` (`llm_memory`/`agent_synthesis` ne relèvent rien, quoi qu'ils couvrent) ; §5 l'agent peut **resserrer** vers `evenement`, jamais desserrer (#29) ; §6 détenteur unique par inspection de signature ; **§7 l'ÉTAT PERSISTÉ** (#43, pas le diff) — 0 `NULL`, 0 nature hors vocabulaire, le compte 13 lui-même asserté, puis les 13 entries déterministes RVMD **nommées une par une**. Sans `CHECK_DB_URL` le script **échoue** au lieu de sauter §7. **Éprouvé par test négatif, 5/5** ; le 5ᵉ cas est **séparé** parce qu'aucun sabotage de la *règle* ne peut rougir §7 (il lit la base) — un test négatif purement code aurait laissé §7 non prouvé. 50 assertions. | `--network coolify` + `CHECK_DB_URL` |
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
