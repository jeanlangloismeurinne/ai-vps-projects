---
id: worker-delegation-card
status: carte-de-provenance
created: 2026-08-21
project: portfolio-tracker
role: >
  Carte de provenance de l'interface orchestrateur→ouvrier (§5.2) — le contrat le plus AMONT :
  le boundary par lequel toute donnée entre dans le système. Requête structurée {query,
  output_schema, reliability_min} → knowledge_entries scorées, jamais du texte libre.
  Pydantic : worker_delegation_schema.py (18/18 vérifiés, container 2.13.4). Voir §5.2, §6.3, §6.4, §13.5.
---

# Carte de provenance — Interface orchestrateur → ouvrier (délégation)

## Ce qui distingue cette carte des autres

Les 6 cartes d'analyse décrivent le contenu **produit** par les agents métier. Celle-ci décrit la
**plomberie de délégation** qui alimente ces agents : un agent métier (curator/research/bull/bear/
synthèse/monitoring) ne cherche jamais lui-même — il **émet une requête structurée** à un ouvrier
(search-worker/gap-intake/ingestion/groundedness), qui renvoie des `knowledge_entries` **scorées**.

C'est le contrat qui rend **G3 vrai à la frontière** : aucun fait n'entre en texte libre. La
`WorkerResponse` n'a structurellement **aucun** champ `answer`/`summary`/`text` — uniquement
`entries[]`. Un ouvrier qui « ne trouve pas » le déclare en `uncovered_fields[]` (structuré), pas
en prose. C'est le pendant amont de la colonne « Gap si non-fondable » des cartes d'analyse.

`ProducedEntry` (forme d'une entry fraîchement créée) est **partagée avec C2 (ingestion)** :
« 1 forme d'entry → 2 producteurs » (search-worker ici, ingestion-agent en C2).

## Twin table — requête (délégation) & réponse (provisioning)

### Requête `WorkerRequest` (orchestrateur → ouvrier)

| Champ | nature | rôle | Vérification |
|---|---|---|---|
| `requester` | **contrôle** | quel agent métier délègue (traçabilité §13) | `Literal` roster §5.2 |
| `worker` | **contrôle** | à quel ouvrier | `Literal[search-worker, gap-intake, ingestion-agent, groundedness-checker]` |
| `query` | **ref** | question structurée | non vide |
| `output_schema.entry_type` | **contrôle** | forme attendue (le contrat n'est pas décoratif) | `EntryType` ; cross-check : entries retournées de ce type |
| `output_schema.field_path` | **ref** | champ précis du contrat aval que l'entry doit combler | grounding aval (`covers`) |
| `reliability_min` | **contrôle** | plancher de fiabilité exigé | cross-check : toute entry `score ≥ min` |
| `max_entries` | **contrôle** | arrêt de Pareto / plafond coût | cross-check : `len(entries) ≤ max` |
| `divergent` | **contrôle** | A6 : mandat de falsification (search-worker du bear) | si `not_found` → `uncovered_fields` exigé |
| `check_existing_first` | **contrôle** | anti-doublon : `query_knowledge` avant `store` (gap-intake) | défaut `True` |

### Réponse `WorkerResponse` (ouvrier → orchestrateur) — provisioning scoré

| Champ | nature | grounding | Vérification (A2) | Provisioning |
|---|---|---|---|---|
| `entries[].content` | **factual** | source_type + refs | non vide, Markdown (pivot lisible) | extrait/trouvé par l'ouvrier |
| `entries[].source_type` | **contrôle** | — | `SourceType` (framework KP §3.3) | d'où vient le fait |
| `entries[].reliability_score` | **derived** | hérité (source×modulation) | ≤ plafond source (baseline + cross-val 0.10, §6.3) | framework fiabilité |
| `entries[].reliability_tier` | **derived** | hérité | `Literal[A…C]` | framework fiabilité |
| `entries[].reliability_note` | **judgment** | — | non vide (jamais un score muet) | pourquoi ce score |
| `entries[].requires_human_review` | **contrôle** | — | **P2** : `True` obligatoire si `llm_memory` (§6.4) | filet cold-start |
| `entries[].model_cutoff` | **contrôle** | — | **P2** : obligatoire si `llm_memory` | mémoire modèle datée |
| `entries[].covers` | **ref** | — | `= output_schema.field_path` (grounding aval) | champ comblé |
| `status` | **contrôle** | — | `found`⇒entries≠∅ ; `not_found`⇒entries=∅ | issue de la recherche |
| `uncovered_fields[]` | **derived** | — | champs demandés non comblés (structuré) | ce qui manque encore |
| `execution.*` | **contrôle** | — | §5.3 : `model/tier/batch/cache/tokens/cost` déclarés | coût auditable |
| `request_hash` | **ref** | — | §13.5 : hash de la requête (reproductibilité) | prompt rejouable |

## Garde-fous encodés (worker_delegation_schema.py — 18/18 vérifiés)

- **G3 — jamais de texte libre.** `WorkerResponse` n'expose aucun champ de prose ; `extra='forbid'`
  rejette un `answer` injecté. Toute donnée = `ProducedEntry` scorée.
- **`reliability_min` honoré (cross-validateur).** Toute entry retournée a `score ≥ reliability_min`.
  Corollaire naturel : le filet `llm_memory` (0.40) ne passe **que** si l'orchestrateur a explicitement
  ouvert le plancher (`min ≤ 0.40`) — le cold-start est un choix tracé, pas une fuite.
- **Plafond de source (§6.3).** Un score ne peut dépasser `baseline(source) + 0.10` (max modulation
  positive = cross-validation). Un `llm_memory` à 0.95 est rejeté ; un `edgar_official` cross-validé
  à 1.0 passe.
- **P2 (§6.4).** `llm_memory` ⇒ `requires_human_review=True` **et** `model_cutoff` — la traçabilité
  du filet est structurellement imposée.
- **Contrat de sortie respecté.** Les `entry_type` retournés doivent correspondre au type demandé
  (`output_schema.entry_type`) — la délégation est typée, pas un fourre-tout.
- **§5.3 — déclaration d'exécution.** L'ouvrier déclare model/tier/batch/cache/tokens/cost ;
  `tier='ouvrier'` verrouille le sens de la délégation (métier → ouvrier, jamais l'inverse).
- **A6 — mandat divergent explicite.** Un `search-worker` du bear en mandat de falsification qui ne
  trouve rien doit l'assumer en `uncovered_fields`, jamais rester muet.
- **Pareto / coût.** `max_entries` plafonne le retour à la construction.

## Stockage

L'échange n'a pas de table dédiée : les `entries` sont persistées dans `knowledge_entries`
(migration 024, append-only A1) via `store_knowledge` ; le `request_hash` + `execution` alimentent
le budget/audit (dust_budget partagé + colonnes cost/tokens des analyses en aval). `ProducedEntry`
est le sous-ensemble des colonnes que l'agent remplit ; id/version/valid_from/embedding/
superseded_by/timestamps sont posés par la DB.

## Les 3 points de synchronisation (G1, règle #19)

1. **Prompt ouvrier** (search-worker/gap-intake/ingestion/groundedness) — schéma de sortie = ce contrat.
2. **Backend** — `providers/` (factory `get_provider`, lot 2) + les classes agent métier construisent
   la `WorkerRequest` et valident la `WorkerResponse` via `WorkerExchange` avant `store_knowledge`.
3. **Import / validation** — `worker_delegation_schema.py` à la frontière de délégation.

## Ancrage

- Pydantic vérifié (pydantic 2.13.4, container backend) : `worker_delegation_schema.py` — 18 cas
  (G3, reliability_min, plafond source, P2, entry_type, A6 divergent, status, max_entries).
- Framework de fiabilité (source_type → tier → score + modulations) : roadmap KP §3.3 ; table
  `knowledge_entries` : migration 024.
- `ProducedEntry` réutilisée par C2 (ingestion). Consommateurs des entries : curator (readiness),
  research, bull/bear (cartes `analysis_v2_schemas.py` + §8).
