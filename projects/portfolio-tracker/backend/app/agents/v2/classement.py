"""Le CLASSEMENT DE L'ÉMETTEUR : ce que le système recommande, ce que le comité décide (#139).

Arbitrage de l'utilisateur (2026-10-18, 07 point 21) : « le système détecte le changement de stade ; le
comité valide toujours ensuite, mais il y a une recommandation claire ». Comme un vrai fonds : le stade
de la société est écrit en tête de chaque dossier ; quand une biotech obtient l'autorisation de vendre
son premier produit, l'analyste propose de la reclasser « commerciale », le directeur de la recherche
décide, date, signe et cite l'événement — et tous les analystes, quel que soit leur chapitre, voient ce
fait (sa pièce est jointe d'office à chaque dossier, `preparation.preparer_dossier_analyste`).

Deux moitiés :
  · `recommandation_de_classement` — PURE, recalculée à chaque lecture (jamais stockée, #53/#77) : un
    dépôt lu par la note flash sous un type qui `reclasse` l'archétype en vigueur (catalogue 1.7.0,
    `changement_de_stade`), et qu'aucune DÉCISION du comité n'a encore tranché ;
  · `decider_classement` — le GESTE : reclasser OU maintenir, signé, motivé, adossé à la lecture du
    dépôt déclencheur. Il prend effet le jour où le comité le prend ; la date du fait reste celle de la
    pièce (c'est elle que l'analyste cite pour justifier une attente, #138).

⚠️ UN CLASSEMENT D'ORIGINE NE TRANCHE RIEN. RVMD a été classée « sans revenus » le 24/09, APRÈS
l'approbation du 26/08, avec le motif « ce classement est daté et destiné à être revu ». Une règle « fait
postérieur au classement » n'aurait donc jamais rien recommandé. Seule une décision du comité (qui
porte un dépôt déclencheur) ferme les faits survenus jusqu'à sa date.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping, Optional

from app.agents.v2.framework_persist import Classement, persist_archetype, read_classement


class ClassementRefuse(ValueError):
    """Le geste ne peut pas être inscrit — le message dit pourquoi, en termes de comité."""


@dataclass(frozen=True)
class Recommandation:
    """Ce que le système recommande au comité : reclasser `de` → `vers`, au vu du dépôt `accession`
    (fait du `fait_du`), lu par la note flash sous le type `type_id`."""
    de: str
    vers: str
    fait_du: date
    accession: str
    type_id: str
    resume: str


def recommandation_de_classement(classement: Optional[Classement], notes: Mapping[str, Any],
                                 fichier) -> Optional[Recommandation]:
    """Le PREMIER fait non tranché qui recommande de reclasser l'archétype en vigueur, ou `None`.

    `notes` : ce que les notes flash ont lu des dépôts de l'émetteur (`QualificationLue` par accession,
    interrupteurs déjà appliqués — un rappel admis ne recommande rien). Un émetteur non classé ne reçoit
    pas de recommandation : son manque est d'abord d'être classé, et le niveau 1 le dit déjà."""
    if classement is None:
        return None
    # Une décision du comité tranche les faits survenus jusqu'à sa date ; un classement d'origine, aucun.
    seuil = classement.effective_from if classement.declencheur_accession else None
    candidats: list[Recommandation] = []
    for t in fichier.types_evenement:
        vers = (t.reclasse or {}).get(classement.archetype)
        if vers is None:
            continue
        for accession, q in notes.items():
            fait = getattr(q, "date_evenement", None)
            if t.id not in q.types or fait is None or (seuil is not None and fait <= seuil):
                continue
            candidats.append(Recommandation(de=classement.archetype, vers=vers, fait_du=fait,
                                            accession=accession, type_id=t.id, resume=q.resume))
    return min(candidats, key=lambda r: (r.fait_du, r.accession)) if candidats else None


async def decider_classement(conn, *, ticker_id: str, archetype: str, accession: str, motif: str,
                             auteur: str, fichier, ancre, aujourd_hui: Optional[date] = None) -> int:
    """Le comité RECLASSE (archétype différent) ou MAINTIENT (le même) l'émetteur au vu d'un dépôt.

    Le code vérifie les RELATIONS, jamais le sens (#68) : archétype déclaré ; dépôt présent dans le fil
    EDGAR de l'émetteur et survenu au plus tard aujourd'hui ; décision postérieure au classement en
    vigueur (sinon elle ne serait pas en vigueur, ou réécrirait celle du jour) ; lecture du dépôt
    obtenue (elle devient la pièce). Écrit la lecture si elle manque (gratuit, EDGAR), puis la ligne."""
    from app.knowledge.lecture_depot import assurer_lectures

    jour = aujourd_hui or date.today()
    if archetype not in set(fichier.archetypes):
        raise ClassementRefuse(f"`{archetype}` n'est pas un classement déclaré ({sorted(fichier.archetypes)})")
    if not motif.strip() or not auteur.strip():
        raise ClassementRefuse("une décision de classement se signe et se motive")
    event = next((e for e in getattr(ancre, "recents", ()) or () if e.accession == accession), None)
    if event is None:
        raise ClassementRefuse(
            f"le dépôt {accession} n'est pas dans le fil EDGAR de {ticker_id} : la décision doit "
            "citer le fait qui la justifie, tel que l'émetteur l'a publié")
    if event.event_date > jour:
        raise ClassementRefuse(f"le dépôt {accession} est daté du {event.event_date}, dans le futur")
    courant = await read_classement(conn, ticker_id=ticker_id, a_la_date=jour)
    if courant is not None and courant.effective_from >= jour:
        raise ClassementRefuse(
            f"un classement de {ticker_id} a déjà pris effet le {courant.effective_from} : une seconde "
            "décision le même jour réécrirait la première au lieu de s'y ajouter — la reprendre demain")
    lecture = (await assurer_lectures(conn, ticker_id, getattr(ancre, "cik", None), [event]))[0]
    if lecture.entry_id is None:
        raise ClassementRefuse(f"la lecture du dépôt {accession} n'a pas pu être versée au dossier : "
                               f"{lecture.motif}")
    return await persist_archetype(conn, ticker_id=ticker_id, archetype=archetype, motif=motif.strip(),
                                   effective_from=jour, piece_id=lecture.entry_id,
                                   auteur=auteur.strip(), declencheur_accession=accession)
