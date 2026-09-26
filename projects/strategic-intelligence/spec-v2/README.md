# Tour de contrôle stratégique — spécification v2 (consolidée)

Système de veille stratégique pour un directeur de la stratégie : il collecte en continu de
l'information publique, la transforme en signaux qualifiés et datés, suit des questions clés
et des scénarios, et produit des briefs et des livrables transmissibles. Mono-utilisateur au
démarrage, hébergé sur le VPS existant, organisé en **modules métier qui gagnent des
fonctions**, avec des **sources ajoutées par paramétrage dans l'outil**.

**Cette v2 remplace intégralement la v1**, supprimée du dépôt (archive locale non versionnée dans `../prive/`).
Elle n'a pas d'ordre de priorité entre fichiers : chaque sujet a **un seul fichier détenteur**.
Si deux fichiers semblent se contredire, c'est un défaut de la spec : le signaler, ne pas
arbitrer seul.

## Fichiers

| Fichier | Détenteur de | Lire quand |
|---|---|---|
| `00-BRIEF-AGENT.md` | règles d'or, méthode, définition du « fini » | toujours, en premier |
| `01-SPEC-FONCTIONNELLE.md` | objets métier, modules métier et leurs fonctions, écrans, diffusion | pour comprendre *quoi* |
| `02-ARCHITECTURE.md` | noyau, modules, manifestes, bus d'événements, points d'extension, infrastructure, suivi d'architecture | pour comprendre *comment* |
| `03-SCHEMA.sql` | schéma PostgreSQL de référence, unique | avant toute migration |
| `04-SOURCES.md` | familles, gabarits, instances, contrat de mappage, 6 cas pilotes, parcours d'ajout | pour toute source |
| `05-SORTIES-EXTERNES.md` | niveaux de sensibilité, segmentation, routeur de sortie, information de l'utilisateur, budget | pour tout appel externe (LLM, recherche, courriel, Slack) |
| `06-ROADMAP.md` | lots, tickets, critères d'acceptation | pour planifier |
| `07-CHANTIER-NEWSLETTER-SUMMARY.md` | évolution à apporter au projet `newsletter-summary` | avant le lot 1 |
| `08-PROMPT-DEMARRAGE.md` | premier message à l'agent de développement | au démarrage |
| `DECISIONS.md` | toutes les décisions prises, avec leur justification | en cas de doute sur un « pourquoi » |
| `config-exemple/` | configuration de référence : noyau générique, pack sectoriel spatial, format d'import des mandats | à l'amorçage |
| `modeles/ARCHITECTURE.md` | registre d'architecture initial, à déposer à la racine du dépôt | au lot 0 |

## Ce qui a changé par rapport à la v1

| Sujet | v1 | v2 |
|---|---|---|
| Confidentialité | isolement réseau d'une « zone rouge » + modèle local | **routeur de sortie unique**, trois niveaux (libre / segmenté / jamais), segmentation des appels, information de l'utilisateur. Aucun modèle local |
| Organisation | couches techniques, 9 points d'extension fermés | **noyau + modules métier + fonctions**, manifeste `module.yml`, bus d'événements, 13 points d'extension |
| Sources | YAML versionné, JSONPath GET, secrets en `.env` | **base = source de vérité, édition dans l'interface**, familles / gabarits / instances, contrat de mappage élargi (XML, POST, liste→détail, HTML), coffre de secrets, 6 cas pilotes |
| Newsletters et terrain | absent | deux alias `newsletter-summary` : `veille@` (newsletters) et `terrain@` (notes personnelles) |
| Wiki | agent curateur réécrivant des pages Git | **fiches générées depuis la base** ; le LLM n'écrit que l'interprétation |
| Métier | domaines, horizons, questions clés, thèses | + **types d'événements**, **scénarios**, **observations chiffrées**, **livrables**, **double score importance/crédibilité**, **calibration** |
| Infrastructure | VPS 8 vCPU/16 Go dédié, Caddy, Valkey, Ollama | VPS existant agrandi, Traefik, `shared-postgres`, file sur Postgres, DeepInfra, Exa, `comms-gateway` |
| Budget | plafond bloquant dès le départ | **mode observation** au démarrage ; plafond bloquant activé par l'utilisateur une fois le système en marche |
| Changement de secteur | test d'agnosticité | + **pack sectoriel** importable et assistant de création d'un pack |
| Suivi d'architecture | `ARCHITECTURE.md` en prose + `make arch-check` | registre **cible** en prose, **réalisé** prouvé par des checks (modèle portfolio-tracker), manifestes contrôlés, tests négatifs |

## Décisions structurantes

Voir `DECISIONS.md`. Résumé : périmètre réel = spatial, mais reconfigurable pour un autre
secteur sans code ; fournisseur LLM = DeepInfra ; recherche web = Exa ; configuration
éditée dans l'outil ; les saisies de l'utilisateur ne partent jamais en clair vers un LLM.
