# Réflexion — mode SDD : idées en réserve et chantiers à venir

> **Statut : notes, rien d'implémenté** (2026-10-21). Ce fichier garde ce qui a été écarté de la
> version légère pour ne pas le perdre. Chaque idée porte la raison de son report et ce qui
> justifierait de la reprendre. Origine : `reference/prompt-2-sdd-pilote.md` + évaluation du
> 2026-10-21.

## Chantier OBLIGATOIRE — multi-comptes / multi-fournisseurs

À faire dans tous les cas, indépendamment du mode SDD. Valeur principale : **la relecture
par un autre contexte, un autre compte ou un autre modèle** (« personne ne valide son propre
travail ») et la sous-traitance de lots quand les crédits d'un compte sont épuisés.

Cible :
- `_governance/scripts/run_agent.sh <fournisseur> <briefing.md> <projet> [--worktree]`
  - lance la CLI en non-interactif, dans un **worktree isolé** ;
  - **timeout dur** (un blocage est un état muet : échec nommé, jamais une attente infinie) ;
  - récupère un rapport au format fixe (contrat worker, `CONTROL_SYSTEM.md` §6) ;
  - refuse un fournisseur non autorisé pour le projet ;
  - deux échecs consécutifs d'un fournisseur → repli sur l'orchestrateur, incident consigné.
- **Registre des fournisseurs** (un seul fichier, ex. `_governance/providers.sh`) :
  - `claude` — ce compte ;
  - `claude2` — 2ᵉ abonnement Claude. Deux pistes **à vérifier dans la doc officielle avant
    usage** (passer par `claude-code-guide`) : `CLAUDE_CONFIG_DIR=/root/.claude-acct2` (dossier
    de config et d'auth séparé, `/login` interactif fait une fois par l'utilisateur), ou
    `claude setup-token` → jeton longue durée passé en `CLAUDE_CODE_OAUTH_TOKEN`. Vérifier aussi
    que `--bare` ou équivalent n'embarque pas les hooks/réglages du compte principal ;
  - `codex` — installé (codex-cli 0.163.0), **non connecté** ; `codex exec -C <dir> -s workspace-write` ;
  - `deepinfra` — reprendre la commande `ds` existante (`~/.claude/deepinfra.env`).
- **Autorisation par projet** : par défaut, comptes Anthropic autorisés partout ; autres
  fournisseurs seulement si listés (`executants_autorises:` dans le frontmatter du 00-REPRISE).
  bank-review (données financières personnelles) : refus de tout fournisseur non Anthropic.
- **Preuves** : un lot `claude → claude2` et une relecture inverse de bout en bout ; un refus
  sur bank-review ; un timeout qui sort en échec nommé.
- Prérequis utilisateur : souscrire le 2ᵉ abonnement (pas encore fait au 2026-10-21).

## Idées en réserve (version complète du prompt 2)

| Idée | Pourquoi reportée | À reprendre si… |
|---|---|---|
| **Hook SessionStart (démarrage + compaction)** qui réinjecte `CAP.md` | la ligne dans le `CLAUDE.md` du projet suffit pour l'essai ; vérifier d'abord si le `CLAUDE.md` de projet est relu après compaction | le journal montre une dérive juste après les compactions. Conception à coût nul hors SDD : un marqueur `_governance/sdd/.locks/<projet>.lock` contenant le `session_id` ; le hook ne parle que si sa session détient un verrou (sert aussi de verrou d'orchestration) |
| **`check_gates.py`** (sort immédiatement en mode simple) | rien à contrôler mécaniquement tant que la version légère est documentaire | un lot sous-traité est en place. Garder alors seulement : taille/fraîcheur de `CAP.md`, **intégrité des tests et fichiers protégés après un lot écrit par un autre exécutant** (cas avéré : un worker a affaibli une mutation), coupe-circuit lu dans le journal. Il compte ce qu'il intercepte |
| Hooks git pre-commit/pre-push | idem | ⚠️ **ne pas utiliser `core.hooksPath`** : il désactiverait le pre-commit de portfolio-tracker (`.git/hooks/pre-commit`). Chaîner dans le hook existant |
| Verrou d'orchestration | un seul utilisateur ; conflit réel seulement avec la boucle de nuit (`autoloop`) | deux orchestrateurs (Claude + Codex, ou nuit + jour) sur un même projet |
| Socle structurel `contracts/`, `tests/jalons/`, `spikes/` | rigide sur un projet existant (exploration-science a `schemas/`) | passage en N2 ; déclarer les chemins dans le frontmatter plutôt qu'imposer des dossiers |
| Briefing / rapport de lot en fichiers (`specs/briefings/`, `specs/reports/`) | le contrat worker §6 existe, en mémoire de conversation | chantier multi-comptes : un fournisseur externe a besoin d'un briefing autonome sur disque |
| File unique `_governance/decisions-en-attente.md` | utile surtout quand plusieurs sessions avancent sans l'utilisateur | pilotage mobile de plusieurs projets SDD en parallèle |
| `AGENTS.md` canonique + adaptateurs (prompt 1) | Codex non configuré ; risque de régression sur Claude | Codex orchestrateur |
| Revue croisée par défaut, défauts consignés par paire auteur/relecteur | dépend du chantier multi-comptes | multi-comptes livré |
| N2 (contrats, CR/ADR, traçabilité) et N3 (specs de modules, gates G2–G4) | le mode de panne réel est la dérive de cap, pas la violation de contrats | N1 a réduit les réorientations (lu dans le journal) ET un projet a assez de modules pour paralléliser. Référence : `reference/n2-n3.md`, à ne lire qu'à ce moment |

## Observations à ne pas perdre

- **portfolio-tracker** : le principe le plus efficace (« agir comme un fonds d'investissement »)
  n'apparaît pas tel quel dans son `CLAUDE.md` ; ses effets oui (comité, PV, signature). La
  jurisprudence y est accumulée sans consolidation : ~140 décisions numérotées dans un fichier
  chargé à chaque session (17 Ko). Candidat à une **formalisation en lecture seule** (rédiger
  `MISSION.md` + consolider la jurisprudence) le jour où ce sera sans risque — le projet
  progresse bien, ne pas l'activer sans raison (décision de l'utilisateur, 2026-10-21).
- Le levier principal est probablement **petit** : en SDD, le `00-REPRISE.md` stocke le jalon
  actif et non « la prochaine étape », qui est recalculée à rebours.
- Historique à respecter (`CONTROL_SYSTEM.md`, en tête) : sprints, `SESSION.md` et tickets
  comme unités de découpage ont été retirés le 2026-09-05 parce qu'ils n'étaient pas appliqués.
  Tout mécanisme ajouté ici doit prouver qu'il est utilisé (journal de lots), sinon il est retiré.
