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


def date_effective(
    entry: dict, *, corpus: Optional[dict[int, dict]] = None
) -> tuple[Optional[date], str]:
    """Date à laquelle un fait doit être confronté à l'ancre. Fonction **pure**.

    Une entry porte normalement sa propre `source_date` (#48 en a fait un porteur fiable). Deux
    producteurs n'en écrivent pas : les synthèses et les analyses d'agent, qui ne relèvent rien du
    monde mais **distillent** des entries de la base. Les traiter comme non datables les rendrait
    `indeterminable` à perpétuité, donc non fondantes sur tout champ où l'actualité bloque — alors
    que leur fraîcheur est parfaitement connue : c'est celle de ce qu'elles citent.

    ⚠️ **La plus ANCIENNE des sources citées, jamais la plus récente.** Une synthèse affirme ses
    énoncés conjointement : si un seul de ses ingrédients décrit un monde révolu, la synthèse le
    décrit aussi. Prendre la plus récente ferait rajeunir un contenu périmé en le recopiant dans une
    synthèse — un blanchiment de péremption, et le mode de panne le plus probable de tout ce
    chantier (le biais de récence, roadmap 02 « risque secondaire »).

    Résolution sur **un seul niveau**, et une citation elle-même non datée est ignorée plutôt que
    résolue en cascade : une chaîne de synthèses citant des synthèses ferait dépendre la date d'un
    parcours de graphe, là où la question posée est simplement « de quand datent les faits ? ».
    Aucune source citée résoluble → `None`, et l'appelant rendra `indeterminable` — l'ignorance
    reste dite, jamais comblée par un défaut (#25/#44).
    """
    propre = entry.get("source_date")
    if propre is not None:
        return propre, "date propre de l'entry (`source_date`)"

    cites = _entries_citees(entry)
    if not cites:
        return None, "aucune `source_date` et aucune entry citée : la fraîcheur n'est pas datable"

    datees = {i: (corpus or {}).get(i, {}).get("source_date") for i in cites}
    connues = {i: d for i, d in datees.items() if d is not None}
    if not connues:
        return None, (
            "aucune `source_date` ; les "
            f"{len(cites)} entry(s) citée(s) n'en portent pas non plus"
        )

    plus_ancienne = min(connues.values())
    porteuses = sorted(i for i, d in connues.items() if d == plus_ancienne)
    return plus_ancienne, (
        f"date héritée de la plus ANCIENNE des {len(connues)} entry(s) citée(s) datée(s) : "
        f"{plus_ancienne.isoformat()} (#{', #'.join(str(i) for i in porteuses)}). Une synthèse "
        "n'est pas plus fraîche que son ingrédient le plus vieux."
    )


def _entries_citees(entry: dict) -> list[int]:
    """Ids des entries qu'une synthèse/analyse distille, lus dans `content_structured`.

    Deux formes coexistent en base : `claims[].cited_entry_ids` (analyses) et `source_entry_refs`
    (context packs). Les deux sont lues — n'en lire qu'une rendrait l'autre famille indatable sans
    que rien ne le signale. Tolérante à la forme : ce qui n'est pas un entier est ignoré, jamais
    fatal (#50 §1 — une donnée hors forme est écartée, elle ne fait pas tomber la lecture).
    """
    cs = entry.get("content_structured")
    if not isinstance(cs, dict):
        return []
    ids: list[int] = []
    for claim in cs.get("claims") or []:
        if isinstance(claim, dict):
            ids += [i for i in (claim.get("cited_entry_ids") or []) if isinstance(i, int)]
    for ref in cs.get("source_entry_refs") or []:
        if isinstance(ref, int):
            ids.append(ref)
        elif isinstance(ref, dict) and isinstance(ref.get("entry_id"), int):
            ids.append(ref["entry_id"])
    return sorted(set(ids))


def etat_actualite_entry(
    entry: dict, *, ancre: MaterialEventLookup, corpus: Optional[dict[int, dict]] = None
) -> Actualite:
    """État d'actualité d'une entry complète — `date_effective` puis `etat_actualite`. Pure.

    C'est la porte d'entrée que les consommateurs doivent appeler : elle est la seule à connaître
    la règle de datation des entries dérivées. Appeler `etat_actualite(source_date=e["source_date"])`
    directement court-circuite cette règle et reclasse toutes les synthèses en `indeterminable`.
    """
    eff, motif_date = date_effective(entry, corpus=corpus)
    act = etat_actualite(source_date=eff, ancre=ancre)
    if eff is not None and entry.get("source_date") is None:
        # La date est héritée : le motif doit le DIRE, sinon le rapport affirme une date que la
        # ligne ne porte pas — exactement le défaut que #48 a corrigé sur `source_date`.
        return Actualite(
            etat=act.etat,
            motif=f"{act.motif} [{motif_date}]",
            seuil=act.seuil,
            source_date=act.source_date,
            jours_avant_evenement=act.jours_avant_evenement,
        )
    return act


def classe_rapport(etat: str) -> str:
    """Nom de classe du rapport de péremption pour un état de l'axe. Un état inconnu lève plutôt que
    de retomber sur une classe « par défaut » : ranger un état non prévu avec les faits courants
    est précisément la panne que ce module existe pour empêcher."""
    return CLASSE_RAPPORT[etat]
