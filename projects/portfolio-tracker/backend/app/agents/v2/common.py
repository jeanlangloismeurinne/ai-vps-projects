"""
Helpers partagés des agents V2 de la chaîne d'analyse (curator / research / bull / bear / synthèse).

Regroupe : la spec MVDD (dimension → champs factuels requis → tier plancher, dérivée de
readiness_derivation.md §), le formatage DÉTERMINISTE des knowledge_entries pour l'insertion en tête
de prompt (discipline de cache §5.3 : tri stable, aucun champ volatil), et le comptage par tier.
"""
from __future__ import annotations

from typing import Any, Sequence

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
