"""
knowledge-curator (V2) — le GATE GO/NO-GO. Produit `readiness_report_json` (§7) et, seulement si
`ready`, le `context_pack` front-loadé (§5.3). C'est le péage AVANT toute dépense Opus/DeepSeek lourde.

Discipline de déterminisme (readiness = « derived, cheap ») : le LLM ne sert qu'au JUGEMENT sémantique
de couverture (quels champs la KB fonde, gaps, rationale) ; le code RECOMPUTE tout ce qui est
arithmétique — `entries_par_tier` (SQL), `ok`/`bloc_ok` (dérivés de champs_non_fondables), `verdict`
(compute_verdict) — et Pydantic verrouille la cohérence (bijection gaps↔manques, ready⇒context_pack).

Le contexte (préambule + rôle) est figé en tête (cache) ; les entries + la tâche du tour en fin.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.agents.providers import ResolvedAgent, get_agent_provider
from app.agents.v2.common import MVDD_SPEC, count_tiers, format_entries_for_prompt
from app.agents.v2.runner import extract_json
from app.contracts import ContextPack, ReadinessReport
from app.db.database import get_db_session
from app.knowledge import get_current_entries, store_knowledge

logger = logging.getLogger(__name__)


def _readiness_task_message(ticker_id: str, entries: list[dict[str, Any]]) -> str:
    spec = json.dumps(MVDD_SPEC, ensure_ascii=False, indent=2)
    listing = format_entries_for_prompt(entries)
    return (
        f"[mode: readiness]\n\n"
        f"Ticker : {ticker_id}\n\n"
        f"Cadre MVDD (8 dimensions, 2 blocs jamais fusionnés — champs requis & tier plancher indicatifs) :\n"
        f"{spec}\n\n"
        f"knowledge_entries COURANTES de la KB ({len(entries)}) — cite-les par entry_id :\n"
        f"{listing}\n\n"
        f"Produis le readiness_report_json (contrat ReadinessReport, JSON strict). Pour chaque "
        f"dimension : liste les champs_non_fondables (aucune entry au tier plancher ne les fonde), le "
        f"tier_atteint, et ok=(champs_non_fondables vide). Émets un gap par champ non fondable "
        f"(bijection stricte). conviction/marge_securite = null. Ne mets pas context_pack_entry_id "
        f"(assigné par le backend). Le verdict sera recalculé par le backend depuis ta couverture."
    )


def _apply_deterministic_overrides(report: dict[str, Any], entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Recompute en Python ce qui est dérivé (comptes, ok/bloc_ok, verdict) — jamais confié au LLM."""
    report["entries_par_tier"] = count_tiers(entries)

    coverage = report.get("coverage") or {}
    for bloc_name in ("structuree", "qualitative_marche"):
        bloc = coverage.get(bloc_name) or {}
        dims = bloc.get("dimensions") or []
        for d in dims:
            d["ok"] = len(d.get("champs_non_fondables") or []) == 0
        bloc["bloc_ok"] = bool(dims) and all(d["ok"] for d in dims)
        bloc["dimensions"] = dims
        coverage[bloc_name] = bloc
    report["coverage"] = coverage

    # A3 : pas de conviction/marge_securite au readiness
    ind = report.get("indicateurs") or {}
    ind["conviction"] = None
    ind["marge_securite"] = None
    report["indicateurs"] = ind

    # verdict CONTRAINT (G2) sauf décisions non dérivées (too_hard/researching gardés du LLM).
    # Même règle que compute_verdict, appliquée aux booléens recalculés (défense en profondeur :
    # le verdict validé par Pydantic sera de toute façon revérifié contre compute_verdict).
    if report.get("verdict") not in ("too_hard", "researching"):
        s_ok = coverage["structuree"]["bloc_ok"]
        q_ok = coverage["qualitative_marche"]["bloc_ok"]
        report["verdict"] = "ready" if (s_ok and q_ok) else ("thin_qualitative" if s_ok else "not_ready")
    return report


async def _call_json(agent: ResolvedAgent, task_message: str, *, max_repair: int = 1) -> tuple[dict, int, int, float]:
    """Appel JSON strict + extraction, avec réparation légère (retourne dict + tokens/coût cumulés)."""
    convo: list[dict[str, Any]] = [{"role": "user", "content": task_message}]
    t_in = t_out = 0
    cost = 0.0
    last_err: Optional[str] = None
    for attempt in range(max_repair + 1):
        res = await agent.complete(convo, response_format={"type": "json_object"}, temperature=0.2)
        t_in += res.tokens_in
        t_out += res.tokens_out
        cost += res.cost_usd
        try:
            return extract_json(res.content), t_in, t_out, cost
        except json.JSONDecodeError as e:
            last_err = str(e)
            convo += [
                {"role": "assistant", "content": res.content},
                {"role": "user", "content": "Sortie non-JSON. Renvoie UNIQUEMENT l'objet JSON du contrat."},
            ]
    raise RuntimeError(f"curator: JSON illisible après réparation ({last_err})")


async def run_readiness(ticker_id: str) -> dict[str, Any]:
    """Exécute le mode readiness pour un ticker. Persiste dans knowledge_curator_reports.
    Renvoie {report_id, verdict, report_json, context_pack_entry_id}."""
    async with get_db_session() as conn:
        entries = await get_current_entries(conn, ticker_id, min_reliability=0.0, limit=500)
        agent = await get_agent_provider("knowledge-curator", "v2")

        raw, t_in, t_out, cost = await _call_json(agent, _readiness_task_message(ticker_id, entries))
        raw.pop("context_pack_entry_id", None)
        report = _apply_deterministic_overrides(raw, entries)

        context_pack_entry_id: Optional[int] = None

        # validation avec réparation Pydantic (une passe) ------------------------------------------
        validated = _validate_or_repair_readiness(report)

        # Si ready : produire + persister le context_pack, puis re-figer l'id et re-valider.
        if validated.verdict == "ready":
            context_pack_entry_id = await _produce_context_pack(conn, agent, ticker_id, entries)
            report["context_pack_entry_id"] = context_pack_entry_id
            validated = ReadinessReport.model_validate(report)

        data = validated.model_dump(mode="json")
        row = await conn.fetchrow(
            """
            INSERT INTO knowledge_curator_reports
                (ticker_id, report_type, report_json, verdict,
                 coverage_structuree, coverage_qualitative, context_pack_entry_id)
            VALUES ($1,'readiness',$2,$3,$4,$5,$6)
            RETURNING id
            """,
            ticker_id, data, data["verdict"],
            data["coverage"]["structuree"], data["coverage"]["qualitative_marche"],
            context_pack_entry_id,
        )
        logger.info("curator.readiness %s → %s (report #%s, %d tok_out, $%.4f)",
                    ticker_id, data["verdict"], row["id"], t_out, cost)
        return {
            "report_id": row["id"],
            "verdict": data["verdict"],
            "report_json": data,
            "context_pack_entry_id": context_pack_entry_id,
            "cost_usd": cost,
        }


def _validate_or_repair_readiness(report: dict[str, Any]) -> ReadinessReport:
    """Valide le ReadinessReport ; en cas d'échec on lève une erreur claire (les incohérences de
    couverture LLM sont rares après overrides déterministes ; l'appelant peut relancer run_readiness)."""
    try:
        return ReadinessReport.model_validate(report)
    except Exception as e:  # noqa: BLE001
        logger.error("curator.readiness: ReadinessReport invalide: %s", e)
        raise RuntimeError(f"curator: readiness non conforme au contrat — {e}") from e


async def _produce_context_pack(
    conn, agent: ResolvedAgent, ticker_id: str, entries: list[dict[str, Any]]
) -> int:
    """Génère le context_pack (ready-only), le valide (ContextPack) et le persiste comme
    knowledge_entry source_type='agent_synthesis'. Renvoie l'entry_id."""
    listing = format_entries_for_prompt(entries)
    msg = (
        f"[mode: context_pack]\n\nTicker : {ticker_id}\n\n"
        f"Le readiness est READY. Distille l'état des connaissances en un context_pack (contrat "
        f"ContextPack, JSON strict) : EXACTEMENT les 8 dimensions MVDD dans l'ordre canonique "
        f"(structuree: business_model, financials, valorisation ; puis qualitative_marche: produits, "
        f"positionnement, marche, management_allocation, risques). Chaque dimension : synthèse Markdown "
        f"condensée + tier_atteint + source_entry_refs NON VIDES (triées par entry_id puis version). "
        f"readiness_verdict='ready'. Aucun champ volatil.\n\nknowledge_entries :\n{listing}"
    )
    raw, *_ = await _call_json(agent, msg)
    raw.setdefault("schema_version", "v2.0.0")
    raw["ticker_id"] = ticker_id
    raw["readiness_verdict"] = "ready"
    raw.setdefault("readiness_report_id", 0)  # rétro-rempli après insertion du report si besoin
    pack = ContextPack.model_validate(raw)
    data = pack.model_dump(mode="json")

    synthese_md = "\n\n".join(
        f"### {d['bloc']} · {d['dimension']} ({d['tier_atteint']})\n{d['synthese']}"
        for d in data["dimensions"]
    )
    stored = await store_knowledge(
        conn,
        ticker_id=ticker_id,
        entry_type="agent_synthesis",
        content=f"# Context pack {ticker_id} (curator, ready)\n\n{synthese_md}",
        content_structured=data,
        source_type="agent_synthesis",
        title=f"Context pack — {ticker_id}",
        tags=["context_pack", "curator"],
    )
    return stored["id"]
