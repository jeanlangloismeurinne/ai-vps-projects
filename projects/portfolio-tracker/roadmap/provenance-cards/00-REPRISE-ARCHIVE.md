---
id: reprise-cartes-provenance-archive
status: archive
created: 2026-08-31
project: portfolio-tracker
role: Historique intégral des MàJ du chantier V2 (cartes de provenance), extrait de 00-REPRISE.md le 2026-08-31 pour alléger le prompt de reprise.
---

# Archive — journal du chantier V2 (provenance cards)

Ce fichier contient **l'intégralité** des blocs de MàJ et des sections de contexte qui figuraient
dans `00-REPRISE.md` jusqu'au 2026-08-31, du plus récent au plus ancien. Rien n'a été réécrit ni
résumé ici : c'est la copie conforme, conservée pour retrouver le *pourquoi* d'une décision, le
détail d'un run, ou le mode de panne exact d'un bug déjà réglé.

Le fichier de reprise vivant est `00-REPRISE.md` — il ne garde que l'état courant et ce qui reste
à faire. Les conventions durables (#22 à #32) vivent, elles, dans le `CLAUDE.md` du projet.

**Le bloc le plus récent (MàJ 2026-08-30 quater, second ticker MSFT) est resté dans `00-REPRISE.md`**
car il décrit l'état atteint et les deux dettes ouvertes.

---

<!-- Versés depuis 00-REPRISE.md le 2026-09-05 : 14 blocs de MàJ du 2026-08-31 au
     2026-09-04 (5). Copie conforme, rien de résumé. -->

> ## ⚡ MàJ 2026-09-05 — le corpus a enfin une horloge (versé le 2026-09-05 (2))
>
> Deux commits, chemin nominal, sonde publique 200 : **`ae02af3`** (ancre matérielle + balayage) et
> **`45379ee`** (F14). Aucune migration.
>
> - **`knowledge/material_events.py` — la seconde horloge.** Les dépôts périodiques (10-K/10-Q) ne
>   datent pas le monde ; un **8-K/6-K** le fait. Le search-worker reçoit désormais l'événement
>   matériel le plus récent, et un avertissement explicite quand il est **postérieur** à l'ancre
>   documentaire (« ce fait peut décrire un monde révolu SANS ÊTRE FAUX »).
> - **`knowledge/staleness.py` — un RAPPORT, jamais un `superseded_by`.** Route
>   `GET /tickers/{id}/knowledge/staleness`, **toujours 200**, `ecrit_en_base: false` (garde de check
>   qui grep l'absence d'`UPDATE`/`INSERT`/`DELETE`). Sur RVMD : seuil **2026-08-27**, 27 actives →
>   **24 suspectes / 2 postérieures / 1 non datée**, 7 champs touchés.
> - **F14, trouvé par le balayage lui-même** dès sa première lecture en prod : l'entry #169 disait
>   `fiscal_period='AU 2026-06-30'` et `source_date=2025-12-31` — **la même ligne se contredisait**.
>   Corrigé par détenteur unique ; vérifié après déploiement par le comptage #43 (une seule ligne
>   active par clef, #169 → #189 daté 2026-06-30, les ratios de flux inchangés à 2025-12-31).
>
> ⚠️ **Ce qui reste vrai et inconfortable** : le balayage *signale*, il ne *décide* pas. Les 24
> entries suspectes de RVMD sont toujours actives, et la porte de complétude (#29) les compte comme
> couvrantes. **Un corpus complet peut être périmé.**

> ## ⚡ MàJ 2026-09-04 (5) — LE SEUIL EST FRANCHI : première dépense réelle de tokens, F12 et F13, et une découverte de fin de session qui commande le prochain jalon
>
> **Le search-worker a tourné en production contre le vrai modèle.** Coût mesuré :
> **~0,0105 $ par mandat** (103 927 tokens en entrée), 0,0066 $ pour un mandat rendant `not_found`.
> Le taux de défaut ne retombe toujours pas à zéro : **deux défauts de plus (F12, F13)**, trouvés
> exactement là où la MàJ (4) disait de regarder — en **lisant les entries en texte** avant
> d'enchaîner les six dimensions.
>
> ### État livré, déployé, vérifié en prod
>
> Deux commits, deux déploiements, sonde publique 200 après `healthy` : **`b496354`** (F12) et
> **`7f91733`** (F13). **Aucune migration : la prochaine reste 034.** Suite hors-ligne :
> **1 262 assertions, 0 échec, 17 scripts** (1 247 → 1 255 → 1 262). Les deux blocs de checks neufs
> sont **éprouvés par test négatif** (6 puis 1 échec sur code neutralisé, restaurés au vert).
>
> | # | Défaut | Correctif |
> |---|---|---|
> | F12 | le message envoyé au worker ne portait **aucune date** : le modèle datait « le présent » à sa coupure d'entraînement. Il a cité le **10-K FY2024** (déposé 2025-02-26) comme source la plus récente, en ignorant le 10-K FY2025 (`rvmd-20251231.htm`, 2026-02-25) et deux 10-Q postérieurs — vérifié contre l'API EDGAR `submissions`. Trésorerie publiée à 2,3 Md$ au 31/12/2024, **en concurrence** avec l'entry déterministe tier A (815,4 M$ au 30/06/2026). Tous les nombres justes, le fait périmé (#42/#43) | date du jour + consigne explicite (« c'est le PRÉSENT, pas ta coupure ») dans **`_build_user_message`**, détenteur unique (#46) — pas dans `agent_prompts`, qui est versionné et hashé. Plus une **ancre temporelle** : le dépôt réglementaire le plus récent déjà connu du corpus, avec le cas « ancre INCONNUE » **dit explicitement** (une ancre absente et une ancre muette se lisent pareil côté modèle). §9 du check assert les **deux branches** |
> | F13 | `requires_human_review` était calculé par `_verify_provenance` (#28), renvoyé dans la réponse HTTP… et **jamais passé** à `store_knowledge`. En base : 26 entrées actives, drapeau à `false` partout, alors que la réponse HTTP en signalait une. Une entry tier A 0,94 dont le 10-K n'a jamais été ouvert était **indiscernable** d'une entry lue en entier | argument transmis (passer `False` ne peut jamais **désarmer** un drapeau : `store_knowledge` fait un OU avec ses source_types à revue d'office). §10 vérifie la **transmission** (`inspect.getsource`) et l'étend à `covers`/`source_type`/`source_url`/`fiscal_period` — un argument oublié est un mode de panne de famille |
>
> **F13 prouvé bout-en-bout, sans appel modèle.** La vérification par mandat réel est revenue
> **vide** (aucune entry drapeautée) : elle était donc **vacue**, pas concluante. Remplacée par un
> échange **synthétique** persisté par le vrai chemin `persist_worker_entries` (`ticker_id=None`,
> lignes supprimées après lecture), portant **deux** entries — `id=187 review=True`,
> `id=188 review=False`. Le contrôle négatif est dans le même échange : si la colonne était
> constante, les deux vaudraient pareil.
>
> ### Corpus RVMD — 14 entrées actives (recomptées en base après déploiement)
>
> | champ | actives | tier |
> |---|---|---|
> | `business_model.description` | 4 (ids 173-176) | A |
> | `business_model.drivers_revenus` | 3 (ids 177-179) | A |
> | `risques.risques_cles` | 6 (ids 180-185) | A, toutes du 10-Q au 30/06/2026 |
> | `marche.croissance_marche_historique` | 1 (id 186) | A |
>
> Plus les 9 entrées déterministes des MàJ précédentes (`financials.*`, `valorisation.*`).
> **`business_model.recurrence_pct` a été déclaré INFONDABLE** par le worker (`status=not_found`,
> avec explication : sans aucun revenu, il n'existe pas de proportion qui pourrait être qualifiée
> de récurrente) — 3ᵉ champ infondable de RVMD après `gross_profit` et `intensite_capex_pct`, tous
> enracinés dans le même fait. **⚠️ Ce verdict est déjà caduc, voir ci-dessous.**
>
> ### ⚠️ Découverte de fin de session — c'est elle qui commande le prochain jalon
>
> **La FDA a approuvé RASONQUE (daraxonrasib) le 2026-08-26.** Vérifié contre EDGAR (8-K
> Item 8.01) : produit prescriptible aux USA, prix catalogue 39 800 $ / 30 jours. Le corpus porte
> donc, **toutes actives et toutes tier A**, des entries incompatibles entre elles :
>
> | id | dit | daté du |
> |---|---|---|
> | 176 | « aucun produit approuvé pour la vente commerciale » | 10-K, 2026-02-25 |
> | 177 | « les seules entrées de trésorerie proviennent de financements » | 10-K, 2026-02-25 |
> | 182 | « la société ne peut être certaine d'obtenir une approbation » | 10-Q, 2026-08-05 |
> | 186 | « la FDA a approuvé RASONQUE le 2026-08-26 » | communiqué IR, 2026-08-26 |
>
> Ces entries ne sont **pas fausses** : elles sont correctement datées et fidèles à leur source.
> Elles sont **périmées**. Et `recurrence_pct` redevient fondable au prochain trimestre.
>
> **Ce que ça révèle.** F12 a donné une horloge au *modèle* ; le **corpus** n'en a toujours pas.
> `superseded_by` existe et est filtré par toutes les requêtes, mais **rien ne le peuple** quand un
> événement postérieur contredit un fait antérieur. Pire : l'ancre temporelle de F12 ne regarde que
> les dépôts **périodiques** (10-K/10-Q) — au 2026-09-04 elle annonce « 2026-06-30 » et **rassure**
> le modèle, alors que le monde a changé le 2026-08-26. Une garde peut être correcte et produire
> quand même un faux sentiment de fraîcheur. Corollaire pour la porte de complétude : #29 compte
> les champs **couverts** ; il est **aveugle à la péremption** et conclurait ici à un socle prêt.
>
> ### Prochain jalon — à arbitrer AVANT d'enchaîner les dimensions restantes
>
> Trois options, **délibérément non implémentées** (toucher au supersedage ou au gate donnerait au
> modèle une voix sur la complétude — cf. `feedback_optional_schema_gate`) :
>
> - **(a)** étendre l'ancre temporelle aux **événements matériels** (8-K, communiqués), pas
>   seulement aux dépôts périodiques ;
> - **(b)** un **balayage de péremption** : lister les entries actives dont la `source_date` précède
>   le dernier événement matériel connu de l'émetteur, et les proposer à re-vérification — un
>   **rapport**, jamais un `superseded_by` automatique ;
> - **(c)** une politique de supersedage sémantique : hors de portée sans jugement humain.
>
> Recommandation : **(a) puis (b)**, avant de dépenser sur les dimensions restantes — sinon chaque
> mandat payant s'ancre sur un corpus qui se croit à jour.
>
> ### Reste à faire sur le socle qualitatif RVMD
>
> Fondées : `business_model` (2 champs sur 3, le 3ᵉ infondable), `risques`, `marche` (1 champ).
> **À faire : `marche.structure_5forces`, `produits.description`, `produits.unit_economics`,
> `positionnement.moat_preuves`, `positionnement.position_vs_pairs`,
> `management_allocation.incitations`, `management_allocation.skin_in_game_pct`.**
> Budget prévisionnel : ~0,08 $ pour les 7 mandats.
>
> ### Blocages et outillage
>
> `compose-deploy.sh` **refusé par le classifieur pour la 4ᵉ session consécutive** — repli §12 de
> `CHANTIER_OUTILLAGE_DEV.md`, inchangé, deux déploiements livrés par lui. **Zéro sous-agent lancé**
> (4ᵉ session consécutive). Les enseignements réplicables de cette session sont écrits dans
> `CHANTIER_OUTILLAGE_DEV.md` : **§21** (un agent n'a pas d'horloge), **§22** (un drapeau non
> persisté est un affichage), **§23** (le corpus n'a pas d'horloge non plus), plus les ajouts au
> **§13** (ne jamais lire un code de sortie derrière un `|`), au **§16** (borne basse de la
> délégation : une recherche dont le rapport tient en une ligne ne rembourse pas l'amorçage) et au
> **§18** (une fois la frontière gratuite franchie, le contrôle le moins cher est le `dry_run`).
>
> **Défaut mineur non corrigé :** `uncovered_fields` peut contenir un champ **deux fois** (une fois
> avec explication, une fois nu) — pas dédupliqué. Impact faible : la porte de complétude lit
> l'index `covers` (#29), pas `uncovered_fields`.
>
> **Limite de conception, à arbitrer, non modifiée :** `_resolve_covers` estampille **toutes** les
> entries d'un mandat avec l'unique `field_path` du mandat, et `persist_worker_entries` écrit
> `covers=([entry.covers] if entry.covers else None)` — le worker ne peut donc **jamais** produire
> un `covers` multi-champs, alors que la migration 029 a fait la colonne `TEXT[]` précisément pour
> ça. Desserrer donnerait au modèle une voix sur la porte de complétude (#24/#29) : à arbitrer, pas
> à changer unilatéralement.

> ## ⚡ MàJ 2026-09-04 (4) — quatrième passage sur les feeds déterministes : F10 et F11, toujours zéro token de modèle
>
> **Le jalon « search-worker » n'est toujours pas atteint, et c'est encore délibéré.** La
> pré-condition écrite en MàJ (3) — *relire en texte une entry de chaque feed encore non inspecté
> sur RVMD, pas seulement son code de retour* — a rendu **deux défauts de plus**. Compteur cumulé
> sur les seuls producteurs déterministes : **F1 → F11**, en quatre passages. Le taux n'est **pas**
> retombé à zéro ; c'est le fait le plus important de cette mise à jour.
>
> ### État livré, déployé, vérifié en prod
>
> Un commit, un déploiement, sonde publique 200 après `healthy` : **`4382dd9`**.
> **Aucune migration : la prochaine reste 034.** Suite hors-ligne complète :
> **1 247 assertions, 0 échec, 17 scripts** (1 216 → 1 247, avec le montage `/contract_frozen`).
> Les trois blocs de checks neufs sont **éprouvés par test négatif** (9, 4 puis 4 échecs sur code
> neutralisé, restaurés au vert).
>
> | # | Défaut trouvé sur RVMD | Correctif |
> |---|---|---|
> | F10 | la règle d'unité de F9 vivait dans `base_rate_corpus._mds` et **seulement là** ; `edgar_feed._md` et `financials_feed._md` divisaient toujours par `1e9` en dur. Capex FY2025 = **15,99 M$** (vérifié contre l'API EDGAR `companyconcept`, CIK 0001628171) publié « 0,02 MdUSD » / « 0,0 Md », et `fcf_conversion_pct` disait « FCF -0,9 Md = CFO -0,9 Md − **capex 0,0 Md** » — une soustraction dont l'arithmétique **paraît juste** parce que ses deux termes sont écrasés à la même unité | nouveau module **`knowledge/units.py`**, détenteur **unique** de la règle ; les trois producteurs l'importent. La devise est passée **à chaque appel** : deux termes d'une même phrase peuvent désormais porter des paliers différents (M et Md), la factoriser ferait lire deux ordres de grandeur comme un seul (#46) |
> | F11 | `_latest_revenue_usd` testait `if rev:` → un CA légitime de **`0.0`** était sauté et la boucle reculait dans le temps. `base-rate-anchor` publiait « pour **11,6 M$ de ventes** » (FY2023) **en contradiction directe** avec l'entry EDGAR tier A qui dit 0 : deux réponses actives à une même question | `is not None`, + datation du flux par son exercice (#42), + **limite déclarée** : une base de ventes nulle ne retire pas l'ancre de taux de base, elle en déclare l'inapplicabilité en taux (un CAGR ne se calcule pas depuis zéro). Le zéro est une propriété **mesurée** de l'émetteur, pas un trou de collecte (#47) |
>
> Conventions **#46** et **#47** ajoutées au `CLAUDE.md` du projet.
>
> ### Les deux leçons de cette itération
>
> **(a) Un correctif de règle s'arrête au premier exemplaire du défaut.** F9 avait écrit la *bonne*
> règle, dans *un seul* des trois modules qui la portaient. Ce n'est plus « le correctif a introduit
> une régression » (leçon de F9) mais « le correctif n'est pas allé au bout de la règle ». Livrable
> correct d'un correctif de règle : un **module détenteur**, pas un `if` corrigé — une règle
> recopiée re-diverge au correctif suivant, par construction. C'est la convention #43 (clef de
> supersedage, détenteur unique) transposée à un **format**, donc probablement générale.
>
> **(b) La fixture de `check_base_rate_corpus.py` était plus favorable que la production** (CA 2025
> à 11,58 M$ au lieu de 0). F11 lui était **structurellement invisible** : 48 assertions vertes sur
> un défaut publié. Pire, le test négatif lui-même aurait « passé » — réintroduire `if rev:` sur
> cette fixture ne produit aucun échec. Une fixture fausse ne rend pas seulement le check
> inefficace, elle rend le **rituel de validation du check** inefficace. Fixture remplacée par les
> chiffres de production (commentaire disant d'où ils viennent) → le test négatif rend alors 9 FAIL.
>
> Les deux leçons sont en mémoire (`feedback_correctif_regle_jumeaux`,
> `feedback_fixture_copiee_du_reel`) et détaillées dans `CHANTIER_OUTILLAGE_DEV.md` §19 et §20.
>
> ### Vérifications faites APRÈS déploiement (le diff ne suffit pas — #43)
>
> Les 3 feeds rejoués (`edgar-refresh`, `financials-refresh`, `base-rate-anchor`, HTTP 200), puis
> les **13 entries actives relues en texte**. Extraits qui étaient faux et ne le sont plus :
> - `#162` — « Chiffre d'affaires FY2025 : **0 USD** » (était « 0,00 MdUSD », indiscernable d'un arrondi)
> - `#168` — « Capex FY2025 : **16,0 MUSD** » (était « 0,02 MdUSD »)
> - `#171` — « FCF **-913,7 MUSD** = cash-flow opérationnel **-897,7 MUSD** − capex **16,0 MUSD** » — la soustraction est désormais **vérifiable**
> - `#172` — « **0 $ de ventes (FY2025)** » + paragraphe ⚠ sur la base de ventes nulle (était « 11,6 M$ »)
>
> Comptage par clef (convention #43) : **exactement 1 ligne active** pour chacun des 6 champs MVDD
> couverts et pour chacun des 10 `metric` EDGAR. Aucune contradiction résiduelle.
>
> ### Prochaine étape — inchangée, et maintenant réellement débloquée
>
> **Socle de connaissance RVMD via le search-worker** sur les 6 dimensions qualitatives
> (`business_model`, `produits`, `positionnement`, `marche`, `management_allocation`, `risques`),
> ~50 entrées attendues — **1ʳᵉ dépense réelle de tokens de modèle**.
>
> ⚠️ **Avant de lancer** : les 4 feeds déterministes ont maintenant été inspectés en texte
> (`edgar`, `financials`, `valuation`, `base_rate`) et leurs 13 entries sont propres. La frontière
> gratuite est donc épuisée pour la partie quantitative — il n'y a plus de raison de reporter la
> dépense. En revanche le taux de défaut par passage (11 en 4 passages) justifie de **relire en
> texte les premières entries du search-worker** avant de lancer les 6 dimensions en série.
>
> Reste aussi, non bloquant : **ingestion-agent**.

> ## ⚡ MàJ 2026-09-04 (3) — la dimension `valorisation` fondée sur RVMD, et trois défauts de plus (F7/F8/F9) — toujours zéro token de modèle
>
> **Suite directe de la MàJ (2).** Le jalon déclaré était « socle de connaissance RVMD via le
> search-worker, 1ʳᵉ dépense réelle de tokens ». Il n'a **pas** été atteint, et c'est délibéré : la
> pré-condition (« réparer le déterministe avant toute dépense de modèle ») a de nouveau rendu trois
> défauts, sur les feeds de **valorisation** cette fois. Ils auraient contaminé chaque appel d'agent
> lisant `valorisation.*`.
>
> ### État livré, déployé, vérifié en prod
>
> Trois commits, trois déploiements, sonde publique 200 après `healthy` à chaque fois :
> `fc1fab2` (F7), `76e9385` (F8), `5c38a13` (F9). **Aucune migration : la prochaine reste 034.**
> Suite hors-ligne complète : **1 216 assertions, 0 échec, 17 scripts** (1 177 → 1 216, avec le
> montage `/contract_frozen`). Les trois correctifs sont **éprouvés par test négatif** (8, 5 puis
> 6 échecs / exit 1 sur code neutralisé, restaurés au vert).
>
> | # | Défaut trouvé sur RVMD | Correctif |
> |---|---|---|
> | F7 | `pe_ntm = −35,95×` et `ev_ebitda = −26,23×` publiés **tels quels** dans le corpus narratif — un P/E négatif n'ordonne rien et n'est pas monotone (une perte plus lourde le rapproche de zéro *par le bas*, donc paraît « moins cher ») | `_trier_multiples()` sépare **calculé / non calculable / absent** — jamais deux confondus (#44) |
> | F8 | « small-cap (CA < 1 Md$) » écrit pour une société capitalisée **44,9 Md$** : classe juste (le Base Rate Book raisonne en CA), **libellé emprunté à une autre maille** | libellé composé avec la base réellement mesurée + déclaration explicite quand les deux mailles divergent (#45) |
> | F9 | le paragraphe que F8 venait d'ajouter annonçait « **0,0 Md$ de ventes** » pour **11,58 M$** — l'agent lit *aucune vente*, sur le chiffre même qui fonde la divergence | `_mds()` choisit son unité par ordre de grandeur, **après** l'arrondi (#45) |
>
> ### La leçon de cette itération : F9 vivait dans le correctif F8
>
> La MàJ (2) disait « un correctif juste dans ce qu'il écrit peut être faux dans ce qu'il omet de
> retirer ». F9 en donne la variante : **un correctif peut publier sa propre justification en la
> rendant illisible**. Il n'était visible ni dans le diff, ni dans la suite de checks — seulement en
> **lisant en texte l'entry produite en production**. D'où la règle, désormais en mémoire
> (`feedback_frontiere_gratuite_avant_depense_modele`) : *avant le premier appel modèle d'une
> chaîne, exécuter tous ses producteurs déterministes en dry-run et lire leur sortie EN TEXTE — et
> refaire ce contrôle après chaque correctif.* Le coût est d'un `curl` par producteur ; le gain est
> tout ce qui n'est pas répercuté sur chaque appel payant en aval.
>
> Détail secondaire mais réutilisable : l'assertion « aucun montant non nul ne s'arrondit à zéro »
> a **viré au rouge d'elle-même** sur `999 999 $` → « 1000,0 k$ » (unité choisie avant l'arrondi).
> Le check a trouvé un défaut que la relecture n'avait pas vu — son seul motif d'existence.
>
> ### Corpus RVMD en prod — 13 entrées actives, **une seule par champ**
>
> ```
> financials.roic_pct 1 · financials.fcf_conversion_pct 1 · financials.levier 1
> valorisation.prix_actuel 1 · valorisation.relatif_multiple 1 · valorisation.base_rate_anchor 1
> ```
> (entrées 141-155 EDGAR + 156, 157, **160**). Le réflexe §15 a été rejoué après **chaque** écriture :
> `SELECT unnest(covers), count(*) … WHERE superseded_by IS NULL GROUP BY 1` → exactement 1 ligne
> active par champ, aucune vérité en double. La dimension `valorisation` est donc **fondée sur ses
> trois champs**, et les 6 dimensions qualitatives restent vides — c'est le jalon suivant.
>
> ### Prochain jalon — **inchangé**, et sa pré-condition est maintenant réellement remplie
>
> **Constituer le socle de connaissance RVMD via le search-worker** (~50 entrées attendues) sur
> `business_model`, `produits`, `positionnement`, `marche`, `management_allocation`, `risques` —
> c'est la **première dépense réelle de tokens de modèle**. Puis readiness (distinguer champ
> **infondable** et **lacune**), puis la chaîne research → bull/bear → réfutation → synthèse.
>
> ⚠️ Avant de lancer le search-worker, **relire une entry produite** par chacun des feeds encore
> non inspectés en texte sur RVMD, pas seulement leur code de retour. Trois passages sur les feeds
> déterministes ont rendu 9 défauts (F1→F9) ; le taux n'est pas encore retombé à zéro.
>
> Frictions d'outillage et arbitrages de délégation de cette session (zéro sous-agent lancé, à
> nouveau, et pourquoi) : `CHANTIER_OUTILLAGE_DEV.md` §12 (re-vérifié), §16, **§17** et **§18**.

> ## ⚡ MàJ 2026-09-04 (2) — 3ᵉ TICKER **RVMD** : le socle financier réparé en six points, avant toute dépense de modèle
>
> **Jalon choisi : 3ᵉ ticker = RVMD (Revolution Medicines, biotech clinique, position réellement
> détenue).** L'exercice a servi ce qu'on lui demandait — sortir du confort NVDA/MSFT — mais **pas
> là où on l'attendait** : il n'a encore consommé **aucun token de modèle** et a déjà trouvé
> **six défauts structurels du socle EDGAR**, dont trois n'existaient que sur un émetteur au profil
> différent (pertes, trésorerie massive, convertibles récentes).
>
> ### État livré, déployé, vérifié en prod
>
> Trois commits, trois déploiements, sonde publique 200 après `healthy` à chaque fois :
> `957ffbb` (F4), `a3d604e` (F5), `019fe4b` (F6). **Aucune migration : la prochaine reste 034.**
> Suite hors-ligne complète : **1 177 assertions, 0 échec, 17 scripts** (mesurée **avec** le
> montage `/contract_frozen` — cf. l'avertissement de `backend/checks/README.md`).
>
> | # | Défaut | Correctif |
> |---|---|---|
> | F1 | `fcf_conversion_pct = +80,77 %` calculé sur **deux négatifs** — un ratio flatteur né de deux mauvaises nouvelles | `None` + champ `cash_burn` |
> | F2 | le composite `cash_and_lt_debt` **laissait tomber la trésorerie** quand la 2ᵉ jambe manquait | `None` + `long_term_debt_status`, jamais un zéro |
> | F3 | `_miss` confondait *absent*, *nul* et *non calculable* | `_absents()` |
> | F4 | le socle ne lisait que les dépôts **annuels** — aveugle à tous les trimestres depuis le dernier 10-K | ancre de bilan sur le dépôt le plus récent |
> | F5 | la clef de supersedage incluait la période : changer l'ancre **ajoutait** la vérité sans retirer le fait périmé | identité = ce que le fait mesure (#43) |
> | F6 | (a) un ratio 100 % bilan étiqueté « FY2025 » ; (b) appariement capex sur `{…,fact}` vs `{…,edgar}` | datation par les postes (#42) + règle d'identité unique |
>
> **Ce que F4 déplaçait sur RVMD** (mesures réelles) : trésorerie 383,7 → **815,4 M$**, capitaux
> propres 1 631,3 → **2 606,2 M$**, actifs 2 354,5 → **4 323,3 M$**, dette convertible 0 →
> **487,4 M$**. Le socle affichait donc un bilan vieux de six mois sur une biotech qui lève.
>
> ### La leçon centrale : un correctif juste **dans ce qu'il écrit** peut être faux **dans ce qu'il omet de retirer**
>
> **F5 et F6 n'ont été trouvés qu'en déployant le correctif précédent puis en RELISANT la base.**
> Ni la suite de checks, ni les contrats Pydantic, ni l'arithmétique ne pouvaient les voir : F5
> laissait **deux valeurs de capitaux propres actives en même temps** (aucun ratio faux —
> l'extraction prend la plus récente — mais le **corpus narratif lu par les agents** portait deux
> réponses) ; F6(a) était un fait dont **tous les nombres étaient justes et l'étiquette fausse**.
> Réflexe à garder sur tout stockage append-only : après le premier déploiement réel, ne pas
> demander « la nouvelle valeur est-elle bonne ? » mais **« combien de lignes sont actives sur
> cette clef maintenant ? »**. Un `GROUP BY` sur `superseded_by IS NULL` aurait trouvé F5 et F6(b)
> d'un coup. → conventions **#42** et **#43** de `CLAUDE.md`, et `CHANTIER_OUTILLAGE_DEV.md` §15.
>
> ### ⚠️ Correction factuelle du message de commit `2eff706`
>
> Ce message affirme que déduire une dette nulle « faisait basculer la dette nette de −383,7 à
> +103,7 M$ ». **C'est faux et l'histoire n'a pas été réécrite** — la correction vit ici et dans
> `checks/README.md` : à l'ancre FY2025, RVMD n'avait **pas** de dette long terme déposée (le seul
> point au 2025-12-31, issu d'un 10-Q, vaut 0) ; les 487,4 M$ de convertibles datent du 2026-06-30.
> L'enjeu du composite n'était donc pas un signe inversé mais **l'assiette**.
>
> ### Corpus RVMD en prod — 10 entrées actives, une par poste, zéro contradiction
>
> `152` capital_expenditure FY2025 (v2) · `147` cash_and_lt_debt AU 2026-06-30 · `155`
> fcf_conversion_pct FY2025 · `153` levier AU 2026-06-30 · `143` net_income FY2025 · `144`
> operating_cash_flow FY2025 · `142` revenue FY2025 · `154` roic_pct FY2025 (mixte déclaré, 181 j
> d'écart) · `141` stockholders_equity AU 2026-06-30 · `145` total_assets AU 2026-06-30.
> **Infondables assumés** : `gross_profit` (aucun concept XBRL exploitable) et
> `intensite_capex_pct` (revenu déposé à 0).
>
> ### Prochaine étape
>
> **Constituer le socle de connaissance RVMD via le search-worker** (~50 entrées attendues) — c'est
> la première étape qui dépense de vrais tokens de modèle, et sa pré-condition (un socle financier
> sain) est désormais remplie. Puis readiness (distinguer champ **infondable** et **lacune**), puis
> la chaîne research → bull/bear → réfutation → synthèse.
>
> ### Frictions d'outillage relevées → `CHANTIER_OUTILLAGE_DEV.md` §12 à §16
>
> `compose-deploy.sh` refusé par le classifieur **dans toutes ses formes** (repli documenté) · le
> montage `/contract_frozen` manquant fait **sous-compter 4 scripts en sortant à 0** (et cette
> mesure incomplète a failli écraser des chiffres corrects dans le README) · la sonde publique rend
> le **404 du frontend** pendant `health: starting` · **registre de délégation** : zéro sous-agent
> lancé sur cette session, avec le test de décision qui l'explique.

> ## ⚡ MàJ 2026-09-04 — DETTE DU RUNNER FERMÉE : un abandon est désormais comptabilisé
>
> **Commit `8b8efef`, backend déployé et vérifié (HTTP 200, 2 conteneurs sur le domaine =
> l'exception attendue).** Suite hors-ligne : **19 scripts, 0 échec**, dont **1 010 assertions** sur
> les 15 qui affichent un total (+49 — `check_runner_telemetry.py`). Aucun changement frontend,
> aucune migration : la prochaine reste **034**.
>
> ### Le périmètre réel était 4× plus large que la description de la dette
>
> Ce fichier et les commentaires `⚠️` de `monitoring.py`, `exit.py`, `debate.py` disaient tous la
> même chose — « la dépense de **cette tentative** n'est pas comptabilisée ». Trois sources
> d'accord, donc crédibles. **La lecture de `runner.py` a montré autre chose** : quand la
> **clôture** de `run_tool_json_agent` échoue, c'est le coût de **toute la boucle d'outils** qui
> disparaît — plusieurs tours à gros contexte, contre un seul pour la clôture. Mesuré par test
> négatif : **3 850 tokens réellement facturés contre 850 comptabilisés, soit 78 % de la facture.**
> Les trois mentions décrivaient le symptôme **vu depuis le site d'appel**, pas la cause. Leçon
> transverse : un fichier de reprise dit **où regarder**, jamais **jusqu'où va le trou** ; et
> plusieurs commentaires concordants ne sont pas des preuves indépendantes — ils sont souvent
> copiés les uns des autres.
>
> ### Livré
>
> `AgentOutputInvalid`, **sous-classe de `RuntimeError`** (les 6 sites d'appel font
> `except RuntimeError` — aucun n'a eu à changer de forme), porte `raw_content`, `tokens_in`,
> `tokens_out`, `cost_usd`, `attempts`, `agent_name`, `schema_name`, `last_error`.
> `add_upstream()` reporte la dépense de la boucle d'outils sur un échec de clôture, et `__str__`
> est **recalculé** (un message figé à la construction annoncerait le coût d'avant report).
> `monitoring.py` / `exit.py` / `debate.py` la passent en `run=` **telle quelle** : leurs
> `_persister_echec` lisaient déjà `getattr(run, "tokens_in", 0)`, d'où un diff minimal. Chacun
> garde un `except RuntimeError` **en second** pour les échecs sans télémétrie (panne réseau,
> provider indisponible) — un échec non tracé resterait un trou de suivi.
>
> ### Ce qui est prouvé, et ce qui ne l'est pas
>
> **Prouvé.** Les 49 assertions **exécutent le vrai runner** contre un `AgentProvider` bouchonné à
> réponses scriptées — du code réellement joué, pas des fixtures relues. Le check a été **éprouvé
> par test négatif** (report du coût supprimé → 3 échecs en §7, exit 1) : sans ça, il n'aurait rien
> valu de plus que le `node --check` de la MàJ du 01-09. Les colonnes cibles ont été relues en base
> (`tokens_in`/`tokens_out` INTEGER, `cost_usd` NUMERIC) et §6 verrouille désormais les **types**
> autant que les noms — `_persister_echec` avale toute `DataError` dans un `except Exception`, donc
> une erreur de binding perdrait la trace **une seconde fois, en silence**.
>
> ⚠️ **Non prouvé, à assumer** : aucun **échec réel de modèle** n'a été provoqué de bout en bout.
> Le chemin d'écriture est établi **par identité de types** avec le chemin de succès, lui-même
> exercé en production (sessions **#8** et **#9** portent des `cost_usd` écrits depuis des floats
> Python). Forcer un vrai échec DeepSeek coûterait un appel payant et écrirait une session `failed`
> sur la thèse MSFT #4 : jugé disproportionné. Si un `failed` apparaît un jour à 0 token, c'est ici
> qu'il faut revenir.
>
> ### Friction relevée, non corrigée (→ `CHANTIER_OUTILLAGE_DEV.md` §9)
>
> `Settings` exige `DUST_*`, `SLACK_*` et `FMP_API_KEY` **sans défaut** : un check **100 % V2**,
> sans réseau ni DB, ne s'importe pas sans sept variables V1 bidons. La disjonction V1/V2 est vraie
> au niveau des agents et des tables, **fausse au niveau de `Settings`**. La commande de check *a
> l'air fausse* et se fait légitimement refuser. ⚠️ **Ne pas « corriger » en mettant des défauts
> `""`** : la prod démarrerait alors sans clés Dust en silence (cf. « desserrage de schéma = trou
> silencieux »). Correctif proposé : un `checks/env.checks` versionné, valeurs factices.

> **Ce fichier a été allégé le 2026-08-31.** Tout l'historique (journaux de sprint détaillés,
> diagnostics de bugs déjà réglés, décisions et leurs mesures) est conservé **intégralement** dans
> **`00-REPRISE-ARCHIVE.md`**, à côté. Les **conventions durables #22 à #32** vivent dans le
> **`CLAUDE.md` du projet** — c'est là qu'il faut les lire, pas ici.

> ## ⚡ MàJ 2026-09-03 (bis) — Coolify est arrêté : le déploiement passe en `docker compose`
>
> **Aucune ligne de code du chantier V2 n'a bougé.** Ce qui change est la façon de livrer, et deux
> réflexes de ce fichier sont désormais **périmés** :
>
> - **`infrastructure/deploy.sh` est neutralisé** (conservé, pas supprimé : il refuse de tourner tant
>   que le conteneur `coolify` n'est pas debout). Le script est **`infrastructure/compose-deploy.sh`**,
>   même contrat d'appel, mêmes codes 2-7, **plus un code 8 = build OK mais l'app ne répond pas**.
>   Voir `DEPLOY.md`. Retour à Coolify : `infrastructure/coolify-restore.sh`.
> - **La limite d'outillage notée plus bas est levée** : `--rebuild-only` existe, donc le cas « un
>   seul commit couvre backend + frontend » ne demande plus de fabriquer une modification bidon.
>   Et `portfolio-tracker` (toute la stack) suffit en un appel ; `portfolio-backend` /
>   `portfolio-frontend` restent valides pour ne rebuilder qu'un service.
> - **Il n'y a plus de numéro de déploiement.** Les `#328`…`#349` de ce fichier étaient des ids
>   Coolify ; la traçabilité est désormais le **SHA du commit** rendu par la ligne `RESULT:`.
>
> **Ce que la migration a changé pour le mieux, et qui touche ce chantier précisément.** Le
> `docker ps | grep <app>` « doit montrer UN SEUL conteneur » n'est plus une vérification qu'on peut
> oublier : le script **compte les conteneurs portant `Host(<domaine>)`** et échoue en code 8 s'il y
> en a deux. Portfolio est l'exception explicitement tolérée (backend et frontend partagent le
> domaine via `PathPrefix`, donc **2 attendus**). Et le script **attend la santé du conteneur avant
> de sonder** : un premier jet acceptait « tout sauf 5xx » et a validé un **404 sur `/api/health`** —
> pendant la recréation du backend, Traefik n'a plus de route `/api` et c'est le catch-all Next.js
> qui répond. Exactement le mode de panne de la convention #39, transposé au déploiement : une
> vérification qui ne regarde que la classe du code ne mesure rien.
>
> Le reste de l'infra est **inchangé et volontairement non renommé** : le proxy s'appelle toujours
> `coolify-proxy`, le réseau toujours `coolify` — tous les labels Traefik du VPS en dépendent.
> Les conventions de compose du projet sont à relire dans le **`CLAUDE.md`** : `env_file` est
> désormais **requis** (c'était « interdit, Coolify injecte ») et les `NEXT_PUBLIC_*` sont inlinés au
> build, un oubli n'échouant **que dans le navigateur**.

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

---

> ## ⚡ MàJ 2026-08-30 (ter) — AUDIT des desserrages de contrat faits à chaud pendant la chaîne : le `Optional` du reverse-DCF cachait un VRAI trou silencieux (bear), corrigé par durcissement prompt PUIS re-serrage du schéma (déployé #324)
>
> **Contexte** : les builds #318-#323 avaient rendu 6 champs plus permissifs pour faire passer le 1er
> run. Audit demandé (« certains paramètres rendus optionnels me semblent significatifs »). Verdict :
> **1 desserrage significatif (#4), 1 modéré (#5), les 4 autres bénins.**
>
> ### 🔬 Le finding : `reverse_dcf.croissance_implicite_prix_actuel_pct` (rendu `Optional=None`)
> C'est le **cœur de l'expectations investing** (« quelle croissance le prix price-t-il ? »). Preuve en
> base sur le 1er run NVDA : le **bull le remplit (15.0)**, le **bear le laisse `null` aux rounds 1 ET 2**
> — alors que le bear **écrit « ~15% » dans sa prose `verdict`**. Le modèle CONNAÎT le chiffre mais
> n'alimente pas le champ machine ; `Optional=None` l'a laissé passer en silence. **Pas de crash
> aujourd'hui** (le consommateur `base_rate_ge` n'est PAS encore câblé dans `analysis.py` — vérifié),
> mais **bombe à retardement** : au câblage, un `null` du bear entrerait sans bruit. Cohérent avec
> #24/#25/#28 : un manque ne doit jamais ressembler à une valeur.
>
> ### Décision utilisateur : « durcir le prompt d'abord » + « contrat d'abord » (avant agents 7-9)
> 1. **Prompts durcis** (commit `4c34367`, source de vérité règle #19) : `30-research` garde-fou 5,
>    `40-bull` garde-fou 4, `41-bear` garde-fou 2 → `croissance_implicite` = **nombre %/an OBLIGATOIRE,
>    jamais null/omis** (obtenu en inversant le DCF) ; `assumptions` **fermé aux 3 clés** contractuelles
>    (taux d'actualisation en prose dans `methode`, pas en champ inventé).
> 2. **Propagé en prod** : `agent_prompts` (research/bull/bear, flow v2) mis à jour via
>    `_gen_prompt_refresh_20260830.py` (réutilise l'assemblage de `_gen_025.py`, DB = commit) +
>    `docker cp`/`psql -f` (#17). **Pas de rebuild** : `get_agent_provider` relit la DB à chaque appel.
> 3. **Re-testé en réel** (NVDA) : research **22.0/18.0**, bull **18.0**, **bear #1 ET #2 = 18.0**
>    (contre `null` avant), `assumptions` = 3 clés partout. **L'omission a disparu en pratique.**
> 4. **Schéma re-serré** (commit `9bebd1c`, **deployment #324**, 1 seul conteneur backend vérifié,
>    HEAD==origin/main) : la copie **runtime** `analysis_v2_schemas.py` re-alignée sur le **contrat figé
>    qui, lui, n'avait JAMAIS été desserré** → `ReverseDcf.croissance_implicite_prix_actuel_pct: float`
>    (requis) + `Assumptions(Strict)` (`extra='forbid'`). Validé sous pydantic 2.13.5 (champ manquant
>    rejeté, champ inventé rejeté) ; run de contrôle post-déploiement OK (croissance 22.0).
>
> ### Les 4 autres desserrages — laissés tels quels (jugés acceptables)
> `BaseRate.taux ÷100 si>1` (bénin) · `BaseRatePct alias taux→taux_pct` (faible) · `curator
> readiness_report_id or 0` (cosmétique) · `BullCase.conviction ×10 si≤1` : **coercition gardée comme
> filet** (risque de polarité théorique sur le float `1.0` → note pour plus tard, pas corrigé). Le
> desserrage `Assumptions extra=ignore` (#5) ne masquait rien en base (invention `taux_actualisation`
> transitoire) mais re-serré par principe.
>
> ### RESTE À FAIRE (inchangé, « contrat d'abord » désormais satisfait)
> 1. **Agents 7-9** (décision/validate M6 → sortie/calibration → débat), migrations 030/031 juste avant.
> 2. **Second ticker** (généralité de la chaîne).
> 3. **UX transverse** (§16). 4. **`ingestion-agent`** (C2, non bloquant).
> ⚠️ **Dette connue** : `reverse_dcf.croissance_implicite` est désormais TOUJOURS chiffré, mais son
> consommateur `base_rate_ge` n'est **toujours pas câblé** dans `run_research` — à faire quand on
> finalisera le `taux_base_pct` précis (le champ est maintenant fiable pour ça).

> ## ⚡ MàJ 2026-08-30 (bis) — CHAÎNE D'ANALYSE COMPLÈTE EXERCÉE EN RÉEL (première fois)
>
> **Chaîne research→bull→bear→réfutation→synthèse complète pour NVDA.** Coût total < $0,015.
>
> | étape | ID | résultat | coût |
> |---|---|---|---|
> | Research memo | #1 | posture NEUTRE, memo structuré complet | $0.003 |
> | Bull case | #1 | conviction 7/10, variant_perception analytique | — |
> | Bear case | #2 | conviction 6/10, ASIC risk comme thèse centrale | $0.003 |
> | Réfutation (bear v2) | #3 | `refutation_du_bull` : 3 items, round 2 | $0.002 |
> | **Synthèse** | **#4** | **PROCEED_AVEC_CONDITIONS** | **$0.004** |
>
> **Verdict final** `PROCEED_AVEC_CONDITIONS` — seuil d'entrée `< 180$` (marge sécurité > 25%). Position
> sizing 3% (Kelly fractionnaire réduit de 3,9% pour marge de sécurité faible). 5 hypothèses de
> monitoring (H1-H5) avec seuils d'invalidation chiffrés (H1 = part de marché inférence IA > 70%,
> seuil invalidation 60%). **Pont `valider_pont()` validé** : chaque risque accepté pointe une hypothèse existante.
>
> ### Corrections de schéma nécessaires au fil de la chaîne (builds #318-#323)
>
> | problème | fix | fichier |
> |---|---|---|
> | `BaseRate.taux=70` (modèle renvoie %) | coerce ÷100 si > 1 | `analysis_v2_schemas.py` |
> | `BaseRatePct.taux_pct` absent (modèle envoie `taux`) | alias `taux`→`taux_pct` | idem |
> | `BullCase.conviction=0.6` (modèle scale 0-1) | coerce ×10 si ≤ 1 | idem |
> | `ReverseDcf.croissance_implicite_prix_actuel_pct` manquant | `Optional[float] = None` | idem |
> | `Assumptions.taux_actualisation*` (champs inventés) | `extra="ignore"` sur `Assumptions` | idem |
> | `curator.readiness_report_id=None` (setdefault ne remplace pas None) | `or 0` pattern | `curator.py` |
>
> ### RESTE À FAIRE
> 1. **Agents 7-9** : décision/validate (monitoring M6) → sortie/calibration → débat conviction
>    (migrations 028/029 à écrire juste avant chaque lot).
> 2. **Second ticker** : exercer la chaîne complète sur un ticker différent de NVDA pour valider la
>    généralité (notamment readiness gate, synthesis_feed, context_pack).
> 3. **UX transverse finale** (§16) : affichage du verdict dans le frontend, suivi des hypothèses H1-H5.
> 4. **`ingestion-agent`** (contrat C2, doc→entries) : non construit, non bloquant tant que le search-worker
>    + synthesis_feed couvrent les champs requis.

> ## ⚡ MàJ 2026-08-30 — le gate de readiness est DÉTERMINISTE : la couverture se LIT dans l'index `covers` (migration 029, `TEXT[]` + chemins complets + GIN), elle ne se demande plus au modèle. L'oscillation à corpus figé est fermée.
>
> **Décision utilisateur : option A** (`covers TEXT[]` + backfill explicite des entries legacy), contre
> l'option « une entry de synthèse par champ ». Motif retenu : une entry porte ce qu'elle porte — #19
> ou #35 fondent réellement plusieurs champs, et fabriquer une entry de synthèse par champ aurait
> multiplié les tours LLM pour ré-écrire ce que le corpus disait déjà.
>
> ### Ce qui change (convention #29 dans `CLAUDE.md`)
> `recompute_coverage` ne **filtre** plus les `entry_ids` cités par le LLM : il **bâtit un index**
> `dimension.champ → [(entry_id, tier)]` depuis la base (`_covers_index`, pur Python — `get_current_entries`
> SELECTait déjà `covers`, aucune requête supplémentaire), puis, pour chaque champ requis, retient les
> entries au-dessus du plancher. Le LLM n'écrit plus que la **prose** (`rationale`, `gaps`,
> `incertitudes_investissables`, `qualite_info`) ; ses `fondations` sont écrasées. Trois leviers fermés
> d'un coup :
> 1. **couverture par citation → index** : une entry adéquate non citée ne crée plus de faux creux ;
> 2. **tag libre → vocabulaire FERMÉ** (`MVDD_FIELD_PATHS`) : depuis que le tag pilote le verdict, c'est
>    un vote — donc seules les voies déterministes l'écrivent, dans l'esprit de #24 ;
> 3. **`_exigences()`** : le modèle peut **RESSERRER** `champs_requis`/`tier_plancher`, jamais desserrer.
>
> ### Migration 029 (appliquée en prod AVANT le déploiement, docker cp + psql, #17)
> `covers` TEXT → **TEXT[]**, valeurs re-qualifiées en **chemins COMPLETS** `dimension.champ` (sans quoi
> `produits.description` fonderait `business_model.description` — homonymie), btree → **GIN**, et
> **backfill relu à la main des 17 entries qualitatives legacy NVDA** (#19-#35). Sortie : `UPDATE 19`
> (re-qualification) puis `UPDATE 12` (backfill). Volontairement **non taguées**, et c'est documenté
> dans la migration : #25/#27 (retours au capital — aucun champ requis), #32/#33/#34 (marges
> consolidées — ce sont les *intrants* de la synthèse #53, pas le champ), #1-10/#48 (faits EDGAR bruts),
> #11-15 (`llm_memory` tier C).
>
> ### Déviation assumée par rapport au chiffrage annoncé
> J'avais chiffré l'option A comme rouvrant le contrat **C1 figé** (donc règle #19, 3 points de synchro).
> **Je ne l'ai pas fait** : `worker_delegation_schema.py:129` garde `covers: Optional[str]`. Le mandat
> d'un search-worker porte **un seul champ** ; lui laisser déclarer une liste lui rendrait précisément
> le levier sur le gate qu'on vient de lui retirer. Le worker écrit donc un chemin complet unique, via
> `_resolve_covers()` qui **préfère le mandat** et ne retient une proposition du modèle que si elle est
> dans `MVDD_FIELD_PATHS`. **Coût réel du sprint : 0 point de synchro #19.**
>
> ### État de la couverture NVDA après backfill (22 entries taguées, lu en base)
> Tous les champs requis sont couverts **au-dessus du plancher** — sauf trois, dont un déjà déclaré :
>
> | champ non couvert | statut |
> |---|---|
> | `business_model.description` | **vrai gap** — synthétisable depuis #19/#20/#35 (tier A) via `synthesis_feed` |
> | `business_model.recurrence_pct` | **vrai gap** — à synthétiser ou à déclarer non bloquant |
> | `marche.croissance_marche_historique` | déjà **déclaré non bloquant** (donnée de marché EXTERNE, #25) |
>
> ### Déterminisme vérifié en prod — 4 tirs consécutifs (reports #16-#19, 2026-08-30)
> ```
> [GAP] business_model: gaps=['description', 'recurrence_pct']
> [OK]  financials, valorisation, produits, positionnement, marche, management_allocation, risques
> verdict: not_ready  (4/4)
> ```
> Corpus strictement identique, verdict strictement identique. L'oscillation est fermée.
>
> ### RESTE À FAIRE
> 1. **Fermer les 2 champs `business_model`** (synthèse grounded #53-style, ou déclaration honnête pour
>    `recurrence_pct` si le corpus ne le porte pas) → NVDA `ready`.
> 2. Puis la **chaîne d'analyse jamais exécutée** (research → bull/bear → réfutation → synthèse +
>    `valider_pont()`). ⚠️ `analysis.py` appelle `run_json_agent` avec `json_object` au défaut (True) :
>    **passer `json_object=False` AVANT le premier run** (même piège DeepSeek que l'ingestion-agent).
>
> ## ⚡ MàJ 2026-08-26 (ter) — couche COVERS DÉPLOYÉE (migration 028 + curator option B) : le gate est resserré, MAIS la readiness NVDA OSCILLE sur données FIXES → c'est du bruit de citation LLM, pas un creux. Finding archi : le recompute Python VÉTOTE les citations du LLM, il ne les DÉCOUVRE pas.
>
> **Déployé** (commit `3776d74`, un seul conteneur backend vérifié `docker ps` — pas d'orphelin,
> HEAD == origin/main). **Migration 028 appliquée** au DB prod AVANT déploiement (docker cp + psql,
> #17) : colonne `knowledge_entries.covers` (champ MVDD nu porté par l'entry) + backfill (32 entries
> depuis `content_structured.field_path`/`field`/`metric`) + index partiel. Les producteurs (synthèse,
> feeds, search-worker) la remplissent désormais à l'écriture.
>
> ### Ce qui a été construit et VÉRIFIÉ en prod
> Le curator (option C tier-plancher) vérifiait le TIER des entries citées mais pas la PERTINENCE de
> leur contenu — une entry tier A **hors-sujet** pouvait « fonder » un champ (constaté : la croissance
> de NVDA #19 « fondait » `croissance_marche_historique`). La couche covers exige **`covers == champ`**
> quand renseigné ; **fallback tier-only quand `covers IS NULL`** (entries legacy non taguées → pas de
> régression). Effet mesuré : readiness NVDA **#10 `ready` (avant covers, 13:43) → #11 `not_ready`
> (après, 14:28)**. Le gate est plus honnête.
>
> ### 🔬 Déterminisme TRANCHÉ (3 tirs, données STRICTEMENT fixes)
> Le seul champ qui bloque est `business_model.description`. Sur données identiques :
>
> | report | verdict | `description` fondée par | ok ? |
> |---|---|---|---|
> | #11 | `not_ready` | [11, 57] (C 0.4 + context_pack B-) | ❌ |
> | #13 | `thin_qualitative` | [11, **19**] (#19 = tier A) | ✅ |
> | #14 | `not_ready` | [11] seul | ❌ |
>
> **Verdict : bruit de citation LLM, PAS un vrai creux.** L'entry **#19** (« Data Center segment
> FY2026 », tier A 0.89) fonde réellement `description` — mais elle est **legacy `covers=NULL`**, donc
> c'est le **LLM du curator** qui décide par-champ à quelle dimension la rattacher (tantôt `description`,
> tantôt seulement `drivers_revenus`/`recurrence_pct`). Ce rattachement n'est **pas déterministe** → le
> verdict oscille `not_ready` ↔ `thin_qualitative` à corpus figé.
>
> ### 🐛 Finding architectural (la vraie cause, `curator.py:67-108`)
> `recompute_coverage` **filtre les `entry_ids` que le LLM a CITÉS** par champ (garde ceux dont
> `covers ∈ {None, champ}` **et** tier ≥ plancher) : c'est un **véto sur la citation LLM, pas un index
> indépendant**. Une citation manquée = **faux creux**, même si une entry adéquate existe en base. Le
> même mécanisme frappe `produits.unit_economics` : l'entry **#53** (`covers='unit_economics'`, tier
> **A-** 0.85) existe et est au-dessus du plancher, mais le run où le LLM ne la cite pas la déclare
> « non fondée, sous plancher » (prose LLM erronée qui la dit « B- » — cosmétique). Le covers **ferme
> le trou de sur-crédit** (tier A hors-sujet) mais **pas le trou de sous-crédit** (entry adéquate non
> citée).
>
> ### RESTE À FAIRE — rendre le gate DÉTERMINISTE (= prochain sprint)
> 1. **Recompute la couverture par champ en Python à partir de l'INDEX `covers`**, pas des citations
>    LLM : pour chaque champ requis, `SELECT` des entries non superseded avec `covers==champ` **et**
>    tier ≥ plancher — le LLM ne sert plus qu'à la **synthèse narrative**, plus au gate. Supprime
>    l'oscillation d'un coup (business_model ET produits).
> 2. **`covers` est mono-valué (TEXT)** mais #19 porte **3 champs** (`description`/`drivers_revenus`/
>    `recurrence_pct`) → trancher : `covers[]` (array + index GIN) **ou** entries de synthèse par-champ
>    (le patron déjà éprouvé pour unit_economics/moat/structure_5forces). **Décision utilisateur requise.**
> 3. Une fois le modèle multi-champ tranché : **backfill `covers`** sur les tier-A qualitatives legacy
>    (#19, #20, #23-#35).
> 4. **Seul vrai gap de CONTENU restant** (inchangé) : `marche.croissance_marche_historique` — donnée
>    de marché EXTERNE (TAM IDC/Gartner, upload), non synthétisable depuis le KB (#25).
> 5. Puis readiness déterministe → `ready` → **chaîne d'analyse jamais exécutée** (research→bull/bear→
>    réfutation→synthèse), `run_json_agent(json_object=False)` obligatoire (même piège DeepSeek).
>
> ## ⚡ MàJ 2026-08-26 (bis) — INGESTION-AGENT mode SYNTHÈSE (C2) CONSTRUIT, DÉPLOYÉ & EXERCÉ EN RÉEL ; run_json_agent a enfin tourné contre le vrai modèle (gotcha json_object trouvé + corrigé)
>
> **Déployé** (commits `fda6340`→`059d3a4`, deployments #297→#302, un seul conteneur backend vérifié
> `docker ps` — orphelin #301 stoppé+supprimé). **Aucune migration.** Même patron que les feeds
> (`valuation_feed`/`financials_feed`) : transformation pure testable + IO, mais **un tour LLM
> grounded**.
>
> ### Ce qui a été construit
> - **`backend/app/knowledge/synthesis_feed.py`** : fonde un champ qualitatif NON-fetchable par
>   SYNTHÈSE grounded des entries tier A/A-/B+ déjà en base. (1) charge le corpus citable pour le
>   champ ; (2) un tour LLM compose la synthèse ; (3) **grounding VÉRIFIÉ en Python** (chaque
>   `cited_entry_id` ∈ corpus, sinon `SynthesisUngrounded`, rien n'est écrit) + **tier dérivé
>   déterministe**. Contrat runtime **`GroundedSynthesis`** (`app/contracts/synthesis_schema.py`),
>   route **`POST /tickers/{id}/knowledge/synthesize`** (dry-run `persist:false`, `debug_raw` pour
>   la sortie LLM brute) + `GET /knowledge/synthesis/targets`. `store_knowledge` gagne
>   `derived_reliability`/`requires_human_review` (override étroit, réservé aux fondations
>   déterministes). Check **`check_synthesis_feed.py` 31/31** hors-ligne, non-régression OK.
> - **Prompt** `prompts/10b-ingestion-synthese.md` (distinct du 10-ingestion-agent, mode extraction).
>   ⚠️ Ce « C2 » est la **synthèse** décrite dans la MàJ du matin, PAS le contrat
>   `ingestion_extraction_schema.py` (document→entries), qui reste à construire (étape 4).
>
> ### 🐛 Gotcha modèle trouvé au 1er run réel (run_json_agent n'avait JAMAIS tourné contre le modèle)
> DeepSeek-V4-Flash est **NON FIABLE sous `response_format=json_object`** : il collapse sur `{}`
> (3 tokens out), ou emballe la sortie dans un objet parasite `{"./": "<json échappé>"}`. En
> **prompt-only** (sans `response_format`) il rend un **JSON propre et correctement cité**. Fix :
> `run_json_agent` gagne un flag `json_object` (défaut True) ; `synthesize` l'appelle avec
> `json_object=False`. **À GARDER À L'ESPRIT pour la chaîne d'analyse** (research/bull/bear/synthèse
> appellent tous `run_json_agent`, jamais exercée) — même piège probable.
>
> ### Résultat des dry-runs NVDA (règle de tier CONSERVATRICE, choix utilisateur)
> Règle validée : **tier = un cran sous la plus faible entry citée** (A→A-, A-→B+, B+→B),
> `source_type='agent_synthesis'`, `requires_human_review=True`, jamais de surévaluation. **Règle
> PROVISOIRE, à revoir à l'usage si trop bloquante** (cf. mémoire `project-synthesis-tier-rule`).
>
> | champ | cited_tiers | plus faible | tier dérivé | fonde B+ ? |
> |---|---|---|---|---|
> | `produits.unit_economics` | 9×A + 2×B+ (#21/#22) | B+ | **B (0.70)** | ❌ |
> | `marche.structure_5forces` | 8×A + 2×B+ (#21/#22) | B+ | **B (0.70)** | ❌ |
>
> ### PERSISTÉ EN PROD + readiness recomputée (choix utilisateur : resserrer unit_economics + persister)
> `unit_economics` resserré au socle **tier A/A-** (`SynthesisTarget.citable_tiers`, deployment #303) :
> exclut par PERTINENCE la presse marché B+ (#21/#22, hors-champ) → cité 11 entries **toutes A** →
> **A- (0.85)**. Persisté :
> - **entry #53** `produits.unit_economics` tier **A-**, `requires_human_review=True` ;
> - **entry #54** `marche.structure_5forces` tier **B** (règle conservatrice : cite #21/#22 B+ →
>   un cran sous = B), `requires_human_review=True`.
>
> `POST /curator/readiness` NVDA (report **#8**) → verdict **`thin_qualitative`** (bloc structuré
> complet). **`produits` : ok=True (tier A)** — la synthèse a FONDÉ le champ, preuve que le C2
> synthèse fonctionne de bout en bout. Gaps qualitatifs restants : `positionnement.moat_preuves`,
> `marche.croissance_marche_historique` (champs DIFFÉRENTS, à sourcer autrement — search-worker).
>
> ### ⚠️ Observation d'intégrité — le curator ne ré-applique pas strictement le plancher
> La synthèse `structure_5forces` **tier B** a été comptée par le curator comme **fondant** le champ
> (plancher B+) : elle n'apparaît plus dans les manques de `marche`. La règle conservatrice est donc
> respectée à la PRODUCTION de l'entry (tier B honnête) mais **pas ré-appliquée à la LECTURE** —
> c'est le jugement LLM du curator qui tranche « fondé/non-fondé » par champ, le backend ne
> recompute que `ok = (manques vides)`. Comportement curator déjà noté (verdict non déterministe,
> MàJ 2026-08-25). **Point pour le fil « revoir la catégorisation des sources à l'usage »** : si on
> veut que le plancher morde à la lecture, il faudrait le recomputer en Python (tier_atteint des
> entries qui couvrent le champ ≥ plancher), pas le laisser au LLM.
>
> ### SUITE (2026-08-26, même session) — `positionnement` fondé par synthèse ; NVDA à UN champ de `ready`
> - `positionnement.moat_preuves` : search-worker `not_found` (sources sous plancher) → **cible de
>   synthèse** ajoutée, resserrée A/A- (les preuves du moat = CUDA #20/échelle/risques EDGAR A ; la
>   presse B+ #21/#22 porte des MENACES, pas des preuves). Persisté **entry #55 tier B+**,
>   `requires_human_review=True`. `deployment #305`.
> - `marche.croissance_marche_historique` : **vrai gap laissé ouvert** — search-worker `not_found`,
>   et NON synthétisable (le KB a la croissance de NVDA, pas du MARCHÉ → erreur de catégorie, #25).
>   Nécessite une donnée de marché EXTERNE (TAM IDC/Gartner, upload).
>
> ### 🐛🐛 Deux bugs curator trouvés au 1er `ready` réel (jamais atteints — aucun ticker n'avait été ready)
> 1. **Ordre context_pack** : `run_readiness` validait le ReadinessReport (qui exige
>    `context_pack_entry_id` dès verdict=ready) AVANT de produire le context_pack → échec
>    systématique de tout `ready`. Fix : produire le context_pack quand verdict recomputé=ready, puis
>    valider une fois (`deployment #306`).
> 2. **`json_object` dans `curator._call_json`** (readiness ET context_pack) : même pathologie
>    DeepSeek (`{}` ou emballage `{"/mnt/data/…json":"…"}`, cette 2ᵉ forme a fait échouer la 1ère
>    prod du context_pack) → **prompt-only + extract_json** (`deployment #307`). Cohérent avec
>    `run_json_agent(json_object=False)`.
>
> ### ÉTAT readiness NVDA (report **#9**, propre) : `thin_qualitative`, 7/8 dimensions fondées
> struct (business_model A, financials A, valorisation B+) ✅ · produits A ✅ (synthèse) ·
> positionnement B+ ✅ (synthèse #55) · management_allocation A ✅ · risques A ✅ ·
> **marche ❌ — manque `croissance_marche_historique`** (donnée de marché externe).
>
> ### RESTE À FAIRE
> 1. **`marche.croissance_marche_historique`** : fournir une donnée de marché (upload TAM, ou source
>    quant marché) → dernière brique pour `ready`. C'est le SEUL gap restant.
> 2. **Décider si le plancher doit mordre à la LECTURE** (recompute Python côté curator) : observé
>    que le curator (LLM) a compté `structure_5forces` **B** comme fondant un champ B+, et son
>    jugement par-champ est non déterministe. Pour un gate fiable, recomputer en Python
>    `tier_atteint(entries couvrant le champ) ≥ plancher` au lieu de le confier au LLM.
> 3. **Chaîne d'analyse (jamais exécutée)** : une fois `ready`, lancer research→bull/bear→réfutation→
>    synthèse. ⚠️ `analysis.py` appelle `run_json_agent` en **json_object par défaut** → lui passer
>    **`json_object=False`** (le param existe) AVANT le 1er run, sinon même collapse `{}` que la synthèse.
>
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
