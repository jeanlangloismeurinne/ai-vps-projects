"""
Accès web du search-worker (couche 3) — `web_search` + `fetch_url`, backend-agnostiques.

Deux primitives, aucune logique d'agent :
  - **web_search** : recherche via un backend interchangeable (Exa nominal, Serper en débordement),
    sélectionné par `settings.SEARCH_PROVIDER`. Le contrat de sortie (`SearchHit`) est identique quel
    que soit le backend → basculer Exa ↔ Serper ↔ autre = écrire UNE classe, sans toucher au
    `tools_json` en DB, au prompt du worker, ni à la boucle tool-calling.
  - **fetch_url** : récupère une page (deux chemins : direct, puis cache du backend) et en rend les
    passages qui répondent à la question du mandat — extraction texte en stdlib `html.parser`,
    sélection déléguée à `document_search`. Aucune dépendance ajoutée à l'image.

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
from app.knowledge.document_search import select_relevant

logger = logging.getLogger(__name__)

# Plafond de **récupération** — distinct du plafond de **restitution** (`FETCH_URL_MAX_CHARS`).
# On récupère le document entier pour pouvoir y chercher, et on ne rend que les passages utiles.
# 400 000 caractères couvrent un 10-K complet (NVDA FY2026 : 362 575) et correspondent au budget
# d'embedding de `document_search` (_MAX_CHUNKS_EMBEDDED × _CHUNK_CHARS ≈ 480 000) : au-delà, la
# sélection échantillonnerait de toute façon.
_RETRIEVAL_MAX_CHARS = 400_000


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

    def to_dict(self, ticker_id: Optional[str] = None) -> dict[str, Any]:
        d = {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "published_date": self.published_date,
            "domain": urlparse(self.url).netloc.lower().removeprefix("www."),
            "source_type_max": source_type_max(self.url, ticker_id),
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
# Deux familles y cohabitent, pour la même raison : un organisme qui publie SES PROPRES chiffres est
# primaire pour ce chiffre-là, sans être pour autant une source d'émetteur ni de presse financière.
# Les cabinets d'études de marché (2ᵉ ligne) sont ajoutés le 2026-08-30 : sans eux,
# `marche.croissance_marche_historique` était structurellement infondable. Son plancher avait déjà été
# abaissé à B (`curator.FIELD_PLANCHER_OVERRIDES`), reconnaissant qu'une taille de marché n'est jamais
# une donnée d'émetteur — mais AUCUNE source ne pouvait atteindre ce B, faute d'être classée ici : sur
# MSFT, deux mandats ont rapporté 35 puis 15 URL (Synergy, Canalys, Omdia) et tout est tombé
# sous-plancher en `web_search_generic` (0.50). Le plancher B était la bonne idée appliquée à une table
# incapable de produire un B ; c'est ici que le trou se bouche, pas par une dispense par émetteur.
# B est le bon plafond et pas davantage : ce sont des ESTIMATIONS, l'analyste doit le lire dans le tier.
_REPUTABLE_SUFFIXES = (
    "arxiv.org", "iea.org", "oecd.org", "worldbank.org",
    "srgresearch.com", "canalys.com", "gartner.com", "idc.com",
    "omdia.tech.informa.com", "counterpointresearch.com", "techinsights.com",
)

# ── Domaines d'émetteur, clefés PAR ÉMETTEUR (#31) ───────────────────────────
# `nvidia.com` vivait dans `_REPUTABLE_SUFFIXES` : un fait sur UN émetteur dans une constante
# globale, soit exactement le bug que la convention #31 dit d'attendre au 2ᵉ ticker. Il est arrivé :
# `microsoft.com/en-us/investor/…` était classé `web_search_generic` (0.50) au lieu de
# `company_ir_official` (0.90), parce que Microsoft publie son IR sur un CHEMIN et non sur un
# sous-domaine `ir.` — `_IR_HOST_PATTERN` ne pouvait pas le voir.
#
# Pourquoi un registre écrit à la main plutôt qu'une résolution automatique : EDGAR expose bien
# `website` et `investorWebsite` dans `submissions`, mais les deux sont **vides** — vérifié le
# 2026-08-31 sur NVDA, AAPL, MSFT, GOOGL, AMZN, cinq fois la chaîne vide. Deviner le domaine depuis
# la raison sociale promouvrait un homonyme ou un squatteur à 0.90, soit la sur-qualification que
# #24 retire précisément au modèle. On préfère une entrée à écrire pour chaque émetteur.
#
# Défaut = tuple vide, donc AUCUNE promotion par héritage : un ticker non enregistré n'a pas de
# domaine d'émetteur, ses pages corporate restent `web_search_generic` (même politique que
# `nonblocking_gaps_for` — on refuse un privilège de trop, on n'en accorde pas par défaut).
_ISSUER_DOMAINS: dict[str, tuple[str, ...]] = {
    "NVDA": ("nvidia.com",),
    "MSFT": ("microsoft.com",),
    # Revolution Medicines : IR servi À LA FOIS en sous-domaine (`ir.revmed.com`, que
    # `_IR_HOST_PATTERN` couvre déjà sans registre) et en CHEMIN (`revmed.com/investors`, vérifié
    # 200 le 2026-09-04). C'est ce second cas — le motif Microsoft de #33 — qui rend l'entrée
    # nécessaire : sans elle il tombe en `web_search_generic` 0.50, donc sous plancher, et le champ
    # paraît infondable alors que la source est la meilleure possible.
    "RVMD": ("revmed.com",),
}

_IR_HOST_PATTERN = re.compile(r"^(ir|investor|investors|investorrelations)\.", re.IGNORECASE)
# Segment de chemin dédié à l'information actionnaire. N'est JAMAIS consulté seul : uniquement sur un
# domaine déjà reconnu comme celui de l'émetteur analysé, sans quoi `unblogquelconque.com/investor/`
# monterait à 0.90.
_IR_PATH_PATTERN = re.compile(
    r"(^|/)(ir|investor|investors|investor-relations|investorrelations|shareholder|shareholders)(/|$)",
    re.IGNORECASE,
)


def issuer_domains_for(ticker_id: Optional[str]) -> tuple[str, ...]:
    """Domaines propres à CET émetteur. Ticker inconnu → tuple vide (aucune promotion héritée)."""
    return _ISSUER_DOMAINS.get((ticker_id or "").strip().upper(), ())


def classify_source_type(url: Optional[str], ticker_id: Optional[str] = None) -> str:
    """`source_type` le plus favorable qu'un domaine puisse justifier. Sans URL → llm_memory.

    `ticker_id` est l'émetteur ANALYSÉ, pas celui que la page mentionne : `microsoft.com` n'est le
    site d'émetteur que d'une analyse MSFT. Sur une analyse MSFT, une page `nvidia.com` est le site
    marketing d'un concurrent, pas une source primaire — d'où la clef par émetteur plutôt qu'une
    table globale. Omettre `ticker_id` ne fait jamais monter une source à tort : on retombe sur les
    règles génériques, strictement.
    """
    if not url:
        return "llm_memory"
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    if not host:
        return "llm_memory"
    bare = host.removeprefix("www.")
    mine = issuer_domains_for(ticker_id)
    is_issuer_site = any(bare == d or bare.endswith("." + d) for d in mine)

    if host in _OFFICIAL_DOMAINS or bare in _OFFICIAL_DOMAINS:
        return _OFFICIAL_DOMAINS.get(host) or _OFFICIAL_DOMAINS[bare]
    if any(bare == s or bare.endswith("." + s) for s in _EU_REGULATOR_SUFFIXES):
        return "regulator_filing_eu"
    # Sous-domaine `ir.`/`investor.` : convention assez forte pour valoir sans registre, et on la
    # garde GÉNÉRIQUE à dessein. La restreindre aux émetteurs enregistrés ferait TOMBER
    # `ir.<concurrent>.com` de 0.90 à 0.50 sur toute analyse — un faux trou de couverture créé par un
    # correctif censé en boucher un (#32).
    if _IR_HOST_PATTERN.match(host):
        return "company_ir_official"
    # Chemin IR sur le site de l'émetteur analysé : le cas Microsoft.
    if is_issuer_site and _IR_PATH_PATTERN.search(parsed.path or ""):
        return "company_ir_official"
    if bare in _PRESS_DOMAINS or any(bare.endswith("." + d) for d in _PRESS_DOMAINS):
        return "financial_press"
    # Site de l'émetteur hors section IR (page produit, salle de presse) : réputé sans être de l'IR.
    # C'est le plafond qu'avait `nvidia.com` en dur ; il est désormais rendu au seul émetteur NVDA.
    if is_issuer_site:
        return "web_search_reputable"
    if any(bare == s or bare.endswith("." + s) for s in _REPUTABLE_SUFFIXES):
        return "web_search_reputable"
    return "web_search_generic"


def source_type_max(url: Optional[str], ticker_id: Optional[str] = None) -> str:
    """Plafond affiché au modèle : qualification par domaine, PLUS le registre nominatif.

    ⚠️ Distincte de `classify_source_type`, et la séparation est load-bearing. Le registre accorde
    un standing au couple (source × nature) ; ici la nature n'existe pas encore — une URL dans une
    liste de résultats n'a pas de nature, seule l'entry qu'on en tirera en aura une. On rend donc le
    MEILLEUR cas, ce qui est la définition d'un plafond.

    Replier cette promotion dans `classify_source_type` casserait la règle : le chemin d'écriture
    appelle `classify_source_type` PUIS `source_registry.qualify`, et `qualify` ne promeut que
    depuis `web_search_generic`. Une source déjà promue en amont traverserait `qualify` sans que la
    condition de nature s'applique — une source admise pour l'interprétation gagnerait un standing
    sur la mesure chiffrée, exactement ce que la capacité 2 refuse.
    """
    generique = classify_source_type(url, ticker_id)
    if generique != "web_search_generic":
        return generique  # #33 : une règle spécifique ne resserre jamais la générique au passage
    from .source_registry import plafond_registre  # import tardif : le registre importe common.py
    return plafond_registre(url, ticker_id) or generique


# ── Backends ─────────────────────────────────────────────────────────────────
class SearchBackend(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    async def search(self, query: str, max_results: int) -> list[SearchHit]:
        ...

    async def fetch_contents(self, urls: list[str], *, max_chars: int) -> dict[str, dict[str, Any]]:
        """Texte de pages déjà crawlées par le backend, `url → {title, text}`.

        Optionnel : un backend qui ne sait pas le faire rend `{}` et le repli de `fetch_url` est
        simplement inopérant — jamais une erreur. Sert de **second chemin** quand la récupération
        directe échoue (cf. `fetch_url`)."""
        return {}


class ExaBackend(SearchBackend):
    """Exa (nominal) — `POST /search`, header `x-api-key`. `type=auto` laisse Exa arbitrer entre
    recherche neurale et mots-clés. On demande les `contents.text` : une page rapportée avec son
    texte évite un `fetch_url` derrière, donc un tour de boucle et des tokens."""
    name = "exa"
    endpoint = "https://api.exa.ai/search"
    contents_endpoint = "https://api.exa.ai/contents"

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

    async def fetch_contents(self, urls: list[str], *, max_chars: int) -> dict[str, dict[str, Any]]:
        """`POST /contents` — le texte que le crawler d'Exa a déjà extrait de ces URL.

        Exa crawle depuis sa propre infrastructure : il rend donc des pages que ce VPS ne peut PAS
        récupérer en direct. Deux familles, mesurées sur NVDA (2026-08-23) :
          - **WAF/paywall par réputation d'IP** — `cnbc.com` répond 403 ici quel que soit le
            User-Agent (vérifié : bot déclaré et Chrome desktop donnent le même 403), Exa en rend
            12 189 caractères depuis son cache.
          - **SPA rendue en JavaScript** — `investor.nvidia.com` rend 0 caractère en direct
            (convention #25) ; Exa en rend 29 909.
        Ces deux familles sont exactement celles qui portent les `source_type` au-dessus du plancher
        (`financial_press` 0.75, `company_ir_official` 0.90). Sans ce chemin, le worker ne voyait
        que des blogs à 0.50 et concluait `not_found` sur des sources qui existaient.
        """
        clean = [u for u in urls if u]
        if not clean:
            return {}
        async with httpx.AsyncClient(timeout=settings.SEARCH_TIMEOUT_S * 2) as client:
            try:
                r = await client.post(
                    self.contents_endpoint,
                    json={"urls": clean, "text": {"maxCharacters": max_chars}},
                    headers={"x-api-key": self._key, "Content-Type": "application/json"},
                )
            except httpx.HTTPError as e:
                raise SearchUnavailable(f"Exa /contents injoignable : {e}") from e
        if r.status_code >= 400:
            raise SearchUnavailable(f"Exa /contents HTTP {r.status_code} : {r.text[:300]}")
        out: dict[str, dict[str, Any]] = {}
        for x in (r.json() or {}).get("results") or []:
            url, text = x.get("url"), (x.get("text") or "").strip()
            if url and text:
                out[url] = {"title": (x.get("title") or "").strip(), "text": text}
        return out


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


class _DirectFetchFailed(RuntimeError):
    """Échec de la récupération directe. `recoverable` dit si le backend de recherche vaut la peine
    d'être interrogé : un 404 est une absence réelle (aucun cache ne la comblera), un 403/SPA est un
    problème d'accès depuis ce VPS (Exa, lui, a peut-être la page)."""

    def __init__(self, message: str, *, recoverable: bool) -> None:
        super().__init__(message)
        self.recoverable = recoverable


async def _fetch_url_direct(url: str, ticker_id: Optional[str] = None) -> dict[str, Any]:
    """Récupération directe depuis ce VPS. Lève `_DirectFetchFailed` en qualifiant l'échec.

    Rend le texte **entier** (borné par `_RETRIEVAL_MAX_CHARS`) : la réduction est décidée plus haut,
    par `fetch_url`, qui seul connaît la question posée."""
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
            raise _DirectFetchFailed(f"fetch_url({url}) : {e}", recoverable=True) from e
    if r.status_code >= 400:
        # 404/410 = la page n'existe pas : aucun cache ne la fera exister. Le reste (401 paywall,
        # 403 WAF, 429 quota, 5xx) est un refus opposé à CETTE IP — un autre crawler peut l'avoir.
        raise _DirectFetchFailed(
            f"fetch_url({url}) : HTTP {r.status_code}",
            recoverable=r.status_code not in (404, 410),
        )

    ctype = (r.headers.get("content-type") or "").split(";")[0].strip().lower()
    if "html" in ctype or "xml" in ctype or not ctype:
        title, text = html_to_text(r.text)
    elif ctype.startswith("text/") or "json" in ctype:
        title, text = "", r.text.strip()
    else:
        # PDF & binaires : pas d'extraction embarquée (pas de dépendance PDF dans l'image).
        # On le DIT au modèle au lieu de lui rendre du binaire illisible qu'il paraphraserait.
        raise _DirectFetchFailed(
            f"fetch_url({url}) : type {ctype!r} non extractible côté serveur — "
            "chercher la version HTML de ce document.",
            recoverable=True,
        )

    # Page volumineuse dont on n'extrait presque rien = rendue côté client (SPA). Constaté sur
    # investor.nvidia.com : HTTP 200, <title> correct, 0 caractère de texte. Rendre ce vide comme un
    # succès ferait conclure au modèle que la page ne dit rien, alors qu'elle n'a pas été lue — le
    # même mode de panne silencieux qui a fait écarter SearXNG. On le DIT.
    if len(r.text) > 2000 and len(text) < 200:
        raise _DirectFetchFailed(
            f"fetch_url({url}) : page sans texte exploitable ({len(text)} car. extraits de "
            f"{len(r.text)} car. de HTML) — contenu probablement rendu en JavaScript.",
            recoverable=True,
        )

    return {
        "url": url,
        "final_url": str(r.url),
        "status": r.status_code,
        "content_type": ctype,
        "title": title,
        "text": text[:_RETRIEVAL_MAX_CHARS],
        "source_type_max": classify_source_type(str(r.url), ticker_id),
        "via": "direct",
    }


_EXTRACT_NOTE = {
    "relevance": (
        "EXTRAIT — passages sélectionnés par pertinence sémantique sur {chars_total} caractères "
        "({chunks_selected} passage(s) sur {chunks_total}). Les `[… N caractères omis …]` marquent du "
        "texte NON lu : ne relie pas deux passages séparés par un marqueur comme s'ils se suivaient."
    ),
    "lexical": (
        "EXTRAIT DÉGRADÉ — l'embedding était indisponible, les passages ont été choisis par simple "
        "recouvrement de termes sur {chars_total} caractères. Moins fiable qu'une sélection "
        "sémantique : si l'information attendue manque, elle peut être dans un passage non retenu."
    ),
    "head": (
        "DÉBUT DE DOCUMENT SEULEMENT — {chars_returned} caractères sur {chars_total}. Le reste n'a "
        "PAS été lu : sur un dépôt réglementaire, le corps utile est typiquement au tiers du document. "
        "N'en conclus pas que ce qui manque ici est absent du document."
    ),
}


async def _finalise(
    payload: dict[str, Any], *, query: Optional[str], limit: int
) -> dict[str, Any]:
    """Réduit le texte récupéré aux passages qui répondent à `query`, et le DIT.

    C'est ici que le plafond arbitraire disparaît : au lieu de couper à `limit` caractères depuis le
    début, on cherche dans le document et on rend les passages utiles. Cf. `document_search` pour les
    mesures qui condamnent la troncature en tête (données clés du 10-K NVDA à 37,5 % du texte).
    """
    full = payload.get("text") or ""
    sel = await select_relevant(full, query, max_chars=limit)
    mode = str(sel["mode"])

    payload["text"] = sel["text"]
    payload["truncated"] = int(sel["chars_returned"]) < int(sel["chars_total"])
    payload["extract"] = {
        "mode": mode,
        "query": query or None,
        "chars_total": sel["chars_total"],
        "chars_returned": sel["chars_returned"],
        "chunks_total": sel["chunks_total"],
        "chunks_selected": sel["chunks_selected"],
        "spans": sel["spans"],
    }
    if mode != "whole":
        # Le modèle doit lire un extrait COMME un extrait. Sans cette phrase, il traite les passages
        # retenus comme le document entier et en tire des absences (« le 10-K ne mentionne pas X »)
        # qui ne sont que des effets de la sélection.
        payload["note"] = _EXTRACT_NOTE[mode].format(**{k: sel[k] for k in (
            "chars_total", "chars_returned", "chunks_total", "chunks_selected")})
    return payload


async def fetch_url(
    url: str,
    *,
    max_chars: Optional[int] = None,
    query: Optional[str] = None,
    ticker_id: Optional[str] = None,
) -> dict[str, Any]:
    """Récupère une URL et en extrait les passages qui répondent à `query`. Renvoie {url, final_url,
    status, title, text, truncated, content_type, via, extract, note}. Lève RuntimeError sur échec —
    remontée telle quelle au modèle.

    **Deux chemins de récupération, dans cet ordre.** D'abord la récupération directe. Si elle échoue
    de façon *récupérable* (403 WAF, 401 paywall, SPA vide, PDF), on demande la page au backend de
    recherche, qui l'a souvent déjà crawlée depuis son infrastructure. Sans ce second chemin, les
    seules sources lisibles depuis ce VPS étaient les blogs — ceux, précisément, qui plafonnent à
    0.50 et tombent sous `reliability_min`. Mesuré sur NVDA : 5 entrées produites, 5 rejetées sous
    plancher, la seule source qualifiante du run (CNBC, 0.75) perdue sur un 403.

    **Puis une lecture ciblée, pas une troncature.** Les deux chemins rapportent le document ENTIER
    (`_RETRIEVAL_MAX_CHARS`) ; `query` sert ensuite à n'en rendre que les passages pertinents. Sans
    `query`, on retombe sur la tête du document — le seul choix honnête quand il n'y a pas de
    pertinence à mesurer — et `extract.mode` le dit. `query` n'est pas un argument du modèle mais le
    mandat du worker (cf. `build_tool_executors`) : l'ouvrier sait déjà ce qu'il cherche, et un
    argument de plus est un argument qu'il peut oublier de passer.

    `via` dit lequel des deux chemins a rendu le texte : le modèle doit pouvoir distinguer une page
    lue à l'instant d'un extrait de cache, et le champ remonte jusqu'au log du worker.

    `ticker_id` obéit à la même règle que `query` — c'est l'émetteur du mandat, fermé dans
    l'exécuteur, jamais un argument que le modèle pourrait choisir : il décide quel domaine vaut
    `company_ir_official`, donc le score (§6.3), et le laisser au modèle rouvrirait exactement le
    contournement que #28 a fermé sur les URL.
    """
    limit = max_chars or settings.FETCH_URL_MAX_CHARS
    if not re.match(r"^https?://", url or "", re.IGNORECASE):
        raise ValueError(f"URL invalide (http/https attendu) : {url!r}")

    try:
        return await _finalise(
            await _fetch_url_direct(url, ticker_id), query=query, limit=limit
        )
    except _DirectFetchFailed as direct_error:
        if not direct_error.recoverable:
            raise RuntimeError(str(direct_error)) from direct_error

        try:
            contents = await get_search_backend().fetch_contents(
                [url], max_chars=_RETRIEVAL_MAX_CHARS
            )
        except SearchUnavailable as e:
            logger.info("fetch_url(%s) : repli backend indisponible (%s)", url[:120], e)
            contents = {}
        except Exception as e:  # noqa: BLE001
            logger.warning("fetch_url(%s) : repli backend en échec (%s)", url[:120], e)
            contents = {}

        hit = contents.get(url) or (next(iter(contents.values())) if len(contents) == 1 else None)
        if not hit or not hit.get("text"):
            raise RuntimeError(
                f"{direct_error} — et le backend de recherche n'a pas cette page en cache. "
                "Chercher une URL alternative : communiqué de presse, version HTML, ou dépôt EDGAR."
            ) from direct_error

        text = hit["text"]
        logger.info(
            "fetch_url(%s) : direct en échec (%s) → repli backend, %d car.",
            url[:120], direct_error, len(text),
        )
        return await _finalise(
            {
                "url": url,
                "final_url": url,
                "status": 200,
                "content_type": "text/plain",
                "title": hit.get("title") or "",
                "text": text,
                "source_type_max": classify_source_type(url, ticker_id),
                "via": "search_backend_cache",
                "direct_fetch_error": str(direct_error),
            },
            query=query,
            limit=limit,
        )


def _iso_date(value: Optional[str]) -> Optional[str]:
    """Normalise une date de backend en ISO `YYYY-MM-DD`. Rend None si non reconnue — une date
    fausse pénaliserait le score par la décote d'âge (§6.3) sans que personne ne le voie."""
    if not value:
        return None
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", value)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None
