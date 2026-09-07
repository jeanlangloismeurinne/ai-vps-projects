"""L'axe `actualité` — calculé à la LECTURE, jamais persisté (capacité 3 de la roadmap 02).

Pourquoi cet axe n'est pas une colonne
--------------------------------------
La révision « autorité contre actualité » sépare trois propriétés qu'un scalaire unique confondait
(#50). Deux sont **stockées** — la fiabilité (propriété de la source) et la nature (propriété de
l'assertion, migration 034). La troisième ne peut pas l'être : l'actualité n'est pas une propriété
du fait, c'est une propriété de la **relation** entre le fait et l'ancre matérielle du moment. La
stocker la figerait, et ce serait **exactement la cause n°2** du diagnostic — un corpus dont le
score est arrêté à l'écriture ne vieillit jamais, donc il ne peut pas signaler qu'il a vieilli.

D'où la forme du module : des fonctions **pures**, sans IO, sans écriture, appelées à chaque
lecture. La même entry, inchangée en base, change d'état quand un 8-K postérieur paraît — et aucun
`UPDATE` n'est émis pour ça. C'est le test d'acceptation de la capacité, et il est gardé par grep
sur ce fichier (comme `staleness.py`).

Trois états, jamais deux confondus (#25/#44)
--------------------------------------------
  • ``courante``        — le fait est daté à/après l'ancre matérielle : il a pu en tenir compte ;
  • ``perimee``         — le fait est STRICTEMENT antérieur à l'ancre : il reste exact à sa date,
    mais il peut décrire un monde révolu. Périmé n'est pas faux — ne jamais le lire comme tel ;
  • ``indeterminable``  — on ne SAIT pas. Deux causes distinctes, toutes deux nommées dans le
    motif : l'entry n'a pas de `source_date`, ou le flux des événements est injoignable.

⚠️ ``indeterminable`` n'est pas ``courante``. Les confondre est le mode de panne central de tout ce
chantier : une panne réseau se lirait « rien n'a changé », c'est-à-dire la phrase la plus
rassurante possible produite par la pire des raisons (#49). L'état est donc rendu **en le disant**,
et un appelant qui veut le traiter comme fondant doit le décider explicitement.

Ce que ce module NE fait pas
----------------------------
Il ne confronte pas l'état au profil du champ (`FIELD_PROFILES[...]["actualite_bloquante"]`) : un
fait `perimee` sur un champ où l'actualité n'est pas bloquante continue de le fonder. Cette
confrontation est le travail de la porte de complétude — **capacité 4**, pas ici. Le mélanger
maintenant perturberait la ligne de base que son test central doit mesurer avant son lot.

Il ne décide rien non plus : aucun `superseded_by`, aucune écriture. Décider qu'un fait est
remplacé est un jugement sémantique, et l'automatiser donnerait à une heuristique de dates une voix
sur ce que le corpus affirme (#29, `feedback_optional_schema_gate`).

Détenteur unique (#46)
----------------------
La comparaison « ce fait est-il antérieur à l'ancre ? » vivait déjà, en clair, dans
`staleness.balayage_peremption` (partition `suspecte` / `posterieure` / `non_datee`). Écrire ici une
seconde implémentation de la même règle aurait produit deux jumeaux qui re-divergent au premier
correctif. `staleness` importe donc ce module et se contente de **traduire** le vocabulaire de
l'axe vers celui de son rapport. La traduction est explicite (`CLASSE_RAPPORT`), pas devinée.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.knowledge.material_events import MaterialEventLookup

# Vocabulaire FERMÉ de l'axe. Un état hors de cette liste n'existe pas : il n'y a pas d'état par
# défaut, et surtout pas de quatrième état « probablement fraîche ».
ETATS: frozenset[str] = frozenset({"courante", "perimee", "indeterminable"})

# Traduction axe → vocabulaire du rapport de péremption (`staleness.py`). Elle est écrite ici, à
# côté de la règle, pour qu'un ajout d'état ne puisse pas laisser le rapport muet sur une classe.
CLASSE_RAPPORT: dict[str, str] = {
    "courante": "posterieures",
    "perimee": "suspectes",
    "indeterminable": "non_datees",
}


@dataclass(frozen=True)
class Actualite:
    """État d'actualité d'un fait à l'instant de la LECTURE. Immuable, et jamais écrit en base.

    `jours_avant_evenement` est positif quand le fait précède l'ancre (c'est l'ancienneté relative,
    donc l'ordre de suspicion le plus honnête dont on dispose sans juger le CONTENU). Il vaut `None`
    dès qu'un des deux termes manque — on ne fabrique pas un écart depuis une date inconnue.
    """

    etat: str
    motif: str
    seuil: Optional[date] = None            # date de l'ÉVÉNEMENT retenu comme ancre
    source_date: Optional[date] = None      # date du FAIT (#48 : la colonne, pas la publication)
    jours_avant_evenement: Optional[int] = None

    @property
    def su(self) -> bool:
        """True seulement si on SAIT. `perimee` compte comme su ; `indeterminable` non."""
        return self.etat in ("courante", "perimee")


def _causes_indeterminables(source_date: Optional[date], ancre: MaterialEventLookup) -> list[str]:
    """Les deux causes d'ignorance, cumulables, chacune nommée. Une seule liste, pour que le motif
    n'en taise jamais une quand les deux sont réunies."""
    causes: list[str] = []
    if ancre.status == "unavailable":
        causes.append(
            "le flux des événements matériels est injoignable"
            + (f" ({ancre.raison})" if ancre.raison else "")
        )
    if source_date is None:
        causes.append("l'entry n'a pas de `source_date` (sa fraîcheur n'est pas datable)")
    return causes


def etat_actualite(
    *,
    source_date: Optional[date],
    ancre: MaterialEventLookup,
) -> Actualite:
    """État d'actualité d'un fait face à l'ancre matérielle. Fonction **pure** : aucune IO, aucune
    écriture, aucun effet de bord — c'est ce qui rend l'axe recalculable à chaque lecture.

    L'actualité se mesure sur la date du **FAIT**, jamais sur celle de la publication : `source_date`
    porte la première (#48 en a fait un porteur fiable), et l'ancre est tirée du `reportDate` d'EDGAR,
    pas du `filingDate` (#49). Un article de ce matin qui commente un trimestre clos en juin est daté
    de juin — sans quoi le biais de récence remplacerait le défaut qu'on corrige.
    """
    causes = _causes_indeterminables(source_date, ancre)
    if causes:
        return Actualite(
            etat="indeterminable",
            motif="indéterminable : " + " ; ".join(causes)
            + ". ⚠️ Indéterminable n'est pas courante — l'absence d'information n'en est pas une.",
            seuil=ancre.event.event_date if ancre.status == "found" and ancre.event else None,
            source_date=source_date,
        )

    if ancre.status == "none":
        # État CONNU, distinct d'une panne : l'émetteur n'a rien publié qui puisse périmer quoi que
        # ce soit. C'est la seule branche où « rien n'a changé » est une mesure, pas un silence.
        return Actualite(
            etat="courante",
            motif="l'émetteur n'a publié aucun 8-K/6-K : aucun événement matériel ne peut périmer "
                  "ce fait. Les dépôts périodiques restent traités par le supersedage (#43).",
            seuil=None,
            source_date=source_date,
        )

    assert ancre.event is not None  # garanti par `found` — les deux autres statuts sont traités
    seuil = ancre.event.event_date
    ecart = (seuil - source_date).days  # type: ignore[operator] — `source_date` non nul ici

    if source_date < seuil:  # type: ignore[operator]
        return Actualite(
            etat="perimee",
            motif=f"fait daté du {source_date.isoformat()}, antérieur de {ecart} jours à "  # type: ignore[union-attr]
                  f"l'événement matériel du {seuil.isoformat()} ({ancre.event.resume()}). "
                  "Il reste EXACT à sa date : périmé n'est pas faux.",
            seuil=seuil,
            source_date=source_date,
            jours_avant_evenement=ecart,
        )

    return Actualite(
        etat="courante",
        motif=f"fait daté du {source_date.isoformat()}, à/après l'événement matériel du "  # type: ignore[union-attr]
              f"{seuil.isoformat()} : il a pu en tenir compte.",
        seuil=seuil,
        source_date=source_date,
        jours_avant_evenement=ecart,
    )


def classe_rapport(etat: str) -> str:
    """Nom de classe du rapport de péremption pour un état de l'axe. Un état inconnu lève plutôt que
    de retomber sur une classe « par défaut » : ranger un état non prévu avec les faits courants
    est précisément la panne que ce module existe pour empêcher."""
    return CLASSE_RAPPORT[etat]
