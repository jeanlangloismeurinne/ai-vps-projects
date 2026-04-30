"""
Vérifie le cookie hub_session signé par la homepage.
Si absent/invalide → redirect vers la page de login du hub.
"""
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request
from fastapi.responses import RedirectResponse

COOKIE_NAME = "hub_session"
_MAX_AGE = 60 * 60 * 24 * 30
LOGIN_URL = "https://jlmvpscode.duckdns.org/login"


def verify_cookie(value: str, secret: str) -> bool:
    try:
        URLSafeTimedSerializer(secret, salt="hub-auth").loads(value, max_age=_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


def check_session(request: Request, secret: str) -> bool:
    value = request.cookies.get(COOKIE_NAME, "")
    return bool(value) and verify_cookie(value, secret)


def redirect_to_login(next_url: str = "") -> RedirectResponse:
    dest = LOGIN_URL
    if next_url:
        dest += f"?next={next_url}"
    return RedirectResponse(dest, status_code=302)
