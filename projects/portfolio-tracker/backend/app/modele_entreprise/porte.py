"""La PORTE DE L'ARCHITECTE — lot M3, roadmap V3 `12-lot-M3-architecte.md` §3.1 (spec métier 09 §11.2).

« Au moins une réponse instruite, quel qu'en soit le statut ; un échec technique ou une question
jamais cherchée ferme la porte, et le manque est nommé. » Cette règle se lit sur le DIAGNOSTIC
EXISTANT de `app/agents/v2/parcours.py` (`manque_pour_question`, détenteur unique des arguments de
`manque_de_la_question`, #46) — jamais recopiée. Pure : aucune IO, aucun appel modèle.

Une porte FERMÉE se lève AVANT toute dépense (#40, #63) — c'est `architecte.py` qui en fait un refus
nommé ; ce module se contente de la DIRE.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.agents.v2.parcours import EtatDossier, manque_pour_question
from app.modele_entreprise.referentiel import ReferentielModele, questions_sources_applicables

__all__ = ["EtatQuestionSource", "Porte", "porte_de_l_architecte"]


@dataclass(frozen=True)
class EtatQuestionSource:
    question_id: str
    framework_id: str
    ouvre: bool
    raison: str
    answer_id: Optional[int] = None


@dataclass(frozen=True)
class Porte:
    ouverte: bool
    archetype: Optional[str]
    questions: tuple[EtatQuestionSource, ...]
    # Raison au niveau de la porte — portée seulement quand `questions` est vide (émetteur sans
    # archétype) : il n'y a alors aucune ligne de question à motiver individuellement.
    raison: Optional[str] = None
    # Nombre de questions qui n'ouvrent que parce que `porte_admet_reponses_refusees` (phase de
    # test, arbitrage du 2026-10-22) est à `true` — le comité doit voir que la porte n'est ouverte
    # QUE par la phase de test, jamais en silence.
    n_refusees_admises: int = 0


def _framework_de(fichier, question_id: str) -> Optional[tuple[object, object]]:
    """Le `(framework, question)` qui porte cet id — un id de question est unique dans tout le
    référentiel (préfixe par méthodologie, `me_`/`mo_`/`se_`/`qf_`/`ma_`/`va_`)."""
    for f in fichier.frameworks:
        for q in f.questions:
            if q.id == question_id:
                return f, q
    return None


def _diagnostic(etat: EtatDossier, f, q, ref: ReferentielModele) -> EtatQuestionSource:
    applicable, manque = manque_pour_question(etat, f, q)

    if applicable is None:
        # `etat.applicables.get(f.id)` est `None` : CE framework n'a pas d'ensemble d'applicables
        # connu (cas défensif — en pratique `etat.archetype` non `None` implique que chaque
        # framework a son ensemble). « Émetteur non classé », comme la ligne de la spec le nomme.
        return EtatQuestionSource(q.id, f.id, False, "émetteur non classé")

    if manque is None:
        # Pas de manque : la réponse tient, l'acceptation du comité est en vigueur, ou la question
        # est dispensée (`manque_de_la_question` rend `None` dans ces trois cas — jamais pour
        # `applicable is False`, puisque `questions_sources_applicables` a déjà écarté les
        # questions `sans_objet` de CET archétype avant que la porte ne les voie).
        dispenses = etat.dispenses.get(f.id, frozenset())
        position = etat.comite.get((f.id, q.id))
        if q.id in dispenses:
            return EtatQuestionSource(q.id, f.id, True, "dispensée par le comité")
        if (position is not None and position.acceptation is not None
                and position.acceptation.etat == "en_vigueur"):
            return EtatQuestionSource(q.id, f.id, True, "acceptée par le comité")
        reps = [r for r in etat.reponses
                if r.servie.framework_id == f.id and r.servie.question_id == q.id]
        from app.agents.v2.parcours import reponse_tient
        qui_tient = next((r for r in reps if reponse_tient(r)), None)
        if qui_tient is not None:
            return EtatQuestionSource(q.id, f.id, True, f"réponse #{qui_tient.answer_id} qui tient",
                                      answer_id=qui_tient.answer_id)
        # Ne devrait pas arriver (les trois cas ci-dessus épuisent `manque is None`) : prudence,
        # jamais un vert muet.
        return EtatQuestionSource(q.id, f.id, True, "aucun manque diagnostiqué", answer_id=None)

    if manque.nature == "renvoyee":
        # Arbitrage de l'utilisateur du 2026-10-22 — interrupteur `porte_admet_reponses_refusees` :
        # CIBLE (false), une réponse renvoyée par le contrôle ferme la porte (il faut une réponse
        # JUSTE pour construire) ; phase de test (true), elle ouvre, marquée « refusée ».
        if ref.porte_admet_reponses_refusees:
            return EtatQuestionSource(
                q.id, f.id, True,
                f"réponse #{manque.answer_id} refusée par le contrôle : {manque.explication}",
                answer_id=manque.answer_id)
        return EtatQuestionSource(
            q.id, f.id, False,
            f"réponse #{manque.answer_id} refusée par le contrôle : {manque.explication} — à "
            "corriger avant de dessiner", answer_id=manque.answer_id)

    if manque.nature in ("perimee", "pas_encore_observable"):
        return EtatQuestionSource(
            q.id, f.id, True, f"réponse #{manque.answer_id} : {manque.explication}",
            answer_id=manque.answer_id)

    if manque.nature == "non_fondee":
        if manque.cause == "source_indisponible":
            return EtatQuestionSource(
                q.id, f.id, False,
                f"échec technique : relancer avant de dessiner — {manque.explication}",
                answer_id=manque.answer_id)
        return EtatQuestionSource(q.id, f.id, True, f"non fondable : {manque.explication}",
                                  answer_id=manque.answer_id)

    if manque.nature == "sans_reponse":
        return EtatQuestionSource(q.id, f.id, False, "aucune réponse instruite")

    if manque.nature == "rouverte_comite":
        return EtatQuestionSource(
            q.id, f.id, False,
            "le comité a renvoyé ou remis à zéro ; rien n'a été écrit depuis")

    # Vocabulaire fermé de `NatureManque` — aucune autre valeur n'existe (contrat `parcours_schema`).
    raise AssertionError(f"nature de manque inconnue : {manque.nature!r}")  # pragma: no cover


def porte_de_l_architecte(etat: EtatDossier, ref: ReferentielModele) -> Porte:
    """La porte de l'architecte pour ce dossier : ouverte si TOUTES les questions sources de
    l'archétype en vigueur ouvrent, fermée sinon — les questions qui ferment le disent, avec leur
    raison (#83)."""
    if etat.archetype is None:
        return Porte(ouverte=False, archetype=None, questions=(),
                     raison="émetteur non classé (aucun archétype en vigueur)")

    ids = questions_sources_applicables(ref, etat.fichier, etat.archetype)
    questions: list[EtatQuestionSource] = []
    for qid in ids:
        trouve = _framework_de(etat.fichier, qid)
        if trouve is None:
            questions.append(EtatQuestionSource(qid, "?", False, "émetteur non classé"))
            continue
        f, q = trouve
        questions.append(_diagnostic(etat, f, q, ref))

    ouverte = all(eq.ouvre for eq in questions) if questions else False
    n_refusees_admises = sum(
        1 for eq in questions if eq.ouvre and eq.raison.startswith("réponse #") and "refusée par le contrôle" in eq.raison)
    return Porte(ouverte=ouverte, archetype=etat.archetype, questions=tuple(questions),
                raison=(f"porte ouverte (phase de test : {n_refusees_admises} réponse(s) refusée(s) "
                        "admise(s))" if ouverte and n_refusees_admises else None),
                n_refusees_admises=n_refusees_admises)
