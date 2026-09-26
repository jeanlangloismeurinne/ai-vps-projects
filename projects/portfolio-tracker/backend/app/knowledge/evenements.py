"""Ce qu'un événement publié ROUVRE — la taxonomie des événements (V3, lot 7, #89).

Pourquoi ce module existe (2026-09-26, RVMD)
--------------------------------------------
L'actualité d'une réponse se jugeait contre « le DERNIER événement substantiel » de l'émetteur
(`material_events.ancre_substantielle`). Chez RVMD, le dernier est un financement (27/08) ; la veille,
la FDA approuvait le premier médicament (26/08). Dire seulement « un financement ne rouvre pas la
barrière » aurait rendu les réponses de défendabilité À JOUR — alors que l'approbation de la veille
doit les rouvrir. Une fausse fraîcheur produite par une règle juste appliquée à la mauvaise horloge.

⟹ **Chaque question a sa propre horloge** : son ancre est le dernier événement d'un TYPE qui la
rouvre. Ce qui rouvre quoi est DÉCLARÉ par le référentiel (`frameworks.yaml`, `rouverte_par` par
question + le catalogue `types_evenement`) — créer un framework, c'est aussi décider ce qui rouvre
chacune de ses questions (arbitrage utilisateur du 2026-09-26). Ce module ne connaît aucune question.

Ce que fait un vrai fonds, et que ce module transcrit
-----------------------------------------------------
Le jour d'une publication, l'analyste la lit et écrit une note flash : quels points de la thèse sont
touchés. Il ne refait pas tout le dossier à chaque communiqué ; il ne laisse jamais un point touché
affiché comme à jour ; et dans le doute il rouvre (arbitrage Q3 : l'erreur coûteuse est le point
faussement à jour, pas le point revu pour rien).

La FORME d'un dépôt n'est pas sa SUBSTANCE
------------------------------------------
Les items 8-K décrivent la forme : l'item 8.01 « autre événement important » a porté chez RVMD une
approbation FDA ; un profit warning n'a pas d'item propre. `types_du_depot` ne qualifie par la forme
que ce que la forme DÉCIDE (2.03 est un financement, 2.01 un changement de périmètre…) ; tout le
reste est `a_qualifier`, un type que le catalogue déclare de portée TOTALE — tant que personne n'a lu
le communiqué, il rouvre tout. C'est la note flash (agent à venir) qui le requalifiera, jamais une
heuristique de mots.

Fonctions PURES : aucune IO, aucune écriture — l'ancre se recalcule à chaque lecture (#53).
"""
from __future__ import annotations

from dataclasses import replace
from typing import Optional

from app.knowledge.material_events import MaterialEvent, MaterialEventLookup

__all__ = [
    "A_QUALIFIER", "ROUTINE", "TYPE_PAR_ITEM", "TYPES_DE_LA_FORME",
    "types_du_depot", "ancre_de_la_question",
]

# Le type d'un dépôt dont la forme ne décide pas. Son nom est aussi sa consigne : quelqu'un doit le
# LIRE. Le catalogue du référentiel doit le déclarer de portée `toutes` (vérifié par le pont).
A_QUALIFIER = "a_qualifier"
# Le type d'un dépôt de pure forme (pièces jointes seules, vote ordinaire…) : il ne rouvre rien.
ROUTINE = "routine"

# Item 8-K → type, pour les seuls items dont la FORME décide la substance. Un item ABSENT de cette
# table est `a_qualifier` — jamais ignoré (même doctrine que `ITEM_LABELS` : une table qui filtre ce
# qu'elle ne connaît pas transforme un événement inconnu en non-événement).
TYPE_PAR_ITEM: dict[str, str] = {
    "1.03": "existentiel",          # faillite / redressement
    "1.05": "incident",             # cybersécurité
    "2.01": "perimetre",            # acquisition ou cession d'actifs
    "2.02": "resultats",            # résultats publiés (une SURPRISE ne se voit qu'à la lecture)
    "2.03": "financement",          # obligation financière directe
    "2.04": "existentiel",          # exigibilité anticipée d'une dette
    "3.01": "existentiel",          # radiation / non-conformité de cotation
    "3.02": "financement",          # émission de titres non enregistrée
    "3.03": "financement",          # modification des droits des porteurs
    "4.01": "integrite_comptes",    # changement de commissaire aux comptes
    "4.02": "integrite_comptes",    # états financiers antérieurs non fiables
    "5.01": "existentiel",          # changement de contrôle
    "5.02": "gouvernance",          # départ ou nomination de dirigeants
    "5.03": ROUTINE,                # statuts / exercice fiscal
    "5.07": ROUTINE,                # résultats du vote des actionnaires
}

# Items qui ACCOMPAGNENT un autre item sans porter de substance propre quand il y en a un : 9.01
# (pièces jointes) toujours ; 7.01 (communication Reg FD) quand il est le communiqué d'un item
# décidé par la forme. Seul, 7.01 peut être un avertissement sur résultats : il est alors à qualifier.
_ACCESSOIRES = frozenset({"9.01", "7.01"})

# Un « accord important » (1.01) n'est un financement que s'il crée l'obligation (2.03) ou émet les
# titres (3.02) dans le même dépôt ; sinon c'est peut-être une licence, un partenariat, un client —
# la forme ne le dit pas.
_PREUVES_DE_FINANCEMENT = frozenset({"2.03", "3.02"})

# L'ensemble des types que la FORME peut produire — le pont vérifie qu'ils sont tous au catalogue.
TYPES_DE_LA_FORME = frozenset(TYPE_PAR_ITEM.values()) | {A_QUALIFIER, ROUTINE, "financement"}


def types_du_depot(event: MaterialEvent) -> frozenset[str]:
    """Les types d'un dépôt, qualifié PAR SA FORME seule. Jamais vide.

    · aucun item déclaré (un 6-K, qui n'en porte jamais) → `a_qualifier` : « sans item » n'est pas
      « sans substance » (même règle que `ancre_substantielle`) ;
    · seulement des accessoires : 9.01 seul → `routine` ; 7.01 (± 9.01) seul → `a_qualifier` ;
    · sinon, l'union des types de chaque item substantiel ; un item non décidé par la forme
      (8.01, 1.01 sans preuve de financement, 1.02, 2.05, 2.06, un item inconnu…) ajoute
      `a_qualifier`, qui l'emporte par sa portée totale — dans le doute, on rouvre (Q3).
    """
    items = tuple(event.items)
    if not items:
        return frozenset({A_QUALIFIER})
    substantiels = [i for i in items if i not in _ACCESSOIRES]
    if not substantiels:
        return frozenset({A_QUALIFIER if "7.01" in items else ROUTINE})
    types: set[str] = set()
    for item in substantiels:
        if item == "1.01":
            types.add("financement" if _PREUVES_DE_FINANCEMENT & set(items) else A_QUALIFIER)
        else:
            types.add(TYPE_PAR_ITEM.get(item, A_QUALIFIER))
    return frozenset(types)


def ancre_de_la_question(
    lookup: MaterialEventLookup, *, rouvrent: frozenset[str],
) -> MaterialEventLookup:
    """L'ancre d'UNE question : le flux restreint aux dépôts dont un type la rouvre.

    `rouvrent` = les types déclarés par la question ∪ les types de portée totale du catalogue —
    l'appelant les calcule depuis le référentiel (`frameworks.types_qui_rouvrent`), ce module ne
    connaît aucune question.

    Les statuts `none` et `unavailable` traversent inchangés (#49) : on ne filtre pas une ignorance.
    Un flux `found` dont AUCUN dépôt ne rouvre la question rend `none` — un état CONNU — avec un
    `filtre` qui le dit, pour que le motif ne prétende pas que l'émetteur n'a rien publié.

    Chaque dépôt retenu porte ses `types`, que `MaterialEvent.resume()` écrit : le motif d'actualité
    dit alors POURQUOI cet événement compte pour cette question.
    """
    if lookup.status != "found":
        return lookup
    familles = ", ".join(sorted(rouvrent)) or "aucun type"
    gardes: list[MaterialEvent] = []
    for e in lookup.recents:
        types = types_du_depot(e)
        touches = types & rouvrent
        if touches:
            gardes.append(replace(e, types=tuple(sorted(touches))))
    if not gardes:
        n = len(lookup.recents)
        depuis: Optional[str] = (min(e.event_date for e in lookup.recents).isoformat()
                                 if lookup.recents else None)
        return MaterialEventLookup(
            status="none", cik=lookup.cik, recents=(),
            filtre=(f"aucun des {n} dépôts importants consultés"
                    + (f" (depuis le {depuis})" if depuis else "")
                    + f" n'est d'un type qui rouvre cette question ({familles})"))
    return MaterialEventLookup(status="found", event=gardes[0], cik=lookup.cik,
                               recents=tuple(gardes), filtre=familles)
