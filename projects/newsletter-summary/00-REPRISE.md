---
id: reprise-newsletter-summary
status: prompt-de-reprise
created: 2026-09-02
updated: 2026-09-03
project: newsletter-summary
role: >
  Prompt à coller pour reprendre le chantier du digest matinal de newsletters. État : HTML (Option
  B) + garanties français/anti-pub côté code + séparation des cartes garantie + **KB des résumés
  (enveloppe KNOWLEDGE §3)** + **éditeur de prompt versionné dans le Hub**.
---

# 🚦 RÈGLE (s'applique à chaque session)

> **En fin de conversation, après avoir implémenté une nouvelle version / un nouveau
> sprint, ACTUALISER ce fichier** : état atteint, prochain jalon, blocages, commandes de
> reprise. La session suivante démarre en relisant ce fichier — ne jamais repartir d'un
> état périmé.

> ## ⚡ MàJ 2026-09-04 — Cartes déterministes + anti-troncature + plein écran mobile
>
> **Cause racine trouvée sur le digest du 04/09** (7 newsletters) : le modèle dépassait « 600 mots »
> (~1200) et la sortie était **coupée à `max_tokens=2500`** → 5 blocs sur 7 tronqués (ex. Euractiv
> « Le Rapporteur » coupé net) ET `<div>` non fermé → **la carte suivante s'imbriquait dans la
> précédente** (Geopolitechs id21 dans Euractiv id20). Un seul bug expliquait les trois symptômes.
>
> **Corrigé et déployé** (`docker compose up -d --build`, health OK, 1 seul conteneur) :
> - `digest.py` : ouverture/fermeture de carte **+ en-tête (expéditeur/sujet) rendus DÉTERMINISTES
>   côté code**. Le modèle ne produit plus QUE le corps. `_sanitize_inner` déballe un `<div>`
>   enveloppant éventuel, coupe une balise finale tronquée et **équilibre les `<div>`** →
>   imbrication **impossible par construction** (vérifié : les 5 blocs cassés du 04/09 re-wrappés
>   sont tous équilibrés ; doc global 45/45).
> - **Marges latérales de l'enveloppe et du bloc blanc = 0** (plein écran mobile), padding interne
>   des cartes conservé (texte non collé au bord).
> - `summarizer.py` : `max_tokens` 2500→**4000** (plus de troncature) ; invariants « corps seul » et
>   « 600 mots » **doublés dans le message système** (garantis même si le prompt est réédité).
> - `deepinfra_client.py` : WARNING si `finish_reason=length`.
> - **Prompt actif V4** (id=5, `prompt_versions`, append-only) : « corps seul, 600 mots strict ».
>   Rollback possible via le dropdown du Hub. `config.py` (défaut) aligné.
> - **Vérif live contre le vrai modèle** (email id27, 73k car. en entrée, sans envoi ni changement
>   de statut) : sortie = **520 mots**, 0 `<div>` du modèle, carte code équilibrée 3/3. ✔
>
> Reste à confirmer : le rendu réel du **prochain digest de 8h** (surtout la séparation sur un lot
> de 5–8 mails et le respect des 600 mots sur des mails variés). Surveiller les WARNING
> `finish_reason=length` (ne devrait plus apparaître).

> ## ⚡ MàJ 2026-09-03 — Coolify est arrêté : le Hub aussi est en `docker compose`
>
> **Rien n'a changé dans ce projet** : il était déjà une stack `docker compose` standalone, c'est
> l'une des raisons pour lesquelles il n'a rien coûté à la migration. Ce qui change est **en face** :
> le **Hub n'est plus une app Coolify**. La consigne « puis rebuild Coolify (pas restart) » qui
> figurait plus bas est donc **périmée** — corrigée dans la section Déploiement.
>
> Conséquences concrètes pour ce chantier :
> - `NEWSLETTER_URL` / `NEWSLETTER_API_TOKEN` se posent désormais dans le **`.env` du Hub**
>   (`projects/hub/.env`, chmod 600, hors git), plus dans l'UI Coolify.
> - Le réseau `coolify` et le proxy `coolify-proxy` (Traefik) **ont survécu** à la migration et
>   gardent leur nom : le routage `mails.jlmvpscode.duckdns.org` et l'appel Hub → service par le
>   réseau interne sont **inchangés**. Ne pas renommer le réseau pour « faire propre » : tous les
>   labels Traefik du VPS y font référence.
> - Le déploiement du Hub passe maintenant par `infrastructure/compose-deploy.sh hub` (voir
>   `DEPLOY.md`) ; `infrastructure/deploy.sh` est neutralisé.
>
> Ce projet reste **hors** de `compose-deploy.sh` (comme `kb-viewer` et `provenance-viz`) : son
> déploiement est le `docker compose up -d --build` ci-dessous, à la main.

# Prompt de reprise

Reprends le chantier `newsletter-summary` (digest matinal de newsletters).

## Contexte (déjà acté)

- **Flux** : mail transféré → Resend inbound (*@oozeenaru.resend.app) → webhook
  `POST /webhook/resend?token=` → stockage `db_newsletter_summary` (dédup `message_id`, `status=new`).
  Le webhook Resend ne livre que des métadonnées → le corps est **ratrapié** via
  `GET /v1/inbound/email/:id` du gateway (`_backfill_body`).
- **Digest** : job 8h Europe/Paris (APScheduler) résume les mails `new` → envoie à
  `RECIPIENT_EMAIL` via **comms-gateway** (le projet ne détient plus de clé Resend).
- **Un seul prompt actif** : `SUMMARIZE_HTML_PROMPT` (via `summarize_html`, seul appelé).
  `SUMMARIZATION_PROMPT` / `summarize()` sont du **code mort** (legacy, jamais appelé).
- **Vérifs actées (2026-09-02)** :
  1. Un appel DeepInfra PAR mail → bloc HTML autonome par mail ; **séparation entre cartes
     garantie côté code** (`_card_html` enveloppe chaque bloc dans un conteneur
     `margin/border-bottom`), corrige la mise en forme étrange du dernier résumé.
  2. **Français** garanti côté système (message system de `summarize_html`).
  3. **Publicités éliminées** : exigence dans le défaut du prompt + message système.
- **KB des résumés** : nouvelle table `kb_documents` (enveloppe KNOWLEDGE_ARCHITECTURE §3,
  pivot Markdown, `visibility=private`), remplie pendant le digest. Export JSON : `GET /api/kb`.
- **Éditeur de prompt versionné** : table `prompt_versions` (append-only, une active). Le digest
  relit le prompt actif **à chaque exécution** → édition Hub sans redémarrage. Endpoints
  `GET /api/prompt`, `POST /api/prompt/versions`, `POST /api/prompt/activate`. **Seeder v1** au
  démarrage (défaut d'env) si l'éditeur n'a rien enregistré.
- **Côté Hub** (app `homepage`) : router `/newsletter` (page KB + éditeur avec dropdown de
  versions), appelant le service via le réseau `coolify` (`NEWSLETTER_URL`,
  `NEWSLETTER_API_TOKEN`). Carte « Newsletter » ajoutée à l'accueil.

## Sécurité

Les `/api/*` sont **publiquement atteignables** via `mails.jlmvpscode.duckdns.org/api/*` →
protégés par le header `X-Hub-Token` = `HUB_API_TOKEN` (service) = `NEWSLETTER_API_TOKEN` (Hub).
Ne jamais laisser ces valeurs vides en prod.

## Déploiement

Stack **standalone docker compose**, réseau `coolify`, routée par le coolify-proxy
(Traefik, `mails.jlmvpscode.duckdns.org`) :

```bash
cd projects/newsletter-summary
docker compose up -d --build
```

Depuis le 2026-09-03, **tout le VPS est en `docker compose`** : ce projet n'est plus l'exception,
mais il reste **hors** de `infrastructure/compose-deploy.sh` (déploiement à la main, ci-dessus).

Le Hub doit avoir `NEWSLETTER_URL` et `NEWSLETTER_API_TOKEN` (même valeur que le `HUB_API_TOKEN` du
service) dans **`projects/hub/.env`** — plus dans l'UI Coolify — puis être **reconstruit** :

```bash
infrastructure/compose-deploy.sh hub -e NEWSLETTER_API_TOKEN=<valeur> --rebuild-only
```

**Rebuild, jamais restart** : le Hub est un Next.js, les variables lues au build y sont figées dans
le bundle. Après coup, `docker ps | grep hub` doit montrer **un seul** conteneur.

## Blocages / jalons

- **Domaine d'envoi Resend non vérifié** : le gateway est en `RESEND_DEV_MODE=1` → tous les
  envois forcés vers `RESEND_DEV_TO`. Sortir du mode dev une fois un domaine d'envoi vérifié.
- **Roadmap (Option A)** : si le rendu HTML produit par le LLM s'avère trop incohérent/cassé dans
  les clients mail, basculer sur une **coquille HTML côte code** (CSS inline, cartes uniformes,
  contenu échappé) avec DeepSeek ne produisant plus que le contenu. Voir backlog
  `project_newsletter_roadmap_optionA`.
- **Fédération KB** : `kb_documents` est prête (enveloppe §3) ; brancher le connecteur
  `mailbox` → `db_knowledge_federation` le jour où la recherche multi-source est demandée.
