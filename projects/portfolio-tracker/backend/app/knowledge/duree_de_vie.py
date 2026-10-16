"""La fraîcheur d'une réponse jugée PIÈCE PAR PIÈCE, dans la durée de vie de ce que chaque pièce fonde
(règle de fraîcheur, arbitrages du 2026-10-16 — `roadmap/V3/06-regle-fraicheur.md`).

Ce que ferait un vrai fonds : la note d'initiation cite des documents de tous âges ; elle est à jour
parce qu'elle INTÈGRE la dernière publication, pas parce que toutes ses sources sont récentes. Chaque
trimestre, l'analyste met à jour ses chiffres, ajoute une ligne à l'historique, et ne relit qu'une fois
par an ce qui ne se publie qu'une fois par an.

La règle d'avant (ordre 0, conservée sous l'interrupteur `fraicheur_par_duree_de_vie`) datait une
réponse par sa pièce LA PLUS ANCIENNE : un historique de cinq ans y vieillissait comme un solde de
trésorerie, et une note sur la direction de NVIDIA naissait périmée parce qu'elle citait le rapport
annuel (A4, 2026-10-16). Ici, chaque pièce est jugée selon l'ingrédient qu'elle fonde :

  · CHIFFRE COURANT — la pièce est postérieure (ou égale) à la dernière clôture de sa cadence
    (trimestrielle : la dernière clôture publiée ; annuelle : le dernier exercice publié) ;
  · HISTORIQUE — l'ingrédient est COMPLÉTÉ : sa pièce la plus RÉCENTE couvre la dernière clôture de sa
    cadence ; les pièces plus anciennes du même historique restent valables (elles disent le passé) ;
  · DESCRIPTION ANNUELLE — la pièce couvre le dernier exercice publié (elle cède au document annuel
    suivant) ;
  · JUGEMENT, REPRISE, AU COURS DU JOUR — aucune durée propre (seuls les faits qui rouvrent la question
    les touchent ; une reprise hérite de la réponse reprise ; un cours se relit à la lecture).

Et, pour toutes les pièces, le FAIT qui rouvre la question (hors publication de comptes, qui passe par
les cadences ci-dessus — arbitrage 3) : une pièce antérieure à ce fait le périme, sauf si l'analyste
l'a lu (#103/#117) ; pour un historique, c'est sa pièce la plus récente qui doit le couvrir (une
acquisition annoncée se COMPLÈTE dans l'historique des acquisitions).

Anti-blanchiment conservé là où il a un sens : un chiffre courant, une description, un jugement se
jugent pièce par pièce (une pièce récente à côté n'en rajeunit pas une vieille) ; seul l'historique se
juge par sa pièce la plus récente — c'est la définition même de « compléter ».

Prudence (ordre 0 aux bords) : une pièce que rien ne rattache à un ingrédient de la question est un
chiffre courant trimestriel (la durée la plus courte) ; une clôture d'exercice inconnue prend la
dernière clôture publiée (plus récente, donc plus exigeante) ; sans aucune clôture connue, la règle
s'abstient (`None`) et l'appelant applique l'ordre 0.

Fonctions PURES, sans IO : la fraîcheur se recalcule à chaque lecture (#53), rien n'est stocké.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping, Optional, Sequence

from app.knowledge.evenements import RESULTATS
from app.knowledge.material_events import MaterialEvent, MaterialEventLookup


@dataclass(frozen=True)
class DureeIngredient:
    """Ce que le référentiel déclare d'un ingrédient, réduit à ce que la règle lit."""
    ingredient_id: str
    duree_de_vie: str
    cadence: Optional[str] = None


# La durée la plus courte : celle d'une pièce que rien ne rattache à un ingrédient de la question.
PAR_DEFAUT = DureeIngredient(ingredient_id="(pièce non rattachée)", duree_de_vie="chiffre_courant",
                             cadence="trimestrielle")

_SANS_DUREE = frozenset({"jugement", "reprise", "au_cours_du_jour"})

_LIBELLE = {"chiffre_courant": "le chiffre courant", "historique": "l'historique",
            "description_annuelle": "la description annuelle", "jugement": "le jugement",
            "reprise": "la reprise", "au_cours_du_jour": "le chiffre au cours du jour"}


@dataclass(frozen=True)
class Clotures:
    """Les deux clôtures que lisent les cadences : la dernière publiée (trimestre ou exercice) et le
    dernier EXERCICE publié. Lues sur l'horloge du TITRE (pas de la question)."""
    derniere: Optional[date]
    exercice: Optional[date]


@dataclass(frozen=True)
class Jugement:
    etat: str          # courante | perimee | indeterminable
    motif: str


def fait_qui_rouvre(horloge: MaterialEventLookup) -> Optional[MaterialEvent]:
    """Le dernier fait (au SEUIL le plus tardif) qui rouvre la question, HORS publication de comptes :
    la part « résultats » d'un communiqué (scindée par `ancre_de_la_question`) passe par les cadences.
    `horloge` est l'ancre de la question privée des faits que la réponse a lus (`retirer_faits_lus`)."""
    if horloge.status != "found":
        return None
    faits = [e for e in horloge.recents if tuple(e.types) != (RESULTATS,)]
    return max(faits, key=lambda e: (e.seuil, e.event_date), default=None)


def _seuil_de_cadence(d: DureeIngredient, clotures: Clotures) -> Optional[date]:
    exercice = clotures.exercice or clotures.derniere
    if d.duree_de_vie in _SANS_DUREE:
        return None
    if d.duree_de_vie == "description_annuelle":
        return exercice
    return clotures.derniere if d.cadence == "trimestrielle" else exercice


def juger_fondation(
    cites: Sequence[int],
    *,
    dates: Mapping[int, Optional[date]],
    ingredients_des_pieces: Mapping[int, Sequence[DureeIngredient]],
    clotures: Clotures,
    fait: Optional[MaterialEvent],
    horloge_indisponible: Optional[str],
) -> Optional[Jugement]:
    """Juge une fondation. `None` = la règle s'abstient (aucune clôture connue) : l'ordre 0 s'applique.

    `ingredients_des_pieces` : pour chaque pièce citée, les ingrédients DE CETTE QUESTION qu'elle fonde
    (lus dans l'index de couverture). `fait` : `fait_qui_rouvre(horloge)`. `horloge_indisponible` : la
    raison si le flux des événements est injoignable (on ne sait pas — #49), sinon `None`."""
    if clotures.derniere is None:
        return None
    if horloge_indisponible:
        return Jugement("indeterminable", "le flux des événements matériels est injoignable "
                                          f"({horloge_indisponible}) : la fraîcheur n'est pas vérifiable")
    seuil_fait = fait.seuil if fait is not None else None
    perimes: list[str] = []
    sans_date: list[int] = []
    historiques: dict[str, tuple[DureeIngredient, list[tuple[int, Optional[date]]]]] = {}

    for p in cites:
        d_piece = dates.get(p)
        ings = list(ingredients_des_pieces.get(p) or ()) or [PAR_DEFAUT]
        for ing in ings:
            if ing.duree_de_vie == "historique":
                historiques.setdefault(ing.ingredient_id, (ing, []))[1].append((p, d_piece))
        autres = [i for i in ings if i.duree_de_vie != "historique"]
        if not autres:
            continue
        if d_piece is None:
            sans_date.append(p)
            continue
        for ing in autres:
            seuil = _seuil_de_cadence(ing, clotures)
            if seuil is not None and d_piece < seuil:
                perimes.append(f"{_LIBELLE[ing.duree_de_vie]} « {ing.ingredient_id} » cite la pièce #{p} "
                               f"du {d_piece.isoformat()}, antérieure à la clôture du {seuil.isoformat()} "
                               "(remplacé par les comptes publiés depuis)")
        if seuil_fait is not None and d_piece < seuil_fait:
            perimes.append(f"la pièce #{p} du {d_piece.isoformat()} précède le fait qui rouvre la question "
                           f"({fait.resume()})")

    for ing_id, (ing, pieces) in historiques.items():
        datees = [d for _p, d in pieces if d is not None]
        if not datees:
            sans_date.extend(p for p, _d in pieces)
            continue
        plus_recente = max(datees)
        seuil = max([s for s in (_seuil_de_cadence(ing, clotures), seuil_fait) if s is not None],
                    default=None)
        if seuil is not None and plus_recente < seuil:
            perimes.append(f"l'historique « {ing_id} » n'est pas complété : sa pièce la plus récente est du "
                           f"{plus_recente.isoformat()}, avant le {seuil.isoformat()} "
                           + ("(clôture publiée depuis)" if seuil != seuil_fait else f"({fait.resume()})"))

    if perimes:
        return Jugement("perimee", " ; ".join(perimes) + ". Elle reste EXACTE à sa date : périmé n'est "
                                                         "pas faux.")
    if sans_date:
        return Jugement("indeterminable", "pièce(s) sans date "
                        + ", ".join(f"#{p}" for p in sorted(set(sans_date)))
                        + " : leur fraîcheur n'est pas datable")
    return Jugement("courante", "chaque pièce est dans la durée de vie de ce qu'elle fonde (dernière "
                    f"clôture publiée : {clotures.derniere.isoformat()}"
                    + (f", dernier exercice : {clotures.exercice.isoformat()}" if clotures.exercice else "")
                    + ")" + (f" ; aucun fait ne la rouvre depuis ses pièces" if fait is None else
                             f" ; le dernier fait qui la rouvre ({fait.resume()}) est couvert"))


@dataclass(frozen=True)
class ContexteDurees:
    """Ce que le point de lecture passe à `servir_answer` quand l'interrupteur est actif : les clôtures
    du titre et, PAR QUESTION, les ingrédients que fonde chaque pièce (index de couverture)."""
    clotures: Clotures
    ingredients_des_pieces: Mapping[str, Mapping[int, Sequence[DureeIngredient]]]  # question → pièce → …
