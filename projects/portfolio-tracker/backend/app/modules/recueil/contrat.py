"""Contrat de sortie du module « Collecte de sources » (M2) : LE RECUEIL D'UN ÉMETTEUR — à chaque
demande, des documents bruts avec leur origine, ou une indisponibilité nommée.

Ce que ferait un vrai fonds : la documentation reçoit une demande de l'analyste (« les derniers
comptes annuels de cette société », « ses annonces importantes depuis le 1er août ») et rend les
documents eux-mêmes, avec leur provenance, ou répond « ça n'existe pas » en disant pourquoi. Elle
sait où chaque société publie (la fiche, M1) et ne fait pas confiance à une source qu'elle ne connaît
pas sans la faire agréer. Elle ne lit pas les documents pour l'analyste : elle les trouve, les date,
les range tels quels.

Ce fichier est le SEUL que le reste du système a le droit d'importer. Il porte :
  · ce qu'on demande (`Demande` : un GENRE de document, jamais un formulaire) ;
  · ce que le module rend (`Recueil`, `Reponse`, `Document`, `Indisponibilite`) et LA fonction qui le
    lit : `lire_recueil` ; le contenu brut d'un document se lit par `lire_contenu` ;
  · les gestes : `collecter` (une demande), `traiter_les_travaux` (la tâche de fond qui répond aux
    demandes lancées), `evaluer_les_sources_rencontrees` ;
  · le pas déclaré au chef de dossier (`pas_collecte`) et ce qu'il laisse à ranger (`Envoi`).

Rien ici ne connaît un formulaire, un registre, une société ni un pays : le genre de document est
traduit par l'adaptateur qui sait où le chercher (`adaptateurs/`, avec son propre référentiel).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Mapping, Protocol, Sequence

from app.modules.chef_de_dossier.contrat import (
    ECHEC,
    EN_COURS,
    FAIT,
    INDISPONIBLE,
    Contexte,
    Depense,
    Pas,
    Resultat,
)

VERSION_CONTRAT = "1.0.0"
NOM_DU_MODULE = "recueil"

# Qui signe ce que la collecte écrit chez M1 : la révision d'identité tirée d'un registre (#147).
# « documentation » n'est pas un rôle qui utilise les sources : elle ne les qualifie pas, elle range.
AUTEUR_DOCUMENTATION = "systeme:documentation"

# Statuts d'une demande lancée (la collecte est un travail suivi, #146).
LANCEE = "lancee"
REPONDUE = "repondue"
ECHOUEE = "echouee"
ESSAIS_PAR_DEMANDE = 2   # un échec d'infrastructure est relancé une fois, puis remonte


class DemandeRefusee(ValueError):
    """La demande elle-même est mal formée (genre inconnu, date illisible) : ce n'est pas une
    indisponibilité de la société, c'est une erreur de celui qui demande."""


@dataclass(frozen=True)
class Demande:
    """Ce qu'un module demande : un GENRE de document (au référentiel du module), pour un émetteur
    (identifiant maison), depuis une date pour les genres qui s'étendent dans le temps, ou à une
    adresse pour une page précise."""
    genre: str
    emetteur: str
    depuis: str = ""
    adresse: str = ""

    @property
    def cle(self) -> str:
        return f"{self.emetteur}|{self.genre}|{self.depuis}|{self.adresse}"


@dataclass(frozen=True)
class Provenance:
    """D'où vient un document. `adaptateur` : qui l'a trouvé ; `registre` : le registre officiel
    qui le tient (vide hors registre) ; `identifiant` : son numéro chez ce registre (ou son adresse) ;
    `partie` : la pièce du dépôt (le document principal, une pièce jointe) ; `publie_le` : date de
    publication (vide si la page ne la dit pas — jamais devinée) ; `faits_au` : date des faits
    couverts ; `remplace` : l'identifiant du document qu'il amende ; `mention` : ce qu'il faut savoir
    pour s'en servir (un prospectus qui tient lieu de comptes annuels)."""
    adaptateur: str
    adresse: str
    registre: str = ""
    identifiant: str = ""
    partie: str = ""
    publie_le: str = ""
    faits_au: str = ""
    remplace: str = ""
    mention: str = ""


@dataclass(frozen=True)
class Qualification:
    """Ce que M1 disait de l'adresse du document, pour la nature d'information du genre, AU JOUR de
    la collecte. Un document d'une source non admise est gardé, marqué, jamais présenté comme admis."""
    admise: bool
    niveau: str
    motif: str
    source: str = ""


@dataclass(frozen=True)
class Document:
    """Un document rangé : brut, jamais modifié, identifié par l'empreinte de son contenu."""
    empreinte: str
    emetteur: str
    genre: str
    provenance: Provenance
    type_media: str
    taille: int
    qualification: Qualification
    collecte_le: str


@dataclass(frozen=True)
class Indisponibilite:
    """Une demande à laquelle rien n'a répondu, avec sa raison (vocabulaire du référentiel) et les
    adaptateurs essayés, chacun avec ce qu'il a constaté."""
    genre: str
    emetteur: str
    raison: str
    detail: str
    essais: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Reponse:
    """La réponse à une demande : des documents, ou une indisponibilité — jamais les deux vides."""
    demande: Demande
    documents: tuple[Document, ...]
    indisponibilite: Indisponibilite | None
    depense: Depense
    collecte_le: str
    # L'acte qui vous revient pour que cette demande aboutisse (un homonyme au registre : #147).
    acte_attendu: str = ""
    # Ce que la consultation du registre a fait à la fiche (révision d'identité), s'il y a lieu.
    identite: Mapping[str, Any] = field(default_factory=dict)
    # Les sources essayées AVANT celle qui a répondu, et ce qu'elles ont dit (un PDF non lu sur le
    # site, trouvé ensuite sur le web) : la trace reste, même quand la demande aboutit.
    essais: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.documents and self.indisponibilite is None:
            raise ValueError("une réponse sans document nomme son indisponibilité")
        if self.documents and self.indisponibilite is not None:
            raise ValueError("une réponse qui rend des documents n'est pas indisponible")


@dataclass(frozen=True)
class Recueil:
    """L'objet de sortie du module : pour un émetteur, la dernière réponse à chacune de ses
    demandes, les demandes encore en cours, et la dépense de collecte."""
    emetteur: str
    reponses: tuple[Reponse, ...] = ()
    en_cours: tuple[Demande, ...] = ()
    depense: Depense = field(default_factory=Depense)
    version_contrat: str = VERSION_CONTRAT


# ── Le dépôt (interface ; en mémoire pour les contrôles) ────────────────────────────────────────

class Depot(Protocol):
    """Où le module range. Les documents et les réponses sont en AJOUT SEUL : un document ne se
    modifie pas, une réponse nouvelle s'ajoute à la précédente."""

    async def document(self, empreinte: str) -> Mapping[str, Any] | None: ...

    async def contenu(self, empreinte: str) -> bytes | None: ...

    async def ranger_document(self, fiche_document: Mapping[str, Any], contenu: bytes) -> bool: ...

    async def parties_rangees(self, emetteur: str, adaptateur: str, identifiant: str) -> Mapping[str, str]: ...

    async def ajouter_reponse(self, reponse: Mapping[str, Any]) -> None: ...

    async def reponses(self, emetteur: str) -> Sequence[Mapping[str, Any]]: ...

    async def travaux(self, emetteur: str | None = None) -> Sequence[Mapping[str, Any]]: ...

    async def ecrire_travail(self, travail: Mapping[str, Any]) -> None: ...

    async def sources_rencontrees(self) -> Sequence[Mapping[str, Any]]: ...

    async def noter_source_rencontree(self, ligne: Mapping[str, Any]) -> None: ...

    async def marquer_source(self, source: str, champs: Mapping[str, Any]) -> None: ...


class DepotMemoire:
    """Dépôt en mémoire : celui des contrôles et de la société fictive (aucune base)."""

    def __init__(self) -> None:
        self._documents: dict[str, dict[str, Any]] = {}
        self._contenus: dict[str, bytes] = {}
        self._reponses: list[dict[str, Any]] = []
        self._travaux: dict[str, dict[str, Any]] = {}
        self._sources: dict[str, dict[str, Any]] = {}

    async def document(self, empreinte: str) -> Mapping[str, Any] | None:
        d = self._documents.get(empreinte)
        return None if d is None else dict(d)

    async def contenu(self, empreinte: str) -> bytes | None:
        return self._contenus.get(empreinte)

    async def ranger_document(self, fiche_document: Mapping[str, Any], contenu: bytes) -> bool:
        e = fiche_document["empreinte"]
        if e in self._documents:
            return False            # déjà rangé : jamais réécrit
        self._documents[e] = dict(fiche_document)
        self._contenus[e] = bytes(contenu)
        return True

    async def parties_rangees(self, emetteur: str, adaptateur: str, identifiant: str) -> Mapping[str, str]:
        return {d["provenance"]["partie"]: e for e, d in self._documents.items()
                if identifiant and (d["emetteur"], d["provenance"]["adaptateur"],
                                    d["provenance"]["identifiant"]) == (emetteur, adaptateur, identifiant)}

    async def ajouter_reponse(self, reponse: Mapping[str, Any]) -> None:
        self._reponses.append(dict(reponse))

    async def reponses(self, emetteur: str) -> Sequence[Mapping[str, Any]]:
        return [dict(r) for r in self._reponses if r["demande"]["emetteur"] == emetteur]

    async def travaux(self, emetteur: str | None = None) -> Sequence[Mapping[str, Any]]:
        return [dict(t) for t in self._travaux.values()
                if emetteur is None or t["demande"]["emetteur"] == emetteur]

    async def ecrire_travail(self, travail: Mapping[str, Any]) -> None:
        self._travaux[travail["cle"]] = dict(travail)

    async def sources_rencontrees(self) -> Sequence[Mapping[str, Any]]:
        return [dict(s) for s in self._sources.values()]

    async def noter_source_rencontree(self, ligne: Mapping[str, Any]) -> None:
        anc = self._sources.get(ligne["source"])
        if anc is None:
            self._sources[ligne["source"]] = dict(ligne)
        else:  # une source déjà notée garde son état ; seules ses adresses s'ajoutent
            vues = list(dict.fromkeys(list(anc["adresses"]) + list(ligne["adresses"])))
            self._sources[ligne["source"]] = {**anc, "adresses": vues}

    async def marquer_source(self, source: str, champs: Mapping[str, Any]) -> None:
        self._sources[source] = {**self._sources[source], **dict(champs)}


def depot_base(connexion: Any) -> Depot:
    """Le dépôt en base (tables `recueil_*`, migration 064), sur une connexion que l'appelant
    possède (et dont il tient la transaction). Le module ne sait pas d'où vient la connexion."""
    from .depot_base import DepotBase
    return DepotBase(connexion)


# ── Ce que la collecte reçoit du dehors (injecté : les contrôles le simulent) ─────────────────

class Outils(Protocol):
    """Ce dont les adaptateurs ont besoin pour atteindre le monde. Réseau et moteur de recherche
    sont INJECTÉS : sur une société fictive, ils sont simulés, sans réseau ni dépense."""
    transport: Any
    moteur: Any


# L'évaluateur de sources (M1, #145) : un rôle distinct de celui qui collecte. Il reçoit la source
# et les adresses de publications rencontrées, rend l'`Evaluation` de M1 et ce qu'il a dépensé.
Evaluateur = Callable[[str, Sequence[str]], Awaitable[tuple[Any, Depense]]]


# ── LA lecture ──────────────────────────────────────────────────────────────────────────────

async def lire_recueil(depot: Depot, emetteur: str) -> Recueil:
    """LA fonction de lecture du contrat : la dernière réponse à chaque demande de cet émetteur,
    ses demandes en cours, et ce que sa collecte a dépensé."""
    from . import coeur
    return await coeur.lire_recueil(depot, emetteur)


async def lire_contenu(depot: Depot, empreinte: str) -> bytes:
    """Le contenu brut d'un document rangé, tel qu'il a été collecté. `KeyError` s'il n'existe pas."""
    brut = await depot.contenu(empreinte)
    if brut is None:
        raise KeyError(f"aucun document d'empreinte {empreinte}")
    return brut


# ── Les gestes ────────────────────────────────────────────────────────────────────────────────

async def collecter(demande: Demande, *, depot: Depot, emetteurs_depot: Any, outils: Outils,
                    le: str) -> Reponse:
    """Répond à une demande : interroge les adaptateurs qui savent ce genre, dans l'ordre du
    référentiel (le registre officiel, puis le site de l'émetteur, puis le web), range les documents
    trouvés, et rend la réponse. Ne lève jamais pour une société : une société sans numéro de
    registre, non cotée ou sans fiche reçoit une indisponibilité nommée."""
    from . import coeur
    return await coeur.collecter(demande, depot=depot, emetteurs_depot=emetteurs_depot, outils=outils, le=le)


async def traiter_les_travaux(*, depot: Depot, emetteurs_depot: Any, outils: Outils, le: str,
                              emetteur: str | None = None) -> list[dict[str, Any]]:
    """La tâche de fond : répond à chaque demande lancée et pas encore répondue (une collecte
    interrompue reprend là ; ce qui est déjà rangé n'est pas recollecté). Rend une ligne par demande
    traitée."""
    from . import coeur
    return await coeur.traiter_les_travaux(depot=depot, emetteurs_depot=emetteurs_depot, outils=outils,
                                           le=le, emetteur=emetteur)


async def evaluer_les_sources_rencontrees(*, depot: Depot, emetteurs_depot: Any, evaluateur: Evaluateur,
                                          le: str) -> list[dict[str, Any]]:
    """Présente à l'évaluateur chaque source inconnue rencontrée en collectant, et range son jugement
    chez M1 (admise au seuil, en suspens dessous). La collecte n'attend pas ce verdict."""
    from . import coeur
    return await coeur.evaluer_les_sources_rencontrees(depot=depot, emetteurs_depot=emetteurs_depot,
                                                       evaluateur=evaluateur, le=le)


async def vue_ecran(depot: Depot, emetteur: str) -> dict[str, Any]:
    """Ce que l'écran montre pour un émetteur : demandes, documents (origine, qualification, date),
    indisponibilités et leur raison, dépense. Aucun module ne s'appuie sur cette vue."""
    from . import coeur
    return await coeur.vue_ecran(depot, emetteur)


# ── Le pas déclaré au chef de dossier (charte, point 8 ; #146) ─────────────────────────────────

@dataclass
class Envoi:
    """Ce que le pas a décidé pendant un passage du chef de dossier et que l'appelant range ensuite,
    dans la même transaction que l'état du dossier : les demandes à lancer, et la dépense de
    collecte désormais déclarée au chef de dossier. Le pas lui-même n'écrit rien."""
    a_lancer: list[Demande] = field(default_factory=list)
    declare: dict[str, Depense] = field(default_factory=dict)
    actes_traites: dict[str, int] = field(default_factory=dict)
    # Le pas d'évaluation des sources : sources à représenter à l'évaluateur, dépense déclarée.
    sources_a_relancer: list[str] = field(default_factory=list)
    declare_sources: dict[str, Depense] = field(default_factory=dict)


@dataclass(frozen=True)
class VueTravaux:
    """Ce que les pas savent des travaux de collecte et des sources rencontrées au début du passage
    (lu par l'appelant)."""
    travaux: Mapping[str, Mapping[str, Any]]
    sources: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)


async def vue_travaux(depot: Depot, emetteur: str) -> VueTravaux:
    return VueTravaux({t["cle"]: t for t in await depot.travaux(emetteur)},
                      {s["source"]: s for s in await depot.sources_rencontrees() if s["emetteur"] == emetteur})


async def ranger_envoi(depot: Depot, envoi: Envoi) -> None:
    """Range ce que le pas a décidé : lance les demandes, note la dépense déclarée."""
    from . import coeur
    await coeur.ranger_envoi(depot, envoi)


def pas_collecte(nom: str, demandes: Sequence[Demande], vue: VueTravaux, envoi: Envoi, *,
                 apres: tuple[str, ...] = (), cout_estime_usd: float = 0.0) -> Pas:
    """Le pas de collecte d'un dossier. À son lancement il demande les documents (rangés dans
    `envoi`) et rend « en cours » ; le chef de dossier le suit à chaque passage jusqu'à ce que toutes
    les demandes aient répondu : « fait », ou « indisponible » si l'une au moins n'a rien rendu (la
    réserve dit lesquelles et pourquoi). Chaque passage déclare la dépense de collecte nouvelle."""
    from . import coeur
    return coeur.pas_collecte(nom, demandes, vue, envoi, apres=apres, cout_estime_usd=cout_estime_usd)


def pas_evaluation(nom: str, emetteur: str, vue: VueTravaux, envoi: Envoi, *, apres: tuple[str, ...] = (),
                   cout_estime_usd: float = 0.0) -> Pas:
    """Le pas qui suit l'évaluation des sources inconnues que la collecte de ce dossier a
    rencontrées. Personne n'a à en dépendre : le dossier avance pendant que l'évaluateur juge (#145,
    #146). Il reste « en cours » tant qu'une source attend son jugement, déclare ce que l'évaluateur
    a coûté, et échoue (motif nommé) quand l'évaluateur a planté deux fois sur une source."""
    from . import coeur
    return coeur.pas_evaluation(nom, emetteur, vue, envoi, apres=apres, cout_estime_usd=cout_estime_usd)


__all__ = [
    "pas_evaluation",
    "VERSION_CONTRAT", "Demande", "Provenance", "Qualification", "Document", "Indisponibilite",
    "Reponse", "Recueil", "Depot", "DepotMemoire", "depot_base", "lire_recueil", "lire_contenu", "collecter",
    "traiter_les_travaux", "evaluer_les_sources_rencontrees", "vue_ecran", "pas_collecte", "Envoi",
    "VueTravaux", "vue_travaux", "ranger_envoi", "DemandeRefusee", "Contexte", "Resultat", "FAIT",
    "INDISPONIBLE", "EN_COURS", "ECHEC",
]
