# newsletter-summary

> **Alias (2026-09-25)** — la newsletter n'est plus un cas à part : c'est l'**alias par défaut** d'un moteur
> unique. On peut aussi créer des alias (`summary@…`, `aaa+bbb@…`) : un mail envoyé à l'alias est résumé et le
> résumé **revient à l'expéditeur**. Voir § Alias.

Reçoit les newsletters transférées vers `*@oozeenaru.resend.app` (inbound Resend), les stocke
dans PostgreSQL, et envoie chaque matin à **8h (Europe/Paris)** un digest récapitulant toutes
les mails reçues depuis la veille, à `jean.langlois-meurinne@mailbox.org`.

Le résumé de chaque mail est généré par DeepInfra (DeepSeek-V4), **un appel par mail** avec un
prompt unique et **éditable** depuis le Hub (voir ci-dessous). Le **système** (côté code, appliqué
à chaque appel) garantit : **rédaction en français** et **exclusion des publicités** — quelles que
soient les éditions du prompt.

Le digest est envoyé en **email HTML lisible** : chaque newsletter est rendue par DeepSeek sous
forme d'un **bloc HTML autonome** (styles inline, cf. `SUMMARIZE_HTML_PROMPT`), assemblé dans
une enveloppe HTML minimale côté code. Chaque bloc est enveloppé dans un **conteneur contrôle par
le code** qui garantit une séparation lisible entre les mails (corrige la mise en forme où deux
cartes pouvaient se coller). Un corps **texte brut** reste envoyé en parallèle comme fallback. Le
gateway accepte un champ `html` en plus du `text`.

## KB + éditeur de prompt (via le Hub)

Deux nouveautés intégrées à l'app « homepage » (Hub) :

- **Base de connaissance (résumés)** : chaque nouveau résumé est persisté dans la table
  `kb_documents`, au format **enveloppe KNOWLEDGE_ARCHITECTURE.md §3** (pivot Markdown +
  métadonnées), `visibility=private`. Exportable en JSON via `GET /api/kb` — prêt pour la future
  fédération pgvector. Affichage dans le Hub : `/newsletter`.
- **Éditeur de prompt versionné** : le prompt actif (`SUMMARIZE_HTML_PROMPT`) est éditable dans le
  Hub (`/newsletter/prompt`), **chaque enregistrement crée une nouvelle version** (append-only) et
  un **menu déroulant** permet de revenir à une version antérieure. Le digest relit le prompt actif
  **à chaque exécution** → une édition s'applique sans redémarrage. Endpoints : `GET /api/prompt`,
  `POST /api/prompt/versions`, `POST /api/prompt/activate`.

Sécurité : les endpoints `/api/*` sont protégés par le header `X-Hub-Token` (= `HUB_API_TOKEN`,
identique à `NEWSLETTER_API_TOKEN` du Hub), car ils sont aussi atteignables publiquement via le
sous-domaine `mails.*`.

## Flux

```
Mail transféré → Resend inbound (*@oozeenaru.resend.app)
  └─ webhook POST https://mails.jlmvpscode.duckdns.org/webhook/resend?token=…
       └─ app:8000 → stocke dans db_newsletter_summary (dédup par message_id, status=new)
Webhook → alias (partie locale exacte, sinon alias par défaut) → contrôle de l'expéditeur → status=new
Trois jobs APScheduler (Europe/Paris) : matin 8h · soir 18h · chaque minute — chacun traite les alias de SA cadence
  └─ réserve les mails new → résume (DeepInfra, prompt de l'alias) → envoie via comms-gateway
       └─ summarized | failed (motif nommé) | rejected ; KB écrite avec le nom de l'alias
```

## Alias — résumé à la demande

Un alias = une adresse de réception + sa politique, configurés dans le Hub (`/newsletter/aliases`).

| Réglage | Effet |
|---|---|
| Adresse (`local_part`) | Correspondance **exacte** sur la partie locale (`summary`, `aaa+bbb`). `summary+x@` ne retombe **pas** sur `summary`. Immuable après création. Toute adresse inconnue du domaine → alias par défaut (catch-all d'avant). |
| Fréquence | `minute` : vérification chaque minute, **un e-mail par mail reçu, jamais de lot** · `morning` (8h) / `evening` (18h) : un **lot par destinataire**. |
| Expéditeurs autorisés | Liste blanche. Vide = personne (défaut sûr). « Tous » = case explicite. Refusé → ligne `rejected` (raison stockée), **ni LLM ni réponse**. |
| Prompt | Versionné **par alias** (copie du prompt newsletter à la création). |
| Destinataire | Alias à la demande : l'expéditeur. Newsletter : `RECIPIENT_EMAIL` (synchronisé à chaque démarrage). |

- **Mode développement** : rien à faire ici. Le gateway (`RESEND_DEV_MODE=1`) redirige tout envoi vers l'adresse du compte
  Resend ; le jour où il est retiré, les réponses partent réellement aux expéditeurs sans changer une ligne.
- **Mail réduit à un lien** : la page est récupérée et résumée. Garde SSRF (`app/urlfetch.py`) : http/https, ports 80/443, hôte
  résolu puis refusé si une IP n'est pas publique, redirections revalidées une à une, 2 Mo / 30 s / 30 000 caractères max.
  « Une phrase + un lien » n'est **pas** un lien seul. Risque résiduel : ré-résolution DNS entre validation et connexion.
- **KB** : chaque résumé est écrit avec le tag `alias:<nom>` (et `source_url` pour un mail-lien).
- **Un mail n'est jamais bloqué ni perdu sans trace** : statuts `new → processing → summarized | failed | rejected`, `last_error`
  nommée, carte d'erreur envoyée au destinataire (HTML **et** texte). Cadence `minute` : 3 tentatives puis échec nommé.
  Réservation atomique (`UPDATE … RETURNING`), `processing` orphelins récupérés après 15 min, run borné à 10 min.
- **Plafond** : `ALIAS_MAX_PER_DAY` (40) mails/jour sur les alias à liste blanche. Le gateway plafonne à **60 e-mails/jour pour tout
  ce client** : sans ce garde-fou un afflux affamerait le digest newsletter. Relever la policy gateway si besoin.
- Non inclus : repli « `+tag` → alias de base » ; `system` du LLM encore rédigé « newsletter, 600 mots, sans pub » (à rendre par alias
  quand le prompt divergera).

## Vérification

`checks/run_all.sh` (8 checks, base jetable `db_ns_scratch`, aucune requête réseau) → `BILAN checks : N/N verts`.
`python3 checks/mutations.py` (hôte) mute chaque garde et exige que **le bon check rougisse pour la bonne raison** → `BILAN mutations`.
Le **test d'or** (`check_golden_newsletter.py`) exige que l'e-mail de la newsletter soit identique octet pour octet à celui de l'ancien
code (fixtures gelées `checks/golden/`, capturées avant le chantier — ne jamais relancer `golden_capture_legacy.py`).

## Déploiement

Stack **standalone docker compose** (pas une app Coolify), sur le réseau `coolify` — routée par
le coolify-proxy (TLS Let's Encrypt), comme `kb-viewer`.

```bash
cd projects/newsletter-summary
# 1. Créer la base (une fois) :
#    docker exec shared-postgres psql -U admin -c "CREATE USER newsletter WITH PASSWORD '<pw>';"
#    docker exec shared-postgres psql -U admin -c "CREATE DATABASE db_newsletter_summary OWNER newsletter;"
# 2. Créer .env (hors git) avec les vraies valeurs — cf. .env.example
# 3. Déployer / redéployer :
docker compose up -d --build
```
Puis configurer le webhook inbound Resend : mails vers `*@oozeenaru.resend.app`
→ `https://mails.jlmvpscode.duckdns.org/webhook/resend?token=$WEBHOOK_TOKEN`.

## Variables d'environnement (.env, non commité)

| Variable | Rôle |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://newsletter:<pw>@shared-postgres:5432/db_newsletter_summary` |
| `GATEWAY_URL` | `http://comms-gateway:8000` (réseau interne) — envoi du digest ET rapatriement du corps inbound |
| `GATEWAY_TOKEN` | Jeton scoped du client auprès du gateway. **Le projet ne détient aucune clé Resend** : les secrets des providers restent au gateway |
| `RECIPIENT_EMAIL` | Destinataire du digest newsletter — recopié sur l'alias par défaut à chaque démarrage |
| `DEEPINFRA_API_KEY` | Clé DeepInfra pour les résumés |
| `DEEPINFRA_MODEL` | `deepseek-ai/DeepSeek-V4-Flash` |
| `SUMMARIZE_HTML_PROMPT` | Défaut du prompt de résumé (HTML) — la **version active** est éditée via le Hub |
| `HUB_API_TOKEN` | Jeton partagé avec le Hub (header `X-Hub-Token` sur `/api/*`) |
| `SUMMARY_HOUR` / `SUMMARY_MINUTE` | Créneau « matin » (défaut 8h00) |
| `WEBHOOK_TOKEN` | Secret requis en `?token=` sur `/webhook/resend` |
| `EVENING_HOUR` / `EVENING_MINUTE` | Créneau du soir (défaut 18h00) |
| `INBOUND_DOMAIN` | Domaine affiché dans le Hub (défaut `oozeenaru.resend.app`) ; le routage ignore le domaine |
| `ALIAS_MAX_PER_DAY` | Plafond de mails/jour sur les alias à liste blanche (défaut 40) |
| `ALIAS_MAX_ATTEMPTS` | Tentatives par mail en cadence `minute` (défaut 3) |

## Endpoints

- `GET /health` — liveness
- `POST /webhook/resend?token=…` — réception inbound Resend
- `POST /webhook/resend/test` — test de routage (no auth, liste les clés du payload)
- `GET /api/prompt` — version active + historique du prompt (header `X-Hub-Token`)
- `POST /api/prompt/versions` — enregistrer une nouvelle version (header `X-Hub-Token`)
- `POST /api/prompt/activate` — revenir à une version antérieure (header `X-Hub-Token`)
- `GET /api/kb` — enveloppes KB §3 des résumés (header `X-Hub-Token`)
- `GET /api/prompt?alias_id=` · `POST /api/prompt/versions` · `POST /api/prompt/activate` — `alias_id` optionnel (absent = alias par défaut)
- `GET /api/aliases` — alias + décompte des mails par statut · `POST /api/aliases` · `PUT /api/aliases/{id}`
- `GET /api/aliases/{id}/mails?limit=` — derniers mails avec statut et `last_error`
