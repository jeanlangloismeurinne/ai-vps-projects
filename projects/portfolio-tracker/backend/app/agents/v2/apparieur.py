"""L'APPARIEUR — maillon 4bis du lot 3 : le pont entre une carte d'appariement et le RÉEL.

Le contrat (`app/contracts/appariement_schema.py`) garantit qu'une ligne d'appariement est cohérente
AVEC ELLE-MÊME : un `exact` porte un concept et rien d'autre, une `approximation` porte sa formule et
ses hypothèses. Il ne peut rien dire de plus, parce qu'un contrat valide un objet et jamais la
cohérence entre deux (#37). Or tout ce qui rend un appariement VRAI est relationnel :

  · le concept nommé est-il DÉPOSÉ par cet émetteur-là ?
  · l'ingrédient apparié existe-t-il dans le plan, et le plan a-t-il dit qu'on le cherchait ?
  · la formule repose-t-elle sur les concepts déclarés, ou sur d'autres qu'on n'a jamais vérifiés ?

C'EST LA GARDE QUI MANQUAIT, ET QUI BLOQUE LA COLLECTE RÉELLE
--------------------------------------------------------------
`collecte_executor.poste_retenu()` vérifie aujourd'hui deux choses — que le poste appartient au
catalogue, et que la métrique n'est pas une dérivation — et **jamais** que le poste nommé répond à la
métrique. « clauses restrictives (covenants) des contrats de dette → `total_liabilities` » traverse
ces deux contrôles sans une alerte : le poste est au catalogue, la métrique ne contient aucun
opérateur. Le lien de couverture porterait alors le bon libellé en face du MAUVAIS nombre (#43/#60),
et rien en aval ne le rattrape — un nombre exact est indiscernable d'un nombre juste.

Le remède par le PROMPT a été mesuré, puis disqualifié : 11 lignes / 11 justes sur NVDA, et le MÊME
prompt sur MSFT rend 15 lignes dont 10 fausses (`feedback_jugement_modele_instable_entre_passages`).
Une garantie qui dépend d'une formulation n'est pas une garantie. D'où ce fichier : le modèle
PROPOSE, le code VÉRIFIE.

CE QUE CE PONT ATTRAPE, ET CE QU'IL N'ATTRAPE PAS — À LIRE AVANT DE S'Y FIER
-----------------------------------------------------------------------------
Il attrape la classe de fautes qui est décidable sans comprendre la question :

  · un concept INVENTÉ ou approchant. C'est le mode de panne de
    `feedback_adressage_par_nom_exige_lecture` : un émetteur dépose entre 269 et 627 concepts, bien
    au-delà de ce qu'un modèle restitue de mémoire, donc il écrit un nom VOISIN (`InventoryNet` là où
    l'émetteur dépose `InventoryNetCurrent`) et fabrique un appariement silencieux. Confronté à
    l'inventaire, ce nom n'existe pas ;
  · un concept que CET émetteur-là ne dépose pas, même s'il est parfaitement réel ailleurs — les six
    postes absents de RVMD ;
  · un concept qui n'apparaît QUE dans la formule, donc qui échapperait à la vérification ci-dessus ;
  · un `deterministe=True` posé sur une formule qui contient un coefficient choisi.

Il n'attrape PAS le faux appariement SÉMANTIQUE : `Liabilities` est déposé par tous les émetteurs, et
l'apparier aux « clauses restrictives » passerait l'inventaire. Ce n'est pas un oubli, c'est la
frontière de ce qui se décide en code. Ce que le maillon 4bis oppose à cette faute-là n'est pas un
`if`, c'est la FORME de la réponse : un `exact` ne peut porter qu'UN concept nu, sans formule et sans
hypothèse, donc tout ce qui demande un raisonnement doit sortir en `approximation` — où le
raisonnement est ÉCRIT, et où le lecteur peut le contester. Le système cesse d'avoir à choisir entre
mentir et renoncer ; c'est ce que la troisième case achète.

Ces asserts gardent donc une STRUCTURE, jamais une sémantique, et ils le disent — même discipline que
`check_collecte_executor` §3bis, qui garde l'énoncé du prompt et jamais son comportement.
"""
from __future__ import annotations

import re
from typing import Collection, Optional

from app.contracts.appariement_schema import AppariementCarte, AppariementItem
from app.contracts.collection_plan_schema import CollectionPlan

__all__ = [
    "AppariementRefuse",
    "concepts_de_la_formule",
    "coefficients_choisis",
    "valider_pont_appariement",
]


class AppariementRefuse(Exception):
    """La carte d'appariement contredit le réel (l'inventaire déposé) ou le plan dont elle dérive.

    Un refus, jamais une dégradation silencieuse : une carte à moitié valide ferait router au web des
    ingrédients dont on croirait avoir vérifié l'appariement.
    """


# Un concept XBRL s'écrit en CamelCase et commence par une majuscule (`NetIncomeLoss`,
# `LiabilitiesCurrent`). Les mots en minuscules d'une formule sont de la prose ou un terme web ; ils
# ne sont pas des concepts déposés et ne se cherchent donc pas dans l'inventaire.
_RE_CONCEPT = re.compile(r"\b[A-Z][A-Za-z0-9]*\b")

# Un littéral DÉCIMAL dans une formule est la signature d'un coefficient CHOISI — « 60 % du capex est
# du maintien ». Un entier ne l'est pas : c'est une conversion d'unité ou de période (`/4` pour un
# trimestre, `*12` pour annualiser un mois), et il n'introduit aucun paramètre à débattre.
#
# ⚠️ La règle est NÉCESSAIRE, pas suffisante, et c'est délibéré : un coefficient peut se cacher dans
# un entier (`*3` pour « trois ans de capex normatif »). Ce que ce contrôle garantit, c'est qu'un
# `deterministe=True` portant un pourcentage visible est REFUSÉ — pas qu'un `deterministe=True` qui
# passe soit vrai. Le reste est porté par les hypothèses écrites, qui sont lisibles et contestables.
_RE_DECIMAL = re.compile(r"\b\d+[.,]\d+\b")


def concepts_de_la_formule(formule: str) -> set[str]:
    """Les identifiants CamelCase référencés par une formule. Pur, hors-ligne."""
    return set(_RE_CONCEPT.findall(formule))


def coefficients_choisis(formule: str) -> list[str]:
    """Les littéraux décimaux d'une formule — la signature d'un paramètre choisi. Pur, hors-ligne."""
    return _RE_DECIMAL.findall(formule)


def valider_pont_appariement(
    carte: AppariementCarte,
    inventaire: Collection[str],
    *,
    plan: Optional[CollectionPlan] = None,
) -> None:
    """Vérifie qu'une carte d'appariement est cohérente avec l'INVENTAIRE réel et avec son plan.
    Ne rend rien : le seul résultat possible est « pas de refus ».

    `inventaire` = les noms de concepts `us-gaap` RÉELLEMENT déposés par cet émetteur, tels que
    `edgar_facts.fetch_company_facts()` les rend. On le reçoit déjà lu plutôt que de l'aller chercher
    ici : le pont reste PUR, donc rejouable hors-ligne et testable sans réseau — la frontière
    gratuite avant toute dépense.

    `plan` est facultatif pour que la carte puisse se valider seule contre l'inventaire (le cas de la
    REVÉRIFICATION À LA LECTURE, où le plan n'est pas forcément rechargé). Quand il est fourni, les
    invariants relationnels [S]/[T]/[U] s'y ajoutent.

    Les invariants, chacun gardant un mode de panne qui se lit comme un succès :

      U. la carte et le plan parlent du MÊME (ticker, framework, version). Une carte appliquée au
         plan d'une autre version apparie des ingrédients qui ont pu changer de sens ;
      S. chaque appariement correspond à une ligne `traduit` du plan. Apparier une ligne
         `inobtenable` est une contradiction : le plan a déjà établi qu'aucune source ne la produit ;
      T. chaque ligne `traduit` a un appariement. Une omission n'est pas un trou — c'est la carte qui
         est REFUSÉE. Un ingrédient sans appariement repart au web en silence, donc en tier B, pour
         un niveau brut que la SEC publie en tier A : le VERT qui masque la perte ;
      V. LE CŒUR — chaque concept nommé est DÉPOSÉ par CET émetteur. C'est la garde absente de
         `poste_retenu()`, et la seule qui ne puisse pas se remplacer par une formulation ;
      W. la formule ne référence QUE des concepts déclarés, et les déclare TOUS. Un concept présent
         dans la seule formule échapperait à [V] ; un concept déclaré et jamais utilisé fait compter
         au tier un ingrédient qui n'entre pas dans le calcul ;
      X. `deterministe=True` interdit un coefficient décimal visible dans la formule.
    """
    if not inventaire:
        raise AppariementRefuse(
            "[V] inventaire VIDE : un inventaire vide est un défaut de récupération, jamais un "
            "émetteur muet (même lecture que `EdgarUnavailable`). Valider une carte contre un "
            "inventaire vide refuserait tous les concepts, et la carte se relirait comme un émetteur "
            "qui ne publie rien")
    depose = set(inventaire)

    if plan is not None:
        # U. même sujet, même version.
        if (carte.ticker_id, carte.framework_id, carte.framework_version) != (
                plan.ticker_id, plan.framework_id, plan.framework_version):
            raise AppariementRefuse(
                f"[U] la carte porte sur ({carte.ticker_id}, {carte.framework_id}, "
                f"{carte.framework_version}) et le plan sur ({plan.ticker_id}, {plan.framework_id}, "
                f"{plan.framework_version}) : une carte appariée contre un autre plan décrit des "
                "ingrédients qui ont pu changer de sens entre deux versions")

        traduits = {(it.question_id, it.ingredient_id)
                    for it in plan.items if it.statut == "traduit"}
        inobtenables = {(it.question_id, it.ingredient_id)
                        for it in plan.items if it.statut == "inobtenable"}

        # S. on n'apparie que ce que le plan a dit chercher.
        for it in carte.items:
            couple = (it.question_id, it.ingredient_id)
            if couple in inobtenables:
                raise AppariementRefuse(
                    f"[S] `{it.question_id}.{it.ingredient_id}` est `inobtenable` au plan et porte "
                    f"pourtant un appariement `{it.statut}` : le plan a établi qu'aucune source "
                    "connue ne produit cet ingrédient ; lui trouver un champ déposé contredit le "
                    "motif qui l'accompagne, et l'un des deux est faux")
            if couple not in traduits:
                raise AppariementRefuse(
                    f"[S] `{it.question_id}.{it.ingredient_id}` est apparié sans ligne au plan : un "
                    "appariement qui ne s'indexe sur aucune ligne relie un champ déposé à rien, et "
                    "sa collecte ne rejoindra aucune question")

        # T. et on apparie TOUT ce que le plan a dit chercher.
        apparies = {(it.question_id, it.ingredient_id) for it in carte.items}
        manquants = sorted(traduits - apparies)
        if manquants:
            raise AppariementRefuse(
                f"[T] {len(manquants)} ligne(s) `traduit` du plan n'ont AUCUN appariement "
                f"{manquants[:5]} : une omission n'est pas un trou, c'est une carte REFUSÉE. Un "
                "ingrédient sans appariement repart chercher au web, en tier B, un niveau brut que "
                "la SEC publie en tier A — et la couverture restera à 100 % sur ce qui reste")

    # V + W + X. le réel, ligne par ligne.
    for it in carte.items:
        _valider_ligne(it, depose)


def _valider_ligne(it: AppariementItem, depose: set[str]) -> None:
    """Les trois invariants qui ne regardent QUE la ligne et l'inventaire. Séparé pour que la
    revérification à la lecture (#54) puisse l'appeler ligne à ligne sans recharger un plan."""
    ou = f"`{it.question_id}.{it.ingredient_id}`"

    # V. LE CŒUR. Chaque concept nommé est déposé par CET émetteur.
    absents = sorted(c for c in it.concepts if c not in depose)
    if absents:
        raise AppariementRefuse(
            f"[V] {ou} nomme {absents}, que cet émetteur NE DÉPOSE PAS (inventaire de "
            f"{len(depose)} concepts). Un nom voisin d'un concept réel est le mode de panne d'un "
            "adressage par nom sans outil de lecture : il produit un appariement d'apparence "
            "normale, et la collecte remontera un vide ou un autre nombre")

    if it.statut != "approximation":
        return
    assert it.formule is not None  # garanti par le contrat : `approximation` ⟹ formule

    # W. la formule et les concepts déclarés disent la même chose.
    refs = concepts_de_la_formule(it.formule)
    declares = set(it.concepts)
    hors_declaration = sorted(refs - declares)
    if hors_declaration:
        raise AppariementRefuse(
            f"[W] {ou} référence {hors_declaration} dans sa formule sans les déclarer en "
            f"`concepts` : un concept qui n'existe que dans la formule échappe à la confrontation "
            "avec l'inventaire [V] — c'est la porte dérobée par laquelle un concept inventé "
            "rentrerait quand même dans le calcul")
    inutilises = sorted(declares - refs)
    if inutilises:
        raise AppariementRefuse(
            f"[W] {ou} déclare {inutilises} sans les employer dans sa formule : un ingrédient qui "
            "n'entre pas dans le calcul pèse quand même sur le tier dérivé (#67 lit le plus FAIBLE "
            "des ingrédients) — il ferait monter ou descendre la fiabilité d'un nombre auquel il ne "
            "contribue pas")

    # X. un déterminisme déclaré ne survit pas à un coefficient visible.
    if it.deterministe:
        coefs = coefficients_choisis(it.formule)
        if coefs:
            raise AppariementRefuse(
                f"[X] {ou} se déclare `deterministe` mais sa formule porte {coefs} : un coefficient "
                "décimal est un paramètre CHOISI, donc un calcul non déterministe — il descend d'un "
                "cran (#67). C'est exactement ce qui sépare `capital_employe` (une soustraction de "
                "postes déposés) de `investissement_de_maintien` (« la PART du capex nécessaire au "
                "maintien »), et le confondre rendrait une estimation en tier A")
