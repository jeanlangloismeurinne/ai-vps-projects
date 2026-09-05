---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-09-05
project: portfolio-tracker
role: >
  Prompt à coller pour reprendre le chantier V2 (cartes de provenance). Contrat FIGÉ · couche 2
  DÉPLOYÉE · boucle V2 complète (décider → surveiller → sortir → apprendre, lots 7-9) · écrans
  UX-1/2/3 livrés · chaîne exercée sur NVDA, MSFT et RVMD. Le chantier courant est la **révision du
  modèle de fiabilité** (autorité contre actualité) ; RVMD reste le banc d'essai des modes de panne
  du socle (14 défauts F1→F14). État au 2026-09-05 (4) : **1 638 assertions / 0 échec / 21 scripts**,
  migrations appliquées jusqu'à **034**, prochaine 035. Roadmap active :
  `roadmap/02-spec-autorite-vs-actualite.md` — **capacités 0, 1 et 2 CLOSES**, prochain jalon
  **capacité 3** (l'axe `actualité`, calculé à la lecture).
---

# Prompt de reprise — portfolio-tracker V2 (cartes de provenance)

> **Ce fichier ne s'empile pas.** Le récit des sessions vit dans `00-REPRISE-ARCHIVE.md` (copie
> conforme, rien de résumé), les règles durables dans le `CLAUDE.md` du projet (conventions
> numérotées), les enseignements d'outillage transverses dans `../../../CHANTIER_OUTILLAGE_DEV.md`.
> Ici : **l'état atteint, ce qui reste, et les pièges à ne pas re-découvrir.** Protocole
> d'éviction : `CONTROL_SYSTEM.md` §5.

## 🎯 Roadmap active

**`roadmap/02-spec-autorite-vs-actualite.md`** (statut `figée`, ouverte le 2026-09-05) — révision du
modèle de fiabilité : **autorité contre actualité**. Six capacités dans un ordre imposé.
**Capacités 0, 1 et 2 CLOSES**, toutes le 2026-09-05 : table de profils co-écrite (#50, 174
assertions) · axe `nature` dérivé (migration 034, #51, 52 assertions) · registre nominatif des
sources (#52, 75 assertions).
**Prochain jalon : capacité 3** — l'axe **actualité**, calculé à la lecture et **jamais persisté**
(le persister reproduirait par construction le défaut n°2 : un corpus qui ne vieillit pas). Son
`contexte partagé` est déjà livré : `knowledge/material_events.py` + `knowledge/staleness.py`.
Migration à écrire *juste avant* son lot, jamais en avance — la prochaine est **035**.

⚠️ **L'ordre est load-bearing, ne pas le réordonner** : le registre des sources (2) doit précéder le
durcissement de la porte (4), sinon tout champ devient `couvert_perime` sans remède disponible.

Motif d'ouverture : l'information la plus fraîche du corpus est la moins bien classée (sur RVMD,
tier A moyen 0,931 sur des faits d'avant l'approbation FDA du 2026-08-26 · tier B+ 0,750 sur
l'information du jour), et le `readiness` prononce quand même `ready, 0 gap` — ⚠️ **ce faux vert est
persisté sur NVDA et MSFT, pas sur RVMD** (voir « Livré cette session »). La roadmap **absorbe** les
points 1 et 2 de « Reste à faire » ci-dessous — ils y sont traités comme des symptômes, pas comme des
tâches indépendantes.

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

- **Suite hors-ligne : 1 638 assertions / 0 échec / 21 scripts** — une seule commande,
  **`bash checks/run_all.sh`** (versionné depuis le 2026-09-05 (3)). Il porte les invocations
  correctes : montage `/contract_frozen` (sans lui 4 scripts sous-comptent en sortant à 0) et
  réseau `coolify` + `CHECK_DB_URL` pour `check_entry_nature`. ⚠️ **Ne pas le réécrire dans
  `/tmp`** : la version jetable sous-comptait 47 assertions en silence (`CHANTIER_OUTILLAGE_DEV.md`
  §27).
- **Migrations appliquées jusqu'à 034. Prochaine : 035** — à écrire *juste avant* son lot, jamais
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

### Livré cette session (2026-09-05, 4) — capacité 2 close : le registre nominatif des sources

**Aucune dépense de modèle. Aucune migration.** Récit complet dans `00-REPRISE-ARCHIVE.md`. Ce qui
doit rester ici :

- **`knowledge/source_registry.py` est le détenteur unique** de la règle d'admission. Quatre sources
  admises pour RVMD, co-choisies avec l'utilisateur : `endpts.com`, `statnews.com`,
  `fiercebiotech.com`, `biopharmadive.com` — portée `secteur:biotech_clinique`, natures
  `{interpretation}`, tier **B**, motif écrit. `checks/check_source_registry.py` : **75
  assertions**, test négatif **5/5**. Convention **#52**.
- 📌 **L'ordre `nature` PUIS `registre` est load-bearing.** `qualify()` dérive la nature depuis le
  source_type **générique**, et n'applique le registre que si celui-ci vaut encore
  `web_search_generic`. Replier la promotion dans `classify_source_type` (premier câblage, corrigé
  avant exécution) faisait sortir `endpts.com` en `web_search_reputable` **avant** toute question de
  nature : une source admise pour l'interprétation gagnait du standing sur une **mesure**.
- 📌 **Deux sites de câblage, et le second est celui qui compte** : `store_knowledge` qualifie avant
  de scorer, mais c'est l'appel dans `worker.py` **avant le filtre `reliability_min`** qui fait que
  le registre admet réellement quelqu'un — le worker rejette sous plancher avant d'atteindre
  `store_knowledge`.
- ⚠️ **Le secteur est déclaré en CODE, et c'est une mesure qui l'a décidé** : `tickers.sector` est
  **NULL sur les 17 tickers**. Un registre clefé dessus n'aurait admis personne, silencieusement.
- ⚠️ **Le desserrage B+ → B n'a TOUJOURS pas de bénéficiaire effectif au gate**, et c'est nommé dans
  `_DESSERRAGE_NON_CABLE` (§1bis du check). La doctrine vit dans `FIELD_PROFILES`, la porte lit
  `FIELD_PLANCHER_OVERRIDES` (qui ne porte que `marche.croissance_marche_historique`) ; les
  planchers de dimension `positionnement` et `marche` valent B+. Une entry `endpts.com` à 0,65 est
  admise par le registre et **encore refusée** par la porte. Le câblage appartient à la **capacité
  4** : le faire maintenant perturberait la ligne de base que son test central doit mesurer AVANT
  le lot. L'assert vire au vert de lui-même ce jour-là.
- 📌 **Rappel load-bearing de la capacité 1** : la nature d'une **entry** et la nature dominante d'un
  **champ** sont deux vocabulaires (#51) — la porte lira la première. `evenement` reste une classe
  **vide déclarée** (66 `mesure` / 68 `interpretation` / 0), sans émetteur ; elle se remplit à la
  capacité 3. Le contrat C1 n'a délibérément **pas** de champ `nature` : ne pas l'ajouter « pour
  compléter ».

⚠️ **Toujours vrai** : le balayage de péremption *signale*, il ne *décide* pas. Les 24 entries
suspectes de RVMD restent actives et la porte (#29) les compte comme couvrantes. **Un corpus complet
peut être périmé** — c'est ce que la capacité 4 ferme.

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
3. **FDA/EMA en régulateur A- (0,85)** — *décidé avec l'utilisateur, non commencé*. Mesuré :
   `fda.gov` n'est dans **aucune** table, et `_EU_REGULATOR_SUFFIXES` porte `esma.europa.eu`
   (titres) mais pas `ema.europa.eu` (médicaments). L'approbation FDA du 2026-08-26 — l'événement
   même qui a ouvert la roadmap 02 — classe aujourd'hui `web_search_generic` **0,50**. Un
   `regulator_filing_us` touche `SOURCE_RELIABILITY_BASELINE`, le `Literal SourceType`, le frontend
   **et les 12 prompts v2 en base** (tous énumèrent les source_types) → **migration 035** + règle
   #19. Lot séparé à dessein : il n'a rien à voir avec le registre, il élargit le vocabulaire.
4. **File de propositions de sources** — *demandée par l'utilisateur, non conçue*. Le système
   observe les domaines `web_search_generic` réellement rencontrés, **recommande** un classement
   (portée secteur/ticker, natures, tier), l'utilisateur **valide**. ⚠️ L'admission reste un **acte
   humain** : rien ne se promeut tout seul, pas même par corroboration (#50 — N sources recopiant
   un communiqué ne sont pas N sources indépendantes).
5. **Les 7 mandats qualitatifs RVMD restants** (~0,08 $) — désormais sans risque connu : le worker
   porte la date du jour, l'ancre documentaire **et** l'ancre matérielle.
6. **`ingestion-agent`** (contrat C2, document → entries) : jamais construit, **non bloquant** tant
   que search-worker + `synthesis_feed` couvrent les champs requis.
7. **4ᵉ ticker** — aucun blocage technique. ⚠️ Ajouter son entrée dans `websearch._ISSUER_DOMAINS`
   **en même temps que le ticker** (#33) : sans elle, son IR retombe sous le plancher. ⚠️ Et son
   **secteur** dans `source_registry._TICKER_SECTEURS` s'il doit hériter d'un registre sectoriel —
   `tickers.sector` est NULL en base et n'est lu par rien (#52).

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
  ⚠️ `DATABASE_URL` porte le dialecte SQLAlchemy `postgresql+asyncpg://` — `asyncpg.connect()` le
  **refuse** (`ClientConfigurationError`). Retirer `+asyncpg` pour une connexion directe.
- **Une colonne `NOT NULL` neuve met le déploiement en DETTE.** Entre l'application de la migration
  et le rebuild, le conteneur sert du code qui ne fournit pas la colonne : tout INSERT échoue. Et le
  check ne le voit pas — il *lit*. Prouver le chemin d'écriture par une **écriture réelle** dans le
  conteneur déployé (créer, relire en base, supprimer, vérifier le total inchangé), pas par un SELECT.
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
- **Un agrégateur reconnaît un bilan à sa FORME, jamais à sa position.** Trois dialectes cohabitent
  dans `checks/` (`… vérifications OK`, `N ok / N FAIL`, `N OK / N KO`) et un script émet un LOG
  *après* son bilan : un `tail -1` a sous-compté 47 assertions en silence, `exit 0`. L'absence de
  toute ligne de bilan est un **échec** (script mort avant ses asserts), jamais un zéro. → §27.
- **Un test négatif qui mute la base ne s'écrit jamais en une commande composée** : saboter,
  mesurer, restaurer, re-vérifier = quatre appels. Un `docker run` mort au milieu laisserait la
  production sabotée sans que rien ne le dise.

## À lire avant de reprendre

- **`CLAUDE.md` du projet** — conventions **#22 à #52**. Les plus structurantes du chantier
  courant : #29 (la couverture se lit dans un index), #42/#43 (datation et identité d'un fait),
  #44 (calculé / non calculable / absent), #46 (détenteur unique d'une règle), #47 (un zéro est une
  valeur), **#48** (la colonne `source_date` est un porteur de la date), **#49** (la péremption est
  une seconde horloge, et elle produit un rapport), **#50** (trois axes jamais recombinés ; le
  standing est une propriété du COUPLE source × nature), **#51** (nature d'une ENTRY ≠ nature
  dominante d'un CHAMP : deux vocabulaires, le second ne dérive jamais le premier ; `mesure`
  n'est jamais accordée par défaut), **#52** (une source est admise pour un COUPLE source × nature,
  et l'ordre `nature` puis `registre` est ce qui rend cette phrase vraie ; plafond ≠ qualification).
- **Specs** : `roadmap/00-principe-directeur-v2.md` · `roadmap/01-spec-v2-unifiee.md`
  (§5 agents, §7 curator/readiness, §8 contrats, §14 migrations, §16 UX, §18 découpage).
- **Cartes de contrat** : `roadmap/provenance-cards/*_card.md` + `*_schema.py` + `prompts/`.
- **Code** : `backend/app/agents/v2/` (`worker.py` · `curator.py` · `analysis.py` · `runner.py`) ·
  `backend/app/knowledge/` (`service.py` · `websearch.py` · **`source_registry.py`** ·
  `edgar_feed.py` · `synthesis_feed.py` · `financials_feed.py` · `valuation_feed.py` · `units.py` ·
  **`material_events.py`** · **`staleness.py`**) · `backend/app/contracts/` ·
  `backend/checks/README.md`.
- **Historique complet** : `00-REPRISE-ARCHIVE.md`. **Outillage transverse** :
  `../../../CHANTIER_OUTILLAGE_DEV.md` (§16 délégation, §24 tests négatifs, §25 porteurs d'un fait,
  §26 la ligne de base est une mesure, **§27 un bilan se reconnaît à sa forme**).
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
> **Capacités 0, 1 et 2 CLOSES** : la table de profils des 19 champs (#50, 174 assertions) · l'axe
> `nature` en dérivé déterministe (#51, migration 034, 52 assertions) · le **registre nominatif des
> sources** (#52, 75 assertions, 4 sources biotech co-choisies pour RVMD). Deux résultats sont
> load-bearing pour la suite : la nature d'une **entry** ≠ la nature dominante d'un **champ** (c'est
> ce que la porte confrontera), et le standing s'accorde au **couple** (source × nature) — d'où
> l'ordre `nature` PUIS `registre` dans `qualify()`.
> **Prochain jalon = capacité 3** : l'axe **actualité**, calculé à la lecture et **jamais persisté**
> (le persister reproduirait le défaut d'origine — un corpus qui ne vieillit pas). Son contexte
> partagé est déjà livré : `material_events.py` + `staleness.py`.
> ⚠️ Ne pas réordonner les capacités : le registre des sources (2) DOIT précéder le durcissement
> de la porte (4). ⚠️ Le desserrage B+ → B n'a toujours pas de bénéficiaire **au gate** : c'est la
> capacité 4 qui câble `FIELD_PROFILES` dans `curator.recompute_coverage`, pas avant (sa ligne de
> base doit être mesurée d'abord).
> LIRE D'ABORD : ce fichier, le `CLAUDE.md` du projet (conventions #22-**#52**),
> `00-REPRISE-ARCHIVE.md` si le *pourquoi* d'une décision manque.
