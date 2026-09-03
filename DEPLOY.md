# DEPLOY.md — Protocole de livraison (commit → push → build → vérification)

> Instructions pour Claude Code. À appliquer **en fin de session**, une fois une ou plusieurs
> features livrées — que la session ait été menée en direct dans le terminal ou via le
> système de tickets (`CONTROL_SYSTEM.md`).

> **Depuis le 2026-09-03, le déploiement se fait en `docker compose`, plus par Coolify.**
> Le script est `infrastructure/compose-deploy.sh` ; `infrastructure/deploy.sh` (Coolify) est
> neutralisé mais conservé pour le jour où Coolify serait remonté
> (`infrastructure/coolify-restore.sh`).

## Objectif

Économiser le **contexte et le quota d'Opus**. La séquence commit/push/build est verbeuse
(diff, logs de push, logs de build) mais mécanique : on la sort du contexte Opus. Deux niveaux :

- **Option 1 — script déterministe** (`infrastructure/compose-deploy.sh`) : le chemin nominal.
  Un seul appel Bash, tout le verbeux est absorbé, seule une ligne `RESULT:` revient à Opus.
- **Option 2 — sous-agent Sonnet** : le filet. Uniquement **si l'option 1 échoue** (exit ≠ 0).

## Quand déclencher

À la fin d'une session ayant produit du code déployable. Ne PAS déployer si la session n'a
touché que des docs/tickets sans changement de code applicatif.

## Option 1 — le chemin nominal

Opus connaît déjà les fichiers qu'il a modifiés dans la session : **pas d'exploration**. Il fait
**un seul appel**, en passant la liste exacte des fichiers de la feature (périmètre juste par
construction — pas de mélange inter-projets dans le repo mono-repo).

```bash
infrastructure/compose-deploy.sh <app> -m "<message de commit>" -f "<fichiers de la feature>" [-e KEY=VALUE ...]
```

- `<app>` : `bank-review`, `assistant-ia`, `ev-prices`, `tool-file-intake`, `hub`,
  `comms-gateway`, `portfolio-tracker`, `portfolio-backend`, `portfolio-frontend`.
  `portfolio-tracker` = toute la stack ; `portfolio-backend` / `portfolio-frontend` = un seul
  service de cette stack (les deux clés Coolify historiques restent valides, un seul appel suffit
  désormais si les deux ont changé).
  (`newsletter-summary`, `kb-viewer`, `provenance-viz` ne sont pas gérés par ce script.)
- `-f` : chemins relatifs à la racine du repo, séparés par des espaces. Le script `git add` ces
  chemins puis **commite l'index seul** ; il **refuse si rien n'est à committer**.
  Variante : `--staged` (Opus a déjà fait `git add`) au lieu de `-f`.
- `-e KEY=VALUE` (répétable) : écrit la variable dans le **`.env` du projet** avant le build.
  La valeur n'est jamais loggée ; seule la clé l'est. Le `.env` reste en `600` et hors git.
  Pour portfolio, viser `portfolio-backend` ou `portfolio-frontend` (deux `.env` distincts) —
  le script refuse `portfolio-tracker -e …` plutôt que de deviner la cible.
- `--rebuild-only` : rebuild du HEAD déjà poussé, sans commit ni push.

Ce que le script fait, dans l'ordre : stage → commit (`Co-Authored-By`) → `git push origin main`
→ écrit les `-e` dans le `.env` → `docker compose config -q` → `docker compose up -d --build`
→ **attend que le conteneur soit `running` (et `healthy` s'il déclare un healthcheck)** →
**sonde l'app et exige le code HTTP attendu** → envoie la notification Slack de déploiement
(bank-review, assistant-ia).

### Ce que la vérification attrape et que Coolify ne voyait pas

`deploy.sh` concluait au succès dès que Coolify disait `finished` : un conteneur qui démarre puis
meurt en boucle passait. `compose-deploy.sh` refuse de conclure tant que l'app n'a pas répondu.

Deux gardes valent d'être connues :
- **Code attendu, pas « code non catastrophique ».** Un premier jet acceptait « tout sauf 5xx » ;
  il a validé un **404 sur `/api/health`**. Pendant la recréation du backend, Traefik n'a plus de
  route `/api` et c'est le catch-all frontend qui répond — un 404 de Next.js, indiscernable d'un
  succès si on ne regarde que la classe du code. D'où l'attente de santé **avant** la sonde, et un
  code exact par app.
- **Unicité du domaine.** Le script compte les conteneurs portant `Host(<domaine>)` et échoue s'il
  y en a deux (sauf portfolio, où backend et frontend partagent le domaine via `PathPrefix`).
  C'est le garde-fou contre le double routage : deux conteneurs aux mêmes labels, et le proxy
  alterne entre ancien et nouveau code sans rien signaler.

**Lecture du résultat par Opus** — dernière ligne :
- `RESULT: success — …` → terminé. Reporter à l'utilisateur (app, SHA court, code HTTP).
- `RESULT: failure — …` (exit ≠ 0) → **basculer sur l'option 2**.

Codes d'échec : `2` rien à committer · `3` app inconnue · `4` push refusé · `5` échec écriture env ·
`6` compose invalide · `7` build en erreur/timeout · `8` build OK mais l'app ne répond pas.

> **Code 8 : ne pas relancer un build.** Le code est construit et poussé ; c'est le démarrage ou
> le routage qui cloche. Regarder `docker compose logs` et `docker ps` avant toute chose —
> rebuilder ne corrigera pas une variable d'env manquante ni un port qui ne correspond pas.

## Option 2 — fallback sous-agent Sonnet

Uniquement si l'option 1 sort en échec. Opus **ne débogue pas lui-même** (ça remplirait son
contexte) : il lance un sous-agent via l'outil `Agent`, `model: sonnet`, accès outils complet.

Prompt à passer au sous-agent (adapter les `{…}`) :

```
Tu es en charge de FINIR un déploiement qui a échoué. Contexte minimal :
- Repo : /root/ai-vps-projects (mono-repo, branche main, remote GitHub origin).
- Déploiement en docker compose standalone (PAS Coolify — arrêté depuis le 2026-09-03).
  La stack de l'app est projects/{app}/docker-compose.yml ; ses variables sont dans son .env
  local (chmod 600, hors git). Le proxy est `coolify-proxy` (Traefik), qui a survécu à la
  migration et route par labels Docker sur le réseau `coolify`.
- App visée : {app}
- Commande tentée : infrastructure/compose-deploy.sh {rappel des args}
- Sortie/erreur observée : {coller la ligne RESULT: + le contexte d'échec}
- Feature livrée : {1-2 phrases}   Nouvelles variables d'env attendues : {clés ou "aucune"}.

Objectif : commit/push si pas encore fait, écrire les variables manquantes dans le .env,
rebuilder (`docker compose up -d --build`), et VÉRIFIER que l'app répond réellement sur son
domaine. Diagnostiquer et corriger la cause de l'échec.

RÈGLES :
- Ne réécris pas le code applicatif de la feature, ne modifie pas d'autres projets.
- Ne conclus JAMAIS au succès sur la seule fin du build : montre la réponse HTTP obtenue.
- Vérifie qu'un SEUL conteneur porte les labels Traefik du domaine (double routage silencieux).
- Si la cause dépasse le déploiement (bug de code, choix d'architecture, secret manquant côté
  utilisateur), NE DEVINE PAS : rends la main avec un statut clair pour qu'Opus tranche.

Renvoie EXACTEMENT :
1. Cause de l'échec initial (1 phrase)
2. Actions correctives menées
3. Statut final : code HTTP obtenu sur quelle URL, et nom du conteneur qui sert
4. Points restant à la charge de l'utilisateur (secrets, DNS, décision) — ou "aucun"
```

Opus lit ce compte-rendu, le reporte à l'utilisateur, et n'intervient dans le code que si le
point 4 l'exige.

## Choix Sonnet vs Haiku (fallback)

**Sonnet.** La récupération d'échec (push rejeté, conflit, label Traefik cassé, variable
manquante) demande du jugement ; Haiku tend à improviser au lieu d'escalader. Réserver Haiku au
trivial.

## Revenir à Coolify

`infrastructure/coolify-restore.sh` — voir son en-tête. Rien n'a été détruit côté Coolify : la
base (`coolify-db`), `/data/coolify` et les sauvegardes sont intacts. Le retour est un
`docker compose up -d` sur les fichiers d'installation, avec les images épinglées sur ce qui
tournait. `deploy.sh` redevient alors utilisable (`COOLIFY_DEPLOY_FORCE=1` pour lever son
garde-fou, ou simplement une fois le conteneur `coolify` de nouveau debout).
