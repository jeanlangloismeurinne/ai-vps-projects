---
id: reprise-newsletter-summary
status: prompt-de-reprise
created: 2026-09-01
project: newsletter-summary
role: Prompt à coller pour reprendre le chantier du digest matinal de newsletters. État : HTTP —  le résumé de chaque newsletter est désormais généré en **HTML (Option B)**, le gateway envoie `text`+`html` à Resend.
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
- **Format du digest (depuis 2026-09-01)** : DeepSeek produit un **bloc HTML autonome**
  par newsletter (`SUMMARIZE_HTML_PROMPT`, styles inline) ; `digest.py` assemble ces blocs
  dans une enveloppe HTML minimale et envoie `body`(texte fallback) + `html` au gateway.
  C'est l'**Option B** (le LLM pilote la mise en page des cartes).

## Déploiement

Stack **standalone docker compose** (pas une app Coolify), réseau `coolify`, routée par le
coolify-proxy (Traefik, `mails.jlmvpscode.duckdns.org`) :

```bash
cd projects/newsletter-summary
docker compose up -d --build
```

## Blocages / jalons

- **Domaine d'envoi Resend non vérifié** : le gateway est en `RESEND_DEV_MODE=1` → tous les
  envois forcés vers `RESEND_DEV_TO`. Sortir du mode dev une fois un domaine d'envoi vérifié.
- **Roadmap (Option A)** : si le rendu HTML produit par le LLM s'avère trop incohérent/cassé dans
  les clients mail, basculer sur une **coquille HTML côte code** (CSS inline, cartes uniformes,
  contenu échappé) avec DeepSeek ne produisant plus que le contenu. Voir backlog
  `project_newsletter_roadmap_optionA`.
