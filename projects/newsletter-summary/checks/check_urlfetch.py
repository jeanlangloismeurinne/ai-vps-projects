#!/usr/bin/env python3
"""Mail réduit à un lien : détection stricte et récupération durcie contre le SSRF.

Le champ `From` est usurpable et le conteneur voit `shared-postgres`, `comms-gateway`, le proxy…
Un mail « http://comms-gateway:8000/… » ne doit JAMAIS faire lire le réseau interne au serveur.
Aucun accès réseau : DNS simulé (`_resolve`), serveur simulé (`httpx.MockTransport`) — ce qui rend
aussi la garde testable sur des cibles qu'on ne voudrait pas viser pour de vrai (métadonnées cloud).

Toutes les redirections sont revalidées : le cas dur est « URL publique qui redirige vers une IP
interne » — le mock ENREGISTRE les hôtes réellement joints, on exige que l'hôte interne ne soit
jamais contacté (pas seulement que l'appel finisse en erreur).
"""
import asyncio
import ipaddress

import httpx

import _harness  # noqa: F401  (chemin, logs)
from app import urlfetch
from app.models import Email
from app.summarizer import _to_plain

HOSTS = {
    "exemple.org": ["93.184.216.34"], "www.exemple.org": ["93.184.216.34"],
    "interne.local": ["10.0.0.5"], "comms-gateway": ["172.18.0.5"], "shared-postgres": ["172.18.0.2"],
    "metadata.local": ["169.254.169.254"], "mixte.example": ["93.184.216.34", "192.168.1.1"],
    "v4mapped.local": ["::ffff:127.0.0.1"], "v6.local": ["2606:4700:4700::1111"],
}


async def fake_resolve(host, port):
    try:
        ipaddress.ip_address(host)
        return [host]                      # littéral IP : getaddrinfo le renvoie tel quel
    except ValueError:
        pass
    if host not in HOSTS:
        raise urlfetch.UrlFetchError(f"domaine introuvable ({host})")
    return HOSTS[host]


urlfetch._resolve = fake_resolve
LONG = "Ceci est le contenu éditorial de la page. " * 15          # > 200 caractères
HTML = f"<html><head><title> Mon  article </title><script>SECRET_JS()</script><style>.x{{}}</style></head><body><h1>Titre</h1><p>{LONG}</p></body></html>"


def transport(handler, seen=None):
    def wrapped(request):
        if seen is not None:
            seen.append(request.url.host)
        return handler(request)
    return httpx.MockTransport(wrapped)


async def refused(url, needle):
    try:
        await urlfetch.fetch_page(url, transport=transport(lambda r: httpx.Response(200, text=HTML, headers={"content-type": "text/html"})))
    except urlfetch.UrlFetchError as exc:
        assert needle in exc.reason, f"{url} refusé pour la mauvaise raison : {exc.reason!r} (attendu : {needle!r})"
        assert exc.permanent, f"{url} : un refus de sécurité doit être permanent"
        return
    raise AssertionError(f"{url} AURAIT DÛ être refusé ({needle})")


async def fails(handler, needle, permanent, url="https://exemple.org/p"):
    try:
        await urlfetch.fetch_page(url, transport=transport(handler))
    except urlfetch.UrlFetchError as exc:
        assert needle in exc.reason and exc.permanent is permanent, f"{url} → {exc.reason!r} (permanent={exc.permanent}), attendu {needle!r} permanent={permanent}"
        return
    raise AssertionError(f"échec attendu ({needle}) mais la page a été récupérée")


async def main():
    # ── détection « le corps n'est qu'un lien » ──
    for ok in ("https://a.fr/c?x=1#y", "  https://a.fr/c\n", "<https://a.fr/c>", "[Lire](https://a.fr/c)", "HTTP://A.FR/C"):
        assert urlfetch.sole_url(ok), f"lien seul non reconnu : {ok!r}"
    for ko in ("Regarde https://a.fr/c", "https://a.fr/c et https://d.fr/f", "", "ftp://a.fr/c", "https://a.fr/c\nmerci", "bonjour", "https://a.fr/c\n--\nJean"):
        assert urlfetch.sole_url(ko) is None, f"à tort reconnu comme lien seul : {ko!r}"
    # Corps réels : un lien envoyé depuis un mobile arrive souvent en HTML, converti par html2text.
    for html in ("<p><a href='https://exemple.org/a'>https://exemple.org/a</a></p>", "<div><a href='https://exemple.org/a'>Lire l'article</a></div>"):
        e = Email(text_body="", html_body=html)
        assert urlfetch.sole_url(_to_plain(e)) == "https://exemple.org/a", f"lien HTML non reconnu : {_to_plain(e)!r}"

    # ── SSRF : refus AVANT toute connexion ──
    for url, why in (
        ("http://127.0.0.1/", "non publique"), ("http://localhost/", "domaine introuvable"), ("http://[::1]/", "non publique"),
        ("http://169.254.169.254/latest/meta-data/", "non publique"), ("http://metadata.local/", "non publique"),
        ("http://interne.local/", "non publique"), ("http://10.0.0.5/", "non publique"), ("http://192.168.1.1/", "non publique"),
        ("http://172.18.0.5/", "non publique"), ("http://comms-gateway/x", "non publique"), ("http://shared-postgres/", "non publique"),
        ("http://mixte.example/", "non publique"),                 # UNE seule IP privée suffit à refuser
        ("http://v4mapped.local/", "non publique"),                # ::ffff:127.0.0.1
        ("http://comms-gateway:8000/v1/messages", "port non autorisé (8000)"), ("https://exemple.org:8443/", "port non autorisé (8443)"),
        ("http://exemple.org:5432/", "port non autorisé (5432)"),
        ("file:///etc/passwd", "schéma"), ("ftp://exemple.org/", "schéma"), ("gopher://exemple.org/", "schéma"),
        ("https://user:pw@exemple.org/", "identifiants"), ("http://inconnu.example/", "domaine introuvable"),
    ):
        await refused(url, why)

    # ── récupération nominale ──
    page = await urlfetch.fetch_page("https://exemple.org/a", transport=transport(lambda r: httpx.Response(200, text=HTML, headers={"content-type": "text/html; charset=utf-8"})))
    assert page.title == "Mon article", page.title
    assert "contenu éditorial" in page.text and "SECRET_JS" not in page.text and ".x{" not in page.text, "script/style doivent être retirés"
    p2 = await urlfetch.fetch_page("https://v6.local/", transport=transport(lambda r: httpx.Response(200, text=LONG, headers={"content-type": "text/plain"})))
    assert p2.text.startswith("Ceci est"), "text/plain accepté"

    # ── redirections : chaque saut est revalidé ──
    seen: list[str] = []

    def to_internal(r):
        if r.url.host == "exemple.org":
            return httpx.Response(302, headers={"location": "http://interne.local/admin"})
        return httpx.Response(200, text=HTML, headers={"content-type": "text/html"})

    try:
        await urlfetch.fetch_page("https://exemple.org/a", transport=transport(to_internal, seen))
        raise AssertionError("redirection vers une IP interne SUIVIE")
    except urlfetch.UrlFetchError as exc:
        assert "non publique" in exc.reason, exc.reason
    assert seen == ["exemple.org"], f"l'hôte interne a été CONTACTÉ : {seen} (refuser après coup ne suffit pas)"

    def to_port(r):
        return httpx.Response(302, headers={"location": "http://exemple.org:8000/"}) if r.url.port is None else httpx.Response(200, text=HTML)
    await fails(to_port, "port non autorisé (8000)", True)

    def relative(r):
        return httpx.Response(301, headers={"location": "/vraie-page"}) if r.url.path == "/a" else httpx.Response(200, text=HTML, headers={"content-type": "text/html"})
    assert (await urlfetch.fetch_page("https://exemple.org/a", transport=transport(relative))).url == "https://exemple.org/vraie-page", "redirection relative"
    await fails(lambda r: httpx.Response(302, headers={"location": "https://exemple.org/p"}), "trop de redirections", True)

    # ── échecs nommés, classés permanent / transitoire ──
    await fails(lambda r: httpx.Response(403), "page bloquée (403)", True)
    await fails(lambda r: httpx.Response(404), "page introuvable (404)", True)
    await fails(lambda r: httpx.Response(410), "page inaccessible (HTTP 410)", True)
    await fails(lambda r: httpx.Response(500), "site indisponible (HTTP 500)", False)
    await fails(lambda r: httpx.Response(429), "site indisponible (HTTP 429)", False)
    await fails(lambda r: httpx.Response(200, content=b"%PDF", headers={"content-type": "application/pdf"}), "type de contenu non pris en charge (application/pdf)", True)
    await fails(lambda r: httpx.Response(200, text="<html><body><p>Chargement…</p></body></html>", headers={"content-type": "text/html"}), "page vide", True)

    def boom(r):
        raise httpx.ConnectTimeout("délai")
    await fails(boom, "délai dépassé", False)

    # ── plafond de lecture : on s'ARRÊTE de lire (pas seulement de garder) ──
    class Flux(httpx.AsyncByteStream):
        n = 0

        async def __aiter__(self):
            for _ in range(50):
                Flux.n += 1
                yield b"mot " * 25_000                              # 100 Ko par chunk
    big = await urlfetch.fetch_page("https://exemple.org/big", transport=transport(lambda r: httpx.Response(200, headers={"content-type": "text/plain"}, stream=Flux())))
    assert Flux.n <= 21, f"{Flux.n} chunks lus sur 50 : le plafond de 2 Mo n'arrête pas la lecture"
    assert len(big.text) <= urlfetch.MAX_TEXT_CHARS, "texte envoyé au LLM non borné"
    print("OK — détection stricte ; 21 cibles internes/interdites refusées ; redirections revalidées ; échecs nommés ; lecture bornée")


asyncio.run(main())
