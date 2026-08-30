"""
Alimentateur de SYNTHÈSE GROUNDED (ingestion-agent, mode synthèse) — V2.

Motif (00-REPRISE, MàJ 2026-08-26) : deux champs qualitatifs bloquent encore la readiness NVDA —
`produits.unit_economics` et `marche.structure_5forces`. Le search-worker a été exercé dessus
(2026-08-26, dry-run) → `not_found` : ce ne sont PAS des faits fetchables (l'économie unitaire n'est
pas disclosée ; l'analyse de Porter n'existe nulle part telle quelle). Le KB a pourtant déjà les
matériaux tier A/B+ (marges/coûts pour unit_economics ; menace ASIC / concentration clients /
AMD-Huawei / TSMC / export controls pour les 5 forces) — mais aucune entry ne les SYNTHÉTISE au niveau
que le curator exige.

Cet alimentateur comble ce trou, même patron que `valuation_feed`/`financials_feed` (transformation
PURE testable + couche IO) mais avec UN tour LLM, GROUNDED :
  1. charger les entries CITABLES (tier A/A-/B+) pertinentes pour le champ visé ;
  2. un tour LLM (DeepInfra, modèle de l'ingestion-agent) compose la synthèse STRICTEMENT à partir de
     ces entries — chaque assertion cite ≥1 `entry_id`, aucun fait hors-KB (GroundedSynthesis) ;
  3. VÉRIFIER en Python que chaque id cité appartient au corpus citable (grounding réel, pas déclaré,
     #24/#28) ; DÉRIVER le tier « un cran sous la plus faible entry citée » (règle validée : une
     synthèse n'est jamais plus solide que son maillon le plus faible, moins un cran de risque de
     composition) ; persister une entry `entry_type='analysis'`, `source_type='agent_synthesis'`,
     `requires_human_review=True` (une synthèse machine se relit avant d'être exploitée par la chaîne).

Ce qu'il NE fait PAS (G3, le cœur du projet) : il n'injecte jamais un fait absent des entries citées
pour forcer `ready`. Si le KB n'a pas assez de matériau citable pour un champ → `SynthesisUnavailable`
(un trou honnête, jamais une entrée fabriquée, #25). Si la synthèse cite hors du corpus →
`SynthesisUngrounded` (rejetée, rien n'est écrit).

La transformation est pure (`derive_synthesis_reliability`, `validate_grounding`,
`build_content_structured`) → vérifiable hors-ligne (`backend/checks/check_synthesis_feed.py`). L'IO
(chargement KB + tour LLM + écriture) vit dans `run_synthesis_feed`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from app.agents.providers import ResolvedAgent, get_agent_provider
from app.agents.v2.common import TIER_ORDER, format_entries_for_prompt
from app.agents.v2.runner import run_json_agent
from app.contracts import GroundedSynthesis
from app.db.database import get_db_session
from app.knowledge.service import query_knowledge, store_knowledge

logger = logging.getLogger(__name__)

_SOURCE_TYPE = "agent_synthesis"

# Tiers qu'une synthèse a le droit de citer (≥ plancher B+ des champs visés). Une synthèse adossée à
# une entry sous B+ serait plus faible que le plancher qu'on cherche à franchir → hors corpus citable.
CITABLE_TIERS = ("A", "A-", "B+")

# Dérivation « un cran sous » : (tier, score) de la synthèse selon la PLUS FAIBLE entry citée.
# A→A- (0.85), A-→B+ (0.75), B+→B (0.70). Cohérent avec RELIABILITY_TABLE (mêmes baselines de tier).
# ⚠️ RÈGLE PROVISOIRE (décision utilisateur 2026-08-26, option conservatrice) : à REVOIR à l'usage si
# elle bloque trop (un champ à plancher B+ citant une seule entry B+ tombe à B < plancher). Pistes de
# relâche si besoin : « un cran sous la MEILLEURE citée dès ≥N tier-A », ou re-tag après revue humaine.
# Plus largement, la catégorisation de qualité des sources (baselines de tier) pourra être réajustée.
_NOTCH_BELOW: dict[str, tuple[str, float]] = {
    "A": ("A-", 0.85),
    "A-": ("B+", 0.75),
    "B+": ("B", 0.70),
}
_FALLBACK_NOTCH = ("B-", 0.60)  # plus faible cité sous B+ (ne devrait pas arriver après filtre citable)

_TIER_RANK = {t: i for i, t in enumerate(TIER_ORDER)}  # 0 = meilleur (A) … plus grand = plus faible


@dataclass(frozen=True)
class SynthesisTarget:
    """Descripteur d'un champ synthétisable : quelles entries charger, et la consigne de composition."""
    field_path: str
    dimension: str
    entry_type: str
    query: str                       # requête sémantique de chargement des entries citables
    candidate_entry_types: tuple[str, ...]
    min_citations: int               # sous ce seuil de matériau citable → SynthesisUnavailable
    guidance: str                    # ce que la synthèse doit couvrir (injecté au LLM)
    # Tiers admis dans le corpus citable de CE champ. Par défaut A/A-/B+. Un champ dont le matériau
    # honnête est purement tier A (ex. unit_economics = marges/coûts EDGAR/IR) restreint à ("A","A-") :
    # ça exclut par PERTINENCE les entries hors-champ de moindre tier (presse marché) qui, sinon,
    # tireraient la synthèse sous le plancher via la règle « un cran sous la plus faible citée ».
    citable_tiers: tuple[str, ...] = CITABLE_TIERS


# Cibles connues. Génériques par construction — ajouter une entrée ici suffit à ouvrir un champ.
SYNTHESIS_TARGETS: dict[str, SynthesisTarget] = {
    "produits.unit_economics": SynthesisTarget(
        field_path="produits.unit_economics",
        dimension="produits",
        entry_type="analysis",
        query=(
            "économie unitaire marge brute marge opérationnelle coût unitaire coût par GPU coût par "
            "token ASP prix de vente moyen pricing power structure de coûts data center"
        ),
        candidate_entry_types=("fact_qualitative", "fact_financial", "analysis", "quote"),
        min_citations=2,
        citable_tiers=("A", "A-"),  # socle marges/coûts tier A ; exclut la presse marché B+ (hors-champ)
        guidance=(
            "Synthétise l'ÉCONOMIE UNITAIRE (unit economics) du produit : structure de marge (marge "
            "brute / opérationnelle disponible dans les entries), levier de prix (ASP / pricing power), "
            "coûts unitaires SEULEMENT s'ils sont dérivables des entries citées (coût par GPU / par "
            "token), et ce qui reste NON OBSERVABLE en l'état. N'invente aucun chiffre absent des "
            "entries. Un aspect sans matériau en base se déclare « non documenté à ce jour »."
        ),
    ),
    "positionnement.moat_preuves": SynthesisTarget(
        field_path="positionnement.moat_preuves",
        dimension="positionnement",
        entry_type="analysis",
        query=(
            "avantage concurrentiel durable moat NVIDIA écosystème logiciel CUDA coûts de transition "
            "base installée développeurs verrouillage réseau NVLink effets d'échelle barrières"
        ),
        candidate_entry_types=("fact_qualitative", "analysis", "quote", "risk", "fact_financial"),
        min_citations=2,
        citable_tiers=("A", "A-"),  # preuves du moat = socle A (CUDA, échelle, risques EDGAR A) ; la
                                    # presse marché B+ (#21/#22) porte des MENACES, pas des preuves
        guidance=(
            "Synthétise les PREUVES du moat (avantage concurrentiel durable) : nature du moat "
            "(écosystème logiciel CUDA / coûts de transition, base installée, effets de réseau "
            "NVLink, échelle R&D), preuves chiffrées ou factuelles tirées des entries, et durabilité "
            "vs menaces (ASIC maison, AMD). Chaque preuve adossée aux entries citées ; un aspect sans "
            "matériau en base se déclare « non documenté », jamais inventé."
        ),
    ),
    "marche.structure_5forces": SynthesisTarget(
        field_path="marche.structure_5forces",
        dimension="marche",
        entry_type="analysis",
        query=(
            "cinq forces de Porter rivalité concurrentielle nouveaux entrants ASIC hyperscalers "
            "concentration clients pouvoir fournisseur TSMC substituts AMD Huawei barrières à l'entrée "
            "export controls"
        ),
        candidate_entry_types=("risk", "fact_qualitative", "analysis", "quote"),
        min_citations=3,
        citable_tiers=("A", "A-"),  # les 5 forces sont adossables aux facteurs de risque EDGAR tier A
                                    # (ASIC, AMD/Huawei, TSMC, concentration, export controls) ; la
                                    # presse B+ portait la même chose en moins fiable → exclue
        guidance=(
            "Structure une analyse des 5 forces de Porter, une par une : (1) intensité de la rivalité "
            "concurrentielle, (2) menace de nouveaux entrants (ASIC maison des hyperscalers, Huawei), "
            "(3) pouvoir de négociation des clients (concentration hyperscalers), (4) pouvoir de "
            "négociation des fournisseurs (TSMC, HBM), (5) menace de produits de substitution. Chaque "
            "force est adossée aux entries citées et qualifiée (faible / modérée / élevée) avec la "
            "preuve. Une force sans matériau en base se déclare « non documentée », jamais inventée."
        ),
    ),
}


_SYNTHESIS_SYSTEM_PROMPT = (
    "Tu es l'ingestion-agent en MODE SYNTHÈSE. On te confie UN champ d'analyse et un corpus d'entries "
    "de connaissance déjà vérifiées et scorées (tier A/A-/B+). Ta tâche : composer une synthèse "
    "dense et structurée de ce champ, STRICTEMENT à partir de ce corpus.\n\n"
    "RÈGLE ABSOLUE (anti-hallucination) : tu n'apportes AUCUN fait qui ne soit dans les entries "
    "fournies. Chaque assertion de `claims[]` doit citer, dans `cited_entry_ids`, le ou les `entry_id` "
    "(#N dans le listing) qui la fondent. Une assertion sans source dans le corpus est INTERDITE : "
    "si l'information manque, écris-le explicitement (« non documenté en base ») plutôt que de la "
    "reconstruire de mémoire. Tu ne cites QUE des id présents dans le listing.\n\n"
    "Tu NE fournis PAS de score, de tier ni de source_type : ils sont dérivés par le backend depuis "
    "les entries que tu cites. Tu ne juges pas la valeur d'investissement : tu synthétises.\n\n"
    "`synthesis_markdown` = la synthèse lisible (Markdown, structurée selon la consigne). `claims[]` = "
    "la décomposition en assertions atomiques sourcées (elles doivent couvrir le contenu de la "
    "synthèse). Sortie : UNIQUEMENT l'objet JSON du contrat GroundedSynthesis, rien d'autre."
)


class SynthesisUnavailable(Exception):
    """Le champ n'est pas synthétisable : cible inconnue, ou pas assez de matériau citable en base.
    Distinct d'un résultat vide — l'appelant DOIT le remonter (#25), jamais fabriquer une entrée."""


class SynthesisUngrounded(Exception):
    """La synthèse produite cite hors du corpus citable (ou une assertion non sourcée) : elle est
    rejetée, rien n'est écrit. Le grounding est VÉRIFIÉ, pas déclaré (#24/#28)."""


# ── Transformations PURES (testables hors-ligne) ─────────────────────────────
def derive_synthesis_reliability(cited_tiers: list[str]) -> tuple[float, str, str]:
    """(score, tier, note) d'une synthèse = un cran SOUS la plus faible entry citée (règle validée).

    Pur. `cited_tiers` = tiers RÉELS (lus en base) des entries citées, pas déclarés par le modèle.
    """
    if not cited_tiers:
        raise ValueError("derive_synthesis_reliability: aucune entry citée")
    # plus faible = rang le plus grand dans TIER_ORDER (A=0 … C=6)
    weakest = max(cited_tiers, key=lambda t: _TIER_RANK.get(t, len(TIER_ORDER)))
    tier, score = _NOTCH_BELOW.get(weakest, _FALLBACK_NOTCH)
    uniq = sorted(set(cited_tiers), key=lambda t: _TIER_RANK.get(t, len(TIER_ORDER)))
    note = (
        f"synthèse grounded de {len(cited_tiers)} citation(s) [tiers {', '.join(uniq)}] ; "
        f"plus faible cité = {weakest} → un cran sous = {tier} ({score:.2f}) ; "
        f"agent_synthesis ; revue humaine requise avant exploitation par la chaîne d'analyse"
    )
    return score, tier, note


def validate_grounding(claims: list[dict[str, Any]], citable_ids: set[int]) -> list[str]:
    """Renvoie la liste des VIOLATIONS de grounding (vide = ok). Pur.

    Un claim doit citer ≥1 id (déjà garanti par le contrat) ET chaque id cité doit appartenir au
    corpus citable réellement chargé. Un id hors corpus = le modèle a apporté une source non vérifiée.
    """
    errors: list[str] = []
    for idx, claim in enumerate(claims):
        cited = claim.get("cited_entry_ids") or []
        if not cited:
            errors.append(f"claim #{idx} sans citation (assertion non sourcée)")
            continue
        for cid in cited:
            if cid not in citable_ids:
                errors.append(
                    f"claim #{idx} cite #{cid} hors du corpus citable {sorted(citable_ids)}"
                )
    return errors


def build_content_structured(
    target: SynthesisTarget,
    synth: GroundedSynthesis,
    cited_ids: list[int],
    tiers_by_id: dict[int, str],
) -> dict[str, Any]:
    """content_structured d'une entry de synthèse (traçabilité du grounding). Pur."""
    return {
        "field_path": target.field_path,
        "dimension": target.dimension,
        "synthesis_kind": "grounded_synthesis",
        "cited_entry_ids": cited_ids,
        "claims": [{"text": c.text, "cited_entry_ids": sorted(c.cited_entry_ids)} for c in synth.claims],
        "derived_from_tiers": {str(cid): tiers_by_id.get(cid) for cid in cited_ids},
        "review_status": "pending",
    }


def _tags(target: SynthesisTarget) -> list[str]:
    return ["synthesis", target.dimension, target.field_path]


# ── Couche IO ────────────────────────────────────────────────────────────────
async def _current_synthesis_entry_id(conn, ticker_id: str, target: SynthesisTarget) -> Optional[int]:
    """Id de la synthèse COURANTE pour ce champ (à superseder). Ce feed est le seul producteur du
    triplet de tags → pas de collision avec une entry de recherche."""
    row = await conn.fetchrow(
        """
        SELECT id FROM knowledge_entries
        WHERE ticker_id = $1 AND superseded_by IS NULL AND is_deleted = FALSE
          AND tags @> $2
        ORDER BY id DESC LIMIT 1
        """,
        ticker_id, _tags(target),
    )
    return row["id"] if row else None


# Squelette JSON explicite injecté au tour : sous response_format=json_object, DeepSeek se rabat sur
# `{}` (JSON valide mais vide) quand la forme attendue n'est pas montrée noir sur blanc. Le curator
# évite ce piège parce que son prompt DB détaille le schéma — on fait pareil ici (vérifié : sans ce
# squelette, le modèle renvoyait `{}` deux fois de suite, 2026-08-26).
_SYNTHESIS_SKELETON = (
    '{\n'
    '  "title": "<titre court du champ synthétisé>",\n'
    '  "synthesis_markdown": "<synthèse Markdown structurée selon la consigne>",\n'
    '  "claims": [\n'
    '    {"text": "<assertion atomique>", "cited_entry_ids": [<#id du corpus>, ...]},\n'
    '    {"text": "<autre assertion>", "cited_entry_ids": [<#id>]}\n'
    '  ],\n'
    '  "lang": "fr"\n'
    '}'
)


def _synthesis_task_message(target: SynthesisTarget, listing: str) -> str:
    return (
        f"[mode: synthese]\n\n"
        f"Champ à synthétiser : `{target.field_path}` (dimension {target.dimension}).\n\n"
        f"Consigne de composition :\n{target.guidance}\n\n"
        f"Corpus citable — entries de connaissance COURANTES, tier A/A-/B+ (cite-les par leur #id, "
        f"et UNIQUEMENT celles-ci) :\n{listing}\n\n"
        f"Produis l'objet GroundedSynthesis, en respectant EXACTEMENT cette forme (commence par `{{` "
        f"et termine par `}}`, aucun texte autour) :\n{_SYNTHESIS_SKELETON}\n\n"
        f"`claims[]` doit être NON VIDE et chaque assertion porte au moins un `cited_entry_ids` pris "
        f"dans le corpus ci-dessus. Aucun fait hors de ce corpus."
    )


async def _resolve_synthesis_agent() -> ResolvedAgent:
    """Réutilise le provider + modèle de l'ingestion-agent (config en DB, #DB source de vérité), mais
    avec le prompt système de SYNTHÈSE (le prompt DB de l'ingestion-agent est celui de l'extraction de
    document, qui interdit explicitement la synthèse). Le prompt de ce mode vit dans le code, comme la
    logique des autres feeds (valuation/financials/base_rate)."""
    base = await get_agent_provider("ingestion-agent", "v2")
    return ResolvedAgent(
        agent_name="ingestion-agent",
        flow_version="v2",
        provider=base.provider,
        model=base.model,
        system_prompt=_SYNTHESIS_SYSTEM_PROMPT,
    )


async def run_synthesis_feed(
    ticker_id: str,
    field_path: str,
    *,
    persist: bool = True,
    max_candidates: int = 20,
    debug_raw: bool = False,
) -> dict[str, Any]:
    """Fonde un champ qualitatif par SYNTHÈSE grounded des entries tier A/A-/B+ déjà en base.

    `persist=False` = dry-run (base append-only : on regarde ce qui entrerait avant d'écrire). Lève
    `SynthesisUnavailable` si le champ est inconnu ou le matériau citable insuffisant ;
    `SynthesisUngrounded` si la synthèse produite sort du corpus (rien n'est écrit).
    """
    target = SYNTHESIS_TARGETS.get(field_path)
    if target is None:
        raise SynthesisUnavailable(
            f"champ non synthétisable : {field_path} (connus : {sorted(SYNTHESIS_TARGETS)})"
        )

    # 1) charger le corpus citable (tier A/A-/B+ pertinent pour le champ) --------------------------
    async with get_db_session() as conn:
        found = await query_knowledge(
            conn, ticker_id=ticker_id, query=target.query,
            entry_types=list(target.candidate_entry_types),
            min_reliability=0.70, include_sector=True, limit=max_candidates,
        )
    citable = [e for e in found if e.get("reliability_tier") in target.citable_tiers]
    if len(citable) < target.min_citations:
        raise SynthesisUnavailable(
            f"{ticker_id}/{field_path} : {len(citable)} entrie(s) citable(s) tier A/A-/B+ en base "
            f"(< {target.min_citations} requis) — le champ n'est pas synthétisable sans plus de "
            f"matériau ; lancer d'abord le search-worker / l'ingestion sur cette dimension (#25)"
        )

    tiers_by_id = {e["id"]: e["reliability_tier"] for e in citable}
    citable_ids = set(tiers_by_id)

    # 2) tour LLM grounded --------------------------------------------------------------------------
    agent = await _resolve_synthesis_agent()
    listing = format_entries_for_prompt(citable, content_limit=700)
    task = _synthesis_task_message(target, listing)

    if debug_raw:
        # Observabilité de la frontière LLM : renvoie la sortie brute sans validation (diagnostic).
        res = await agent.complete([{"role": "user", "content": task}], temperature=0.2)
        return {
            "ticker_id": ticker_id, "field_path": field_path, "debug_raw": True,
            "citable_count": len(citable), "citable_ids": sorted(citable_ids), "model": agent.model,
            "finish_reason": res.finish_reason, "tokens_out": res.tokens_out,
            "raw_content": res.content[:3000],
        }

    # json_object=False : DeepSeek-V4-Flash est non fiable en mode json_object (cf. run_json_agent).
    run = await run_json_agent(
        agent, [{"role": "user", "content": task}],
        GroundedSynthesis, temperature=0.2, json_object=False,
    )
    synth: GroundedSynthesis = run.parsed  # type: ignore[assignment]

    # 3) vérifier le grounding (RÉEL, pas déclaré) --------------------------------------------------
    errors = validate_grounding(
        [{"text": c.text, "cited_entry_ids": c.cited_entry_ids} for c in synth.claims], citable_ids
    )
    if errors:
        raise SynthesisUngrounded(
            f"{ticker_id}/{field_path} : synthèse non fondée ({len(errors)} violation(s)) — "
            + " ; ".join(errors[:5])
        )

    cited_ids = synth.cited_entry_ids()
    cited_tiers = [tiers_by_id[cid] for cid in cited_ids]
    score, tier, note = derive_synthesis_reliability(cited_tiers)
    content_structured = build_content_structured(target, synth, cited_ids, tiers_by_id)

    content = (
        f"{synth.synthesis_markdown}\n\n"
        f"_Synthèse grounded (`{target.field_path}`) composée à partir des entries "
        f"{', '.join('#' + str(i) for i in cited_ids)}. Tier dérivé {tier} (un cran sous la plus "
        f"faible entry citée). Revue humaine requise._"
    )

    persisted: Optional[dict[str, Any]] = None
    if persist:
        async with get_db_session() as conn:
            async with conn.transaction():
                prev = await _current_synthesis_entry_id(conn, ticker_id, target)
                stored = await store_knowledge(
                    conn, ticker_id=ticker_id, entry_type=target.entry_type, content=content,
                    source_type=_SOURCE_TYPE, title=synth.title,
                    content_structured=content_structured, tags=_tags(target), lang=synth.lang,
                    supersedes_entry_id=prev, requires_human_review=True,
                    derived_reliability=(score, tier, note),
                    covers=[target.field_path],   # index 029 : chemin complet, plus le nom nu
                )
                persisted = dict(stored) | {"supersedes": prev}
        logger.info(
            "synthesis_feed %s/%s → entry #%s tier %s (%.2f) ; %d citation(s) %s ; supersede %s",
            ticker_id, field_path, persisted["id"], tier, score, len(cited_ids), cited_ids,
            persisted["supersedes"],
        )

    return {
        "ticker_id": ticker_id,
        "field_path": field_path,
        "dimension": target.dimension,
        "entry_type": target.entry_type,
        "source_type": _SOURCE_TYPE,
        "derived_tier": tier,
        "derived_score": score,
        "reliability_note": note,
        "citable_count": len(citable),
        "cited_entry_ids": cited_ids,
        "cited_tiers": cited_tiers,
        "n_claims": len(synth.claims),
        "title": synth.title,
        "content": content,
        "content_structured": content_structured,
        "requires_human_review": True,
        "cost_usd": run.cost_usd,
        "tokens_in": run.tokens_in,
        "tokens_out": run.tokens_out,
        "persisted": persisted,
        "dry_run": not persist,
    }
