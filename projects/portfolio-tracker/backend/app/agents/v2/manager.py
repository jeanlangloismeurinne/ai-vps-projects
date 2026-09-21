"""Le MANAGER d'un framework et ses quatre contrôles (spec v3 §3) — chantier v3, lot 4.

CE QUE FAIT LE MANAGER, ET CE QU'IL NE FAIT PAS
-----------------------------------------------
Le manager est le garant de la QUALITÉ DE LA SORTIE d'un framework (§3.1). Il n'a **aucune opinion
sur l'entreprise** : son autorité dérive du framework et s'exerce par quatre contrôles **mécaniques**,
chacun rendant `ok`/`ko` motivé (§3.2). Il **acquitte** ou il **renvoie** — il ne réécrit jamais une
réponse et ne promeut jamais un rang (§3.3). Un renvoi PRODUIT un mandat de recherche exécutable
consommé par le collecteur (§3.6) : c'est la fermeture de l'Écart B (§0.5).

POURQUOI IL EST DÉTERMINISTE, ET POURQUOI SES CONTRÔLES NE DOUBLENT PAS LE PONT ANALYSTE
---------------------------------------------------------------------------------------
Aucun des quatre contrôles ne demande un jugement d'investissement, donc **aucun appel modèle** :
le manager est une fonction pure, rejouable et gratuite (`feedback_frontiere_gratuite_avant_
depense_modele`). Il RE-VÉRIFIE, au moment de la revue, ce que le pont analyste
(`valider_pont_framework_answer`) a vérifié à la PRODUCTION — mais contre le corpus tel qu'il est
MAINTENANT. C'est là qu'un `ko` naît là où le pont était vert : une entry citée a pu être supersédée
depuis l'analyse (② tombe), une réponse a pu être persistée par un chemin qui n'a pas franchi le pont
(③/④ tombent), ou une question **inapplicable** pour l'archétype a reçu une vraie réponse (① tombe —
c'est le défaut T4/entry #190 : un ROIC fabriqué pour une société sans revenus). Le contrat
(`ControlesManager`, `ManagerVerdict`, `FrameworkMandate`) valide un OBJET ; il ne peut pas juger la
cohérence entre une réponse, le corpus et le référentiel (#37) — c'est exactement ce que fait ici le
manager, et c'est pourquoi chaque `ko` est atteignable par une mutation (aucun n'est garanti
impossible par la construction Pydantic).

CE QUI RESTE HORS DE CE MAILLON (couche données, maillon suivant)
-----------------------------------------------------------------
Le manager rend une DÉCISION (les 4 contrôles + acquitte/renvoie + la spécification du mandat), pas
un `ManagerVerdict` complet : ce dernier porte `mandat_de_recherche_id`, un entier assigné par la
BASE au moment de persister le mandat. La persistance (migration 043 : `framework_mandates` par
question — la table 039 est au grain ingrédient —, et le verdict rangé sur la réponse) et
l'acceptation de bout en bout T8 (un renvoi crée un mandat consommable, le re-run change le statut)
sont le maillon suivant. Ici : la logique pure, gardée hors ligne.

Détenteurs uniques réutilisés, jamais recopiés (#46) :
  · ② fondation           → `synthesis_feed.validate_grounding` (le grounding est vérifié, pas
                            déclaré, #24/#28) ;
  · ③ honnêteté (le cran) → `synthesis_feed.derive_synthesis_reliability` + `frameworks._plus_faible`
                            (la règle du cran a un seul détenteur — la recopier la ferait diverger) ;
  · ④ non-substitution    → `frameworks.motif_substitut_hors_sujet` (extrait du pont, partagé) ;
  · applicabilité         → `traducteur.questions_applicables` (le filtrage par archétype §4.1.3).

Cible : pydantic v2 (container backend). Tester en container, PAS le python hôte (v1).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from app.agents.v2.frameworks import (
    _plus_faible,
    _TIER_RANK,
    motif_substitut_hors_sujet,
)
from app.agents.v2.traducteur import questions_applicables
from app.contracts.framework_answer_schema import (
    ControlesManager,
    FrameworkAnswer,
    FrameworkMandate,
)
from app.contracts.framework_definition_schema import FrameworksFile
from app.knowledge.synthesis_feed import derive_synthesis_reliability, validate_grounding

__all__ = [
    "Decision",
    "ManagerReview",
    "controles_de_la_reponse",
    "reviser_framework",
]

_PIRE = len(_TIER_RANK)  # un tier inconnu compte pour le pire, jamais pour le meilleur (#46, cran)


@dataclass(frozen=True)
class Decision:
    """La décision du manager pour UNE réponse : les quatre contrôles + le verdict + la spécification
    du mandat à créer si c'est un renvoi. Le `ManagerVerdict` complet (avec `mandat_de_recherche_id`)
    s'assemble à la persistance, quand le mandat reçoit son id (couche données, maillon suivant)."""
    controles: ControlesManager
    verdict: Literal["acquitte", "renvoye"]
    motif: str
    mandat: Optional[FrameworkMandate]  # etat='ouvert', sans id — None sur un acquittement


@dataclass(frozen=True)
class ManagerReview:
    """La revue d'un framework pour un émetteur : une décision par réponse + les mandats des
    questions applicables restées SANS réponse (contrôle ①, au niveau du framework)."""
    decisions: dict[tuple[str, str], Decision]  # (question_id, analyste) -> Decision
    questions_manquantes: list[str]
    mandats_manquantes: list[FrameworkMandate]

    def mandats(self) -> list[FrameworkMandate]:
        """Tous les mandats produits par la revue — renvois de réponses ET questions manquantes.
        C'est ce que la couche données persiste dans `framework_mandates`."""
        renvois = [d.mandat for d in self.decisions.values() if d.mandat is not None]
        return renvois + self.mandats_manquantes


# ── Les quatre contrôles, chacun `(etat, motif)` — un motif seulement quand `ko` ────────────────

def _completude(answer: FrameworkAnswer, *, applicable: bool) -> tuple[str, str]:
    """① Une question INAPPLICABLE pour l'archétype (mode `sans_objet`, §4.1.3) qui reçoit autre
    chose qu'un `sans_objet` est une réponse FABRIQUÉE à une question qui n'a pas d'objet — le défaut
    T4, exactement celui de l'entry #190 (un ROIC pour une société sans revenus). Une question
    applicable : tout statut EST un statut (le contrat garantit déjà qu'un `sans_objet` porte son
    motif, §2.4). L'absence TOTALE de réponse à une question applicable est traitée au niveau du
    framework (`reviser_framework`), pas ici : il n'y a pas d'objet `answer` à contrôler."""
    if not applicable and answer.statut != "sans_objet":
        return "ko", (f"`{answer.question_id}` est sans objet pour l'archétype, mais la réponse la "
                      f"traite en `{answer.statut}` : une réponse fabriquée à une question qui n'a "
                      "pas de sens (défaut T4, entry #190)")
    return "ok", ""


def _fondation(answer: FrameworkAnswer, *, entries: dict[int, dict[str, Any]]) -> tuple[str, str]:
    """② Le grounding, re-vérifié contre le corpus FOURNI AU MANAGER — qui peut avoir maigri depuis
    l'analyse (une entry supersédée). Détenteur unique `validate_grounding` : la même fonction que
    la synthèse, délibérément (#46/#28). Une citation hors corpus = une source apportée de mémoire."""
    citable = set(entries)
    claims: list[dict[str, Any]] = []
    approx: list[dict[str, Any]] = []
    if answer.fondation is not None:
        claims.append({"cited_entry_ids": list(answer.fondation.cited_entry_ids)})
    if answer.approximation is not None:
        approx.append({"question": answer.question_id,
                       "cited_entry_ids": list(answer.approximation.ingredients_entry_ids)})
    violations = validate_grounding(claims, citable, approx or None)
    if violations:
        return "ko", " ; ".join(violations)
    return "ok", ""


def _honnetete(answer: FrameworkAnswer, *, entries: dict[int, dict[str, Any]]) -> tuple[str, str]:
    """③ `sans_objet` si la réponse n'approxime pas (équivalence du contrat — un `ok` sur zéro ligne
    serait le 1er faux vert). Sinon, le rang est-il EFFECTIVEMENT dégradé ? La complétude du bloc
    (méthode, ingrédients, hypothèses, sensibilité) est déjà garantie par le contrat ; ce qui ne
    l'est PAS, et que le manager re-vérifie, c'est que `rang_derive` vaut bien UN CRAN SOUS la plus
    faible pièce citée (règle transverse 7). Un rang non dégradé est une estimation qui se fait
    passer pour aussi solide que sa source."""
    if answer.statut != "approxime":
        return "sans_objet", ""
    # Le rang se dérive des tiers RÉELS des entries citées par la fondation — la même base que le
    # pont (control C) : le manager n'invente pas une seconde base de dérivation (#46).
    tiers = [str(entries[i].get("reliability_tier"))
             for i in answer.fondation.cited_entry_ids if i in entries]
    if not tiers:
        return "ko", ("approximation dont aucun ingrédient cité n'a de tier lisible dans le corpus "
                      "fourni : un cran ne se dérive pas d'un ensemble vide")
    _, degrade, _ = derive_synthesis_reliability(tiers)
    faible = _plus_faible(tiers)
    if answer.fondation.rang_derive != degrade:
        return "ko", (f"`rang_derive` = {answer.fondation.rang_derive} alors que les tiers cités "
                      f"{tiers} commandent {degrade} (un cran sous {faible}) : un rang auto-déclaré "
                      "est un rang faux (règle transverse 7)")
    if _TIER_RANK.get(degrade, _PIRE) <= _TIER_RANK.get(faible, _PIRE):
        return "ko", (f"le rang {degrade} n'est pas dégradé sous la plus faible citée {faible} : une "
                      "approximation qui garde le rang de ses ingrédients se présente comme une "
                      "mesure (§1.5, contrôle ③)")
    return "ok", ""


def _non_substitution(
    answer: FrameworkAnswer,
    *,
    autres_reponses: Optional[dict[int, FrameworkAnswer]],
) -> tuple[str, str]:
    """④ Un substitut de `sans_objet` pointe la réponse d'une AUTRE question, jamais la sienne (sinon
    il republie ce qu'il vient de déclarer sans objet). Détenteur unique partagé avec le pont
    (`motif_substitut_hors_sujet`). La moitié intra-objet du contrôle ④ — une approximation présentée
    comme une `mesure`, un statut portant les blocs d'un autre — est rendue IMPOSSIBLE par le contrat
    (`FrameworkAnswer._le_statut_porte_exactement_ses_blocs`), donc il n'y a rien à re-tester ici :
    l'ajouter serait un contrôle qu'aucune mutation ne peut atteindre (une garde satisfaite par
    construction)."""
    motif = motif_substitut_hors_sujet(answer, autres_reponses)
    if motif is not None:
        return "ko", motif
    return "ok", ""


def controles_de_la_reponse(
    answer: FrameworkAnswer,
    *,
    applicable: bool,
    entries: dict[int, dict[str, Any]],
    autres_reponses: Optional[dict[int, FrameworkAnswer]] = None,
) -> tuple[ControlesManager, str]:
    """Les quatre contrôles d'UNE réponse → `(ControlesManager, motif_agrégé)`. Pur.

    `motif_agrégé` concatène les motifs des contrôles `ko` : c'est ce qui nourrit le `motif` du
    verdict et du mandat, pour qu'un renvoi nomme SA cause et non « le manager a renvoyé »."""
    c_comp, m_comp = _completude(answer, applicable=applicable)
    c_fond, m_fond = _fondation(answer, entries=entries)
    c_honn, m_honn = _honnetete(answer, entries=entries)
    c_nsub, m_nsub = _non_substitution(answer, autres_reponses=autres_reponses)

    controles = ControlesManager(
        completude=c_comp,               # type: ignore[arg-type]
        fondation=c_fond,                # type: ignore[arg-type]
        honnetete_approximation=c_honn,  # type: ignore[arg-type]
        non_substitution=c_nsub,         # type: ignore[arg-type]
    )
    motifs = [m for m in (m_comp, m_fond, m_honn, m_nsub) if m]
    return controles, " | ".join(motifs)


# ── L'orchestration au niveau du framework ─────────────────────────────────────────────────────

def _mandat_pour(
    *,
    framework_id: str,
    framework_version: str,
    question_id: str,
    ticker_id: str,
    motif: str,
    mandat: str,
) -> FrameworkMandate:
    return FrameworkMandate(
        framework_id=framework_id,
        question_id=question_id,
        ticker_id=ticker_id,
        origine="manager_renvoi",
        motif=motif,
        mandat=mandat,
        etat="ouvert",
    )


def reviser_framework(
    answers: list[FrameworkAnswer],
    *,
    fichier: FrameworksFile,
    framework_id: str,
    archetype: str,
    ticker_id: str,
    entries: dict[int, dict[str, Any]],
    dispenses: frozenset[str] = frozenset(),
    autres_reponses: Optional[dict[int, FrameworkAnswer]] = None,
) -> ManagerReview:
    """Révise TOUTES les réponses d'un framework pour un émetteur (spec §3.4 : N analystes possibles).

    Deux réponses divergentes à une même question ne se moyennent JAMAIS (§3.4) : chacune reçoit sa
    propre décision, clefée `(question_id, analyste)`. Le contrôle ① au niveau du framework produit
    en plus un mandat par question APPLICABLE restée sans réponse (ni dispensée) — c'est « toutes
    les questions ont-elles un statut ? » (§3.2), et son remède est une collecte, pas un affichage.
    """
    applicables = questions_applicables(fichier, framework_id, archetype)
    applicables_by_id = {q.id: q for q in applicables}
    version = fichier.schema_version

    decisions: dict[tuple[str, str], Decision] = {}
    for a in answers:
        applicable = a.question_id in applicables_by_id
        controles, motif = controles_de_la_reponse(
            a, applicable=applicable, entries=entries, autres_reponses=autres_reponses,
        )
        kos = controles.kos()
        if kos:
            qdef = applicables_by_id.get(a.question_id)
            quoi = qdef.variables_par_archetype[archetype].variable if qdef else a.question_id
            mandat = _mandat_pour(
                framework_id=a.framework_id, framework_version=a.framework_version,
                question_id=a.question_id, ticker_id=a.ticker_id,
                motif=f"renvoi manager : {', '.join(kos)} ko — {motif}",
                mandat=f"{a.question_id} : re-collecter de quoi lever {', '.join(kos)}. "
                       f"À chercher : {quoi or a.question_id}",
            )
            decisions[(a.question_id, a.analyste)] = Decision(
                controles=controles, verdict="renvoye",
                motif=f"{', '.join(kos)} ko — {motif}", mandat=mandat)
        else:
            decisions[(a.question_id, a.analyste)] = Decision(
                controles=controles, verdict="acquitte", motif="4 contrôles au vert", mandat=None)

    answered = {a.question_id for a in answers}
    manquantes = [q.id for q in applicables if q.id not in answered and q.id not in dispenses]
    mandats_manquantes = [
        _mandat_pour(
            framework_id=framework_id, framework_version=version,
            question_id=qid, ticker_id=ticker_id,
            motif=(f"question applicable `{qid}` sans aucune réponse : un blanc n'est pas un "
                   "`sans_objet` (contrôle ①, §3.2)"),
            mandat=(f"{qid} : {applicables_by_id[qid].variables_par_archetype[archetype].variable} "
                    "— aucune réponse produite, collecter de quoi la fonder"),
        )
        for qid in manquantes
    ]
    return ManagerReview(
        decisions=decisions,
        questions_manquantes=manquantes,
        mandats_manquantes=mandats_manquantes,
    )
