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
from datetime import datetime, timezone
from typing import Any, Optional

from app.agents.v2.frameworks import _plus_faible, load_frameworks
from app.contracts.cause_manque_schema import CauseManqueCollecte
from app.contracts.framework_answer_schema import FrameworkAnswer, FrameworkAnswerServie
from app.contracts.framework_definition_schema import FrameworksFile
from app.contracts.parcours_schema import (
    CauseManque,
    DossierTitre,
    FrameworkDuDossier,
    IngredientManquant,
    LigneQuestion,
    Manque,
    PeutOnDecider,
    PieceCitee,
    PreuveReponse,
    PreuvesQuestion,
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
}


def _cause_de_collecte(collecte: Optional[Collecte]) -> tuple[CauseManque, list[IngredientManquant]]:
    if collecte is None or collecte.plan_id is None:
        return "pas_encore_cherchee", []
    if not collecte.mandats:
        return "pieces_insuffisantes", []
    causes = {m.cause for m in collecte.mandats}
    tete = next(c for c in _PRECEDENCE_COLLECTE if c in causes)
    return tete, list(collecte.mandats)


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
) -> Optional[Manque]:
    """DÉTENTEUR UNIQUE (#46) de « cette question manque-t-elle au dossier, et pourquoi ? ». Pure.

    L'ordre des branches EST la doctrine :
      1. inapplicable ou dispensée (le comité a accepté le trou) → pas un manque ;
      2. une réponse acquittée qui tient AUJOURD'HUI (fondée et courante, ou hors-sujet motivé) →
         pas un manque — deux analystes sont deux points : il suffit qu'un point tienne ;
      3. sinon, le manque le plus actionnable : une réponse RENVOYÉE (le contrôle nomme sa cause),
         puis une réponse PÉRIMÉE (un fait nouveau, ou une date qui manque), puis NON FONDÉE, puis
         l'absence de réponse — ces deux dernières prennent leur cause dans la dernière collecte.
    """
    if not applicable or dispensee:
        return None

    def tient(r: ReponseLue) -> bool:
        a = r.servie
        if r.verdict != "acquitte":
            return False
        if a.statut == "sans_objet":
            return True
        return a.statut in ("repondu", "approxime") and a.fondation is not None \
            and a.fondation.actualite == "courante"

    if any(tient(r) for r in reponses):
        return None

    commun = dict(framework_id=framework_id, libelle_framework=libelle_framework,
                  question_id=question_id, enonce=enonce, mandat_ouvert_id=mandat_ouvert_id)

    renvoyees = [r for r in reponses if r.verdict == "renvoye"]
    if renvoyees:
        r = renvoyees[0]
        return Manque(nature="renvoyee", cause="controle_ko", answer_id=r.answer_id,
                      explication=f"{_EXPLICATION['controle_ko']} : {r.motif_revue}", **commun)

    fondees = [r for r in reponses
               if r.servie.statut in ("repondu", "approxime") and r.servie.fondation is not None]
    for etat, cause in (("perimee", "fait_nouveau_publie"),
                        ("indeterminable", "actualite_indeterminable")):
        vieilles = [r for r in fondees if r.servie.fondation.actualite == etat]
        if vieilles:
            r = vieilles[0]
            return Manque(nature="perimee", cause=cause, answer_id=r.answer_id,
                          explication=f"{_EXPLICATION[cause]} — "
                                      f"{r.servie.fondation.motif_actualite}", **commun)

    cause, ingredients = _cause_de_collecte(collecte)
    non_fondees = [r for r in reponses if r.servie.statut == "non_fondable"]
    if non_fondees:
        return Manque(nature="non_fondee", cause=cause, answer_id=non_fondees[0].answer_id,
                      explication=_EXPLICATION[cause], ingredients=ingredients, **commun)
    return Manque(nature="sans_reponse", cause=cause, explication=_EXPLICATION[cause],
                  ingredients=ingredients, **commun)


# ── Les trois niveaux (PURS) ───────────────────────────────────────────────────────────────────

def _framework(etat: EtatDossier, framework_id: str):
    for f in etat.fichier.frameworks:
        if f.id == framework_id:
            return f
    raise ReferenceInconnue(f"framework `{framework_id}` absent du référentiel "
                            f"({[f.id for f in etat.fichier.frameworks]})")


def _lignes(etat: EtatDossier, f) -> list[LigneQuestion]:
    applicables = etat.applicables.get(f.id)
    dispenses = etat.dispenses.get(f.id, frozenset())
    lignes = []
    for q in f.questions:
        reps = [r for r in etat.reponses
                if r.servie.framework_id == f.id and r.servie.question_id == q.id]
        applicable = None if applicables is None else q.id in applicables
        manque = None
        if applicable is not None:
            manque = manque_de_la_question(
                framework_id=f.id, libelle_framework=f.libelle, question_id=q.id,
                enonce=q.enonce, applicable=applicable, dispensee=q.id in dispenses,
                reponses=reps, collecte=etat.collecte.get((f.id, q.id)),
                mandat_ouvert_id=etat.mandats_ouverts.get((f.id, q.id)))
        lignes.append(LigneQuestion(
            question_id=q.id, enonce=q.enonce, applicable=applicable,
            dispensee=q.id in dispenses, manque=manque,
            reponses=[ReponseResumee(
                answer_id=r.answer_id, analyste=r.servie.analyste, statut=r.servie.statut,
                rang_derive=r.servie.fondation.rang_derive if r.servie.fondation else None,
                actualite=r.servie.fondation.actualite if r.servie.fondation else None,
                verdict=r.verdict, controles=r.controles) for r in reps],
        ))
    return lignes


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
    )


def dresser_niveau1(etat: EtatDossier, memo) -> DossierTitre:
    """NIVEAU 1 : l'alerte en tête, puis la note de chaque méthodologie, puis la note de comité."""
    syntheses, manques = [], []
    for f in etat.fichier.frameworks:
        lignes = _lignes(etat, f)
        syntheses.append(_synthese(etat, f, lignes))
        manques.extend(lq.manque for lq in lignes if lq.manque is not None)

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
    else:
        pod = PeutOnDecider(etat="dossier_complet",
                            motif="toutes les questions applicables ont une réponse acquittée et "
                                  "à jour")
    return DossierTitre(ticker_id=etat.ticker_id, archetype=etat.archetype,
                        genere_le=etat.genere_le, peut_on_decider=pod,
                        frameworks=syntheses, memo=memo)


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
            pieces.append(PieceCitee(entry_id=i, role=role, present_au_corpus=False))
            continue
        pieces.append(PieceCitee(
            entry_id=i, role=role, present_au_corpus=True, titre=p["title"],
            source_type=p["source_type"], source_url=p["source_url"],
            source_date=p["source_date"], date_du_fait=p["date_du_fait"],
            reliability_tier=p["reliability_tier"], nature=p["nature"],
            remplacee=p["superseded_by"] is not None))
    return pieces


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
        applicable=ligne.applicable, preuves=preuves, manque=ligne.manque)


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


async def charger_etat_dossier(conn, ticker_id: str) -> EtatDossier:
    """Base → revue RECALCULÉE → réponses servies. N'écrit rien — ni verdict, ni mandat, ni note.

    ⚠️ L'AVIS DU MANAGER SE RECALCULE ICI (#77) : les 4 contrôles dépendent du corpus, des dispenses
    et de l'actualité, qui bougent. Un renvoi recalculé se complète par l'id du mandat OUVERT sur la
    question (`id_du_mandat_ouvert`, détenteur unique) ; s'il n'y en a pas, on n'en invente pas :
    `renvoi_a_emettre`.
    """
    # Imports tardifs : ce module est importé par des checks sans base ni réseau.
    from app.agents.v2.frameworks import servir_answer
    from app.agents.v2.framework_persist import (
        read_answers_courantes, read_archetype, read_dispenses)
    from app.agents.v2.manager import reviser_framework
    from app.agents.v2.manager_persist import assemble_verdict
    from app.agents.v2.traducteur import questions_applicables
    from app.knowledge.material_events import ancre_substantielle, material_anchor_for_ticker

    fichier = load_frameworks()
    version = fichier.schema_version
    brutes = await read_answers_courantes(conn, ticker_id=ticker_id, framework_version=version)

    cites: set[int] = set()
    for _id, a in brutes:
        if a.fondation is not None:
            cites.update(a.fondation.cited_entry_ids)
        if a.approximation is not None:
            cites.update(a.approximation.ingredients_entry_ids)

    pieces: dict[int, dict[str, Any]] = {}
    if cites:
        rows = await conn.fetch(
            "SELECT id, title, source_type, source_url, source_date, date_du_fait, "
            "reliability_tier, nature, superseded_by FROM knowledge_entries "
            "WHERE id = ANY($1::int[])", sorted(cites))
        pieces = {r["id"]: dict(r) for r in rows}
    # Le corpus des RÈGLES : exactement les deux colonnes que lisent l'actualité et le contrôle ③.
    entries = {i: {"source_date": p["source_date"], "reliability_tier": p["reliability_tier"]}
               for i, p in pieces.items()}

    classement = await read_archetype(conn, ticker_id=ticker_id)
    archetype = classement[0] if classement is not None else None

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

    # L'ancre qui PÈSE, jamais la dernière venue (#54, arbitrage du comité n°2 du 2026-09-25) : une
    # information de routine — un 8-K de pure forme — ne remet pas une réponse en cause. Les deux
    # assembleurs d'avant lisaient l'ancre brute, là où la porte de complétude lisait déjà celle-ci :
    # un 8-K formel aurait périmé la note projetée sans périmer la readiness.
    ancre = ancre_substantielle(await material_anchor_for_ticker(conn, ticker_id))
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
        reponses.append(ReponseLue(
            answer_id=i, servie=servir_answer(a, ancre=ancre, entries=entries),
            verdict=verdict, controles=controles, motif_revue=motif, etat_revue=etat_revue))

    return EtatDossier(
        ticker_id=ticker_id, fichier=fichier, archetype=archetype, reponses=reponses,
        pieces=pieces, applicables=applicables, dispenses=dispenses,
        mandats_ouverts=mandats_ouverts, collecte=await _collectes(conn, ticker_id, version))
