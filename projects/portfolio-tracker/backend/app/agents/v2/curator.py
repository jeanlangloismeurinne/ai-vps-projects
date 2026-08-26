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
from app.agents.v2.common import MVDD_SPEC, TIER_ORDER, count_tiers, format_entries_for_prompt
from app.agents.v2.runner import extract_json
from app.contracts import ContextPack, ReadinessReport
from app.db.database import get_db_session
from app.knowledge import get_current_entries, store_knowledge

logger = logging.getLogger(__name__)

_TIER_RANK = {t: i for i, t in enumerate(TIER_ORDER)}  # 0 = meilleur (A) … plus grand = plus faible

# Plancher PAR CHAMP (option C + dégradé Q1) : par défaut le plancher de la dimension (MVDD) ; on
# ABAISSE explicitement les champs dont aucune source primaire tier A n'existe. `croissance_marche_
# historique` = taille d'un marché tiers → au mieux une estimation de presse/cabinet (jamais tier A) ;
# plancher B, exception DÉCLARÉE (pas un compromis caché — l'entry porte son vrai tier + revue humaine).
FIELD_PLANCHER_OVERRIDES: dict[str, str] = {
    "marche.croissance_marche_historique": "B",
}


def _plancher_for(dimension: str, champ: str, dim_plancher: str) -> str:
    return FIELD_PLANCHER_OVERRIDES.get(f"{dimension}.{champ}", dim_plancher)


def _tier_ge(tier: Optional[str], plancher: str) -> bool:
    """tier ≥ plancher (A=meilleur). tier inconnu/None ne satisfait jamais un plancher."""
    if tier not in _TIER_RANK:
        return False
    return _TIER_RANK[tier] <= _TIER_RANK.get(plancher, len(TIER_ORDER))


def _best_tier(tiers: list[str]) -> Optional[str]:
    valides = [t for t in tiers if t in _TIER_RANK]
    return min(valides, key=lambda t: _TIER_RANK[t]) if valides else None


def recompute_coverage(coverage: dict[str, Any], entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Option C — recompute déterministe de la couverture par dimension.

    Le LLM a PROPOSÉ, par champ requis fondé, les `entry_ids` qui le fondent (`fondations`). Ici le
    backend DISPOSE : pour chaque champ, il ne le tient pour fondé QUE si ≥1 entry citée existe en
    base à un tier RÉEL ≥ plancher DU CHAMP (dimension, sauf override). Le LLM ne peut donc plus faire
    passer un champ sous-doté (bug observé : #54 tier B compté pour un champ B+). Pur, sans IO.
    """
    tier_by_id = {e["id"]: e.get("reliability_tier") for e in entries}
    for bloc_name in ("structuree", "qualitative_marche"):
        bloc = coverage.get(bloc_name) or {}
        for d in bloc.get("dimensions") or []:
            if not isinstance(d, dict):
                continue
            dim = d.get("dimension")
            dim_plancher = d.get("tier_plancher")
            requis = d.get("champs_requis") or []
            # La sortie LLM est NON fiable (#24) : `fondations` peut arriver malformée (liste de
            # chaînes, ids non entiers…). On parse défensivement — jamais de crash sur la forme du
            # modèle ; un élément malformé = champ simplement non fondé.
            fond: dict[str, list[int]] = {}
            for g in d.get("fondations") or []:
                if not isinstance(g, dict):
                    continue
                champ = g.get("champ")
                ids = g.get("entry_ids")
                if isinstance(champ, str) and isinstance(ids, list):
                    fond[champ] = [i for i in ids if isinstance(i, int)]
            non_fondables: list[str] = []
            all_cited_tiers: list[str] = []
            for champ in requis:
                plancher = _plancher_for(dim, champ, dim_plancher)
                ids = fond.get(champ) or []
                real = [tier_by_id[i] for i in ids if tier_by_id.get(i)]
                all_cited_tiers.extend(real)
                if not any(_tier_ge(t, plancher) for t in real):
                    non_fondables.append(champ)
            d["champs_non_fondables"] = non_fondables
            d["tier_atteint"] = _best_tier(all_cited_tiers)
            d["ok"] = len(non_fondables) == 0
        bloc["bloc_ok"] = bool(bloc.get("dimensions")) and all(x["ok"] for x in bloc["dimensions"])
        coverage[bloc_name] = bloc
    return coverage


def reconcile_gaps(report: dict[str, Any], coverage: dict[str, Any]) -> dict[str, Any]:
    """Rebâtit `gaps` pour la bijection stricte champs_non_fondables ↔ gaps (contrat) après recompute :
    on garde les gaps LLM en rabotant leurs `champs_cibles` aux non-fondables recalculés, on jette
    ceux devenus vides, et on synthétise un gap pour tout champ non fondable resté sans gap. Pur."""
    dims = {d["dimension"]: d
            for b in (coverage["structuree"], coverage["qualitative_marche"])
            for d in b["dimensions"]}
    kept: list[dict[str, Any]] = []
    covered: dict[str, set[str]] = {}
    for g in report.get("gaps") or []:
        if not isinstance(g, dict):
            continue
        dim = g.get("dimension")
        if dim not in dims:
            continue
        nf = set(dims[dim]["champs_non_fondables"])
        cibles = [c for c in (g.get("champs_cibles") or []) if c in nf]
        if not cibles:
            continue
        g["champs_cibles"] = cibles
        kept.append(g)
        covered.setdefault(dim, set()).update(cibles)
    for dim, d in dims.items():
        manquants = [c for c in d["champs_non_fondables"] if c not in covered.get(dim, set())]
        if manquants:
            kept.append({
                "dimension": dim,
                "champs_cibles": manquants,
                "manque": f"Aucune entry au tier plancher ne fonde : {', '.join(manquants)}.",
                "queries_suggerees": [],
                "priorite": "moyenne",
                "coverage_actuelle": d.get("tier_atteint") or "aucune",
                "origine": "curator",
            })
    report["gaps"] = kept
    return report


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
        f"Produis le readiness_report_json (contrat ReadinessReport, JSON strict). Pour CHAQUE "
        f"dimension, remplis `fondations` EXACTEMENT sous cette forme (liste d'objets, jamais de "
        f'chaînes) : "fondations": [{{"champ": "roic_pct", "entry_ids": [50, 52]}}, '
        f'{{"champ": "levier", "entry_ids": [49]}}] — un objet par champ requis que la KB fonde, avec '
        f"les `entry_ids` (#id du listing) qui le fondent ; cite UNIQUEMENT des entries réelles du "
        f"listing, celles qui portent VRAIMENT ce champ. Le backend VÉRIFIE ensuite en Python que "
        f"chaque entry citée existe à un tier ≥ plancher du champ, et en DÉRIVE champs_non_fondables, "
        f"tier_atteint, ok, les gaps et le verdict — ne triche pas sur le tier, tu ne peux pas faire "
        f"passer un champ sous-doté. Émets quand même un gap par champ que tu sais non fondé, "
        f"conviction/marge_securite = null, et ne mets pas context_pack_entry_id (backend)."
    )


def _apply_deterministic_overrides(report: dict[str, Any], entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Recompute en Python ce qui est dérivé (comptes, couverture, gaps, ok/bloc_ok, verdict) — jamais
    confié au LLM. Option C : la couverture par champ est recalculée depuis les tiers RÉELS des entries
    citées dans `fondations` vs le plancher par champ (recompute_coverage), puis les gaps sont
    reconciliés pour tenir la bijection du contrat (reconcile_gaps)."""
    report["entries_par_tier"] = count_tiers(entries)

    coverage = recompute_coverage(report.get("coverage") or {}, entries)
    report["coverage"] = coverage
    reconcile_gaps(report, coverage)

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
    """Appel JSON + extraction, avec réparation légère (retourne dict + tokens/coût cumulés).

    ⚠️ PAS de response_format=json_object : mesuré 2026-08-26, DeepSeek-V4-Flash y est NON FIABLE (il
    collapse sur `{}` ou emballe la sortie dans une clé parasite `{"/mnt/data/…json": "<json échappé>"}`
    — cette 2ᵉ pathologie a fait échouer la 1ère production réelle du context_pack). En prompt-only +
    extract_json, le JSON sort propre. Même correctif que run_json_agent(json_object=False)."""
    convo: list[dict[str, Any]] = [{"role": "user", "content": task_message}]
    t_in = t_out = 0
    cost = 0.0
    last_err: Optional[str] = None
    for attempt in range(max_repair + 1):
        res = await agent.complete(convo, temperature=0.2)
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

        # Si le verdict recomputé est `ready`, produire le context_pack AVANT la validation : le
        # contrat ReadinessReport exige `context_pack_entry_id` dès que verdict=ready, donc valider
        # d'abord échouerait (bug jamais atteint tant qu'aucun ticker n'était `ready` — le 1er ready
        # réel l'a révélé, 2026-08-26). On se fie au verdict déterministe (compute_verdict), pas au LLM.
        if report.get("verdict") == "ready":
            context_pack_entry_id = await _produce_context_pack(conn, agent, ticker_id, entries)
            report["context_pack_entry_id"] = context_pack_entry_id

        # validation avec réparation Pydantic (une passe) ------------------------------------------
        validated = _validate_or_repair_readiness(report)

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
