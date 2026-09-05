#!/usr/bin/env python3
"""Garde le tri entrant/sortant du webhook Resend (`app/resend.is_inbound_event`).

Pourquoi ce check existe — mode de panne réel, digest du 2026-09-05 : une seule URL de webhook
reçoit TOUS les événements Resend. Les `email.sent` / `email.delivered` / `email.opened` du
digest qu'on venait d'envoyer étaient stockés comme des newsletters à résumer. Le digest se
mangeait lui-même : une ligne fantôme par jour, corps vide, ressortie le lendemain en carte vide
dont l'en-tête affichait le sujet de la veille. L'utilisateur a vu « 2 newsletter(s) » en objet,
« 8 newsletter(s) » en tête de la première carte, et un seul vrai bloc.

⚠️ Les payloads ci-dessous sont **copiés des logs de production du 2026-09-05**, pas inventés :
une fixture plus propre que le réel ferait un check aveugle au vert.

Lancer :  python3 projects/newsletter-summary/checks/check_webhook_event_filter.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.resend import is_inbound_event, parse_inbound  # noqa: E402

# ── Payloads réels, journalisés le 2026-09-05 ────────────────────────────────────────────────

DIGEST_DELIVERED = {
    "created_at": "2026-09-05T06:00:28.177Z",
    "type": "email.delivered",
    "data": {
        "created_at": "2026-09-05T06:00:27.136Z",
        "email_id": "d113f5a9-fd39-4281-818d-45327f02070a",
        "from": "onboarding@resend.dev",
        "message_id": "<010001a070276dd9-f934ae4e-c8e6-4d19-99b1-4642635e2c9b-000000@email.amazonses.com>",
        "subject": "📬 Résumé hebdo-news — 2 newsletter(s) — Saturday 05 September 2026",
        "to": ["jean.langlois.meurinne@gmail.com"],
    },
}

DIGEST_SENT = {**DIGEST_DELIVERED, "type": "email.sent"}
DIGEST_OPENED = {**DIGEST_DELIVERED, "type": "email.opened"}

# La vraie newsletter reçue le même matin (row 29, backfill OK, 25262 caractères de corps).
NEWSLETTER_RECUE = {
    "created_at": "2026-09-05T06:00:03.000Z",
    "type": "email.received",
    "data": {
        "attachments": [],
        "bcc": [],
        "cc": [],
        "created_at": "2026-09-05T06:01:00.076Z",
        "email_id": "77257e8f-7fe2-4dd2-a0d9-0f2fb0a64662",
        "from": "no-reply@newsletter.euractiv.com",
        "message_id": "<20260905060003.6b8c170fa12e871b@newsletter.euractiv.com>",
        "received_for": ["newsletter@oozeenaru.resend.app", "jean.langlois.meurinne@gmail.com"],
        "subject": "It’s (not) the economy, dummkopf!",
        "to": ["newsletter@oozeenaru.resend.app"],
    },
}

# Forme « plano » sans enveloppe : tolérée par parse_inbound, elle doit rester acceptée.
PLANO_SANS_TYPE = {
    "from": "no-reply@newsletter.euractiv.com",
    "subject": "Duracell Meloni",
    "message_id": "<20260903060002.aaaa@newsletter.euractiv.com>",
    "text": "corps du mail",
}

# Type inédit : Resend en ajoute (bounced, clicked, complained, delivery_delayed…). La liste
# blanche doit les refuser par défaut — c'est tout l'intérêt de ne pas faire de liste noire.
TYPE_INEDIT = {**DIGEST_DELIVERED, "type": "email.delivery_delayed"}

REJETES = [
    ("email.delivered du digest", DIGEST_DELIVERED),
    ("email.sent du digest", DIGEST_SENT),
    ("email.opened du digest", DIGEST_OPENED),
    ("type inédit (liste blanche)", TYPE_INEDIT),
]

ACCEPTES = [
    ("email.received (vraie newsletter)", NEWSLETTER_RECUE),
    ("payload plano sans type", PLANO_SANS_TYPE),
]


def main() -> int:
    anomalies = []

    for label, payload in REJETES:
        if is_inbound_event(payload):
            anomalies.append(f"INGÉRÉ à tort : {label} (type={payload.get('type')!r})")

    for label, payload in ACCEPTES:
        if not is_inbound_event(payload):
            anomalies.append(f"REJETÉ à tort : {label} (type={payload.get('type')!r})")

    # Le tri ne sert à rien si le mail accepté n'est pas exploitable ensuite : on vérifie que
    # la vraie newsletter se parse toujours avec de quoi la dédupliquer et rapatrier son corps.
    fields = parse_inbound(NEWSLETTER_RECUE)
    if not fields.get("message_id"):
        anomalies.append("newsletter acceptée mais sans message_id (dédup impossible)")
    if not fields.get("email_id"):
        anomalies.append("newsletter acceptée mais sans email_id (backfill du corps impossible)")

    if anomalies:
        for a in anomalies:
            print(f"ANOMALIE : {a}")
        print(f"\nÉCHEC — {len(anomalies)} anomalie(s).")
        return 1

    print(f"{len(REJETES)} événement(s) sortant(s) rejeté(s), "
          f"{len(ACCEPTES)} entrant(s) accepté(s), parse de l'entrant OK.")
    print("OK : le digest ne peut plus ingérer ses propres notifications d'envoi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
