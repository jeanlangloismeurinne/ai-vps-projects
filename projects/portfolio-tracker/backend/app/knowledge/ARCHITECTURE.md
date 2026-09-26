# `knowledge/` — base de connaissance & sources de données

> **Cible** (spec : `roadmap/V3/doctrine-trois-axes.md`, `03-spec-frameworks.md` §5/§1.7).
> **Réalisé** : prouvé par les `check_*.py` cités ci-dessous — les exécuter, ne pas croire cette prose.

## Rôle

La couche 3 : la base de connaissance (`knowledge_entries`, versionnée append-only) + les **8 feeds
déterministes** qui l'alimentent + la recherche vectorielle. C'est ici qu'on **ajoute une source de
données**.

## Ajouter une source de données — le contrat

Une source est un **objet standard** : elle règle son interface avec la base, rien d'autre.

1. **Émettre par le passage obligé.** Écrire `<x>_feed.py` qui appelle
   `service.store_knowledge(conn, *, ticker_id, entry_type, content, source_type, …)`. **Jamais
   d'INSERT direct.** Le `reliability_score`/`tier` sont **CALCULÉS** par `store_knowledge`, jamais
   fournis par l'appelant (§6.3, #50).
2. **S'inscrire nominativement.** Déclarer le domaine de la source dans `source_registry.py` — le
   standing est accordé pour un **couple (source × nature)** (#52). L'admission est un **acte humain**,
   jamais une promotion automatique, pas même par corroboration.
3. **La nature se dérive, ne se déclare pas.** Un fait à recette déterministe (un `metric` structuré)
   est `mesure` ; `store_knowledge` l'arbitre via `derive_nature` (détenteur unique, #51). Le feed ne
   passe que `nature_declaree`.
4. **Formats et datation par les détenteurs uniques.** Montants via `units.py` (#46) ; un flux se date
   par son exercice, un poste de bilan par un instant, un ratio par ses postes (#42) ; l'identité d'un
   fait est ce qu'il mesure (#43) ; *calculé / non calculable / absent* sont **trois états** (#44).
5. **Plan-dérivé (v3).** Un producteur ne collecte que ce que le **plan** réclame, jamais « tout ce
   qu'il sait faire » (#61) — ex. `run_edgar_feed(metrics=…)`.
6. **Jamais recombiner les axes en scalaire** (#50) ; l'actualité se **calcule à la lecture** (#53).

## Fichiers

| Fichier | Rôle |
|---|---|
| `service.py` | `store_knowledge` (passage obligé), scoring, versionnement A1 |
| `source_registry.py` | Registre nominatif des sources admises (#52) |
| `edgar_feed.py` · `financials_feed.py` · `valuation_feed.py` · `base_rate_corpus.py` | Feeds financiers déterministes |
| `material_events.py` · `staleness.py` · `actualite.py` | Événements matériels & péremption (axe actualité) |
| `evenements.py` | Ce qu'un événement ROUVRE (#89) : type d'un dépôt par sa FORME (`a_qualifier` quand la forme ne décide pas) et ancre PAR QUESTION — le dernier fait d'un type qui la rouvre, filtré par `frameworks.types_qui_rouvrent` |
| `websearch.py` · `document_search.py` · `embeddings.py` | Recherche web + sélection de passages + embeddings bge-m3 1024d |
| `units.py` | Détenteur unique du format des montants (#46) |
| `datation.py` | Détenteur unique de la datation d'une pièce : portée fermée (`constatee`/`prospective`/`indatable`), **deux dates nommées** (fait, document), `source_date` DÉRIVÉE (#79). Moitié ÉCRITURE de ce dont `actualite.py` est la moitié LECTURE |
| `edgar_facts.py` · `synthesis_feed.py` | Extraction EDGAR · synthèses grounded |
| `appariement_feed.py` | Exécute une formule d'appariement sur les concepts XBRL **déjà lus** — produit un fait calculé, sa provenance concept par concept et son tier dérivé (#72) |

## Cible → garde (réalisé)

| Invariant cible | Garant |
|---|---|
| Score/tier calculés, jamais fournis ; passage obligé | `check_provenance.py`, `check_synthesis_feed.py` |
| Nature dérivée (`metric` structuré ⟹ `mesure`) | `check_entry_nature.py` §7 (état persisté) |
| Datation : deux dates nommées, `source_date` dérivée, confusion fait/document INEXPRIMABLE (#79) | `check_datation.py` + `negatif_datation.sh` |
| Registre : standing par couple (source × nature) | `check_source_registry.py` |
| Feeds financiers : identité #43, datation #42, 3 états #44 | `check_edgar_feed.py`, `check_financials_feed.py`, `check_valuation_feed.py`, `check_base_rate_corpus.py` |
| Un ratio valide un CALCUL, jamais sa SIGNIFICATION : conversion FCF et ROIC ne se publient pas quand l'émetteur n'a ni bénéfice ni exploitation — le refus est PUBLIÉ (il supersede la ligne fausse), et « intrant absent » ne se confond pas avec « ratio non défini » | `check_financials_feed.py` §6 + `negatif_financials_feed.sh` |
| Une formule d'appariement s'EXÉCUTE sur le dépôt : 4 refus nommés, ancre commune par cadrage, tier dérivé du déterminisme (#67/#72) | `check_appariement_feed.py` + `negatif_appariement_feed.sh` (le câblage amont est chez `check_collecte_executor.py` §11) |
| Actualité calculée à la lecture, jamais persistée | `check_actualite.py`, `check_material_events.py` |
| Une note flash ne remplace que la part `a_qualifier` d'un dépôt ; illisible, elle le laisse rouvert ; l'horloge la reçoit en paramètre REQUIS (#90) | `check_evenements.py` §7 + `negatif_evenements.sh` ; l'agent chez `check_note_flash.py` |
| Chaque question a sa propre horloge : un fait ne rouvre que les questions dont le référentiel déclare son type (#89) | `check_evenements.py` + `negatif_evenements.sh` ; le référentiel ([Q]/[R]) chez `check_frameworks_definitions.py` |
| Format des montants (détenteur unique) | `check_edgar_feed.py` §11, `check_financials_feed.py` §9 |
| search-worker ne qualifie pas sa propre source | `check_search_worker.py` |
| `fetch_url` : deux chemins, le domaine décide (live) | `check_fetch_live.py`, `check_fetch_relevance.py` |
| Listing lisible des entries | `check_knowledge_entries_listing.py` |
