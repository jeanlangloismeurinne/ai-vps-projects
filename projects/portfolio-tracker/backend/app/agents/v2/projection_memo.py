"""LE PROJECTEUR — la note de comité produite depuis le classeur (chantier v3, lot 5, spec §6).

DÉTENTEUR UNIQUE (#46) de la projection framework → chapitre de note. Personne d'autre ne décide
ce qu'un chapitre contient.

⚠️ CE FICHIER NE NOMME AUCUN FRAMEWORK, ET C'EST TOUTE LA GARANTIE DU LOT
--------------------------------------------------------------------------
La feuille de route l'exige : « ajouter une méthodologie doit être une opération de DONNÉES, jamais
de code ». Ici, `qualite_financiere` et `defendabilite` n'apparaissent nulle part — ni en constante,
ni en `if`, ni en table de correspondance. Le lien vit dans `frameworks.yaml` (`bloc_memo`), et ce
module l'itère.

Le test qui le prouve n'est pas « les 2 rubriques marchent » : ce serait vrai d'un projecteur qui
les aurait codées en dur. C'est **« un 3ᵉ framework fictif ajouté en YAML SEUL se projette sans
diff de code »** (`check_memo_projete.py` §4). La garantie porte sur la croissance, elle se teste
sur la croissance — et le cas négatif correspondant mute le YAML, pas le Python.

CE QUE LE PROJECTEUR NE FAIT PAS
---------------------------------
  · il ne RÉDIGE rien. Aucun appel de modèle, aucune phrase sur l'émetteur : il transporte des
    réponses déjà acquittées. Tout ce qu'il écrit est un motif d'ÉTAT, en langue déterministe ;
  · il n'AGRÈGE pas. Deux analystes sur une même question donnent DEUX points, jamais une moyenne
    (§3.4) — moyenner reproduirait la cause n°1 du diagnostic #50 ;
  · il ne JUGE pas. Aucun verdict d'investissement : la note sort `posture='NEUTRE'`, et le contrat
    ne lui laisse nulle part où écrire autre chose (verrou Q2) ;
  · il n'ÉCRIT pas. Produit à la lecture, jamais persisté (#53/#54).

POURQUOI UN REFUS PLUTÔT QU'UN SAUT
------------------------------------
Une réponse orpheline (framework inconnu, question inconnue, version périmée) est écartée par un
REFUS qui lève, jamais par un `continue`. Sautée, elle rétrécirait la note en silence : un chapitre
passerait de `instruite` à `sans_acquittement` sans qu'aucun décompte ne bouge, et le comité
lirait « rien n'a passé le contrôle » là où la vérité est « le référentiel a bougé sous les
réponses ». Un contrôle qui dégrade en sortant à zéro est un vert
(`feedback_check_degrade_en_sortant_a_zero`).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import NamedTuple, Optional, Sequence

from app.contracts.framework_answer_schema import FrameworkAnswerServie, ManagerVerdict
from app.contracts.framework_definition_schema import FrameworksFile
from app.contracts.memo_blocs import BLOCS_MEMO
from app.contracts.memo_projete_schema import MemoProjete, PointProjete, RubriqueProjetee

from app.agents.v2.frameworks import load_frameworks

__all__ = ["AnswerLue", "ProjectionRefusee", "projeter_memo"]


class ProjectionRefusee(Exception):
    """Refus de PROJECTION — des réponses formellement valides, mais qui ne se rangent pas.

    Levée, jamais rendue en valeur : un refus qui se lit comme un résultat finit par être ignoré.
    Distincte des trois autres refus du chantier — elle ne dit ni que le référentiel est cassé
    (`FrameworkDefinitionRefused`), ni qu'une réponse l'est (`FrameworkAnswerRefused`), ni qu'un
    plan l'est (`CollectionPlanRefused`), mais que la note ne peut pas être dressée.
    """


class AnswerLue(NamedTuple):
    """Une réponse telle qu'elle sort de la base : sa ligne et son contenu SERVI.

    Le type d'entrée est `FrameworkAnswerServie`, pas `FrameworkAnswer` : l'axe actualité se
    recalcule à la lecture (#53), et l'exiger dans le type vaut mieux que l'espérer dans une
    consigne. Un appelant qui aurait oublié `servir_answer()` ne construit pas son objet.
    """
    answer_id: Optional[int]
    answer: FrameworkAnswerServie


def _motif_sans_methodologie() -> str:
    return ("aucune méthodologie approuvée ne projette sur ce chapitre — l'absence est une "
            "décision du fonds, pas une propriété de l'émetteur")


def _motif_sans_acquittement(libelle: str, au_dossier: int, questions: int) -> str:
    if au_dossier == 0:
        return (f"méthodologie « {libelle} » approuvée ({questions} question(s)) — aucune réponse "
                f"au dossier pour cet émetteur")
    return (f"méthodologie « {libelle} » approuvée ({questions} question(s)) — {au_dossier} "
            f"réponse(s) au dossier, aucune acquittée par le manager")


def _motif_non_revalidable(libelle: str, au_dossier: int, questions: int) -> str:
    """Le motif de l'état qui dit « la revue n'a PAS PU avoir lieu ».

    Il nomme le remède, et ce remède est le nôtre : classer l'émetteur. Écrire ici « aucune réponse
    acquittée » ferait porter à l'émetteur une lacune de NOTRE saisie — le faux mesuré sur RVMD le
    2026-09-24, celui pour lequel ce quatrième état existe.
    """
    return (f"méthodologie « {libelle} » approuvée ({questions} question(s)), {au_dossier} "
            f"réponse(s) au dossier — mais l'émetteur n'est PAS CLASSÉ : on ignore quelles "
            "questions lui sont applicables, donc aucune revue n'a pu avoir lieu. Ce n'est pas un "
            "refus du manager, c'est un classement qui manque au dossier")


def _motif_instruite(libelle: str, points: int, questions: int, non_acquittees: int) -> str:
    base = (f"méthodologie « {libelle} » — {points} point(s) acquitté(s) sur {questions} "
            f"question(s) instruite(s)")
    if non_acquittees:
        return f"{base} ; {non_acquittees} réponse(s) au dossier non acquittée(s)"
    return base


def projeter_memo(
    *,
    ticker_id: str,
    lues: Sequence[AnswerLue],
    archetype: Optional[str],
    fichier: Optional[FrameworksFile] = None,
    genere_le: Optional[datetime] = None,
) -> MemoProjete:
    """Dresse la note de comité de `ticker_id` depuis les réponses `lues`. N'écrit rien.

    `lues` : les réponses COURANTES de cet émetteur pour la version de référentiel en vigueur —
    `framework_persist.read_answers_courantes()` les filtre, puis `frameworks.servir_answer()` les
    sert. La sélection « courantes » appartient à la base (`superseded_by IS NULL`) ; la refaire
    ici en referait un jumeau.

    `archetype` : le classement de l'émetteur, ou `None` s'il n'est pas classé. REQUIS, sans valeur
    par défaut — un appelant qui l'oublie doit échouer, pas hériter d'un `None` silencieux qui
    ferait sortir toute la note en `non_revalidable` (`feedback_optional_schema_gate`). Ce paramètre
    ne sert pas à re-réviser ici : la revue est faite par `servir_memo`, en amont. Il sert à dire
    au comité POURQUOI une rubrique est vide — « rien n'a passé les contrôles » (le dossier) ou
    « personne n'a pu relire » (notre saisie).
    """
    fichier = fichier or load_frameworks()
    genere_le = genere_le or datetime.now(timezone.utc)

    # L'ordre du jour, dans l'ordre du contrat. Aucun nom de chapitre n'est écrit ici.
    par_bloc = {f.bloc_memo: f for f in fichier.frameworks}
    par_framework = {f.id: f for f in fichier.frameworks}

    # ── Les refus, AVANT toute répartition ────────────────────────────────────────────────────
    # Prononcés d'abord : une réponse orpheline écartée plus tard aurait déjà faussé un décompte.
    for lue in lues:
        a = lue.answer
        if a.ticker_id != ticker_id:
            raise ProjectionRefusee(
                f"réponse de `{a.ticker_id}` dans la note de `{ticker_id}` — une note qui mélange "
                "deux émetteurs est pire qu'une note vide")
        f = par_framework.get(a.framework_id)
        if f is None:
            raise ProjectionRefusee(
                f"réponse `{a.question_id}` rattachée au framework `{a.framework_id}`, absent du "
                f"référentiel ({sorted(par_framework)}) — sautée, elle rétrécirait la note en "
                "silence et le comité lirait « rien n'a passé le contrôle »")
        if a.framework_version != fichier.schema_version:
            raise ProjectionRefusee(
                f"réponse `{a.question_id}` en `{a.framework_version}`, référentiel en "
                f"`{fichier.schema_version}` — une réponse à un énoncé qui a changé n'est plus la "
                "réponse à la question qu'on publie (§2.4/§5.2, écart V10)")
        if a.question_id not in {q.id for q in f.questions}:
            raise ProjectionRefusee(
                f"question `{a.question_id}` inconnue du framework `{f.id}` — une réponse qui ne "
                "s'indexe sur aucune question s'indexerait sur une question voisine")

    # ── La répartition ────────────────────────────────────────────────────────────────────────
    rubriques: list[RubriqueProjetee] = []
    for bloc in BLOCS_MEMO:
        f = par_bloc.get(bloc)
        if f is None:
            rubriques.append(RubriqueProjetee(
                bloc=bloc,
                etat="pas_de_methodologie_approuvee",
                motif=_motif_sans_methodologie(),
            ))
            continue

        enonces = {q.id: q for q in f.questions}
        du_framework = [lue for lue in lues if lue.answer.framework_id == f.id]
        # Acquittées SEULEMENT. Le tri n'est pas cosmétique : la note se lit dans l'ordre des
        # questions du référentiel, pas dans celui où la base a rendu ses lignes — un ordre qui
        # dépend de la base ferait bouger la note sans qu'aucune donnée ne change.
        rang = {q.id: i for i, q in enumerate(f.questions)}
        acquittees = sorted(
            (lue for lue in du_framework
             if lue.answer.manager is not None and lue.answer.manager.verdict == "acquitte"),
            key=lambda lue: (rang[lue.answer.question_id], lue.answer.analyste),
        )
        non_acquittees = len(du_framework) - len(acquittees)

        points = [
            PointProjete(
                question_id=lue.answer.question_id,
                enonce=enonces[lue.answer.question_id].enonce,
                chemin_indexation=enonces[lue.answer.question_id].chemin_indexation,
                answer=lue.answer,
                answer_id=lue.answer_id,
            )
            for lue in acquittees
        ]

        commun = dict(
            bloc=bloc,
            framework_id=f.id,
            libelle=f.libelle,
            methodologie=f.methodologie,
            framework_version=fichier.schema_version,
            reponses_non_acquittees=non_acquittees,
        )
        if archetype is None:
            # Aucune revue n'a pu avoir lieu : sans classement, `questions_applicables` ne sait pas
            # quelles questions s'appliquent. L'état le DIT plutôt que de laisser le décompte à zéro
            # se lire comme un refus. Il précède le test sur `points` parce qu'un point acquitté
            # sous un émetteur non classé ne peut pas exister — et s'il en arrivait un, la garde de
            # `RubriqueProjetee` lèverait plutôt que de le publier.
            rubriques.append(RubriqueProjetee(
                etat="non_revalidable",
                motif=_motif_non_revalidable(f.libelle, len(du_framework), len(f.questions)),
                **commun,
            ))
        elif points:
            rubriques.append(RubriqueProjetee(
                etat="instruite",
                motif=_motif_instruite(f.libelle, len(points), len(f.questions), non_acquittees),
                points=points,
                **commun,
            ))
        else:
            rubriques.append(RubriqueProjetee(
                etat="sans_acquittement",
                motif=_motif_sans_acquittement(f.libelle, non_acquittees, len(f.questions)),
                **commun,
            ))

    return MemoProjete(
        ticker_id=ticker_id,
        genere_le=genere_le,
        framework_version=fichier.schema_version,
        rubriques=rubriques,
    )


async def servir_memo(conn, ticker_id: str) -> MemoProjete:
    """LE POINT DE LECTURE de la note : base → revue RECALCULÉE → réponses servies → projection.

    N'écrit rien — ni verdict, ni mandat, ni note.

    DÉTENTEUR UNIQUE de l'assemblage (#46) : l'outil `montrer_memo_projete`, le check et
    l'endpoint du lot 6 passent tous par ici. Trois assembleurs, c'est trois façons de rater
    `servir_answer()` — et la note sortirait alors sans axe actualité, donc en servant le verdict
    d'avant le dernier événement matériel (#53/#54).

    ⚠️ POURQUOI L'AVIS DU MANAGER SE RECALCULE ICI, ET NE SE LIT PAS EN BASE
    Il n'y est pas, et c'est l'arbitrage du 2026-09-21 (#77) : les 4 contrôles dépendent du corpus,
    des dispenses et de l'actualité, qui bougent. Un acquittement figé servirait le verdict d'avant
    la rétractation d'une pièce. `reviser_framework` est PURE (aucun appel de modèle), donc le
    recalcul à la lecture ne coûte rien et ne peut pas dériver de ce qui serait stocké.

    ⚠️ SEULS LES ACQUITTEMENTS SONT ATTACHÉS, JAMAIS LES RENVOIS
    Un renvoi n'est pas un verdict complet : le contrat exige qu'il porte l'id du mandat qui le
    matérialise (`_un_renvoi_produit_quelque_chose`, Écart B). Cet id est attribué par la BASE, à
    l'écriture — or cette fonction est une LECTURE. Fabriquer un id ici, ou attacher un renvoi sans
    id, inventerait une pièce qui n'existe pas. Le complément est publié quand même, en clair :
    `RubriqueProjetee.reponses_non_acquittees`.

    Le corpus chargé porte `source_date` (lu par `date_effective`) et `reliability_tier` (lu par le
    contrôle ③ d'honnêteté). Pas `content` : rien ne le consomme, et il donnerait l'illusion d'une
    note enrichie.
    """
    # Imports tardifs : ce module est importé par des checks sans base ni réseau. En tête, ils
    # tireraient asyncpg et le client EDGAR pour une projection qui est purement en mémoire.
    from app.agents.v2.frameworks import servir_answer
    from app.agents.v2.framework_persist import (
        read_answers_courantes, read_archetype, read_dispenses)
    from app.agents.v2.manager import reviser_framework
    from app.agents.v2.manager_persist import assemble_verdict
    from app.knowledge.material_events import material_anchor_for_ticker

    fichier = load_frameworks()
    brutes = await read_answers_courantes(
        conn, ticker_id=ticker_id, framework_version=fichier.schema_version)

    cites: set[int] = set()
    for _id, a in brutes:
        if a.fondation is not None:
            cites.update(a.fondation.cited_entry_ids)
        if a.approximation is not None:
            cites.update(a.approximation.ingredients_entry_ids)

    entries: dict[int, dict] = {}
    if cites:
        rows = await conn.fetch(
            "SELECT id, source_date, reliability_tier FROM knowledge_entries "
            "WHERE id = ANY($1::int[])",
            sorted(cites))
        entries = {r["id"]: {"source_date": r["source_date"],
                             "reliability_tier": r["reliability_tier"]} for r in rows}

    classement = await read_archetype(conn, ticker_id=ticker_id)
    archetype = classement[0] if classement is not None else None

    # ── La revue, recalculée framework par framework ──────────────────────────────────────────
    # `autres_reponses` est keyé par l'ID DE LIGNE (contrôle ④, non-substitution) : la clef vient
    # de la base, pas d'un index de boucle qui changerait avec l'ordre de lecture.
    verdicts: dict[int, ManagerVerdict] = {}
    if archetype is not None:
        par_ligne = {i: a for i, a in brutes}
        for f in fichier.frameworks:
            du_framework = [(i, a) for i, a in brutes if a.framework_id == f.id]
            if not du_framework:
                continue
            dispenses = frozenset(await read_dispenses(
                conn, ticker_id=ticker_id, framework_id=f.id,
                framework_version=fichier.schema_version))
            revue = reviser_framework(
                [a for _i, a in du_framework],
                fichier=fichier, framework_id=f.id, archetype=archetype,
                ticker_id=ticker_id, entries=entries, dispenses=dispenses,
                autres_reponses=par_ligne,
            )
            for i, a in du_framework:
                d = revue.decisions.get((a.question_id, a.analyste))
                if d is None or d.verdict != "acquitte":
                    continue
                verdicts[i] = assemble_verdict(d, mandat_de_recherche_id=None)

    ancre = await material_anchor_for_ticker(conn, ticker_id)
    lues = []
    for i, a in brutes:
        # `model_copy` ne valide pas — mais `servir_answer` reconstruit un `FrameworkAnswerServie`
        # depuis le dump, donc le verdict attaché repasse par le contrat entier (qui re-vérifie
        # notamment qu'un acquittement ne porte pas de mandat).
        if i in verdicts:
            a = a.model_copy(update={"manager": verdicts[i]})
        lues.append(AnswerLue(answer_id=i, answer=servir_answer(a, ancre=ancre, entries=entries)))

    return projeter_memo(
        ticker_id=ticker_id, lues=lues, archetype=archetype, fichier=fichier)
