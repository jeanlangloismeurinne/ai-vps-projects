"""Contrat de sortie du module « Base de connaissance » (M3) : LE LECTEUR COMMUN — chaque document
collecté mis en lecture (lignes numérotées), et les PIÈCES : des extraits vérifiés mot pour mot,
rattachés à leur document et à leurs lignes, jamais modifiés.

Ce que ferait un vrai fonds : on met le rapport annuel en lecture une fois pour toutes, lignes
numérotées ; chaque analyste cite « rapport annuel 2025, ligne 4 512 » ; une citation qui ne se
retrouve pas mot pour mot dans le document n'entre pas au dossier ; ce que vaut la source, c'est le
registre des sources qui le dit, au jour où l'on relit (une source révoquée demain se voit sur les
pièces d'hier).

Ce fichier est le SEUL que le reste du système a le droit d'importer. Il porte :
  · ce que le module rend (`Connaissance`, `Lecture`, `Piece`, `PieceLue`, `Valeur`) et LA fonction
    qui le lit : `lire_connaissance` ; les lignes d'une lecture se lisent par `lire_lignes` ;
  · les gestes : `lire_documents` (la tâche de fond qui met en lecture ce que la collecte a rangé),
    `citer` (établir une pièce), `chercher` (retrouver un passage par les mots) ;
  · le pas déclaré au chef de dossier (`pas_lecture`) ;
  · la vérification d'un extrait (`normaliser`, `extrait_introuvable`, `etablir_extraits`), dont ce
    module est le détenteur unique (#126, #141), partagée avec l'ancien code tant qu'il vit.

Aucune horloge : la date est donnée par l'appelant. Aucun modèle, aucun réseau, aucune dépense.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence

from app.modules.chef_de_dossier.contrat import Pas

from .citation import (  # noqa: F401 — exposés par le contrat (détenteur unique, #46)
    CONTEXTE_MAX_CARS,
    EXTRAIT_MIN_CARS,
    etablir_extraits,
    extrait_introuvable,
    normaliser,
)

VERSION_CONTRAT = "1.0.0"
NOM_DU_MODULE = "connaissance"

LUE = "lue"
IMPOSSIBLE = "impossible"
SANS_OBJET = "sans_objet"


class PieceRefusee(ValueError):
    """La citation ne peut pas devenir une pièce : document inconnu ou pas encore lu, extrait
    introuvable ou ambigu. Le message dit pourquoi (#63 : un refus qui ne dit pas sur quoi condamne
    l'auteur à deviner)."""


@dataclass(frozen=True)
class Lecture:
    """Un document de la collecte mis en lecture par une version du lecteur : `nb_lignes` lignes
    (statut « lue »), ou rien, avec la raison (« impossible », « sans_objet »). Les dates et l'adresse
    sont celles que la collecte a rangées, jamais devinées."""
    empreinte: str
    emetteur: str
    genre: str
    lecteur: str
    statut: str
    nb_lignes: int
    raison: str
    detail: str
    adresse: str
    publie_le: str
    faits_au: str
    lue_le: str


@dataclass(frozen=True)
class Piece:
    """Un extrait d'une lecture, vérifié mot pour mot. `extrait` est le texte du DOCUMENT (forme
    typographique), jamais celui que l'auteur a proposé ; `ligne_debut`/`ligne_fin` le situent (1 =
    première ligne). `periode` : la période du fait cité, quand l'auteur la dit (arbitrage du
    2026-11-21 : celui qui cite dit la période ; vide = non précisée, jamais devinée).
    `autres_lignes` : le même texte figure aussi à ces lignes (relevé sur un communiqué réel : la
    même ligne de chiffre d'affaires dans le tableau comptable et dans le tableau retraité) — la pièce
    retient la première et le dit, le lecteur juge du contexte."""
    identifiant: str
    emetteur: str
    empreinte: str
    lecteur: str
    ligne_debut: int
    ligne_fin: int
    extrait: str
    auteur: str
    periode: str
    cite_le: str
    genre: str
    adresse: str
    publie_le: str
    faits_au: str
    autres_lignes: tuple[int, ...] = ()


@dataclass(frozen=True)
class Valeur:
    """Ce que vaut la source d'une pièce AU JOUR DE LA LECTURE (M1 le dit ; rien n'est rangé avec la
    pièce). `revoquee_le` non vide : la source a été révoquée, la pièce est signalée."""
    admise: bool
    niveau: str
    motif: str
    source: str = ""
    revoquee_le: str = ""
    motif_revocation: str = ""


@dataclass(frozen=True)
class PieceLue:
    piece: Piece
    valeur: Valeur


@dataclass(frozen=True)
class Passage:
    """Une ligne qui répond à une recherche : où elle est, ce qu'elle dit."""
    empreinte: str
    ligne: int
    texte: str
    genre: str
    adresse: str
    publie_le: str
    occurrences: int


@dataclass(frozen=True)
class Connaissance:
    """L'objet de sortie du module, pour un émetteur : la lecture courante de chaque document
    collecté, les documents pas encore lus, et les pièces avec ce que vaut leur source aujourd'hui."""
    emetteur: str
    lectures: tuple[Lecture, ...] = ()
    a_lire: tuple[str, ...] = ()
    pieces: tuple[PieceLue, ...] = ()
    version_contrat: str = VERSION_CONTRAT


# ── Le dépôt (interface ; en mémoire pour les contrôles) ────────────────────────────────────────

class Depot(Protocol):
    """Où le module range. Lectures et pièces sont en AJOUT SEUL : une lecture ne se réécrit pas
    (un lecteur amélioré en ajoute une à côté), une pièce ne se modifie jamais."""

    async def ranger_lecture(self, lecture: Mapping[str, Any], lignes: Sequence[str]) -> bool: ...

    async def lectures(self, emetteur: str) -> Sequence[Mapping[str, Any]]: ...

    async def lignes(self, empreinte: str, lecteur: str) -> Sequence[str] | None: ...

    async def ranger_piece(self, piece: Mapping[str, Any]) -> bool: ...

    async def pieces(self, emetteur: str) -> Sequence[Mapping[str, Any]]: ...


class DepotMemoire:
    """Dépôt en mémoire : celui des contrôles et de la société fictive (aucune base)."""

    def __init__(self) -> None:
        self._lectures: dict[tuple[str, str], dict[str, Any]] = {}
        self._lignes: dict[tuple[str, str], tuple[str, ...]] = {}
        self._pieces: dict[str, dict[str, Any]] = {}

    async def ranger_lecture(self, lecture: Mapping[str, Any], lignes: Sequence[str]) -> bool:
        cle = (lecture["empreinte"], lecture["lecteur"])
        if cle in self._lectures:
            return False
        self._lectures[cle] = dict(lecture)
        self._lignes[cle] = tuple(lignes)
        return True

    async def lectures(self, emetteur: str) -> Sequence[Mapping[str, Any]]:
        return [dict(l) for l in self._lectures.values() if l["emetteur"] == emetteur]

    async def lignes(self, empreinte: str, lecteur: str) -> Sequence[str] | None:
        return self._lignes.get((empreinte, lecteur))

    async def ranger_piece(self, piece: Mapping[str, Any]) -> bool:
        if piece["identifiant"] in self._pieces:
            return False
        self._pieces[piece["identifiant"]] = dict(piece)
        return True

    async def pieces(self, emetteur: str) -> Sequence[Mapping[str, Any]]:
        return [dict(p) for p in self._pieces.values() if p["emetteur"] == emetteur]


def depot_base(connexion: Any) -> Depot:
    """Le dépôt en base, sur une connexion que l'appelant possède (et dont il tient la transaction)."""
    from .depot_base import DepotBase
    return DepotBase(connexion)


# ── LA lecture ────────────────────────────────────────────────────────────────────────────────

async def lire_connaissance(depot: Depot, *, recueil_depot: Any, emetteurs_depot: Any,
                            emetteur: str) -> Connaissance:
    """LA fonction de lecture du contrat : la lecture courante de chaque document que la collecte a
    rangé pour cet émetteur, ceux qui attendent leur lecture, et chaque pièce avec ce que vaut sa
    source AUJOURD'HUI (redemandé à M1 à chaque lecture, jamais rangé)."""
    from . import coeur
    return await coeur.lire_connaissance(depot, recueil_depot=recueil_depot,
                                         emetteurs_depot=emetteurs_depot, emetteur=emetteur)


async def lire_lignes(depot: Depot, empreinte: str, lecteur: str, debut: int = 1,
                      fin: int | None = None) -> tuple[str, ...]:
    """Les lignes [debut, fin] (numérotées à partir de 1) d'une lecture. `KeyError` si elle n'existe pas."""
    lignes = await depot.lignes(empreinte, lecteur)
    if lignes is None:
        raise KeyError(f"aucune lecture {lecteur} du document {empreinte}")
    return tuple(lignes[max(debut, 1) - 1:fin])


# ── Les gestes ────────────────────────────────────────────────────────────────────────────────

async def lire_documents(depot: Depot, *, recueil_depot: Any, emetteur: str, le: str) -> list[dict[str, Any]]:
    """La tâche de fond : met en lecture chaque document que la collecte a rangé pour cet émetteur et
    que la version courante du lecteur n'a pas encore lu. Rend une ligne par document lu."""
    from . import coeur
    return await coeur.lire_documents(depot, recueil_depot=recueil_depot, emetteur=emetteur, le=le)


async def citer(depot: Depot, *, emetteur: str, empreinte: str, extrait: str, auteur: str, le: str,
                periode: str = "") -> Piece:
    """Établit une pièce : l'extrait est vérifié mot pour mot contre la lecture courante du document
    (#126) ; court et unique, il est remplacé par sa ligne (#141). Lève `PieceRefusee` (motif nommé)
    sinon. La même pièce citée deux fois n'est rangée qu'une fois : la seconde rend la première."""
    from . import coeur
    return await coeur.citer(depot, emetteur=emetteur, empreinte=empreinte, extrait=extrait,
                             auteur=auteur, le=le, periode=periode)


async def chercher(depot: Depot, *, emetteur: str, mots: str, genre: str = "") -> list[Passage]:
    """Les lignes des lectures de cet émetteur qui contiennent TOUS les mots demandés (forme
    comparable de la citation), les plus riches en occurrences d'abord. Gratuit, reproductible."""
    from . import coeur
    return await coeur.chercher(depot, emetteur=emetteur, mots=mots, genre=genre)


async def vue_ecran(depot: Depot, *, recueil_depot: Any, emetteurs_depot: Any, emetteur: str) -> dict[str, Any]:
    """Ce que l'écran montre pour un émetteur. Aucun module ne s'appuie sur cette vue."""
    from . import coeur
    return await coeur.vue_ecran(depot, recueil_depot=recueil_depot, emetteurs_depot=emetteurs_depot,
                                 emetteur=emetteur)


# ── Le pas déclaré au chef de dossier (charte, point 8) ────────────────────────────────────────

@dataclass(frozen=True)
class VueLecture:
    """Ce que le pas sait au début du passage (lu par l'appelant) : les documents collectés et ceux
    qui ont déjà leur lecture courante."""
    documents: tuple[str, ...] = ()
    lus: frozenset[str] = field(default_factory=frozenset)


async def vue_lecture(depot: Depot, *, recueil_depot: Any, emetteur: str) -> VueLecture:
    from . import coeur
    return await coeur.vue_lecture(depot, recueil_depot=recueil_depot, emetteur=emetteur)


def pas_lecture(nom: str, vue: VueLecture, *, apres: tuple[str, ...]) -> Pas:
    """Le pas de lecture d'un dossier : après la collecte, il attend que chaque document collecté ait
    sa lecture (ou une lecture impossible, nommée). Il ne dépense rien."""
    from . import coeur
    return coeur.pas_lecture(nom, vue, apres=apres)


__all__ = [
    "VERSION_CONTRAT", "NOM_DU_MODULE", "LUE", "IMPOSSIBLE", "SANS_OBJET", "PieceRefusee", "Lecture",
    "Piece", "Valeur", "PieceLue", "Passage", "Connaissance", "Depot", "DepotMemoire", "depot_base",
    "lire_connaissance", "lire_lignes", "lire_documents", "citer", "chercher", "vue_ecran",
    "VueLecture", "vue_lecture", "pas_lecture", "normaliser", "extrait_introuvable", "etablir_extraits",
    "EXTRAIT_MIN_CARS", "CONTEXTE_MAX_CARS",
]
