# Décisions — spécification v2

Format court : décision · pourquoi · conséquence. Numérotation stable, jamais réutilisée.
L'agent de développement ajoute ses propres décisions à la suite, dans `DECISIONS.md` à la
racine du dépôt, en reprenant la numérotation à partir de D100.

## Décisions de l'utilisateur (2026-09-26)

**D1 — Périmètre réel : activités spatiales. L'outil doit se reconfigurer vite pour un autre secteur.**
L'identité de l'entreprise ne figure dans aucun fichier versionné (réglage saisi dans l'interface).
Pourquoi : le besoin est immédiat sur le spatial, mais l'outil doit servir d'autres contextes.
Conséquence : toute valeur sectorielle vit dans un *pack sectoriel* (`config-exemple/packs/spatial/`) ;
un contrôle automatique interdit tout terme du pack dans le code ; un assistant aide à créer un
nouveau pack (`01` §9).

**D2 — Confidentialité par transparence et segmentation, pas par isolement réseau.**
Pourquoi : les sources sont toutes publiques au démarrage ; seules les saisies de l'utilisateur
sont sensibles ; le VPS ne peut pas porter un modèle local.
Conséquence : trois niveaux `green` / `amber` / `red` (`05` §1), routeur de sortie unique,
journal des sorties, revue hebdomadaire, validation de chaque nouveau gabarit de prompt touchant
une donnée `amber`. Pas de modèle local, pas de réseau interne dédié.

**D3 — Les énoncés de thèses, niveaux de confiance, annotations et notes terrain ne sont jamais envoyés à un LLM.**
Pourquoi : ce sont les convictions de l'utilisateur.
Conséquence : les fonctions qui les exploitent sont déterministes ou manuelles ; elles passent
par les indicateurs (`amber`, segmentés) pour être rapprochées des signaux.

**D4 — Résidu accepté : un fournisseur qui recouperait tous les appels pourrait déduire des centres d'intérêt, pas des convictions.**
Conséquence : la segmentation vise l'irréconstituabilité des *convictions*, pas l'invisibilité
des *sujets*.

**D5 — Fournisseur LLM et embeddings : DeepInfra.**
Pourquoi : déjà utilisé sur le VPS (newsletter-summary, portfolio-tracker), clé disponible,
embeddings `BAAI/bge-m3` (1024 dimensions, multilingue) standard du dépôt.
Conséquence : un seul fournisseur externe de modèles au démarrage ; le routeur reste
multi-fournisseur (point d'extension E4).

**D6 — Recherche web : Exa.** Pourquoi : clé existante, déjà intégrée ailleurs.

**D7 — Budget : plafond configuré mais non bloquant au démarrage.**
Pourquoi : on veut d'abord mesurer le coût réel du système en marche.
Conséquence : garde-budget en mode `observe` (comptage, projection, bandeau, alerte) ;
l'utilisateur bascule en mode `enforce` dans l'interface quand il le décide (`05` §6).

**D8 — Newsletters : un alias dédié `veille@` de newsletter-summary.** L'utilisateur y abonne les
newsletters stratégiques. Le flux newsletter personnel existant n'alimente pas l'outil.

**D9 — Notes terrain : un second alias `terrain@`**, accepté uniquement depuis les adresses de
l'utilisateur, sans LLM, avec accusé de réception sans reprise du contenu, pièces jointes PDF
acceptées. Pas de résumé par courriel des newsletters de veille : le brief de l'outil le remplace.

**D10 — Configuration : la base fait foi, l'interface l'édite, le YAML sert à l'import/export.**

**D11 — Connaissance : fiches générées depuis la base ; le LLM n'écrit que les sections d'interprétation.**
Pas d'agent curateur libre, pas de dépôt Git de wiki.

**D12 — Diffusion : le brief par courriel (via `comms-gateway`), les alertes immédiates sur Slack.**
Le courriel et Slack ne contiennent que du `green` ; le reste est un lien vers l'outil.

**D13 — Axes métier retenus : types d'événements, scénarios, observations chiffrées, livrables,
capture terrain, double score, calibration, rôles utilisateur, classification allégée au départ.
Refusé : calendrier des décisions internes.**

**D14 — `horizon-scan` archivé**, remplacé par ce projet.

**D15 — Réutiliser les briques du VPS** : Traefik, `shared-postgres` (base dédiée `db_strategic`),
`comms-gateway`, DeepInfra, Exa, `kb-viewer` (optionnel). Pas de Caddy, pas de Valkey, pas d'Ollama.

**D16 — Agrandir le VPS** (au moins 8 Go de RAM, disque augmenté) avant la mise en service
continue (lot 1). Constat du 2026-09-26 : 2 vCPU, 3 Go dont ~0 disponible, 5,4 Go de disque libre.

**D17 — Suivi d'architecture sur le modèle de portfolio-tracker**, adapté aux manifestes de
module (`02` §10). Cible en prose, réalisé prouvé par des checks, chaque check éprouvé en négatif.

## Décisions techniques par défaut (acceptées par l'utilisateur)

**D20 — File de tâches et ordonnanceur sur Postgres** (`SKIP LOCKED`, ou bibliothèque
`procrastinate`). Pourquoi : un service de moins, événements rejouables.

**D21 — Déploiement `docker compose` standalone** via `infrastructure/compose-deploy.sh`,
comme les autres projets du VPS, derrière Traefik.

**D22 — Interface FastAPI + Jinja2 + HTMX.** Pas de framework JavaScript en V1.

**D23 — Architecture noyau + modules métier à manifeste** (`02`).

## Décisions héritées de la v1 et conservées

**D30** — Signal = fait daté, atomique, sourcé ; chaque affirmation générée porte une `evidence`
avec citation exacte.
**D31** — Brut immuable, `source_payload` conservé, traitements versionnés, rejeu fantôme.
**D32** — Géographie : trois rôles par signal (`actor`, `market`, `jurisdiction`).
**D33** — Taxonomies métier en tables de référence ; `ENUM` réservés au structurel.
**D34** — Activation progressive (gating) : chaque fonction déclare ses prérequis de données et
s'auto-désactive en l'expliquant ; les composantes de score inactives voient leur poids redistribué.
**D35** — Registre d'identité `entity` avec intégrité référentielle ; table `embedding` séparée.
**D36** — Tranche verticale avant toute largeur ; critères d'acceptation exprimés en extensibilité.
**D37** — Rien n'est jeté : un contenu écarté est marqué `discarded` avec son motif.

**D18 — Contenu sensible jamais versionné** : mandats, questions clés, indicateurs, scénarios,
relations au périmètre, termes d'identité vivent en base ou dans `prive/` (gitignoré). Les exemples des
documents versionnés sont neutres (`SEG-XX`).

## Décisions de la v1 abandonnées

| v1 | Remplacée par |
|---|---|
| Réseaux `netpub` / `netint`, `worker-reason` isolé | D2 |
| Ollama, modèle instruct local | D3, D5 |
| Chiffrement applicatif avec clé hors sauvegarde | chiffrement des colonnes `red` conservé, clé dans le coffre (`05` §7) |
| Wiki Git + contrat curateur (`04-WIKI-CONTRACT.md`) | D11 |
| Caddy, Valkey, `arq` | D15, D20 |
| `config/*.yml` source de vérité | D10 |
| Plafond bloquant d'emblée | D7 |
| Neuf points d'extension fermés | D23, `02` §6 |
| Interdiction de relire le code | `00` règle 12 |
| Profils `frugal`/`standard` | drapeaux de capacité par module dans l'interface (`02` §4) |
