"""
Auth partagée hub — cookie hub_session signé (itsdangerous).
Même logique de vérification dans assistant-ia (app/routes/auth.py).
"""
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request
from fastapi.responses import RedirectResponse

COOKIE_NAME = "hub_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 jours


def _signer(secret: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret, salt="hub-auth")


def make_cookie_value(username: str, secret: str) -> str:
    return _signer(secret).dumps(username)


def verify_cookie(value: str, secret: str) -> str | None:
    """Retourne le username si valide, None sinon."""
    try:
        return _signer(secret).loads(value, max_age=COOKIE_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def get_session(request: Request, secret: str) -> str | None:
    value = request.cookies.get(COOKIE_NAME)
    if not value:
        return None
    return verify_cookie(value, secret)


def redirect_to_login(next_url: str = "") -> RedirectResponse:
    dest = "/login"
    if next_url:
        dest += f"?next={next_url}"
    return RedirectResponse(dest, status_code=302)
