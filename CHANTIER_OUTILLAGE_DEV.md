# Chantier — friction d'outillage de développement (transverse, tous projets)

**Rôle de ce fichier : un tampon, pas une archive.** On y note les frictions d'outillage
constatées en session (permission refusée, script manquant, contournement répété) pour les
traiter à froid. **Dès qu'un point est appliqué, on supprime sa section** — seule une ligne
dans le journal en bas subsiste. Sans cette discipline le fichier grossit et coûte du contexte
à chaque session qui l'ouvre.

**Où va la connaissance quand on supprime une section.** Un point appliqué laisse presque
toujours quelque chose qui n'est gardé par aucun check automatique. Ça ne reste pas ici :

| Nature du constat | Destination |
|---|---|
| Règle de permission | `~/.claude/settings.json` — qui devient la source de vérité |
| Piège d'usage d'un script | l'en-tête du script lui-même |
| Règle de méthode / mode de panne silencieux | mémoire auto (`~/.claude/projects/-root/memory/`) |
| Convention de projet | `CLAUDE.md` du projet, ou `CONTROL_SYSTEM.md` si transverse |

**Qui applique.** Le classifieur refuse l'auto-édition de `settings.json` par l'assistant, y
compris via la skill `update-config` (re-vérifié le 2026-09-03) — c'est un garde-fou : un
assistant ne s'octroie pas ses propres droits. Il passe si **l'utilisateur demande l'édition en
clair** dans la session. Donc : l'assistant diagnostique et rédige le patch, l'utilisateur
autorise.

---

## En attente

*(rien — ajouter ici les frictions constatées, une section par point : constat, preuve, correctif
proposé, effort, et si un arbitrage humain est requis)*

---

## Journal des points soldés

Une ligne par point traité, pour ne pas le re-diagnostiquer. Le détail vit à sa destination.

- **2026-09-02 — §1+§2 allow-list `deploy.sh` + outils texte.** 19 règles ajoutées à
  `~/.claude/settings.json`.
- **2026-09-02 — §3 `deploy.sh --rebuild-only`.** Redéploie un commit déjà poussé sans
  fabriquer de commit vide. ⚠️ Jamais éprouvé en conditions réelles à ce jour.
- **2026-09-02 — §4 `infrastructure/shoot.sh`.** Captures headless ; un HTTP 200 ne prouve rien
  sur l'affichage. Limite (capture non authentifiée) documentée dans l'en-tête du script.
- **2026-09-02 — §5 contrat de sous-traitance aux agents Sonnet.** Deux règles dans
  `CONTROL_SYSTEM.md` § « Contrat du sous-agent worker ».
- **2026-09-03 — §6 coût de contexte fixe.** Résolu par compression du `CLAUDE.md` de
  portfolio-tracker (56 → 38 Ko) : pointeur d'une ligne quand un `check_*.py` garde la règle,
  prose intégrale + tag ⚠️ sinon. Voir mémoire `feedback_convention_compression_by_test_coverage`.
- **2026-09-03 — §7 deuxième relevé de permissions.** 12 règles ajoutées à `settings.json`.
  Le piège des préfixes (`timeout`/`env` neutralisent une règle `Bash(x:*)`) est en mémoire :
  `feedback_permission_prefix_trap`.
- **2026-09-03 — §8 `~/.netrc` cassait tous les `git push`.** Réglé ; push vérifié sans
  contournement le 2026-09-03. Diagnostic et faux-ami en mémoire :
  `reference_netrc_bloque_git_push`.

## Voir aussi

- `DEPLOY.md` — protocole de déploiement nominal.
- `COOLIFY_PLAYBOOK.md` — rebuild, tokens, labels Traefik, UUIDs.
