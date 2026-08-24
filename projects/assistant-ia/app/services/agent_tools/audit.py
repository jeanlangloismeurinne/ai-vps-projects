"""Écriture de la piste d'audit `agent_tool_calls` (#1787579840504, roadmap §5).

Règle qui gouverne tout ce module : **un échec d'écriture d'audit ne doit jamais faire perdre la
réponse à l'utilisateur.** Toutes les fonctions sont best-effort + `logger.exception`, comme
`ensure_vault()` après le correctif de #1787559677486. La conséquence assumée : une ligne d'audit
peut manquer si la base est indisponible — mais l'agent, lui, répond.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.db import get_pool

logger = logging.getLogger(__name__)

# Plafond du résultat conservé en base. Aligné sur le plafond de réinjection (roadmap §3.5) :
# l'audit doit permettre de comprendre ce que le modèle a vu, pas d'archiver le web.
RESULT_EXCERPT_MAX = 2000


def _excerpt(value: Any) -> str | None:
    if value is None:
        return None
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    if len(text) <= RESULT_EXCERPT_MAX:
        return text
    return text[:RESULT_EXCERPT_MAX] + f"… (tronqué, {len(text)} car.)"


async def record_call(
    *,
    tool_name: str,
    arguments: dict[str, Any],
    verdict: str,
    verdict_reason: str = "",
    resolved_payload: dict[str, Any] | None = None,
    result: Any = None,
    channel_id: str | None = None,
    slack_ts: str | None = None,
    thread_ts: str | None = None,
    user_id: str | None = None,
    doc_version: int | None = None,
    taint_sources: list[str] | None = None,
    user_confirmed: bool = False,
) -> str | None:
    """Journalise un appel d'outil. Renvoie l'id de la ligne, ou None si l'écriture a échoué.

    L'id sert de jeton pour les confirmations : il voyage dans la `value` du bouton Slack, ce qui
    fait de la ligne d'audit *elle-même* l'objet en attente — pas de seconde table à tenir
    cohérente avec celle-ci.
    """
    try:
        pool = await get_pool()
        row = await pool.fetchrow(
            "INSERT INTO agent_tool_calls "
            "(tool_name, arguments, resolved_payload, verdict, verdict_reason, result_excerpt, "
            " channel_id, slack_ts, thread_ts, user_id, doc_version, taint_sources, user_confirmed) "
            "VALUES ($1, $2::jsonb, $3::jsonb, $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb, $13) "
            "RETURNING id",
            tool_name,
            json.dumps(arguments or {}, ensure_ascii=False, default=str),
            json.dumps(resolved_payload, ensure_ascii=False, default=str) if resolved_payload else None,
            verdict,
            verdict_reason or None,
            _excerpt(result),
            channel_id, slack_ts, thread_ts, user_id, doc_version,
            json.dumps(taint_sources or [], ensure_ascii=False),
            user_confirmed,
        )
        return str(row["id"])
    except Exception:
        logger.exception("agent_tools.audit: écriture de la trace impossible (tool=%s)", tool_name)
        return None


async def attach_confirm_ts(call_id: str, confirm_ts: str) -> None:
    """Mémorise le ts du message de confirmation, pour pouvoir l'éditer au clic."""
    try:
        pool = await get_pool()
        await pool.execute(
            "UPDATE agent_tool_calls SET confirm_ts = $2 WHERE id = $1", call_id, confirm_ts
        )
    except Exception:
        logger.exception("agent_tools.audit: confirm_ts non enregistré (call=%s)", call_id)


async def get_pending(call_id: str) -> dict[str, Any] | None:
    """Lit une ligne en attente de confirmation. None si absente ou déjà tranchée."""
    try:
        pool = await get_pool()
        row = await pool.fetchrow(
            "SELECT * FROM agent_tool_calls "
            "WHERE id = $1 AND verdict = 'confirmation_requise' AND resolved_at IS NULL",
            call_id,
        )
        return dict(row) if row else None
    except Exception:
        logger.exception("agent_tools.audit: lecture de la confirmation impossible (%s)", call_id)
        return None


async def settle(
    call_id: str,
    *,
    verdict: str,
    user_confirmed: bool,
    verdict_reason: str = "",
    result: Any = None,
) -> bool:
    """Clôt une confirmation en attente. False si quelqu'un l'a déjà tranchée.

    Le `resolved_at IS NULL` dans le WHERE est ce qui rend un double-clic inoffensif : le second
    ne trouve plus rien à trancher et n'écrit donc rien.
    """
    try:
        pool = await get_pool()
        row = await pool.fetchrow(
            "UPDATE agent_tool_calls "
            "SET verdict = $2, user_confirmed = $3, verdict_reason = COALESCE($4, verdict_reason), "
            "    result_excerpt = COALESCE($5, result_excerpt), resolved_at = now() "
            "WHERE id = $1 AND resolved_at IS NULL RETURNING id",
            call_id, verdict, user_confirmed, verdict_reason or None, _excerpt(result),
        )
        return row is not None
    except Exception:
        logger.exception("agent_tools.audit: clôture impossible (%s)", call_id)
        return False


async def daily_counts() -> dict[str, int]:
    """Appels `ok` par outil sur les dernières 24 h — alimente `rate_limit.per_day`.

    En cas d'échec de lecture, renvoie un dict vide : le quota journalier ne s'applique pas, mais
    le quota **par tour** (en mémoire) reste actif. Perdre un plafond souple vaut mieux que
    rendre l'agent muet parce qu'un compteur n'a pas pu être lu.
    """
    try:
        pool = await get_pool()
        rows = await pool.fetch(
            "SELECT tool_name, count(*) AS n FROM agent_tool_calls "
            "WHERE created_at > now() - interval '24 hours' AND verdict = 'ok' "
            "GROUP BY tool_name"
        )
        return {r["tool_name"]: int(r["n"]) for r in rows}
    except Exception:
        logger.exception("agent_tools.audit: compteurs journaliers illisibles")
        return {}
