---
id: spec-autorite-vs-actualite
status: figée
created: 2026-09-05
project: portfolio-tracker
role: >
  Décide comment le corpus V2 arbitre entre l'AUTORITÉ d'une source (EDGAR, dépôts réglementaires)
  et l'ACTUALITÉ d'un fait (communiqués, presse, experts sectoriels suivis). Remplace le scalaire
  `reliability_score` par trois axes jamais recombinés, ouvre l'admission des sources par un
  registre curé à la main, et donne des dents à la péremption sans donner de voix à une heuristique.
---

# Autorité contre actualité — révision du modèle de fiabilité

## Le défaut, mesuré

Sur RVMD, au 2026-09-05, corpus actif :

| Tier | Entries | Score moyen | Source la plus ancienne | La plus récente |
|---|---|---|---|---|
| A | 24 | **0,931** | 2025-12-31 | 2026-08-26 |
| B+ | 3 | **0,750** | 2026-09-04 | 2026-09-04 |

**L'information la plus fraîche du corpus est la moins bien classée.** Quatre entries tier A
affirment « aucun produit approuvé pour la vente commerciale » alors que la FDA a approuvé RASONQUE
le 2026-08-26. Aucune n'est fausse : chacune est fidèle à sa source et correctement datée.

⚠️ **Correction du 2026-09-05.** Ce paragraphe affirmait « le `readiness` prononce néanmoins
`ready`, 0 gap » **sur RVMD** : c'est FAUX, et vérifié comme tel en base. RVMD n'a jamais eu de
rapport `readiness`, ne couvre que 10 des 19 champs et n'a aucune dispense — il sortirait
`not_ready` pour **lacune**. Le faux vert `ready, 0 gap` est réel mais il est **persisté sur NVDA et
MSFT** (rapports #26/#27 du 2026-08-31), dont les corpus, eux, sont complets. Le diagnostic ci-dessous
est inchangé — c'est la **pièce à conviction** qui changeait d'émetteur, et avec elle le test
d'acceptation de la capacité 4. Famille de #42 appliquée à la spec elle-même : *tous les nombres du
tableau justes, le fait énoncé faux*.

Trois causes structurelles, vérifiées dans le code (2026-09-05) :

1. **La porte de complétude ne lit que le `tier`, et le `tier` ne bouge jamais.**
   `compute_reliability` module le *score* selon l'âge (−0,05/an financier, −0,02/an qualitatif),
   mais son contrat dit explicitement « le tier NE change pas à la modulation » ; le curator lit
   `reliability_tier` (`curator.py:127`). **Toute la temporalité est invisible à la porte, par
   construction.**
2. **Le score est figé à l'écriture.** Les seuls `UPDATE knowledge_entries` du code touchent
   `superseded_by` et `embedding`. Une entry écrite le jour de sa source garde son 0,95
   indéfiniment : le corpus ne vieillit pas. La décote ne pénalise que ce qui était **déjà vieux à
   la collecte** — jamais ce qui vieillit ensuite.
3. **Les leviers de corroboration sont morts.** `cross_validated` (+0,10) et `has_conflict` (−0,20)
   sont câblés de `store_knowledge` jusqu'à `compute_reliability` ; **aucun appelant de production
   ne les passe à `True`**.

**Le diagnostic n'est donc pas « le barème est mal réglé ».** Un scalaire unique porte deux
propriétés orthogonales — *à quel point je fais confiance à cette source* et *ce fait décrit-il
encore le monde* — et les confond. C'est la famille des conventions #42 (tous les nombres justes,
le fait faux) et #44 (trois états jamais confondus), appliquée au scoring lui-même.

## Principe directeur

**Un fait a trois propriétés indépendantes, et on ne les recombine jamais en un nombre.**

| Axe | Ce qu'il mesure | Où il vit | Pourquoi là |
|---|---|---|---|
| **fiabilité** | l'autorité de la source | **stocké** | propriété de la source, immuable une fois la source connue |
| **actualité** | le fait décrit-il le présent | **calculé à la LECTURE** | propriété d'une *relation* entre le fait et maintenant : la stocker la fige, et c'est exactement le défaut n°2 |
| **nature** | ce que l'assertion prétend être | **stocké** | propriété de l'assertion : mesure chiffrée · événement · interprétation |

**La nature commande.** Elle décide quel axe fait autorité pour un champ donné :

- **mesure** (trésorerie, capex, capitaux propres) → la fiabilité domine. EDGAR est imbattable ; un
  blog qui recopie le chiffre n'ajoute rien et introduit un risque de transcription.
- **événement** (approbation FDA, contrat, départ d'un dirigeant) → l'actualité domine. Un
  communiqué du jour bat un 10-K de six mois, et la fiabilité n'a qu'à franchir un plancher.
- **interprétation** (pourquoi ce marché croît, ce que l'approbation change au TAM) → l'expertise
  domine. La section « facteurs de risque » d'un 10-K est du boilerplate juridique ; un analyste qui
  suit le secteur est **strictement meilleur**, et le système le classe aujourd'hui 0,50.

**Corollaire, et c'est le cœur de la révision :** le standing d'une source n'est pas une propriété
de la source, c'est une propriété du **couple (source × nature)**. Un substack d'expert biotech peut
valoir B+ sur une interprétation et rester C+ sur une mesure chiffrée. Une table à une seule entrée
par domaine ne peut pas exprimer ça — c'est pourquoi le correctif n'est pas « monter les blogs ».

### Ce qu'on refuse de faire

- **Jamais de score composite.** Trois nombres qu'on recombine redeviennent un scalaire, et
  reproduisent le défaut au premier arrondi. La porte lit un **triplet**.
- **Jamais de promotion automatique d'un domaine inconnu.** Ni par corroboration : en biotech, *N*
  blogs recopiant le même communiqué ne sont pas *N* sources indépendantes — la corroboration
  deviendrait un amplificateur de rumeur. L'admission est **nominative et humaine**.
- **Jamais de `superseded_by` écrit par le système.** Décider qu'un fait est remplacé est un
  jugement sémantique (#29, `feedback_optional_schema_gate`). Le système *signale*, il ne décide pas.
- **Jamais demander sa nature au modèle sans filet.** La nature se dérive de manière déterministe
  (champ couvert · `source_type` · `entry_type`) ; le modèle peut **RESSERRER**, jamais desserrer —
  transposition directe de #29 et #24.
- **L'actualité se mesure sur la date du FAIT, jamais sur celle de la publication.** Un article de
  ce matin qui commente un trimestre clos en juin est daté de juin. Règle déjà tenue par
  `material_events` (tri sur `reportDate`, pas `filingDate`) et par #42.

## Capacités (ordre imposé)

**Justification de l'ordre — elle est load-bearing.** Le réflexe serait de durcir la porte d'abord,
puisque c'est là qu'est le faux vert. **Ce serait une panne** : sans sources fraîches admissibles,
tout champ deviendrait `couvert_perime` sans remède disponible, EDGAR ne déposant que
trimestriellement. **Le registre des sources (2) doit précéder le durcissement (4).** De même, la
nature (1) précède tout, puisque c'est elle qui donne un sens aux planchers.

---

### 0. La doctrine et la table de profils par champ · contexte partagé : ce document, `CLAUDE.md` #29/#42/#44, `01-spec-v2-unifiee.md` §6.3

Aucun code. Le livrable est la **table des 19 champs MVDD** : pour chacun, sa nature dominante, le
plancher de fiabilité, et si l'actualité est bloquante. C'est le seul endroit où le jugement métier
s'exprime, et il se co-écrit — l'agent ne le remplit pas seul.

- [x] Statuer champ par champ : nature dominante · plancher fiabilité · actualité bloquante O/N
      → `agents/v2/common.py: FIELD_PROFILES`, détenteur **unique**, adjacent à `MVDD_SPEC` pour que
      les 19 chemins et leurs profils ne puissent pas diverger.
- [x] Nommer les champs où un 10-K est **insuffisant** malgré son tier A → `risques.risques_cles`,
      `marche.structure_5forces`, `positionnement.moat_preuves`, `positionnement.position_vs_pairs`
      (desserrés B+ → B, **effet conditionné à la capacité 2**). ⚠️ `business_model.drivers_revenus`
      était candidat mais reste à **B+** : le dépôt y est légitime, c'est son *actualité* qui manque
      — d'où `actualite_bloquante=True` plutôt qu'un desserrage. Confondre les deux ouvrirait
      l'admission là où le remède est un rafraîchissement.
- [x] Nommer les champs où une source non-EDGAR ne doit **jamais** suffire → les 4 `financials.*`
      (plancher **A**, seuls `edgar_official` et `company_ir_official` l'atteignent).
- [x] Convention **#50** dans le `CLAUDE.md` du projet
- [x] **Acceptation tenue** : `check_field_profiles.py`, **174 assertions / 0 échec**. Test négatif
      **5/5 concluants**, chacun rouge sur un assert **nommé** et le script allant jusqu'au bout :
      ligne retirée · desserrage tacite · motif nommant un émetteur · profil orphelin · score
      composite réintroduit.
- 📌 **Résultat de rédaction, load-bearing pour la capacité 1** : **aucun** des 19 champs n'a
  `evenement` pour nature dominante. Un événement ne *fonde* aucun champ, il *périme* les autres
  natures — c'est ce qui justifie que l'actualité soit une **troisième colonne** et non une
  conséquence de la nature. `evenement` reste au vocabulaire des **entries** (migration 034).

### 1. L'axe `nature`, dérivé déterministe · contexte partagé : `knowledge/service.py`, `agents/v2/worker.py`, migration 034

- [x] Migration **034** : colonne `nature` (`mesure`|`evenement`|`interpretation`), CHECK nommé,
      index partiel `(ticker_id, nature)`, `NOT NULL`. Backfill de **180 lignes** — pas seulement
      les ~134 actives : une entry superseded reste lue par `analysis_knowledge_refs` (snapshot figé
      A1/A2), et c'est ce qui permet de poser le `NOT NULL` dans la même migration.
- [x] Détenteur **unique** (#46) : `agents/v2/common.py: derive_nature`, appelé par
      `store_knowledge` — **seul passage obligé des 8 producteurs**, donc aucun feed n'a d'endroit
      où la ré-implémenter. `store_knowledge` n'accepte pas de paramètre `nature`.
      ⚠️ Le backfill lui-même passe par la règle : `_gen_034.py` l'appelle sur un instantané `psql`
      et n'émet que des listes d'ids. Un `UPDATE … CASE WHEN` aurait écrit la règle une seconde
      fois, en SQL — exactement le défaut de `_current_fact_ids` ré-implémenté par tags (#43).
- [x] Le modèle peut resserrer, jamais desserrer : `declared` n'est honoré que pour **promouvoir
      vers `evenement`**, seule nature qui SOUMET l'assertion à l'horloge matérielle. Tout autre
      mouvement est écarté **en le disant** dans le motif.
- 📌 **Résultat de dérivation, load-bearing pour la capacité 4** : la nature d'une ENTRY ne se dérive
  **pas** de la nature dominante du CHAMP (convention **#51**). Les deux vocabulaires diffèrent —
  `valorisation.base_rate_anchor` est un champ d'*interprétation* rempli par une *fréquence
  empirique*, donc une entry `mesure`. Les faire coïncider par construction supprimerait la
  confrontation que la porte doit opérer, et rendrait `evenement` inatteignable.
- 📌 **`evenement` est une classe VIDE après backfill, et c'est déclaré dans la migration** : aucun
  producteur n'écrit encore d'entry adossée à un 8-K/6-K (`material_events` signale et n'écrit rien,
  #49). Le canal `nature_declaree` n'a donc **aucun émetteur** — état volontaire, à ne pas confondre
  avec le défaut de #50 : l'absence de déclarant rend la nature 100 % déterministe, donc plus
  stricte. Il se remplira avec la capacité 3, qui introduit l'événement de bout en bout ; c'est là,
  et pas avant, que l'ajout d'un champ au contrat C1 (règle #19, 3 points de synchro) se justifie.
- **Acceptation TENUE** : `check_entry_nature.py`, **50 assertions / 0 échec**. §7 lit l'**état
  persisté** (#43, pas le diff) : 0 `NULL` sur les entries actives, 0 nature hors vocabulaire, et
  les 13 entries déterministes RVMD **nommées une par une** sont toutes `mesure` — le compte 13 est
  lui-même asserté, sans quoi « toutes `mesure` » serait vrai sur zéro ligne. Répartition :
  **66 `mesure` / 68 `interpretation` / 0 `evenement`**.
- **Test négatif 5/5 concluants**, chacun rouge sur un assert **nommé**, script allant jusqu'à son
  bilan : (1) la source ne démote plus → 6 FAIL ; (2) la déclaration de l'agent honorée sans
  arbitrage → 3 FAIL, dont le cas exigé par cette spec (fait EDGAR requalifié `interpretation`) ;
  (3) la nature de l'entry dérivée du champ → 4 FAIL ; (4) unanimité de `covers` remplacée par « au
  moins un » → 2 FAIL ; (5) **état persisté corrompu en base** (une entry déterministe reclassée)
  → 1 FAIL nommant l'id. ⚠️ Le cas (5) est indispensable et **séparé** : §7 lit la base, donc aucun
  sabotage de la RÈGLE ne peut le faire rougir — un test négatif portant seulement sur le code
  aurait laissé §7 non éprouvé.
- **Suite** : 1 561 assertions / 0 échec / 20 scripts (`bash checks/run_all.sh`).

### 2. Le registre des sources admissibles, curé à la main · contexte partagé : `knowledge/websearch.py` (`_ISSUER_DOMAINS`, `classify_source_type`), convention #33

- [x] Registre clefé par **secteur** et/ou **ticker**, sur le modèle à deux niveaux de #33, portant
      pour chaque source : domaine, nature(s) pour lesquelles elle a standing, tier accordé, **date
      d'admission** et **motif** écrit → `knowledge/source_registry.py`, `SourceAdmise` (frozen
      dataclass, `__post_init__` refusant un tier non supporté, des natures vides ou hors
      vocabulaire, un motif vide). Portée = `"secteur:<nom>"` **ou** `"ticker:<id>"`, sur le même
      pied ; `_TICKER_SECTEURS` rattache le ticker à son secteur.
      ⚠️ **Le secteur est déclaré en code, pas lu en base, et c'est une mesure qui l'a décidé** :
      `tickers.sector` est **NULL sur les 17 tickers**. Un registre clefé sur cette colonne
      n'aurait admis personne, **silencieusement** — exactement #32 (un plancher qu'aucun domaine
      ne peut atteindre) transposé à une clef de jointure.
- [x] Amorçage biotech clinique pour RVMD (≥ 2 sources non-EDGAR), validé par l'utilisateur :
      **`endpts.com`, `statnews.com`, `fiercebiotech.com`, `biopharmadive.com`** — portée
      `secteur:biotech_clinique`, natures `{interpretation}`, tier **B**, admises le 2026-09-05
      avec motif écrit. Plafond du registre arrêté à **B** par l'utilisateur : une source de presse
      spécialisée interprète, elle ne mesure pas.
- [x] Un domaine inconnu reste `web_search_generic` 0,50 — inchangé (assert §3)
- **Acceptation TENUE** : `check_source_registry.py`, **75 assertions / 0 échec**. §2 est l'assert
  central du couple (source × nature) : `endpts.com` **promu** sur une `interpretation`, **refusé**
  sur une `mesure` — et le refus est **dit** (« aucun standing sur `mesure` » ajouté au motif),
  jamais muet. §3 : un domaine hors registre reste `web_search_generic`. §5 : NVDA, hors secteur,
  n'hérite de rien.
- 📌 **L'ordre `nature` PUIS `registre` est load-bearing** : `qualify()` dérive la nature depuis le
  `source_type` **générique**, et n'applique le registre que si ce source_type vaut encore
  `web_search_generic`. Le premier câblage repliait la promotion dans `classify_source_type` —
  `endpts.com` sortait alors `web_search_reputable` **avant** toute question de nature, la
  condition ne s'appliquait plus, et une source admise pour l'interprétation gagnait du standing
  sur une mesure. Défaut rattrapé avant exécution, puis **gardé** par le cas négatif 2.
- 📌 **Plafond ≠ qualification** : `websearch.source_type_max()` (le plafond montré au modèle dans
  les résultats de recherche) est une **seconde** fonction, pas une modification de
  `classify_source_type`, qui reste générique et sans registre. §7 asserte la distinction.
- [x] Qualification **avant** scoring dans `store_knowledge`, et appel dans `worker.py` **avant**
      le filtre `reliability_min` : le worker rejette sous plancher avant que `store_knowledge`
      soit atteint — sans ce second site, le registre n'aurait admis personne tout en paraissant
      câblé.
- **Test négatif 5/5 concluants**, chacun rouge sur un assert **nommé**, script allant jusqu'à son
  bilan : (1) condition de nature retirée → 4 FAIL ; (2) registre replié dans `classify_source_type`
  → 5 FAIL ; (3) admission élargie à `mesure` → 5 FAIL ; (4) portée ignorée → 2 FAIL ; (5) plafond
  de tier élargi en silence → 2 FAIL.
- ⚠️ **Aucune section « état persisté » dans le check, et c'est écrit dans sa docstring** : la
  capacité 2 n'écrit rien en base. Une section SQL aujourd'hui serait verte sur zéro ligne —
  **fixture non discriminante**, le premier des trois faux verts (#47/#49).
- ⚠️ **Écart mesuré et laissé ouvert — `_DESSERRAGE_NON_CABLE` (§1bis)** : le desserrage B+ → B de la
  capacité 0 vit dans `FIELD_PROFILES` (la doctrine), alors que la porte de production lit
  `FIELD_PLANCHER_OVERRIDES`, qui ne contient que `marche.croissance_marche_historique`. Mesuré :
  les planchers de dimension `positionnement` et `marche` valent **B+**. Donc une entry `endpts.com`
  à B (0,65) est admise par le registre et **encore refusée par la porte**. Le câblage appartient à
  la **capacité 4** (`curator.recompute_coverage`, son `contexte partagé`) : déplacer les planchers
  maintenant perturberait la ligne de base que son test central doit mesurer AVANT le lot. L'assert
  « la liste des écarts ne survit pas à leur câblage » vire au vert de lui-même le jour du câblage.
- ⚠️ Piège #33 : une règle spécifique ne resserre jamais la règle générique au passage (assert §4 :
  le registre ne **démote** jamais — `sec.gov` traverse `qualify` intact).
- 📌 **Deux suites du lot, décidées avec l'utilisateur, non commencées** :
  1. **FDA/EMA en régulateur A- (0,85)** — mesuré : `fda.gov` n'est dans **aucune** table, et
     `_EU_REGULATOR_SUFFIXES` porte `esma.europa.eu` (titres) mais pas `ema.europa.eu`
     (médicaments). L'approbation FDA du 2026-08-26, l'événement même qui a ouvert cette spec,
     classe aujourd'hui `web_search_generic` 0,50. Un `regulator_filing_us` touche
     `SOURCE_RELIABILITY_BASELINE`, le `Literal SourceType`, le frontend **et les 12 prompts v2 en
     base** (tous énumèrent les source_types) → **migration 035** + règle #19. Lot séparé à dessein.
  2. **File de propositions** — le système observe les domaines `web_search_generic` réellement
     rencontrés, **recommande** un classement (portée, natures, tier), l'utilisateur **valide**.
     L'admission reste un acte humain : rien ne se promeut tout seul (#50, pas de promotion
     automatique fût-ce par corroboration).
- **Suite** : 1 638 assertions / 0 échec / 21 scripts (`bash checks/run_all.sh`).

### 3. L'axe `actualité`, calculé à la lecture · contexte partagé : `knowledge/material_events.py`, `knowledge/staleness.py` (livrés le 2026-09-05)

- [ ] Trois états relatifs à l'ancre matérielle : `courante` · `perimee` · `indeterminable`
      (`source_date IS NULL` — indéterminable n'est pas fraîche, #44)
- [ ] **Jamais persisté** : recalculé à chaque lecture, ce qui dissout le défaut n°2 par construction
- [ ] Propager l'état `indeterminable` du balayage quand le flux d'événements est injoignable — une
      panne réseau ne doit jamais se lire « rien n'a changé »
- **Acceptation** : la **même** entry, lue avant et après l'arrivée d'un 8-K postérieur, change
  d'état **sans qu'aucun `UPDATE` ne soit émis** (garde par grep de source, comme `staleness.py`).

### 4. La porte de complétude à trois états · contexte partagé : `agents/v2/curator.py` (`recompute_coverage`), convention #29

- [ ] `couvert` · `couvert_perime` · `non_couvert` — jamais deux confondus
- [ ] Deux remèdes **distincts** : mandat de **rafraîchissement** (le champ a des entries, elles
      sont datées) contre mandat de **collecte** (le champ n'a rien). Les confondre fait payer une
      recherche complète là où un rafraîchissement suffisait
- [ ] Le verdict global distingue `not_ready (péremption)` de `not_ready (lacune)`
- **Acceptation, et c'est le test central de toute la révision** — ⚠️ **ligne de base corrigée le
  2026-09-05, la rédaction initiale visait le mauvais émetteur.** Vérifié en base : RVMD n'a **jamais
  eu de rapport `readiness`** (`knowledge_curator_reports` ne porte que NVDA et MSFT), ne couvre que
  **10 des 19 champs** et n'a **aucune dispense** — il sortirait donc `not_ready` **pour lacune**
  aujourd'hui. Le test « RVMD passe de `ready` à `not_ready` » aurait viré au vert sans rien prouver :
  **fixture non discriminante**, le premier des trois faux verts (§24). Le faux vert `ready, 0 gap`
  est persisté sur **NVDA et MSFT** (rapports #26/#27, 2026-08-31) — ce sont eux les porteurs.
  - **Test central** : **NVDA et MSFT** doivent passer de `ready, 0 gap` à **`not_ready` avec cause
    `péremption`**, en nommant les champs concernés, **sans** les compter comme lacunes de collecte.
  - **Test de séparation** (RVMD) : le verdict doit distinguer ses **9 lacunes de collecte** de ses
    champs périmés — les deux causes ne se confondent jamais, et les deux remèdes non plus.
  - Les 9 champs non couverts de RVMD, pour mémoire : `business_model.recurrence_pct`,
    `financials.intensite_capex_pct`, `produits.description`, `produits.unit_economics`,
    `positionnement.moat_preuves`, `positionnement.position_vs_pairs`, `marche.structure_5forces`,
    `management_allocation.incitations`, `management_allocation.skin_in_game_pct`.
- ⚠️ Risque assumé : un 8-K de routine (item 9.01, pièces jointes) ne doit périmer personne. Le
  filtre `items_substantiels` de `material_events.py` existe déjà — le brancher, et **le prouver par
  un cas négatif** (un 8-K purement formel laisse le corpus `courant`).

### 5. La contradiction, signalée jamais tranchée · contexte partagé : `knowledge/service.py` (`has_conflict`, `conflict_entry_id`), convention #43

- [ ] Activer les leviers morts : deux entries qui répondent à la **même question** (clef d'identité
      #43 + index `covers`) et divergent sont **mutuellement** marquées
- [ ] File d'arbitrage humain exposée en lecture, avec le motif et les deux extraits
- [ ] **Aucune écriture de `superseded_by`** par le système (garde par grep, comme `staleness.py`)
- **Acceptation** : sur RVMD, l'entry du communiqué FDA (2026-08-26) et les quatre entries « aucun
  produit approuvé » sont mutuellement marquées et remontent dans la file. Test négatif : deux
  entries qui couvrent des champs **différents** ne doivent **pas** être appariées.

---

## Coût, risques, et ce qui pourrait invalider cette révision

**Coût.** Capacités 0-1 et 3-4 sont du travail déterministe, hors ligne, à coût de modèle nul — la
frontière gratuite avant toute dépense, qui a trouvé onze défauts sur quatorze dans ce chantier. La
capacité 2 demande du jugement humain (curation) et la 5 est la plus lourde en code. Une migration
(034), aucune autre prévue.

**Risque principal — le desserrage déguisé.** Ouvrir l'admission des sources *est* un desserrage.
Ce qui le rend acceptable ici, et qu'il faut tenir : rien n'est promu automatiquement, l'admission
est nominative, et le standing est accordé **par nature** — donc aucune source nouvelle ne peut
fonder une mesure chiffrée. Si l'une de ces trois conditions saute en cours de route, la révision
devient exactement le trou que `feedback_optional_schema_gate` décrit.

**Risque secondaire — le biais de récence.** Un article récent qui rehashe une vieille nouvelle ne
doit pas déclasser un fait solide. Tenu par la règle « l'actualité se mesure sur la date du fait ».
À surveiller au premier corpus réel : c'est le mode de panne le plus probable.

**Ce qui invaliderait la révision, et qu'il faut accepter de voir.** Si, après la capacité 2, les
sources admises n'apportent sur RVMD que des redites du communiqué officiel, alors le problème
n'était pas l'admission mais la **collecte** — et la bonne réponse serait d'ingérer les communiqués
IR (déjà tier A 0,90, déjà admissibles aujourd'hui) plutôt que d'ouvrir aux experts. Ce test est
peu coûteux et se fait **avant** les capacités 3-5 : le poser tôt est délibéré.

## Ce que cette spec ne traite pas

- La **calibration** des sources par track record (`calibration_registry`, migration 032) : une
  source pourrait *mériter* son standing plutôt que le recevoir. Séduisant, prématuré — il faut
  d'abord des prédictions closes.
- La limite de conception de `covers` multi-champs (une entry couvre 3 champs « également »).
- Le `readiness` des deux autres émetteurs : NVDA et MSFT devront être **re-mesurés** après la
  capacité 4, et il faut s'attendre à ce qu'ils perdent leur `ready` — ce serait un **succès** du
  correctif, pas une régression.
