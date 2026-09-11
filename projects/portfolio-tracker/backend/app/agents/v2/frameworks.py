"""Le PONT relationnel du contrat de framework (chantier v3, lot 1) — et rien d'autre.

Un contrat valide un **objet**, jamais la cohérence entre deux (convention #37). Tout ce qui exige
de connaître le corpus, la question ou les autres réponses vit ici, en Python, et lève
`FrameworkAnswerRefused` — comme `monitoring._valider_pont_hypotheses` le fait déjà pour les
hypothèses figées. Le partage exact est écrit dans l'en-tête de `contracts/framework_answer_schema`.

CE QUE LE PONT VÉRIFIE, ET POURQUOI CHACUN EXISTE
--------------------------------------------------
  A. la question existe dans le framework — sinon la réponse s'indexe sur une question voisine, et
     T4/T5 passeraient sur une question qui n'est pas celle qu'on croit ;
  B. les entries citées ont été RÉELLEMENT fournies (A2) — un id hors corpus, c'est le modèle qui
     apporte une source que personne n'a lue. Même mode de panne que `validate_grounding`, et c'est
     LUI qui le prononce, pas une seconde implémentation (#46) ;
  C. le rang est celui que les tiers RÉELS commandent — un `rang_derive` est dérivé, jamais déclaré
     (règle transverse 7, §3.5). Un rang auto-déclaré est un rang faux ;
  D. le rang atteint le plancher de la question — une réponse fondée sur du C ne vaut pas une
     réponse, quel que soit son aplomb ;
  E. la nature attendue est portée par une entry citée — l'axe `nature` est une propriété de
     l'assertion (#51), il ne se déduit pas du statut ;
  F. un substitut pointe la réponse d'une AUTRE question — un `sans_objet` qui se cite lui-même
     comme substitut est le contrôle ④ retourné contre lui-même.

`servir_answer()` est le POINT DE LECTURE : il ajoute l'axe actualité, recalculé, sans rien écrire.
Un GET qui servirait la ligne stockée telle quelle servirait le verdict d'avant l'événement
matériel — le faux vert que la capacité 4 a mis une journée à voir (#54).

`load_frameworks()` (lot 2) charge les 13 questions depuis `app/frameworks/frameworks.yaml`. Elles
sont des DONNÉES INERTES, jamais du code : voir l'en-tête du YAML pour la raison — écrites en
Python, elles pourraient se dériver de `MVDD_SPEC` ou des postes EDGAR, et le test de couverture
mesurerait alors sa propre constante.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import ValidationError

from app.agents.v2.common import NATURES, TIER_ORDER, _TIER_RANK
from app.contracts.collection_plan_schema import CollectionPlan
from app.contracts.framework_answer_schema import (
    FrameworkAnswer,
    FrameworkAnswerServie,
)
from app.contracts.framework_definition_schema import (
    FRAMEWORK_DEFINITION_SCHEMA_VERSION,
    FrameworksFile,
)
from app.knowledge.actualite import MaterialEventLookup, etat_actualite_entry
from app.knowledge.synthesis_feed import derive_synthesis_reliability

FRAMEWORKS_YAML = Path(__file__).resolve().parents[2] / "frameworks" / "frameworks.yaml"

# Les clefs que le pont LIT dans un profil de question. Détenteur unique : `valider_pont_…` les
# consomme par `profil.get(...)`, et un `.get` sur une clef mal orthographiée rend `None`, ce qui
# SAUTE le contrôle au lieu de le faire échouer. Un contrôle qui ne s'exécute pas est un vert
# (`feedback_check_degrade_en_sortant_a_zero`). `check_frameworks_definitions.py` vérifie que les
# profils produits portent exactement ces clefs.
CLEFS_PROFIL_LUES = ("plancher_tier", "nature_attendue")


class FrameworkAnswerRefused(Exception):
    """Refus du pont — une réponse formellement valide, mais incohérente avec le corpus.

    Levée, jamais rendue en valeur : un refus qui se lit comme un résultat finit par être ignoré.
    """


class FrameworkDefinitionRefused(Exception):
    """Refus au CHARGEMENT — le fichier de définitions est formellement valide mais incohérent.

    Distincte de `FrameworkAnswerRefused` : celle-ci dit que le référentiel est cassé, pas qu'une
    réponse l'est. Elle doit faire échouer le démarrage, jamais dégrader silencieusement vers un
    référentiel partiel — un framework à demi chargé rendrait `sans_objet` des questions qui
    existent (#54, la complétude à trois états).
    """


class CollectionPlanRefused(Exception):
    """Refus d'un PLAN DE COLLECTE — formellement valide (le contrat l'accepte), mais incohérent
    avec le référentiel. Sortie du traducteur (§3.6), vérifiée AVANT que le collecteur ne dépense.

    Levée, jamais rendue en valeur : un refus qui se lit comme un résultat finit par être ignoré.
    Distincte des deux autres — elle ne dit ni que le référentiel est cassé
    (`FrameworkDefinitionRefused`), ni qu'une réponse l'est (`FrameworkAnswerRefused`), mais que le
    PLAN l'est.
    """


def _valider_pont_definitions(fichier: FrameworksFile) -> None:
    """Les invariants RELATIONNELS des définitions — ceux qu'un contrat d'objet ne peut pas voir.

    Chacun garde un mode de panne qui se lit comme un succès :

      G. deux questions de frameworks DIFFÉRENTS partageant un id. §6 fait des `framework_questions`
         LE vocabulaire unique — deux `qf_1` et l'index désigne l'un pour l'autre ;
      H. deux chemins d'indexation identiques entre frameworks. Même panne, côté lien de couverture ;
      I. une question qui ne couvre pas exactement les archétypes déclarés. En trop : un archétype
         inventé n'est jamais interrogé. En moins : la question est MUETTE sur cet archétype, et
         l'agent tranchera seul — l'expérience du chantier dit qu'il fabrique une réponse plutôt
         que de se taire (entry #190, §0.2) ;
      J. un substitut qui ne résout pas, ou qui pointe sa propre question. Un hors-sujet qui se
         cite lui-même republie la question qu'il vient de déclarer sans objet ;
      K/L. `nature_attendue` et `plancher_tier` hors des vocabulaires DÉTENUS ailleurs
         (`common.NATURES`, `common.TIER_ORDER`). Le contrat les répète en `Literal` pour
         l'ergonomie ; c'est ici qu'on vérifie qu'ils n'ont pas divergé de leur détenteur (#46) ;
      M. une version de schéma qui ne correspond pas au contrat qui vient de valider le fichier.
    """
    if fichier.schema_version != FRAMEWORK_DEFINITION_SCHEMA_VERSION:
        raise FrameworkDefinitionRefused(
            f"[M] fichier en {fichier.schema_version}, contrat en "
            f"{FRAMEWORK_DEFINITION_SCHEMA_VERSION}"
        )

    toutes = [(f, q) for f in fichier.frameworks for q in f.questions]

    vus: dict[str, str] = {}
    for f, q in toutes:
        if q.id in vus:
            raise FrameworkDefinitionRefused(
                f"[G] la question `{q.id}` est déclarée par `{vus[q.id]}` ET par `{f.id}` — "
                f"les question_id sont LE vocabulaire unique (§6), ils ne peuvent pas collisionner"
            )
        vus[q.id] = f.id

    chemins: dict[str, str] = {}
    for _f, q in toutes:
        if q.chemin_indexation in chemins:
            raise FrameworkDefinitionRefused(
                f"[H] le chemin `{q.chemin_indexation}` est partagé par `{chemins[q.chemin_indexation]}` "
                f"et `{q.id}` — l'index ne saurait plus laquelle des deux il fonde"
            )
        chemins[q.chemin_indexation] = q.id

    attendus = set(fichier.archetypes)
    for _f, q in toutes:
        couverts = set(q.variables_par_archetype)
        if couverts != attendus:
            raise FrameworkDefinitionRefused(
                f"[I] `{q.id}` couvre {sorted(couverts)} au lieu de {sorted(attendus)} — "
                f"manquants : {sorted(attendus - couverts)}, inventés : {sorted(couverts - attendus)}"
            )

    for _f, q in toutes:
        for archetype, va in q.variables_par_archetype.items():
            cible = va.substitut_question_id
            if cible is None:
                continue
            if cible == q.id:
                raise FrameworkDefinitionRefused(
                    f"[J] `{q.id}` ({archetype}) se cite elle-même comme substitut"
                )
            if cible not in vus:
                raise FrameworkDefinitionRefused(
                    f"[J] `{q.id}` ({archetype}) renvoie au substitut `{cible}`, qui n'existe pas"
                )

    for _f, q in toutes:
        if q.nature_attendue not in NATURES:
            raise FrameworkDefinitionRefused(
                f"[K] `{q.id}` : nature `{q.nature_attendue}` hors du vocabulaire détenu par "
                f"`common.NATURES` ({sorted(NATURES)})"
            )
        if q.plancher_tier not in TIER_ORDER:
            raise FrameworkDefinitionRefused(
                f"[L] `{q.id}` : plancher `{q.plancher_tier}` hors de `common.TIER_ORDER`"
            )


@lru_cache(maxsize=1)
def load_frameworks(chemin: Optional[str] = None) -> FrameworksFile:
    """Charge et VALIDE le référentiel. Lève plutôt que de rendre un référentiel partiel.

    Le YAML est lu en `safe_load` : un fichier de données ne doit pas pouvoir instancier d'objet
    Python. C'est la contrepartie du choix « données inertes » — l'inertie doit tenir au chargement,
    pas seulement à l'écriture.
    """
    p = Path(chemin) if chemin else FRAMEWORKS_YAML
    if not p.exists():
        raise FrameworkDefinitionRefused(f"référentiel introuvable : {p}")
    brut = yaml.safe_load(p.read_text(encoding="utf-8"))
    try:
        fichier = FrameworksFile.model_validate(brut)
    except ValidationError as exc:
        raise FrameworkDefinitionRefused(f"référentiel invalide ({p}) : {exc}") from exc
    _valider_pont_definitions(fichier)
    return fichier


def question_profiles(fichier: Optional[FrameworksFile] = None) -> dict[str, dict[str, Any]]:
    """Les profils à plat, dans la forme que `valider_pont_framework_answer` consomme.

    ⚠️ Les clefs sont produites depuis `CLEFS_PROFIL_LUES` et depuis les attributs du contrat, pas
    réécrites à la main : une clef mal orthographiée ici ferait sauter le contrôle D ou E côté pont
    sans qu'aucun test ne rougisse.
    """
    fichier = fichier or load_frameworks()
    profils: dict[str, dict[str, Any]] = {}
    for f in fichier.frameworks:
        for q in f.questions:
            profil = {clef: getattr(q, clef) for clef in CLEFS_PROFIL_LUES}
            profil.update({
                "framework_id": f.id,
                "chemin_indexation": q.chemin_indexation,
                "actualite_bloquante": q.actualite_bloquante,
                "sens_admis": list(q.sens_admis),
                "ingredients_essentiels": [i.id for i in q.ingredients_requis if i.essentiel],
            })
            profils[q.id] = profil
    return profils


def _plus_faible(tiers: list[str]) -> str:
    """Le tier le plus faible d'une liste — rang le plus GRAND dans `TIER_ORDER` (A=0 … C=6).

    Même convention d'ordre que `derive_synthesis_reliability` (elle-même détenteur de la règle du
    cran) : un tier inconnu compte pour le pire, jamais pour le meilleur.
    """
    return max(tiers, key=lambda t: _TIER_RANK.get(t, len(TIER_ORDER)))


def valider_pont_framework_answer(
    answer: FrameworkAnswer,
    *,
    questions: dict[str, dict[str, Any]],
    entries: dict[int, dict[str, Any]],
    autres_reponses: Optional[dict[int, FrameworkAnswer]] = None,
) -> None:
    """Vérifie A→F. Ne rend rien : le seul résultat possible est « pas de refus ».

    `questions` : `{question_id: {plancher_tier, nature_attendue, ...}}` — les DONNÉES du lot 2.
    `entries`   : le corpus RÉELLEMENT fourni, `{id: {reliability_tier, entry_type, ...}}`.
    """
    # A. la question existe. Vérifié AVANT tout le reste : les contrôles D et E lisent son profil,
    #    et un profil absent les rendrait muets — un contrôle qui ne s'exécute pas est un vert.
    if answer.question_id not in questions:
        raise FrameworkAnswerRefused(
            f"question `{answer.question_id}` inconnue du framework `{answer.framework_id}` "
            f"({len(questions)} questions chargées) : une réponse qui ne s'indexe sur aucune "
            "question s'indexerait sur une question voisine")
    profil = questions[answer.question_id]

    if answer.fondation is not None:
        cites = list(answer.fondation.cited_entry_ids)

        # B. citations RÉELLEMENT fournies (A2).
        hors_corpus = [i for i in cites if i not in entries]
        if hors_corpus:
            raise FrameworkAnswerRefused(
                f"entries citées hors du corpus fourni : {hors_corpus}. Une source que personne n'a "
                "chargée n'est pas une source — c'est le modèle qui l'apporte de mémoire")

        tiers_reels = [str(entries[i].get("reliability_tier")) for i in cites]

        # C. LE RANG EST DÉRIVÉ. Deux règles distinctes, jamais confondues :
        #    • `repondu`   → le rang de la plus faible entry citée ;
        #    • `approxime` → UN CRAN SOUS, via le détenteur unique de la règle du cran. Le recopier
        #      ici le ferait diverger au prochain ajustement de seuil (#46).
        if answer.statut == "approxime":
            _, attendu, _ = derive_synthesis_reliability(tiers_reels)
            regle = "un cran sous la plus faible citée (estimation)"
        else:
            attendu = _plus_faible(tiers_reels)
            regle = "le rang de la plus faible citée"
        if answer.fondation.rang_derive != attendu:
            raise FrameworkAnswerRefused(
                f"`rang_derive` = {answer.fondation.rang_derive} alors que les tiers réels "
                f"{tiers_reels} commandent {attendu} ({regle}). Un rang auto-déclaré est un rang "
                "faux : il se dérive, il ne s'annonce pas (règle transverse 7)")

        # D. le rang atteint le PLANCHER de la question.
        plancher = profil.get("plancher_tier")
        if plancher is not None and _TIER_RANK.get(attendu, len(TIER_ORDER)) > _TIER_RANK.get(
                plancher, len(TIER_ORDER)):
            raise FrameworkAnswerRefused(
                f"rang {attendu} sous le plancher {plancher} de `{answer.question_id}` : une "
                "réponse qui n'atteint pas son plancher est un `non_fondable`, pas une réponse "
                "faible — la nuance est ce qui déclenche une collecte au lieu d'un affichage")

        # E. la nature attendue est PORTÉE par une entry citée, pas déduite du statut (#51).
        attendue = profil.get("nature_attendue")
        if attendue is not None:
            portees = {entries[i].get("nature") for i in cites}
            if attendue not in portees and answer.statut != "approxime":
                raise FrameworkAnswerRefused(
                    f"`{answer.question_id}` attend une assertion de nature `{attendue}`, mais les "
                    f"entries citées portent {sorted(str(p) for p in portees)}. La nature est une "
                    "propriété de l'assertion : elle se lit sur la source, elle ne se déduit pas "
                    "du statut de la réponse")

    # F. un substitut pointe la réponse d'une AUTRE question.
    if answer.sans_objet is not None and answer.sans_objet.substitut_answer_id is not None:
        cible = (autres_reponses or {}).get(answer.sans_objet.substitut_answer_id)
        if cible is None:
            raise FrameworkAnswerRefused(
                f"`substitut_answer_id` = {answer.sans_objet.substitut_answer_id} ne désigne "
                "aucune réponse fournie : un substitut qu'on ne peut pas ouvrir n'est pas un "
                "substitut, c'est une promesse")
        if cible.question_id == answer.question_id:
            raise FrameworkAnswerRefused(
                f"le substitut de `{answer.question_id}` est une réponse à `{answer.question_id}` "
                "elle-même : un hors-sujet qui se cite en substitut republie la question qu'il "
                "vient de déclarer sans objet (contrôle ④, §3.2)")


def servir_answer(
    answer: FrameworkAnswer,
    *,
    ancre: MaterialEventLookup,
    entries: dict[int, dict[str, Any]],
) -> FrameworkAnswerServie:
    """LE POINT DE LECTURE : la réponse persistée + l'axe actualité RECALCULÉ. N'écrit rien.

    L'actualité d'une réponse est celle de sa fondation, et la fondation se date par **la plus
    ancienne** de ses entries citées — jamais la plus récente, qui blanchirait la péremption en
    citant un communiqué frais à côté d'un chiffre de 2019. Cette règle a déjà un détenteur
    (`actualite.date_effective`) : plutôt que de la ré-implémenter, on présente la réponse dans la
    forme que ce détenteur sait lire (#46).
    """
    if answer.fondation is None:
        return FrameworkAnswerServie(**answer.model_dump())

    pseudo_entry = {
        "source_date": None,  # aucune date propre : la fondation se date par ses citations
        "content_structured": {"source_entry_refs": list(answer.fondation.cited_entry_ids)},
    }
    act = etat_actualite_entry(pseudo_entry, ancre=ancre, corpus=entries)

    donnees = answer.model_dump()
    donnees["fondation"] = {**donnees["fondation"], "actualite": act.etat,
                            "motif_actualite": act.motif}
    return FrameworkAnswerServie(**donnees)


def valider_pont_collection_plan(
    plan: CollectionPlan,
    *,
    fichier: Optional[FrameworksFile] = None,
) -> None:
    """Vérifie qu'un plan de collecte est cohérent avec le RÉFÉRENTIEL. Ne rend rien : le seul
    résultat possible est « pas de refus ».

    Ce que le contrat d'objet (`collection_plan_schema`) ne peut pas voir, parce qu'il exige de
    connaître les questions et leurs ingrédients (#37). Chaque invariant garde un mode de panne qui
    se lit comme un succès :

      N. le framework existe, ET à la version du plan. Un plan daté d'une autre version décrit un
         framework qui a pu changer de questions — le mode de panne de la couverture rétroactive
         (#57) ;
      O. l'archétype est l'un des archétypes DÉCLARÉS (§4.1.3). Un archétype inventé n'est jamais
         interrogé, et le plan paraîtrait complet en ayant sauté la moitié des questions ;
      P. chaque ligne RÉSOUT — la question appartient au framework, l'ingrédient à la question. Un
         ingrédient inventé écrirait le corrigé (le §0.2, entry #190, est né d'exactement ça) ;
      Q. une ligne ne planifie pas une question SANS OBJET pour cet archétype. Collecter pour une
         question que le framework déclare hors-sujet, c'est fabriquer une réponse là où il n'y a
         pas de question — l'inverse du signal que `sans_objet` porte ;
      R. LE CŒUR — T1bis (§9.2). Chaque ingrédient ESSENTIEL d'une question APPLICABLE a une ligne
         (`traduit` ou `inobtenable motivé`). Une omission n'est pas un trou : c'est un plan
         REFUSÉ. Un essentiel qui disparaît en silence produit un VERT (couverture à 100 % sur ce
         qui reste) — le mode de panne que toute la v3 combat.

    Ce que ce pont NE fait PAS : émettre le mandat d'une ligne `inobtenable` (c'est le flux
    traducteur → `framework_mandates`), ni écrire `question_coverage` (c'est l'aiguilleur du
    collecteur). Il VALIDE, il ne collecte pas.
    """
    fichier = fichier or load_frameworks()

    # N. le framework existe, à la bonne version.
    frameworks = {f.id: f for f in fichier.frameworks}
    fw = frameworks.get(plan.framework_id)
    if fw is None:
        raise CollectionPlanRefused(
            f"[N] framework `{plan.framework_id}` inconnu du référentiel ({sorted(frameworks)}) : "
            "un plan pour un framework qui n'existe pas ne collecte sur rien")
    if plan.framework_version != fichier.schema_version:
        raise CollectionPlanRefused(
            f"[N] plan en `{plan.framework_version}`, référentiel en `{fichier.schema_version}` : "
            "un plan daté d'une autre version décrit un framework qui a pu changer de questions")

    # O. l'archétype est déclaré. Vérifié AVANT de lire `variables_par_archetype[plan.archetype]` —
    #    le chargement garantit que chaque question couvre exactement les archétypes déclarés
    #    (invariant [I]), donc l'indexation qui suit est sûre une fois O franchi.
    if plan.archetype not in set(fichier.archetypes):
        raise CollectionPlanRefused(
            f"[O] archétype `{plan.archetype}` hors des archétypes déclarés "
            f"{sorted(fichier.archetypes)} : une question ne s'instancie que sur un archétype connu")

    questions = {q.id: q for q in fw.questions}

    # P + Q. chaque ligne résout, et ne vise pas une question sans objet pour cet archétype.
    for it in plan.items:
        q = questions.get(it.question_id)
        if q is None:
            raise CollectionPlanRefused(
                f"[P] la ligne vise la question `{it.question_id}`, absente de "
                f"`{plan.framework_id}` : une collecte qui ne s'indexe sur aucune question relie "
                "un fait à rien")
        ingredients = {i.id for i in q.ingredients_requis}
        if it.ingredient_id not in ingredients:
            raise CollectionPlanRefused(
                f"[P] `{it.question_id}` n'a pas d'ingrédient `{it.ingredient_id}` "
                f"({sorted(ingredients)}) : un ingrédient inventé écrirait le corrigé")
        if q.variables_par_archetype[plan.archetype].mode == "sans_objet":
            raise CollectionPlanRefused(
                f"[Q] `{it.question_id}` est SANS OBJET pour l'archétype `{plan.archetype}` : "
                "planifier sa collecte, c'est fabriquer une réponse là où le framework dit qu'il "
                "n'y a pas de question (§0.2)")

    # R. T1bis — chaque ingrédient essentiel d'une question APPLICABLE a une ligne. `sans_objet`
    #    n'a aucun ingrédient à collecter : on ne l'exige pas, mais on ne le tolère pas non plus (Q).
    couples = {(it.question_id, it.ingredient_id) for it in plan.items}
    for q in fw.questions:
        if q.variables_par_archetype[plan.archetype].mode != "variable":
            continue
        for i in q.ingredients_requis:
            if i.essentiel and (q.id, i.id) not in couples:
                raise CollectionPlanRefused(
                    f"[R] l'ingrédient essentiel `{q.id}.{i.id}` n'a AUCUNE ligne dans le plan : "
                    "un essentiel omis n'est pas un trou, c'est un plan REFUSÉ (T1bis). Il doit "
                    "sortir en `traduit` ou en `inobtenable motivé`, jamais en rien")
