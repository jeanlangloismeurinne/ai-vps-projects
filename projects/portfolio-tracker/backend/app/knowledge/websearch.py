"""
Accès web du search-worker (couche 3) — `web_search` + `fetch_url`, backend-agnostiques.

Deux primitives, aucune logique d'agent :
  - **web_search** : recherche via un backend interchangeable (Exa nominal, Serper en débordement),
    sélectionné par `settings.SEARCH_PROVIDER`. Le contrat de sortie (`SearchHit`) est identique quel
    que soit le backend → basculer Exa ↔ Serper ↔ autre = écrire UNE classe, sans toucher au
    `tools_json` en DB, au prompt du worker, ni à la boucle tool-calling.
  - **fetch_url** : récupère une page et en extrait le texte (stdlib `html.parser`, aucune dépendance
    ajoutée à l'image).

**Échec explicite, jamais silencieux.** Sans clé, ou si le backend répond mal, on lève
`SearchUnavailable` — l'erreur remonte au modèle comme `{"error": …}`. C'est délibéré : la raison
pour laquelle SearXNG a été écarté (00-REPRISE.md) est qu'il renvoyait, depuis une IP unique
captchaée, **des résultats vides sans erreur** — l'agent croit alors avoir cherché et conclut à une
absence de source. Un `uncovered_fields` fondé sur une recherche qui n'a pas eu lieu contamine le
readiness et le garde-fou A2 n'y voit rien : les refs citées existent, ce sont les refs manquantes
qui sont fausses.

`classify_source_type()` fixe, à partir du **domaine**, le plafond de `source_type` défendable pour
une URL (sec.gov → edgar_official, ir.nvidia.com → company_ir_official, blog inconnu →
web_search_generic). Il est appliqué côté Python dans le worker : le score de fiabilité découle du
source_type, donc laisser le modèle qualifier lui-même sa source reviendrait à lui laisser fixer son
propre score — exactement ce que le plafond de source (§6.3) interdit.
"""
from __future__ import annotations

import abc
import logging
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class SearchUnavailable(RuntimeError):
    """Backend de recherche non configuré ou en échec. Jamais confondu avec « 0 résultat »."""


@dataclass
class SearchHit:
    """Résultat normalisé, indépendant du backend."""
    title: str
    url: str
    snippet: str = ""
    published_date: Optional[str] = None   # ISO date si le backend la donne
    text: Optional[str] = None             # contenu extrait si le backend le fournit (Exa)

    def to_dict(self) -> dict[str, Any]:
        d = {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "published_date": self.published_date,
            "domain": urlparse(self.url).netloc.lower().removeprefix("www."),
            "source_type_max": classify_source_type(self.url),
        }
        if self.text:
            d["text"] = self.text
        return d


# ── Qualification de source par domaine (plafond opposable au modèle) ────────
# Un domaine ne PROUVE pas la qualité d'un contenu, mais il la BORNE : un PDF sur sec.gov peut
# légitimement porter edgar_official, un billet Medium ne le peut jamais. On borne, on ne promeut pas.
_OFFICIAL_DOMAINS = {
    "sec.gov": "edgar_official",
    "www.sec.gov": "edgar_official",
    "efts.sec.gov": "edgar_official",
}
_EU_REGULATOR_SUFFIXES = ("amf-france.org", "esma.europa.eu", "bafin.de", "fca.org.uk", "consob.it")
_PRESS_DOMAINS = {
    "reuters.com", "bloomberg.com", "ft.com", "wsj.com", "cnbc.com", "barrons.com",
    "lesechos.fr", "latribune.fr", "handelsblatt.com", "nikkei.com", "economist.com",
    "marketwatch.com", "morningstar.com", "seekingalpha.com", "fool.com",
}
# Un domaine « réputé » sans être de la presse financière primaire : plafond B (0.65).
_REPUTABLE_SUFFIXES = ("nvidia.com", "arxiv.org", "iea.org", "oecd.org", "worldbank.org")
_IR_HOST_PATTERN = re.compile(r"^(ir|investor|investors|investorrelations)\.", re.IGNORECASE)


def classify_source_type(url: Optional[str]) -> str:
    """`source_type` le plus favorable qu'un domaine puisse justifier. Sans URL → llm_memory."""
    if not url:
        return "llm_memory"
    host = (urlparse(url).netloc or "").lower()
    if not host:
        return "llm_memory"
    bare = host.removeprefix("www.")

    if host in _OFFICIAL_DOMAINS or bare in _OFFICIAL_DOMAINS:
        return _OFFICIAL_DOMAINS.get(host) or _OFFICIAL_DOMAINS[bare]
    if any(bare == s or bare.endswith("." + s) for s in _EU_REGULATOR_SUFFIXES):
        return "regulator_filing_eu"
    if _IR_HOST_PATTERN.match(host):
        return "company_ir_official"
    if bare in _PRESS_DOMAINS or any(bare.endswith("." + d) for d in _PRESS_DOMAINS):
        return "financial_press"
    if any(bare == s or bare.endswith("." + s) for s in _REPUTABLE_SUFFIXES):
        return "web_search_reputable"
    return "web_search_generic"


# ── Backends ─────────────────────────────────────────────────────────────────
class SearchBackend(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    async def search(self, query: str, max_results: int) -> list[SearchHit]:
        ...


class ExaBackend(SearchBackend):
    """Exa (nominal) — `POST /search`, header `x-api-key`. `type=auto` laisse Exa arbitrer entre
    recherche neurale et mots-clés. On demande les `contents.text` : une page rapportée avec son
    texte évite un `fetch_url` derrière, donc un tour de boucle et des tokens."""
    name = "exa"
    endpoint = "https://api.exa.ai/search"

    def __init__(self, api_key: str, *, text_chars: int = 2000) -> None:
        self._key = api_key
        self._text_chars = text_chars

    async def search(self, query: str, max_results: int) -> list[SearchHit]:
        payload = {
            "query": query,
            "numResults": max_results,
            "type": "auto",
            "contents": {"text": {"maxCharacters": self._text_chars, "includeHtmlTags": False}},
        }
        async with httpx.AsyncClient(timeout=settings.SEARCH_TIMEOUT_S) as client:
            try:
                r = await client.post(
                    self.endpoint,
                    json=payload,
                    headers={"x-api-key": self._key, "Content-Type": "application/json"},
                )
            except httpx.HTTPError as e:
                raise SearchUnavailable(f"Exa injoignable : {e}") from e
        if r.status_code >= 400:
            raise SearchUnavailable(f"Exa HTTP {r.status_code} : {r.text[:300]}")
        results = (r.json() or {}).get("results") or []
        return [
            SearchHit(
                title=(x.get("title") or "").strip(),
                url=x.get("url") or "",
                snippet=(x.get("summary") or "")[:500],
                published_date=_iso_date(x.get("publishedDate")),
                text=(x.get("text") or None),
            )
            for x in results
            if x.get("url")
        ]


class SerperBackend(SearchBackend):
    """Serper (débordement, ~$1/1000) — SERP Google brute : liens + snippets, pas de contenu.
    Chaque résultat exploitable coûte donc un `fetch_url` de plus qu'avec Exa."""
    name = "serper"
    endpoint = "https://google.serper.dev/search"

    def __init__(self, api_key: str) -> None:
        self._key = api_key

    async def search(self, query: str, max_results: int) -> list[SearchHit]:
        async with httpx.AsyncClient(timeout=settings.SEARCH_TIMEOUT_S) as client:
            try:
                r = await client.post(
                    self.endpoint,
                    json={"q": query, "num": max_results},
                    headers={"X-API-KEY": self._key, "Content-Type": "application/json"},
                )
            except httpx.HTTPError as e:
                raise SearchUnavailable(f"Serper injoignable : {e}") from e
        if r.status_code >= 400:
            raise SearchUnavailable(f"Serper HTTP {r.status_code} : {r.text[:300]}")
        organic = (r.json() or {}).get("organic") or []
        return [
            SearchHit(
                title=(x.get("title") or "").strip(),
                url=x.get("link") or "",
                snippet=(x.get("snippet") or "")[:500],
                published_date=_iso_date(x.get("date")),
            )
            for x in organic[:max_results]
            if x.get("link")
        ]


def get_search_backend() -> SearchBackend:
    """Backend courant d'après la config. Lève `SearchUnavailable` si la clé manque — c'est le
    point où l'absence de recherche devient visible, plutôt que de dégénérer en résultat vide."""
    provider = (settings.SEARCH_PROVIDER or "none").strip().lower()
    if provider == "exa":
        if not settings.EXA_API_KEY:
            raise SearchUnavailable(
                "SEARCH_PROVIDER=exa mais EXA_API_KEY est vide — recherche web indisponible. "
                "Poser la clé dans Coolify (portfolio-backend) ou basculer SEARCH_PROVIDER."
            )
        return ExaBackend(settings.EXA_API_KEY)
    if provider == "serper":
        if not settings.SERPER_API_KEY:
            raise SearchUnavailable("SEARCH_PROVIDER=serper mais SERPER_API_KEY est vide.")
        return SerperBackend(settings.SERPER_API_KEY)
    raise SearchUnavailable(
        f"Aucun backend de recherche web configuré (SEARCH_PROVIDER={provider!r}). "
        "Valeurs supportées : 'exa', 'serper'."
    )


def search_is_configured() -> bool:
    """Vrai si `web_search` peut aboutir. Sert à composer la liste d'outils exposée à l'agent :
    un outil câblé sur un backend absent vaut moins que pas d'outil du tout."""
    try:
        get_search_backend()
        return True
    except SearchUnavailable:
        return False


async def web_search(query: str, max_results: int = 5) -> list[SearchHit]:
    """Recherche web via le backend courant. Lève `SearchUnavailable` (jamais une liste vide muette)."""
    backend = get_search_backend()
    hits = await backend.search(query.strip(), max(1, min(max_results, 10)))
    logger.info("web_search[%s] %r → %d résultat(s)", backend.name, query[:80], len(hits))
    return hits


# ── fetch_url ────────────────────────────────────────────────────────────────
_SKIP_TAGS = {"script", "style", "noscript", "svg", "head", "nav", "footer", "form", "template"}
_BLOCK_TAGS = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article"}
_WS = re.compile(r"[ \t\x0b\f\r]+")
_BLANKS = re.compile(r"\n{3,}")


class _TextExtractor(HTMLParser):
    """Extraction texte en stdlib : on laisse tomber le contenu non textuel et on matérialise les
    ruptures de bloc. Suffisant pour une page IR / un communiqué, et cela évite d'ajouter une
    dépendance (lxml/bs4) à l'image sur un VPS à 84 % de disque."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title: str = ""
        self._skip = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag in _SKIP_TAGS:
            self._skip += 1
        elif tag == "title":
            self._in_title = True
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip:
            self._skip -= 1
        elif tag == "title":
            self._in_title = False
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._in_title and not self.title:
            self.title = data.strip()
        if self._skip:
            return
        text = _WS.sub(" ", data)
        if text.strip():
            self.parts.append(text)

    def text(self) -> str:
        raw = "".join(self.parts)
        lines = [ln.strip() for ln in raw.split("\n")]
        return _BLANKS.sub("\n\n", "\n".join(ln for ln in lines if ln)).strip()


def html_to_text(html: str) -> tuple[str, str]:
    """(titre, texte) d'un document HTML. Sur HTML malformé, on rend ce qui a été parsé avant l'erreur
    plutôt que d'échouer : une page à moitié lue reste exploitable, une exception ne l'est pas."""
    parser = _TextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception as e:  # noqa: BLE001
        logger.debug("html_to_text: parsing interrompu (%s) — rendu partiel", e)
    return parser.title, parser.text()


async def fetch_url(url: str, *, max_chars: Optional[int] = None) -> dict[str, Any]:
    """Récupère une URL et en extrait le texte. Renvoie {url, final_url, status, title, text,
    truncated, content_type}. Lève RuntimeError sur échec réseau/HTTP — remontée telle quelle au
    modèle par la boucle d'outils."""
    limit = max_chars or settings.FETCH_URL_MAX_CHARS
    if not re.match(r"^https?://", url or "", re.IGNORECASE):
        raise ValueError(f"URL invalide (http/https attendu) : {url!r}")

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; portfolio-tracker/2.0; +https://portfolio.jlmvpscode.duckdns.org)",
        "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.8,*/*;q=0.5",
        "Accept-Language": "fr,en;q=0.8",
    }
    async with httpx.AsyncClient(
        timeout=settings.SEARCH_TIMEOUT_S, follow_redirects=True, headers=headers
    ) as client:
        try:
            r = await client.get(url)
        except httpx.HTTPError as e:
            raise RuntimeError(f"fetch_url({url}) : {e}") from e
    if r.status_code >= 400:
        raise RuntimeError(f"fetch_url({url}) : HTTP {r.status_code}")

    ctype = (r.headers.get("content-type") or "").split(";")[0].strip().lower()
    if "html" in ctype or "xml" in ctype or not ctype:
        title, text = html_to_text(r.text)
    elif ctype.startswith("text/") or "json" in ctype:
        title, text = "", r.text.strip()
    else:
        # PDF & binaires : pas d'extraction embarquée (pas de dépendance PDF dans l'image).
        # On le DIT au modèle au lieu de lui rendre du binaire illisible qu'il paraphraserait.
        raise RuntimeError(
            f"fetch_url({url}) : type {ctype!r} non extractible côté serveur — "
            "chercher la version HTML de ce document."
        )

    # Page volumineuse dont on n'extrait presque rien = rendue côté client (SPA). Constaté sur
    # investor.nvidia.com : HTTP 200, <title> correct, 0 caractère de texte. Rendre ce vide comme un
    # succès ferait conclure au modèle que la page ne dit rien, alors qu'elle n'a pas été lue — le
    # même mode de panne silencieux qui a fait écarter SearXNG. On le DIT.
    if len(r.text) > 2000 and len(text) < 200:
        raise RuntimeError(
            f"fetch_url({url}) : page sans texte exploitable ({len(text)} car. extraits de "
            f"{len(r.text)} car. de HTML) — contenu probablement rendu en JavaScript. "
            "Chercher une URL alternative : communiqué de presse, PDF converti, ou dépôt EDGAR."
        )

    truncated = len(text) > limit
    return {
        "url": url,
        "final_url": str(r.url),
        "status": r.status_code,
        "content_type": ctype,
        "title": title,
        "text": text[:limit],
        "truncated": truncated,
        "source_type_max": classify_source_type(str(r.url)),
    }


def _iso_date(value: Optional[str]) -> Optional[str]:
    """Normalise une date de backend en ISO `YYYY-MM-DD`. Rend None si non reconnue — une date
    fausse pénaliserait le score par la décote d'âge (§6.3) sans que personne ne le voie."""
    if not value:
        return None
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", value)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None
