"""
Helpers partagés des agents V2 de la chaîne d'analyse (curator / research / bull / bear / synthèse).

Regroupe : la spec MVDD (dimension → champs factuels requis → tier plancher, dérivée de
readiness_derivation.md §), le formatage DÉTERMINISTE des knowledge_entries pour l'insertion en tête
de prompt (discipline de cache §5.3 : tri stable, aucun champ volatil), et le comptage par tier.
"""
from __future__ import annotations

from typing import Any, Optional, Sequence

# ── Spec MVDD (readiness_derivation.md) — guidage injecté au curator ──────────
# Chaque dimension : (bloc, champs factuels requis fondables, tier plancher). Ce sont les MÊMES noms
# de dimension que readiness_report_schema (_DIMS_STRUCTUREE / _DIMS_QUALITATIVE) et context_pack
# (CANONICAL_DIMS). L'agent affine les champs_requis/tier au cas d'espèce ; ceci borne le cadre.
MVDD_SPEC: list[dict[str, Any]] = [
    {"bloc": "structuree", "dimension": "business_model",
     "champs_requis": ["description", "drivers_revenus", "recurrence_pct"], "tier_plancher": "B+"},
    {"bloc": "structuree", "dimension": "financials",
     "champs_requis": ["roic_pct", "fcf_conversion_pct", "intensite_capex_pct", "levier"],
     "tier_plancher": "A"},
    {"bloc": "structuree", "dimension": "valorisation",
     "champs_requis": ["prix_actuel", "relatif_multiple", "base_rate_anchor"], "tier_plancher": "B+"},
    {"bloc": "qualitative_marche", "dimension": "produits",
     "champs_requis": ["description", "unit_economics"], "tier_plancher": "B+"},
    {"bloc": "qualitative_marche", "dimension": "positionnement",
     "champs_requis": ["moat_preuves", "position_vs_pairs"], "tier_plancher": "B+"},
    {"bloc": "qualitative_marche", "dimension": "marche",
     "champs_requis": ["croissance_marche_historique", "structure_5forces"], "tier_plancher": "B+"},
    {"bloc": "qualitative_marche", "dimension": "management_allocation",
     "champs_requis": ["incitations", "skin_in_game_pct"], "tier_plancher": "A-"},
    {"bloc": "qualitative_marche", "dimension": "risques",
     "champs_requis": ["risques_cles"], "tier_plancher": "B"},
]

# Chemins complets `dimension.champ` de tous les champs requis — vocabulaire FERMÉ de l'index
# `covers` (migration 029). Sert à filtrer ce qu'un modèle propose comme tag : depuis que la
# couverture est pilotée par l'index, un tag est un vote sur le verdict (cf. #24, même esprit que
# source_type). Un tag hors vocabulaire ne fonde rien — il est écarté, pas inventé.
MVDD_FIELD_PATHS: frozenset[str] = frozenset(
    f"{s['dimension']}.{champ}" for s in MVDD_SPEC for champ in s["champs_requis"]
)

# ordre de tri des tiers (meilleur → moins bon) pour comparaisons de plancher
TIER_ORDER = ["A", "A-", "B+", "B", "B-", "C+", "C"]
_TIER_RANK = {t: i for i, t in enumerate(TIER_ORDER)}

# ── Table de profils par champ (capacité 0 de `roadmap/02-spec-autorite-vs-actualite.md`) ────
# Trois propriétés indépendantes par champ, JAMAIS recombinées en un nombre (cf. convention #50) :
#
#   nature    — ce que l'assertion prétend être. Décide quel axe fait AUTORITÉ sur le champ :
#               `mesure` → la fiabilité domine · `interpretation` → l'expertise domine.
#   plancher  — tier minimal d'une entry pour FONDER le champ (borne basse d'admissibilité).
#   actualite_bloquante — un fait antérieur au dernier événement matériel cesse-t-il de fonder
#               le champ ? C'est une propriété du CHAMP, pas de la source.
#
# ⚠️ Aucun champ n'a `evenement` pour nature dominante, et ce n'est pas un oubli : un événement ne
# FONDE aucun des 19 champs, il PÉRIME les deux autres natures. Si la nature suffisait à décider de
# la péremption, cette colonne n'existerait pas — c'est exactement pourquoi elle existe. La nature
# `evenement` reste au vocabulaire des ENTRIES (migration 034), où elle qualifie une assertion.
#
# ⚠️ Le `motif` est un GABARIT et ne nomme jamais un émetteur (#31) : il énonce une propriété du
# champ, valable pour tout émetteur. Un motif qui nomme un acteur est une dispense déguisée.
FIELD_PROFILES: dict[str, dict[str, Any]] = {
    # ── structuree · business_model ──────────────────────────────────────────
    "business_model.description": {
        "nature": "interpretation", "plancher": "B+", "actualite_bloquante": True,
        "motif": "Ce que fait l'entreprise se réécrit à chaque événement structurant (première "
                 "approbation, cession d'un segment). Un dépôt périodique antérieur reste FIDÈLE à "
                 "sa source tout en décrivant un monde révolu.",
    },
    "business_model.drivers_revenus": {
        "nature": "interpretation", "plancher": "B+", "actualite_bloquante": True,
        "motif": "Les moteurs du chiffre d'affaires basculent avec le passage d'un stade au "
                 "suivant ; l'énoncé périmé ne devient pas faux, il devient hors sujet.",
    },
    "business_model.recurrence_pct": {
        "nature": "mesure", "plancher": "B+", "actualite_bloquante": False,
        "motif": "Part chiffrée, publiée par exercice quand elle l'est. Sa péremption est traitée "
                 "par le supersedage de l'identité du fait (#43), pas par l'ancre matérielle.",
    },
    # ── structuree · financials ──────────────────────────────────────────────
    "financials.roic_pct": {
        "nature": "mesure", "plancher": "A", "actualite_bloquante": False,
        "motif": "Ratio à composante de FLUX, donc daté par un exercice (#42) et remplacé au dépôt "
                 "suivant. L'ancre matérielle n'a rien à y ajouter.",
    },
    "financials.fcf_conversion_pct": {
        "nature": "mesure", "plancher": "A", "actualite_bloquante": False,
        "motif": "Ratio de flux sur flux, daté par son exercice (#42). Supersedage par (metric, "
                 "period_end) suffit à retirer le périmé.",
    },
    "financials.intensite_capex_pct": {
        "nature": "mesure", "plancher": "A", "actualite_bloquante": False,
        "motif": "Ratio de flux sur flux, daté par son exercice (#42).",
    },
    "financials.levier": {
        "nature": "mesure", "plancher": "A", "actualite_bloquante": True,
        "motif": "SEUL ratio bâti sur des postes de BILAN, donc daté à un instant (#42/#48) : une "
                 "levée de dette ou une émission de convertibles le change du jour au lendemain, "
                 "entre deux dépôts périodiques. La mention n'est portée QUE là où elle compte "
                 "(#42/#45) — l'étendre aux trois ratios de flux la rendrait invisible ici.",
    },
    # ── structuree · valorisation ────────────────────────────────────────────
    "valorisation.prix_actuel": {
        "nature": "mesure", "plancher": "B+", "actualite_bloquante": True,
        "motif": "Un cours se périme en jours. C'est le champ où l'actualité prime le plus "
                 "nettement sur l'autorité de la source.",
    },
    "valorisation.relatif_multiple": {
        "nature": "mesure", "plancher": "B+", "actualite_bloquante": True,
        "motif": "Multiples adossés au cours : ils héritent de sa péremption. ⚠️ Un multiple à "
                 "dénominateur négatif est NON CALCULABLE, pas absent (#44) — état distinct d'une "
                 "péremption, jamais confondu avec elle.",
    },
    "valorisation.base_rate_anchor": {
        "nature": "interpretation", "plancher": "B+", "actualite_bloquante": False,
        "motif": "Ancre de taux de base : un corpus historique long, délibérément insensible à "
                 "l'actualité — c'est sa fonction même. ⚠️ Son entry est transverse aux émetteurs "
                 "et peut n'avoir AUCUNE `source_date` : la rendre bloquante la classerait "
                 "`indeterminable` (#44) et bloquerait tout émetteur d'emblée.",
    },
    # ── qualitative_marche · produits ────────────────────────────────────────
    "produits.description": {
        "nature": "interpretation", "plancher": "B+", "actualite_bloquante": True,
        "motif": "Le portefeuille de produits est ce qu'une autorisation de mise sur le marché ou "
                 "un retrait modifie en premier. Champ le plus exposé à la péremption silencieuse.",
    },
    "produits.unit_economics": {
        "nature": "mesure", "plancher": "B+", "actualite_bloquante": False,
        "motif": "Économie unitaire chiffrée, à évolution lente et publiée par exercice.",
    },
    # ── qualitative_marche · positionnement ──────────────────────────────────
    "positionnement.moat_preuves": {
        "nature": "interpretation", "plancher": "B", "actualite_bloquante": False,
        "desserrage": "B+ → B : champ d'INTERPRÉTATION où un observateur sectoriel suivi vaut "
                      "mieux qu'un dépôt réglementaire. Ne prend effet qu'avec la capacité 2 "
                      "(registre nominatif) — sans elle, ce plancher n'admet personne de nouveau.",
        "motif": "Les preuves d'avantage concurrentiel s'établissent sur plusieurs exercices ; un "
                 "événement isolé ne les périme pas.",
    },
    "positionnement.position_vs_pairs": {
        "nature": "interpretation", "plancher": "B", "actualite_bloquante": True,
        "desserrage": "B+ → B : voir `positionnement.moat_preuves`. Effet conditionné à la "
                      "capacité 2.",
        "motif": "La position relative bascule quand un pair OU l'émetteur franchit une étape "
                 "structurante : c'est une comparaison, donc datée par le plus récent des deux.",
    },
    # ── qualitative_marche · marche ──────────────────────────────────────────
    "marche.croissance_marche_historique": {
        "nature": "mesure", "plancher": "B", "actualite_bloquante": False,
        "motif": "Série historique chiffrée. Plancher B DÉJÀ en vigueur "
                 "(`FIELD_PLANCHER_OVERRIDES`) : les cabinets d'études plafonnent à "
                 "`web_search_reputable` (#32), un plancher plus haut rendrait le champ "
                 "infondable au lieu de le rendre exigeant.",
    },
    "marche.structure_5forces": {
        "nature": "interpretation", "plancher": "B", "actualite_bloquante": False,
        "desserrage": "B+ → B : cas d'école de la doctrine — un dépôt réglementaire est ici du "
                      "boilerplate juridique malgré son tier A, un analyste sectoriel est "
                      "STRICTEMENT meilleur. Effet conditionné à la capacité 2.",
        "motif": "Structure concurrentielle d'un marché : elle bouge à l'échelle des années.",
    },
    # ── qualitative_marche · management_allocation ───────────────────────────
    "management_allocation.incitations": {
        "nature": "mesure", "plancher": "A-", "actualite_bloquante": False,
        "motif": "Structure de rémunération, publiée annuellement dans un document de "
                 "sollicitation de procurations. Périodique, donc traitée par supersedage.",
    },
    "management_allocation.skin_in_game_pct": {
        "nature": "mesure", "plancher": "A-", "actualite_bloquante": True,
        "motif": "La détention des dirigeants change par déclarations d'initiés ponctuelles, pas "
                 "au rythme des dépôts périodiques : un chiffre d'il y a un an peut décrire une "
                 "position soldée depuis.",
    },
    # ── qualitative_marche · risques ─────────────────────────────────────────
    "risques.risques_cles": {
        "nature": "interpretation", "plancher": "B", "actualite_bloquante": True,
        "desserrage": "B+ → B (plancher de dimension B, donc ALIGNÉ, pas desserré) — mentionné "
                      "pour mémoire : c'est le second champ où le tier A d'un dépôt ne vaut pas "
                      "son autorité apparente.",
        "motif": "Une section « facteurs de risque » énumère des risques juridiquement exhaustifs "
                 "sans les hiérarchiser ; et le risque le plus vif est celui qu'un événement "
                 "récent vient de matérialiser ou d'éteindre.",
    },
}

NATURES: frozenset[str] = frozenset({"mesure", "evenement", "interpretation"})

# ── L'axe `nature` d'une ENTRY (capacité 1 · migration 034) ───────────────────
# ⚠️ DEUX VOCABULAIRES DISTINCTS, et les confondre casse la doctrine :
#
#   FIELD_PROFILES[...]["nature"] — nature DOMINANTE d'un CHAMP : quel axe fait autorité pour le
#       fonder. C'est une exigence, co-écrite, qui ne décrit aucune donnée existante.
#   `knowledge_entries.nature`    — ce que l'ASSERTION prétend être. C'est un fait sur l'entry.
#
# Le vocabulaire des entries est STRICTEMENT PLUS LARGE : `evenement` n'est la nature dominante
# d'aucun des 19 champs (résultat de la capacité 0 — un événement ne FONDE rien, il PÉRIME), mais
# une entry peut parfaitement en être un. Dériver la nature d'une entry depuis celle de son champ
# rendrait donc `evenement` inatteignable, et surtout : ça ferait dire à une donnée ce qu'on
# ATTEND d'elle. La confrontation des deux est le travail de la porte (capacité 4), pas celui de
# l'écriture.
#
# ⚠️ `mesure` est la nature FORTE : elle donne autorité à la fiabilité de la source et soustrait le
# fait à l'horloge matérielle. On ne l'accorde donc jamais par défaut — toute incertitude retombe
# sur `interpretation` (transposition de #44 : « non qualifiable » n'est pas « mesure au rabais »).

# Une source qui ne MESURE jamais, quoi qu'elle couvre : une mémoire de modèle et une synthèse
# d'agent produisent un énoncé, pas un relevé. Filtre appliqué EN PREMIER — il l'emporte sur
# l'entry_type, sinon un `fact_financial` restitué de mémoire hériterait de l'autorité d'un dépôt.
_NON_MEASURING_SOURCES: frozenset[str] = frozenset({"llm_memory", "agent_synthesis"})

# Producteurs déterministes : le contenu est un relevé (dépôt XBRL, fournisseur de marché) ou une
# fréquence empirique tirée d'un corpus (`base_rate` — « P(≥20 %/an)=8,5 % » est une mesure sur une
# classe de référence, pas une prévision ; le CHAMP qu'elle fonde est d'interprétation, l'entry
# non).
_MEASURING_ENTRY_TYPES: frozenset[str] = frozenset({"fact_financial", "base_rate"})

# Producteurs de jugement : quel que soit le champ visé, la sortie est un énoncé du modèle.
_INTERPRETING_ENTRY_TYPES: frozenset[str] = frozenset(
    {"analysis", "agent_synthesis", "risk", "lesson_learned"}
)


def _covers_all_mesure(covers: Optional[Sequence[str]]) -> bool:
    """Unanimité : TOUS les champs couverts sont de nature dominante `mesure`.

    L'unanimité est exigée dans le sens PRUDENT (cf. #44) : une entry qui fonde à la fois un
    pourcentage publié et un driver d'interprétation fait deux choses, et la plus forte des deux
    revendications ne doit pas emporter l'autre. Un chemin hors vocabulaire ne vote pas `mesure` —
    il ne peut pas non plus lever un KeyError (#50 §1 : un champ inconnu est nommé, pas fatal).
    """
    paths = [c for c in (covers or []) if c]
    if not paths:
        return False
    return all(FIELD_PROFILES.get(p, {}).get("nature") == "mesure" for p in paths)


def derive_nature(
    *,
    entry_type: str,
    source_type: str,
    covers: Optional[Sequence[str]] = None,
    declared: Optional[str] = None,
) -> tuple[str, str]:
    """Nature d'une entry — DÉTENTEUR UNIQUE de la règle (#46). Rend `(nature, motif)`.

    Dérivation déterministe depuis les trois entrées prévues par la spec (`source_type` ·
    `entry_type` · champ couvert), dans cet ordre de priorité. Aucun producteur ne la
    ré-implémente : `store_knowledge` l'appelle pour TOUS les sites d'écriture, c'est le seul
    passage obligé des 8 producteurs.

    `declared` = la nature proposée par le modèle. **Elle n'est honorée que pour promouvoir vers
    `evenement`** — la seule nature qui SOUMET l'assertion à l'horloge matérielle, donc le seul
    mouvement qui resserre (garde symétrique de #29/#24). Toute autre proposition est écartée en le
    disant : laisser un modèle requalifier un fait EDGAR en `interpretation` le sortirait du
    plancher A, et le requalifier en `mesure` lui accorderait l'autorité de la fiabilité sans
    qu'aucune source ne la porte.
    """
    if source_type in _NON_MEASURING_SOURCES:
        nature, motif = "interpretation", f"source `{source_type}` : énoncé produit, jamais relevé"
    elif entry_type in _MEASURING_ENTRY_TYPES:
        nature, motif = "mesure", f"entry_type `{entry_type}` : producteur déterministe"
    elif entry_type in _INTERPRETING_ENTRY_TYPES:
        nature, motif = "interpretation", f"entry_type `{entry_type}` : jugement produit"
    elif _covers_all_mesure(covers):
        nature = "mesure"
        motif = "champs couverts tous de nature dominante `mesure` : " + ",".join(sorted(covers or []))
    else:
        nature = "interpretation"
        motif = (
            "défaut prudent : ni producteur déterministe, ni couverture unanimement `mesure`"
            + (f" (couvre {','.join(sorted(covers or []))})" if covers else " (ne couvre aucun champ)")
        )

    if declared and declared != nature:
        if declared == "evenement" and declared in NATURES:
            return "evenement", f"{motif} → promu `evenement` par l'agent (resserrement admis)"
        motif += f" ; proposition `{declared}` écartée (desserrage : seul `evenement` peut être promu)"
    return nature, motif


def profile_for(field_path: str) -> dict[str, Any]:
    """Profil d'un champ MVDD. Champ hors vocabulaire → KeyError : il n'y a pas de profil par
    défaut, un champ sans doctrine écrite ne se traite pas « au mieux » (#31)."""
    return FIELD_PROFILES[field_path]


def count_tiers(entries: Sequence[dict[str, Any]]) -> dict[str, int]:
    """entries_par_tier DÉTERMINISTE (recompute depuis la KB, aucun token — readiness §7).

    Regroupe A/A- → tier_A, B+/B/B- → tier_B ; tier_C_llm_memory = entrées C ou source llm_memory.
    """
    tier_A = tier_B = tier_C = 0
    for e in entries:
        tier = e.get("reliability_tier")
        if e.get("source_type") == "llm_memory" or tier == "C":
            tier_C += 1
        elif tier in ("A", "A-"):
            tier_A += 1
        elif tier in ("B+", "B", "B-", "C+"):
            tier_B += 1
        else:
            tier_C += 1
    return {"tier_A": tier_A, "tier_B": tier_B, "tier_C_llm_memory": tier_C,
            "total": tier_A + tier_B + tier_C}


def _truncate(text: str, limit: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def format_entries_for_prompt(entries: Sequence[dict[str, Any]], *, content_limit: int = 400) -> str:
    """Listing déterministe des knowledge_entries pour le head de prompt (cache §5.3).

    Trié par id (stable). Chaque ligne : `#id vN [tier · source_type · fiscal] type — contenu`. Le
    contenu financier n'est pas tronqué agressivement (les chiffres portent la décision). L'agent cite
    par `entry_id` (+ version) dans ses `source_entry_refs`.
    """
    lines: list[str] = []
    for e in sorted(entries, key=lambda x: x["id"]):
        meta = f"{e.get('reliability_tier','?')} · {e.get('source_type','?')}"
        if e.get("fiscal_period"):
            meta += f" · {e['fiscal_period']}"
        flag = " ⚠review" if e.get("requires_human_review") else ""
        covers = e.get("covers")
        if isinstance(covers, str):
            covers = [covers]
        if covers:
            # Rend l'index VISIBLE au modèle : il n'en dérive plus la couverture (c'est le backend),
            # mais il écrit les gaps — voir quels champs sont déjà tenus lui évite d'en réclamer.
            meta += " · couvre " + ",".join(sorted(covers))
        title = f"{e['title']} — " if e.get("title") else ""
        body = _truncate(e.get("content", ""), content_limit)
        lines.append(f"#{e['id']} v{e.get('version',1)} [{meta}]{flag} {e.get('entry_type','')}: {title}{body}")
    return "\n".join(lines) if lines else "(aucune knowledge_entry courante)"
