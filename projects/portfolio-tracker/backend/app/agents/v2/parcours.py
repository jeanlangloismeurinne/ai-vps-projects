"""L'ASSEMBLEUR DU PARCOURS DU COMITÉ — les trois niveaux de drill-down (chantier v3, lot 6 maillon 2).

DÉTENTEUR UNIQUE (#46) de « ce que le comité voit d'un dossier » : la note projetée
(`projection_memo.servir_memo`), la note de qualité (`qualite_info.servir_qualite_info`) et les trois
niveaux passent TOUS par `charger_etat_dossier`. Avant ce module, deux assembleurs recopiaient la même
plomberie (réponses courantes → pièces → ancre → service) et divergeaient déjà : l'un chargeait les
ingrédients d'approximation, l'autre non. Trois écrans de plus en auraient fait cinq.

DEUX MOITIÉS, ET LA FRONTIÈRE GRATUITE ENTRE ELLES
--------------------------------------------------
  · `charger_etat_dossier(conn, ticker)` — la SEULE moitié qui lit (base + ancre matérielle EDGAR).
    Elle rejoue la revue du manager (#77 : l'avis se recalcule, il ne se lit pas) et sert chaque
    réponse (#53 : l'actualité se recalcule). Elle n'écrit RIEN.
  · `dresser_niveau1/2/3(etat, …)` et `manque_de_la_question(…)` — PURES, rejouables hors ligne,
    sans dépense. C'est là que vivent les règles, et c'est là que les checks les éprouvent.

L'ALERTE « PEUT-ON DÉCIDER ? » (arbitrage du comité n°3, 2026-09-25)
-------------------------------------------------------------------
Ce que ferait un vrai fonds : l'analyste qui présente un dossier incomplet ne dit pas « 5 questions
sans réponse ». Il dit, question par question, ce qui manque et POURQUOI il n'a pas pu l'obtenir —
parce que le comité ne réagit pas pareil à « la donnée n'est pas publiée » (on décide sans), à « la
base était en panne » (on relance avant de décider) et à « ça n'existe pas pour une biotech » (on
reformule la question). `manque_de_la_question` est le détenteur unique de ce diagnostic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Optional

from app.agents.v2.frameworks import _plus_faible, load_frameworks
from app.contracts.cause_manque_schema import CauseManqueCollecte
from app.contracts.comite_schema import (
    ACTIONS_OUVRANTES, AcceptationServie, DecisionComite, PositionComite)
from app.contracts.framework_answer_schema import FrameworkAnswer, FrameworkAnswerServie
from app.contracts.framework_definition_schema import FrameworksFile
from app.knowledge.standard_collecte import COLONNES_SQL, piece_au_standard
from app.contracts.parcours_schema import (
    BaisseDeFondement,
    CauseManque,
    ClassementServi,
    DossierTitre,
    FrameworkDuDossier,
    IngredientManquant,
    LigneQuestion,
    Manque,
    PeutOnDecider,
    PieceCitee,
    PreuveReponse,
    PreuvesQuestion,
    ReclassementRecommande,
    RenvoiAEmettre,
    ReponseResumee,
    SyntheseFramework,
)

__all__ = [
    "EtatDossier",
    "Collecte",
    "ReponseLue",
    "charger_etat_dossier",
    "manque_de_la_question",
    "manque_pour_question",
    "reponse_tient",
    "PerimetreRelance",
    "EmetteurNonClasse",
    "questions_a_relancer",
    "dresser_niveau1",
    "dresser_niveau2",
    "dresser_niveau3",
    "ReferenceInconnue",
]


class ReferenceInconnue(LookupError):
    """Un framework ou une question qui n'existe pas dans le référentiel — l'endpoint en fait un 404.
    Jamais un niveau vide : un écran vide se lirait « rien au dossier »."""


@dataclass(frozen=True)
class Collecte:
    """Ce que la DERNIÈRE collecte a fait pour une question : la preuve de la cause d'un manque.

    `plan_id` None = aucun plan de collecte n'a jamais couvert la question. Sinon `ingredients_vus`
    sont les lignes du plan pour cette question, et `mandats` ceux qui n'ont pas abouti."""
    plan_id: Optional[int]
    ingredients_vus: tuple[str, ...] = ()
    mandats: tuple[IngredientManquant, ...] = ()


@dataclass(frozen=True)
class ReponseLue:
    """Une réponse du dossier, SERVIE, avec l'avis du manager recalculé à la lecture."""
    answer_id: int
    servie: FrameworkAnswerServie            # `manager` attaché ssi l'avis est complet
    verdict: Optional[str]                   # acquitte | renvoye | None (non revalidable)
    controles: Any = None                    # ControlesManager | None
    motif_revue: Optional[str] = None
    etat_revue: str = "non_revalidable"      # revue | renvoi_a_emettre | non_revalidable
    # L'instant d'écriture (`framework_answers.created_at`) : une réponse écrite AVANT un renvoi ou une
    # réinitialisation du comité ne ferme plus la question (#137). Inconnu (None) = antérieure.
    cree_le: Optional[datetime] = None
    # Point 13 — cette réponse est-elle une BAISSE à lire par le comité ? Recalculée à la lecture
    # par `revision.baisse_a_lire`, jamais stockée (#53/#77).
    baisse: Optional[BaisseDeFondement] = None


@dataclass
class EtatDossier:
    """Tout ce que les trois niveaux lisent — chargé UNE fois par `charger_etat_dossier`."""
    ticker_id: str
    fichier: FrameworksFile
    archetype: Optional[str]
    reponses: list[ReponseLue]
    # Colonnes d'AFFICHAGE des pièces (titre, url, dates, nature…) — distinctes du corpus des
    # RÈGLES (`source_date`, `reliability_tier`), pour que l'ajout d'une colonne d'affichage ne
    # puisse jamais changer un verdict.
    pieces: dict[int, dict[str, Any]]
    applicables: dict[str, Optional[frozenset[str]]]         # framework → questions applicables
    dispenses: dict[str, frozenset[str]]                      # framework → questions dispensées
    mandats_ouverts: dict[tuple[str, str], int]               # (framework, question) → id
    collecte: dict[tuple[str, str], Collecte]                 # (framework, question) → dernière
    genere_le: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # Le COMITÉ (maillon 3) : le PV de chaque question (le plus récent d'abord) et sa position du
    # jour, SERVIE par `comite.position_du_comite` au chargement (recalculée, jamais lue en base).
    registre: dict[tuple[str, str], list[DecisionComite]] = field(default_factory=dict)
    comite: dict[tuple[str, str], PositionComite] = field(default_factory=dict)
    # #139 — le classement en vigueur (pièce et auteur quand c'est une décision du comité) et la
    # recommandation de le revoir, RECALCULÉE à chaque lecture (`classement.recommandation_de_classement`).
    classement: Optional[Any] = None
    recommandation: Optional[Any] = None


# ── La règle du manque (PURE) ──────────────────────────────────────────────────────────────────

# Quand plusieurs ingrédients ont échoué pour des raisons différentes, la cause affichée en tête est
# celle qui appelle un GESTE : une panne se relance, donc elle passe devant « rien de publié », qui
# passe devant « aucune source possible ». Un fonds regarde d'abord ce qu'il peut encore obtenir.
_PRECEDENCE_COLLECTE: tuple[CauseManqueCollecte, ...] = (
    "source_indisponible", "recherche_epuisee", "sans_source_possible")

_EXPLICATION: dict[CauseManque, str] = {
    "recherche_epuisee": "la source a été lue, la donnée n'y est pas publiée",
    "source_indisponible": "la source n'a pas pu être lue (panne ou temps épuisé) — une relance "
                           "peut la ramener",
    "sans_source_possible": "aucune source ne produit cette information pour cette société — "
                            "c'est la question qu'il faut reformuler",
    "pieces_insuffisantes": "toutes les pièces prévues ont été collectées, mais elles ne suffisent "
                            "pas à fonder une réponse",
    "pas_encore_cherchee": "aucune collecte n'a encore été lancée sur cette question",
    "fait_nouveau_publie": "un fait important publié depuis rend les pièces caduques",
    "actualite_indeterminable": "les pièces ne sont pas datables : leur fraîcheur n'est pas prouvée",
    "controle_ko": "le contrôle du manager a refusé la réponse",
    "renvoi_comite": "le comité a renvoyé la question en recherche ; aucune réponse n'a encore été "
                     "écrite depuis",
    "reinitialisation": "la question a été remise à zéro ; aucune réponse n'a encore été écrite "
                        "depuis",
    "pas_encore_observable": "l'analyste juge que l'information n'existe pas encore — aucune "
                             "recherche n'est relancée avant la date de revue ; au comité de juger "
                             "la cause (accepter, ou renvoyer en recherche)",
}


def _note_baisse(r: "ReponseLue") -> str:
    """Point 13 — « le motif du manque d'une question en baisse le dit. » Un fragment à ajouter en
    fin d'`explication` quand la réponse choisie par une branche du manque est ELLE-MÊME une baisse
    à lire ; vide sinon. `r.baisse` est `None` pour la plupart des réponses (le cas courant)."""
    if r.baisse is None:
        return ""
    b = r.baisse
    return (f" ; révisée à la baisse le {b.courante.cree_le:%Y-%m-%d} — la précédente était "
           f"`{b.precedente.statut}` (#{b.precedente.answer_id}) : {b.precedente.resume}")


def _cause_de_collecte(collecte: Optional[Collecte]) -> tuple[CauseManque, list[IngredientManquant]]:
    if collecte is None or collecte.plan_id is None:
        return "pas_encore_cherchee", []
    if not collecte.mandats:
        return "pieces_insuffisantes", []
    causes = {m.cause for m in collecte.mandats}
    tete = next(c for c in _PRECEDENCE_COLLECTE if c in causes)
    return tete, list(collecte.mandats)


def reponse_tient(r: ReponseLue) -> bool:
    """DÉTENTEUR UNIQUE (#46) de « cette réponse tient-elle AUJOURD'HUI ? » : acquittée par le contrôle,
    ET fondée sur des pièces toujours courantes (un fait important publié depuis la rend périmée), ou
    hors-sujet motivé. Lu par la règle du manque et par la valorisation, qui ne reprend que le chiffre
    d'une réponse qui tient (`valorisation/signature.py`). Pure."""
    a = r.servie
    if r.verdict != "acquitte":
        return False
    if a.statut == "sans_objet":
        return True
    return a.statut in ("repondu", "approxime") and a.fondation is not None \
        and a.fondation.actualite == "courante"


def manque_de_la_question(
    *,
    framework_id: str,
    libelle_framework: str,
    question_id: str,
    enonce: str,
    applicable: bool,
    dispensee: bool,
    reponses: list[ReponseLue],
    collecte: Optional[Collecte],
    mandat_ouvert_id: Optional[int],
    acceptation: Optional[AcceptationServie] = None,
    decision_ouvrante: Optional[DecisionComite] = None,
    aujourd_hui: Optional[date] = None,
) -> Optional[Manque]:
    """DÉTENTEUR UNIQUE (#46) de « cette question manque-t-elle au dossier, et pourquoi ? ». Pure.

    L'ordre des branches EST la doctrine :
      1. inapplicable ou dispensée (le comité a accepté le trou) → pas un manque ;
      1bis. une ACCEPTATION DU COMITÉ en vigueur → pas un manque : le comité a lu la réponse et passé
         outre sa faiblesse, par écrit (arbitrage n°1). Tombée, elle ne protège plus rien, et le
         manque la PORTE pour dire pourquoi la question repasse devant le comité (arbitrage n°2) ;
      1ter. la dernière décision du comité ROUVRE la question (renvoi, réinitialisation — #137) :
         seules les réponses écrites APRÈS elle comptent ; s'il n'y en a aucune, la question est
         ouverte (`rouverte_comite`), même si une réponse antérieure « tenait » ;
      2. une réponse acquittée qui tient AUJOURD'HUI (fondée et courante, ou hors-sujet motivé) →
         pas un manque — deux analystes sont deux points : il suffit qu'un point tienne ;
      3. sinon, le manque le plus actionnable : une réponse RENVOYÉE (le contrôle nomme sa cause),
         puis une réponse PÉRIMÉE (un fait nouveau, ou une date qui manque), puis NON FONDÉE, puis
         l'absence de réponse — ces deux dernières prennent leur cause dans la dernière collecte.
    """
    if not applicable or dispensee:
        return None
    if acceptation is not None and acceptation.etat == "en_vigueur":
        return None

    commun = dict(framework_id=framework_id, libelle_framework=libelle_framework,
                  question_id=question_id, enonce=enonce, mandat_ouvert_id=mandat_ouvert_id,
                  acceptation_tombee=acceptation)

    if decision_ouvrante is not None:
        if decision_ouvrante.action not in ACTIONS_OUVRANTES:
            raise ValueError(f"décision `{decision_ouvrante.action}` passée comme ouvrante")
        reponses = [r for r in reponses
                    if r.cree_le is not None and r.cree_le > decision_ouvrante.decide_le]
        if not reponses:
            cause = "renvoi_comite" if decision_ouvrante.action == "renvoyer" else "reinitialisation"
            return Manque(nature="rouverte_comite", cause=cause,
                          explication=f"{_EXPLICATION[cause]} ({decision_ouvrante.auteur}, "
                                      f"{decision_ouvrante.decide_le:%Y-%m-%d} : "
                                      f"{decision_ouvrante.motif})", **commun)

    if any(reponse_tient(r) for r in reponses):
        return None

    renvoyees = [r for r in reponses if r.verdict == "renvoye"]
    if renvoyees:
        r = renvoyees[0]
        return Manque(nature="renvoyee", cause="controle_ko", answer_id=r.answer_id,
                      explication=f"{_EXPLICATION['controle_ko']} : {r.motif_revue}"
                                  f"{_note_baisse(r)}", **commun)

    fondees = [r for r in reponses
               if r.servie.statut in ("repondu", "approxime") and r.servie.fondation is not None]
    for etat, cause in (("perimee", "fait_nouveau_publie"),
                        ("indeterminable", "actualite_indeterminable")):
        vieilles = [r for r in fondees if r.servie.fondation.actualite == etat]
        if vieilles:
            r = vieilles[0]
            return Manque(nature="perimee", cause=cause, answer_id=r.answer_id,
                          explication=f"{_EXPLICATION[cause]} — "
                                      f"{r.servie.fondation.motif_actualite}{_note_baisse(r)}", **commun)

    cause, ingredients = _cause_de_collecte(collecte)
    non_fondees = [r for r in reponses if r.servie.statut == "non_fondable"]
    # #138 — une attente justifiée, et pas encore échue : la question reste à l'alerte (le comité juge
    # la cause), sous sa propre nature, pour qu'aucune relance ne la recollecte. Échue, elle retombe
    # dans le cas général ci-dessous : la question redevient cherchable d'elle-même, sans geste.
    jour = aujourd_hui or date.today()
    attentes = [r for r in non_fondees
                if r.servie.gap is not None and r.servie.gap.attente is not None
                and r.servie.gap.attente.revoir_le > jour]
    if attentes:
        r, att = attentes[0], attentes[0].servie.gap.attente
        return Manque(nature="pas_encore_observable", cause="pas_encore_observable",
                      answer_id=r.answer_id, attente=att,
                      explication=(f"{_EXPLICATION['pas_encore_observable']}. Cause : {att.cause} "
                                   f"Fait déclencheur : {att.fait_declencheur} ({att.depuis}, pièce "
                                   f"#{att.piece_du_fait}). Il faudra : {att.historique_requis}. "
                                   f"Revue le {att.revoir_le}.{_note_baisse(r)}"), **commun)
    if non_fondees:
        r = non_fondees[0]
        return Manque(nature="non_fondee", cause=cause, answer_id=r.answer_id,
                      explication=f"{_EXPLICATION[cause]}{_note_baisse(r)}", ingredients=ingredients,
                      **commun)
    return Manque(nature="sans_reponse", cause=cause, explication=_EXPLICATION[cause],
                  ingredients=ingredients, **commun)


# ── Les trois niveaux (PURS) ───────────────────────────────────────────────────────────────────

def _framework(etat: EtatDossier, framework_id: str):
    for f in etat.fichier.frameworks:
        if f.id == framework_id:
            return f
    raise ReferenceInconnue(f"framework `{framework_id}` absent du référentiel "
                            f"({[f.id for f in etat.fichier.frameworks]})")


def manque_pour_question(etat: EtatDossier, f, q) -> tuple[Optional[bool], Optional["Manque"]]:
    """Rend `(applicable, manque)` pour une question `q` d'un framework `f`, sur CET état de
    dossier — la préparation des arguments de `manque_de_la_question`, DÉTENTEUR UNIQUE (#46) :
    `_lignes` (ci-dessous) et `porte.porte_de_l_architecte` (M3) l'appellent tous deux, avec les
    MÊMES arguments, plutôt que de dupliquer cette extraction (`feedback_correctif_regle_jumeaux`)."""
    applicables = etat.applicables.get(f.id)
    dispenses = etat.dispenses.get(f.id, frozenset())
    reps = [r for r in etat.reponses
            if r.servie.framework_id == f.id and r.servie.question_id == q.id]
    applicable = None if applicables is None else q.id in applicables
    position = etat.comite.get((f.id, q.id))
    if applicable is None:
        return None, None
    manque = manque_de_la_question(
        framework_id=f.id, libelle_framework=f.libelle, question_id=q.id,
        enonce=q.enonce, applicable=applicable, dispensee=q.id in dispenses,
        reponses=reps, collecte=etat.collecte.get((f.id, q.id)),
        mandat_ouvert_id=etat.mandats_ouverts.get((f.id, q.id)),
        acceptation=position.acceptation if position else None,
        decision_ouvrante=(position.derniere if position is not None
                           and position.derniere.action in ACTIONS_OUVRANTES else None),
        aujourd_hui=etat.genere_le.date())
    return applicable, manque


def _lignes(etat: EtatDossier, f) -> list[LigneQuestion]:
    dispenses = etat.dispenses.get(f.id, frozenset())
    lignes = []
    for q in f.questions:
        reps = [r for r in etat.reponses
                if r.servie.framework_id == f.id and r.servie.question_id == q.id]
        applicable, manque = manque_pour_question(etat, f, q)
        position = etat.comite.get((f.id, q.id))
        # Point 13 — UNE baisse par ligne (le cas courant : au plus une réponse courante en baisse
        # par question ; la première rencontrée si plusieurs analystes en portaient une).
        baisse = next((r.baisse for r in reps if r.baisse is not None), None)
        lignes.append(LigneQuestion(
            question_id=q.id, enonce=q.enonce, applicable=applicable,
            dispensee=q.id in dispenses, manque=manque, comite=position, baisse=baisse,
            reponses=[ReponseResumee(
                answer_id=r.answer_id, analyste=r.servie.analyste, statut=r.servie.statut,
                rang_derive=r.servie.fondation.rang_derive if r.servie.fondation else None,
                actualite=r.servie.fondation.actualite if r.servie.fondation else None,
                verdict=r.verdict, controles=r.controles,
                standard_anterieur=standard_anterieur(etat, r.servie),
                n_chiffres_sans_piece=len(r.servie.chiffres_sans_piece)) for r in reps],
        ))
    return lignes


class EmetteurNonClasse(LookupError):
    """Sans classement de l'émetteur, on ne sait pas quelles questions s'appliquent, donc pas ce qui
    est ouvert : la relance bornée refuse plutôt que de tout refaire (ou de ne rien faire)."""


@dataclass(frozen=True)
class PerimetreRelance:
    """Ce qu'une relance d'un chapitre refait, et pourquoi elle laisse le reste (#137, point 17)."""
    framework_id: str
    ouvertes: tuple[str, ...]                 # dans l'ordre du référentiel
    closes: dict[str, str]                    # question → pourquoi on n'y touche pas


def questions_a_relancer(etat: EtatDossier, framework_id: str) -> PerimetreRelance:
    """DÉTENTEUR UNIQUE (#46) de « que refait une relance de ce chapitre ? » (#137, point 17). Pure.

    Une relance ne porte QUE sur les questions OUVERTES — celles dont `manque_de_la_question` dit
    qu'elles manquent : sans réponse, non fondée, périmée, renvoyée (manager ou comité), réinitialisée.
    Une question CLOSE (à jour, acceptée par le comité, dispensée) n'est jamais refaite : un fonds ne
    défait pas une décision du comité en refaisant le travail ; seul le gérant la rouvre, par une
    réinitialisation tracée au PV. Une question hors sujet pour l'émetteur n'est ni l'une ni l'autre.
    """
    f = _framework(etat, framework_id)
    if etat.applicables.get(f.id) is None:
        raise EmetteurNonClasse(
            f"`{etat.ticker_id}` n'est pas classé : on ne sait pas quelles questions de "
            f"`{framework_id}` s'appliquent, donc pas lesquelles sont ouvertes — classer l'émetteur "
            "d'abord (`tools/classer_emetteur.sh`)")
    ouvertes, closes = [], {}
    for lq in _lignes(etat, f):
        if lq.manque is not None and lq.manque.nature == "pas_encore_observable":
            # #138 — ouverte au comité, FERMÉE à la relance : on ne recollecte pas ce qui n'est pas
            # advenu. Rouverte par la date de revue, un renvoi ou une remise à zéro du comité.
            att = lq.manque.attente
            closes[lq.question_id] = (f"pas encore observable jusqu'au {att.revoir_le} — "
                                      f"{att.cause} (cause à juger par le comité)")
        elif lq.manque is not None:
            ouvertes.append(lq.question_id)
        elif not lq.applicable:
            closes[lq.question_id] = "hors sujet pour cet émetteur"
        elif lq.dispensee:
            closes[lq.question_id] = "dispensée"
        elif _acceptee(lq):
            d = lq.comite.derniere
            closes[lq.question_id] = (f"acceptée par le comité ({d.auteur}, "
                                      f"{d.decide_le:%Y-%m-%d}, réponse #{d.answer_id})")
        else:
            tient = [r.answer_id for r in lq.reponses if r.verdict == "acquitte"]
            closes[lq.question_id] = f"à jour (réponse #{tient[0] if tient else '?'} acquittée et courante)"
    return PerimetreRelance(framework_id=f.id, ouvertes=tuple(ouvertes), closes=closes)


def _synthese(etat: EtatDossier, f, lignes: list[LigneQuestion]) -> SyntheseFramework:
    from app.agents.v2.qualite_info import derive_qualite_info

    reps = [r for r in etat.reponses if r.servie.framework_id == f.id]
    mesures = derive_qualite_info([r.servie for r in reps])
    applicables = etat.applicables.get(f.id)
    return SyntheseFramework(
        framework_id=f.id, libelle=f.libelle, methodologie=f.methodologie,
        framework_version=etat.fichier.schema_version,
        qualite=mesures[0] if mesures else None,
        n_questions=len(f.questions),
        n_applicables=None if applicables is None else len(applicables),
        n_acquittees=sum(1 for r in reps if r.verdict == "acquitte"),
        n_renvoyees=sum(1 for r in reps if r.verdict == "renvoye"),
        n_manques=sum(1 for lq in lignes if lq.manque is not None),
        n_acceptees_comite=sum(1 for lq in lignes if lq.applicable and _acceptee(lq)),
        n_standard_anterieur=sum(1 for lq in lignes for r in lq.reponses if r.standard_anterieur),
        n_chiffres_sans_piece=sum(r.n_chiffres_sans_piece for lq in lignes for r in lq.reponses),
        n_pas_encore_observable=sum(1 for lq in lignes if lq.manque is not None
                                    and lq.manque.nature == "pas_encore_observable"),
    )


def _acceptee(lq: LigneQuestion) -> bool:
    """L'acceptation du comité tient-elle sur cette ligne aujourd'hui ?"""
    return (lq.comite is not None and lq.comite.acceptation is not None
            and lq.comite.acceptation.etat == "en_vigueur")


def dresser_niveau1(etat: EtatDossier, memo) -> DossierTitre:
    """NIVEAU 1 : l'alerte en tête, puis la note de chaque méthodologie, puis la note de comité."""
    syntheses, manques, baisses, acceptees = [], [], [], 0
    for f in etat.fichier.frameworks:
        lignes = _lignes(etat, f)
        syntheses.append(_synthese(etat, f, lignes))
        manques.extend(lq.manque for lq in lignes if lq.manque is not None)
        baisses.extend(lq.baisse for lq in lignes if lq.baisse is not None)
        acceptees += sum(1 for lq in lignes if lq.applicable and _acceptee(lq))

    if etat.archetype is None:
        pod = PeutOnDecider(
            etat="non_revalidable",
            motif="la société n'est pas classée : on ne sait pas quelles questions s'appliquent à "
                  "elle, donc ni le contrôle ni l'alerte ne peuvent être dressés")
    elif manques:
        n = len(manques)
        pod = PeutOnDecider(
            etat="dossier_incomplet", manques=manques,
            motif=(f"{n} questions applicables sans réponse qui tienne aujourd'hui — le système "
                   "n'a pas pu les obtenir" if n > 1 else
                   "1 question applicable sans réponse qui tienne aujourd'hui — le système n'a "
                   "pas pu l'obtenir"))
    elif etat.recommandation is not None:
        # #139 — un reclassement en suspens change la GRILLE : les questions applicables d'aujourd'hui
        # ne sont peut-être plus les bonnes. « Complet » sur une grille que le comité doit revoir
        # tairait l'alerte ; le dossier attend sa décision.
        r = etat.recommandation
        pod = PeutOnDecider(
            etat="non_revalidable",
            motif=(f"toutes les questions de la grille « {r.de} » ont une réponse qui tient, mais le "
                   f"dépôt du {r.fait_du.strftime('%d/%m/%Y')} recommande de reclasser l'émetteur "
                   f"« {r.vers} » : le comité doit reclasser ou maintenir avant de conclure"))
    elif baisses:
        # Point 13 — même forme que la recommandation de reclassement ci-dessus : une baisse à lire
        # empêche « dossier complet », SEULE quand rien d'autre ne manque déjà (sinon elle est
        # listée à côté des manques, sans changer l'état — c'est `baisses` passé plus bas, toujours).
        n = len(baisses)
        b0 = baisses[0]
        pod = PeutOnDecider(
            etat="non_revalidable",
            motif=(f"{n} révision(s) à la baisse à lire par le comité — toutes les autres questions "
                   "applicables tiennent. La première : "
                   f"#{b0.courante.answer_id} (`{b0.courante.statut}`), dont la précédente "
                   f"#{b0.precedente.answer_id} était `{b0.precedente.statut}`"))
    else:
        # Le comité doit savoir que la complétude repose en partie sur SES acceptations : un dossier
        # complet « parce que le comité a passé outre » ne se lit pas comme un dossier sans faiblesse.
        pod = PeutOnDecider(etat="dossier_complet",
                            motif="toutes les questions applicables ont une réponse acquittée et "
                                  "à jour" + (f", dont {acceptees} acceptée(s) par le comité malgré "
                                              "leur faiblesse" if acceptees else ""))
    return DossierTitre(ticker_id=etat.ticker_id, archetype=etat.archetype,
                        genere_le=etat.genere_le, peut_on_decider=pod,
                        frameworks=syntheses, memo=memo,
                        classement=_classement_servi(etat.classement),
                        reclassement_recommande=_recommandation_servie(etat.recommandation),
                        baisses=baisses)


def _classement_servi(c) -> Optional[ClassementServi]:
    if c is None:
        return None
    return ClassementServi(archetype=c.archetype, depuis=c.effective_from, motif=c.motif,
                           auteur=c.auteur, piece_id=c.piece_id,
                           declencheur_accession=c.declencheur_accession)


def _recommandation_servie(r) -> Optional[ReclassementRecommande]:
    if r is None:
        return None
    return ReclassementRecommande(de=r.de, vers=r.vers, fait_du=r.fait_du, accession=r.accession,
                                  type_id=r.type_id, resume=r.resume)


def dresser_niveau2(etat: EtatDossier, framework_id: str) -> FrameworkDuDossier:
    f = _framework(etat, framework_id)
    lignes = _lignes(etat, f)
    return FrameworkDuDossier(ticker_id=etat.ticker_id, archetype=etat.archetype,
                              synthese=_synthese(etat, f, lignes), questions=lignes)


def _pieces(etat: EtatDossier, a: FrameworkAnswer) -> list[PieceCitee]:
    vus: list[tuple[int, str]] = []
    if a.fondation is not None:
        vus += [(i, "citee") for i in a.fondation.cited_entry_ids]
    if a.approximation is not None:
        vus += [(i, "ingredient") for i in a.approximation.ingredients_entry_ids]
    pieces, deja = [], set()
    for i, role in vus:
        if (i, role) in deja:
            continue
        deja.add((i, role))
        p = etat.pieces.get(i)
        if p is None:
            pieces.append(PieceCitee(entry_id=i, role=role, present_au_corpus=False, au_standard=None))
            continue
        pieces.append(PieceCitee(
            entry_id=i, role=role, present_au_corpus=True, titre=p["title"],
            source_type=p["source_type"], source_url=p["source_url"],
            source_date=p["source_date"], date_du_fait=p["date_du_fait"],
            reliability_tier=p["reliability_tier"], nature=p["nature"],
            remplacee=p["superseded_by"] is not None,
            au_standard=piece_au_standard(source_type=p["source_type"], tags=p["tags"],
                                          metric=p["metric"], debut_contenu=p["debut_contenu"])))
    return pieces


def corpus_des_regles(pieces: dict[int, dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Le corpus que lisent les RÈGLES au point de lecture : la date (actualité), le rang (contrôle ③) et le
    TEXTE (le recoupement des chiffres, #136). Sans le texte, chaque chiffre de chaque réponse passait
    pour « sans pièce » (mesuré au déploiement de #136 : 38 sur NVDA qualité financière, contre 2). Une
    colonne non chargée lève ici, elle ne se lit jamais comme un texte vide."""
    return {i: {"source_date": p["source_date"], "reliability_tier": p["reliability_tier"],
                "title": p["title"], "content": p["content"]} for i, p in pieces.items()}


def standard_anterieur(etat: EtatDossier, a: FrameworkAnswer) -> bool:
    """La réponse s'appuie-t-elle sur au moins une pièce au standard antérieur (#127) ? Lue sur les
    pièces que `_pieces` sert — un seul assemblage, donc les trois niveaux disent la même chose."""
    return any(p.au_standard is False for p in _pieces(etat, a))


def dresser_niveau3(etat: EtatDossier, framework_id: str, question_id: str) -> PreuvesQuestion:
    f = _framework(etat, framework_id)
    q = next((q for q in f.questions if q.id == question_id), None)
    if q is None:
        raise ReferenceInconnue(f"question `{question_id}` inconnue du framework `{framework_id}`")
    ligne = next(lq for lq in _lignes(etat, f) if lq.question_id == question_id)
    preuves = []
    for r in etat.reponses:
        a = r.servie
        if a.framework_id != framework_id or a.question_id != question_id:
            continue
        pieces = _pieces(etat, a)
        tiers = [p.reliability_tier for p in pieces
                 if p.role == "citee" and p.reliability_tier is not None]
        preuves.append(PreuveReponse(
            answer_id=r.answer_id, answer=a, etat_revue=r.etat_revue,  # type: ignore[arg-type]
            renvoi_a_emettre=(RenvoiAEmettre(controles=r.controles, motif=r.motif_revue)
                              if r.etat_revue == "renvoi_a_emettre" else None),
            pieces=pieces,
            rang_plus_faible_cite=_plus_faible(tiers) if tiers else None))  # type: ignore[arg-type]
    return PreuvesQuestion(
        ticker_id=etat.ticker_id, framework_id=f.id, libelle_framework=f.libelle,
        framework_version=etat.fichier.schema_version, question_id=q.id, enonce=q.enonce,
        applicable=ligne.applicable, preuves=preuves, manque=ligne.manque,
        comite=ligne.comite, registre=etat.registre.get((f.id, q.id), []), baisse=ligne.baisse)


# ── La seule moitié qui lit ────────────────────────────────────────────────────────────────────

async def _collectes(conn, ticker_id: str, version: str) -> dict[tuple[str, str], Collecte]:
    """Par (framework, question) : la DERNIÈRE collecte qui l'a couverte. « Dernière » par question,
    pas par framework : un bouclage re-collecte seulement les questions renvoyées, et son plan ne
    doit pas effacer celui des autres questions."""
    rows = await conn.fetch(
        "SELECT DISTINCT ON (p.framework_id, i.question_id) "
        "       p.framework_id, i.question_id, p.id AS plan_id "
        "FROM collection_plans p JOIN collection_plan_items i ON i.plan_id = p.id "
        "WHERE p.ticker_id = $1 AND p.framework_version = $2 "
        "ORDER BY p.framework_id, i.question_id, p.id DESC",
        ticker_id, version)
    derniers = {(r["framework_id"], r["question_id"]): r["plan_id"] for r in rows}
    if not derniers:
        return {}
    items = await conn.fetch(
        "SELECT plan_id, question_id, ingredient_id FROM collection_plan_items "
        "WHERE plan_id = ANY($1::int[]) ORDER BY id", sorted(set(derniers.values())))
    mandats = await conn.fetch(
        "SELECT plan_id, question_id, ingredient_id, cause, motif, created_at "
        "FROM framework_mandates WHERE plan_id = ANY($1::int[]) "
        "AND origine IN ('inobtenable', 'echec_collecte') ORDER BY id",
        sorted(set(derniers.values())))
    out: dict[tuple[str, str], Collecte] = {}
    for (fid, qid), pid in derniers.items():
        out[(fid, qid)] = Collecte(
            plan_id=pid,
            ingredients_vus=tuple(r["ingredient_id"] for r in items
                                  if r["plan_id"] == pid and r["question_id"] == qid),
            mandats=tuple(IngredientManquant(
                ingredient_id=m["ingredient_id"], cause=m["cause"], motif=m["motif"],
                constate_le=m["created_at"])
                for m in mandats if m["plan_id"] == pid and m["question_id"] == qid),
        )
    return out


async def horloge_du_titre(conn, ticker_id: str, fichier) -> tuple[Any, dict[str, Any]]:
    """L'ancre qui pèse + les notes flash relues — le montage de l'horloge, DÉTENTEUR UNIQUE : la lecture
    du dossier (`charger_etat_dossier`) et l'analyste (`faits_posterieurs_du_titre`) doivent voir la même,
    sinon l'analyste lirait des faits que la lecture ne retire pas, ou l'inverse (#46)."""
    from app.agents.v2.note_flash import qualifications_de_l_emetteur
    from app.knowledge.material_events import ancre_substantielle, material_anchor_for_ticker

    # L'ancre qui PÈSE, jamais la dernière venue (#54, arbitrage du comité n°2 du 2026-09-25) : une
    # information de routine — un 8-K de pure forme — ne remet pas une réponse en cause. Les deux
    # assembleurs d'avant lisaient l'ancre brute, là où la porte de complétude lisait déjà celle-ci :
    # un 8-K formel aurait périmé la note projetée sans périmer la readiness.
    ancre = ancre_substantielle(await material_anchor_for_ticker(conn, ticker_id))
    # ⚠️ CHAQUE QUESTION A SA PROPRE HORLOGE (#89) : son ancre est le dernier fait important d'un
    # TYPE qui la rouvre (référentiel, `rouverte_par`). Juger toutes les questions contre le dernier
    # fait venu fabriquait les deux erreurs : un financement périmait la barrière brevetaire, et —
    # pire — dire « un financement ne périme pas le moat » contre le DERNIER fait aurait rendu à
    # jour un moat que l'approbation FDA de la veille devait rouvrir.
    # Ce que les notes flash ont LU des dépôts que la forme ne qualifie pas (maillon 2) : sans elles,
    # chaque 8.01 rouvre tout ; avec elles, il rouvre ce qu'il touche. Relu à chaque assemblage.
    notes = await qualifications_de_l_emetteur(conn, ancre.cik, fichier)
    return ancre, notes


async def faits_posterieurs_du_titre(conn, ticker_id: str, fichier, framework_id: str) -> dict[str, list]:
    """Par question du framework : les faits postérieurs aux derniers comptes que l'analyste peut lire
    (#103), contre l'horloge même qui servira ses réponses. N'écrit rien."""
    from app.agents.v2.frameworks import types_qui_rouvrent
    from app.knowledge.evenements import ancre_de_la_question, derniere_cloture_publiee, faits_a_lire

    ancre, notes = await horloge_du_titre(conn, ticker_id, fichier)
    cloture = derniere_cloture_publiee(ancre)
    fw = next(f for f in fichier.frameworks if f.id == framework_id)
    return {q.id: faits_a_lire(ancre_de_la_question(ancre, rouvrent=types_qui_rouvrent(fichier, q.id),
                                                    qualifications=notes), cloture=cloture)
            for q in fw.questions}


async def contexte_durees(conn, *, fichier, version: str, ancre_titre, cites: set[int]):
    """DÉTENTEUR UNIQUE du contexte de la règle de fraîcheur par durée de vie (2026-10-16) : les
    clôtures lues sur l'horloge du TITRE, et — question par question — les ingrédients que fonde chaque
    pièce citée (index de couverture `question_coverage`, à la version du référentiel). `None` quand
    l'interrupteur `fraicheur_par_duree_de_vie` est coupé : le point de lecture applique l'ordre 0."""
    from app.knowledge.duree_de_vie import Clotures, ContexteDurees, DureeIngredient
    from app.knowledge.evenements import derniere_cloture_annuelle_publiee, derniere_cloture_publiee

    if not fichier.fraicheur_par_duree_de_vie:
        return None
    definitions = {(q.id, i.id): i for f in fichier.frameworks for q in f.questions
                   for i in q.ingredients_requis}
    framework_de = {q.id: f.id for f in fichier.frameworks for q in f.questions}
    # La durée de vie est une propriété de la MATIÈRE — ce pour quoi la pièce a été collectée —, pas de la
    # question qui la cite : l'analyste voit tout le dossier de son chapitre (#108) et cite à bon droit une
    # pièce collectée pour une question voisine (mesuré le 2026-10-16 : RVMD ma_3 cite #1368, collectée
    # pour ma_1). Rattachée à la question qui la cite : ses ingrédients-là ; sinon, ceux du MÊME chapitre ;
    # rattachée nulle part (socle, lecture de dépôt) : aucune, la règle prend la durée la plus courte.
    propres: dict[tuple[str, int], list] = {}
    du_chapitre: dict[tuple[str, int], list] = {}
    if cites:
        rows = await conn.fetch(
            "SELECT DISTINCT question_id, ingredient_id, entry_id FROM question_coverage "
            "WHERE framework_version = $1 AND entry_id = ANY($2::int[])", version, sorted(cites))
        for r in rows:
            ing = definitions.get((r["question_id"], r["ingredient_id"]))
            if ing is None:
                continue
            d = DureeIngredient(ingredient_id=ing.id, duree_de_vie=ing.duree_de_vie, cadence=ing.cadence)
            propres.setdefault((r["question_id"], r["entry_id"]), []).append(d)
            du_chapitre.setdefault((framework_de[r["question_id"]], r["entry_id"]), []).append(d)
    par_question: dict[str, dict[int, list]] = {}
    for qid, fid in framework_de.items():
        for e in cites:
            ings = propres.get((qid, e)) or du_chapitre.get((fid, e))
            if ings:
                par_question.setdefault(qid, {})[e] = ings
    lk = ancre_titre if ancre_titre.status == "found" else None
    return ContexteDurees(
        clotures=Clotures(derniere=derniere_cloture_publiee(lk) if lk else None,
                          exercice=derniere_cloture_annuelle_publiee(lk) if lk else None),
        ingredients_des_pieces=par_question, par_sujet=fichier.fraicheur_par_sujet)


async def charger_etat_dossier(conn, ticker_id: str) -> EtatDossier:
    """Base → revue RECALCULÉE → réponses servies. N'écrit rien — ni verdict, ni mandat, ni note.

    ⚠️ L'AVIS DU MANAGER SE RECALCULE ICI (#77) : les 4 contrôles dépendent du corpus, des dispenses
    et de l'actualité, qui bougent. Un renvoi recalculé se complète par l'id du mandat OUVERT sur la
    question (`id_du_mandat_ouvert`, détenteur unique) ; s'il n'y en a pas, on n'en invente pas :
    `renvoi_a_emettre`.
    """
    # Imports tardifs : ce module est importé par des checks sans base ni réseau.
    from app.agents.v2.comite import lire_registre, position_du_comite
    from app.agents.v2.frameworks import servir_answer, types_qui_rouvrent
    from app.knowledge.evenements import ancre_de_la_question
    from app.knowledge.material_events import MaterialEventLookup
    from app.agents.v2.framework_persist import (
        read_answers_courantes, read_classement, read_dispenses)
    from app.agents.v2.classement import recommandation_de_classement
    from app.agents.v2.manager import reviser_framework
    from app.agents.v2.manager_persist import assemble_verdict
    from app.agents.v2.revision import ReponsePourBaisse, baisse_a_lire, precedente_validee
    from app.agents.v2.traducteur import questions_applicables

    fichier = load_frameworks()
    version = fichier.schema_version
    brutes = await read_answers_courantes(conn, ticker_id=ticker_id, framework_version=version)

    cites: set[int] = set()
    for _id, a in brutes:
        if a.fondation is not None:
            cites.update(a.fondation.cited_entry_ids)
        if a.approximation is not None:
            cites.update(a.approximation.ingredients_entry_ids)
        if a.reponse is not None:  # #136 — les pièces d'un fait lu fondent aussi les chiffres de son effet
            for f in a.reponse.faits_posterieurs:
                cites.update(f.cited_entry_ids)

    pieces: dict[int, dict[str, Any]] = {}
    if cites:
        rows = await conn.fetch(
            "SELECT id, title, content, source_type, source_url, source_date, date_du_fait, "
            f"reliability_tier, nature, superseded_by, {COLONNES_SQL} FROM knowledge_entries "
            "WHERE id = ANY($1::int[])", sorted(cites))
        pieces = {r["id"]: dict(r) for r in rows}
    entries = corpus_des_regles(pieces)

    classement = await read_classement(conn, ticker_id=ticker_id)
    archetype = classement.archetype if classement is not None else None

    ouverts = await conn.fetch(
        "SELECT framework_id, question_id, min(id) AS id FROM framework_mandates "
        "WHERE ticker_id = $1 AND framework_version = $2 "
        "AND origine IN ('manager_renvoi', 'comite') AND statut = 'ouvert' "
        "GROUP BY framework_id, question_id", ticker_id, version)
    mandats_ouverts = {(r["framework_id"], r["question_id"]): r["id"] for r in ouverts}

    applicables: dict[str, Optional[frozenset[str]]] = {}
    dispenses: dict[str, frozenset[str]] = {}
    decisions: dict[int, Any] = {}
    par_ligne = {i: a for i, a in brutes}
    for f in fichier.frameworks:
        dispenses[f.id] = frozenset(await read_dispenses(
            conn, ticker_id=ticker_id, framework_id=f.id, framework_version=version))
        if archetype is None:
            applicables[f.id] = None
            continue
        applicables[f.id] = frozenset(
            q.id for q in questions_applicables(fichier, f.id, archetype))
        du_framework = [(i, a) for i, a in brutes if a.framework_id == f.id]
        if not du_framework:
            continue
        revue = reviser_framework(
            [a for _i, a in du_framework], fichier=fichier, framework_id=f.id,
            archetype=archetype, ticker_id=ticker_id, entries=entries,
            dispenses=dispenses[f.id], autres_reponses=par_ligne)
        for i, a in du_framework:
            decisions[i] = revue.decisions.get((a.question_id, a.analyste))

    ancre, notes = await horloge_du_titre(conn, ticker_id, fichier)
    ancres: dict[str, MaterialEventLookup] = {}

    def ancre_de(question_id: str) -> MaterialEventLookup:
        if question_id not in ancres:
            ancres[question_id] = ancre_de_la_question(
                ancre, rouvrent=types_qui_rouvrent(fichier, question_id), qualifications=notes)
        return ancres[question_id]

    durees = await contexte_durees(conn, fichier=fichier, version=version, ancre_titre=ancre,
                                   cites=cites)

    # Le PV du comité — chargé ICI (avant les réponses) : le point 13 (révision à la baisse) juge
    # chaque réponse courante contre le registre de SA question, au même titre que le reste.
    registre = await lire_registre(conn, ticker_id=ticker_id, framework_version=version)

    cree_le = {r["id"]: r["created_at"] for r in await conn.fetch(
        "SELECT id, created_at FROM framework_answers WHERE id = ANY($1::int[])",
        [i for i, _a in brutes])}
    # Point 13 — la PRÉCÉDENTE IMMÉDIATE de chaque réponse courante, en UNE requête (la table porte
    # déjà la relation : `superseded_by` pointe de la précédente vers la courante).
    precedentes_brutes = (await conn.fetch(
        "SELECT id, statut, answer_json, created_at, superseded_by FROM framework_answers "
        "WHERE superseded_by = ANY($1::int[])", [i for i, _a in brutes]) if brutes else [])
    precedente_de = {r["superseded_by"]: r for r in precedentes_brutes}

    reponses: list[ReponseLue] = []
    for i, a in brutes:
        d = decisions.get(i)
        etat_revue, verdict, controles, motif = "non_revalidable", None, None, None
        if d is not None:
            verdict, controles, motif = d.verdict, d.controles, d.motif
            mandat_id = mandats_ouverts.get((a.framework_id, a.question_id))
            if d.verdict == "acquitte" or mandat_id is not None:
                # `model_copy` ne valide pas ; `servir_answer` reconstruit l'objet depuis le dump,
                # donc l'avis attaché repasse par le contrat entier.
                a = a.model_copy(update={"manager": assemble_verdict(
                    d, mandat_de_recherche_id=mandat_id)})
                etat_revue = "revue"
            else:
                etat_revue = "renvoi_a_emettre"
        baisse = None
        prec_row = precedente_de.get(i)
        if prec_row is not None:
            prec_rpb = ReponsePourBaisse(
                answer_id=prec_row["id"], cree_le=prec_row["created_at"],
                statut_brut=prec_row["statut"],
                answer=precedente_validee(prec_row["statut"], prec_row["answer_json"]))
            cour_rpb = ReponsePourBaisse(answer_id=i, cree_le=cree_le.get(i), statut_brut=a.statut,
                                         answer=a)
            baisse = baisse_a_lire(
                cour_rpb, prec_rpb, registre.get((a.framework_id, a.question_id), []))
        reponses.append(ReponseLue(
            answer_id=i, servie=servir_answer(a, ancre=ancre_de(a.question_id), entries=entries,
                                              durees=durees),
            verdict=verdict, controles=controles, motif_revue=motif, etat_revue=etat_revue,
            cree_le=cree_le.get(i), baisse=baisse))

    # Le COMITÉ : sa position du jour recalculée contre la MÊME ancre qui pèse (arbitrage n°2) et
    # les réponses COURANTES (une réponse refaite n'est pas celle que le comité a lue).
    courantes: dict[tuple[str, str], frozenset[int]] = {}
    for i, a in brutes:
        cle = (a.framework_id, a.question_id)
        courantes[cle] = courantes.get(cle, frozenset()) | {i}
    comite = {cle: position_du_comite(decisions, reponses_courantes=courantes.get(cle, frozenset()),
                                      ancre=ancre_de(cle[1]))
              for cle, decisions in registre.items()}

    return EtatDossier(
        ticker_id=ticker_id, fichier=fichier, archetype=archetype, reponses=reponses,
        pieces=pieces, applicables=applicables, dispenses=dispenses,
        mandats_ouverts=mandats_ouverts, collecte=await _collectes(conn, ticker_id, version),
        registre=registre, comite=comite, classement=classement,
        recommandation=recommandation_de_classement(classement, notes, fichier))
