# DEPLOY.md — Protocole de livraison (commit → push → rebuild Coolify)

> Instructions pour Claude Code. À appliquer **en fin de session**, une fois une ou plusieurs
> features livrées — que la session ait été menée en direct dans le terminal ou via le
> système de tickets (`CONTROL_SYSTEM.md`).

## Objectif

Économiser le **contexte et le quota d'Opus**. La séquence commit/push/rebuild est verbeuse
(diff, logs de push, logs de build) mais mécanique : on la sort du contexte Opus. Deux niveaux :

- **Option 1 — script déterministe** (`infrastructure/deploy.sh`) : le chemin nominal. Un seul
  appel Bash, tout le verbeux est absorbé, seule une ligne `RESULT:` revient à Opus.
- **Option 2 — sous-agent Sonnet** : le filet. Uniquement **si l'option 1 échoue** (exit ≠ 0).
  Le sous-agent diagnostique et récupère avec le playbook Coolify, et ne renvoie qu'un statut court.

## Quand déclencher

À la fin d'une session ayant produit du code déployable. Ne PAS déployer si la session n'a
touché que des docs/tickets sans changement de code applicatif.

## Option 1 — le chemin nominal

Opus connaît déjà les fichiers qu'il a modifiés dans la session : **pas d'exploration**. Il fait
**un seul appel**, en passant la liste exacte des fichiers de la feature (périmètre juste par
construction — pas de mélange inter-projets dans le repo mono-repo).

```bash
infrastructure/deploy.sh <app> -m "<message de commit>" -f "<fichiers de la feature>" [-e KEY=VALUE ...]
```

- `<app>` : clé Coolify — `bank-review`, `assistant-ia`, `ev-prices`, `tool-file-intake`, `hub`,
  `comms-gateway`, `portfolio-backend`, `portfolio-frontend`. Pour portfolio-tracker (2 apps), **deux appels**.
  (`newsletter-summary` n'est **pas** une app Coolify gérée par deploy.sh : conteneur standalone.)
- `-f` : chemins relatifs à la racine du repo, séparés par des espaces. Le script `git add` ces
  chemins puis **commite l'index seul** ; il **refuse si rien n'est à committer**.
  Variante : `--staged` (Opus a déjà fait `git add`) au lieu de `-f`.
- `-e KEY=VALUE` (répétable) : nouvelles variables d'env Coolify, écrites **automatiquement**
  avant le rebuild (elles doivent exister au build). La valeur n'est jamais loggée ; seule la clé
  l'est. À utiliser quand la feature introduit une nouvelle variable d'environnement.

Ce que le script fait, dans l'ordre : stage → commit (avec `Co-Authored-By`) → `git push origin main`
→ écrit les env vars via Eloquent dans le container `coolify` → déclenche le rebuild (méthode PHP
vérifiée, sans token) → surveille la file de déploiement jusqu'à `finished`. La notification Slack
de déploiement part automatiquement (via `post_deployment_command`, cf. CLAUDE.md).

**Lecture du résultat par Opus** — dernière ligne :
- `RESULT: success — …` → terminé. Reporter à l'utilisateur (app, SHA court, #deployment).
- `RESULT: failure — …` (exit ≠ 0) → **basculer sur l'option 2**.

Codes d'échec : `2` rien à committer · `3` app inconnue · `4` push refusé · `5` échec env ·
`6` rebuild non déclenché · `7` build en erreur/timeout.

> **Cas particulier — code 7 uniquement.** C'est le seul code ambigu : vrai échec de build **ou**
> faux négatif de monitoring (blip transitoire du poll DB pendant un build lourd). Avant de lancer
> le sous-agent, faire **une seule** requête de vérification — coût ~1 aller-retour Bash, négligeable
> devant un sous-agent Sonnet démarré à froid + un rebuild potentiellement redondant. Le `#DEPLOY_ID`
> figure dans la ligne `RESULT: failure` :
> ```bash
> docker exec coolify-db psql -U coolify -d coolify -tAc \
>   "SELECT status FROM application_deployment_queues WHERE id=<DEPLOY_ID>"
> ```
> `finished` → le déploiement est en fait OK : reporter *success*, **ne pas** lancer le fallback.
> Autre valeur → basculer sur l'option 2. Les codes `2/3/4/5/6` sont sans ambiguïté : fallback direct,
> aucune vérif.

## Option 2 — fallback sous-agent Sonnet

Uniquement si l'option 1 sort en échec. Opus **ne débogue pas lui-même** (ça remplirait son
contexte) : il lance un sous-agent via l'outil `Agent`, `model: sonnet`, accès outils complet.

Prompt à passer au sous-agent (adapter les `{…}`) :

```
Tu es en charge de FINIR un déploiement qui a échoué. Contexte minimal :
- Repo : /root/ai-vps-projects (mono-repo, branche main, remote GitHub origin).
- App Coolify visée : {app} (UUID dans COOLIFY_PLAYBOOK.md § "UUIDs des applications Coolify").
- Commande tentée : infrastructure/deploy.sh {rappel des args}
- Sortie/erreur observée : {coller la ligne RESULT: + le contexte d'échec}
- Feature livrée : {1-2 phrases}   Nouvelles variables d'env attendues : {clés ou "aucune"}.

Playbook de référence : COOLIFY_PLAYBOOK.md (rebuild PHP sans token, monitoring DB,
génération de token API, env vars, labels Traefik). DEPLOY.md pour le contrat.

Objectif : commit/push si pas encore fait, écrire les env vars manquantes, déclencher le rebuild,
surveiller jusqu'à status 'finished'. Diagnostiquer et corriger la cause de l'échec (push rejeté,
conflit, label Traefik, source_type, etc.).

RÈGLE : ne réécris pas le code applicatif de la feature et ne modifie pas d'autres projets. Si la
cause dépasse le déploiement (bug de code, choix d'architecture, secret manquant côté utilisateur),
NE DEVINE PAS : rends la main avec un statut clair pour qu'Opus tranche.

Renvoie EXACTEMENT :
1. Cause de l'échec initial (1 phrase)
2. Actions correctives menées
3. Statut final du déploiement (#id + status) et URL/app concernée
4. Points restant à la charge de l'utilisateur (secrets, DNS, décision) — ou "aucun"
```

Opus lit ce compte-rendu, le reporte à l'utilisateur, et n'intervient dans le code que si le
point 4 l'exige.

## Choix Sonnet vs Haiku (fallback)

**Sonnet.** La récupération d'échec (push rejeté, conflit, label Traefik cassé, `source_type` nul)
demande du jugement ; Haiku tend à improviser au lieu d'escalader. Réserver Haiku au trivial.
