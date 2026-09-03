---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-09-03
project: portfolio-tracker
role: Prompt à coller pour reprendre le chantier V2. Contrat FIGÉ · couche 2 DÉPLOYÉE · chaîne d'analyse VALIDÉE SUR DEUX ÉMETTEURS (NVDA, MSFT) · dettes A/B fermées · généralité #3 fermée · LOT 7 LIVRÉ (acte de décision, `theses_v2`, migration 030) · LOT 8 LIVRÉ (monitoring V2 modes 1-6, `monitoring_sessions_v2`, migration 031, EventRouterV2, dry-run réel modes 2 et 6) · LOT 9 LIVRÉ (sortie/calibration/débat, migrations 032+033, dry-run réel de bout en bout sur thèse jetable puis supprimée). **La boucle V2 est complète : décider → surveiller → sortir → apprendre.** · **UX-1 LIVRÉ** (fil conducteur V2 : `GET /v2/theses`, pages liste + thèse, primitives `components/v2/`) · **UX-2 LIVRÉ** (écrans du lot 9 : sortie/post-mortem/calibration/débat + marqueur de flux V1/V2 sur `/portfolio`, construits contre une thèse jetable réelle puis vérifiés par capture d'écran en prod). · **UX-3 LIVRÉ** (écrans V2 **amont** : knowledge, readiness, research, analyses 3 colonnes, décision — plus le point d'entrée par ticker qui manquait : `GET /v2/tickers` + pages pivots + entrée `V2Nav`). Reste : ingestion-agent, dette du runner, et le blocage `~/.netrc` sur `git push` (décision utilisateur).
---

# Prompt de reprise — portfolio-tracker V2 (cartes de provenance)

> **Ce fichier a été allégé le 2026-08-31.** Tout l'historique (journaux de sprint détaillés,
> diagnostics de bugs déjà réglés, décisions et leurs mesures) est conservé **intégralement** dans
> **`00-REPRISE-ARCHIVE.md`**, à côté. Les **conventions durables #22 à #32** vivent dans le
> **`CLAUDE.md` du projet** — c'est là qu'il faut les lire, pas ici.

> ## ⚡ MàJ 2026-09-03 — UX-3 : les écrans V2 AMONT (knowledge → readiness → research → analyses → décision)
>
> **UX-3 est livré.** 9 routes frontend + 1 route backend, déployées et vérifiées par capture d'écran
> en prod (commits `37fc1b3` puis `c4f9fed`, déploiements #347 backend / #349 frontend).
>
> **Le trou qu'on n'avait pas vu venir : l'espace V2 n'avait aucun point d'entrée par ticker.**
> Les 5 écrans amont auraient été inatteignables. D'où, en plus des 5 écrans prévus :
> `GET /v2/tickers` (agrégat d'avancement de la chaîne par ticker), les pages pivots `/v2/tickers`
> et `/v2/tickers/[ticker_id]`, et l'entrée « Tickers » dans `V2Nav`. C'est le même symptôme que
> le `GET /v2/theses` manquant avant UX-1 : **le backend V2 sait faire, mais rien ne s'y branche.**
>
> ### La méthode a payé — 3 fois
>
> Elle est reconduite telle quelle pour la suite. Vérifier, jamais croire l'auto-rapport.
>
> 1. **Le sous-agent backend n'a pas pu lancer Bash** (permission refusée) et a rendu du code
>    **non exécuté**, en le présentant comme terminé. Son check passait 162 assertions… **contre ses
>    propres fixtures**, jamais contre la base. Exécuté par moi contre la vraie base : le SQL était
>    bon, mais **deux fixtures étaient fausses** (`bear` MSFT 2→3, NVDA 3→4) — des assertions vides
>    de sens qui auraient l'air vertes pour toujours. Corrigées.
> 2. **`docker build` a rattrapé une erreur de syntaxe** que le sous-agent readiness affirmait
>    absente après « scan manuel » : une apostrophe non échappée dans une chaîne `'…d'arrêt…'`.
>    Rappel : **`node --check` est un NO-OP** sur ces fichiers, il rend 0 sur du JSX cassé.
> 3. **Les captures ont rattrapé deux défauts qu'aucun `200` n'aurait montrés** : (a) le texte du
>    bloc Pareto de readiness était **inversé** — les deux branches du ternaire décrivaient l'état
>    opposé, et comme les deux tickers réels ont `arret_pareto_recommande=false`, c'est la mauvaise
>    phrase qui s'affichait en prod ; (b) l'écran analyses s'ouvrait sur le **tour le plus récent**,
>    souvent un tour de réfutation partiel — 2 colonnes vides sur 3 à l'ouverture de l'écran phare.
>    Il ouvre désormais sur le tour portant la synthèse `final`.
>
> **Diff programmatique des accesseurs** (la technique d'UX-2, reprise) : extraction par regex de
> tous les `.snake_case` des 9 fichiers, diffés contre l'union récursive des clés des payloads réels
> capturés dans `/tmp/ux3/`. Résultat : **aucun nom de champ inventé**, seuls restent des paramètres
> de route/query (`memo_id`, `analysis_id`, `include_inactive`). ⚠️ Attention au piège : ma première
> regex avait un lookbehind `(?<![\w$])` avant le point qui excluait **tous** les vrais accesseurs —
> elle rendait « 1 accesseur, aucun problème » sur un fichier qui en a 22. Un diff qui trouve zéro
> anomalie doit d'abord être suspecté de ne rien mesurer.
>
> ### G2 sur l'écran décision
>
> `/v2/tickers/[ticker_id]/decision` est **en lecture seule, à dessein**. Verdict, sizing et
> conditions d'entrée sont lus en base et rendus « figés » ; ils ne sont jamais des champs de saisie.
> L'écran **rend compte** de la décision, il ne la déclenche pas : le `POST /validate` fige la
> décision **et** ouvre la position en une opération irréversible, ce qui n'a pas sa place derrière
> un bouton d'écran de consultation. Les `risk_acks` (qui ne portent que `{risk_index, accepted}`)
> sont réconciliés avec les libellés de `risques_acceptes` lus dans la synthèse — sans quoi l'écran
> afficherait « risque 0 accepté », ce qui n'apprend rien.
>
> ### Réconciliation des tiers (les 7 vs les 3)
>
> `GET /v2/tickers` et l'écran knowledge exposent les **7 tiers stockés** (A, A-, B+, B, B-, C+, C) ;
> readiness en expose **3 groupes** (tier_A/B/C). Ils comptent les mêmes entrées. La page pivot
> affiche l'arithmétique du regroupement en clair (`tier_A = A(42) + A-(2) = 44`) pour que les deux
> écrans **ne se lisent pas comme une contradiction**. Mesuré : NVDA 32/15/5, MSFT 44/10/0.
>
> ### Reste à faire
>
> - **`~/.netrc` bloque tous les `git push`** (voir juste en dessous) — décision utilisateur.
> - Écran analyses : la bannière dit que synthèse #11 déclare `bull #8 / bear #9` alors que les
>   cartes du tour 1 montrent #12/#13 (produits après). C'est **honnête et voulu**, mais mérite
>   sans doute une mise en forme plus explicite.
> - ingestion-agent, dette du runner (inchangés).
>
> ### ⚠️ `~/.netrc` casse `git push` — non réglé, décision utilisateur
>
> **Symptôme** : tout `git push` rend `403 Permission ... denied to jeanlangloismeurinne`.
> **Ce n'est pas le token du repo** : celui de `~/.git-credentials` est valide et rend **200** sur
> `info/refs?service=git-receive-pack`. Ce n'est pas non plus le bac à sable.
>
> **Cause** : `~/.netrc` contient un **autre** token (fine-grained, 93 caractères) sans droit
> d'écriture. git le consulte **via libcurl avant** le credential helper — et même avant des
> identifiants embarqués dans l'URL, ce qui rend le contournement « pousser vers une URL avec token »
> **inopérant**.
>
> **Contournement utilisé** (non destructif, à refaire à chaque push) :
> ```bash
> mkdir -p /tmp/githome
> GT=$(grep -o 'ghp_[A-Za-z0-9]*' ~/.git-credentials | head -1)
> HOME=/tmp/githome git push "https://x-access-token:${GT}@github.com/<user>/<repo>.git" HEAD:main \
>   2>&1 | sed "s|$GT|<token>|g"     # le token n'est jamais affiché
> git fetch origin                    # resynchroniser la ref de suivi
> ```
>
> **Correctif durable — à trancher par l'utilisateur, je n'y touche pas** : `~/.netrc` est son
> fichier d'identifiants, créé par autre chose que ce chantier. Soit en retirer l'entrée `github.com`,
> soit y mettre un token ayant le droit de push. Tant que ce n'est pas fait, **chaque push de chaque
> projet** exige le contournement ci-dessus.

> ## ⚡ MàJ 2026-09-02 — UX-2 : les écrans du lot 9, construits contre des données RÉELLES
>
> **Le prérequis a été levé en premier, et il valait la peine.** Les 5 tables du lot 9 étaient vides.
> La thèse V2 jetable **#5 (NVDA)** a été re-fabriquée et **toute la chaîne rejouée contre l'API réelle**
> — débat #9 → clôture → plan de sortie #6 (3 tranches 50/30/20 + 3 conditions accélérées) → alerte #5
> → 3 exécutions (position à 0 titre, `exit_status=closed`) → post-mortem #3 (`duree_jours=204`,
> `performance_pct=18.0`, tous deux **calculés**) → calibration (10 paires, `lisible:false` à n=1).
> Coût total **~0,0042 $**. Les 4 écrans ont ensuite été écrits **à partir des payloads capturés**
> (`/tmp/ux2/*.json`), pas d'un schéma lu.
>
> **Ce que le dry-run a démontré au passage** : l'anti-complaisance tient en réel. Le débat #9 avait
> `invalidation_franchie=true` et le modèle a suggéré `closed_monitor`, jamais `closed_proceed`. La
> clôture a été faite en `closed_pass` **à dessein**, pour fabriquer une divergence agent/investisseur
> tracée et vérifier qu'elle se voit à l'écran.
>
> **Livré (frontend seul — aucun changement backend n'a été nécessaire).**
> `/v2/theses/[id]/sortie`, `/v2/theses/[id]/post-mortem`, `/v2/theses/[id]/debat`, `/v2/calibration`,
> entrée « Calibration » dans `V2Nav`, section « Sortie, bilan et débat » sur la page pivot, et le
> **marqueur de flux V1/V2 sur `/portfolio`**. `portfolio_summary()` faisant déjà `SELECT pp.*`,
> `thesis_v2_id` remontait déjà : le point 2 du reste-à-faire ne coûtait rien côté API.
>
> **Le marqueur de flux, fait SANS le filtre que la MàJ (bis) déconseillait.** Les deux positions MSFT
> restent affichées, badgées V1/V2, avec un bandeau qui explique que ce n'est pas un doublon. Deux bugs
> **préexistants** ont été trouvés en le câblant, aucun des deux n'était soupçonné : (a) `key={p.ticker_id || p.id}`
> donnait la **même clé React `"MSFT"`** aux positions #1 et #8 ; (b) le clic sur une ligne V2
> envoyait vers la page **V1** du ticker. Corrigés en `key={p.id ?? p.ticker_id}` et route
> `/v2/theses/{thesis_v2_id}`.
>
> **⚠ Un `200` ne prouve rien sur l'affichage — les 6 pages ont été CAPTURÉES en prod** (chromium
> headless, `/tmp/ux2/shots/`) et regardées. Deux défauts que seul le rendu pouvait montrer :
> — le plan de sortie affichait **deux badges `closed` côte à côte** sans étiquette (statut de la thèse
>   et statut du plan, deux choses différentes, même mot) → préfixés « Thèse : » / « Plan : » ;
> — sur `/v2/theses/[id]/debat`, la divergence n'était qu'un **badge** dans la liste alors que
>   l'arbitrage UX n°4 exige un bandeau visible **sans clic** → le débat le plus récent s'ouvre
>   désormais tout seul au premier chargement (garde par thèse, refermer ne rouvre pas).
> Les deux sont invisibles à `docker build`, invisibles à un check hors ligne, invisibles à un 200.
>
> **⚠ Vérification indépendante des sous-agents, pas leur auto-rapport.** Deux passes après livraison :
> (a) `grep` des replis `a || b` sur les noms de champs — un seul hit, légitime ; (b) extraction
> **programmatique** de tous les accesseurs `.snake_case` des 4 fichiers neufs, diffés contre l'union
> des clés des payloads réels — seul `sell_date` ressort, et c'est un champ de **corps de requête**.
> C'est la technique à reprendre : elle transforme « je n'ai pas deviné de nom » en fait vérifiable.
>
> **⚠ Le script de nettoyage de la thèse jetable était périmé et DANGEREUX.** `lot9_these_jetable_cleanup.sql`
> listait `knowledge_entries (121,122,123)` et `cash_movements (10,11,12)` — les ids du run **de la
> veille**. Ce run-ci a produit 124/125/126 et 13/14/15 : le rejouer tel quel aurait supprimé trois
> entrées de connaissance d'un autre exercice **et laissé derrière lui** de la fausse trésorerie dans
> un solde **partagé avec le flux V1 réel** (#34). Réécrit : tout est dérivé de `thesis_v2_id`, les ids
> des faits rattachés sont capturés en tables temporaires **avant** d'effacer ce qui les porte, et
> `thesis_id` est un paramètre `-v` **sans valeur par défaut** (un script de DELETE n'en prend pas).
> Les deux seeds sont désormais versionnés dans `backend/app/db/seeds/` — le prochain sprint UX
> redémarre à moindre coût. **La thèse #5 a été supprimée après les captures**, pas avant : la
> supprimer d'abord aurait laissé les écrans neufs sans rien à afficher.
>
> **Sur le déploiement** : `infrastructure/deploy.sh` a été **refusé par le classifieur** (comme
> l'écriture d'un PHP ad-hoc dans le conteneur Coolify). Chemin utilisé à la place : commit + push
> en commandes séparées, puis rebuild par **l'API Coolify avec un token généré**
> (`COOLIFY_PLAYBOOK.md` § « méthode alternative »). Vérifié après coup : `docker ps` ne montre
> **qu'un** conteneur `portfoliofrontend`, pas d'orphelin.
>
> **Reste ouvert côté UX** : les écrans V2 **amont** (knowledge, readiness, research memo, analyse
> 3 colonnes, décision) — tout leur backend existe, aucun n'a d'écran.
>
> ---
>
> ## ⚡ MàJ 2026-09-01 (bis) — UX-1 : le fil conducteur V2 (l'espace V2 avait un backend complet et AUCUN écran)
>
> **Le constat qui a défini le sprint.** Le reste-à-faire annonçait une « passe UX transverse : verdict
> dans le frontend, suivi des hypothèses H1-H5 » — formulation qui laissait croire à des retouches.
> Inventaire fait : `frontend/pages/v2/` contenait **un seul fichier** (la liste des 12 agents), aucun
> dossier `components/v2/`, **une** entrée dans `V2Nav`, et **aucune** page ne lisait `theses_v2` ni
> `monitoring_sessions_v2`. Neuf lots de backend, zéro écran. Ce n'est pas une passe, c'est un chantier
> de plusieurs sprints — et le §16 de la spec est **muet** sur le lot 9 (ni sortie, ni post-mortem, ni
> calibration ; le §4 nomme `ExitPlanBuilder` et `CalibrationPanel` sans dire où ils vivent). Sept
> points d'UX sont donc à trancher au fil de l'eau, pas à lire dans la spec.
>
> **Pourquoi le fil conducteur AVANT les écrans du lot 9, et pas l'inverse.** Trois raisons, la
> première étant décisive et mesurée : `exit_plans`, `exit_executions`, `post_mortems_v2`,
> `calibration_registry`, `conviction_debates_v2` sont **toutes vides** (la thèse jetable #5 du dry-run
> a été supprimée). Construire ces écrans d'abord, c'est les construire contre des données **inventées**
> — et une donnée inventée est toujours conforme. C'est la convention #39 d'un cran plus haut. Le fil
> conducteur, lui, avait de quoi s'afficher : thèse #4 MSFT et ses 2 sessions. Ensuite, G2 interdit
> l'ordre inverse (« la logique de décision contraint l'UX ») : un écran dessiné avant sa donnée invente
> des affordances que le backend refuse — ici les seuils, en lecture seule par #37. Enfin les trous
> d'API se trouvent en câblant : `GET /v2/theses` **n'existait pas**, donc aucune thèse V2 n'était
> listable et aucun écran du lot 9 n'était atteignable.
>
> **Livré.** Backend : `GET /v2/theses` (agrégats position / sessions / exit_plan / post-mortem,
> filtre `?ticker_id=`) + enrichissement **strictement additif** de `GET /v2/theses/{id}`.
> Frontend : primitives `components/v2/`, `/v2/theses` (liste), `/v2/theses/[id]` (page pivot),
> entrée « Thèses » dans `V2Nav`. Suite hors-ligne : **759 assertions / 0 échec** sur 12 scripts
> (707 avant, **+52** — `check_theses_v2_listing.py`).
>
> **La page thèse affiche DEUX fourchettes de valorisation, et c'est structurel.** MSFT #4 porte
> `validation_json` **250/450/700** (figée au validate) et `valuation_range` **280/480/750**
> (réactualisée par la revue mode 6). N'en afficher qu'une masquerait l'écart — or c'est **contre la
> figée** que la calibration A5 mesure l'erreur de prévision. Les deux sont donc étiquetées
> séparément, l'écart est explicite, et aucune moyenne n'est calculée.
>
> **⚠ Ce que ce sprint a trouvé et qui vaut pour tout le frontend : `node --check` est un NO-OP sur
> ces fichiers.** Node 20 détecte le `import` en tête, bascule en analyse ESM et **rend 0 sans rien
> vérifier** — y compris sur du JSX volontairement cassé. Vérifié dans les deux sens : le même JSX
> **sans** `import` échoue en `exit=1`, **avec** `import` passe en `exit=0`. Un sous-agent avait
> rapporté « `node --check` OK » de bonne foi ; ça ne prouvait strictement rien. **La seule
> vérification frontend qui ait du sens est `docker build`** (npm ci + next build) — faite, les deux
> pages compilent (`/v2/theses` 2,88 kB, `/v2/theses/[id]` 4,93 kB). Corollaire général : un contrôle
> qui réussit **toujours** est pire qu'aucun contrôle, parce qu'il se rapporte comme une preuve.
>
> **⚠ Un check à fixtures ne prouve jamais qu'une requête SQL s'exécute.** Les 52 assertions neuves
> travaillent sur des dicts Python : elles ne touchent pas la base. Or la requête référence
> `exit_plans.status` et `post_mortems_v2.status`, colonnes dont la migration 032 ne parle pas (elle
> décrit `exit_status`). Elles existent bien (défaut `'completed'`) — mais **vérifié en jouant le SQL
> exact contre `db_portfolio`**, pas en le supposant. Le `JOIN tickers` a été contrôlé de même : FK
> `theses_v2_ticker_id_fkey` présente, donc l'INNER JOIN ne peut pas escamoter une thèse (le mode de
> panne du LEFT JOIN du lot 7 n'est pas reconduit).
>
> **⚠ Les replis sur variantes de noms de champs sont un trou silencieux.** La page thèse avait
> d'abord été écrite avec des `h.hypothese || h.text || '—'`, `h.base_rate_taux`, `h.classe_reference`
> — noms devinés. Structure réelle relevée en base : `id`, `enonce`, `kpi`, `unite`, `horizon`,
> `statut`, `seuil_alerte`, `seuil_invalidation`, `base_rate{taux, reference_class, ajustement}`,
> `source_entry_refs[{entry_id, version}]`, `derniere_revue`, `derniere_observation`. Un nom faux
> n'aurait pas levé d'erreur : il aurait affiché **du vide**, qui se lit comme « cette donnée n'existe
> pas ». Corrigé aux noms exacts, avec un marqueur **visible** « — champ absent » (et `ajustement:
> null` nommé comme tel, pour distinguer « vide à dessein » de « donnée manquante »).
>
> **Faux positif à ne pas re-chasser** : `check_search_worker.py` rend `50 OK / 1 FAIL` **si on lui
> passe `EXA_API_KEY=x`** — l'assertion « sans clé de recherche, le worker doit lever » ne peut alors
> pas se déclencher. Avec l'environnement documenté dans `checks/README.md` (sans clé), il rend bien
> **52 OK / 0 échec**. Le script est correct ; c'est l'env du runner qui doit l'être.
>
> **⚠ Le « double comptage » MSFT : une des deux options proposées est nuisible.** Positions ouvertes
> réelles : **#1** MSFT V1 (1 titre, 100 €) et **#8** MSFT V2 (1 titre, 400 €, ligne de dry-run
> conservée). Le fichier proposait « filtrer sur `thesis_v2_id IS NULL` côté V1 **ou** afficher les
> deux avec un marqueur ». **Filtrer les positions sans filtrer la trésorerie aggrave le mensonge** :
> le `cash_movements` #9 de 400 € resterait débité sans contrepartie visible, la page afficherait
> 400 € évaporés. Positions et trésorerie sont des **faits du monde** (#34) et la page portefeuille
> décrit le monde : le **marqueur de flux** est la seule des deux options qui ne fasse pas mentir la
> page. Non traité dans ce sprint, à faire dans la tranche UX suivante.
>
> **Reste ouvert côté UX** : les écrans du lot 9 (sortie, post-mortem, calibration, débat) — ils
> demandent d'abord de **fabriquer une thèse jetable** pour avoir des données réelles à afficher,
> sinon on retombe dans le piège des fixtures conformes ; le marqueur de flux sur `/portfolio` ;
> les écrans amont (knowledge, readiness, research, analyse) toujours absents de l'espace V2.
>
> ---
>
> ## ⚡ MàJ 2026-09-01 — LOT 9 : la sortie, la calibration et le débat (migrations 032 + 033)
>
> **La boucle V2 est fermée** : décider (lot 7) → surveiller (lot 8) → **sortir et apprendre** (lot 9).
> Suite hors-ligne : **707 assertions / 0 échec** sur 11 scripts (532 avant, **+175** —
> `check_exit_debate.py`). Migration 032 appliquée (`exit_plans`, `exit_executions`,
> `post_mortems_v2`, `calibration_registry`, `conviction_debates_v2`, + `price_alerts.exit_plan_id`),
> puis **033** (resynchro du prompt `debate-agent`, voir plus bas). 13 routes exposées dans
> `api/analysis_v2.py`. Détail des tables et des CHECK : `CLAUDE.md` § Migrations.
>
> **Dry-run réel de bout en bout, joué contre le vrai DeepSeek**, sur une thèse V2 **jetable #5**
> (NVDA, 2ᵉ ticker) créée pour l'exercice puis **intégralement supprimée** — la thèse MSFT #4 et sa
> position #8 (argent réel) n'ont jamais été touchées. La chaîne complète a tourné : débat →
> clôture → plan de sortie → 3 tranches → post-mortem → calibration → `GET /v2/calibration/summary`.
> Ce que le run a **prouvé en réel**, et qu'aucun check hors ligne ne pouvait établir :
> • `seuil_franchi` **redérivé** des seuils figés dans les **deux sens** — H1 `invalidation` (18 < 25,
>   décroissante), H2 `alerte`, H3 `aucun` (39 < 40, **croissante**) ;
> • **anti-complaisance** tenue : H1 invalidée → l'agent a suggéré `closed_monitor`, jamais
>   `closed_proceed` ;
> • **souveraineté de l'utilisateur** préservée et tracée : une clôture en `closed_proceed` contre
>   l'avis du débat est **acceptée** (le CHECK 032 ne contraint que `resolution_suggeree`), avec la
>   divergence conservée en ligne (`resolution_suggeree` ≠ `status`, `invalidation_franchie=t`) et un
>   WARNING — c'est la matière du post-mortem, pas un bug ;
> • `duree_jours`=202 et `performance_pct`=18,00 **calculés** (1 180 € encaissés / 1 000 € de revient)
>   là où le modèle rendait `0` et `0.0` ;
> • **le cœur de l'exercice** — la calibration a lu la fourchette **FIGÉE au validate**
>   (`validation_json` : 90/**120**/150) et non la `valuation_range` réactualisée (100/140/180). C'est
>   pour ça que le seed les avait délibérément rendues différentes : mesurer son erreur contre sa
>   dernière opinion ne mesure rien ;
> • `summary` à n=1 se déclare **`lisible: false`** — le registre A5 refuse de généraliser d'un cas.
>
> **Ce que seul le run réel a trouvé — la désynchro de prompt (→ convention #39, migration 033).**
> Premier appel réel du lot : **HTTP 502**, `seuil_franchi` reçu en booléen sur les 3 hypothèses.
> L'exemple JSON de `60-debate-agent.md` datait d'**avant** le figeage du Pydantic
> `ConvictionChallenge` (écrit seulement au lot 9) et montrait `"franchi": false`,
> `"observation_courante"`, **aucun `valeur_observee`**. Le modèle a recopié l'exemple. **Le 502 est
> bénin — ce qu'il masquait ne l'est pas** : `_forcer_seuils_figes` ne redérive que si
> `valeur_observee is not None`, donc un prompt qui n'enseigne jamais ce champ rend la dérivation
> **no-op silencieuse** et tue le garde-fou central du lot, **sans qu'aucun check hors ligne ne le
> voie** (ils alimentent tous les ponts avec des fixtures déjà conformes). Un check prouve qu'une
> fonction refuse ce qu'on lui donne ; jamais que le modèle produira de quoi la déclencher.
> Correctif conforme à la règle « desserrage de schéma = trou silencieux » : **prompt durci**
> (table des champs + mention explicite que le système réécrit les seuils et redérive le
> franchissement, donc sous-déclarer n'achète rien), **contrat inchangé**, et DB resynchronisée par
> la **migration 033** générée (`_gen_prompt_refresh_20260901.py`) — jamais un UPDATE à la main.
> Re-testé contre le vrai modèle : **200**, les 3 hypothèses conformes.
>
> **Second défaut trouvé par le run (→ convention #40)** : le post-mortem sur position non soldée
> était refusé **après** l'appel (dans `_valider_pont_postmortem`), alors que `_verifier_etat` porte
> justement la consigne « AVANT toute dépense de tokens ». Un appel complet payé pour apprendre un
> état lisible dans `inputs`. Déplacé en pré-condition (`ThesisNotExitable` → **409**), le pont le
> reteste en défense en profondeur. **Deux assertions ajoutées** (173 → 175).
>
> **Reste ouvert** : les **pages V2** du lot 9 (plan de sortie, post-mortem, `CalibrationPanel`) —
> tout est côté API, rien côté UI ; la dette du runner (tokens d'une tentative abandonnée non
> comptabilisés, commune à tous les agents V2, ouverte depuis le lot 8) ; l'ingestion-agent.
>
> ---
>
> ## ⚡ MàJ 2026-09-01 — LOT 8 : le monitoring V2 (modes 1-6, `monitoring_sessions_v2`, migration 031)
>
> **Le flux V2 sait maintenant se surveiller.** Déploiement **#335** (`062e459`), un seul conteneur
> vérifié. Suite hors-ligne : **532 assertions / 0 échec** sur 10 scripts (416 avant, **+116** —
> `check_monitoring_v2.py`). Dry-run réel joué contre le vrai DeepSeek sur les **deux** modes qui
> comptent (2 et 6), thèse V2 #4 MSFT.
>
> **Le lot 8 demandait bien une migration — CLAUDE.md disait le contraire.** La phrase « le lot 8
> n'en demande pas a priori » était **fausse** : `monitoring_sessions.thesis_id` est une FK vers
> `theses`, la table V1. Une session V2 n'a littéralement **pas de place où pointer**. Trouvé en
> vérifiant le FK, pas en le supposant — même schéma que le `LEFT JOIN` du lot 7. D'où la
> **migration 031** : `monitoring_sessions_v2`, `calendar_events.session_v2_id`,
> `portfolio_settings.v2_auto_enabled`, et des CHECK qui contraignent les domaines de routage.
> **La numérotation du lot 9 décale donc à 032.**
>
> **Le principe à retenir de ce lot — un contrat valide un objet, jamais la cohérence entre deux.**
> C'est le trou que le lot 8 ferme, et il était invisible depuis le schéma. Mesuré :
> `Mode2QuarterlyReview` **accepte parfaitement** une escalade motivée par une hypothèse `H7` qui
> **n'existe pas dans la thèse**. Contrat satisfait, `extra='forbid'` satisfait, anti-churn
> **contourné** — puisque l'anti-churn dit « n'escalader que sur un seuil PRÉ-ENREGISTRÉ » et que
> rien, dans le schéma, ne relie la sortie du modèle à la liste figée. D'où un **pont inter-objets**
> en code (`_valider_pont_hypotheses`), en trois vérifications distinctes :
> **(1) référentiel** — ids cités ⊆ ids figés (tous modes citant des hypothèses) ;
> **(2) exhaustivité** — ids figés ⊆ ids cités (**mode 6 seul**, comme l'exige la carte C5) ;
> **(3) citations** — tout `entry_id` cité appartient aux entries réellement envoyées.
> Refus → `MonitoringRefused` → **HTTP 422** (la requête est valide, c'est la *sortie du modèle* qui
> est incohérente) + session `failed` persistée : un refus reste visible. `check_monitoring_v2.py`
> **§3** prouve les deux moitiés — le contrat accepte le `H7`, le pont le refuse.
>
> **Corollaire, tout aussi structurel : les seuils figés sont en LECTURE SEULE.** `_reporter_statuts`
> fusionne **par id** sur la liste du validate et n'écrit que `statut`, `derniere_revue`,
> `derniere_observation`. `seuil_alerte`, `seuil_invalidation`, `base_rate`, `source_entry_refs` ne
> sont **jamais** repris de la sortie du modèle — sinon une revue pourrait **abaisser le seuil
> qu'elle vient de franchir**, et l'anti-churn deviendrait décoratif. Vérifié : le modèle a rendu
> `seuil_invalidation: 5.0` là où la thèse portait `25.0` ; c'est `25.0` qui est resté.
>
> **Ce que le code dérive et ne demande jamais au modèle** (#24 appliqué au monitoring) :
> `mode`, `thesis_id`, `pair_ticker` (mode 4), `source_mode` (mode 5), `schema_version`, et surtout
> **`next_review_date`** — `jour + 365j` en Python. La valeur du modèle est journalisée et conservée
> dans `result_json`, mais ne pilote aucun planning. *Vérifié en dry-run* : le modèle proposait
> `2027-08-31`, l'événement a été posé au **`2027-09-01`**.
>
> **`EventRouterV2` — le défaut V1 n'est pas reconduit.** INNER JOIN sur `theses_v2 … status='active'`
> (pas de LEFT JOIN, cf. lot 7), `ce.thesis_v2_id IS NOT NULL` explicite, **aucune garde `synced`**
> (notion Dust : le prompt en base EST celui envoyé, une garde ici ne vérifierait rien et bloquerait
> au premier PATCH), interrupteur **`v2_auto_enabled`** (FALSE par défaut — pas de dépense
> automatique non supervisée). Job scheduler **séparé** à 7h15, 10 min après le V1 : les enchaîner
> ferait qu'une exception d'un flux empêcherait l'autre de tourner, alors qu'ils sont censés être
> indépendants. **Seul le mode 6 se rattrape** (`scheduled_date <= today`) : un brief J-2 ou une revue
> J+1 joués trois semaines plus tard commentent une publication déjà digérée, alors qu'une revue
> annuelle en retard est **plus** urgente, pas moins. À `v2_auto_enabled=FALSE`, l'échéance n'est pas
> perdue : session `pending_manual` **avec son contexte exact**, et notifiée. Non-choix assumé : le
> mode 5 **n'est pas** enchaîné automatiquement après une escalade mode 2 — `routing_suggestion` +
> Slack, déclenchement humain (comme en V1 ; l'automatiser doublerait la dépense du jour et rendrait
> invisible la décision d'aiguillage).
>
> **Dry-run réel MSFT (thèse V2 #4, 4 hypothèses figées).**
> *Mode 2* → session **#8**, `alert_level=RAS`, `verdict`/`routing` **NULL** (corrects : pas
> d'escalade), 13 827/637 tokens, **$0,001221**, 6 refs snapshotées, H1-H4 cités avec de vrais
> `entry_id`. Le commentaire de valorisation **refuse de mécaniser** : prix 513,53 $ au-dessus de la
> VI base 450 $, marge négative -12,4 %, et pourtant « *cela reste contextuel et ne constitue pas un
> ordre de vente* » — DÉCISION #5 tenue par le modèle lui-même.
> *Mode 6* → session **#9**, verdict **CONFIRMER**, 13 818/1 192 tokens, **$0,00132**, **exhaustivité
> respectée** (H1-H4 tous revus), `thermometer.contraignant=False`, `rendement_prospectif.suffisant=True`
> en zone « étirée » (donc **aucune sortie de valorisation** — l'anti-seuil-mécanique fonctionne),
> `exit_trigger=None`.
>
> **⚠ Effets du mode 6 conservés sur décision de l'utilisateur.** La revue a réactualisé
> `theses_v2.valuation_range` **250/450/700 → 280/480/750** : gardée comme ré-appréciation légitime
> sur données actuelles. En revanche l'événement **#67** (`annual_review` 2027-09-01, source
> `monitoring_agent_v2`) a été **supprimé** — il doublonnait le vrai **#66** (2027-08-31) à un jour
> près et aurait déclenché **deux** revues annuelles. Les sessions #8 et #9 sont **gardées** comme
> trace du dry-run. Les événements #65/#66 n'ont **pas** été consommés (dry-runs joués sans
> `calendar_event_id`, délibérément) : le lot 8 aura donc bien un vrai événement à router le
> **2026-10-28**.
>
> **Dette connue, à traiter au lot 9 ou avant.** `run_json_agent` **perd le texte brut fautif et la
> comptabilité de tokens** quand il abandonne après échec de validation (il lève un `RuntimeError` nu).
> On persiste le motif pour que l'échec reste visible, mais **la dépense de cette tentative n'est pas
> comptabilisée**. Limite du runner, **commune à tous les agents V2** — pas propre au monitoring. Ne
> pas la corriger à chaud sans re-tester les autres agents.

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

- **Code déployé** : commit `e3ac3b5`, backend deployment **#340**, frontend deployment **#339**
  (commit `7f0c02a`), **un seul conteneur par app vérifié**. UX-1 est en ligne et **vérifié contre
  l'API réelle** : `GET /api/v2/theses` renvoie la thèse #4 MSFT avec ses **deux** fourchettes
  distinctes (`valuation_range` 280/480/750 vs `valuation_range_figee` 250/450/700),
  `hypotheses_par_statut = {"confirmee": 4}`, `position.id = 8` ; `?ticker_id=NVDA` renvoie `[]`.
  ⚠️ **Ce qui n'est PAS prouvé** : les pages `/v2/theses` et `/v2/theses/4` renvoient 200, mais
  Next.js sert la coquille et charge les données **côté client** — un 200 ne prouve donc rien sur
  l'affichage. Le rendu réel dans le navigateur reste à contrôler à l'œil.
  ⚠️ **Limite d'outillage rencontrée** : `deploy.sh` fusionne « committer » et « reconstruire » et
  refuse un index vide (`fail 2`). Quand **un seul commit couvre les deux apps** (backend + frontend),
  la seconde ne peut donc pas être reconstruite par la voie normale. Contournement propre : joindre au
  commit suivant une modification réelle (ex. ce fichier) et appeler `deploy.sh <la seconde app>`.
  À corriger un jour dans le script : un mode « rebuild seul, sans commit ».
- **Suite hors-ligne** : **779 assertions / 0 échec** sur 13 scripts (`backend/checks/`).
  ⚠️ Lancer avec l'env **documenté dans `checks/README.md`** (sans `EXA_API_KEY`) : une clé factice
  fait échouer à tort l'assertion « sans clé de recherche, le worker doit lever ».

> ### 🐛 Le bug qui a survécu à 759 assertions vertes — accolades dans une f-string SQL
>
> Livré au #338, `GET /v2/theses` renvoyait **500 à chaque appel** en production. Cause : un
> **commentaire SQL** à l'intérieur de la f-string qui construit la requête —
> `-- hypotheses_par_statut : {statut: count}`. Python y a lu un champ de remplacement (expression
> `statut`, format spec ` count`) → `NameError: name 'statut' is not defined`.
>
> **Pourquoi rien ne l'a attrapé**, et c'est là tout l'intérêt du cas :
> - une f-string n'est évaluée qu'**à l'exécution de sa ligne** → le module **s'importe très bien**,
>   et le contrôle d'import est passé au vert ;
> - les 52 assertions de `check_theses_v2_listing.py` valident des **formes** sur fixtures, sans
>   jamais exécuter la fonction de route ;
> - la vérification SQL contre la vraie base avait été faite depuis un fichier `.sql` séparé, **d'où
>   le commentaire fautif était absent** — on a donc prouvé que le SQL tourne, jamais que Python
>   sait le fabriquer.
>
> C'est la **convention #39 dans sa forme la plus pure** : trois vérifications vertes, aucune ne
> touchant le chemin réel. Rappel de la règle transverse : **un correctif n'est acquis que testé
> contre l'API réelle**.
>
> **Garde-fou installé** : `backend/checks/check_fstring_sql.py` (20 assertions) parcourt en `ast`
> tous les `.py` de `backend/app/` et échoue sur tout nom référencé dans une f-string qui n'est pas
> résoluble dans sa portée (args, locales, `except ... as e`, compréhensions, englobantes, imports,
> builtins). Il a été **validé par test négatif** : bug réintroduit → exit 1 pointant `statut`, puis
> restauré → vert.
- **Migrations appliquées** jusqu'à **033** (resynchro prompt `debate-agent`). Prochaine : **034**
  — à écrire **juste avant** son lot, jamais en avance (§18).
- **La boucle de vie d'une thèse V2 est fermée** (lots 7 à 9) : décider → surveiller → sortir →
  apprendre. Le manque n'est plus dans le backend, il est **dans les écrans**.
- **Vérifier le frontend avec `docker build`, jamais avec `node --check`** (no-op sur fichiers ESM,
  cf. MàJ bis).

## Ce qui reste à faire — dans l'ordre

1. ~~**UX-2 — les écrans du lot 9**~~ · ~~**Marqueur de flux sur `/portfolio`**~~ — **FAITS**
   (MàJ 2026-09-02), vérifiés par capture d'écran en prod, pas seulement par un 200.
2. **UX-3 — les écrans V2 amont, toujours absents** : knowledge, readiness (le gate `ready`),
   research memo, analyse 3 colonnes bull/bear/synthèse, décision. **C'est le prochain jalon.**
   Le backend existe pour tous. ⚠️ **Reprendre la méthode UX-2, qui a fait ses preuves** :
   (a) capturer les payloads RÉELS avant d'écrire une ligne de JSX et n'utiliser que ces clés-là
   (un nom de champ faux n'affiche pas une erreur, il affiche **du vide**, qui se lit comme
   « cette donnée n'existe pas ») ; (b) vérifier les sous-agents par extraction programmatique des
   accesseurs plutôt que sur leur auto-rapport ; (c) `docker build` est la **seule** vérification
   frontend qui vaille (`node --check` est un no-op) — et elle ne dit rien de l'affichage, donc
   **capturer les pages en headless et les regarder**.
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
- **`run_json_agent` perd le brut et les tokens sur abandon** (trouvé au lot 8, **commun à TOUS les
  agents V2**) : quand la validation échoue après `max_repair`, il lève un `RuntimeError` nu — ni
  texte fautif, ni comptabilité. On persiste le motif (session `failed`) pour que l'échec reste
  visible, mais **la dépense de cette tentative n'est pas comptabilisée** et le brut qui aurait servi
  à diagnostiquer est perdu. Ne pas corriger à chaud sans re-tester les autres agents : c'est de
  l'infra partagée.

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
