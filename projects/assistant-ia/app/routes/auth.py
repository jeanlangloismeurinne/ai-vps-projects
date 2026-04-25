"""
Vérifie le cookie hub_session signé par homepage.
Si absent/invalide → lève HubAuthRequired, intercepté dans main.py → redirect login.
"""
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request

COOKIE_NAME = "hub_session"
_MAX_AGE = 60 * 60 * 24 * 30
LOGIN_URL = "https://jlmvpscode.duckdns.org/login"


class HubAuthRequired(Exception):
    def __init__(self, next_url: str = ""):
        self.next_url = next_url


def verify_cookie(value: str, secret: str) -> bool:
    try:
        URLSafeTimedSerializer(secret, salt="hub-auth").loads(value, max_age=_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


async def require_auth(request: Request) -> None:
    from app.config import settings
    value = request.cookies.get(COOKIE_NAME, "")
    if value and verify_cookie(value, settings.SESSION_SECRET):
        return
    raise HubAuthRequired(str(request.url))
