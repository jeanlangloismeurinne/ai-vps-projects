# Mission : construire un mode de développement « SDD » activable par projet, et le tester sur exploration-science

## Prérequis

La mission « gouvernance neutre » est terminée : `AGENTS.md` racine canonique, adaptateurs Claude et Codex, skills neutres dans `_governance/skills/`, `run_agent.sh`, `install.sh`. Vérifie-le avant toute chose. Si ce n'est pas le cas, arrête-toi et dis-le-moi.

## Contexte

Monorepo `/root/ai-vps-projects`. Gouvernance en vigueur : AGENTS.md + adaptateurs, CONTROL_SYSTEM.md, 00-REPRISE.md.

Projet pilote : **exploration-science** — outil pédagogique d'exploration de systèmes scientifiques et techniques. Une spec v1 existe. Localise le projet et sa spec ; s'ils ne sont pas dans le monorepo, demande-moi où ils se trouvent.

Problème que le cadre doit résoudre en priorité : **l'orchestrateur perd de vue les principes clés et doit être régulièrement réorienté.** Tout ce qui ne sert pas cet objectif, ou la délégation fiable du code, est suspect.

Document de référence pour N2 et N3 : `_governance/sdd/reference/n2-n3.md` (fourni séparément). **Ne le lis pas** avant que je décide d'activer N2 sur un projet.

---

## Le modèle

### Deux axes indépendants

**Axe 1 — Rigueur.**
- **Mode simple** : le défaut, implicite. Un projet sans champ `mode` est en mode simple. Aucun script, hook ou gate SDD ne s'applique à lui : le cadre est strictement inerte.
- **Mode SDD**, à trois niveaux cumulatifs :
  - **N1 — Cap** : mission, principes ordonnés, jalons fonctionnels, CAP.md, recentrage, jurisprudence ;
  - **N2 — Contrats** : N1 + architecture, contrats en code, traçabilité, gestion du changement ;
  - **N3 — Délégation contrôlée** : N2 + specs de modules, tests écrits avant le code, gates bloquantes, parallélisme.

**Axe 2 — Exécution.**
- `orchestrateur` : claude | codex. Un seul orchestrateur actif par projet à un instant donné.
- `executants_autorises` : liste des fournisseurs qui peuvent écrire du code ou relire sur ce projet.

Un projet peut être en N1 avec Codex orchestrateur, ou en N1 avec Claude qui sous-traite un lot à Codex. La sous-traitance n'est pas réservée à N3.

### Source de vérité unique

Frontmatter YAML en tête de `00-REPRISE.md` :

```yaml
mode: sdd            # absent = simple
niveau: N1
active_le: 2026-..   # date et raison de la dernière décision
raison: ...
orchestrateur: claude
executants_autorises: [claude, codex]
modules: [...]
```

Il n'y a pas d'autre fichier de configuration avant N3.

### Socle structurel (tout projet SDD, dès N1)

Coût quasi nul, mais il rend la montée de niveau bon marché :
- modules déclarés dans le frontmatter ;
- types partagés dans `contracts/` dès la première ligne de code, même sans spec ;
- `tests/jalons/` existe ;
- `spikes/` pour le code jetable, jamais importé.

### Activation, montée, descente

- Décision consignée dans le frontmatter (niveau, date, raison), prise par moi uniquement, sur proposition argumentée.
- **Nouveau projet** : il entre directement au niveau adapté à sa taille attendue.
- **Projet existant** : il passe par N1 avant N2.
- **Descente ou désactivation** : les artefacts restent et servent de documents de référence. Aucun code n'est supprimé.

---

## Principes non négociables

- **La mission prime.** Ce qui ne se rattache pas à la mission est suspect par défaut.
- **On avance par jalon fonctionnel** : une capacité observable par l'utilisateur, avec un scénario de démonstration exécutable.
- **Un arbitrage cite un principe directeur.** Sans principe applicable, c'est à moi de trancher. La décision devient jurisprudence.
- **Une décision est dans la spec ou elle est escaladée.** Un exécutant ne tranche jamais une décision visible hors de son périmètre.
- **Personne ne valide son propre travail.** Le relecteur est un fournisseur différent de l'auteur quand c'est autorisé ; sinon, une session neuve en contexte forké.
- **Les contrôles vivent hors de l'agent** : hooks git et scripts, valables quel que soit le fournisseur. Les hooks propres à une CLI ne servent qu'au retour anticipé.
- **Économie de contexte**, voir la section suivante.
- **Construction juste-à-temps du cadre.** Les artefacts d'un niveau sont construits la première fois qu'un projet l'active, puis réutilisés par tous.
- **Rigueur proportionnée.** Une gate qui n'intercepte rien est allégée.
- **Je co-écris** la mission, les principes, la roadmap et les specs. Tu audites, proposes, rédiges des amendements ; je tranche. Une lacune devient une question, jamais un complément de ton cru.
- **Statut explicite** : « implémenté — vérifié le … » ou « proposé, non implémenté ».

## Répartition du cadre : où vit chaque chose

| Couche | Rôle | Chargement |
|---|---|---|
| Scripts et hooks git | vérifier | jamais chargés dans le contexte |
| Fichiers d'état (00-REPRISE, CAP.md, mission, jurisprudence) | dire où on en est | CAP.md au démarrage de session ; le reste à la demande |
| Skills (`_governance/skills/sdd-*`) | dire comment faire | description seule, corps au déclenchement |
| AGENTS.md (racine et projet) | pointeurs + interdits | toujours, donc minimal |

Règle : un fichier d'état ne contient jamais de procédure ; un skill ne contient jamais d'état de projet. La section SDD de CONTROL_SYSTEM.md tient en une vingtaine de lignes et renvoie aux skills.

Les skills de QC et de relecture s'exécutent en contexte forké, ou chez un autre fournisseur via `run_agent.sh`, pour garder le contexte de l'orchestrateur propre.

---

## Phase 0 — Reconnaissance (lecture seule, brève)

1. Vérifie le prérequis. Reprends le rapport de capacités des CLI de la mission précédente, sans le refaire.
2. Localise exploration-science et sa spec. Fais-les résumer par un sous-agent ; ne les charge pas en entier.
3. Vérifie, pour Codex, ce dont le cadre a besoin et qui n'aurait pas été couvert : injection d'un fichier au démarrage de session (hook ou équivalent), comportement dans un worktree.

**Livrable :** 10 lignes maximum. **STOP.**

---

## Phase 1 — Construire le kit « simple + N1 + exécution »

Emplacement : `/root/ai-vps-projects/_governance/sdd/`.

### 1.1 Mode simple
- Template de 00-REPRISE.md avec frontmatter facultatif et ligne recommandée **objectif courant**, formulée comme une capacité utilisateur.
- Aucun diff sur les 00-REPRISE existants : l'absence de champ vaut « simple ».

### 1.2 Kit N1
Templates :
- `00-mission.md` : une page. Utilisateur et valeur (en résultat, pas en fonctionnalité), mesure de succès, non-objectifs, **modèle de référence** s'il existe, 3 à 7 **principes ordonnés** (énoncé, question-test, exemple d'arbitrage).
- `01-roadmap-jalons.md` : chaque jalon est une capacité observable, avec scénario dans `tests/jalons/`, éléments de mission servis, modules traversés.
- `CAP.md` : 15 lignes maximum. Mission en une phrase ; principes en une ligne chacun ; jalon actif et scénario ; étapes restantes **recalculées depuis le jalon** ; ce qui bloque.
- `jurisprudence.md` : arbitrages tranchés, chacun avec le principe invoqué. Chaque entrée devient un dilemme du test d'arbitrage.
- **Journal de lots** en pied de 00-REPRISE : une ligne par lot (date, exécutant, étape du jalon avancée oui/non).

Skills :
- `sdd-recentrage` : réécrit CAP.md depuis la mission et le jalon, sans regarder l'ancienne liste. Déclencheurs : début de session, jalon atteint, changement de niveau ou de mission, **coupe-circuit** (3 lots sans avancement du jalon, ou plus de 2 lots sur un même bug, lus dans le journal).
- `sdd-qc-mission` : critères B/M/m ci-dessous, puis **test d'arbitrage** — un relecteur neuf reçoit uniquement 00-mission.md et les dilemmes (5 au départ, plus la jurisprudence) ; il doit trancher comme moi.
  - (B) Utilisateur et valeur explicites, valeur en résultat.
  - (B) Mesure de succès.
  - (B) Principes ordonnés, chacun avec question-test et exemple.
  - (M) Modèle de référence proposé, ou absence justifiée.
  - (B) Premier jalon avec scénario de démonstration.
  - (M) Chaque jalon sert au moins un élément de la mission.
- `sdd-adoption-n1` : extraire mission et principes d'un projet existant ou d'une spec. N'ajoute rien qui n'y figure pas ; les lacunes deviennent des questions.
- `sdd-lot` : briefing et rapport de lot pour la sous-traitance.

**Triage des bugs** (dans `sdd-recentrage`) : un bug n'est traité tout de suite que s'il bloque le scénario du jalon actif. Sinon, il devient un ticket.

### 1.3 Exécution multi-fournisseurs
- **Briefing de lot** (`specs/briefings/`), autonome : mission en une phrase, principes, jalon et étape visée, tâche, chemins des contrats et des tests, interdits (pas d'écriture dans `specs/`, `contracts/`, `tests/jalons/` sauf mention contraire), format de sortie. Jamais de secret ni de donnée réelle.
- **Rapport de lot** (`specs/reports/`), rubriques fixes : fait ; décisions locales prises ; étape du jalon avancée ; tests ; escalades.
- Le lanceur réutilise `run_agent.sh` de la mission précédente et ajoute : génération du briefing, récupération du rapport, mise à jour du journal, `check_gates`. Repli sur l'orchestrateur après deux échecs consécutifs d'un fournisseur, avec incident consigné.
- **Revue croisée par défaut** : le code d'un fournisseur est relu par un autre quand c'est autorisé. Défauts consignés par paire auteur/relecteur.
- **Verrou d'orchestration** : un orchestrateur prend le verrou en début de session et le rend à la fin. Le passage de relais entre Claude et Codex se fait uniquement par 00-REPRISE et CAP.md.

### 1.4 Contrôles mécaniques
- **`check_gates.py <projet>`** : lit le frontmatter et **sort immédiatement si le projet est en mode simple**. En N1, il vérifie :
  - présence et taille de CAP.md ;
  - frontmatter valide ;
  - scénario du jalon actif présent ;
  - fournisseur autorisé pour chaque rapport de lot ;
  - aucun import depuis `spikes/` ;
  - intégrité de `contracts/` et `tests/jalons/` quand un exécutant autre que l'orchestrateur a écrit le lot.

  Il compte les défauts réellement interceptés.
- **Hooks git** (pre-commit, pre-push), installés par `core.hooksPath` : exécutent check_gates sur les projets touchés et contrôlent le verrou.
- **Démarrage de session** : CAP.md (mode SDD) ou 00-REPRISE.md (mode simple) injecté par hook quand la CLI le permet ; sinon, instruction en tête de l'AGENTS.md du projet.

### 1.5 File de décisions
Une seule file pour tout le monorepo : `_governance/decisions-en-attente.md`. Chaque entrée contient : projet, question, options, recommandation et principe invoqué, ce qui est bloqué.

Le cadre n'envoie aucune notification (ni Slack, ni autre canal) : je pilote les sessions depuis les applications mobiles des fournisseurs. Quand une décision bloque, l'orchestrateur la consigne dans la file, me la pose dans la session en cours, avance sur ce qui n'est pas bloqué, puis s'arrête proprement si plus rien ne l'est. En début de session, il signale les entrées ouvertes de la file qui concernent le projet.

### 1.6 Preuves sur projets fictifs
- Projet en mode simple : check_gates et les hooks n'ont **aucun** effet, et leur temps d'exécution est négligeable.
- Projet en N1 :
  - le coupe-circuit se déclenche sur un journal fabriqué ;
  - un lot sous-traité qui modifie `tests/jalons/` est bloqué au commit ;
  - un lot Claude → Codex et une relecture Codex → Claude passent de bout en bout ;
  - un second orchestrateur est refusé par le verrou.
- Budget de contexte mesuré : démarrage d'une session sur le projet N1, pour chaque CLI.

**STOP — attends ma validation.**

---

## Phase 2 — Note d'activation sur exploration-science

Une page :
- état du projet ;
- niveau d'entrée recommandé et pourquoi. C'est un nouveau projet : l'entrée directe en N2 est possible si la taille le justifie, mais N1 se construit d'abord dans tous les cas ;
- orchestrateur proposé et exécutants autorisés ;
- ce que je devrai observer pour me faire un avis (pas de mesure formelle : un ressenti appuyé sur le journal de lots).

**STOP.** J'active ou non.

## Phase 3 — N1 sur exploration-science

1. Avec `sdd-adoption-n1`, extrais de la spec ce qui relève de la mission, des principes et d'un éventuel modèle de référence.
2. Propose un brouillon de 00-mission.md, la roadmap des jalons et 5 dilemmes. Les lacunes vont dans la file de décisions.

**STOP.** On finalise ensemble jusqu'à la gate M.

3. Travaille un jalon en N1. Au moins un lot est sous-traité à Codex et relu par Claude, ou l'inverse. La gate J est validée par moi sur démonstration du scénario.

## Phase 4 — N2 et N3, uniquement si je le décide

À la première activation de N2 : lis alors `_governance/sdd/reference/n2-n3.md`, transforme-le en templates, skills et règles de check_gates, puis applique-le au pilote. Même chose pour N3. Les modules hérités relèvent de l'effet cliquet décrit dans la référence.

## Phase 5 — Rétrospective

1. Escalades et réorientations que j'ai dû faire : quel mécanisme aurait dû les éviter ? Durcis-le.
2. Gates et contrôles qui n'ont rien intercepté : propose de les alléger.
3. Codex face à Claude, comme orchestrateur et comme exécutant : qualité, fiabilité, défauts trouvés en revue croisée.
4. Budget de contexte : ce qui est chargé et n'a pas servi.
5. Mets à jour CONTROL_SYSTEM.md (« SDD — expérimental », avec les statuts) et le 00-REPRISE du pilote.
6. Rapport en 10 lignes, avec une recommandation de niveau d'entrée par défaut pour les futurs projets.

## Règles de conduite

- Annonce chaque lot en une ligne, avec l'étape du jalon qu'il fait avancer.
- Respecte strictement les STOP.
- En cas de doute : relis CAP.md (ou 00-REPRISE.md en mode simple), puis les principes non négociables.
