---
id: reprise-newsletter-summary
status: prompt-de-reprise
created: 2026-09-02
project: newsletter-summary
role: Prompt à coller pour reprendre le chantier du digest matinal de newsletters. État : HTML (Option B) + garanties français/anti-pub côté code + séparation des cartes garantie + **KB des résumés (enveloppe KNOWLEDGE §3)** + **éditeur de prompt versionné dans le Hub**.
---

# 🚦 RÈGLE (s'applique à chaque session)

> **En fin de conversation, après avoir implémenté une nouvelle version / un nouveau
> sprint, ACTUALISER ce fichier** : état atteint, prochain jalon, blocages, commandes de
> reprise. La session suivante démarre en relisant ce fichier — ne jamais repartir d'un
> état périmé.

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

Stack **standalone docker compose** (pas une app Coolify), réseau `coolify`, routée par le
coolify-proxy (Traefik, `mails.jlmvpscode.duckdns.org`) :

```bash
cd projects/newsletter-summary
docker compose up -d --build
```

Le Hub (app Coolify) doit avoir en env `NEWSLETTER_URL` et `NEWSLETTER_API_TOKEN` (même valeur
que `HUB_API_TOKEN` du service), puis **rebuild Coolify** (pas restart).

## Blocages / jalons

- **Domaine d'envoi Resend non vérifié** : le gateway est en `RESEND_DEV_MODE=1` → tous les
  envois forcés vers `RESEND_DEV_TO`. Sortir du mode dev une fois un domaine d'envoi vérifié.
- **Roadmap (Option A)** : si le rendu HTML produit par le LLM s'avère trop incohérent/cassé dans
  les clients mail, basculer sur une **coquille HTML côte code** (CSS inline, cartes uniformes,
  contenu échappé) avec DeepSeek ne produisant plus que le contenu. Voir backlog
  `project_newsletter_roadmap_optionA`.
- **Fédération KB** : `kb_documents` est prête (enveloppe §3) ; brancher le connecteur
  `mailbox` → `db_knowledge_federation` le jour où la recherche multi-source est demandée.
