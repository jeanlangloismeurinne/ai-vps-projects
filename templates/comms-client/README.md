# comms-client — SDK d'appel au `comms-gateway`

Client léger en Python pour appeler le gateway central de communication externe
(`projects/comms-gateway`). **Le projet consommateur ne détient jamais les secrets des
providers** (Resend, Slack, …) : ils vivent uniquement dans les secrets du gateway.

## Pourquoi ce SDK

Centraliser dans `comms-gateway` (spec `comms-gateway.md`) :
- un seul composant détient les clés des providers (email/Resend, Slack, puis SMS/WhatsApp/Signal) ;
- chaque projet = un *client* du gateway, avec ses canaux autorisés, ses quotas et sa
  liste de destinataires (refus par défaut) ;
- chaque message est journalisé (audit).

Un projet n'a besoin que de **deux variables d'environnement** pour basculer sur le gateway.

## Installation

Embarquer ce module **dans le projet** (copie, comme `templates/knowledge-base/`) :

```bash
cp templates/comms-client/comms_client.py projects/<mon-projet>/app/comms_client.py
```

`httpx` requis (déjà présent dans la plupart des projets FastAPI).

## Configuration (2 variables par projet)

| Variable | Valeur (interne) |
|---|---|
| `GATEWAY_URL` | `http://comms-gateway:8000` (réseau coolify) ou URL publique en dev |
| `GATEWAY_TOKEN` | token scoped du client, déposé en secret Coolify du projet |

> Sur le réseau Docker interne, utiliser le nom de service `comms-gateway` :
> `GATEWAY_URL=http://comms-gateway:8000`.

## Utilisation

```python
import comms_client as comms

# asynchrone (FastAPI)
await comms.get_client().send_email(to="jean@mailbox.org", subject="Titre", body="Corps")
await comms.get_client().send_slack(to="#journal", body="Bonjour")
await comms.get_client().send_sms(number="+33600000000", body="Alerte")

# synchrone (scripts)
comms.send_email_sync("jean@mailbox.org", "Titre", "Corps")
```

Lève `CommsError` si l'envoi est rejeté par une policy ou le rate-limit.

## Onboarding d'un NOUVEAU projet (côté gateway)

1. **Enregistrer le client** (via l'API admin, `ADMIN_TOKEN`) :
   ```bash
   curl -X POST $GATEWAY_URL/v1/admin/clients \
     -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" \
     -d '{"client_id":"<mon-projet>","policies":[
           {"channel":"email","action":"send","default_from":"<from>","rate_limit_per_day":50}
         ]}'
   ```
   → retourne un token **une seule fois** : le copier en secret Coolify du projet (`GATEWAY_TOKEN`).
2. **Autoriser le destinataire** : la policy du client lève `rejected_policy` si le
   destinataire n'est pas dans `recipients` (ou motif `@domaine`).
3. Tester : envoi via le SDK + limite de débit (dépasser `rate_limit_per_day` → `rejected_rate_limit`).
4. Coupe-circuit : `PATCH /v1/admin/clients/<id>/status {"enabled":false}` → refus immédiat.

## Vérifier l'audit

```bash
curl -H "Authorization: Bearer $GATEWAY_TOKEN" $GATEWAY_URL/v1/messages
```
Historique strictement limité aux messages de **ce client**.
