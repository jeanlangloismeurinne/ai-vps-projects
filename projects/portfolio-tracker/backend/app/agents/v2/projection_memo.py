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
from typing import Mapping, NamedTuple, Optional, Sequence

from app.contracts.framework_answer_schema import FrameworkAnswerServie, ManagerVerdict
from app.contracts.framework_definition_schema import FrameworksFile
from app.contracts.memo_blocs import BLOCS_MEMO
from app.contracts.comite_schema import PositionComite
from app.contracts.memo_projete_schema import (
    MemoProjete, PointProjete, RetenueParLeComite, RubriqueProjetee)

from app.agents.v2.frameworks import load_frameworks

__all__ = ["AnswerLue", "ProjectionRefusee", "projeter_memo", "memo_de_l_etat"]


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
    # Ce que le contrôle reproche à la réponse, RECALCULÉ à la lecture (#77). Lu seulement quand le
    # comité l'a retenue malgré tout (arbitrage A) : la note doit dire ce qu'il a surmonté.
    motif_revue: Optional[str] = None


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


def _motif_instruite(libelle: str, points: int, questions: int, non_acquittees: int,
                     retenues: int = 0) -> str:
    if retenues:
        base = (f"méthodologie « {libelle} » — {points} point(s) publié(s) sur {questions} "
                f"question(s) instruite(s) : {points - retenues} acquitté(s) par le contrôle, "
                f"{retenues} retenu(s) par le comité malgré leur faiblesse")
    else:
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
    comite: Mapping[tuple[str, str], PositionComite],
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

    `comite` : la position du comité par (framework, question), SERVIE (`EtatDossier.comite`).
    REQUIS pour la même raison qu'`archetype` : un assembleur qui l'oublierait publierait une note
    qui ignore les décisions du comité alors que l'alerte les compte (arbitrage A). Une réponse non
    acquittée entre dans la note SSI le comité l'a acceptée, que l'acceptation tient AUJOURD'HUI,
    et qu'elle porte sur CETTE réponse — et elle y entre marquée, avec sa faiblesse.
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
        # Une réponse entre dans la note par le contrôle (acquittée) OU par le comité (retenue
        # malgré sa faiblesse, arbitrage A) — jamais par aucun des deux.
        publiees: list[tuple[AnswerLue, Optional[RetenueParLeComite]]] = []
        for lue in du_framework:
            if lue.answer.manager is not None and lue.answer.manager.verdict == "acquitte":
                publiees.append((lue, None))
                continue
            retenue = _retenue(comite.get((f.id, lue.answer.question_id)), lue)
            if retenue is not None:
                publiees.append((lue, retenue))
        publiees.sort(key=lambda p: (rang[p[0].answer.question_id], p[0].answer.analyste))
        non_acquittees = len(du_framework) - len(publiees)
        retenues = sum(1 for _l, r in publiees if r is not None)

        points = [
            PointProjete(
                question_id=lue.answer.question_id,
                enonce=enonces[lue.answer.question_id].enonce,
                chemin_indexation=enonces[lue.answer.question_id].chemin_indexation,
                answer=lue.answer,
                answer_id=lue.answer_id,
                retenue_par_comite=retenue,
            )
            for lue, retenue in publiees
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
                motif=_motif_instruite(f.libelle, len(points), len(f.questions), non_acquittees,
                                       retenues),
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


def _retenue(position: Optional[PositionComite], lue: AnswerLue) -> Optional[RetenueParLeComite]:
    """La décision du comité qui fait entrer CETTE réponse non acquittée dans la note, ou None.

    Trois conditions, chacune un faux si on la lâche : la dernière décision est une ACCEPTATION (un
    renvoi postérieur l'a remplacée) ; elle est EN VIGUEUR aujourd'hui (tombée sur un fait nouveau,
    elle ne fonde plus rien) ; elle porte sur CETTE réponse (le comité a lu une version précise).
    """
    if position is None or position.acceptation is None:
        return None
    acc = position.acceptation
    if acc.etat != "en_vigueur" or acc.decision.answer_id != lue.answer_id:
        return None
    return RetenueParLeComite(
        acceptation=acc,
        faiblesse=lue.motif_revue or "le contrôle qualité n'a pas pu relire cette réponse")


def memo_de_l_etat(etat, *, genere_le: Optional[datetime] = None) -> MemoProjete:
    """DÉTENTEUR UNIQUE (#46) de l'assemblage état du dossier → note. L'endpoint, l'outil
    `montrer_parcours`, `servir_memo` et les checks passent tous par ici : cinq assembleurs
    recopiés, c'est cinq endroits où oublier le comité (arbitrage A) ou le motif de la revue."""
    lues = [AnswerLue(answer_id=r.answer_id, answer=r.servie, motif_revue=r.motif_revue)
            for r in etat.reponses]
    return projeter_memo(ticker_id=etat.ticker_id, lues=lues, archetype=etat.archetype,
                         comite=etat.comite, fichier=etat.fichier,
                         genere_le=genere_le or etat.genere_le)


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

    ⚠️ UN RENVOI N'EST ATTACHÉ QUE S'IL A SON MANDAT
    Le contrat exige qu'un renvoi porte l'id du mandat qui le matérialise
    (`_un_renvoi_produit_quelque_chose`, Écart B). L'assembleur le complète par le mandat OUVERT sur
    la question ; s'il n'y en a pas, il n'invente rien (`renvoi_a_emettre`, niveau 3 du parcours).
    Ici seuls comptent les acquittements ; le complément est publié en clair :
    `RubriqueProjetee.reponses_non_acquittees`.

    Le corpus chargé porte `source_date` (lu par `date_effective`) et `reliability_tier` (lu par le
    contrôle ③ d'honnêteté). Pas `content` : rien ne le consomme, et il donnerait l'illusion d'une
    note enrichie.
    """
    # L'assemblage (réponses courantes → pièces → revue recalculée → service) a UN détenteur depuis
    # le lot 6 : `parcours.charger_etat_dossier`, que partagent la note de qualité et les trois
    # niveaux du parcours. Import tardif : ce module est importé par des checks sans base ni réseau.
    from app.agents.v2.parcours import charger_etat_dossier

    return memo_de_l_etat(await charger_etat_dossier(conn, ticker_id))
