# Mesure NVDA — ce qu'une relance des chapitres ferait (avant comité)

Date de la mesure : 2026-10-21. Archétype NVDA : **rentable**. Aucune écriture, aucun appel modèle
payant — `montrer_parcours.sh` (lecture), `recouper_nombres.sh` (lecture), `acceptation_analyste.sh
--admissibilite` (dry-run DB, zéro appel DeepSeek). `ps aux`/`docker ps` vérifiés avant chaque lancer :
aucun autre passage en cours.

## 1. Vue d'ensemble par framework (niveau 1, `montrer_parcours.sh NVDA`)

| Framework | Qualité | Applicables | Manques | #127 standard antérieur | #136 chiffres sans pièce |
|---|---|---|---|---|---|
| Qualité financière | 1.00 (A) | 8/8 | 0 | 3 | 2 |
| Défendabilité / moat | 0.17 (A) | 6/6 | 5 | 3 | 2 |
| Modèle économique | 0.83 (A-) | 6/6 | 1 | 5 | 6 |
| Secteur et concurrence | 0.50 (B+) | 6/6 | 3 | 0 | 0 |
| Management et allocation du capital | 0.00 (A) | 7/7 | 7 | 0 | 0 |
| Valorisation | n/d | 6/6 | 6 | 0 | 0 |

Bilan niveau 1 : **22 manques**, **1 révision à la baisse** (ma_1, voir §3).

## 2. Tableau question → statut → cause → ce que la relance peut espérer

Colonne « admissibilité » = sortie de `acceptation_analyste.sh --admissibilite` (dry-run, 0 appel
modèle) : les statuts que le corpus réel, structurellement, laisse ouverts pour cette question.

### Qualité financière (0 manque — mentionné pour #127/#136 seulement)
| Q | Statut | #127 | #136 |
|---|---|---|---|
| qf_1 | repondu (courante) | | |
| qf_2 | repondu (courante) | | 2 (absents : '194 897', '222 707') |
| qf_3 | repondu (courante) | | |
| qf_4 | repondu (courante) | #127 | |
| qf_5 | repondu (courante) | | |
| qf_6 | repondu (courante) | #127 | |
| qf_7 | repondu (courante) | | |
| qf_8 | repondu (courante) | #127 | |

### Défendabilité / moat
| Q | Statut actuel | Cause | Admissibilité (statuts ouverts) | Ce que la relance peut espérer |
|---|---|---|---|---|
| mo_1 | perimee (#127) | fait_nouveau_publie | repondu, approxime, sans_fondement | le corpus permet un `repondu` (3 pièces citables, tier A) — question seulement rouverte par un fait postérieur (8-K 2026-09-02), pas bloquée |
| mo_2 | perimee (#127) | fait_nouveau_publie | repondu, approxime, sans_fondement | idem — le corpus permet |
| mo_3 | perimee (#127, #136 ×2 absents : '215,94', '87,03') | fait_nouveau_publie | repondu, approxime, sans_fondement | le corpus permet ; mais #136 à surveiller si la relance recopie les mêmes chiffres sans les reccitér |
| mo_4 | non_fondable | recherche_epuisee (2 ingrédients : classe_de_reference, echeances_contractuelles_ou_legales — search-worker n'a rien retenu) | repondu, approxime, sans_fondement | le corpus *structurellement* permet un `repondu` (3/40 citables, tier A) — l'échec constaté est une absence de résultat de RECHERCHE WEB, pas un manque de pièce déjà en base ; une relance peut ramener autre chose |
| mo_5 | repondu (courante) | — | — | déjà acquitté |
| mo_6 | non_fondable | pieces_insuffisantes | repondu, approxime, sans_fondement | le corpus permet *mécaniquement* un `repondu` (mêmes 3/40 citables que mo_1-5) mais le passage réel a jugé insuffisant sur le FOND — l'admissibilité ne garde que la structure, jamais le sens (#68) ; une relance peut ou non changer ce jugement de fond |

### Modèle économique
| Q | Statut actuel | Cause | Admissibilité | Ce que la relance peut espérer |
|---|---|---|---|---|
| me_1 | repondu (#127, #136 : '7,5' absent) | — | — | acquitté |
| me_2 | repondu (#127, #136 : '1,8' absent) | — | — | acquitté |
| me_3 | repondu (#136 ×2 : '71,1', '74,7') | — | — | acquitté |
| me_4 | repondu (#127, #136 ×2 : '104,8', '164 269') | — | — | acquitté |
| me_5 | approxime (#127) | — | — | acquitté |
| me_6 | perimee | fait_nouveau_publie (chiffre `poids_des_premiers_clients` antérieur à la clôture 2026-07-26) | repondu, sans_fondement (approxime écarté, plancher A) | le corpus permet un `repondu` — seulement rouverte par la clôture plus récente |

### Secteur et concurrence
| Q | Statut actuel | Cause | Admissibilité | Ce que la relance peut espérer |
|---|---|---|---|---|
| se_1 | repondu | — | — | acquitté |
| se_2 | non_fondable | pieces_insuffisantes | repondu, approxime, sans_fondement | le corpus permet *mécaniquement* (12/66 citables, tiers A/B+) mais le passage réel a jugé insuffisant sur le fond — même réserve que mo_6 |
| se_3 | repondu | — | — | acquitté |
| se_4 | repondu | — | — | acquitté |
| se_5 | perimee | fait_nouveau_publie (`reaction_de_l_entreprise`, pièce la plus récente 2025-12-24, clôture 2026-07-26) | repondu, approxime, sans_fondement | le corpus permet un `repondu` |
| se_6 | perimee | fait_nouveau_publie (même historique `reaction_de_l_entreprise`) | repondu, approxime, sans_fondement | le corpus permet un `repondu` |

### Management et allocation du capital
| Q | Statut actuel | Cause | Admissibilité | Ce que la relance peut espérer |
|---|---|---|---|---|
| ma_1 | non_fondable, **révisé à la baisse le 2026-10-16** (← #1475 `repondu`, raison analyste : pas de répartition pluriannuelle 5-10 ans ni rendement par usage) | pieces_insuffisantes | repondu, sans_fondement (approxime écarté, plancher A) | le corpus permet *mécaniquement* un `repondu` (17/51 citables, tier A) ; la baisse vient d'un jugement de fond plus exigeant (horizon pluriannuel), pas d'une perte de pièces |
| ma_2 | non_fondable | pieces_insuffisantes | repondu, approxime, sans_fondement | le corpus permet mécaniquement (18/51 citables) ; même réserve fond/structure |
| ma_3 | non_fondable | **source_indisponible** — collecte web échouée (AgentOutputInvalid), ingrédient `valeur_au_moment_de_l_operation` | repondu, approxime, sans_fondement | le corpus permet mécaniquement un `repondu` — l'échec réel est une panne d'agent (voir §4), pas un manque de pièce en base |
| ma_4 | non_fondable | **source_indisponible** — ingrédient `cessions_et_achats_des_dirigeants` (AgentOutputInvalid) + `detention_des_dirigeants` (recherche_epuisee, status=not_found) | repondu, sans_fondement (approxime écarté, plancher A) | le corpus permet mécaniquement un `repondu` — deux pannes de recherche distinctes (voir §4) |
| ma_5 | non_fondable | pieces_insuffisantes | repondu, approxime, sans_fondement | le corpus permet mécaniquement (18/51 citables) ; réserve fond/structure |
| ma_6 | perimee | fait_nouveau_publie (`independance_du_conseil`, pièce du 2026-05-12, fait du 2026-07-02) | repondu, approxime, sans_fondement | le corpus permet un `repondu` |
| ma_7 | perimee | fait_nouveau_publie (`criteres_de_remuneration`, pièce du 2026-01-25, fait du 2026-07-02) | repondu, sans_fondement (approxime écarté, plancher A) | le corpus permet un `repondu` |

### Valorisation (6/6 en manque, aucune collecte lancée)
| Q | Statut actuel | Cause | Admissibilité | Ce que la relance peut espérer |
|---|---|---|---|---|
| va_1 à va_6 | sans_reponse | pas_encore_cherchee | **0 pièce remise sur 399 courantes** — `repondu`/`approxime` écartés (0 citable) ; seul `sans_fondement` ouvert → sort en `non_fondable` SANS appel modèle (#40) | **manque une source** : le framework Valorisation n'a aucune chemise classée pour NVDA (0 pièces/0 chemises contre 399 pièces du titre au total) — une relance de CE chapitre ne produira RIEN tant que des pièces n'auront pas été classées dans `valorisation` ; ce n'est pas une panne d'agent, c'est une collecte jamais lancée |

## 3. Révision à la baisse (point 13)

- **ma_1** : réponse courante `#1499` (`non_fondable`) ← précédente `#1475` (`repondu`, 2026-10-16T11:04:23Z).
  Raison de l'analyste : « Le corpus ne fournit pas de répartition pluriannuelle (5 à 10 ans) des
  usages du cash généré ou levé (réinvestissement, acquisitions, rachats, dividendes, dette) ni le
  rendement de chaque usage. » La précédente réponse (résumé) : allocation sur l'exercice clos
  2026-01-25 — 82,4 % rachats (40,09 Md$), 12,4 % réinvestissement (6,04 Md$), 3,1 % acquisitions
  (1,53 Md$), 2,0 % dividendes (974 M$) ; politique annoncée de rachats portée à 235 Md$ (horizon
  FY2028), dividende relevé de 0,01 $ à 0,25 $/action.
  C'est un durcissement de l'EXIGENCE (horizon pluriannuel), pas une perte de pièce — l'admissibilité
  (§2, ma_1) montre que le corpus permet toujours mécaniquement un `repondu` sur un seul exercice.

## 4. `source_indisponible` (ma_3, ma_4) — panne transitoire ou stable ? Éléments, sans trancher

Les deux ingrédients en échec (`valeur_au_moment_de_l_operation` pour ma_3, `cessions_et_achats_des_dirigeants`
pour ma_4) échouent par la **même classe d'erreur** : `AgentOutputInvalid` — le search-worker produit,
après 8 tentatives, un JSON qui ne respecte PAS le contrat `WorkerResponse` (Pydantic), pour la MÊME
raison dans les deux cas :

> `Value error, extrait de moins de 20 caractères, non discriminant (#126)` — ex. `'$198.89'` (ma_3),
> `'X Director'` (ma_4).

Éléments factuels :
- **Une seule date d'observation** pour chaque ingrédient : `2026-10-16T14:43:25Z` (ma_3) et
  `2026-10-16T14:49:16Z` (ma_4) — 6 minutes d'écart, même session de collecte. Aucune deuxième mesure
  à une date différente n'est visible dans ce dossier pour comparer.
- Les deux échecs viennent de la même règle de contrat (#126, extrait ≥ 20 caractères) rejetant des
  valeurs structurellement COURTES (un prix d'action, un titre de fonction) — donc le même type de
  contenu bref échoue deux fois dans la même session, après 8 tentatives chacun (coût facturé :
  0,0162 $ et 0,0189 $, déjà dépensé lors du passage précédent, pas lors de cette mesure).
- `ma_4` porte EN PLUS un second ingrédient en échec par une cause différente :
  `detention_des_dirigeants` → `recherche_epuisee` (search-worker n'a rien retenu, `status=not_found`)
  — absence de résultat, pas un rejet de contrat.
- L'admissibilité à blanc (§2) montre que, structurellement, le corpus laisse `repondu` ouvert pour
  ma_3 et ma_4 : rien n'indique que le corpus lui-même manque de pièces pour ces deux questions —
  l'échec vient de la CHAÎNE DE COLLECTE WEB (search-worker), pas de la base déjà classée.
- Le mémoire projet (`feedback_blocage_classifieur_non_permanent.md`) rapporte un cas où un refus
  stable sur 4 sessions a fini par se lever : ce précédent existe, mais rien dans CETTE mesure ne
  permet de dire si le cas ma_3/ma_4 est du même type (un seul point de mesure, une seule session).

**Je ne tranche pas** : les éléments disponibles ne permettent de dire ni que c'est transitoire
(aucune relance effective n'a été rejouée pour voir si le search-worker produit un extrait plus long
la fois suivante) ni que c'est stable (une seule session observée, pas 4 comme dans le précédent cité).

## 5. Recoupement des nombres (`recouper_nombres.sh NVDA <framework>`, les 6 frameworks)

| Framework | Réponses | Nombres recoupés | Absents des pièces citées |
|---|---|---|---|
| qualite_financiere | 8 | 48 | 2 |
| defendabilite | 6 | 20 | 2 |
| modele_economique | 6 | 57 | 6 |
| secteur_concurrence | 6 | 38 | 0 |
| management_capital | 7 | 8 | 0 |
| valorisation | 0 | 0 | 0 |

Détail des 12 chiffres ABSENTS (portés par d'autres pièces COURANTES du titre mais non cités par la
réponse qui les emploie — signe d'une citation manquante, jamais une citation à rattacher) :

- **qf_2** (#1210) : `194 897` et `222 707` — absents, aucune pièce porteuse alternative listée.
- **mo_3** (#1436) : `215,94` — porté par #592, #838, #867, #1018 (non citées) ; `87,03` — absent, sans porteuse listée.
- **me_1** (#1366) : `7,5` — porté par #839, #840, #867, #880 (non citées).
- **me_2** (#1367) : `1,8` — porté par #389, #860, #836, #863 (non citées).
- **me_3** (#1368) : `71,1` — porté par #1458, #1459, #1511 (non citées) ; `74,7` — porté par #1338, #1340, #1335 (non citées).
- **me_4** (#1369) : `104,8` — absent, sans porteuse listée ; `164 269` — porté par #988, #1003, #1014 (non citées).

Également signalé (hors #136) : `qf_7` (#1214) cite une pièce #864 **hors du corpus courant du titre**
(pièce périmée/non courante encore citée).

## 6. Sur le plafond du dossier de collecte

Les admissibilités à blanc signalent, pour 3 des 6 frameworks (qualite_financiere, secteur_concurrence,
management_capital), un **PLAFOND INSUFFISANT** : 51, 66 et 51 pièces à remettre contre un plafond de
40 (`ACCEPTATION_CORPUS_MAX`, ici au défaut). Aucune pièce n'a été coupée dans ces mesures d'admissibilité
(l'outil le signale explicitement), mais ce même plafond s'appliquerait à une relance réelle via
`executer_chaine.sh` — à vérifier séparément si une relance réelle est engagée, hors périmètre de
cette mesure (lecture seule).

## 7. Synthèse en 5 lignes

1. 22 manques sur 39 questions applicables (6 frameworks) ; 15 sont des `perimee`/`non_fondable` où
   l'admissibilité dit que le corpus permet mécaniquement un `repondu` — une relance a des chances d'y
   répondre.
2. Les 6 questions de Valorisation (va_1-va_6) ne peuvent RIEN espérer d'une relance : 0 pièce classée
   dans ce framework pour NVDA — il manque une source (classement), pas un appel modèle.
3. ma_3/ma_4 échouent par une panne de recherche web (`AgentOutputInvalid`, règle #126 sur extraits
   courts, et un `recherche_epuisee`) observée une seule fois le 2026-10-16 ; transitoire ou stable
   non trancheable avec cette seule mesure.
4. ma_1 a été révisée à la baisse le 2026-10-16 par un durcissement de l'exigence (horizon
   pluriannuel), pas par une perte de pièce — le corpus permet toujours un `repondu` sur un exercice.
5. 12 chiffres (#136) ne sont pas recoupés à leurs pièces citées dans 3 frameworks (qf, mo, me) ; 11
   questions portent le `standard antérieur` (#127) — un relancement devra re-vérifier ces citations,
   pas seulement rouvrir les questions périmées.
