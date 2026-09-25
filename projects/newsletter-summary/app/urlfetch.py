"""Mail réduit à un lien → récupération du contenu de la page pour le résumer.

⚠️ SSRF. Le champ `From` d'un mail est usurpable, et ce conteneur voit `shared-postgres`,
`comms-gateway`, le proxy… Sans garde, un mail « http://comms-gateway:8000/… » ferait lire le
réseau interne au serveur. Chaque requête — et chaque redirection, suivie À LA MAIN — est donc
revalidée : http/https seulement, ports 80/443 seulement, hôte résolu puis REFUSÉ si une seule des
adresses n'est pas publique. Risque résiduel assumé : ré-résolution DNS entre la validation et la
connexion (fenêtre étroite ; atténuée par la liste blanche d'expéditeurs et parce que ce qui revient
est un texte de page résumé, jamais la réponse brute).

Chaque échec est NOMMÉ (`UrlFetchError.reason`) et classé permanent / transitoire : le moteur
répond à l'expéditeur avec la raison plutôt que de se taire.
"""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import re
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx

logger = logging.getLogger(__name__)

MAX_REDIRECTS = 5
MAX_BYTES = 2_000_000
MAX_TEXT_CHARS = 30_000
MIN_TEXT_CHARS = 200
TOTAL_TIMEOUT_S = 30.0
ALLOWED_PORTS = {80, 443}
ALLOWED_TYPES = ("text/html", "application/xhtml+xml", "text/plain")
USER_AGENT = "Mozilla/5.0 (compatible; newsletter-summary/1.0)"


class UrlFetchError(Exception):
    """Échec de récupération. `permanent` : inutile de réessayer (403, adresse interne…)."""

    def __init__(self, reason: str, permanent: bool = True):
        super().__init__(reason)
        self.reason = reason
        self.permanent = permanent


@dataclass
class FetchedPage:
    url: str
    title: str
    text: str


# ── Détection : « le corps n'est qu'un lien » ────────────────────────────────────────────────
_BARE_URL = re.compile(r"^<?(https?://[^\s<>]+)>?$", re.IGNORECASE)
# html2text rend `<a href=u>texte</a>` en `[texte](u)` et un lien nu en `<u>`.
_MD_LINK = re.compile(r"^\[[^\]]*\]\((https?://[^)\s]+)\)$", re.IGNORECASE)


def sole_url(text: str) -> str | None:
    """L'URL si le corps ne contient RIEN d'autre (espaces et retours ignorés), sinon None.

    « Regarde ça https://… » n'est volontairement PAS un lien seul : l'utilisateur a écrit du
    texte, c'est le mail qui est résumé.
    """
    s = (text or "").strip()
    if not s:
        return None
    for rx in (_BARE_URL, _MD_LINK):
        m = rx.match(s)
        if m:
            return m.group(1)
    return None


# ── Garde réseau ─────────────────────────────────────────────────────────────────────────────

async def _resolve(host: str, port: int) -> list[str]:
    """Adresses IP de l'hôte (surchargeable dans les tests, qui n'ont pas de DNS)."""
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UrlFetchError(f"domaine introuvable ({host})") from exc
    return list({info[4][0] for info in infos})


def _is_public(ip_text: str) -> bool:
    # `::ffff:127.0.0.1` est jugé non public par Python ≥ 3.12.4 (image python:3.12) : pas de dépliage
    # maison. Le cas `v4mapped.local` de check_urlfetch.py épingle ce comportement de l'interpréteur.
    return ipaddress.ip_address(ip_text.split("%", 1)[0]).is_global


async def validate_url(url: str) -> None:
    """Lève UrlFetchError (permanente) si l'URL n'est pas une page web publique."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise UrlFetchError(f"schéma non autorisé ({parts.scheme or 'vide'})")
    if not parts.hostname:
        raise UrlFetchError("adresse sans nom d'hôte")
    if parts.username or parts.password:
        raise UrlFetchError("adresse avec identifiants refusée")
    try:
        port = parts.port or (443 if parts.scheme == "https" else 80)
    except ValueError:
        raise UrlFetchError("port invalide")
    if port not in ALLOWED_PORTS:
        raise UrlFetchError(f"port non autorisé ({port})")
    for ip in await _resolve(parts.hostname, port):
        if not _is_public(ip):
            raise UrlFetchError("adresse non publique refusée")


# ── Extraction ───────────────────────────────────────────────────────────────────────────────
_STRIP_BLOCKS = re.compile(
    r"<(script|style|noscript|svg|iframe|template)\b.*?</\1\s*>|<!--.*?-->", re.IGNORECASE | re.DOTALL
)
_TITLE = re.compile(r"<title[^>]*>(.*?)</title\s*>", re.IGNORECASE | re.DOTALL)


def extract_text(raw: str, content_type: str) -> tuple[str, str]:
    """(titre, texte) d'une page. Texte brut pris tel quel ; HTML nettoyé puis converti."""
    if content_type.startswith("text/plain"):
        return "", raw.strip()
    import html as html_mod
    import html2text

    m = _TITLE.search(raw)
    title = re.sub(r"\s+", " ", html_mod.unescape(m.group(1))).strip() if m else ""
    cleaned = _STRIP_BLOCKS.sub(" ", raw)
    conv = html2text.HTML2Text()
    conv.ignore_links = True     # les liens de navigation noient le contenu et coûtent des jetons
    conv.ignore_images = True
    conv.body_width = 0
    return title, conv.handle(cleaned).strip()


# ── Récupération ─────────────────────────────────────────────────────────────────────────────

async def _fetch(url: str, transport: httpx.AsyncBaseTransport | None) -> FetchedPage:
    current = url
    async with httpx.AsyncClient(
        follow_redirects=False, timeout=15.0, transport=transport,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain;q=0.9"},
    ) as client:
        for _hop in range(MAX_REDIRECTS + 1):
            await validate_url(current)
            try:
                async with client.stream("GET", current) as r:
                    if r.is_redirect:
                        loc = r.headers.get("location")
                        if not loc:
                            raise UrlFetchError("redirection sans destination")
                        current = urljoin(current, loc)
                        continue
                    if r.status_code in (429,) or r.status_code >= 500:
                        raise UrlFetchError(f"site indisponible (HTTP {r.status_code})", permanent=False)
                    if r.status_code == 403:
                        raise UrlFetchError("page bloquée (403)")
                    if r.status_code == 404:
                        raise UrlFetchError("page introuvable (404)")
                    if r.status_code >= 400:
                        raise UrlFetchError(f"page inaccessible (HTTP {r.status_code})")
                    ctype = r.headers.get("content-type", "").split(";")[0].strip().lower()
                    if not ctype.startswith(ALLOWED_TYPES):
                        raise UrlFetchError(f"type de contenu non pris en charge ({ctype or 'inconnu'})")
                    buf = bytearray()
                    async for chunk in r.aiter_bytes():
                        buf += chunk
                        if len(buf) >= MAX_BYTES:   # on résume le début : tronquer vaut mieux qu'échouer
                            del buf[MAX_BYTES:]     # plafond STRICT même si un seul chunk le dépasse
                            break
                    charset = r.encoding or "utf-8"
            except httpx.TimeoutException as exc:
                raise UrlFetchError("délai dépassé en récupérant la page", permanent=False) from exc
            except httpx.HTTPError as exc:
                raise UrlFetchError(f"erreur réseau ({type(exc).__name__})", permanent=False) from exc
            raw = bytes(buf).decode(charset, errors="replace")
            title, text = extract_text(raw, ctype)
            if len(text) < MIN_TEXT_CHARS:
                raise UrlFetchError("page vide (contenu rendu par JavaScript ?)")
            return FetchedPage(url=current, title=title, text=text[:MAX_TEXT_CHARS])
    raise UrlFetchError(f"trop de redirections (> {MAX_REDIRECTS})")


async def fetch_page(url: str, *, transport: httpx.AsyncBaseTransport | None = None) -> FetchedPage:
    """Contenu texte d'une page publique. `transport` : injection pour les tests (pas de réseau)."""
    try:
        return await asyncio.wait_for(_fetch(url, transport), timeout=TOTAL_TIMEOUT_S)
    except asyncio.TimeoutError as exc:
        raise UrlFetchError("délai dépassé en récupérant la page", permanent=False) from exc
