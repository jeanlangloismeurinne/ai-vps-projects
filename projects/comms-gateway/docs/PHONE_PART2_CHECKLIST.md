# 2ᵉ partie — Checklist téléphone (SMS / WhatsApp / Signal)

Le connecteur email (Resend) et le connecteur Slack sont fonctionnels dès la 1re étape.
Les canaux **SMS**, **WhatsApp** et **Signal** restent en **mock** tant que le matériel
n'est pas en place. Voici **ce que tu dois réaliser** pour débloquer la partie 2 — aucun
code côté gateway ne sera nécessaire au-delà du câblage des connecteurs (phases 3-5 du
spec).

> Principe du spec : le numéro WhatsApp est **sacrifiable** — jamais ton numéro principal.

## Matériel

- [ ] Un **vieux smartphone Android** qui hébergera la eSIM/SIM Free (dédié, jamais ton
      téléphone principal).
- [ ] Un **numéro Free** dédié (carte SIM **ou eSIM**), inséré dans ce téléphone.

## Étapes 🔧 utilisateur

### 1. Téléphone — réseau Tailscale
- [ ] Installer l'app **Tailscale** sur le téléphone, puis rejoindre le **même tailnet**
      que le VPS avec la clé d'authentification (Phase 0 : créer une clé Tailscale
      réutilisable dans la console Tailscale).
- [ ] Noter l'IP Tailscale du téléphone (elle servira au gateway pour le joindre).
- [ ] ⚠️ **Heartbeat** : si l'IP Tailscale du téléphone disparaît, une alerte Slack
      `#comms-gateway` doit prévenir (à brancher côté opérateur).

### 2. SMS — app SMSGate
- [ ] Installer **SMSGate** (ou équivalent : SMS-Fowarder / `sms_forwarder`) sur le
      téléphone, qui expose une API REST locale pour envoyer/lire les SMS.
- [ ] Prévoir que `comms-gateway` appelle le téléphone **via son IP Tailscale** (jamais
      via IP publique).
- [ ] Configurer la réception : SMSGate POSTe les SMS entrants vers
      `https://comms.jlmvpscode.duckdns.org/webhooks/sms`.

### 3. WhatsApp — conteneur Baileys
- [ ] (Le gateway étant en Node, le connecteur Baileys vit dans le gateway.)
- [ ] Prévoir la session Baileys dans le volume `comms_data` (`/data/whatsapp`).
- [ ] **Liage** : au premier lancement, scanner le QR WhatsApp avec le téléphone (ou code
      de liaison) — le numéro sacrifiable est lié au compte WhatsApp.

### 4. Signal — signal-cli
- [ ] Enregistrer `signal-cli` dans son conteneur avec le numéro Free dédié.
- [ ] Saisir l'OTP reçu par SMS lors de l'enregistrement.
- [ ] La session vit dans le volume (`/data/signal`).

## Variables déjà prévues dans le gateway

```
SMSGATE_BASE_URL=<ip_tailscale_du_telephone>   # SMS
WHATSAAP_SESSION_DIR=/data/whatsapp            # WhatsApp (Baileys)
SIGNAL_SESSION_DIR=/data/signal                # Signal
```

## Une fois le matériel prêt

1. Me dire : « **le téléphone est prêt (SMS/WhatsApp/Signal), câble les connecteurs réels** ».
2. Je remplace les connecteurs mock par les vrais, derrière la **même interface**
   (`send`/`receive`) — aucun changement côté clients ni côté permissions.
3. Déclarer les policies des clients (canaux + quotas + numéros autorisés).

## Critère d'acceptation Partie 2

- Un SMS, un WhatsApp et un Signal réellement envoyés/requalifiés reçus, journalisés
  avec attribution au client.
- Un destinataire hors whitelist est refusé (`rejected_policy`).
- L'arrêt du téléphone déclenche une alerte Slack (heartbeat Tailscale).
