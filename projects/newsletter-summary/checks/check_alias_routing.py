#!/usr/bin/env python3
"""Routage à la réception : quel alias reçoit quel mail, et qui est admis.

Passe par le VRAI webhook (`POST /webhook/resend`) sur une base jetable. Le payload de base est
COPIÉ de la production (la newsletter Euractiv du 2026-09-05, cf. check_webhook_event_filter.py),
seuls `to`, `from` et `message_id` varient : une fixture plus régulière que le réel serait un check
aveugle au vert.

Ce qui doit tenir :
  - `newsletter@` (et toute adresse inconnue) → l'alias par défaut, comportement d'avant les alias ;
  - correspondance EXACTE : `summary+x@` ne retombe PAS sur `summary` (sinon la liste blanche de
    `summary` couvrirait un espace d'adresses illimité) — il tombe sur le défaut ;
  - `aaa+bbb@` est un alias à part entière ; le nom d'affichage `"Nom" <a@b>` ne gêne ni le routage
    ni la liste blanche ; la casse est ignorée ;
  - expéditeur hors liste, liste vide, alias désactivé → `rejected` avec la raison, SANS rapatrier le corps ;
  - un `From` vide n'est pas refusé à la réception (pas encore rapatrié) : le moteur fait foi.
"""
import asyncio
import copy
import os

import httpx

from _harness import add_email, fresh_db, get_email, make_alias  # noqa: F401  (chemin + doublures)
from app import aliases as al
from app.database import AsyncSessionLocal
from app.main import app
from app.models import Email
from sqlalchemy import select

# Copié des logs de production (2026-09-05) — voir check_webhook_event_filter.py.
REAL = {
    "created_at": "2026-09-05T06:00:03.000Z",
    "type": "email.received",
    "data": {
        "attachments": [], "bcc": [], "cc": [],
        "created_at": "2026-09-05T06:01:00.076Z",
        "email_id": "77257e8f-7fe2-4dd2-a0d9-0f2fb0a64662",
        "from": "no-reply@newsletter.euractiv.com",
        "message_id": "<20260905060003.6b8c170fa12e871b@newsletter.euractiv.com>",
        "received_for": ["newsletter@oozeenaru.resend.app", "jean.langlois.meurinne@gmail.com"],
        "subject": "It’s (not) the economy, dummkopf!",
        "to": ["newsletter@oozeenaru.resend.app"],
    },
}
TOKEN = os.environ.get("WEBHOOK_TOKEN", "")


def payload(n, *, to, frm="no-reply@newsletter.euractiv.com"):
    p = copy.deepcopy(REAL)
    d = p["data"]
    d["message_id"] = f"<routing-{n}@test>"
    d["email_id"] = ""            # pas de rapatriement réseau dans ce check
    d["to"] = to if isinstance(to, list) else [to]
    d["from"] = frm
    d["text"] = "corps"
    if frm is None:
        del d["from"]
    return p


async def post(client, n, **kw):
    r = await client.post(f"/webhook/resend?token={TOKEN}", json=payload(n, **kw))
    assert r.status_code == 200, r.text
    body = r.json()
    async with AsyncSessionLocal() as db:
        row = (await db.execute(select(Email).where(Email.message_id == f"<routing-{n}@test>"))).scalar_one_or_none()
    return body, row


async def main():
    default = await fresh_db()
    summary = await make_alias("summary", frequency="minute", allowed_senders="Jean@Exemple.fr")
    plus = await make_alias("aaa+bbb", frequency="morning", allowed_senders=["marie@exemple.fr"])
    closed = await make_alias("vide", frequency="minute")                                  # liste blanche vide
    off = await make_alias("eteint", frequency="minute", allowed_senders=["jean@exemple.fr"], enabled=False)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        # ── flux d'avant les alias : inchangé ──
        b, row = await post(c, 1, to="newsletter@oozeenaru.resend.app")
        assert b["status"] == "stored" and row.alias_id == default.id and row.status == "new", (b, row and row.alias_id)
        b, row = await post(c, 2, to="contact@oozeenaru.resend.app")
        assert row.alias_id == default.id, "adresse inconnue → doit atterrir sur l'alias par défaut (catch-all d'avant)"

        # ── alias à la demande ──
        b, row = await post(c, 3, to="summary@oozeenaru.resend.app", frm="jean@exemple.fr")
        assert row.alias_id == summary.id and row.status == "new", "summary@ + expéditeur autorisé → new"
        b, row = await post(c, 4, to="Summary <SUMMARY@oozeenaru.resend.app>", frm='"Jean Dupont" <JEAN@exemple.fr>')
        assert row.alias_id == summary.id and row.status == "new", "nom d'affichage + casse ne doivent gêner ni routage ni liste blanche"
        b, row = await post(c, 5, to="summary@oozeenaru.resend.app", frm="intrus@spam.example")
        assert b["status"] == "rejected" and row.status == "rejected" and "non autorisé" in row.last_error, (b, row.status)
        b, row = await post(c, 6, to="vide@oozeenaru.resend.app", frm="jean@exemple.fr")
        assert row.status == "rejected", "liste blanche vide = personne (défaut sûr)"
        b, row = await post(c, 7, to="eteint@oozeenaru.resend.app", frm="jean@exemple.fr")
        assert row.status == "rejected" and "désactivé" in row.last_error, "alias désactivé → rejet nommé"
        b, row = await post(c, 8, to="summary@oozeenaru.resend.app", frm=None)
        assert row.status == "new", "From vide : pas refusé à la réception, le moteur re-contrôle après rapatriement"

        # ── format aaa+bbb : alias à part entière, correspondance exacte ──
        b, row = await post(c, 9, to="aaa+bbb@oozeenaru.resend.app", frm="marie@exemple.fr")
        assert row.alias_id == plus.id and row.status == "new", "aaa+bbb@ doit router vers l'alias aaa+bbb"
        b, row = await post(c, 10, to="summary+x@oozeenaru.resend.app", frm="jean@exemple.fr")
        assert row.alias_id == default.id, "summary+x@ ne doit PAS retomber sur `summary` (correspondance exacte)"
        b, row = await post(c, 11, to=["autre@x.fr", "summary@oozeenaru.resend.app"], frm="jean@exemple.fr")
        assert row.alias_id == summary.id, "plusieurs destinataires : le premier qui correspond à un alias"

    # ── validation des noms et des listes (aucune saisie silencieusement fausse) ──
    for ok in ("summary", "aaa+bbb", "a.b", "a_b-c", "AbC"):
        al.validate_local_part(ok)
    for bad in ("", ".a", "a.", "a..b", "a b", "a@b", "é", "a" * 65, "a,b"):
        try:
            al.validate_local_part(bad)
        except ValueError:
            continue
        raise AssertionError(f"nom d'alias {bad!r} aurait dû être refusé")
    try:
        al.parse_allowed_senders("jean@exemple.fr\nfaute-de-frappe")
    except ValueError:
        pass
    else:
        raise AssertionError("une entrée qui n'est pas une adresse doit être REFUSÉE à la saisie, pas ignorée")
    assert al.parse_allowed_senders("A@x.fr, b@y.fr;\n a@X.fr") == ["a@x.fr", "b@y.fr"], "normalisation + dédoublonnage"
    async with AsyncSessionLocal() as db:
        for args, msg in (({"local_part": "summary"}, "doublon"), ({"local_part": "x", "frequency": "hebdo"}, "fréquence")):
            try:
                await al.create_alias(db, **args)
            except ValueError:
                continue
            raise AssertionError(f"création invalide acceptée : {msg}")
    print("OK — routage, admission, correspondance exacte, validation : 11 mails via le webhook réel + validations")


asyncio.run(main())
