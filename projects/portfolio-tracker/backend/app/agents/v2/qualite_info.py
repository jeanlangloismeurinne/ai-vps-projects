"""DÉRIVATION de `qualite_info` — la mesure de qualité d'information (chantier v3, lot 6, spec §7).

DÉTENTEUR UNIQUE (#46) de la règle « comment un dossier de réponses devient une mesure de qualité
d'information ». Personne d'autre ne décide ce que valent un `sans_objet`, un `approxime` ou une
réponse périmée.

FONCTION PURE, PRODUITE À LA LECTURE (#53/#54)
----------------------------------------------
`derive_qualite_info` consomme des réponses DÉJÀ SERVIES (`FrameworkAnswerServie` — l'axe actualité
recalculé par `frameworks.servir_answer`, jamais la ligne stockée telle quelle) et rend une mesure
PAR (framework, version). Aucune IO, aucun appel de modèle, aucune écriture : la mesure se recalcule
à chaque lecture, exactement comme l'actualité dont elle dépend. La stocker figerait un verdict
d'avant le prochain événement matériel — la cause n°2 du diagnostic #50.

Le SERVICE (réponse → réponse servie) appartient à `frameworks.servir_answer`, qui seul connaît
l'ancre matérielle. Ce module reçoit le résultat de ce service : il reste pur, donc rejouable
hors-ligne et sans dépense — la frontière gratuite du lot.

CE QUE LA RÈGLE DIT (les quatre arbitrages du fonds, contrat `qualite_info_schema`)
-----------------------------------------------------------------------------------
  · `sans_objet` → HORS base (compté à part). La qualité ne mesure que les questions applicables.
  · `repondu` et `approxime` → même crédit de STATUT (1.0). La moindre qualité d'une approximation
    est portée par son rang (cran A → A−), pas par une 2ᵉ décote au statut (#46).
  · le crédit est ensuite MODULÉ par l'actualité : `courante` ×1.0, `perimee`/`indeterminable` ×0.0
    (`FACTEUR_ACTUALITE`, détenteur unique). Une réponse périmée ne fonde pas la décision du jour.
  · `non_fondable` → crédit 0, DANS la base (c'est un trou, pas une exclusion).
  · le rang moyen des réponses fondées est PUBLIÉ à côté du score, jamais fondu dedans (#50).

DEUX ANALYSTES = DEUX POINTS, JAMAIS UNE MOYENNE (§3.4)
------------------------------------------------------
Comme le projecteur (#50, cause n°1), on ne moyenne jamais deux réponses. Si deux analystes ont
répondu à la même question, chaque réponse est un point de la base. La base compte des RÉPONSES
courantes, pas des questions distinctes.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Optional, Sequence, get_args

from app.contracts.analysis_v2_schemas import Tier
from app.contracts.framework_answer_schema import FrameworkAnswerServie
from app.contracts.qualite_info_schema import FACTEUR_ACTUALITE, QualiteInfo

__all__ = ["derive_qualite_info", "rang_moyen_de", "servir_qualite_info"]


# Le vocabulaire ORDONNÉ des tiers, du meilleur (index 0 = "A") au plus faible (index 6 = "C").
# C'est le `Tier` Literal lui-même qui EST cet ordre — on le lit par `get_args`, on ne recopie pas
# une seconde liste qui divergerait au premier tier ajouté (#46).
TIERS_ORDONNES: tuple[str, ...] = get_args(Tier)


def rang_moyen_de(rangs: Sequence[str]) -> Optional[str]:
    """Le rang MOYEN d'un ensemble de réponses fondées, rendu comme une étiquette de tier.

    La moyenne se fait sur la POSITION dans le vocabulaire ordonné (A=0 … C=6), puis on revient à
    l'étiquette la plus proche (arrondi au demi supérieur, déterministe — `round()` de Python
    arrondit 0,5 vers le pair, ce qui ferait dépendre le résultat de la parité de l'index). Moyenner
    des positions plutôt que des scores évite d'introduire une table tier → nombre qui divergerait de
    `RELIABILITY_TABLE` (#46) : ici on ne convertit jamais en [0,1], on reste dans le vocabulaire.

    `None` quand il n'y a aucune réponse fondée : un rang moyen sur zéro ligne serait un faux.
    """
    if not rangs:
        return None
    positions = [TIERS_ORDONNES.index(r) for r in rangs]
    moyenne = sum(positions) / len(positions)
    idx = int(moyenne + 0.5)                     # demi supérieur, déterministe
    idx = min(idx, len(TIERS_ORDONNES) - 1)
    return TIERS_ORDONNES[idx]


def derive_qualite_info(answers: Sequence[FrameworkAnswerServie]) -> list[QualiteInfo]:
    """Mesure la qualité d'information, une `QualiteInfo` par (framework_id, framework_version).

    L'entrée est un ensemble de réponses SERVIES (actualité recalculée). Le regroupement par
    (framework, version) est fait ici : deux dossiers de versions différentes ne se comparent pas au
    niveau 3 (écart V9), donc ils ne se mêlent jamais dans une même mesure.
    """
    groupes: dict[tuple[str, str], list[FrameworkAnswerServie]] = defaultdict(list)
    for a in answers:
        groupes[(a.framework_id, a.framework_version)].append(a)

    mesures: list[QualiteInfo] = []
    for (framework_id, framework_version), reponses in sorted(groupes.items()):
        n = {"repondu": 0, "approxime": 0, "non_fondable": 0, "sans_objet": 0}
        actualite = {"courante": 0, "perimee": 0, "indeterminable": 0}
        credit_total = 0.0
        rangs: list[str] = []

        for a in reponses:
            n[a.statut] += 1
            if a.statut == "non_fondable":
                # dans la base, crédit nul, pas d'axe actualité (aucune fondation).
                continue
            if a.statut == "sans_objet":
                # hors base : ni crédit, ni actualité, ni rang.
                continue
            # repondu | approxime : fondés, donc datés et notés.
            act = a.fondation.actualite
            actualite[act] += 1
            credit_total += FACTEUR_ACTUALITE[act]          # statut ×1.0, modulé par l'actualité
            rangs.append(a.fondation.rang_derive)

        base = n["repondu"] + n["approxime"] + n["non_fondable"]
        if base == 0:
            etat = "aucune_question_applicable"
            score = None
        else:
            etat = "mesure"
            score = round(credit_total / base, 4)

        mesures.append(QualiteInfo(
            framework_id=framework_id,
            framework_version=framework_version,
            etat=etat,
            score=score,
            n_repondu=n["repondu"],
            n_approxime=n["approxime"],
            n_non_fondable=n["non_fondable"],
            n_sans_objet=n["sans_objet"],
            base=base,
            n_courante=actualite["courante"],
            n_perimee=actualite["perimee"],
            n_indeterminable=actualite["indeterminable"],
            rang_moyen=rang_moyen_de(rangs),
        ))
    return mesures


async def servir_qualite_info(conn, ticker_id: str) -> list[QualiteInfo]:
    """LE POINT DE LECTURE de la mesure : base → réponses SERVIES (actualité recalculée) → dérivation.

    N'écrit rien. DÉTENTEUR UNIQUE de l'assemblage (#46) : l'outil `montrer_qualite_info`, le futur
    endpoint du niveau 1 et toute lecture passent par ici. Trois assembleurs, ce serait trois façons
    de rater `servir_answer()` — et la mesure sortirait alors sur l'axe actualité d'avant le dernier
    événement matériel (#53/#54), c'est-à-dire en surévaluant systématiquement une réponse périmée.

    Même plomberie que `projection_memo.servir_memo` (dont ce module est le voisin) : lecture des
    réponses courantes à la version de référence, chargement du seul `source_date` des entries citées
    (l'actualité s'en date), ancre matérielle, service, dérivation.
    """
    # Imports tardifs : ce module est importé par un check sans base ni réseau. En tête, ils
    # tireraient asyncpg et le client EDGAR pour une dérivation qui est purement en mémoire.
    from app.agents.v2.frameworks import load_frameworks, servir_answer
    from app.agents.v2.framework_persist import read_answers_courantes
    from app.knowledge.material_events import material_anchor_for_ticker

    fichier = load_frameworks()
    brutes = await read_answers_courantes(
        conn, ticker_id=ticker_id, framework_version=fichier.schema_version)

    cites: set[int] = set()
    for _id, a in brutes:
        if a.fondation is not None:
            cites.update(a.fondation.cited_entry_ids)

    entries: dict[int, dict] = {}
    if cites:
        rows = await conn.fetch(
            "SELECT id, source_date, reliability_tier FROM knowledge_entries "
            "WHERE id = ANY($1::int[])",
            sorted(cites))
        entries = {r["id"]: {"source_date": r["source_date"],
                             "reliability_tier": r["reliability_tier"]} for r in rows}

    ancre = await material_anchor_for_ticker(conn, ticker_id)
    servies = [servir_answer(a, ancre=ancre, entries=entries) for _id, a in brutes]
    return derive_qualite_info(servies)
