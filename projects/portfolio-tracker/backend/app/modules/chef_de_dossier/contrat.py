"""Contrat de sortie du chef de dossier : l'ÉTAT D'UN DOSSIER, et ce qu'un module déclare pour y
inscrire son pas.

Ce que ferait un vrai fonds : un analyste tient son dossier ; il ne s'arrête que lorsqu'il lui faut
une décision d'un supérieur, et il dit laquelle. Ici l'analyste responsable est un automate SANS
modèle de langage : à dossier égal il prend toujours la même décision, donc tout passage se rejoue.

Trois familles d'objets :
  · ce qu'un module DÉCLARE (`Pas`) et ce que son pas REND (`Resultat`, `Depense`) ;
  · ce que le chef de dossier REND (`EtatDossier`, avec son `Arret` et son journal) — l'objet de
    sortie versionné, lu par une seule fonction : `lire_etat` ;
  · où l'état se range (`Depot`) : une interface (en mémoire pour les contrôles, en base via
    `depot_base`).

Version 1.1.0 (2026-11-14, arbitrage de l'utilisateur) : un pas peut LANCER un travail qui dure (une
collecte) et rendre « en cours ». Le dossier avance alors sur tout ce qui ne dépend pas de ce
travail ; ce qui en dépend l'attend, sans limite de temps. Ce que ferait un vrai fonds : l'analyste
qui attend des documents avance sur ce qui ne les exige pas ; il n'écrit pas la partie qui en a
besoin avant de les avoir. L'arrêt porte donc TOUTES les attentes du dossier, pas seulement la
première.

Rien ici ne connaît une société, un pays, une place de cotation ni un fournisseur.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Callable, Mapping, Protocol

VERSION_CONTRAT = "1.1.0"

# Issues d'un pas. « indisponible » n'est pas un échec : la source demandée n'existe pas pour ce
# dossier, le pas le NOMME, et le dossier continue avec cette réserve (une société sans dépôt
# réglementaire traverse le parcours sans plantage).
#
# « en_cours » : le pas a LANCÉ un travail qui se poursuit hors de l'automate (une collecte) ; il
# n'est pas fait. Le chef de dossier le suit à chaque passage (`Pas.suivre`) jusqu'à une autre issue,
# et avance en attendant sur ce qui n'en dépend pas.
FAIT = "fait"
INDISPONIBLE = "indisponible"
ACTE_HUMAIN = "acte_humain"
ECHEC = "echec"
EN_COURS = "en_cours"
ISSUES = (FAIT, INDISPONIBLE, ACTE_HUMAIN, ECHEC, EN_COURS)

# Natures d'un pas : « automatique » s'exécute ; « humain » est un acte qui vous revient (valider
# la carte, décider en comité) — le chef de dossier s'y arrête en le nommant, il ne l'exécute jamais.
AUTOMATIQUE = "automatique"
HUMAIN = "humain"

# Motifs d'arrêt.
ARRET_ACTE_HUMAIN = "acte_humain"
ARRET_PAUSE_DEPENSE = "pause_depense"
ARRET_ECHEC_REPETE = "echec_repete"
ARRET_PARCOURS_TERMINE = "parcours_termine"
# Plus rien ne peut avancer, mais un travail est en cours : ce n'est ni une panne ni un acte qui vous
# revient. Le dossier reprend seul au passage suivant, quand le travail a abouti.
ARRET_ATTENTE = "attente"
MOTIFS_ARRET = (ARRET_ACTE_HUMAIN, ARRET_PAUSE_DEPENSE, ARRET_ECHEC_REPETE, ARRET_PARCOURS_TERMINE,
                ARRET_ATTENTE)


def _usd(x: float) -> float:
    """Un montant se range au millionième de dollar : deux additions dans un ordre différent
    donnent le même état, donc le même journal."""
    return round(float(x), 6)


@dataclass(frozen=True)
class Depense:
    """Ce qu'un pas a coûté. Modèles ET recherches web, comptés à part : le coût complet d'un
    dossier n'était pas mesuré tant que le web n'était pas compté."""
    modeles_usd: float = 0.0
    web_usd: float = 0.0

    def __post_init__(self) -> None:
        if self.modeles_usd < 0 or self.web_usd < 0:
            raise ValueError("une dépense n'est jamais négative")
        object.__setattr__(self, "modeles_usd", _usd(self.modeles_usd))
        object.__setattr__(self, "web_usd", _usd(self.web_usd))

    @property
    def total_usd(self) -> float:
        return _usd(self.modeles_usd + self.web_usd)

    def plus(self, autre: "Depense") -> "Depense":
        return Depense(self.modeles_usd + autre.modeles_usd, self.web_usd + autre.web_usd)


@dataclass(frozen=True)
class Resultat:
    """Ce qu'un pas rend au chef de dossier. `motif` est obligatoire dès que l'issue n'est pas
    « fait » : un manque se nomme avec sa cause. `acte` nomme l'acte attendu de vous quand le pas
    ne peut pas continuer seul."""
    issue: str
    depense: Depense = field(default_factory=Depense)
    motif: str = ""
    acte: str = ""

    def __post_init__(self) -> None:
        if self.issue not in ISSUES:
            raise ValueError(f"issue inconnue : {self.issue!r}")
        if self.issue != FAIT and not self.motif.strip():
            raise ValueError(f"une issue « {self.issue} » se motive")
        if self.issue == ACTE_HUMAIN and not self.acte.strip():
            raise ValueError("un acte humain attendu se nomme")


@dataclass(frozen=True)
class Contexte:
    """Ce qu'un pas reçoit : le dossier (identifiant maison de l'émetteur) et les actes déjà
    accomplis. Le reste, il le lit dans les contrats des modules qu'il déclare lire."""
    dossier: str
    actes_accomplis: tuple[str, ...] = ()


@dataclass(frozen=True)
class Pas:
    """Le pas qu'un module déclare au chef de dossier (charte, point 8).

    `apres` : les pas qui doivent être faits avant. `cout_estime_usd` : ce que le module pense
    dépenser — sert à estimer le coût restant jusqu'au comité à chaque pause. `acte` : pour un pas
    humain, l'acte attendu, en mots de gérant. `suivre` : pour un pas qui peut rendre « en cours »,
    ce qui dit où en est le travail lancé (rappelé une fois par passage, jusqu'à une autre issue).
    Un pas qui rend « en cours » sans savoir se suivre échoue : le dossier ne l'attendrait jamais."""
    nom: str
    module: str
    nature: str = AUTOMATIQUE
    apres: tuple[str, ...] = ()
    executer: Callable[[Contexte], Resultat] | None = None
    cout_estime_usd: float = 0.0
    acte: str = ""
    suivre: Callable[[Contexte], Resultat] | None = None

    def __post_init__(self) -> None:
        if not self.nom.strip() or not self.module.strip():
            raise ValueError("un pas a un nom et un module")
        if self.nature not in (AUTOMATIQUE, HUMAIN):
            raise ValueError(f"nature inconnue : {self.nature!r}")
        if self.nature == AUTOMATIQUE and self.executer is None:
            raise ValueError(f"le pas automatique « {self.nom} » n'a rien à exécuter")
        if self.nature == HUMAIN and (self.executer is not None or self.suivre is not None
                                      or not self.acte.strip()):
            raise ValueError(f"le pas humain « {self.nom} » nomme son acte et n'exécute rien")
        if self.cout_estime_usd < 0:
            raise ValueError("un coût estimé n'est jamais négatif")


@dataclass(frozen=True)
class Attente:
    """Une chose que le dossier attend : un acte de votre part (`acte_humain`, avec la `cle` à
    enregistrer), une relance après deux échecs (`echec_repete`), ou un travail en cours (`attente`,
    sans geste : il aboutira seul)."""
    motif: str
    pas: str
    cle: str = ""
    acte: str = ""
    detail: str = ""


@dataclass(frozen=True)
class Arret:
    """Pourquoi le dossier n'avance plus, et ce qu'il faut pour qu'il reparte.

    `cle` identifie l'acte à enregistrer pour lever l'arrêt. `cout_restant_estime_usd` : la somme
    des coûts estimés des pas restants — donnée à CHAQUE arrêt, pour juger du coût total jusqu'au
    comité. `ratio_constate` : dépensé / estimé sur les pas déjà faits (None tant que rien n'était
    estimé) : il dit de combien les estimations se trompent, sans corriger le chiffre à votre place.
    `attentes` : TOUT ce que le dossier attend à cet arrêt (le motif principal en est la première
    chose qui vous revient) — plusieurs branches du parcours peuvent attendre en même temps."""
    motif: str
    pas: str = ""
    cle: str = ""
    acte: str = ""
    detail: str = ""
    depense_totale_usd: float = 0.0
    cout_restant_estime_usd: float = 0.0
    ratio_constate: float | None = None
    attentes: tuple[Attente, ...] = ()


@dataclass(frozen=True)
class LigneJournal:
    rang: int
    pas: str
    evenement: str
    modeles_usd: float = 0.0
    web_usd: float = 0.0
    detail: str = ""


@dataclass(frozen=True)
class EtatDossier:
    """L'état d'un dossier : l'objet de sortie du chef de dossier.

    Immuable : chaque geste rend un NOUVEL état. Aucune date n'y entre (deux passages sur le même
    dossier rendent le même état, octet pour octet) ; l'horodatage est l'affaire du dépôt.
    `en_cours` : (pas, motif) des travaux lancés et pas encore aboutis. `demandes` : (pas, clé, acte)
    des actes qu'un pas a demandés en cours de route et que vous n'avez pas encore accomplis."""
    dossier: str
    faits: tuple[str, ...] = ()
    reserves: tuple[tuple[str, str], ...] = ()
    en_cours: tuple[tuple[str, str], ...] = ()
    demandes: tuple[tuple[str, str, str], ...] = ()
    actes_accomplis: tuple[str, ...] = ()
    echecs: tuple[tuple[str, int], ...] = ()
    depense: Depense = field(default_factory=Depense)
    depense_par_pas: tuple[tuple[str, float], ...] = ()
    depense_acquittee_usd: float = 0.0
    journal: tuple[LigneJournal, ...] = ()
    arret: Arret | None = None
    version_contrat: str = VERSION_CONTRAT

    def vers_dict(self) -> dict:
        return {
            "version_contrat": self.version_contrat,
            "dossier": self.dossier,
            "faits": list(self.faits),
            "reserves": [list(r) for r in self.reserves],
            "en_cours": [list(e) for e in self.en_cours],
            "demandes": [list(d) for d in self.demandes],
            "actes_accomplis": list(self.actes_accomplis),
            "echecs": [list(e) for e in self.echecs],
            "depense": {"modeles_usd": self.depense.modeles_usd, "web_usd": self.depense.web_usd},
            "depense_par_pas": [list(d) for d in self.depense_par_pas],
            "depense_acquittee_usd": self.depense_acquittee_usd,
            "journal": [vars(ligne).copy() for ligne in self.journal],
            "arret": None if self.arret is None else asdict(self.arret),
        }

    @staticmethod
    def depuis_dict(d: Mapping) -> "EtatDossier":
        version = d.get("version_contrat")
        if version != VERSION_CONTRAT:
            # Un état d'une autre version ne se lit pas « au mieux » : il se refuse, nommément.
            raise ValueError(f"état de dossier en version {version!r}, attendu {VERSION_CONTRAT!r}")
        arret = d.get("arret")
        return EtatDossier(
            dossier=d["dossier"],
            faits=tuple(d["faits"]),
            reserves=tuple((p, m) for p, m in d["reserves"]),
            en_cours=tuple((p, m) for p, m in d["en_cours"]),
            demandes=tuple((p, c, a) for p, c, a in d["demandes"]),
            actes_accomplis=tuple(d["actes_accomplis"]),
            echecs=tuple((p, int(n)) for p, n in d["echecs"]),
            depense=Depense(**d["depense"]),
            depense_par_pas=tuple((p, float(x)) for p, x in d["depense_par_pas"]),
            depense_acquittee_usd=float(d["depense_acquittee_usd"]),
            journal=tuple(LigneJournal(**ligne) for ligne in d["journal"]),
            arret=None if arret is None else Arret(
                **{**arret, "attentes": tuple(Attente(**x) for x in arret["attentes"])}),
        )


class EcritureConcurrente(RuntimeError):
    """Deux passages ont voulu ranger l'état du même dossier depuis la même lecture : le second est
    refusé, rien n'est écrasé."""


class Depot(Protocol):
    """Où l'état d'un dossier se range. Le chef de dossier possède ce rangement, personne d'autre
    n'y lit : on passe par `lire_etat`."""

    def charger(self, dossier: str) -> Mapping | None: ...

    def ranger(self, dossier: str, etat: Mapping) -> None: ...


class DepotMemoire:
    """Dépôt en mémoire : celui des contrôles et de la société fictive (aucune base, aucune dépense)."""

    def __init__(self) -> None:
        self._etats: dict[str, dict] = {}

    def charger(self, dossier: str) -> Mapping | None:
        return self._etats.get(dossier)

    def ranger(self, dossier: str, etat: Mapping) -> None:
        self._etats[dossier] = dict(etat)


def depot_base(connexion):
    """Le rangement en base, sur une connexion que l'appelant possède : `ouvrir` charge l'état dans
    un `DepotMemoire`, `refermer` le range (refus si la base a bougé entre-temps)."""
    from .depot_base import DepotBase
    return DepotBase(connexion)


def lire_etat(depot: Depot, dossier: str) -> EtatDossier:
    """LA fonction de lecture du contrat : l'état du dossier, ou un état vierge (« titre entré »)
    s'il n'a jamais avancé."""
    brut = depot.charger(dossier)
    return EtatDossier(dossier=dossier) if brut is None else EtatDossier.depuis_dict(brut)
