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
le 2026-08-26. Aucune n'est fausse : chacune est fidèle à sa source et correctement datée. Le
`readiness` prononce néanmoins **`ready`, 0 gap**.

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

- [ ] Statuer champ par champ : nature dominante · plancher fiabilité · actualité bloquante O/N
- [ ] Nommer les champs où un 10-K est **insuffisant** malgré son tier A (candidats : `risques.*`,
      `marche.dynamique`, `business_model.drivers_revenus`)
- [ ] Nommer les champs où une source non-EDGAR ne doit **jamais** suffire (candidats :
      `financials.*`, tout ce qui est chiffré)
- [ ] Convention **#50** dans le `CLAUDE.md` du projet
- **Acceptation** : un check échoue si un seul des 19 champs requis n'a pas d'entrée dans la table.
  Test négatif : retirer une ligne de la table doit faire virer le check au rouge en **nommant** le
  champ manquant — pas en sortant à 0 (§13/§24 de `CHANTIER_OUTILLAGE_DEV.md`).

### 1. L'axe `nature`, dérivé déterministe · contexte partagé : `knowledge/service.py`, `agents/v2/worker.py`, migration 034

- [ ] Migration **034** : colonne `nature` (`mesure`|`evenement`|`interpretation`), index, backfill
      des ~130 entries actives NVDA/MSFT/RVMD
- [ ] Détenteur **unique** de la dérivation (#46), importé par les feeds et le worker — jamais
      ré-implémenté par producteur
- [ ] Le modèle peut resserrer, jamais desserrer (garde symétrique de #29)
- **Acceptation** : après backfill, `SELECT nature, count(*)` ne rend **aucun** `NULL` sur les
  entries actives, et les 13 entries déterministes RVMD sont toutes `mesure`. Test négatif : forcer
  la dérivation à rendre `interpretation` sur un fait EDGAR doit faire rougir un assert **nommé**.
- ⚠️ Vérifier après déploiement le comptage par clef (#43), pas seulement le diff.

### 2. Le registre des sources admissibles, curé à la main · contexte partagé : `knowledge/websearch.py` (`_ISSUER_DOMAINS`, `classify_source_type`), convention #33

- [ ] Registre clefé par **secteur** et/ou **ticker**, sur le modèle à deux niveaux de #33, portant
      pour chaque source : domaine, nature(s) pour lesquelles elle a standing, tier accordé, **date
      d'admission** et **motif** écrit
- [ ] Amorçage biotech clinique pour RVMD (≥ 2 sources non-EDGAR), validé par l'utilisateur
- [ ] Un domaine inconnu reste `web_search_generic` 0,50 — inchangé
- **Acceptation** : une source admise pour `interpretation` ne gagne **aucun** standing sur une
  `mesure` (assert dédié) ; un domaine hors registre reste à 0,50 ; RVMD dispose d'au moins deux
  sources admissibles capables de fonder un champ d'interprétation.
- ⚠️ Piège #33 : une règle spécifique ne resserre jamais la règle générique au passage.

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
- **Acceptation, et c'est le test central de toute la révision** : le `readiness` RVMD doit passer
  de `ready, 0 gap` — le faux vert observé aujourd'hui — à **`not_ready` avec cause `péremption`**,
  en nommant les champs concernés, **sans** les compter comme des lacunes de collecte.
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
