# `frameworks/` — référentiel des frameworks d'analyse

> **Cible** (spec : `roadmap/V3/03-spec-frameworks.md` §2/§4, `benchmark-methodologies.md`).
> **Réalisé** : prouvé par les `check_*.py` cités ci-dessous — les exécuter.

## Rôle

`frameworks.yaml` est le **détenteur unique** du référentiel : un **fichier inerte versionné**, pas
des tables, pas du Python. Un framework est une **question d'investissement stable** décomposée en
**questions universelles** applicables à toute entreprise. C'est ici qu'on **ajoute un framework**.

**Pourquoi du YAML et pas du Python** : l'ordre imposé est UX → agent → données. Les questions se
dérivent d'une **méthodologie** (Greenwald, Porter), jamais de ce que la base contient déjà. En
Python, rien n'empêcherait de dériver les ingrédients par compréhension sur `MVDD_SPEC` — et le test
de couverture mesurerait alors sa propre constante (4ᵉ faux vert). En YAML, la seule façon de faire
coïncider les questions avec le corpus est de les écrire à la main, ce qui se lit dans le diff.

## Ajouter un framework — le contrat

Un framework est un **objet standard** : ajouter une entrée YAML conforme suffit, la question traverse
ensuite `traducteur → collecteur → analyste → manager` **sans code neuf**.

Structure (validée strictement par `contracts/framework_definition_schema.py`, `extra` interdit) :

- `id`, `libelle`, `etape_benchmark` (1-8, rattachement au benchmark Partie B), `methodologie` ;
- `questions[]`, chacune :
  - `id` (`^[a-z]{2}_[0-9]+$`), `enonce` — **en substance ÉCONOMIQUE, jamais en artefact comptable**
    (§2.3 : « le capital employé rapporte-t-il plus que son coût ? », pas « quel est le ROIC ? ») ;
  - `chemin_indexation` (`famille.champ`), `plancher_tier`, `nature_attendue`, `actualite_bloquante` ;
  - `sens_admis[]` (≥2), `ingredients_requis[]` (chacun `essentiel: bool` ; nomment le **besoin**,
    jamais une entry du corpus — un ingrédient qui nommerait « #33 » écrirait le corrigé) ;
  - `variables_par_archetype{}` — comment la question s'instancie (ou sort `sans_objet` + substitut).

**Interdits** : aucun seuil de couverture, aucun compte d'orphelines dans le YAML (la couverture est
un **résultat mesuré**, pas un objectif inscrit). Aucun levier de modèle sur `plancher_tier` /
`nature_attendue` / `essentiel` (#59/#62). Versionner via `schema_version`.

## Cible → garde (réalisé)

| Invariant cible | Garant |
|---|---|
| Le YAML est confronté aux tables de la spec §7 (jamais recopié) | `check_frameworks_definitions.py` (lit `/roadmap/V3/03-spec-frameworks.md`) + `negatif_frameworks_definitions.sh` |
| Contrat de définition strict (`extra` interdit) | `check_framework_contract.py` + `negatif_framework_contract.sh` |
| Traduction questions → plan de collecte par ticker | `check_traducteur.py`, `check_collection_plan_contract.py` |
| Collecte plan-dérivée, aveugle à la question | `check_collecteur.py`, `check_collecte_executor.py` |
| Appariement par TICKER contre l'inventaire réellement déposé — trois états, tier dérivé du déterminisme (#67) | `check_appariement.py` + `negatif_appariement.sh` (contrat `appariement_schema.py`, pont `agents/v2/apparieur.py`, règle `synthesis_feed.derive_tier_calcul`) |
| Réponses de framework versionnées, refus avant dépense | `check_analyste.py`, `check_framework_persist.py` |
| Réponse/dispense clefées par `framework_version` | `check_framework_persist.py` (#64) |
| Un `chemin_indexation` appartient au framework qui l'instruit (invariant **[N]**) | `check_frameworks_definitions.py` + `negatif_frameworks_definitions.sh` |
| La règle de réconciliation mémo ↔ questions est éprouvable dans les DEUX sens (satisfiable et discriminante), et tenue à un seul endroit | `check_reconciliation.py` + `negatif_reconciliation.sh` (règle : `tools/reconcilier_vocabulaires.ecart`) |

> ⚠️ **L'écart lui-même n'est pas gardé ici, et c'est voulu.** `tools/reconcilier_vocabulaires.sh`
> est ROUGE par construction (30 feuilles de mémo sans question, 13 questions jamais consommées) et
> le reste jusqu'à ce que chaque bloc du mémo soit la projection d'un framework acquitté — l'état
> terminal de la roadmap, pas un lot. `check_reconciliation.py` garde l'INSTRUMENT, pas le chiffre :
> asserter `30` et `13` serait geler un décompte de corpus en cible (§0.6), et le faire rougir à la
> première question ajoutée.
