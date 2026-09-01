"""
Debate-agent — le challenge de conviction (option C « Maintenir », §9-§11, lot 9, migration 032).

Quand un monitoring a soulevé un doute et que l'investisseur envisage de MAINTENIR, cet agent ne
re-décide pas : il soumet la conviction de maintien au test le plus dur (ancrage sur le prix
d'entrée, coût irrécupérable, aversion à matérialiser une perte) et rend une résolution SUGGÉRÉE.
L'utilisateur tranche — le débat éclaire, il n'ordonne pas.

Ce module tient trois choses que ni le contrat Pydantic ni la base ne peuvent tenir seuls.

1. LES SEUILS SONT REPRIS DE LA THÈSE FIGÉE, PAS DU MODÈLE (`_forcer_seuils_figes`). C'est LE point
   du lot 9. Le garde-fou anti-complaisance du contrat (`_anti_complaisance`) ne se déclenche que
   sur `seuil_franchi == "invalidation"` — mais `seuil_alerte`, `seuil_invalidation`, `valeur_observee`
   et `seuil_franchi` sont TOUS déclarés par le modèle. Un modèle qui recopie un seuil d'invalidation
   à 5 % là où la thèse dit 25 %, ou qui écrit `seuil_franchi='alerte'` sur une invalidation réelle,
   satisfait parfaitement le contrat ET DÉSARME le garde-fou : il peut alors conclure « maintenir
   avec conviction » sur une thèse cassée. C'est le trou H7 du lot 8, transposé au seul endroit du
   système où sa conséquence est de garder une position qu'il fallait vendre.
   Réparation : les deux seuils sont réécrits depuis `theses_v2.hypotheses` (lecture seule — un débat
   ne modifie jamais le seuil qu'il est en train de franchir), et `seuil_franchi` est DÉRIVÉ.

2. LA DIRECTION DU SEUIL SE DÉDUIT DE L'ORDRE DES DEUX SEUILS (`_deriver_franchissement`). La carte
   figée dit « la direction n'est pas recomputable » ; c'est vrai d'UN seuil isolé, faux dès qu'on a
   les deux. `seuil_invalidation < seuil_alerte` décrit une grandeur qu'on surveille À LA BAISSE
   (l'alerte se déclenche avant l'invalidation, donc plus haut) ; l'ordre inverse décrit une
   surveillance À LA HAUSSE. Vérifié sur les quatre hypothèses figées de la thèse MSFT #4, toutes en
   `invalidation < alerte`. Seul le cas dégénéré `seuil_alerte == seuil_invalidation` reste
   indécidable : là, et là seulement, on conserve la déclaration du modèle.

3. LE PONT RÉFÉRENTIEL ET LES CITATIONS (`_valider_pont_debat`). Une hypothèse « sous tension » qui
   n'existe pas dans la thèse figée est une tension inventée ; une `source_entry_refs` absente du
   contexte envoyé est un contre-argument fondé sur rien (A2).

Atomicité (convention #35) : l'appel modèle est fait HORS transaction ; l'écriture du débat et le
snapshot des refs sont ensuite atomiques.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from app.agents.providers import get_agent_provider
from app.agents.v2.common import format_entries_for_prompt
from app.agents.v2.runner import run_json_agent
from app.contracts import ConvictionChallenge
from app.db.database import get_db_session
from app.knowledge import collect_refs, get_current_entries, snapshot_refs

logger = logging.getLogger(__name__)

AGENT_NAME = "debate-agent"

# Statuts de clôture ouverts à l'utilisateur (la table accepte aussi 'open' et 'failed').
RESOLUTIONS = ("closed_pass", "closed_monitor", "closed_proceed")


class ThesisNotDebatable(RuntimeError):
    """On ne challenge la conviction que sur une thèse active : ailleurs il n'y a rien à maintenir."""


class DebateRefused(ValueError):
    """Sortie conforme au contrat mais incohérente avec la thèse figée, ou complaisante une fois les
    seuils rétablis. Se traduit en HTTP 422 ; le débat est persisté `failed` pour rester auditable."""


class DebateNotFound(LookupError):
    """Débat introuvable."""


# ── Chargement des intrants ──────────────────────────────────────────────────
async def _load_debate_inputs(conn, thesis_v2_id: int) -> dict[str, Any]:
    thesis = await conn.fetchrow("SELECT * FROM theses_v2 WHERE id = $1", thesis_v2_id)
    if thesis is None:
        raise LookupError(f"Thèse V2 #{thesis_v2_id} introuvable.")
    if thesis["status"] != "active":
        raise ThesisNotDebatable(
            f"Thèse V2 #{thesis_v2_id} au statut '{thesis['status']}' — le débat de conviction porte "
            "sur une décision de MAINTIEN, qui n'a de sens que sur une thèse active."
        )

    position = await conn.fetchrow(
        "SELECT * FROM portfolio_positions WHERE thesis_v2_id = $1 ORDER BY id LIMIT 1", thesis_v2_id
    )
    sessions = [
        dict(r) for r in await conn.fetch(
            "SELECT id, mode, alert_level, verdict, routing_suggestion, result_json, created_at "
            "FROM monitoring_sessions_v2 WHERE thesis_v2_id = $1 AND status = 'completed' "
            "ORDER BY id DESC LIMIT 10",
            thesis_v2_id,
        )
    ]
    entries = await get_current_entries(conn, thesis["ticker_id"], limit=500)
    return {
        "thesis": thesis,
        "hypotheses": list(thesis["hypotheses"] or []),
        "position": position,
        "sessions": sessions,
        "entries": entries,
    }


# ── Contexte ─────────────────────────────────────────────────────────────────
def _format_hypotheses(hypotheses: list[dict[str, Any]]) -> str:
    """Seuils figés donnés EN LECTURE. Ils sont dans le prompt pour que le modèle raisonne dessus —
    pas pour qu'il les redéclare : ce qu'il en redira sera de toute façon écrasé."""
    if not hypotheses:
        return "(aucune hypothèse figée — anomalie : une thèse active en porte toujours)"
    return "\n".join(
        f"- {h.get('id')} [statut courant : {h.get('statut', 'active')}] {h.get('enonce', '')}\n"
        f"    KPI {h.get('kpi', '?')} — seuil_alerte {h.get('seuil_alerte')}{h.get('unite') or ''} · "
        f"seuil_invalidation {h.get('seuil_invalidation')}{h.get('unite') or ''}"
        + (f"\n    dernière observation : {h['derniere_observation']}"
           if h.get("derniere_observation") else "")
        for h in hypotheses
    )


def _head(inputs: dict[str, Any]) -> str:
    t = inputs["thesis"]
    pos = inputs["position"]
    val = t["valuation_range"] or {}
    sessions = "\n".join(
        f"- session #{s['id']} (mode {s['mode']}, {str(s['created_at'])[:10]}) : "
        f"alerte={s['alert_level']} verdict={s['verdict']} routage={s['routing_suggestion']}"
        for s in inputs["sessions"]
    ) or "(aucune session de monitoring aboutie)"

    ancrage = (
        f"PRU {pos['purchase_price_eur']} € · {pos['shares']} titre(s) · entrée le {pos['purchase_date']}"
        if pos is not None else "(aucune position enregistrée)"
    )
    return (
        f"## Thèse V2 #{t['id']} — {t['ticker_id']} (figée au validate)\n"
        f"Verdict d'entrée : {t['verdict']} · sizing {t['position_sizing_pct']}% · "
        f"validée le {t['validated_at']}\n"
        f"Fourchette de valeur intrinsèque courante : low {val.get('low')} · base {val.get('base')} · "
        f"high {val.get('high')}\n"
        f"Position (c'est l'ancrage dont il faut se méfier, pas un argument) : {ancrage}\n\n"
        f"## Hypothèses figées et seuils PRÉ-ENREGISTRÉS (lecture seule)\n"
        f"{_format_hypotheses(inputs['hypotheses'])}\n\n"
        f"## Historique de suivi\n{sessions}\n\n"
        f"## knowledge_entries courantes (cite par entry_id — un contre-argument sans ref n'est pas "
        f"recevable)\n{format_entries_for_prompt(inputs['entries'])}"
    )


def _tache(inputs: dict[str, Any], motif: str) -> str:
    ids = ", ".join(str(h.get("id")) for h in inputs["hypotheses"]) or "(aucune)"
    return (
        f"Motif du débat : {motif or 'maintien envisagé après un doute soulevé par le suivi'}\n"
        f"Produis le challenge de conviction (contrat ConvictionChallenge). Tu n'es NI analyste NI "
        f"arbitre : tu stress-testes une conviction de MAINTIEN contre le biais de statu quo.\n"
        f"`hypotheses_sous_tension` ne cite que des hypothèses figées ({ids}), avec la "
        f"`valeur_observee` lue dans les entries et étayée par des `source_entry_refs` réelles. "
        f"Redonne les seuils tels qu'ils sont ci-dessus : le système les réécrira depuis la thèse "
        f"figée et RECALCULERA `seuil_franchi` — ne compte pas dessus pour adoucir un verdict.\n"
        f"`cas_contre_maintien` : le MEILLEUR cas contre, pas le plus commode ; chacun sourcé et "
        f"ancré par un `base_rate` dont la classe de référence est spécifique.\n"
        f"`biais_a_surveiller` : ceux qui jouent ICI (ancrage sur le prix d'entrée, coût "
        f"irrécupérable, aversion à matérialiser une perte). `cout_opportunite` : maintenir se juge "
        f"contre les alternatives, pas dans l'absolu.\n"
        f"`resolution_suggeree` est une SUGGESTION alignée sur les statuts de clôture "
        f"(closed_pass / closed_monitor / closed_proceed), jamais un ordre d'exécution : ni verdict "
        f"de synthèse, ni sizing. Sur une hypothèse dont le seuil d'INVALIDATION est franchi, "
        f"`closed_proceed` est interdit et `closed_monitor` exige `escalade_recommandee=true`."
    )


# ── Le cœur : rétablir les seuils figés et dériver le franchissement ─────────
def _deriver_franchissement(
    valeur: float, seuil_alerte: float, seuil_invalidation: float, declare: str
) -> str:
    """Déduit `seuil_franchi` de l'ORDRE des deux seuils figés face à la valeur observée.

    L'ordre encode la direction de surveillance : quand `seuil_invalidation < seuil_alerte`, la
    grandeur est surveillée à la BAISSE (on alerte avant d'invalider, donc plus haut) ; l'ordre
    inverse décrit une surveillance à la HAUSSE. Le cas `seuil_alerte == seuil_invalidation` ne
    porte aucune direction : on conserve alors la déclaration du modèle plutôt que d'inventer une
    convention qui trancherait à sa place.
    """
    if seuil_alerte == seuil_invalidation:
        return declare
    if seuil_invalidation < seuil_alerte:          # surveillance à la baisse
        if valeur <= seuil_invalidation:
            return "invalidation"
        return "alerte" if valeur <= seuil_alerte else "aucun"
    if valeur >= seuil_invalidation:               # surveillance à la hausse
        return "invalidation"
    return "alerte" if valeur >= seuil_alerte else "aucun"


def _forcer_seuils_figes(data: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
    """Réécrit seuils et franchissement AVANT validation (#24 + corollaire lecture seule de #37).

    Ce qui reste au modèle : quelle hypothèse est sous tension, quelle `valeur_observee` il lit dans
    les entries, et son raisonnement. Ce qui lui est retiré : la métrique qui ARME le garde-fou.
    Les divergences sont logguées en WARNING — un seuil redéclaré faux n'est pas anodin, c'est soit
    une perte de contexte, soit une complaisance, et les deux méritent une trace.
    """
    figees = {str(h.get("id")): h for h in inputs["hypotheses"] if h.get("id")}
    data["thesis_id"] = inputs["thesis"]["id"]
    data["schema_version"] = "v2.0.0"

    for h in data.get("hypotheses_sous_tension") or []:
        figee = figees.get(str(h.get("hypothese_id")))
        if figee is None:
            continue                     # hypothèse inventée : le pont référentiel la refusera
        for champ in ("seuil_alerte", "seuil_invalidation"):
            attendu = figee.get(champ)
            if attendu is None:
                continue
            rendu = h.get(champ)
            if rendu is not None and abs(float(rendu) - float(attendu)) > 1e-9:
                logger.warning(
                    "debate: %s.%s redéclaré par le modèle (%r) ≠ seuil figé au validate (%r) — "
                    "écrasé. C'est ce seuil-là qui arme l'anti-complaisance.",
                    h.get("hypothese_id"), champ, rendu, attendu)
            h[champ] = float(attendu)

        if h.get("valeur_observee") is not None:
            derive = _deriver_franchissement(
                float(h["valeur_observee"]), float(h["seuil_alerte"]),
                float(h["seuil_invalidation"]), str(h.get("seuil_franchi") or "aucun"),
            )
            if h.get("seuil_franchi") != derive:
                logger.warning(
                    "debate: %s seuil_franchi déclaré %r → dérivé %r (valeur %s vs alerte %s / "
                    "invalidation %s)", h.get("hypothese_id"), h.get("seuil_franchi"), derive,
                    h.get("valeur_observee"), h.get("seuil_alerte"), h.get("seuil_invalidation"))
            h["seuil_franchi"] = derive
    return data


def _valider_pont_debat(challenge: ConvictionChallenge, inputs: dict[str, Any]) -> None:
    """Référentiel des hypothèses + réalité des entries citées. Lève DebateRefused."""
    ids_figes = {str(h.get("id")) for h in inputs["hypotheses"] if h.get("id")}
    cites = {str(h.hypothese_id) for h in challenge.hypotheses_sous_tension}
    inventees = sorted(cites - ids_figes)
    if inventees:
        raise DebateRefused(
            f"Hypothèses inconnues de la thèse figée : {inventees} (figées : {sorted(ids_figes)}). "
            "Une « tension » sur une hypothèse qui n'a jamais été pré-enregistrée ne peut ni être "
            "vérifiée ni être franchie : elle échapperait au garde-fou anti-complaisance."
        )

    ids_entries = {e["id"] for e in inputs["entries"]}
    fantomes = sorted({r["entry_id"] for r in collect_refs(challenge.model_dump(mode="json"))}
                      - ids_entries)
    if fantomes:
        raise DebateRefused(
            f"source_entry_refs pointant des entries absentes du contexte envoyé : {fantomes}. "
            "Un contre-argument doit s'étayer sur une entry réellement fournie (A2) — sinon le "
            "snapshot est vide et le débat n'est opposable à rien."
        )


# ── L'acte ───────────────────────────────────────────────────────────────────
async def run_debate(
    thesis_v2_id: int, *, motif: str = "", monitoring_session_v2_id: Optional[int] = None,
) -> dict[str, Any]:
    """Produit le challenge de conviction et l'ouvre dans `conviction_debates_v2` (statut `open`).

    Le débat naît OUVERT : sa résolution est une suggestion, la clôture appartient à l'utilisateur
    (`close_debate`). Un débat qui se clôturerait lui-même serait un arbitre déguisé.
    """
    async with get_db_session() as conn:
        inputs = await _load_debate_inputs(conn, thesis_v2_id)

    thesis = inputs["thesis"]
    ticker_id = thesis["ticker_id"]
    # À défaut de session explicite, on rattache celle qui a routé vers le débat (mode 5).
    if monitoring_session_v2_id is None:
        monitoring_session_v2_id = next(
            (s["id"] for s in inputs["sessions"] if s["routing_suggestion"] == "debate"), None
        )

    contexte = f"{_head(inputs)}\n\n---\n[mode: debate]\n{_tache(inputs, motif)}"
    agent = await get_agent_provider(AGENT_NAME, "v2")

    # `json_object=False` : DeepSeek-V4-Flash est non fiable en mode json_object (mesuré 2026-08-26).
    try:
        run = await run_json_agent(
            agent, [{"role": "user", "content": contexte}], ConvictionChallenge,
            json_object=False, temperature=0.2,
        )
    except RuntimeError as e:
        # ⚠️ Comme partout en V2 : `run_json_agent` perd le brut et les tokens quand il abandonne.
        await _persister_echec(inputs, contexte, agent, str(e), monitoring_session_v2_id)
        raise

    try:
        data = _forcer_seuils_figes(dict(run.data), inputs)
        # Revalidation APRÈS rétablissement des seuils : c'est ICI que l'anti-complaisance du contrat
        # s'exerce pour de bon. Le premier passage l'avait évalué sur les seuils du modèle ; celui-ci
        # l'évalue sur les seuils figés. Un `closed_proceed` qui survivait au premier tombe au second.
        challenge = ConvictionChallenge.model_validate(data)
        _valider_pont_debat(challenge, inputs)
    except (DebateRefused, ValueError) as e:
        motif_echec = str(e)
        await _persister_echec(inputs, contexte, agent, motif_echec, monitoring_session_v2_id,
                               raw_content=run.raw_content, run=run)
        raise e if isinstance(e, DebateRefused) else DebateRefused(
            "Résolution incompatible avec les seuils FIGÉS de la thèse (le contrat, réévalué après "
            f"rétablissement des seuils, la refuse) : {motif_echec}"
        ) from e

    invalidation = any(h.seuil_franchi == "invalidation" for h in challenge.hypotheses_sous_tension)

    async with get_db_session() as conn:
        async with conn.transaction():
            debat = await conn.fetchrow(
                """
                INSERT INTO conviction_debates_v2
                    (thesis_v2_id, ticker_id, monitoring_session_v2_id, challenge_json, context_sent,
                     raw_content, resolution_suggeree, escalade_recommandee, invalidation_franchie,
                     status, provider_used, model_used, prompt_snapshot,
                     tokens_in, tokens_out, cost_usd)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,'open',$10,$11,$12,$13,$14,$15)
                RETURNING *
                """,
                thesis["id"], ticker_id, monitoring_session_v2_id, data, contexte, run.raw_content,
                challenge.resolution_suggeree, challenge.escalade_recommandee, invalidation,
                agent.provider.name, agent.model, agent.system_prompt,
                run.tokens_in, run.tokens_out, run.cost_usd,
            )
            refs = collect_refs(data)
            if refs:
                await snapshot_refs(conn, analysis_id=debat["id"], analysis_kind="debate", refs=refs)

    logger.info("debate: thèse #%s (%s) → débat #%s, suggestion=%s, invalidation=%s, escalade=%s, $%.4f",
                thesis["id"], ticker_id, debat["id"], challenge.resolution_suggeree, invalidation,
                challenge.escalade_recommandee, run.cost_usd)
    return {"debate": dict(debat), "result": data, "invalidation_franchie": invalidation}


async def close_debate(debate_id: int, resolution: str, note: str = "") -> dict[str, Any]:
    """Clôture par l'UTILISATEUR. Aucun appel modèle : c'est sa décision, pas celle de l'agent.

    La contrainte anti-complaisance de la migration 032 ne porte QUE sur `resolution_suggeree` :
    l'investisseur reste souverain, y compris pour maintenir contre l'avis du débat. Ce qu'on refuse,
    c'est qu'un AGENT rende ce maintien recommandable ; ce qu'on garantit ici, c'est que sa décision
    reste tracée à côté de la suggestion qu'elle contredit — c'est la matière du post-mortem.
    """
    if resolution not in RESOLUTIONS:
        raise ValueError(f"resolution doit être l'une de {RESOLUTIONS}.")
    async with get_db_session() as conn:
        row = await conn.fetchrow(
            "UPDATE conviction_debates_v2 SET status = $2, closure_note = $3, closed_at = NOW(), "
            "updated_at = NOW() WHERE id = $1 AND status = 'open' RETURNING *",
            debate_id, resolution, note,
        )
    if row is None:
        raise DebateNotFound(f"Débat #{debate_id} introuvable ou déjà clôturé.")

    if row["invalidation_franchie"] and resolution == "closed_proceed":
        logger.warning(
            "debate #%s clôturé en 'closed_proceed' alors qu'un seuil d'INVALIDATION est franchi "
            "(suggestion de l'agent : %s). Décision de l'utilisateur, tracée telle quelle.",
            debate_id, row["resolution_suggeree"])
    return dict(row)


async def _persister_echec(inputs, contexte, agent, motif, session_id, *, raw_content=None, run=None):
    """Trace un débat `failed`. Un refus silencieux effacerait la trace d'une complaisance détectée."""
    thesis = inputs["thesis"]
    try:
        async with get_db_session() as conn:
            await conn.execute(
                """
                INSERT INTO conviction_debates_v2
                    (thesis_v2_id, ticker_id, monitoring_session_v2_id, context_sent, raw_content,
                     status, provider_used, model_used, prompt_snapshot,
                     tokens_in, tokens_out, cost_usd)
                VALUES ($1,$2,$3,$4,$5,'failed',$6,$7,$8,$9,$10,$11)
                """,
                thesis["id"], thesis["ticker_id"], session_id, contexte,
                raw_content or f"[échec sans sortie exploitable] {motif}",
                agent.provider.name, agent.model, agent.system_prompt,
                getattr(run, "tokens_in", 0) or 0, getattr(run, "tokens_out", 0) or 0,
                getattr(run, "cost_usd", 0) or 0,
            )
    except Exception:  # noqa: BLE001 — journaliser l'échec ne doit jamais masquer l'échec initial
        logger.exception("debate: échec de la trace d'échec (thèse #%s)", thesis["id"])
