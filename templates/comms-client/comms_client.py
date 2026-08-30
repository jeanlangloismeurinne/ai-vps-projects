"""
comms_client — SDK client du gateway de communication externe `comms-gateway`.

Chaque projet consommateur embarque une copie de ce module (cf. README) et l'appelle
pour ENVOYER des messages (email, Slack, puis SMS/WhatsApp/Signal) sans jamais détenir
les secrets des providers externes — ils restent au gateway.

Configuration : deux variables d'environnement suffisent pour un nouveau projet :
    GATEWAY_URL   = https://comms.jlmvpscode.duckdns.org   (ou http://comms-gateway:8000 en interne)
    GATEWAY_TOKEN = <token scoped du client, distribué en secret Coolify du projet>

Usage :
    import comms_client as comms
    await comms.send_email(to="jean@mailbox.org", subject="Titre", body="Corps")
    await comms.send_slack(to="#journal", body="Bonjour")

Le module est écrit en asyncio (httpx). Pour du code synchrone, envelopper via asyncio.run().
"""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)


class CommsError(RuntimeError):
    """Erreur d'envoi via le gateway (rejet policy, rate-limit ou échec provider)."""


class CommsClient:
    def __init__(
        self,
        *,
        gateway_url: str | None = None,
        token: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = (gateway_url or os.environ.get("GATEWAY_URL", "")).rstrip("/")
        self.token = token or os.environ.get("GATEWAY_TOKEN", "")
        self.timeout = timeout
        if not self.base_url or not self.token:
            raise CommsError("GATEWAY_URL et GATEWAY_TOKEN sont requis")

    async def send(
        self,
        channel: str,
        to: str,
        *,
        subject: str | None = None,
        body: str | None = None,
        attachments: list[dict] | None = None,
    ) -> dict:
        """POST /v1/send — lève CommsError si rejeté (policy/rate-limit) ou en échec."""
        payload: dict = {"channel": channel, "to": to}
        if subject:
            payload["subject"] = subject
        if body:
            payload["body"] = body
        if attachments:
            payload["attachments"] = attachments

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(
                f"{self.base_url}/v1/send",
                headers={"Authorization": f"Bearer {self.token}"},
                json=payload,
            )
        if r.status_code in (200, 201):
            return r.json()
        # Le gateway renvoie 200 avec status 'rejected', ou 4xx/5xx
        try:
            data = r.json()
        except Exception:
            data = {}
        if r.status_code == 200 and data.get("status") == "sent":
            return data
        reason = data.get("reason") or data.get("error") or f"HTTP {r.status_code}"
        raise CommsError(reason)

    async def send_email(self, to: str, subject: str, body: str, **kw) -> dict:
        return await self.send("email", to, subject=subject, body=body, **kw)

    async def send_slack(self, to: str, body: str, **kw) -> dict:
        return await self.send("slack", to, body=body, **kw)

    async def send_sms(self, number: str, body: str, **kw) -> dict:
        return await self.send("sms", number, body=body, **kw)

    async def messages(self, limit: int = 100) -> list:
        """GET /v1/messages — historique strictement limité à ce client."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(
                f"{self.base_url}/v1/messages",
                headers={"Authorization": f"Bearer {self.token}"},
                params={"limit": limit},
            )
        r.raise_for_status()
        return r.json().get("rows", [])


# Client par défaut, configuré depuis l'environnement.
default: CommsClient | None = None


def get_client() -> CommsClient:
    global default
    if default is None:
        default = CommsClient()
    return default


# --- Helpers synchrones (pratique dans des scripts/apps sans asyncio) ---
def send_email_sync(to: str, subject: str, body: str, **kw) -> dict:
    import asyncio

    return asyncio.run(get_client().send_email(to, subject, body, **kw))


def send_slack_sync(to: str, body: str, **kw) -> dict:
    import asyncio

    return asyncio.run(get_client().send_slack(to, body, **kw))
