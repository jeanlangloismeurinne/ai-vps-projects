"""Contrat de sortie du module « Fiche de l'émetteur et sources » : LA FICHE D'UN ÉMETTEUR.

Ce que ferait un vrai fonds : la direction de la recherche tient une fiche par société — qui elle
est, où elle publie, sa spécialité — et la liste des sources qu'elle tient pour fiables sur elle,
chaque admission datée et motivée. Une source retirée fait relire ce qui s'appuyait dessus.

Ce fichier est le SEUL que le reste du système a le droit d'importer. Il porte :
  · l'objet de sortie versionné (`Fiche`) et LA fonction qui le lit : `lire_fiche` ;
  · ce qu'on peut demander à une fiche, sans rien lire d'autre : `qualifier` (cette adresse
    est-elle une source admise pour cette nature d'information ?) et `pieces_a_signaler` ;
  · les gestes qui écrivent (`etablir_fiche`, `admettre_source`, `revoquer_source`,
    `evaluer_source`) : ce sont des actes datés, motivés et signés, jamais une retouche ;
  · la vue de l'écran (`vue_ecran`) et le pas déclaré au chef de dossier (`pas_fiche`).

Une référence externe (numéro d'un régulateur, code d'une place) est TOUJOURS facultative, et son
nom est une donnée : ce fichier n'en connaît aucune. Rien ici ne connaît une société, un pays, une
place de cotation ni un formulaire.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

from app.modules.chef_de_dossier.contrat import ACTE_HUMAIN, FAIT, Contexte, Pas, Resultat

VERSION_CONTRAT = "1.1.0"   # 1.1.0 (2026-11-14) : sources en suspens, évaluation des sources inconnues
NOM_DU_MODULE = "emetteurs"
NOM_DU_PAS = "fiche_emetteur"

UTILISATEUR = "utilisateur"
PREFIXE_SYSTEME = "systeme:"

PORTEE_GENERALE = "generale"
PREFIXE_PORTEE_SPECIALITE = "specialite:"
PREFIXE_PORTEE_EMETTEUR = "emetteur:"

# Les pages de relations investisseurs des autres sociétés (concurrents, clients, fournisseurs) :
# le système les admet lui-même, sous ce critère écrit et cette signature (arbitrage du 2026-11-14).
CRITERE_PAGES_INVESTISSEURS = "relations_investisseurs_d_une_autre_societe"
AUTEUR_PAGES_INVESTISSEURS = PREFIXE_SYSTEME + "evaluateur_de_sources"

# Une source inconnue est jugée par l'évaluateur de sources (arbitrage du 2026-11-14) : admise par le
# système au-dessus du seuil écrit au référentiel, mise EN SUSPENS en dessous pour votre arbitrage.
AUTEUR_EVALUATEUR = PREFIXE_SYSTEME + "evaluateur_de_sources"

ADMETTRE = "admettre"
REVOQUER = "revoquer"
SUSPENDRE = "suspendre"


class FicheAbsente(LookupError):
    """Aucune fiche n'a été établie pour cet émetteur. Ce n'est pas une fiche vide : c'est un acte
    qui reste à faire, et le chef de dossier s'y arrête."""


class ActeRefuse(ValueError):
    """Le geste demandé enfreint une règle du registre ; le message dit laquelle, en clair."""


class EcritureConcurrente(RuntimeError):
    """Deux écritures ont visé le même rang : la seconde est refusée, rien n'est écrasé."""


@dataclass(frozen=True)
class Reference:
    """Une référence externe de la société : le nom du registre qui l'attribue, et sa valeur."""
    registre: str
    valeur: str


@dataclass(frozen=True)
class Cotation:
    """Où le titre se négocie, et sous quel symbole. Une société non cotée n'en a aucune."""
    place: str
    symbole: str


@dataclass(frozen=True)
class Lieu:
    """Où la société publie. `adresse` : un domaine, suivi ou non d'un chemin (sans protocole)."""
    genre: str
    adresse: str


@dataclass(frozen=True)
class SourceAdmise:
    """Une admission en vigueur qui vaut pour cet émetteur. Elle vaut pour des NATURES
    d'information nommées, jamais pour la source entière."""
    source: str
    portee: str
    natures: tuple[str, ...]
    niveau: str
    auteur: str
    critere: str
    motif: str
    le: str
    rang: int


@dataclass(frozen=True)
class SourceRevoquee:
    """Une révocation en vigueur qui vaut pour cet émetteur, avec ce qu'elle a retiré."""
    source: str
    portee: str
    natures: tuple[str, ...]
    auteur: str
    motif: str
    le: str
    rang: int


@dataclass(frozen=True)
class SourceEnSuspens:
    """Une source que l'évaluateur a jugée sous le seuil : ni admise ni écartée, elle attend votre
    arbitrage. Elle porte ce que l'évaluateur proposait (natures, niveau, critère), la note calculée,
    le seuil, et l'évaluation entière (les publications lues, une réponse motivée par question)."""
    source: str
    portee: str
    natures: tuple[str, ...]
    niveau: str
    critere: str
    note: float
    seuil: float
    motif: str
    le: str
    rang: int
    evaluation: Mapping[str, Any]


@dataclass(frozen=True)
class Reponse:
    """La réponse de l'évaluateur à une question du référentiel, sur une publication : oui ou non,
    et ce qu'il a constaté (jamais vide : une réponse se motive)."""
    question: str
    oui: bool
    constat: str


@dataclass(frozen=True)
class ExempleEvalue:
    """Une publication de la source, lue par l'évaluateur. Son adresse doit relever de la source."""
    adresse: str
    reponses: tuple[Reponse, ...]


@dataclass(frozen=True)
class Evaluation:
    """Ce que l'évaluateur de sources rend sur une source inconnue. Il PROPOSE (critère écrit, natures,
    niveau) et RÉPOND aux questions du référentiel sur quelques publications ; il ne note pas : la
    note, le seuil et la décision sont calculés par le code. `critere` vide : aucun critère écrit ne
    convient — la source va en suspens."""
    source: str
    portee: str
    natures: tuple[str, ...]
    niveau: str
    critere: str
    exemples: tuple[ExempleEvalue, ...]
    evaluateur: str = AUTEUR_EVALUATEUR


@dataclass(frozen=True)
class Fiche:
    """La fiche d'un émetteur : l'objet de sortie du module.

    `emetteur` est l'identifiant MAISON : il ne dépend d'aucun registre extérieur. `sources` et
    `revocations` sont celles qui valent pour CET émetteur (portée générale, sa spécialité s'il en
    a une, lui-même). `en_suspens` : celles qui attendent votre arbitrage (non admises d'ici là).
    `specialite` vide : la société suit le parcours généraliste."""
    emetteur: str
    raison_sociale: str
    pays: str = ""
    cotations: tuple[Cotation, ...] = ()
    references: tuple[Reference, ...] = ()
    lieux: tuple[Lieu, ...] = ()
    specialite: str = ""
    revision: int = 1
    auteur: str = ""
    motif: str = ""
    le: str = ""
    sources: tuple[SourceAdmise, ...] = ()
    revocations: tuple[SourceRevoquee, ...] = ()
    en_suspens: tuple[SourceEnSuspens, ...] = ()
    version_referentiel: str = ""
    version_contrat: str = VERSION_CONTRAT

    def reference(self, registre: str) -> str | None:
        """La valeur de la référence attribuée par ce registre, ou `None` : une référence est
        toujours facultative, et son absence n'est jamais une erreur de la fiche."""
        for r in self.references:
            if r.registre == registre:
                return r.valeur
        return None


@dataclass(frozen=True)
class Qualification:
    """Ce que vaut une adresse, pour une nature d'information, sur cet émetteur."""
    admise: bool
    niveau: str
    motif: str
    source: str = ""


@dataclass(frozen=True)
class Origine:
    """D'où vient une pièce : ce que son détenteur dit au registre pour savoir si elle est touchée
    par une révocation. Le registre ne lit aucune pièce : on lui présente leurs origines."""
    piece: str
    adresse: str
    nature: str


@dataclass(frozen=True)
class Signalement:
    """Une pièce qui s'appuie sur une source révoquée, avec la date et le motif de la révocation."""
    piece: str
    adresse: str
    nature: str
    source: str
    revoquee_le: str
    motif: str


class Depot(Protocol):
    """Où les fiches et le journal des sources se rangent. Deux registres, tous deux en AJOUT
    SEUL : une correction est une révision nouvelle, une révocation est un acte de plus."""

    async def emetteurs(self) -> Sequence[str]: ...

    async def fiches(self, emetteur: str) -> Sequence[Mapping[str, Any]]: ...

    async def ajouter_fiche(self, emetteur: str, revision: int, contenu: Mapping[str, Any]) -> None: ...

    async def actes(self) -> Sequence[Mapping[str, Any]]: ...

    async def ajouter_acte(self, rang: int, acte: Mapping[str, Any]) -> None: ...


class DepotMemoire:
    """Dépôt en mémoire : celui des contrôles et de la société fictive (aucune base)."""

    def __init__(self) -> None:
        self._fiches: dict[str, list[dict[str, Any]]] = {}
        self._actes: list[dict[str, Any]] = []

    async def emetteurs(self) -> Sequence[str]:
        return sorted(self._fiches)

    async def fiches(self, emetteur: str) -> Sequence[Mapping[str, Any]]:
        return [dict(f) for f in self._fiches.get(emetteur, [])]

    async def ajouter_fiche(self, emetteur: str, revision: int, contenu: Mapping[str, Any]) -> None:
        rangees = self._fiches.setdefault(emetteur, [])
        if revision != len(rangees) + 1:
            raise EcritureConcurrente(f"fiche {emetteur} : la révision {revision} n'est pas la suivante")
        rangees.append(dict(contenu))

    async def actes(self) -> Sequence[Mapping[str, Any]]:
        return [dict(a) for a in self._actes]

    async def ajouter_acte(self, rang: int, acte: Mapping[str, Any]) -> None:
        if rang != len(self._actes) + 1:
            raise EcritureConcurrente(f"journal des sources : le rang {rang} n'est pas le suivant")
        self._actes.append(dict(acte))


def depot_base(connexion: Any) -> Depot:
    """Le dépôt en base, sur une connexion que l'appelant possède (et dont il tient la
    transaction). Le module ne sait pas d'où vient la connexion."""
    from .depot_base import DepotBase
    return DepotBase(connexion)


# ── LA lecture ────────────────────────────────────────────────────────────────────────────────

async def lire_fiche(depot: Depot, emetteur: str) -> Fiche:
    """LA fonction de lecture du contrat : la fiche en vigueur de cet émetteur, avec les sources
    admises et révoquées qui valent pour lui. Lève `FicheAbsente` s'il n'en a pas."""
    from . import regles
    return await regles.lire_fiche(depot, emetteur)


# ── Ce qu'on demande à une fiche (fonctions pures : aucune lecture) ──────────────────────────────

def qualifier(fiche: Fiche, adresse: str, nature: str) -> Qualification:
    """Cette adresse est-elle, pour cet émetteur, une source admise pour cette nature
    d'information ? Dans le doute, non — et le motif dit pourquoi."""
    from . import regles
    return regles.qualifier(fiche, adresse, nature)


def pieces_a_signaler(fiche: Fiche, origines: Sequence[Origine]) -> tuple[Signalement, ...]:
    """Parmi ces pièces, celles qui s'appuient sur une source révoquée — et elles seules."""
    from . import regles
    return regles.pieces_a_signaler(fiche, origines)


# ── Les gestes (chacun est un acte daté, motivé, signé) ──────────────────────────────────────────

async def etablir_fiche(depot: Depot, emetteur: str, *, raison_sociale: str, auteur: str, motif: str,
                        le: str, pays: str = "", cotations: Sequence[tuple[str, str]] = (),
                        references: Sequence[tuple[str, str]] = (),
                        lieux: Sequence[tuple[str, str]] = (), specialite: str = "") -> Fiche:
    """Établit la fiche d'un émetteur, ou la corrige : chaque appel ajoute une révision, les
    précédentes restent lisibles. C'est le seul geste nécessaire pour ajouter un titre."""
    from . import regles
    return await regles.etablir_fiche(
        depot, emetteur, raison_sociale=raison_sociale, auteur=auteur, motif=motif, le=le, pays=pays,
        cotations=cotations, references=references, lieux=lieux, specialite=specialite)


async def admettre_source(depot: Depot, *, source: str, portee: str, natures: Sequence[str],
                          niveau: str, auteur: str, motif: str, le: str, critere: str = "") -> int:
    """Admet une source pour des natures d'information nommées. Rend le rang de l'acte au journal."""
    from . import regles
    return await regles.acter_source(
        depot, acte=ADMETTRE, source=source, portee=portee, natures=natures, niveau=niveau,
        auteur=auteur, motif=motif, le=le, critere=critere)


async def revoquer_source(depot: Depot, *, source: str, portee: str, auteur: str, motif: str,
                          le: str) -> int:
    """Révoque une source admise — ou écarte une source en suspens. Les pièces qui s'appuyaient sur
    une source admise seront signalées à la lecture ; une source en suspens n'en fondait aucune."""
    from . import regles
    return await regles.acter_source(
        depot, acte=REVOQUER, source=source, portee=portee, natures=(), niveau="", auteur=auteur,
        motif=motif, le=le, critere="")


async def evaluer_source(depot: Depot, evaluation: Evaluation, *, le: str) -> dict[str, Any]:
    """Range le jugement de l'évaluateur sur une source inconnue. Le code calcule la note (part des
    « oui ») et la compare au seuil du référentiel : au-dessus, le système ADMET la source sous le
    critère proposé ; en dessous (ou trop peu de publications lues, ou aucun critère), il la met EN
    SUSPENS pour votre arbitrage. Rend l'issue (`admise` / `en_suspens`), le rang, la note, le seuil
    et le motif. Une évaluation mal formée (publication d'un autre site, question sans réponse ou
    sans constat) est refusée : elle n'entre pas au journal."""
    from . import regles
    return await regles.evaluer_source(depot, evaluation, le=le)


def page_investisseurs(adresse: str) -> str | None:
    """Le domaine d'une page de relations investisseurs reconnue à son adresse dédiée, ou `None`."""
    from . import regles
    return regles.page_investisseurs(adresse)


async def admettre_pages_investisseurs(depot: Depot, adresses: Sequence[str], *, le: str) -> list[dict[str, Any]]:
    """Le système admet les pages de relations investisseurs des autres sociétés rencontrées dans
    ces adresses (portée générale, critère écrit, signé du système). Une page que l'utilisateur a
    révoquée reste révoquée. Rend une ligne par domaine reconnu : admise, déjà admise, écartée."""
    from . import regles
    return await regles.admettre_pages_investisseurs(depot, adresses, le=le)


# ── L'écran ──────────────────────────────────────────────────────────────────────────────────

async def vue_ecran(depot: Depot, emetteur: str | None = None) -> dict[str, Any]:
    """Ce que l'écran montre, et lui seul : la liste des émetteurs et le journal complet des
    sources ; pour un émetteur, sa fiche, ses révisions passées, ses sources. Aucun module ne
    s'appuie sur cette vue : un module lit `lire_fiche`."""
    from . import regles
    return await regles.vue_ecran(depot, emetteur)


# ── Le pas déclaré au chef de dossier (charte, point 8) ──────────────────────────────────────────

ACTE_ETABLIR_LA_FICHE = "établir la fiche de l'émetteur (qui il est, où il publie, sa spécialité)"


def pas_fiche(fiche: Fiche | None) -> Pas:
    """Le pas de ce module dans le parcours d'un dossier. Il ne dépense rien. Sans fiche, il
    s'arrête en nommant l'acte attendu : c'est l'utilisateur qui dit quoi analyser."""

    def executer(contexte: Contexte) -> Resultat:
        if fiche is None:
            return Resultat(issue=ACTE_HUMAIN, acte=ACTE_ETABLIR_LA_FICHE,
                            motif=f"aucune fiche n'existe pour « {contexte.dossier} »")
        if fiche.emetteur != contexte.dossier:
            raise ValueError(f"fiche de « {fiche.emetteur} » présentée au dossier « {contexte.dossier} »")
        return Resultat(issue=FAIT)

    return Pas(nom=NOM_DU_PAS, module=NOM_DU_MODULE, executer=executer, cout_estime_usd=0.0)
