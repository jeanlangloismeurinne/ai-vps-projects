"""
Chaîne d'analyse V2 (métier) — research → bull/bear → réfutation (A6) → synthèse (§8).

DÉCISION #1 (option C) : base NEUTRE (research_memo) → bull/bear produits en contexte ISOLÉ →
réfutation asymétrique bear→bull (une passe) → synthèse dialectique (seul verdict, Q2). Chaque agent
est front-loadé par le `context_pack` du curator (réutilisation durable + cache §5.3) et cite ses
sources par entry_id ; les refs sont figées en snapshot (analysis_knowledge_refs, A1/A2) à la
persistance. Le contexte figé (préambule + rôle + context_pack) est en tête, la tâche du tour en fin.

Chaque sortie est VALIDÉE contre son contrat Pydantic (G1) via run_json_agent ; la synthèse valide en
plus le pont risques↔hypothèses (§8.5). L'auditabilité (P0) fige provider/model/prompt_snapshot +
coût/tokens par ligne.

NB infra : le mandat de recherche divergente du bear (A6) et l'enrichissement à la demande passent par
le search-worker (web_search) — backend absent (SearXNG/API). En attendant, bull & bear travaillent sur
la KB existante (context_pack + entries courantes) ; la divergence reste possible dès l'infra dispo.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.agents.providers import ResolvedAgent, get_agent_provider
from app.agents.v2.common import format_entries_for_prompt
from app.agents.v2.runner import run_json_agent
from app.contracts import BearCase, BullCase, ResearchMemo
from app.contracts.composites import SynthesisOutput
from app.db.database import get_db_session
from app.knowledge import collect_refs, get_current_entries, snapshot_refs

logger = logging.getLogger(__name__)


# ── chargement du front-load (context_pack ready) ────────────────────────────
class NotReadyError(RuntimeError):
    """Levée quand on tente une analyse sur un ticker sans readiness=ready + context_pack."""


async def _load_ready_context(conn, ticker_id: str) -> dict[str, Any]:
    """Charge le dernier readiness `ready` + son context_pack. Lève NotReadyError sinon (le gate §7
    protège la dépense d'analyse : pas d'Opus/DeepSeek lourd sans base front-loadée)."""
    rep = await conn.fetchrow(
        """
        SELECT id, context_pack_entry_id FROM knowledge_curator_reports
        WHERE ticker_id = $1 AND report_type = 'readiness' AND verdict = 'ready'
              AND context_pack_entry_id IS NOT NULL
        ORDER BY created_at DESC LIMIT 1
        """,
        ticker_id,
    )
    if rep is None:
        raise NotReadyError(
            f"{ticker_id}: aucune readiness 'ready' avec context_pack — lance le curator (gate §7) d'abord."
        )
    pack = await conn.fetchrow(
        "SELECT id, content, content_structured FROM knowledge_entries WHERE id = $1",
        rep["context_pack_entry_id"],
    )
    return {
        "readiness_report_id": rep["id"],
        "context_pack_entry_id": rep["context_pack_entry_id"],
        "context_pack_md": pack["content"] if pack else "",
        "context_pack_data": pack["content_structured"] if pack else None,
    }


def _head(ctx: dict[str, Any], entries: list[dict[str, Any]]) -> str:
    """Bloc front-loadé commun (context_pack + entries courantes) — déterministe (cache §5.3)."""
    return (
        f"## Context pack (curator, front-load)\n{ctx['context_pack_md']}\n\n"
        f"## knowledge_entries courantes (cite par entry_id)\n{format_entries_for_prompt(entries)}"
    )


# ── persistance ──────────────────────────────────────────────────────────────
async def _persist_analysis(
    conn, *, ticker_id: str, analysis_type: str, result: dict[str, Any], agent: ResolvedAgent,
    tokens_in: int, tokens_out: int, cost: float, ctx: dict[str, Any],
    research_memo_id: Optional[int] = None, bull_analysis_id: Optional[int] = None,
    bear_analysis_id: Optional[int] = None, round_: int = 1, supersedes_id: Optional[int] = None,
    status: str = "draft",
) -> int:
    row = await conn.fetchrow(
        """
        INSERT INTO investment_analyses
            (ticker_id, analysis_type, result_json, result_json_original, context_pack_entry_id,
             research_memo_id, bull_analysis_id, bear_analysis_id, round, supersedes_id,
             provider_used, model_used, prompt_snapshot, tokens_in, tokens_out, cost_usd, status)
        VALUES ($1,$2,$3,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
        RETURNING id
        """,
        ticker_id, analysis_type, result, ctx.get("context_pack_entry_id"),
        research_memo_id, bull_analysis_id, bear_analysis_id, round_, supersedes_id,
        agent.provider.name, agent.model, agent.system_prompt, tokens_in, tokens_out, cost, status,
    )
    analysis_id = row["id"]
    refs = collect_refs(result)
    if refs:
        await snapshot_refs(conn, analysis_id=analysis_id, analysis_kind="analysis", refs=refs)
    return analysis_id


# ── research (base NEUTRE, §8.0) ─────────────────────────────────────────────
async def run_research(ticker_id: str) -> dict[str, Any]:
    """research-agent : research_memo NEUTRE (pas de verdict, Q2) depuis le context_pack ready."""
    async with get_db_session() as conn:
        ctx = await _load_ready_context(conn, ticker_id)
        entries = await get_current_entries(conn, ticker_id, limit=500)
        agent = await get_agent_provider("research-agent", "v2")
        msg = (
            f"{_head(ctx, entries)}\n\n---\n[mode: research]\nTicker : {ticker_id}\n"
            f"Produis le research_memo_json (contrat ResearchMemo) : base NEUTRE, aucun verdict/"
            f"recommandation (posture='NEUTRE'). Toute affirmation factuelle porte des source_entry_refs ; "
            f"toute prévision porte une ancre base_rate. Livre aussi les incertitudes bloquantes/"
            f"investissables."
        )
        run = await run_json_agent(agent, [{"role": "user", "content": msg}], ResearchMemo)
        row = await conn.fetchrow(
            """
            INSERT INTO research_memos
                (ticker_id, memo_json, memo_json_original, context_pack_entry_id, readiness_report_id,
                 provider_used, model_used, prompt_snapshot, tokens_in, tokens_out, cost_usd, status)
            VALUES ($1,$2,$2,$3,$4,$5,$6,$7,$8,$9,$10,'draft')
            RETURNING id
            """,
            ticker_id, run.data, ctx["context_pack_entry_id"], ctx["readiness_report_id"],
            agent.provider.name, agent.model, agent.system_prompt, run.tokens_in, run.tokens_out, run.cost_usd,
        )
        memo_id = row["id"]
        refs = collect_refs(run.data)
        if refs:
            await snapshot_refs(conn, analysis_id=memo_id, analysis_kind="research_memo", refs=refs)
        logger.info("research %s → memo #%s ($%.4f)", ticker_id, memo_id, run.cost_usd)
        return {"memo_id": memo_id, "memo_json": run.data, "cost_usd": run.cost_usd}


# ── bull / bear (contexte isolé, §8.1-8.2) ───────────────────────────────────
async def _run_case(ticker_id: str, research_memo_id: int, *, side: str) -> dict[str, Any]:
    schema = BullCase if side == "bull" else BearCase
    agent_name = "bull-agent" if side == "bull" else "bear-agent"
    async with get_db_session() as conn:
        ctx = await _load_ready_context(conn, ticker_id)
        entries = await get_current_entries(conn, ticker_id, limit=500)
        memo = await conn.fetchrow("SELECT memo_json FROM research_memos WHERE id = $1", research_memo_id)
        if memo is None:
            raise ValueError(f"research_memo {research_memo_id} introuvable")
        agent = await get_agent_provider(agent_name, "v2")
        # ISOLATION (Q3) : chaque cas est produit sans voir le cas adverse (voile levé au round A6).
        posture = ("le MEILLEUR cas POUR l'investissement" if side == "bull"
                   else "le MEILLEUR cas CONTRE (mandat de falsification A6)")
        msg = (
            f"{_head(ctx, entries)}\n\n## research_memo (base neutre)\n"
            f"{json.dumps(memo['memo_json'], ensure_ascii=False)}\n\n---\n[mode: {side}]\n"
            f"Ticker : {ticker_id}\nProduis {posture} — contrat {schema.__name__}, JSON strict. "
            f"variant_perception obligatoire (règle 6) ; chaque argument porte base_rate + "
            f"source_entry_refs ; indicateurs A3 séparés."
            + ("" if side == "bull" else
               " Ajoute failles_bull_conventionnel, scenario_destruction_valeur, conviction_negative. "
               "Laisse refutation_du_bull VIDE (rempli au round de réfutation).")
        )
        run = await run_json_agent(agent, [{"role": "user", "content": msg}], schema)
        aid = await _persist_analysis(
            conn, ticker_id=ticker_id, analysis_type=side, result=run.data, agent=agent,
            tokens_in=run.tokens_in, tokens_out=run.tokens_out, cost=run.cost_usd, ctx=ctx,
            research_memo_id=research_memo_id,
        )
        logger.info("%s %s → analysis #%s ($%.4f)", side, ticker_id, aid, run.cost_usd)
        return {"analysis_id": aid, "result_json": run.data, "cost_usd": run.cost_usd}


async def run_bull(ticker_id: str, research_memo_id: int) -> dict[str, Any]:
    return await _run_case(ticker_id, research_memo_id, side="bull")


async def run_bear(ticker_id: str, research_memo_id: int) -> dict[str, Any]:
    return await _run_case(ticker_id, research_memo_id, side="bear")


# ── réfutation A6 (asymétrique bear → bull, §8.3) ────────────────────────────
async def run_rebuttal(ticker_id: str, bull_analysis_id: int, bear_analysis_id: int) -> dict[str, Any]:
    """Une passe : le bear VOIT le bull et l'attaque argument par argument (refutation_du_bull).
    Produit une nouvelle version du bear (round 2) qui supersede la précédente (auditabilité)."""
    async with get_db_session() as conn:
        ctx = await _load_ready_context(conn, ticker_id)
        entries = await get_current_entries(conn, ticker_id, limit=500)
        bull = await conn.fetchrow("SELECT result_json FROM investment_analyses WHERE id = $1", bull_analysis_id)
        bear = await conn.fetchrow(
            "SELECT result_json, research_memo_id FROM investment_analyses WHERE id = $1", bear_analysis_id
        )
        if bull is None or bear is None:
            raise ValueError("bull/bear introuvable pour la réfutation")
        agent = await get_agent_provider("bear-agent", "v2")
        msg = (
            f"{_head(ctx, entries)}\n\n## Ton cas bear (round 1)\n"
            f"{json.dumps(bear['result_json'], ensure_ascii=False)}\n\n## Le cas BULL adverse (voile levé)\n"
            f"{json.dumps(bull['result_json'], ensure_ascii=False)}\n\n---\n[mode: rebuttal]\n"
            f"Attaque le bull argument par argument : renvoie ton bear_case_json COMPLET (contrat "
            f"BearCase) avec refutation_du_bull[] rempli (une passe, chaque item cible un argument bull "
            f"+ contre_argument + source_entry_refs). Ne modifie pas le reste sans raison."
        )
        run = await run_json_agent(agent, [{"role": "user", "content": msg}], BearCase)
        # marque l'ancien bear superseded, insère la v2 (round 2)
        await conn.execute(
            "UPDATE investment_analyses SET status='superseded', updated_at=NOW() WHERE id=$1",
            bear_analysis_id,
        )
        aid = await _persist_analysis(
            conn, ticker_id=ticker_id, analysis_type="bear", result=run.data, agent=agent,
            tokens_in=run.tokens_in, tokens_out=run.tokens_out, cost=run.cost_usd, ctx=ctx,
            research_memo_id=bear["research_memo_id"], round_=2, supersedes_id=bear_analysis_id,
        )
        logger.info("rebuttal %s → bear v2 #%s ($%.4f)", ticker_id, aid, run.cost_usd)
        return {"analysis_id": aid, "result_json": run.data, "cost_usd": run.cost_usd}


# ── synthèse (seul verdict, §8.4-8.5) ────────────────────────────────────────
async def run_synthesis(
    ticker_id: str, bull_analysis_id: int, bear_analysis_id: int, research_memo_id: int
) -> dict[str, Any]:
    """thesis-agent : bull+bear+réfutation → risk_matrix (SEUL verdict Q2) + hypotheses[]. Valide le
    pont risques↔hypothèses (§8.5)."""
    async with get_db_session() as conn:
        ctx = await _load_ready_context(conn, ticker_id)
        entries = await get_current_entries(conn, ticker_id, limit=500)
        bull = await conn.fetchrow("SELECT result_json FROM investment_analyses WHERE id = $1", bull_analysis_id)
        bear = await conn.fetchrow("SELECT result_json FROM investment_analyses WHERE id = $1", bear_analysis_id)
        memo = await conn.fetchrow("SELECT memo_json FROM research_memos WHERE id = $1", research_memo_id)
        if not (bull and bear and memo):
            raise ValueError("bull/bear/memo introuvable pour la synthèse")
        agent = await get_agent_provider("thesis-agent", "v2")
        msg = (
            f"{_head(ctx, entries)}\n\n## research_memo\n{json.dumps(memo['memo_json'], ensure_ascii=False)}\n\n"
            f"## bull\n{json.dumps(bull['result_json'], ensure_ascii=False)}\n\n"
            f"## bear (+ réfutation)\n{json.dumps(bear['result_json'], ensure_ascii=False)}\n\n---\n"
            f"[mode: synthesis]\nTicker : {ticker_id}\nProduis la synthèse : objet JSON "
            f"{{\"schema_version\":\"v2.0.0\",\"risk_matrix\":<RiskMatrix>,\"hypotheses\":[<Hypothese>]}}. "
            f"risk_matrix = le SEUL verdict du flux (Q2), 4 axes séparés (A3), risques_acceptes chacun "
            f"avec base_rate + hypothese_liee, pre_mortem ≥3, position_sizing (Kelly capé). Chaque risque "
            f"accepté a une hypothèse falsifiable correspondante (seuil_invalidation chiffré) dans "
            f"hypotheses[] — le champ hypothese_liee DOIT matcher un id d'hypothèse."
        )
        run = await run_json_agent(agent, [{"role": "user", "content": msg}], SynthesisOutput)
        run.parsed.valider_pont()  # type: ignore[attr-defined]  — pont risques↔hypothèses (§8.5)
        aid = await _persist_analysis(
            conn, ticker_id=ticker_id, analysis_type="synthesis", result=run.data, agent=agent,
            tokens_in=run.tokens_in, tokens_out=run.tokens_out, cost=run.cost_usd, ctx=ctx,
            research_memo_id=research_memo_id, bull_analysis_id=bull_analysis_id,
            bear_analysis_id=bear_analysis_id, status="final",
        )
        verdict = run.data["risk_matrix"]["verdict"]
        logger.info("synthesis %s → #%s verdict=%s ($%.4f)", ticker_id, aid, verdict, run.cost_usd)
        return {"analysis_id": aid, "result_json": run.data, "verdict": verdict, "cost_usd": run.cost_usd}
