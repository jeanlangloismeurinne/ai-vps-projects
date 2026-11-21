"""Contrat du module « Étude » : LES SOCIÉTÉS MISES À L'ÉTUDE ET LE PASSAGE DE LEURS DOSSIERS.

Ce que ferait un vrai fonds : c'est le gérant qui dit quoi analyser ; une fois un titre « mis à
l'étude », l'analyste fait avancer son dossier chaque jour sans qu'on le relance — il relève le
courrier, lit ce qui est arrivé, avance ce qui peut l'être — et ne revient vers le gérant que pour une
décision. Il ne dépense rien sur un dossier que le gérant a mis en pause.

Ce module est le DÉCLENCHEUR du chef de dossier (M3 §2) : vous mettez une société à l'étude
(`mettre_a_l_etude`) ; ensuite une tâche de fond (`traiter_les_dossiers`) passe sur chaque dossier :
elle relève les collectes lancées, fait évaluer les sources inconnues rencontrées, met en lecture les
documents arrivés, puis fait avancer le dossier et range, dans UNE transaction, l'état du dossier et
ce qu'il a lancé. Un dossier non mis à l'étude n'avance jamais ; deux passages simultanés sur un même
dossier : le second ne fait rien.

Ce fichier est le SEUL que l'API et la tâche planifiée importent. Il porte :
  · ce que le module rend (`Etude`, `Passage`, `EtudeLue`) et LA fonction qui le lit : `lire_etudes` ;
  · les gestes : `mettre_a_l_etude`, `passer` (un dossier), `traiter_les_dossiers` (la tâche de fond),
    et les gestes qui lèvent un arrêt du dossier (`enregistrer_acte`, `lever_pause`, `relancer`) ;
  · ce que le passage reçoit du dehors (`Monde` : les dépôts des modules, les outils de collecte,
    l'évaluateur, la transaction) — injecté : sur une société fictive, tout est en mémoire.

Rien ici ne connaît une société, un pays, un formulaire ni un fournisseur.
"""
from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import Any, AsyncContextManager, Callable, Mapping, Protocol, Sequence

VERSION_CONTRAT = "1.0.0"
NOM_DU_MODULE = "etude"

# Ce qu'un passage a fait sur un dossier.
AVANCE = "avance"                 # quelque chose a bougé (un travail relevé, un document lu, un pas)
RIEN_DE_NEUF = "rien_de_neuf"     # passage fait, rien n'a bougé (non journalisé)
DEJA_EN_COURS = "deja_en_cours"   # un autre passage tient ce dossier : celui-ci ne fait rien
NON_ETUDIE = "non_etudie"         # la société n'est pas à l'étude : rien ne se fait
ISSUES = (AVANCE, RIEN_DE_NEUF, DEJA_EN_COURS, NON_ETUDIE)


class GesteRefuse(ValueError):
    """Le geste demandé ne peut pas être fait (société sans fiche, acte non attendu…), motif nommé."""


@dataclass(frozen=True)
class Etude:
    """Une société mise à l'étude : par qui, quand, pourquoi. Jamais modifiée."""
    dossier: str
    mise_le: str
    par: str
    motif: str


@dataclass(frozen=True)
class Passage:
    """Ce qu'un passage a fait sur un dossier : les collectes relevées, les sources évaluées, les
    documents mis en lecture, les pas du dossier (journal de l'état), et l'arrêt où il s'est posé.
    `payant_suspendu` : le dossier était en pause de dépense (ou terminé) ; rien de payant n'a été
    lancé. Les montants du dossier sont ceux de son état (chef de dossier), pas recopiés ici."""
    dossier: str
    le: str
    issue: str
    collectes: tuple[Mapping[str, Any], ...] = ()
    sources: tuple[Mapping[str, Any], ...] = ()
    lectures: tuple[Mapping[str, Any], ...] = ()
    evenements: tuple[str, ...] = ()
    arret: str = ""
    payant_suspendu: bool = False
    detail: str = ""

    def __post_init__(self) -> None:
        if self.issue not in ISSUES:
            raise ValueError(f"issue de passage inconnue : {self.issue!r}")


@dataclass(frozen=True)
class EtudeLue:
    """Ce que le module rend pour une société à l'étude : l'étude, son dernier passage qui a fait
    quelque chose, et l'état de son dossier en clair."""
    etude: Etude
    dernier_passage: Passage | None
    dossier_en_clair: str
    version_contrat: str = VERSION_CONTRAT


# ── Le dépôt du module (interface ; en mémoire pour les contrôles) ────────────────────────────

class Depot(Protocol):
    """Où le module range. Les études et les passages sont en AJOUT SEUL. Le verrou dit qu'un passage
    tient un dossier : `prendre` rend faux si un autre le tient déjà."""

    async def etudes(self) -> Sequence[Mapping[str, Any]]: ...

    async def etude(self, dossier: str) -> Mapping[str, Any] | None: ...

    async def ajouter_etude(self, etude: Mapping[str, Any]) -> bool: ...

    async def noter_passage(self, passage: Mapping[str, Any]) -> None: ...

    async def passages(self, dossier: str) -> Sequence[Mapping[str, Any]]: ...

    async def prendre(self, dossier: str) -> bool: ...

    async def rendre(self, dossier: str) -> None: ...


class DepotMemoire:
    """Dépôt en mémoire : celui des contrôles et de la société fictive (aucune base)."""

    def __init__(self) -> None:
        self._etudes: dict[str, dict[str, Any]] = {}
        self._passages: list[dict[str, Any]] = []
        self._tenus: set[str] = set()

    async def etudes(self) -> Sequence[Mapping[str, Any]]:
        return [dict(e) for _, e in sorted(self._etudes.items())]

    async def etude(self, dossier: str) -> Mapping[str, Any] | None:
        e = self._etudes.get(dossier)
        return None if e is None else dict(e)

    async def ajouter_etude(self, etude: Mapping[str, Any]) -> bool:
        if etude["dossier"] in self._etudes:
            return False            # déjà à l'étude : jamais réécrite
        self._etudes[etude["dossier"]] = dict(etude)
        return True

    async def noter_passage(self, passage: Mapping[str, Any]) -> None:
        self._passages.append(dict(passage))

    async def passages(self, dossier: str) -> Sequence[Mapping[str, Any]]:
        return [dict(p) for p in self._passages if p["dossier"] == dossier]

    async def prendre(self, dossier: str) -> bool:
        if dossier in self._tenus:
            return False
        self._tenus.add(dossier)
        return True

    async def rendre(self, dossier: str) -> None:
        self._tenus.discard(dossier)


def depot_base(connexion: Any) -> Depot:
    """Le dépôt en base (tables `etude_*`), sur une connexion que l'appelant possède."""
    from .depot_base import DepotBase
    return DepotBase(connexion)


# ── Ce que le passage reçoit du dehors ──────────────────────────────────────────────────────────

@contextlib.asynccontextmanager
async def _sans_transaction():
    yield


@dataclass
class Monde:
    """Tout ce dont un passage a besoin, INJECTÉ : en mémoire pour les contrôles, en base (une même
    connexion pour tous les dépôts) pour la tâche planifiée.

    `chef` : le rangement de l'état des dossiers (`ouvrir` / `refermer`, du contrat du chef de
    dossier). `outils` et `evaluateur` : la collecte et l'évaluateur de sources ; absents, rien de
    payant ne peut être lancé, et le passage le dit. `transaction` : ouvre une transaction sur la
    connexion des dépôts (en mémoire : rien)."""
    etude: Depot
    chef: Any
    emetteurs: Any
    recueil: Any
    connaissance: Any
    outils: Any = None
    evaluateur: Any = None
    transaction: Callable[[], AsyncContextManager] = field(default=_sans_transaction)


# ── LA lecture ──────────────────────────────────────────────────────────────────────────────

async def lire_etudes(monde: Monde) -> list[EtudeLue]:
    """LA fonction de lecture du contrat : chaque société à l'étude, son dernier passage qui a fait
    quelque chose, et l'état de son dossier en clair."""
    from . import coeur
    return await coeur.lire_etudes(monde)


# ── Les gestes ────────────────────────────────────────────────────────────────────────────────

async def mettre_a_l_etude(monde: Monde, dossier: str, *, par: str, motif: str, le: str) -> Etude:
    """Vous mettez une société à l'étude. Refusé (motif nommé) si elle n'a pas de fiche : on n'ouvre
    pas de dossier sur une société qu'on n'a pas identifiée. Déjà à l'étude : l'étude d'origine est
    rendue, rien n'est réécrit."""
    from . import coeur
    return await coeur.mettre_a_l_etude(monde, dossier, par=par, motif=motif, le=le)


async def passer(monde: Monde, dossier: str, *, le: str) -> Passage:
    """Un passage sur un dossier : relever, lire, avancer, ranger. Ne lève jamais pour une société :
    ce qui échoue en route est un échec nommé du pas concerné, porté par l'état du dossier."""
    from . import coeur
    return await coeur.passer(monde, dossier, le=le)


async def traiter_les_dossiers(monde: Monde, *, le: str) -> list[Passage]:
    """La tâche de fond : un passage sur chaque société à l'étude, l'une après l'autre."""
    from . import coeur
    return await coeur.traiter_les_dossiers(monde, le=le)


async def enregistrer_acte(monde: Monde, dossier: str, cle: str, *, le: str) -> str:
    """Vous avez accompli l'acte attendu (valider les documents collectés, corriger une identité…).
    Rend l'état du dossier en clair ; le passage suivant fait avancer."""
    from . import coeur
    return await coeur.geste(monde, dossier, "acte", cle=cle, le=le)


async def lever_pause(monde: Monde, dossier: str, *, le: str) -> str:
    """Vous avez vu la dépense et le coût restant : le dossier peut consommer un palier de plus."""
    from . import coeur
    return await coeur.geste(monde, dossier, "pause", le=le)


async def relancer(monde: Monde, dossier: str, *, pas: str | None = None, le: str) -> str:
    """Après un échec répété : vous décidez de réessayer."""
    from . import coeur
    return await coeur.geste(monde, dossier, "relance", pas=pas, le=le)


def lecture_humaine() -> dict[str, bool]:
    """Les interrupteurs de relecture humaine en vigueur (une copie du référentiel)."""
    from . import coeur
    return dict(coeur.referentiel()["lecture_humaine"])


__all__ = [
    "VERSION_CONTRAT", "NOM_DU_MODULE", "AVANCE", "RIEN_DE_NEUF", "DEJA_EN_COURS", "NON_ETUDIE",
    "GesteRefuse", "Etude", "Passage", "EtudeLue", "Depot", "DepotMemoire", "depot_base", "Monde",
    "lire_etudes", "mettre_a_l_etude", "passer", "traiter_les_dossiers", "enregistrer_acte",
    "lever_pause", "relancer", "lecture_humaine",
]
