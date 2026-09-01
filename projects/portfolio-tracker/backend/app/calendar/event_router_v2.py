"""
EventRouterV2 — déclenchement calendaire du monitoring V2 (lot 8, migration 031).

Miroir de `event_router_v1`, avec quatre différences assumées :

1. **INNER JOIN, pas LEFT JOIN.** C'est le défaut trouvé en V1 (convention #34) : un
   `LEFT JOIN theses … AND th.status='active'` rend la ligne MÊME sans thèse jointe, et aucune garde
   en aval ne testait `thesis_json IS NULL` — le scheduler V1 pouvait appeler l'agent, avec dépense
   réelle, sur une thèse inexistante ou archivée. Ici la jointure est un filtre : pas de thèse V2
   active, pas d'événement. Et `ce.thesis_v2_id IS NOT NULL` est explicite, pendant exact du
   `ce.thesis_v2_id IS NULL` posé sur les 4 requêtes V1.

2. **Aucune garde `synced`.** `agent_prompts.synced` sert à savoir si un prompt local a bien été
   recopié dans l'UI Dust. La V2 n'a pas d'UI externe : le prompt en base EST celui envoyé au
   modèle. Une garde `synced` ici ne vérifierait rien et bloquerait le flux au premier PATCH de
   prompt, pour une raison qui n'existe pas.

3. **`v2_auto_enabled`, pas `dust_auto_enabled`.** Interrupteur propre au flux (migration 031),
   FALSE par défaut. À FALSE, l'échéance n'est pas perdue : elle est enregistrée en session
   `pending_manual` avec son contexte, et notifiée. C'est un report, pas un abandon.

4. **Le mode 6 se rattrape, les modes trimestriels non.** Un brief J-2 ou une revue J+1 n'ont de sens
   qu'à leur date : les jouer trois semaines plus tard produirait un commentaire sur une publication
   déjà digérée. La revue annuelle, elle, est la colonne vertébrale du suivi long terme — une revue
   en retard est plus urgente, pas moins. D'où `scheduled_date <= today` pour le seul mode 6 : une
   journée d'indisponibilité du scheduler ne doit pas coûter une année de suivi.

Ce que ce routeur NE fait PAS, délibérément : enchaîner le mode 5 après un mode 2 en
`REVIEW_REQUIRED`. La suggestion est posée en base (`routing_suggestion='mode5'`) et notifiée, mais
le routage est une décision d'aiguillage — l'exécuter automatiquement doublerait la dépense du jour
sur la même thèse et rendrait invisible le fait qu'on vient de décider de rouvrir une analyse. Comme
en V1, c'est un déclenchement humain.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Optional

from app.db.database import get_db_session

logger = logging.getLogger(__name__)

PORTFOLIO_BASE_URL = "https://portfolio.jlmvpscode.duckdns.org"

MODE_LABELS = {
    1: "Pré-event brief", 2: "Revue trimestrielle", 3: "Décision review",
    4: "Sector pulse", 5: "Routage d'alerte", 6: "Revue annuelle",
}

# Colonnes communes : la thèse V2 active est ramenée par la jointure, donc toujours présente.
_SELECT = """
    SELECT ce.id, ce.ticker_id, ce.thesis_v2_id, ce.event_type, ce.label,
           ce.scheduled_date, ce.peer_ticker, ce.monitoring_mode,
           t.name AS ticker_name
    FROM calendar_events ce
    JOIN tickers t     ON t.id = ce.ticker_id
    JOIN theses_v2 tv  ON tv.id = ce.thesis_v2_id AND tv.status = 'active'
    WHERE ce.thesis_v2_id IS NOT NULL
      AND ce.pending_validation = FALSE
"""


class EventRouterV2:
    """Routeur calendaire du flux V2. Une instance par passage du scheduler."""

    async def process_daily_events(self, today: Optional[date] = None) -> dict[str, int]:
        today = today or date.today()
        logger.info("EventRouterV2 — traitement des événements du %s", today)
        compteurs = {
            "mode1": await self._trigger_pre_event_briefs(today),
            "mode2": await self._trigger_quarterly_reviews(today),
            "mode4": await self._trigger_sector_pulses(today),
            "mode3": await self._trigger_decision_reviews(today),
            "mode6": await self._trigger_annual_reviews(today),
        }
        logger.info("EventRouterV2 — %s", compteurs)
        return compteurs

    # ── Interrupteur de dépense ──────────────────────────────────────────────
    async def _is_auto_enabled(self) -> bool:
        async with get_db_session() as db:
            row = await db.fetchrow("SELECT v2_auto_enabled FROM portfolio_settings LIMIT 1")
        return bool(row and row["v2_auto_enabled"])

    # ── Sélection ────────────────────────────────────────────────────────────
    async def _fetch(self, sql: str, *params: Any) -> list[dict[str, Any]]:
        async with get_db_session() as db:
            return [dict(r) for r in await db.fetch(sql, *params)]

    async def _trigger_pre_event_briefs(self, today: date) -> int:
        events = await self._fetch(
            _SELECT + """
              AND ce.scheduled_date = $1::date + INTERVAL '2 days'
              AND ce.brief_triggered = FALSE
              AND ce.triggered = FALSE
              AND ce.event_type IN ('quarterly_results', 'cmd', 'agm')
            """,
            today,
        )
        return await self._executer(events, mode=1)

    async def _trigger_quarterly_reviews(self, today: date) -> int:
        events = await self._fetch(
            _SELECT + """
              AND ce.scheduled_date = $1::date - INTERVAL '1 day'
              AND ce.triggered = FALSE
              AND ce.event_type IN ('quarterly_results', 'cmd', 'agm')
            """,
            today,
        )
        return await self._executer(events, mode=2)

    async def _trigger_sector_pulses(self, today: date) -> int:
        events = await self._fetch(
            _SELECT + """
              AND ce.scheduled_date = $1::date - INTERVAL '1 day'
              AND ce.triggered = FALSE
              AND ce.event_type = 'sector_pulse_peer'
            """,
            today,
        )
        return await self._executer(events, mode=4)

    async def _trigger_decision_reviews(self, today: date) -> int:
        events = await self._fetch(
            _SELECT + """
              AND ce.scheduled_date = $1
              AND ce.triggered = FALSE
              AND ce.event_type IN ('conviction_review', 'decision_review')
            """,
            today,
        )
        return await self._executer(events, mode=3)

    async def _trigger_annual_reviews(self, today: date) -> int:
        # `<=` : une revue annuelle en retard se rattrape (cf. en-tête, point 4).
        events = await self._fetch(
            _SELECT + """
              AND ce.scheduled_date <= $1
              AND ce.triggered = FALSE
              AND ce.event_type = 'annual_review'
            """,
            today,
        )
        return await self._executer(events, mode=6)

    # ── Exécution ────────────────────────────────────────────────────────────
    async def _executer(self, events: list[dict[str, Any]], *, mode: int) -> int:
        if not events:
            return 0

        auto = await self._is_auto_enabled()
        traites = 0
        for event in events:
            try:
                if auto:
                    await self._run_auto(event, mode)
                else:
                    await self._enregistrer_en_attente(event, mode)
                traites += 1
            except Exception:  # noqa: BLE001 — un événement en échec n'arrête pas les suivants
                logger.exception(
                    "EventRouterV2 mode %s — échec sur l'événement #%s (%s)",
                    mode, event["id"], event["ticker_id"],
                )
        return traites

    async def _run_auto(self, event: dict[str, Any], mode: int) -> None:
        from app.agents.v2.monitoring import run_monitoring

        result = await run_monitoring(
            event["thesis_v2_id"], mode,
            trigger_type="scheduled",
            trigger_label=event.get("label") or event["event_type"],
            calendar_event_id=event["id"],
            peer_ticker=event.get("peer_ticker"),
        )
        session = result["session"]
        await self._notifier(
            f"{'⚠️' if session['alert_level'] in ('REVIEW_REQUIRED', 'CRITICAL') else '📊'} "
            f"{MODE_LABELS.get(mode, f'Mode {mode}')} — {event['ticker_id']} "
            f"| {event.get('label') or event['event_type']}\n"
            + (f"Niveau d'alerte : {session['alert_level']}\n" if session["alert_level"] else "")
            + (f"Verdict : {session['verdict']}\n" if session["verdict"] else "")
            + (f"Suite suggérée : {session['routing_suggestion']} (déclenchement manuel)\n"
               if session["routing_suggestion"] else "")
            + f"{PORTFOLIO_BASE_URL}/v2/ticker/{event['ticker_id']}/monitoring/{session['id']}"
        )

    async def _enregistrer_en_attente(self, event: dict[str, Any], mode: int) -> None:
        """`v2_auto_enabled=FALSE` : on trace l'échéance au lieu de dépenser.

        Le drapeau calendaire est consommé et la session `pending_manual` devient l'objet de suivi —
        sinon le routeur recréerait la même attente chaque jour jusqu'à ce que quelqu'un agisse.
        """
        from app.agents.v2.monitoring import build_monitoring_context

        label = event.get("label") or event["event_type"]
        contexte = await build_monitoring_context(
            event["thesis_v2_id"], mode, trigger_label=label, peer_ticker=event.get("peer_ticker"),
        )
        async with get_db_session() as db:
            async with db.transaction():
                session_id = await db.fetchval(
                    """
                    INSERT INTO monitoring_sessions_v2
                        (thesis_v2_id, ticker_id, mode, trigger_type, trigger_label,
                         calendar_event_id, context_sent, status)
                    VALUES ($1,$2,$3,'scheduled',$4,$5,$6,'pending_manual')
                    RETURNING id
                    """,
                    event["thesis_v2_id"], event["ticker_id"], mode, label, event["id"], contexte,
                )
                flag = "brief_triggered" if mode == 1 else "triggered"
                await db.execute(
                    f"UPDATE calendar_events SET {flag} = TRUE, session_v2_id = $2 WHERE id = $1",
                    event["id"], session_id,
                )

        await self._notifier(
            f"🔔 [En attente] {MODE_LABELS.get(mode, f'Mode {mode}')} — {event['ticker_id']} | {label}\n"
            f"L'automatisme V2 est désactivé (`v2_auto_enabled=FALSE`) — session #{session_id} "
            f"enregistrée avec son contexte, à déclencher manuellement :\n"
            f"{PORTFOLIO_BASE_URL}/v2/ticker/{event['ticker_id']}/monitoring/{session_id}"
        )
        logger.info(
            "EventRouterV2 mode %s — %s en attente manuelle (session #%s)",
            mode, event["ticker_id"], session_id,
        )

    async def _notifier(self, message: str) -> None:
        """Une notification qui échoue ne doit jamais faire échouer la session déjà persistée."""
        try:
            from app.notifications.slack_webhook import SlackWebhook

            await SlackWebhook().send(message)
        except Exception as e:  # noqa: BLE001
            logger.warning("EventRouterV2 — notification Slack non envoyée : %s", e)
