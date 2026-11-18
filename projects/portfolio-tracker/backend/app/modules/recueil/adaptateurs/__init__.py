"""L'interface d'un adaptateur de collecte, et ce que tous partagent.

Un adaptateur sait OÙ chercher un genre de document pour une famille de sources : un registre
officiel, le site de l'émetteur, le web. Il traduit le genre demandé par SON référentiel (un fichier
JSON à côté de lui) : c'est le seul endroit où un nom de formulaire, une adresse de registre ou un mot
de recherche s'écrit. Ajouter un régulateur, ou les documents fournis à la main, c'est un adaptateur
de plus ; le cœur ne change pas.

Un adaptateur ne range rien et ne qualifie rien : il rend ce qu'il a trouvé (`Trouvaille`), le cœur
range et demande à M1 ce que vaut chaque adresse. Le réseau et le moteur de recherche lui sont
INJECTÉS (`outils.transport`, `outils.moteur`) : sur une société fictive, ils sont simulés.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Awaitable, Callable, Mapping, Protocol, Sequence
from urllib.parse import urljoin

from app.modules.chef_de_dossier.contrat import Depense

from ..contrat import Demande, Provenance

# Familles, dans l'ordre d'autorité : le registre officiel fait foi, le site de l'émetteur ensuite,
# le web à défaut (#133). L'ordre lui-même est au référentiel du cœur.
REGISTRE = "registre"
SITE = "site"
WEB = "web"


@dataclass(frozen=True)
class Lu:
    """Ce qu'une adresse a rendu. `statut` 0 : rien n'a répondu (réseau)."""
    statut: int
    contenu: bytes = b""
    type_media: str = ""


class Transport(Protocol):
    async def lire(self, adresse: str) -> Lu: ...


class Poste(Protocol):
    """Le transport, quand il faut ENVOYER une demande (moteur de recherche, modèle)."""
    async def envoyer(self, adresse: str, corps: Mapping[str, Any], *, en_tetes: Mapping[str, str],
                      delai_s: float = ...) -> Lu: ...


@dataclass(frozen=True)
class Resultat:
    """Un résultat de moteur de recherche : l'adresse, son titre, sa date si le moteur la donne."""
    adresse: str
    titre: str = ""
    publie_le: str = ""


@dataclass(frozen=True)
class Texte:
    """Le texte d'une page tel que le moteur de recherche l'a lu depuis chez lui (une page qui refuse
    la lecture directe, ou rendue en JavaScript)."""
    adresse: str
    texte: str
    titre: str = ""
    publie_le: str = ""


class MoteurInjoignable(RuntimeError):
    """Le moteur de recherche n'a pas répondu (réseau, refus, crédit). L'adaptateur en fait une
    indisponibilité nommée ; il ne la fait jamais passer pour « rien trouvé »."""


class Moteur(Protocol):
    # `categorie` : un genre de pages au vocabulaire du moteur (« actualites »…), vide = toutes.
    async def rechercher(self, requete: str, *, domaines: Sequence[str] = (), depuis: str = "",
                         nombre: int = 5, categorie: str = "") -> tuple[list[Resultat], Depense]: ...

    # Facultatif : un moteur qui ne sait pas rendre le texte d'une page ne l'expose pas.
    # async def contenus(self, adresses: Sequence[str]) -> tuple[list[Texte], Depense]: ...


@dataclass(frozen=True)
class Trouve:
    """Un document trouvé. `contenu` est None quand il est DÉJÀ rangé (`empreinte_connue`) : une
    collecte interrompue ne retélécharge pas ce qu'elle a déjà."""
    provenance: Provenance
    contenu: bytes | None
    type_media: str
    empreinte_connue: str = ""


@dataclass
class Trouvaille:
    """Ce qu'un adaptateur rend pour une demande : des documents, ou une raison (vocabulaire du
    référentiel du cœur) et son détail. `rencontrees` : les adresses vues en chemin (pages d'autres
    sociétés, sources inconnues), que le cœur présente à M1. `depense` : ce que la recherche a coûté."""
    trouves: list[Trouve] = field(default_factory=list)
    raison: str = ""
    detail: str = ""
    depense: Depense = field(default_factory=Depense)
    rencontrees: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Identification:
    """Ce qu'un registre officiel dit de l'identité de l'émetteur (#147). `issue` : « trouvee »,
    « homonyme » (plusieurs sociétés : `candidats`), « inconnue », « injoignable »."""
    issue: str
    registre: str = ""
    raison_sociale: str = ""
    pays: str = ""
    cotations: tuple[tuple[str, str], ...] = ()
    references: tuple[tuple[str, str], ...] = ()
    candidats: tuple[str, ...] = ()
    detail: str = ""


@dataclass(frozen=True)
class Appel:
    """Ce que le cœur donne à un adaptateur pour une demande."""
    demande: Demande
    fiche: Any                      # la fiche de M1 (contrat `emetteurs`)
    genre: Mapping[str, Any]        # l'entrée du genre au référentiel du cœur
    transport: Transport
    moteur: Moteur | None
    # identifiant → {partie: empreinte} des documents de cet émetteur déjà rangés sous cet identifiant
    deja: Callable[[str], Awaitable[Mapping[str, str]]]
    le: str


class Adaptateur(Protocol):
    nom: str
    famille: str

    def sait(self, genre: str) -> bool: ...

    async def chercher(self, appel: Appel) -> Trouvaille: ...


# ── Partagé ─────────────────────────────────────────────────────────────────────────────────

PASSAGERES = (0, 429, 500, 502, 503, 504)


async def lire_avec_reprise(transport: Transport, adresse: str) -> Lu:
    """Une seconde tentative sur une erreur passagère, puis on rend ce qui a été lu : l'appelant
    nomme l'indisponibilité, il ne réessaie pas en boucle."""
    lu = await transport.lire(adresse)
    if lu.statut in PASSAGERES:
        lu = await transport.lire(adresse)
    return lu


def referentiel_de(fichier: str) -> Mapping[str, Any]:
    """Le référentiel JSON d'un adaptateur, à côté de lui."""
    return _charger(str(Path(__file__).with_name(fichier)))


@lru_cache(maxsize=None)
def _charger(chemin: str) -> Mapping[str, Any]:
    return json.loads(Path(chemin).read_text(encoding="utf-8"))


class _Liens(HTMLParser):
    def __init__(self, base: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base = base
        self.liens: list[tuple[str, str]] = []
        self._href: str | None = None
        self._texte: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            self._href = urljoin(self.base, href) if href else None
            self._texte = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._texte.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            self.liens.append((self._href, " ".join("".join(self._texte).split())))
            self._href = None


def liens(html: bytes, base: str) -> list[tuple[str, str]]:
    """Les liens d'une page (adresse absolue, texte du lien), dans l'ordre de la page."""
    p = _Liens(base)
    try:
        p.feed(html.decode("utf-8", errors="replace"))
        p.close()
    except Exception:  # noqa: BLE001 — une page mal formée rend les liens lus jusque-là
        pass
    return list(dict.fromkeys(p.liens))


class _Texte(HTMLParser):
    _MUETS = {"script", "style", "noscript", "svg", "head", "template"}
    _BLOCS = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "table"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.morceaux: list[str] = []
        self._muet = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._MUETS:
            self._muet += 1
        elif tag in self._BLOCS:
            self.morceaux.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._MUETS and self._muet:
            self._muet -= 1

    def handle_data(self, data: str) -> None:
        if not self._muet:
            self.morceaux.append(data)


def texte_de(contenu: bytes) -> str:
    """Le texte lisible d'une page (sans scripts ni styles), lignes vides fusionnées. Sert à LIRE pour
    juger (l'évaluateur) ; le document rangé, lui, reste brut."""
    p = _Texte()
    try:
        p.feed(contenu.decode("utf-8", errors="replace"))
        p.close()
    except Exception:  # noqa: BLE001 — une page mal formée rend le texte lu jusque-là
        pass
    lignes = (" ".join(l.split()) for l in "".join(p.morceaux).splitlines())
    return "\n".join(l for l in lignes if l)


def lisible(lu: Lu, formats_lus: Sequence[str]) -> str:
    """Vide si le contenu est lisible ; sinon la raison, en clair. Un PDF (format non lu) ou une page
    vide n'est jamais rangé comme bon."""
    if not lu.contenu.strip():
        return "contenu vide"
    tm = (lu.type_media or "").split(";")[0].strip().lower()
    if lu.contenu[:5] == b"%PDF-" or tm == "application/pdf":
        return "document PDF : format non lu"
    if tm and not any(tm.startswith(f) for f in formats_lus):
        return f"format non lu ({tm})"
    return ""


def tous() -> list[Adaptateur]:
    """Les adaptateurs construits, dans un ordre stable. Le cœur les range par famille."""
    from .registre_sec import RegistreSec
    from .site import SiteEmetteur
    from .web import Web
    return [RegistreSec(), SiteEmetteur(), Web()]
