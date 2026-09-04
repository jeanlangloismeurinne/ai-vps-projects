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

### §9 — Un check V2 ne peut pas tourner sans les secrets V1 (Dust/Slack/FMP)

**Constat.** `Settings` (`portfolio-tracker/backend/app/config.py`) déclare `DUST_API_KEY`,
`DUST_RESEARCH_AGENT_ID`, `DUST_PORTFOLIO_AGENT_ID`, `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`,
`SLACK_PORTFOLIO_CHANNEL_ID` et `FMP_API_KEY` **sans valeur par défaut**. N'importe quel check —
même 100 % V2, même sans réseau, même sans DB — échoue à l'import tant qu'on ne lui passe pas ces
sept variables bidons. D'où le bloc `ENV` de `checks/README.md`, recopié à la main à chaque appel.

**Preuve.** `docker run --network none … python checks/check_runner_telemetry.py` sans variables →
`ValidationError: FMP_API_KEY Field required` (+ 6 autres). Le check en question ne touche ni Dust,
ni Slack, ni FMP : il exerce le runner V2 contre un provider bouchonné.

**Pourquoi ça coûte, au-delà de la frappe.** La commande *a l'air fausse* : elle étale des
identifiants Dust (V1) dans une vérification V2, alors que la disjonction V1/V2 est un principe
structurant du projet. Dans cette session, l'utilisateur a refusé la commande pour cette raison
précise — **et il avait raison de la trouver suspecte**. Une commande dont la forme contredit
l'architecture se fait refuser, et chaque refus coûte un aller-retour.

**Correctif proposé** (aucun n'est appliqué, arbitrage requis) :
- **(a) — le moins risqué.** Un fichier `backend/checks/env.checks` (valeurs factices, versionné,
  aucun secret) + `--env-file checks/env.checks` dans le README. La commande cesse d'énumérer du
  V1 ; l'incohitude de fond demeure mais n'est plus sous les yeux à chaque appel. Effort : ~15 min.
- **(b) — traite la cause.** Rendre ces champs optionnels dans `Settings` et valider leur présence
  **au démarrage de l'app** (V1 seulement), pas à l'import du module. ⚠️ C'est un desserrage de
  schéma : sans la validation de démarrage écrite **en même temps**, la prod démarrerait sans clés
  Dust en silence — exactement le mode de panne que la mémoire `feedback_optional_schema_gate`
  décrit. À ne faire que d'un bloc. Effort : ~1 h + un re-test de démarrage réel.

**Recommandation** : (a) maintenant, (b) seulement si un autre projet rencontre le même couplage.

### §10 — Un check neuf n'est pas livrable tant qu'il n'a pas viré au rouge une fois

**Constat.** Rien n'oblige aujourd'hui à éprouver un `check_*.py` par test négatif. Or ce projet a
déjà été mordu deux fois par des vérifications qui réussissaient **toujours** : `node --check`
(no-op sur fichiers ESM, rendait 0 sur du JSX cassé) et les 162 assertions d'un sous-agent qui
tournaient contre ses propres fixtures. Un contrôle qui ne peut pas échouer est pire qu'aucun
contrôle : il se rapporte comme une preuve.

**Preuve, chiffrée, obtenue dans cette session.** `check_runner_telemetry.py` rendait 46/46 au
vert. Dette réintroduite volontairement (suppression du report de coût de la boucle d'outils) →
**3 échecs, exit 1**, pointant §7 : `3850` tokens réellement facturés contre `850` comptabilisés.
Le test négatif n'a pas seulement prouvé que le check mesure quelque chose — il a **chiffré
l'enjeu** (78 % de la facture d'un run d'ouvrier) et c'est ce chiffre qui justifie le correctif.

**Correctif proposé.** Deux lignes dans `CONTROL_SYSTEM.md` § « Contrat du sous-agent worker » :
tout `check_*.py` neuf est livré avec (1) la modification exacte qui le fait échouer et (2) la
sortie rouge correspondante. Sans ces deux pièces, le check est réputé non éprouvé et doit être
annoncé comme tel. Effort : ~10 min. Destination durable : `CONTROL_SYSTEM.md` (transverse).

### §11 — La dette décrite dans un fichier de reprise est un symptôme, pas un périmètre

**Constat.** `00-REPRISE.md` décrivait la dette du runner comme « la dépense de **cette tentative**
n'est pas comptabilisée » — formulation exacte reprise à l'identique dans les commentaires de
`monitoring.py`, `exit.py` et `debate.py`. Trois fichiers d'accord entre eux, donc crédibles.

**Preuve.** La lecture de `runner.py` a montré que le trou principal était **ailleurs** : quand la
clôture de `run_tool_json_agent` échoue, c'est le coût de **toute la boucle d'outils** qui
disparaît — plusieurs tours à gros contexte, mesurés à 78 % de la facture. Aucune des trois
mentions ne le disait ; elles décrivaient le symptôme observé depuis le site d'appel.

**Enseignement réplicable, tous projets.** Un fichier de reprise dit **où regarder**, jamais
**jusqu'où va le problème**. Le périmètre d'une dette se relit dans le code au moment de la
traiter, sinon on livre un correctif calibré sur la description et on laisse le gros du trou
ouvert — avec, en prime, la conviction de l'avoir fermé. Coût de la relecture ici : ~10 min pour
un correctif 4× plus large. Destination durable : mémoire auto.

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
