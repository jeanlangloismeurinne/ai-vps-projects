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

# Champs requis GÉNUINEMENT introuvables (aucune source accessible à aucun tier — ni KB, ni web même
# dégradé, ni synthèse) : ils NE bloquent PAS `ready` mais sont portés comme LACUNE DÉCLARÉE
# (incertitude investissable « non quantifiée »). Décision méthodo 2026-08-26 : mieux vaut une thèse
# ready avec un trou VISIBLE et assumé qu'un blocage indéfini sur une donnée qui n'existe pas.
DECLARED_NONBLOCKING_GAPS: dict[str, str] = {
    "marche.croissance_marche_historique":
        "Croissance historique du marché des accélérateurs IA — non quantifiée (aucune source "
        "primaire/presse accessible à un tier suffisant). Lacune déclarée, non bloquante.",
    "business_model.recurrence_pct":
        "Part des revenus récurrents (logiciels/abonnements) — non chiffrée dans les sources "
        "primaires disponibles. NVIDIA est un business hardware-dominant (quasi-totalité du CA "
        "= vente de GPU/plateformes, one-time) ; NVIDIA AI Enterprise est en croissance mais sa "
        "contribution relative n'est pas disclosée séparément à un tier accessible. "
        "Lacune déclarée, non bloquante.",
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


_MVDD_BY_DIM = {s["dimension"]: s for s in MVDD_SPEC}


def _exigences(dimension: Optional[str], d: dict[str, Any]) -> tuple[list[str], str]:
    """Champs requis + tier plancher d'une dimension : le LLM peut RESSERRER, jamais DESSERRER.

    Le cadre MVDD est le plancher d'exigence (`common.MVDD_SPEC`) ; l'agent peut l'affiner au cas
    d'espèce — ajouter un champ requis, relever le plancher. Mais une fois la couverture pilotée par
    l'index, `champs_requis` et `tier_plancher` sont le DERNIER levier du modèle sur le verdict :
    retirer `recurrence_pct` des requis, ou passer un plancher de A à B, ferait passer la dimension
    sans qu'aucune entry ne bouge. On prend donc l'union des champs et le plus STRICT des planchers.
    """
    spec = _MVDD_BY_DIM.get(dimension or "", {})
    socle: list[str] = list(spec.get("champs_requis") or [])
    proposes = [c for c in (d.get("champs_requis") or []) if isinstance(c, str)]
    requis = socle + sorted(set(proposes) - set(socle))   # ordre stable : socle MVDD, puis ajouts

    candidats = [t for t in (spec.get("tier_plancher"), d.get("tier_plancher")) if t in _TIER_RANK]
    plancher = min(candidats, key=lambda t: _TIER_RANK[t]) if candidats else "B"
    return (requis or ["description"]), plancher


def _covers_index(entries: list[dict[str, Any]]) -> dict[str, list[tuple[int, str]]]:
    """`dimension.champ` → [(entry_id, tier)] — l'INDEX de couverture, bâti depuis la BASE.

    Une entry annonce ses champs via `covers` (chemins complets, migration 029), écrit par les
    chemins déterministes (feeds, mandat du worker, backfill relu). Trié par id pour un rapport
    stable. Tolérant à la forme : une entry pré-029 peut encore porter une chaîne nue.
    """
    index: dict[str, list[tuple[int, str]]] = {}
    for e in sorted(entries, key=lambda x: x["id"]):
        covers = e.get("covers")
        if isinstance(covers, str):          # tolérance pré-029 (colonne encore TEXT)
            covers = [covers]
        tier = e.get("reliability_tier")
        for path in covers or []:
            if isinstance(path, str) and tier:
                index.setdefault(path, []).append((e["id"], tier))
    return index


def recompute_coverage(coverage: dict[str, Any], entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Recompute déterministe de la couverture — depuis l'INDEX `covers`, pas depuis le LLM (029).

    Chaque champ requis est fondé si et seulement si la BASE contient ≥1 entry courante qui le PORTE
    (`covers` contient `dimension.champ`) à un tier RÉEL ≥ plancher DU CHAMP. Le LLM n'intervient plus
    du tout : ni pour proposer, ni pour omettre.

    Ce que ça corrige (mesuré sur NVDA, corpus STRICTEMENT figé) : l'ancienne version filtrait les
    `entry_ids` que le LLM avait CITÉS — un véto sur la citation, pas un index. Elle fermait le trou
    de SUR-crédit (entry hors-sujet) mais pas celui de SOUS-crédit : une entry adéquate NON citée
    créait un faux creux, et le rattachement par-champ n'étant pas déterministe, le verdict oscillait
    `not_ready` ↔ `thin_qualitative` sur des données identiques (rapports #11/#13/#14).

    `fondations` est RÉÉCRIT depuis l'index : le rapport montre ce qui fonde réellement chaque champ,
    et non ce que le modèle a bien voulu citer. Pur, sans IO.
    """
    index = _covers_index(entries)
    for bloc_name in ("structuree", "qualitative_marche"):
        bloc = coverage.get(bloc_name) or {}
        for d in bloc.get("dimensions") or []:
            if not isinstance(d, dict):
                continue
            dim = d.get("dimension")
            requis, dim_plancher = _exigences(dim, d)
            d["champs_requis"] = requis
            d["tier_plancher"] = dim_plancher
            non_fondables: list[str] = []
            fondations: list[dict[str, Any]] = []
            tiers_retenus: list[str] = []
            for champ in requis:
                # Lacune déclarée non-bloquante : ni fondée, ni comptée comme manque (portée en
                # incertitude investissable par _apply_deterministic_overrides).
                if f"{dim}.{champ}" in DECLARED_NONBLOCKING_GAPS:
                    continue
                plancher = _plancher_for(dim, champ, dim_plancher)
                # Seules comptent les entries qui PORTENT le champ ET tiennent son plancher. Une
                # entry sous plancher n'est pas une fondation partielle : elle ne compte pas du tout.
                retenues = [(i, t) for i, t in index.get(f"{dim}.{champ}", [])
                            if _tier_ge(t, plancher)]
                if retenues:
                    fondations.append({"champ": champ, "entry_ids": [i for i, _ in retenues]})
                    tiers_retenus.extend(t for _, t in retenues)
                else:
                    non_fondables.append(champ)
            d["fondations"] = fondations
            d["champs_non_fondables"] = non_fondables
            # tier_atteint = le meilleur tier parmi ce qui fonde VRAIMENT la dimension (une entry
            # écartée ne peut pas rehausser le tier affiché : ce serait un tier de façade).
            d["tier_atteint"] = _best_tier(tiers_retenus)
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
        f"Produis le readiness_report_json (contrat ReadinessReport, JSON strict).\n\n"
        f"⚠️ La COUVERTURE ne t'appartient pas. Le backend la recompute en Python depuis l'index "
        f"`covers` de la base (quelles entries portent quel champ, à quel tier réel) : `fondations`, "
        f"`champs_non_fondables`, `tier_atteint`, `ok`, `bloc_ok`, les gaps et le verdict sont "
        f"DÉRIVÉS et écraseront ce que tu écris. Tu ne peux ni faire passer un champ, ni en creuser "
        f"un : laisse `fondations` à [] et ne cherche pas à deviner ce qui est fondé.\n\n"
        f"Ce qui est VRAIMENT attendu de toi, et que le code ne sait pas produire : le `rationale` "
        f"(lecture d'ensemble du dossier), les `gaps` (ce qui manque, avec des `queries_suggerees` "
        f"actionnables), les `incertitudes_investissables` et `qualite_info`. Reprends les 8 "
        f"dimensions du cadre MVDD ci-dessus avec leurs `champs_requis` et `tier_plancher` (tu peux "
        f"les RESSERRER si le cas d'espèce l'exige — ajouter un champ requis, relever un plancher — "
        f"jamais les assouplir). conviction/marge_securite = null, pas de context_pack_entry_id."
    )


def _declare_nonblocking_gaps(report: dict[str, Any], coverage: dict[str, Any]) -> dict[str, Any]:
    """Porte chaque lacune déclarée (champ requis introuvable, non bloquant) comme incertitude
    investissable VISIBLE — jamais un trou caché. Dedup par question. Pur."""
    requis_par_dim = {d["dimension"]: set(d.get("champs_requis") or [])
                      for b in (coverage["structuree"], coverage["qualitative_marche"])
                      for d in b["dimensions"]}
    existantes = {u.get("question") for u in (report.get("incertitudes_investissables") or [])}
    ajouts: list[dict[str, str]] = []
    for full, libelle in DECLARED_NONBLOCKING_GAPS.items():
        dim, champ = full.split(".", 1)
        if champ in requis_par_dim.get(dim, set()) and libelle not in existantes:
            ajouts.append({"question": libelle, "fourchette": "non quantifiée — source indisponible"})
    if ajouts:
        report["incertitudes_investissables"] = (report.get("incertitudes_investissables") or []) + ajouts
    return report


def _apply_deterministic_overrides(report: dict[str, Any], entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Recompute en Python ce qui est dérivé (comptes, couverture, gaps, ok/bloc_ok, verdict) — jamais
    confié au LLM. La couverture par champ est recalculée depuis l'INDEX `covers` de la base
    (recompute_coverage, 029), puis les gaps sont reconciliés pour tenir la bijection du contrat
    (reconcile_gaps). Le verdict devient donc une FONCTION du corpus : à corpus figé, il ne bouge plus."""
    report["entries_par_tier"] = count_tiers(entries)

    coverage = recompute_coverage(report.get("coverage") or {}, entries)
    report["coverage"] = coverage
    reconcile_gaps(report, coverage)
    _declare_nonblocking_gaps(report, coverage)

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
    raw["readiness_report_id"] = raw.get("readiness_report_id") or 0  # rétro-rempli après insertion du report si besoin
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
