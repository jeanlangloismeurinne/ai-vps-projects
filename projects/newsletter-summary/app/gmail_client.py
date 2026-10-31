"""Client signé du script Apps Script qui pilote les filtres Gmail.

Contrat : docs/gmail-forward/SPEC.md. Le VPS ne parle qu'au script ; chaque appel est signé
(HMAC-SHA256 de `v.ts.nonce.action.payload`) et chaque réponse est vérifiée avant usage
(`nonce.true.result` ou `nonce.false.code`). Une réponse dont la signature ne se vérifie pas n'est
JAMAIS utilisée : la règle reste en attente plutôt que d'être déclarée synchronisée par hypothèse.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import secrets
import time

import httpx

TIMEOUT_S = 30.0
_SCRIPT_URL_RE = re.compile(r"https://script\.google(?:usercontent)?\.com/\S*")


class _RedactScriptUrl(logging.Filter):
    """httpx journalise « POST <url> » en INFO : l'URL du déploiement est un secret (accès anonyme)."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _SCRIPT_URL_RE.sub("[url-script-masquée]", record.getMessage())
        record.args = ()
        return True


logging.getLogger("httpx").addFilter(_RedactScriptUrl())
AUTH_CODES = {"bad_signature", "stale_timestamp", "replayed_nonce"}


class ScriptUnreachable(Exception):
    """Réseau, délai dépassé, statut HTTP anormal ou corps illisible : on ne sait pas si l'écriture a eu lieu."""


class ScriptSignatureError(Exception):
    """Réponse reçue mais dont la signature est absente ou fausse : non fiable, ignorée."""


class ScriptError(Exception):
    """Refus explicite et authentique du script (réponse signée `ok: false`) — ou erreur d'authentification."""

    def __init__(self, code: str, message: str = "", signed: bool = True):
        super().__init__(f"{code}: {message}")
        self.code, self.message, self.signed = code, message, signed

    @property
    def is_auth(self) -> bool:
        return self.code in AUTH_CODES


def sign(secret: str, v: int, ts: int, nonce: str, action: str, payload: str) -> str:
    return hmac.new(secret.encode(), ".".join([str(v), str(ts), nonce, action, payload]).encode(), hashlib.sha256).hexdigest()


def _response_sig(secret: str, nonce: str, ok: bool, body: str) -> str:
    msg = ".".join([nonce, "true" if ok else "false", body])
    return hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()


def payload_hash(payload: dict) -> str:
    """Empreinte du payload pour le journal (jamais le payload lui-même)."""
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


class ScriptClient:
    def __init__(self, url: str, secret: str, *, transport: httpx.AsyncBaseTransport | None = None,
                 timeout: float = TIMEOUT_S, now=time.time):
        self.url, self.secret, self.timeout, self.now = url, secret, timeout, now
        self.transport = transport

    async def call(self, action: str, payload: dict | None = None) -> dict:
        """Appelle une action et renvoie le résultat décodé.

        Lève ScriptUnreachable (issue inconnue), ScriptSignatureError (réponse non fiable) ou ScriptError
        (refus authentique). Un seul appel, SANS réessai : seul l'appelant sait si l'action est idempotente.
        """
        if not self.url or not self.secret:
            raise ScriptUnreachable("script non configuré (URL ou secret absent)")
        payload_str = json.dumps(payload or {}, ensure_ascii=False, separators=(",", ":"))
        nonce = secrets.token_hex(8)
        ts = int(self.now())
        envelope = {"v": 1, "ts": ts, "nonce": nonce, "action": action, "payload": payload_str,
                    "sig": sign(self.secret, 1, ts, nonce, action, payload_str)}
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, transport=self.transport) as c:
                r = await c.post(self.url, content=json.dumps(envelope), headers={"Content-Type": "text/plain"})
        except httpx.HTTPError as exc:
            raise ScriptUnreachable(f"{type(exc).__name__}") from None   # jamais l'URL : elle est secrète
        if r.status_code != 200:
            raise ScriptUnreachable(f"statut HTTP {r.status_code}")
        try:
            body = r.json()
            assert isinstance(body, dict)
        except Exception:
            raise ScriptUnreachable("réponse non JSON") from None

        sig = body.get("sig")
        if not sig:
            # Seules les erreurs d'authentification/enveloppe ne sont pas signées. On en retient le CODE
            # (pour compter les échecs d'auth) mais on ne s'y fie pour rien d'autre.
            err = body.get("error") if isinstance(body.get("error"), dict) else {}
            raise ScriptError(str(err.get("code") or "unsigned"), str(err.get("message") or ""), signed=False)
        if body.get("nonce") != nonce:
            raise ScriptSignatureError("nonce de réponse inattendu")
        if body.get("ok") is True and isinstance(body.get("result"), str):
            expected = _response_sig(self.secret, nonce, True, body["result"])
            if not hmac.compare_digest(expected, str(sig)):
                raise ScriptSignatureError("signature de réponse fausse")
            return json.loads(body["result"])
        if body.get("ok") is False and isinstance(body.get("error"), dict) and isinstance(body["error"].get("code"), str):
            expected = _response_sig(self.secret, nonce, False, body["error"]["code"])
            if not hmac.compare_digest(expected, str(sig)):
                raise ScriptSignatureError("signature de réponse fausse")
            raise ScriptError(body["error"]["code"], str(body["error"].get("message") or ""))
        raise ScriptSignatureError("réponse mal formée")
