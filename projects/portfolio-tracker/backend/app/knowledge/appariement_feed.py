"""Le PRODUCTEUR de faits APPARIÉS — exécuter une formule sur les concepts déposés (maillon 4, #72).

CE QU'IL DÉBLOQUE, ET CE QUE LA MESURE DISAIT
----------------------------------------------
Au 2026-09-18, la carte d'appariement faisait passer le routage de 0 à 9 lignes vers EDGAR sur RVMD,
et **0 de ces 9 n'était exécutable**. `_SocleEdgar` ne sait collecter que les 33 RECETTES du
catalogue `POSTES` (un poste = un nom interne, des concepts candidats, une préférence de fraîcheur),
là où une `approximation` est une **FORMULE sur des concepts XBRL nus**. Les 9 repartaient au web par
le repli nommé de `collecter_un` — chercher chez un tiers, en tier B, un nombre dont tous les termes
étaient déposés en tier A. La décision avait changé, la collecte pas encore.

Ce module est la collecte. Il prend un appariement (une expression, ses concepts, ses hypothèses,
son déterminisme), l'inventaire DÉJÀ LU (`fetch_company_facts`, aucun appel réseau de plus), et
produit un fait : la valeur, sa provenance concept par concept, et son tier DÉRIVÉ.

⚠️ LE CHIFFRE À SUIVRE EST « LIGNES COLLECTÉES DEPUIS LE DÉPÔT », JAMAIS « LIGNES ROUTÉES VERS
EDGAR ». C'est la faute que #71 a corrigée une fois, et elle se re-commet en changeant de niveau :
router n'est pas collecter, et exécuter une formule n'est pas non plus la collecter si l'ancre
commune manque. Chaque refus ci-dessous est donc NOMMÉ et devient un mandat motivé (#25), jamais un
silence ni un nombre approximatif.

LES QUATRE REFUS, ET POURQUOI CHACUN EST UN REFUS PLUTÔT QU'UNE TOLÉRANCE
-------------------------------------------------------------------------
  1. **un terme du calcul manque au dépôt** (`termes_web` non vide) — l'apparieur a lui-même déclaré
     qu'il manque un ingrédient. Exécuter quand même produirait un nombre AMPUTÉ de ce qu'il a nommé
     comme manquant, et ce nombre porterait le tier de ses termes déposés. La ligne part au web
     chercher le terme, ce qui est exactement le rôle du web tranché en #67 ;
  2. **aucune ancre commune** — les concepts n'ont pas de date où tous sont publiés (±20 j). Prendre
     `Assets` au 2026-06-30 et `LiabilitiesCurrent` au 2025-12-31 donne une soustraction dont les
     deux termes sont justes et dont le résultat ne décrit aucun instant (#43, « tous les nombres
     justes, le fait faux ») ;
  3. **dimensions incohérentes** — une somme de `USD` et de `shares`. Le contrôle vit sur l'ARBRE
     (`formule_grammaire.dimension_formule`) et non sur la liste des concepts, parce qu'un ratio
     `USD / shares` est légitime là où la somme ne l'est pas : le discriminant est l'opérateur ;
  4. **division par zéro** — le dénominateur vaut 0 chez cet émetteur (une biotech sans chiffre
     d'affaires). C'est une information sur l'entreprise, pas une panne : le ratio n'existe pas pour
     elle, et le publier en `inf` ou en 0 dirait le contraire.

CE QUE L'ENTRY NE PORTE PAS, ET C'EST STRUCTUREL (principe 2)
---------------------------------------------------------------
Aucun `question_id`, aucun `ingredient_id`, aucun `framework_id`. Ce module ne les REÇOIT pas : son
entrée est une `ConsigneAppariement`, aussi aveugle qu'une `LigneAveugle` — une expression en
us-gaap, des hypothèses, un booléen. Le plan comptable américain n'est pas du vocabulaire de
framework (c'est le statut déjà acquis de `metrique` et de `poste`, #58), et la couverture reste
écrite par l'aiguilleur, qui SAIT. Le principe « l'entry ne nomme aucun framework » demeure donc une
conséquence du flux, pas une discipline d'écriture.

LE TIER SE DÉRIVE, ET LES DEUX CAS NE SONT PAS LE MÊME
--------------------------------------------------------
  · `exact` — un concept déposé, recopié. Ce n'est PAS un calcul : le tier est celui de la source
    (`edgar_official`, tier A), par le chemin normal de `store_knowledge`. Y faire passer
    `derive_tier_calcul` lui ferait « hériter du plus faible de ses ingrédients » alors qu'il n'a pas
    d'ingrédient — un calcul à un terme n'est pas un calcul ;
  · `approximation` — `derive_tier_calcul(ingredients, deterministe=…)` (#67/#68). Les ingrédients
    sont les concepts déposés, tous `edgar_official`, donc leur tier est lu dans `RELIABILITY_TABLE`
    et jamais écrit ici (#46). Déterministe → tier A sans cran ; non déterministe → un cran sous.

⚠️ **AUCUN SCORE N'EST ÉCRIT DANS CE MODULE.** Le seul (tier, score) qui y apparaît est LU dans
`RELIABILITY_TABLE`, et le cran est celui de `derive_synthesis_reliability`, appelé par
`derive_tier_calcul`. Une troisième table aurait divergé des deux autres au premier ajustement.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, NamedTuple, Optional

import asyncpg

from app.contracts.formule_grammaire import (
    DimensionIncoherente,
    FormuleInexecutable,
    dimension_formule,
    evaluer_formule,
    noms_de_la_formule,
    references_de_la_formule,
    rendre_dimension,
)
from app.knowledge.edgar_facts import (
    duree_jours,
    point_pour_periode,
    points_annuels,
    points_instantanes,
)
# L'identité d'un fait EDGAR — quelle entrée courante un nouveau fait remplace — est une règle
# UNIQUE, tenue par `edgar_feed` (clé par `metric` seul pour un stock, `metric`+`end` pour un flux).
# `financials_feed` l'importe déjà pour la même raison : deux appariements du même fait sous deux
# jeux de tags feraient répondre deux choses à la même question.
from app.knowledge.edgar_feed import _current_fact_ids, filing_url, is_annual_flow
from app.knowledge.service import RELIABILITY_TABLE, store_knowledge
from app.knowledge.synthesis_feed import derive_tier_calcul
from app.knowledge.units import montant

logger = logging.getLogger(__name__)

__all__ = [
    "AppariementInexecutable",
    "ConsigneAppariement",
    "PointRetenu",
    "FaitApparie",
    "TOLERANCE_ANCRE_J",
    "SOURCE_TYPE",
    "serie_du_concept",
    "rendre_resultat",
    "ancre_commune",
    "resoudre_points",
    "construire_fait_apparie",
    "executer_appariement",
]

# La provenance d'un fait calculé sur des concepts déposés est EDGAR — même raisonnement que
# `financials_feed` : aucun intrant non-EDGAR n'entre. Le TIER, lui, ne vient pas de là quand le
# calcul est non déterministe : il est passé en `derived_reliability` (cf. l'en-tête).
SOURCE_TYPE = "edgar_official"

# La même tolérance que `point_pour_periode` / `collect_postes` : un exercice fiscal ne tombe pas au
# jour près d'une année sur l'autre, et deux postes d'un même bilan peuvent être datés à quelques
# jours d'écart selon le dépôt qui les porte. Nommée ici pour être lisible dans un motif de refus.
TOLERANCE_ANCRE_J = 20

_TAGS = ["financials", "edgar", "appariement"]


class AppariementInexecutable(Exception):
    """Ce calcul-ci ne se fait pas, et le motif le DIT. Devient un `echec` de collecte, donc un
    mandat motivé (#25) — jamais un nombre approché, jamais un silence, jamais un zéro."""


class ConsigneAppariement(NamedTuple):
    """Ce que le producteur voit d'un appariement — et RIEN d'autre.

    Le pendant de `LigneAveugle` pour la carte : `question_id` et `ingredient_id` n'y sont PAS, donc
    le fait produit ne peut pas porter de vocabulaire de framework. C'est le même geste que #58, au
    même endroit du flux : l'aveuglement est une propriété du type, pas une règle d'écriture.

    `expression` est l'unité de calcul : la `formule` d'une `approximation`, ou le concept nu d'un
    `exact` (qui est une expression à un terme — la grammaire l'admet tel quel, et cela évite une
    seconde branche d'évaluation dont la seule différence serait de ne rien calculer).
    """
    statut: str                       # "exact" | "approximation"
    expression: str
    hypotheses: tuple[str, ...] = ()
    deterministe: Optional[bool] = None
    termes_web: tuple[str, ...] = ()


class PointRetenu(NamedTuple):
    """UNE référence (concept, offset d'exercice), résolue à sa date : sa valeur et de quel dépôt
    elle sort. Ce qui rend la provenance CONTESTABLE plutôt que promise — `accn` identifie le dépôt,
    `end` la date. `offset` (0 = exercice le plus récent, -1 = précédent) rend LISIBLE, dans la
    provenance, à quelle période chaque terme a été lu : une croissance annuelle lit `Revenues` à
    deux exercices, et le lecteur doit voir lequel est lequel."""
    concept: str
    valeur: float
    unite: str
    end: str
    cadrage: str                      # "flux" | "instant"
    duree_jours: Optional[int]
    form: Optional[str]
    accn: Optional[str]
    offset: int = 0


class FaitApparie(NamedTuple):
    """La spec de l'entry à écrire. Pure : construite hors de toute IO, donc rejouable hors-ligne et
    imprimable EN TEXTE avant la première écriture (`feedback_frontiere_gratuite...`)."""
    metric: str
    titre: str
    contenu: str
    structure: dict[str, Any]
    tags: list[str]
    source_url: Optional[str]
    source_date: date
    fiscal_period: str
    flux: bool
    fiabilite: Optional[tuple[float, str, str]]


# ─────────────────────────────── la partie PURE (hors réseau, hors DB) ───────────────────────────

def _ref_libelle(p: PointRetenu) -> str:
    """`Concept` (offset 0) ou `Concept[-1]` : la provenance nomme la PÉRIODE de chaque terme, pour
    qu'une croissance annuelle ne présente pas deux lectures du même concept comme interchangeables."""
    return p.concept if p.offset == 0 else f"{p.concept}[{p.offset}]"


def rendre_resultat(valeur: float, dimension: tuple, devise: str) -> str:
    """Le RÉSULTAT du calcul, rendu pour être LU dans le contenu. Pur.

    `montant` arrondit à l'entier tout ce qui est sous le million — sa mantisse `nd` ne s'applique
    qu'aux paliers M/Md. Juste pour un poste de bilan, c'est FAUX pour un ratio SANS DIMENSION : une
    croissance de 0,25 (25 %) y deviendrait « 0 », un fait dont le nombre structuré est juste et dont
    le contenu ment (#42/#45 — le contenu est ce que l'agent lit). Le temporel produit précisément ce
    genre de fait (une croissance est un flux ÷ un flux, donc sans dimension), donc un résultat sans
    dimension est rendu à chiffres significatifs, jamais via `montant`. Un résultat dimensionné (un
    montant, un `USD/shares`) reste rendu par `montant`, détenteur unique du format des montants (#46).
    """
    if not dimension:
        return f"{valeur:.4g}".replace(".", ",")
    return montant(valeur, devise, nd=2)


def serie_du_concept(
    bruts: list[dict[str, Any]], concept: str
) -> tuple[list[dict[str, Any]], str, str]:
    """Les points exploitables d'un concept : (série, unité retenue, cadrage). Pur.

    DEUX choix déterministes, et chacun garde un mode de panne :

      · L'UNITÉ. Un concept peut être déposé sous plusieurs unités (`USD` et `USD/shares` pour un
        résultat, `shares` et `pure` pour un décompte). On retient celle dont la série va le PLUS
        LOIN dans le temps, puis la plus fournie, puis l'ordre alphabétique — trois critères, donc
        un résultat qui ne dépend pas de l'ordre d'itération d'un dict. Choisir « la première
        rencontrée » aurait rendu le fait non reproductible d'un run à l'autre, dans le module même
        qui décide de ce qui est déterministe.
      · LE CADRAGE. Un concept qui porte des points ANNUELS est lu comme un flux ; sinon comme un
        instant. L'ordre n'est pas un goût : un flux mal lu comme un instant ramène un trimestre à
        la place d'un exercice et divise le nombre par ~4 sans erreur visible (`is_annual_flow`).

    Lève `AppariementInexecutable` si le concept est déposé mais n'a aucun point exploitable — le
    cas du concept ABANDONNÉ, que l'inventaire affiche encore et que [V] laisse passer.
    """
    par_unite: dict[str, list[dict[str, Any]]] = {}
    for p in bruts or []:
        if p.get("end") is None or p.get("val") is None:
            continue
        par_unite.setdefault(str(p.get("unit")), []).append(p)
    if not par_unite:
        raise AppariementInexecutable(
            f"`{concept}` est déposé mais ne porte aucun point daté et chiffré : il est NOMMABLE "
            "(donc [V] l'accepte) et illisible. C'est la signature d'une étiquette abandonnée")

    def rang(item: tuple[str, list[dict[str, Any]]]) -> tuple[str, int, str]:
        unite, pts = item
        return (max(str(p["end"]) for p in pts), len(pts), unite)

    unite, pts = max(par_unite.items(), key=rang)
    annuels = points_annuels(pts)
    if annuels:
        return annuels, unite, "flux"
    instants = points_instantanes(pts)
    if instants:
        return instants, unite, "instant"
    raise AppariementInexecutable(
        f"`{concept}` ({unite}) ne porte ni exercice annuel complet ni point de bilan : ses points "
        "sont des fractions d'exercice. Les employer tels quels ferait passer un trimestre pour un "
        "exercice, sans erreur visible")


def ancre_commune(series: dict[str, list[dict[str, Any]]]) -> Optional[str]:
    """La date la PLUS RÉCENTE à laquelle TOUS les concepts ont un point (±`TOLERANCE_ANCRE_J`). Pure.

    Pourquoi une ancre COMMUNE, et pas « le dernier point de chacun » : la seconde option rend un
    nombre dont chaque terme est juste et dont le tout ne décrit aucun instant. Sur un bilan, elle
    soustrairait des dettes de décembre à des actifs de juin ; l'écart ne se verrait nulle part —
    l'entry resterait tier A, exacte poste par poste, et fausse (#43).

    Les CANDIDATES sont les dates réellement déposées, parcourues de la plus récente à la plus
    ancienne : on ne fabrique aucune date, on choisit parmi celles qui existent. Rendre None est un
    résultat, pas un échec technique — l'appelant en fait un refus NOMMÉ.
    """
    if not series:
        return None
    candidates = sorted({str(p["end"]) for pts in series.values() for p in pts}, reverse=True)
    for candidate in candidates:
        try:
            cible = date.fromisoformat(candidate)
        except ValueError:
            continue
        if all(point_pour_periode(pts, cible, tol_days=TOLERANCE_ANCRE_J) is not None
               for pts in series.values()):
            return candidate
    return None


def _decaler_annees(iso: str, k: int) -> date:
    """La date `iso` décalée de `k` années (k <= 0), même mois et même jour. Pure.

    Le décalage garde le mois/jour plutôt que de retrancher `k×365` jours : un exercice fiscal tombe
    au même mois d'une année sur l'autre, et soustraire des jours accumulerait une dérive sur les
    décalages profonds (`[-5]`). Le 29 février d'une année non bissextile retombe sur le 28 — un
    exercice clos un 29 février est assez rare pour que le 28 soit le bon rattrapage, et
    `point_pour_periode` absorbe l'écart d'un jour dans sa tolérance.
    """
    d = date.fromisoformat(iso)
    try:
        return d.replace(year=d.year + k)
    except ValueError:
        return d.replace(year=d.year + k, day=28)


def resoudre_points(
    consigne: ConsigneAppariement, facts: dict[str, list[dict[str, Any]]]
) -> tuple[dict[tuple[str, int], PointRetenu], Optional[str], Optional[str]]:
    """Résout chaque RÉFÉRENCE (concept, offset d'exercice) de l'expression. Pur.

    Rend (points, ancre_flux, ancre_bilan). Deux ancres de BASE (offset 0), jamais une : un flux
    appartient à un exercice, un poste de bilan date d'un instant, et les confondre est le défaut de
    sens que `collect_postes` documente. Une formule peut légitimement mêler les deux (une intensité
    = un flux rapporté à un solde) ; elle porte alors ses DEUX dates, et l'entry les écrit toutes
    deux plutôt que d'en supposer une.

    LE TEMPOREL : une référence `Concept[-k]` est résolue à l'exercice ~k an(s) avant l'ancre de base
    de son cadrage (`_decaler_annees` + `point_pour_periode`). Le fait reste daté de l'ancre de base
    (la période la plus RÉCENTE) — une croissance annuelle est affirmable « au dernier exercice » ;
    les exercices antérieurs sont sa PROVENANCE, pas sa date. Un exercice décalé absent est un refus
    NOMMÉ (l'émetteur manque d'historique), jamais un zéro ni un repli sur le point courant.

    Lève `AppariementInexecutable` avec un motif LISIBLE — il finira dans un mandat, donc il doit
    dire ce qui manque, pas qu'il manque quelque chose.
    """
    if consigne.termes_web:
        raise AppariementInexecutable(
            f"le calcul déclare {len(consigne.termes_web)} terme(s) absent(s) du dépôt "
            f"({', '.join(consigne.termes_web)}) : l'apparieur a lui-même nommé ce qui manque. "
            "L'exécuter sur les seuls concepts déposés produirait un nombre AMPUTÉ de ce terme-là, "
            "et ce nombre porterait le tier de ses termes déposés (#67 : le web apporte un terme du "
            "calcul, il ne comble pas un calcul incomplet)")

    try:
        references = sorted(references_de_la_formule(consigne.expression))
    except FormuleInexecutable as e:
        # Le contrat `AppariementItem` valide déjà la FORME de la formule à la construction, donc ce
        # chemin est théoriquement mort au flux nominal. Mais le producteur est sur la chaîne de
        # collecte : une formule qui l'atteindrait mal formée (carte hors contrat, appel direct) doit
        # devenir un mandat NOMMÉ (#25), jamais une exception nue qui casserait toute la collecte.
        raise AppariementInexecutable(f"formule mal formée — {e}") from e
    concepts = sorted({c for c, _ in references})
    if not concepts:
        raise AppariementInexecutable(
            f"« {consigne.expression} » ne référence aucun concept : il n'y a rien à lire au dépôt")

    series: dict[str, list[dict[str, Any]]] = {}
    unites: dict[str, str] = {}
    cadrages: dict[str, str] = {}
    for concept in concepts:
        if concept not in facts:
            # [V] l'a vérifié À LA PRODUCTION de la carte ; ici on est au point de LECTURE, et une
            # carte persistée peut avoir survécu à un changement d'inventaire. Le contrôle se refait
            # là où il est employé (`feedback_controle_au_point_de_lecture`).
            raise AppariementInexecutable(
                f"`{concept}` n'est pas (ou plus) déposé par cet émetteur : la carte a été établie "
                f"contre un inventaire qui le portait")
        series[concept], unites[concept], cadrages[concept] = serie_du_concept(
            facts[concept], concept)

    ancres: dict[str, Optional[str]] = {}
    for cadrage in ("flux", "instant"):
        sous = {c: s for c, s in series.items() if cadrages[c] == cadrage}
        if not sous:
            ancres[cadrage] = None
            continue
        ancre = ancre_commune(sous)
        if ancre is None:
            derniers = ", ".join(
                f"{c} → {max(str(p['end']) for p in s)}" for c, s in sorted(sous.items()))
            raise AppariementInexecutable(
                f"aucune date où les {len(sous)} concept(s) de cadrage « {cadrage} » soient TOUS "
                f"publiés à ±{TOLERANCE_ANCRE_J} j (derniers points : {derniers}). Les prendre à "
                "deux dates différentes ferait un calcul dont chaque terme est juste et dont le "
                "résultat ne décrit aucune période (#43)")
        ancres[cadrage] = ancre

    points: dict[tuple[str, int], PointRetenu] = {}
    for concept, offset in references:
        base = ancres[cadrages[concept]]
        assert base is not None  # garanti ci-dessus : un cadrage présent a une ancre de base
        cible = _decaler_annees(base, offset)
        p = point_pour_periode(series[concept], cible, tol_days=TOLERANCE_ANCRE_J)
        if p is None:
            # L'exercice décalé n'est pas déposé : refus NOMMÉ, jamais un zéro ni un repli sur le
            # point courant (qui ferait une croissance de 0 %, un fait faux et rassurant). C'est un
            # émetteur qui manque d'historique — une propriété de l'émetteur, donc un mandat (#25/#44).
            dispo = ", ".join(str(pt["end"]) for pt in series[concept][-5:])
            raise AppariementInexecutable(
                f"`{concept}[{offset}]` demande l'exercice ~{-offset} an(s) avant {base} "
                f"(cible {cible.isoformat()} ±{TOLERANCE_ANCRE_J} j), que cet émetteur n'a pas "
                f"déposé (exercices lisibles : {dispo}). L'historique lui manque — c'est une "
                "propriété de l'émetteur, pas un trou de collecte")
        points[(concept, offset)] = PointRetenu(
            concept=concept, offset=offset, valeur=float(p["val"]), unite=unites[concept],
            end=str(p["end"]), cadrage=cadrages[concept], duree_jours=duree_jours(p),
            form=p.get("form"), accn=p.get("accn"))
    return points, ancres["flux"], ancres["instant"]


def _fiabilite(consigne: ConsigneAppariement, points: dict[str, PointRetenu]
               ) -> Optional[tuple[float, str, str]]:
    """Le (score, tier, note) d'une `approximation` — None pour un `exact`, qui n'est pas un calcul.

    None n'est PAS un défaut de dérivation : c'est l'aiguillage vers `compute_reliability`, qui
    scorera le fait par sa source (`edgar_official`, tier A) comme n'importe quel relevé EDGAR. Un
    `exact` passé par `derive_tier_calcul` hériterait « du plus faible de ses ingrédients » alors
    qu'il n'a qu'un terme, et la note publierait un raisonnement de calcul sur une recopie.
    """
    if consigne.statut != "approximation":
        return None
    tier_a = RELIABILITY_TABLE[SOURCE_TYPE]                       # LU, jamais écrit ici (#46)
    ingredients = [tier_a for _ in points]
    return derive_tier_calcul(ingredients, deterministe=bool(consigne.deterministe))


def construire_fait_apparie(
    ticker_id: str,
    symbole: str,
    cik: int,
    libelle: str,
    consigne: ConsigneAppariement,
    points: dict[str, PointRetenu],
    *,
    ancre_flux: Optional[str],
    ancre_bilan: Optional[str],
) -> FaitApparie:
    """L'expression ÉVALUÉE, et le fait qui en sort. Pur : aucune IO, aucun appel modèle.

    `libelle` est la métrique de la ligne AVEUGLE (« capital employé »), du vocabulaire du plan et
    non du framework — le même statut que celui qui traverse déjà vers le search-worker (#58).

    Le `metric` du `content_structured` est l'EXPRESSION elle-même, et ce choix porte l'identité du
    fait : deux exécutions de la même formule à la même ancre écrivent le même `metric`, donc la
    seconde SUPERSÈDE la première (`_current_fact_ids`) au lieu de la doubler. Le nommer d'après
    l'ingrédient aurait inscrit du vocabulaire de framework sur le corpus — ce que #57 a retiré.
    """
    unites = {p.concept: p.unite for p in points.values()}     # keyé par concept (l'unité ignore l'offset)
    try:
        dimension = dimension_formule(consigne.expression, unites)
        valeur = evaluer_formule(consigne.expression, {cle: p.valeur for cle, p in points.items()})
    except DimensionIncoherente as e:
        raise AppariementInexecutable(f"unités incohérentes — {e}") from e
    except FormuleInexecutable as e:
        raise AppariementInexecutable(f"formule non calculable sur le dépôt — {e}") from e

    devise = rendre_dimension(dimension)
    # Un cadrage MIXTE porte ses deux dates ; sinon la seule qui existe. La date de l'entry
    # (`source_date`) est la PLUS RÉCENTE des deux : c'est l'instant à partir duquel le fait est
    # affirmable, et la dater de la plus ancienne le ferait vieillir d'un exercice le jour de son
    # écriture (l'axe actualité se calcule à la lecture, encore faut-il ne pas lui mentir en amont).
    dates = [d for d in (ancre_flux, ancre_bilan) if d]
    ancre_fait = max(dates)
    flux = ancre_bilan is None                    # aucun poste de bilan → le fait est un flux pur
    if ancre_flux and ancre_bilan:
        periode = f"FLUX {ancre_flux} + BILAN {ancre_bilan}"
    elif ancre_flux:
        periode = f"EXERCICE CLOS LE {ancre_flux}"
    else:
        periode = f"AU {ancre_bilan}"

    fiabilite = _fiabilite(consigne, points)
    detail = "\n".join(
        f"  · {_ref_libelle(p)} = {montant(p.valeur, p.unite, nd=2)} "
        f"({'flux' if p.cadrage == 'flux' else 'bilan'} {p.end}"
        + (f", {p.duree_jours} j" if p.duree_jours else "")
        + f", {p.form or 'forme inconnue'}, accession {p.accn or 'n/d'})"
        for p in sorted(points.values(), key=lambda q: (q.concept, q.offset)))
    hypotheses = ("\nHypothèses, à contester : "
                  + " ; ".join(consigne.hypotheses)) if consigne.hypotheses else ""
    if consigne.statut == "approximation":
        qualif = (f"\n⚠️ Calcul {'DÉTERMINISTE' if consigne.deterministe else 'NON DÉTERMINISTE'} "
                  f"sur {len(points)} concept(s) déposé(s). {fiabilite[2] if fiabilite else ''}")
    else:
        qualif = "\nRelevé EXACT : le concept déposé est recopié tel quel, sans transformation."

    contenu = (
        f"{libelle} — {ticker_id} ({symbole}), {periode} : "
        f"{rendre_resultat(valeur, dimension, devise)}.\n"
        f"Calculé depuis les dépôts SEC. Expression : {consigne.expression}\n{detail}"
        f"{hypotheses}{qualif}"
    )
    structure: dict[str, Any] = {
        "metric": consigne.expression,
        "value": valeur,
        "currency": devise,
        "period": periode,
        "period_end": ancre_fait,
        "poste_kind": "flow" if flux else "stock",
        "appariement_statut": consigne.statut,
        "deterministe": consigne.deterministe,
        "hypotheses": list(consigne.hypotheses),
        "ancre_flux": ancre_flux,
        "ancre_bilan": ancre_bilan,
        "ingredients": [
            {"concept": p.concept, "offset": p.offset, "xbrl_tag": f"us-gaap:{p.concept}",
             "value": p.valeur, "unit": p.unite, "end": p.end, "cadrage": p.cadrage,
             "form": p.form, "accn": p.accn}
            for p in sorted(points.values(), key=lambda q: (q.concept, q.offset))
        ],
    }
    # L'URL pointe le dépôt du point le plus récent : c'est celui qu'un lecteur ouvrira pour
    # contester le nombre, et les autres accessions restent lisibles dans `ingredients`.
    plus_recent = max(points.values(), key=lambda p: (p.end, p.concept, p.offset))
    return FaitApparie(
        metric=consigne.expression,
        titre=f"{libelle} — {periode} ({symbole})",
        contenu=contenu,
        structure=structure,
        tags=list(_TAGS),
        source_url=filing_url(cik, plus_recent.accn),
        source_date=date.fromisoformat(ancre_fait),
        fiscal_period=periode,
        flux=flux,
        fiabilite=fiabilite,
    )


# ─────────────────────────────────────── la couche IO ────────────────────────────────────────────

async def executer_appariement(
    conn: asyncpg.Connection,
    *,
    ticker_id: str,
    symbole: str,
    cik: int,
    libelle: str,
    consigne: ConsigneAppariement,
    facts: dict[str, list[dict[str, Any]]],
) -> int:
    """Exécute UN appariement contre l'inventaire déjà lu et écrit l'entry. Rend son `id`.

    AUCUN APPEL RÉSEAU : `facts` arrive de `assurer_carte`, qui l'a lu une fois pour tout le plan.
    C'est ce qui rend ce producteur gratuit à l'exécution — la dépense a déjà eu lieu, et la refaire
    par ligne serait un appel `companyfacts` (1 à 5 Mo) par ingrédient.

    Lève `AppariementInexecutable` (motif nommé) sur les quatre refus de l'en-tête. L'appelant en
    fait un `echec`, donc un mandat — jamais un nombre approché.
    """
    points, ancre_flux, ancre_bilan = resoudre_points(consigne, facts)
    fait = construire_fait_apparie(
        ticker_id, symbole, cik, libelle, consigne, points,
        ancre_flux=ancre_flux, ancre_bilan=ancre_bilan)

    prevs = await _current_fact_ids(
        conn, ticker_id, fait.metric, fait.structure["period_end"], flow=fait.flux)
    stored = await store_knowledge(
        conn, ticker_id=ticker_id, entry_type="fact_financial", content=fait.contenu,
        source_type=SOURCE_TYPE, title=fait.titre, content_structured=fait.structure,
        tags=fait.tags, lang="fr", source_url=fait.source_url, source_date=fait.source_date,
        fiscal_period=fait.fiscal_period, supersedes_entry_id=prevs[0] if prevs else None,
        derived_reliability=fait.fiabilite,
    )
    # Même geste que `run_edgar_feed` : `store_knowledge` ne referme que la lignée de version.
    # Les autres entrées courantes du même `metric` — laissées orphelines par un changement
    # d'ancre — sont retirées ici, sans quoi le corpus répondrait deux choses à la même question.
    if len(prevs) > 1:
        await conn.execute(
            "UPDATE knowledge_entries SET superseded_by = $1 WHERE id = ANY($2::int[])",
            stored["id"], prevs[1:])
    logger.info(
        "appariement exécuté %s « %s » → entry #%d (%s, %d concept(s), ancres flux=%s bilan=%s, "
        "tier %s)", ticker_id, consigne.expression, stored["id"], consigne.statut, len(points),
        ancre_flux, ancre_bilan, fait.fiabilite[1] if fait.fiabilite else "A (source)")
    return int(stored["id"])
