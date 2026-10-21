# Mission : rendre la gouvernance du monorepo neutre vis-à-vis du fournisseur (Claude Code + Codex)

## Contexte

Tu travailles dans le monorepo `/root/ai-vps-projects`. La gouvernance actuelle (CLAUDE.md, CONTROL_SYSTEM.md, SESSION_BRIEF.md, fichiers 00-REPRISE.md, configuration `.claude/`) est écrite pour Claude Code. Elle reste en vigueur pendant toute la mission.

Objectif : que Codex puisse travailler sur le monorepo de deux façons, avec les mêmes règles que Claude :
- **en sous-traitance headless**, appelé par une session Claude Code ;
- **en orchestrateur autonome**, avec un rôle équivalent à celui de Claude Code, et capable d'appeler Claude en headless (relecture, sous-traitance).

Cette mission ne crée aucun cadre SDD. Elle prépare le terrain pour une mission ultérieure.

## Principes

- **Zéro régression pour Claude.** Après migration, une session Claude Code se comporte exactement comme avant.
- **Une règle, un seul endroit.** Les règles du monorepo vivent dans `AGENTS.md` racine, canonique. Les fichiers propres à un fournisseur ne contiennent que la traduction de ces règles dans ses mécanismes.
- **Règles formulées en rôles, pas en modèles.** « Les opérations git passent par un exécutant dédié », et non « par un sous-agent Sonnet ». La correspondance rôle → modèle est dans l'adaptateur.
- **Économie de contexte.** Ce qui est toujours chargé est court. Les procédures longues et rarement utilisées deviennent des skills, chargés à la demande. Les contrôles deviennent des scripts.
- **Rien d'inventé.** Toute syntaxe, tout emplacement de fichier, tout comportement d'une CLI est vérifié dans la documentation officielle. Pour Claude Code, passe par le sous-agent `claude-code-guide`.
- **Statut explicite.** Dans tout document de gouvernance : « implémenté — vérifié le … » ou « proposé, non implémenté ».
- **Je tranche.** Tu proposes des diffs ; rien n'est appliqué sans mon accord.

---

## Phase 0 — Reconnaissance (lecture seule)

1. **Inventaire des instructions.** Recense tout ce qui instruit un agent : CLAUDE.md (racine et projets), CONTROL_SYSTEM.md, SESSION_BRIEF.md, 00-REPRISE.md (structure uniquement, via un sous-agent qui résume), `.claude/` (settings, hooks, agents, skills, commandes), skills partagés.
2. **Classement des règles.** Pour chaque règle : universelle / propre à Claude / obsolète / contradictoire avec une autre. Cite la source.
3. **Capacités des CLI.** Pour Codex CLI, Claude Code et, à titre d'information, Grok Build :
   - installé ou non, version ;
   - authentification (abonnement ou clé API) ;
   - mode non interactif (commande, options de sandbox et d'approbation, sortie exploitable) ;
   - fichiers d'instructions lus nativement, hiérarchie (racine / sous-dossier) et limite de taille éventuelle ;
   - support des skills : format, emplacement, découverte ;
   - hooks : existence et événements disponibles ;
   - sous-agents ou délégation interne ;
   - accès réseau et accès aux fichiers `.env` dans son mode par défaut.
4. **Conflits à me soumettre**, au minimum :
   - la règle « tout sous abonnement Claude Code, jamais d'API externe ». Propose une reformulation (par exemple : pas de facturation à l'usage non plafonnée ; fournisseurs autorisés par projet) ;
   - l'accès de Codex aux secrets et à l'API Coolify (règle d'autonomie Coolify) ;
   - les projets à données personnelles ou financières (bank-review notamment) : fournisseurs autorisés par défaut ;
   - la règle git (exécutant dédié, branche main) quand Codex orchestre.
5. **Mesure de départ du contexte.** Nombre approximatif de tokens chargés au démarrage d'une session Claude Code à la racine et dans deux projets.

**Livrable :** un rapport court avec trois tableaux (règles classées, capacités des CLI, conflits) et un plan de migration.

**STOP.**

---

## Phase 1 — Proposition de la structure cible (diffs non appliqués)

1. **`AGENTS.md` racine** : toutes les règles universelles, en rôles. Budget : court, sous la limite de taille lue par Codex, avec des pointeurs plutôt que des procédures.
2. **`CLAUDE.md` racine** : importe AGENTS.md, puis ajoute uniquement la traduction Claude (tiering Opus/Sonnet, sous-agent git, hooks Claude Code, sous-agents).
3. **Adaptateur Codex** : l'équivalent pour Codex, selon ses mécanismes vérifiés en phase 0 (configuration, profil d'exécution headless, traduction des rôles).
4. **Fichiers d'instructions par projet** : même schéma. Un AGENTS.md de projet ne répète jamais une règle racine.
5. **Skills neutres** : les skills partagés existants et les procédures longues de CONTROL_SYSTEM.md qui ne servent qu'occasionnellement migrent dans `_governance/skills/` au format commun. Ils sont exposés à chaque CLI par lien symbolique vers son répertoire natif. Si un format diffère, le skill source reste unique et l'adaptation est générée.
6. **Délégation croisée** : `_governance/scripts/run_agent.sh <provider> <fichier-tâche> [worktree]`. Il appelle la CLI en mode non interactif, dans un worktree isolé, et refuse tout fournisseur non autorisé pour le projet. Il doit fonctionner dans les deux sens : Claude → Codex et Codex → Claude.
7. **`_governance/install.sh`** : configure un clone neuf du repo (liens des skills, `core.hooksPath`), pour que la gouvernance s'applique aussi hors du VPS.
8. **CONTROL_SYSTEM.md** : allégé de ce qui part dans AGENTS.md ou dans les skills ; il garde le fonctionnement du pilotage (00-REPRISE, lots, Hub) et renvoie au reste.

Présente :
- les diffs ;
- la table de correspondance « règle actuelle → nouvel emplacement », sans perte ;
- le budget de contexte estimé au démarrage, avant et après, pour chaque CLI.

**STOP — attends ma validation.**

---

## Phase 2 — Application et tests de non-régression

Application via l'exécutant git dédié, en commits atomiques et réversibles.

Tests :
1. **Test de restitution.** Rédige 10 questions dont la réponse est une règle clé (git, Coolify, tickets, reprise de projet, tiering, secrets…). Une session Claude neuve et une session Codex neuve y répondent sans autre contexte que le démarrage normal. Les réponses doivent être justes et cohérentes entre elles.
2. **Sous-traitance Claude → Codex.** Une tâche triviale sur un projet sans données sensibles, via `run_agent.sh`, dans un worktree, avec fusion par l'exécutant git.
3. **Sous-traitance Codex → Claude.** Une relecture triviale demandée par Codex à Claude en headless.
4. **Refus.** `run_agent.sh` refuse Codex sur bank-review.
5. **Mesure du contexte** au démarrage, comparée à la phase 0.

## Phase 3 — Clôture

- Statuts « implémenté — vérifié le … » dans CONTROL_SYSTEM.md et AGENTS.md.
- Rapport en 10 lignes : ce qui a migré, ce qui reste propre à Claude, écarts de comportement observés entre les deux CLI, gain ou perte de contexte.

## Règles de conduite

- Annonce chaque lot en une ligne.
- Respecte strictement les STOP.
- Aucune modification de code applicatif : seuls les fichiers d'instructions, de configuration d'agent, les skills et les scripts de `_governance/` sont concernés.
