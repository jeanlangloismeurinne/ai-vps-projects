"""Harnais commun des checks du moteur d'alias (base jetable + doublures du gateway et du LLM).

Ne fait AUCUN appel réseau : le gateway et DeepInfra sont remplacés, la date est gelée. Ce qui est
réel : la base PostgreSQL (jetable, cf. run.sh), le code de routage, de réservation et de rendu.
"""
import asyncio
import sys
from datetime import datetime
from pathlib import Path

import logging

logging.disable(logging.INFO)   # les logs INFO d'httpx impriment l'URL du webhook, jeton compris
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import alias_digest, comms_client, digest, summarizer  # noqa: E402
from app import aliases as al  # noqa: E402
from app.database import AsyncSessionLocal, init_db  # noqa: E402
from app.models import Email  # noqa: E402
from app.prompts import seed_default  # noqa: E402

GOLDEN = Path(__file__).resolve().parent / "golden"
ERROR_MARKER = "[[echec-resume]]"


class FakeGateway:
    def __init__(self):
        self.sent: list[dict] = []
        self.fail = False
        self.delay = 0.0   # élargit la fenêtre de chevauchement des runs (test de réservation)

    async def send_email(self, to, subject, body, html=None, **kw):
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail:
            raise RuntimeError("gateway simulé indisponible")
        self.sent.append({"to": to, "subject": subject, "body": body, "html": html})
        return {"status": "sent"}


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 25, 8, 0, 0)


class Doubles:
    """Installe les doublures. `seen_plain[id]` = texte que le LLM a reçu pour ce mail."""

    def __init__(self):
        self.gateway = FakeGateway()
        self.kb: list[dict] = []
        self.seen_plain: dict[int, str] = {}
        self.summarize_calls = 0

    def install(self):
        async def fake_summarize(email, *, prompt=None, plain=None, **_):
            self.summarize_calls += 1
            if ERROR_MARKER in (email.subject or ""):
                raise RuntimeError("DeepInfra simulé indisponible")
            text = plain if plain is not None else ((email.text_body or "") or (email.html_body or ""))
            self.seen_plain[email.id] = text
            if not text:
                return ""
            return f"<h3>Résumé simulé</h3><p>{email.subject}</p>"

        async def fake_kb(email, alias=None, source_url=None):
            self.kb.append({"id": email.id, "alias": alias, "source_url": source_url})

        summarizer.summarize_html = fake_summarize
        comms_client.get_client = lambda: self.gateway
        digest.datetime = FrozenDatetime
        alias_digest.store_email_summary = fake_kb
        return self


async def fresh_db():
    """Schéma + alias par défaut + prompt v1, comme au démarrage du service. Renvoie l'alias par défaut."""
    await init_db()
    async with AsyncSessionLocal() as db:
        default = await al.seed_default_alias(db)
        await seed_default(db)
    return default


async def add_email(alias_id, *, frm="jean@exemple.fr", to="summary@oozeenaru.resend.app", subject="Sujet",
                    body="corps présent", status="new", received="2026-09-25T05:00:00", email_id=None,
                    message_id=None, attempts=0) -> int:
    async with AsyncSessionLocal() as db:
        n = (await db.execute(__import__("sqlalchemy").text("select count(*) from emails"))).scalar_one()
        e = Email(message_id=message_id or f"h-{n}-{subject}", alias_id=alias_id, from_addr=frm, to_addr=to,
                  subject=subject, text_body=body, html_body="", status=status, email_id=email_id,
                  received_at=datetime.fromisoformat(received), attempts=attempts)
        db.add(e)
        await db.commit()
        return e.id


async def get_email(email_id):
    async with AsyncSessionLocal() as db:
        return await db.get(Email, email_id)


async def make_alias(local_part, **kw):
    async with AsyncSessionLocal() as db:
        return await al.create_alias(db, local_part, **kw)


async def sql(query, **params):
    from sqlalchemy import text
    async with AsyncSessionLocal() as db:
        res = await db.execute(text(query), params)
        await db.commit()
        return res
