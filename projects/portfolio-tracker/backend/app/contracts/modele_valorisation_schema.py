"""Contrat du MODÈLE DE VALORISATION propre à une entreprise (#97, roadmap 05 capacité 4 bis).

CE QUE FERAIT UN VRAI FONDS — ET CE QUE L'UTILISATEUR A ARBITRÉ (2026-09-29)
---------------------------------------------------------------------------
À l'initiation, l'analyste construit un modèle PROPRE au dossier ; le directeur de la recherche le
signe ; la mécanique est conservée d'une révision à l'autre. Ce contrat est ce que l'agent PROPOSE et
ce que le comité SIGNE — cinq pièces, chacune tenue par un arbitrage :

  • `methodologie` — la mécanique DÉCRITE en prose (#96 : « il faut que l'agent décrive la mécanique
    qu'il va utiliser »), et `motif_de_la_forme` — pourquoi cette forme de fourchette.
  • `segments` — le découpage du marché (#96 : « charge à l'agent de bien segmenter le marché »).
    Un segment déclaré qu'aucune hypothèse ne chiffre est REFUSÉ : ce serait un découpage de façade.
  • `hypotheses` — le TABLEAU que le comité juge (#96 : « chiffrées et sourcées »). Chaque ligne dit
    d'où vient son chiffre, et il n'y a que TROIS origines (#97, arbitrage « jugement ancré ») :
      - `piece` : une ou plusieurs pièces du dossier ;
      - `reponse_reprise` : une réponse déjà contrôlée d'une autre méthodologie (le coût du capital
        de qf_1 — un seul chiffre par dossier, #95) ; elle se met à jour d'elle-même ;
      - `jugement` : un pari de l'analyste, admis SEULEMENT ancré sur un taux de base sourcé (le
        taux historique de succès d'une phase 2 en oncologie) avec l'écart JUSTIFIÉ par écrit. Le
        comité voit ainsi quelles lignes sont des faits et lesquelles sont des paris, et de combien
        on s'écarte de la moyenne.
  • `fourchette` — sa FORME dépend de l'entreprise (#97, arbitrage du 2026-09-29) :
      - `scenarios_nommes` pour une incertitude CONTINUE (MSFT, NVDA) : trois récits, où seules les
        hypothèses décisives changent ; le central est le tableau tel quel ;
      - `arbre_evenements` pour une incertitude BINAIRE (RVMD) : les événements qui arrivent ou non,
        chacun avec sa probabilité (qui est elle-même une hypothèse du tableau). Le bas = tous
        échouent, le haut = tous réussissent, le central = la valeur pondérée — qui n'est PAS un
        scénario (on n'observera jamais la moitié d'une approbation).
  • `mecanique` — le code exécuté dans le bac à calcul (#96). Il DOIT définir `valeur_action`.

CE QUE CE FICHIER VÉRIFIE, ET CE QU'IL NE PEUT PAS VÉRIFIER (#37)
-----------------------------------------------------------------
Ici : la cohérence INTERNE de l'objet (clés uniques, segment déclaré, scénarios bien formés,
probabilités dans [0, 1]). Là-bas (`app/valorisation/modele.py`, `valider_pont_modele`) : ce qui
demande le dossier (la pièce existe, la réponse reprise est acquittée pour ce titre) ou l'exécution
(le code tourne, lit chaque hypothèse, rend une fourchette ordonnée).

La SIGNATURE du comité n'est pas ici : c'est un acte au procès-verbal, pas une propriété du modèle
proposé (lot suivant, avec sa migration).

Cible : pydantic v2 (container). Module PUR.
"""
from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

from pydantic import Field, model_validator

from .analysis_v2_schemas import NonEmptyRefs, Strict

__all__ = [
    "MODELE_SCHEMA_VERSION", "NOM_RESERVE_SEGMENTS", "SORTIE_OBLIGATOIRE",
    "TauxDeBase", "OriginePiece", "OrigineReprise", "OrigineJugement", "Origine",
    "Segment", "Hypothese", "ScenarioNomme", "ScenariosNommes", "Evenement", "ArbreEvenements",
    "ModeleValorisation", "cle_hypothese",
]

MODELE_SCHEMA_VERSION = "modele-1.0.0"
# Les hypothèses PAR SEGMENT arrivent dans la mécanique sous `segments[<id>][<nom>]` : le nom est
# donc réservé, une hypothèse globale qui le porterait masquerait tout le découpage.
NOM_RESERVE_SEGMENTS = "segments"
# Ce que toute mécanique doit calculer : la valeur PAR ACTION diluée, seule grandeur que le comité
# confronte au cours (va_6). Une valeur d'entreprise seule laisserait la dilution hors du chiffre.
# (Pas `valeur_par_action` : c'est le nom d'un gabarit du fonds, que le bac interdit de réaffecter.)
SORTIE_OBLIGATOIRE = "valeur_action"

Identifiant = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=60)]
Texte = Annotated[str, Field(min_length=3)]
Recit = Annotated[str, Field(min_length=20)]


class TauxDeBase(Strict):
    """La référence qui ancre un jugement : la classe (« phase 2 → approbation, oncologie »), sa
    valeur, et la pièce qui la publie. Un taux de base de mémoire n'ancre rien."""
    classe_de_reference: Recit
    valeur: float
    source_entry_refs: NonEmptyRefs


class OriginePiece(Strict):
    type: Literal["piece"]
    source_entry_refs: NonEmptyRefs


class OrigineReprise(Strict):
    """Le chiffre EST celui d'une réponse acquittée d'une autre méthodologie — jamais recollecté."""
    type: Literal["reponse_reprise"]
    question_id: Annotated[str, Field(pattern=r"^[a-z]{2}_[0-9]+$")]
    answer_id: int


class OrigineJugement(Strict):
    type: Literal["jugement"]
    taux_de_base: TauxDeBase
    ecart_justifie: Annotated[str, Field(min_length=30)]


Origine = Annotated[Union[OriginePiece, OrigineReprise, OrigineJugement], Field(discriminator="type")]


class Segment(Strict):
    id: Identifiant
    libelle: Texte
    perimetre: Recit            # ce que le segment couvre, en termes d'entreprise


class Hypothese(Strict):
    nom: Identifiant
    segment: Optional[Identifiant] = None   # None = hypothèse du dossier entier
    libelle: Texte                          # en termes d'entreprise, lu par le comité
    unite: Annotated[str, Field(min_length=1)]   # « % », « M$ », « années »
    valeur: float                           # la valeur CENTRALE
    origine: Origine


def cle_hypothese(h: Hypothese) -> str:
    """Clé d'une ligne du tableau — `nom` ou `segment.nom` —, détentrice unique de la forme des
    clés que les scénarios et les événements référencent."""
    return h.nom if h.segment is None else f"{h.segment}.{h.nom}"


class ScenarioNomme(Strict):
    role: Literal["bas", "central", "haut"]
    recit: Recit                            # ce qui arrive à l'entreprise dans ce scénario
    valeurs: dict[str, float] = Field(default_factory=dict)   # clé d'hypothèse → valeur du scénario


class ScenariosNommes(Strict):
    forme: Literal["scenarios_nommes"]
    scenarios: Annotated[list[ScenarioNomme], Field(min_length=3, max_length=3)]

    @model_validator(mode="after")
    def _trois_roles(self) -> "ScenariosNommes":
        roles = sorted(s.role for s in self.scenarios)
        if roles != ["bas", "central", "haut"]:
            raise ValueError(f"trois scénarios, un par rôle bas/central/haut (reçus : {roles})")
        for s in self.scenarios:
            if s.role == "central" and s.valeurs:
                raise ValueError("le scénario central EST le tableau signé : il ne modifie aucune hypothèse")
            if s.role != "central" and not s.valeurs:
                raise ValueError(f"le scénario {s.role} doit dire quelles hypothèses le séparent du central")
        return self


class Evenement(Strict):
    id: Identifiant
    recit: Recit                            # « daraxonrasib approuvé en 1re ligne du pancréas »
    probabilite: str                        # clé de l'hypothèse qui porte sa probabilité


class ArbreEvenements(Strict):
    forme: Literal["arbre_evenements"]
    evenements: Annotated[list[Evenement], Field(min_length=1)]


Fourchette = Annotated[Union[ScenariosNommes, ArbreEvenements], Field(discriminator="forme")]


class ModeleValorisation(Strict):
    schema_version: Literal["modele-1.0.0"] = "modele-1.0.0"
    ticker_id: Annotated[str, Field(min_length=1)]
    version: Annotated[int, Field(ge=1)]
    methodologie: Annotated[str, Field(min_length=80)]
    motif_de_la_forme: Recit
    segments: Annotated[list[Segment], Field(min_length=1)]
    hypotheses: Annotated[list[Hypothese], Field(min_length=1)]
    fourchette: Fourchette
    mecanique: Annotated[str, Field(min_length=1)]

    @model_validator(mode="after")
    def _coherence_interne(self) -> "ModeleValorisation":
        ids_segments = [s.id for s in self.segments]
        if len(set(ids_segments)) != len(ids_segments):
            raise ValueError("deux segments portent le même identifiant")
        cles = [cle_hypothese(h) for h in self.hypotheses]
        doublons = sorted({c for c in cles if cles.count(c) > 1})
        if doublons:
            raise ValueError(f"deux lignes du tableau pour la même hypothèse : {doublons}")
        for h in self.hypotheses:
            if h.segment is None and h.nom == NOM_RESERVE_SEGMENTS:
                raise ValueError(f"`{NOM_RESERVE_SEGMENTS}` est réservé au découpage du marché")
            if h.segment is not None and h.segment not in ids_segments:
                raise ValueError(f"l'hypothèse `{cle_hypothese(h)}` vise un segment non déclaré")
        chiffres = {h.segment for h in self.hypotheses if h.segment is not None}
        orphelins = [s for s in ids_segments if s not in chiffres]
        if orphelins:
            raise ValueError(f"segment(s) qu'aucune hypothèse ne chiffre : {orphelins} — découpage de façade")

        par_cle = {cle_hypothese(h): h for h in self.hypotheses}
        f = self.fourchette
        if isinstance(f, ScenariosNommes):
            for s in f.scenarios:
                inconnues = sorted(set(s.valeurs) - set(par_cle))
                if inconnues:
                    raise ValueError(f"le scénario {s.role} modifie des hypothèses absentes du tableau : {inconnues}")
        else:
            ids = [e.id for e in f.evenements]
            if len(set(ids)) != len(ids):
                raise ValueError("deux événements portent le même identifiant")
            portees = [e.probabilite for e in f.evenements]
            if len(set(portees)) != len(portees):
                raise ValueError("deux événements partagent la même probabilité : ils sont un seul événement")
            for e in f.evenements:
                h = par_cle.get(e.probabilite)
                if h is None:
                    raise ValueError(f"l'événement `{e.id}` cite une probabilité absente du tableau : `{e.probabilite}`")
                if not 0.0 <= h.valeur <= 1.0:
                    raise ValueError(f"la probabilité de `{e.id}` vaut {h.valeur} : elle doit être entre 0 et 1")
        return self
