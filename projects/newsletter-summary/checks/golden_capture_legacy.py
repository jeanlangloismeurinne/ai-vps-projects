#!/usr/bin/env python3
"""Capture le comportement du digest LEGACY (`digest.run_daily_digest`) — à lancer AVANT toute
modification du moteur. Produit deux fixtures gelées, copiées du réel :

  checks/golden/legacy_rows.json    lignes d'entrée (métadonnées de vraies newsletters de prod)
  checks/golden/legacy_digest.json  ce que le legacy envoie (destinataire, objet, texte, HTML)

Le test d'or (`check_golden_newsletter.py`) exige que le moteur générique reproduise ces sorties
octet à octet. Ne PAS relancer après avoir touché au moteur : ce serait capturer le nouveau
comportement et rendre le test d'or tautologique.

Lancer :  projects/newsletter-summary/checks/run.sh checks/golden_capture_legacy.py
"""
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

GOLDEN = Path(__file__).resolve().parent / "golden"
ERROR_MARKER = "[[echec-resume]]"


async def fetch_real_rows() -> list[dict]:
    eng = create_async_engine(os.environ["PROD_DATABASE_URL"])
    async with eng.connect() as c:
        rs = (await c.execute(text(
            "select id, from_addr, to_addr, subject, received_at, "
            "(length(text_body) > 0 or length(html_body) > 0) as has_body "
            "from emails where status='summarized' and to_addr <> '' "
            "order by id desc limit 3"
        ))).mappings().all()
    await eng.dispose()
    rows = [
        {"from_addr": r["from_addr"], "to_addr": r["to_addr"], "subject": r["subject"],
         "received_at": r["received_at"].isoformat(), "has_body": bool(r["has_body"])}
        for r in reversed(rs)
    ]
    # Deux branches que le réel du jour n'exerce pas : corps jamais rapatrié, résumé en échec.
    rows.append({"from_addr": "playbook@politico.eu", "to_addr": "newsletter@oozeenaru.resend.app",
                 "subject": "Mail arrivé trop tôt (corps non rapatrié)",
                 "received_at": "2026-09-25T05:10:00", "has_body": False})
    rows.append({"from_addr": "no-reply@newsletter.euractiv.com", "to_addr": "newsletter@oozeenaru.resend.app",
                 "subject": f"Résumé en échec {ERROR_MARKER}",
                 "received_at": "2026-09-25T05:20:00", "has_body": True})
    return rows


async def main() -> None:
    from app import comms_client, digest, summarizer
    from app.database import AsyncSessionLocal, init_db
    from app.models import Email

    rows = await fetch_real_rows()
    GOLDEN.mkdir(exist_ok=True)
    (GOLDEN / "legacy_rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")

    await init_db()
    async with AsyncSessionLocal() as db:
        for i, r in enumerate(rows):
            db.add(Email(
                message_id=f"golden-{i}", from_addr=r["from_addr"], to_addr=r["to_addr"],
                subject=r["subject"], received_at=datetime.fromisoformat(r["received_at"]),
                text_body="corps présent" if r["has_body"] else "", html_body="", status="new",
            ))
        await db.commit()

    async def fake_summarize(email, *, prompt=None, **_):
        if ERROR_MARKER in (email.subject or ""):
            raise RuntimeError("DeepInfra simulé indisponible")
        if not (email.text_body or email.html_body):
            return ""
        return f"<h3>Résumé simulé</h3><p>{email.subject}</p>"

    sent: list[dict] = []

    class FakeClient:
        async def send_email(self, to, subject, body, html=None, **kw):
            sent.append({"to": to, "subject": subject, "body": body, "html": html})
            return {"status": "sent"}

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 25, 8, 0, 0)

    summarizer.summarize_html = fake_summarize
    comms_client.get_client = lambda: FakeClient()
    digest.datetime = FrozenDatetime
    digest.store_email_summary = lambda e: asyncio.sleep(0)

    result = await digest.run_daily_digest()
    assert result == {"sent": True, "count": len(rows)}, result
    assert len(sent) == 1, sent
    (GOLDEN / "legacy_digest.json").write_text(json.dumps(sent[0], ensure_ascii=False, indent=2) + "\n")
    print(f"OK — {len(rows)} lignes, 1 envoi capturé (objet : {sent[0]['subject']!r}, to={sent[0]['to']})")


asyncio.run(main())
