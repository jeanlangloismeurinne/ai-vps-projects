"""
EventRouterV1 — Déclenchements automatiques V1 via calendar_events.
Lit uniquement calendar_events (V1), jamais v0_calendar_events.
"""
import json
import logging
from datetime import date

from app.db.database import get_db_session
from app.config import settings

logger = logging.getLogger(__name__)

PORTFOLIO_BASE_URL = "https://portfolio.jlmvpscode.duckdns.org"


class EventRouterV1:

    async def process_daily_events(self):
        today = date.today()
        logger.info(f"EventRouterV1 — traitement des événements du {today}")
        await self._trigger_pre_event_briefs(today)
        await self._trigger_quarterly_reviews(today)
        await self._trigger_sector_pulses(today)
        await self._trigger_conviction_reviews(today)

    async def _is_agent_synced(self) -> bool:
        async with get_db_session() as db:
            row = await db.fetchrow(
                "SELECT synced FROM agent_prompts WHERE agent_name='monitoring-agent'"
            )
        return bool(row and row["synced"])

    async def _is_dust_auto_enabled(self) -> bool:
        async with get_db_session() as db:
            row = await db.fetchrow("SELECT dust_auto_enabled FROM portfolio_settings LIMIT 1")
        return bool(row and row["dust_auto_enabled"])

    async def _handle_manual_mode(
        self,
        event: dict,
        mode: int,
        context: str,
        calendar_flag: str,
    ):
        """Crée une session pending_manual et envoie 2 notifications Slack."""
        from app.notifications.slack_webhook import SlackWebhook

        ticker_id = event["ticker_id"]
        label = event.get("label") or event.get("event_type", "")

        async with get_db_session() as db:
            session_row = await db.fetchrow(
                """
                INSERT INTO monitoring_sessions
                    (ticker_id, thesis_id, trigger_type, trigger_label, mode, status, calendar_event_id)
                VALUES ($1,$2,'scheduled',$3,$4,'pending_manual',$5)
                RETURNING *
                """,
                ticker_id, event.get("thesis_id"), label, mode, event["id"],
            )
            session_id = session_row["id"]
            await db.execute(
                "INSERT INTO monitoring_messages (session_id, role, content) VALUES ($1,'user',$2)",
                session_id, context,
            )
            await db.execute(
                f"UPDATE calendar_events SET {calendar_flag}=TRUE WHERE id=$1",
                event["id"],
            )

        MODE_LABELS = {
            1: "Pré-event brief",
            2: "Revue trimestrielle",
            3: "Révision conviction",
            4: "Sector Pulse",
        }
        mode_label = MODE_LABELS.get(mode, f"Mode {mode}")
        url = f"{PORTFOLIO_BASE_URL}/ticker/{ticker_id}/monitoring/{session_id}"

        webhook = SlackWebhook()

        await webhook.send(
            f"🔔 [Manuel] {mode_label} — {ticker_id} | {label}\n"
            f"Uploader le résultat Dust sur : {url}"
        )

        # Tronquer si le contexte dépasse la limite Slack (3000 chars par bloc)
        max_ctx = 2500
        ctx_display = context if len(context) <= max_ctx else context[:max_ctx] + "\n[…tronqué]"
        await webhook.send(
            f"*Contexte à coller dans Dust — Mode {mode} — {ticker_id}:*\n```{ctx_display}```"
        )

        logger.info(f"EventRouterV1 Mode {mode} manuel — {ticker_id} (session #{session_id})")

    # ─────────────────── Mode 1 — J-2 pré-event brief ────────────────────────

    async def _trigger_pre_event_briefs(self, today: date):
        async with get_db_session() as db:
            events = await db.fetch(
                """
                SELECT ce.*, t.name AS ticker_name, t.company_type,
                       th.thesis_json, th.id AS thesis_id, th.one_liner AS thesis_one_liner
                FROM calendar_events ce
                JOIN tickers t ON t.id = ce.ticker_id
                LEFT JOIN theses th ON th.id = ce.thesis_id AND th.status = 'active'
                WHERE ce.scheduled_date = $1::date + INTERVAL '2 days'
                  AND ce.brief_triggered = FALSE
                  AND ce.triggered = FALSE
                  AND ce.pending_validation = FALSE
                  AND ce.event_type IN ('quarterly_results', 'cmd', 'agm')
                """,
                today,
            )

        if not events:
            return

        if not await self._is_agent_synced():
            logger.warning("EventRouterV1 Mode 1 — monitoring-agent non synchronisé, skip")
            return

        auto_enabled = await self._is_dust_auto_enabled()

        from app.agents.monitoring_agent_v1 import MonitoringAgentV1
        from app.notifications.slack_webhook import SlackWebhook

        agent = MonitoringAgentV1()
        webhook = SlackWebhook()

        for event in events:
            event = dict(event)
            ticker_id = event["ticker_id"]
            try:
                context = self._build_pre_event_context(event)

                if not auto_enabled:
                    await self._handle_manual_mode(
                        event=event, mode=1, context=context, calendar_flag="brief_triggered"
                    )
                    continue

                result = await agent.run(mode=1, message=context)
                parsed = agent.extract_json(result["content"])

                async with get_db_session() as db:
                    session_row = await db.fetchrow(
                        """
                        INSERT INTO monitoring_sessions
                            (ticker_id, thesis_id, trigger_type, trigger_label, mode, status,
                             result_json, model_used, calendar_event_id, completed_at)
                        VALUES ($1,$2,'scheduled','pre_event_brief',1,'completed',
                                $3,$4,$5,NOW())
                        RETURNING *
                        """,
                        ticker_id, event.get("thesis_id"),
                        parsed or {"raw": result["content"]},
                        result.get("model"),
                        event["id"],
                    )
                    session_id = session_row["id"]
                    await db.execute(
                        "INSERT INTO monitoring_messages (session_id, role, content) VALUES ($1,'user',$2)",
                        session_id, context,
                    )
                    await db.execute(
                        """
                        INSERT INTO monitoring_messages (session_id, role, content, raw_payload)
                        VALUES ($1,'agent',$2,$3)
                        """,
                        session_id, result["content"],
                        {"tokens_input": result.get("tokens_input"),
                         "tokens_output": result.get("tokens_output"),
                         "cost_usd": result.get("cost_usd")},
                    )
                    await db.execute(
                        "UPDATE calendar_events SET brief_triggered=TRUE WHERE id=$1",
                        event["id"],
                    )

                label = event.get("label") or event.get("event_type", "")
                url = f"{PORTFOLIO_BASE_URL}/ticker/{ticker_id}/monitoring/{session_id}"
                await webhook.send(
                    f"📋 Pré-event brief — {ticker_id} | {label} dans 2 jours\n→ {url}"
                )
                logger.info(f"EventRouterV1 Mode 1 — {ticker_id} OK (session #{session_id})")

            except Exception as e:
                logger.error(f"EventRouterV1 Mode 1 error for {ticker_id}: {e}")

    def _build_pre_event_context(self, event: dict) -> str:
        scheduled_date = event.get("scheduled_date")
        if hasattr(scheduled_date, "isoformat"):
            scheduled_date = scheduled_date.isoformat()

        parts = [
            f"Ticker : {event['ticker_id']}",
            f"Trigger : {event.get('label') or event.get('event_type', '')}",
            "Mode demandé : 1",
            f"company_type : {event.get('company_type') or 'public'}",
            f"Événement : {event['event_type']} prévu le {scheduled_date}",
        ]

        thesis_json = event.get("thesis_json")
        if thesis_json:
            parts.append(
                f"Thèse — one_liner : {event.get('thesis_one_liner') or '(non renseigné)'}"
            )
            hyps = thesis_json.get("hypotheses", [])
            if hyps:
                lines = ["Hypothèses à surveiller :"]
                for h in hyps:
                    at = h.get("alert_threshold", {})
                    lines.append(
                        f"  {h.get('id', '')} — {h.get('text', '')} | "
                        f"KPI : {h.get('kpi_metric', '')} | "
                        f"Seuil alerte : {at}"
                    )
                parts.append("\n".join(lines))

        return "\n\n".join(parts)

    # ─────────────────── Mode 2 — J+1 revue trimestrielle ────────────────────

    async def _trigger_quarterly_reviews(self, today: date):
        async with get_db_session() as db:
            events = await db.fetch(
                """
                SELECT ce.*, t.name AS ticker_name, t.company_type,
                       th.thesis_json, th.id AS thesis_id, th.one_liner AS thesis_one_liner
                FROM calendar_events ce
                JOIN tickers t ON t.id = ce.ticker_id
                LEFT JOIN theses th ON th.id = ce.thesis_id AND th.status = 'active'
                WHERE ce.scheduled_date = $1::date - INTERVAL '1 day'
                  AND ce.triggered = FALSE
                  AND ce.pending_validation = FALSE
                  AND ce.event_type IN ('quarterly_results', 'cmd')
                """,
                today,
            )

        if not events:
            return

        if not await self._is_agent_synced():
            logger.warning("EventRouterV1 Mode 2 — monitoring-agent non synchronisé, skip")
            return

        auto_enabled = await self._is_dust_auto_enabled()

        from app.agents.monitoring_agent_v1 import MonitoringAgentV1
        from app.notifications.slack_webhook import SlackWebhook
        from app.api.monitoring_v2 import _normalize_monitoring_result

        agent = MonitoringAgentV1()
        webhook = SlackWebhook()

        for event in events:
            event = dict(event)
            ticker_id = event["ticker_id"]
            try:
                context = await self._build_thesis_context(event, mode=2)

                if not auto_enabled:
                    await self._handle_manual_mode(
                        event=event, mode=2, context=context, calendar_flag="triggered"
                    )
                    continue

                result = await agent.run(mode=2, message=context)
                parsed = agent.extract_json(result["content"])
                if parsed:
                    parsed = _normalize_monitoring_result(parsed, event.get("thesis_json"))

                alert_level = None
                routing_suggestion = None
                if parsed:
                    alert_level = parsed.get("alert_level") or parsed.get("flag")
                    routing_suggestion = parsed.get("routing_suggestion") or parsed.get("action")

                async with get_db_session() as db:
                    session_row = await db.fetchrow(
                        """
                        INSERT INTO monitoring_sessions
                            (ticker_id, thesis_id, trigger_type, trigger_label, mode, status,
                             result_json, alert_level, routing_suggestion, model_used,
                             calendar_event_id, completed_at)
                        VALUES ($1,$2,'scheduled',$3,2,'completed',$4,$5,$6,$7,$8,NOW())
                        RETURNING *
                        """,
                        ticker_id, event.get("thesis_id"),
                        event.get("label") or event.get("event_type", ""),
                        parsed or {"raw": result["content"]},
                        alert_level, routing_suggestion,
                        result.get("model"),
                        event["id"],
                    )
                    session_id = session_row["id"]
                    await db.execute(
                        "INSERT INTO monitoring_messages (session_id, role, content) VALUES ($1,'user',$2)",
                        session_id, context,
                    )
                    await db.execute(
                        """
                        INSERT INTO monitoring_messages (session_id, role, content, raw_payload)
                        VALUES ($1,'agent',$2,$3)
                        """,
                        session_id, result["content"],
                        {"tokens_input": result.get("tokens_input"),
                         "tokens_output": result.get("tokens_output"),
                         "cost_usd": result.get("cost_usd")},
                    )
                    await db.execute(
                        "UPDATE calendar_events SET triggered=TRUE WHERE id=$1",
                        event["id"],
                    )

                label = event.get("label") or event.get("event_type", "")
                url = f"{PORTFOLIO_BASE_URL}/ticker/{ticker_id}/monitoring/{session_id}"
                if alert_level == "RAS":
                    await webhook.send(f"✅ Monitoring RAS — {ticker_id} | {label}")
                elif alert_level == "REVIEW_REQUIRED":
                    await webhook.send(
                        f"⚠️ Révision requise — {ticker_id} | {label}\n→ {url}"
                    )
                elif alert_level == "CRITICAL":
                    await webhook.send(f"🔴 CRITIQUE — {ticker_id} | {label}\n→ {url}")

                logger.info(
                    f"EventRouterV1 Mode 2 — {ticker_id} OK "
                    f"(session #{session_id}, alert={alert_level})"
                )

            except Exception as e:
                logger.error(f"EventRouterV1 Mode 2 error for {ticker_id}: {e}")

    async def _build_thesis_context(self, event: dict, mode: int) -> str:
        parts = [
            f"Ticker : {event['ticker_id']}",
            f"Trigger : {event.get('label') or event.get('event_type', '')}",
            f"Mode demandé : {mode}",
            f"company_type : {event.get('company_type') or 'public'}",
        ]

        thesis_json = event.get("thesis_json")
        if thesis_json:
            parts.append(
                f"Thèse JSON :\n```json\n"
                f"{json.dumps(thesis_json, ensure_ascii=False, indent=2)}\n```"
            )

        company_type = event.get("company_type") or "public"
        if company_type == "private":
            async with get_db_session() as db:
                profile = await db.fetchrow(
                    "SELECT * FROM private_company_profiles WHERE ticker_id=$1",
                    event["ticker_id"],
                )
            if profile:
                pd = dict(profile)
                for k, v in pd.items():
                    if hasattr(v, "isoformat"):
                        pd[k] = v.isoformat()
                parts.append(
                    f"Profil private :\n{json.dumps(pd, ensure_ascii=False, indent=2)}"
                )
        else:
            try:
                from app.data_collection.data_service import DataService
                m1 = await DataService().get_m1(event["ticker_id"], settings.FMP_API_KEY)
                parts.append(
                    f"Données de marché : prix={m1.get('price')}, "
                    f"PER NTM={m1.get('forward_pe')}, "
                    f"market_cap={m1.get('market_cap')}"
                )
            except Exception:
                pass

        return "\n\n".join(parts)

    # ─────────────────── Mode 4 — J+1 sector pulse ───────────────────────────

    async def _trigger_sector_pulses(self, today: date):
        async with get_db_session() as db:
            events = await db.fetch(
                """
                SELECT ce.*, ce.peer_ticker,
                       t.company_type, th.thesis_json, th.id AS thesis_id
                FROM calendar_events ce
                JOIN tickers t ON t.id = ce.ticker_id
                LEFT JOIN theses th ON th.id = ce.thesis_id AND th.status = 'active'
                WHERE ce.scheduled_date = $1::date - INTERVAL '1 day'
                  AND ce.triggered = FALSE
                  AND ce.pending_validation = FALSE
                  AND ce.event_type = 'sector_pulse_peer'
                """,
                today,
            )

        if not events:
            return

        if not await self._is_agent_synced():
            logger.warning("EventRouterV1 Mode 4 — monitoring-agent non synchronisé, skip")
            return

        auto_enabled = await self._is_dust_auto_enabled()

        from app.agents.monitoring_agent_v1 import MonitoringAgentV1
        from app.notifications.slack_webhook import SlackWebhook

        agent = MonitoringAgentV1()
        webhook = SlackWebhook()

        for event in events:
            event = dict(event)
            ticker_id = event["ticker_id"]
            try:
                context = self._build_sector_pulse_context(event)

                if not auto_enabled:
                    await self._handle_manual_mode(
                        event=event, mode=4, context=context, calendar_flag="triggered"
                    )
                    continue

                result = await agent.run(mode=4, message=context)
                parsed = agent.extract_json(result["content"])

                action = parsed.get("action") if parsed else None

                async with get_db_session() as db:
                    session_row = await db.fetchrow(
                        """
                        INSERT INTO monitoring_sessions
                            (ticker_id, thesis_id, trigger_type, trigger_label, mode, status,
                             result_json, routing_suggestion, model_used,
                             calendar_event_id, completed_at)
                        VALUES ($1,$2,'scheduled',$3,4,'completed',$4,$5,$6,$7,NOW())
                        RETURNING *
                        """,
                        ticker_id, event.get("thesis_id"),
                        event.get("label") or event.get("event_type", ""),
                        parsed or {"raw": result["content"]},
                        action,
                        result.get("model"),
                        event["id"],
                    )
                    session_id = session_row["id"]
                    await db.execute(
                        "INSERT INTO monitoring_messages (session_id, role, content) VALUES ($1,'user',$2)",
                        session_id, context,
                    )
                    await db.execute(
                        """
                        INSERT INTO monitoring_messages (session_id, role, content, raw_payload)
                        VALUES ($1,'agent',$2,$3)
                        """,
                        session_id, result["content"],
                        {"tokens_input": result.get("tokens_input"),
                         "tokens_output": result.get("tokens_output"),
                         "cost_usd": result.get("cost_usd")},
                    )
                    await db.execute(
                        "UPDATE calendar_events SET triggered=TRUE WHERE id=$1",
                        event["id"],
                    )

                if action == "escalate_to_regime3":
                    peer_ticker = event.get("peer_ticker", "")
                    score = parsed.get("sector_health_score", "?") if parsed else "?"
                    url = f"{PORTFOLIO_BASE_URL}/ticker/{ticker_id}/monitoring/{session_id}"
                    await webhook.send(
                        f"⚠️ Sector Pulse négatif — {peer_ticker} → {ticker_id}\n"
                        f"Score : {score}/5\n→ {url}"
                    )

                logger.info(
                    f"EventRouterV1 Mode 4 — {ticker_id} OK "
                    f"(session #{session_id}, action={action})"
                )

            except Exception as e:
                logger.error(f"EventRouterV1 Mode 4 error for {ticker_id}: {e}")

    def _build_sector_pulse_context(self, event: dict) -> str:
        parts = [
            f"Ticker suivi : {event['ticker_id']}",
            f"Pair qui publie : {event.get('peer_ticker', '')}",
            f"Trigger : {event.get('label') or event.get('event_type', '')}",
            "Mode demandé : 4",
        ]

        thesis_json = event.get("thesis_json")
        if thesis_json:
            hyps = thesis_json.get("hypotheses", [])
            if hyps:
                lines = ["Hypothèses à scorer (-5 à +5) :"]
                for h in hyps:
                    lines.append(f"  {h.get('id', '')} — {h.get('text', '')}")
                parts.append("\n".join(lines))

        return "\n\n".join(parts)

    # ─────────────────── Mode 3 — Jour J conviction review ───────────────────

    async def _trigger_conviction_reviews(self, today: date):
        async with get_db_session() as db:
            events = await db.fetch(
                """
                SELECT ce.*, t.name AS ticker_name, t.company_type,
                       th.thesis_json, th.id AS thesis_id, th.one_liner AS thesis_one_liner
                FROM calendar_events ce
                JOIN tickers t ON t.id = ce.ticker_id
                LEFT JOIN theses th ON th.id = ce.thesis_id AND th.status = 'active'
                WHERE ce.scheduled_date = $1
                  AND ce.triggered = FALSE
                  AND ce.pending_validation = FALSE
                  AND ce.event_type = 'conviction_review'
                """,
                today,
            )

        if not events:
            return

        if not await self._is_agent_synced():
            logger.warning("EventRouterV1 Mode 3 — monitoring-agent non synchronisé, skip")
            return

        auto_enabled = await self._is_dust_auto_enabled()

        from app.agents.monitoring_agent_v1 import MonitoringAgentV1
        from app.notifications.slack_webhook import SlackWebhook
        from app.api.monitoring_v2 import _normalize_monitoring_result

        agent = MonitoringAgentV1()
        webhook = SlackWebhook()

        for event in events:
            event = dict(event)
            ticker_id = event["ticker_id"]
            try:
                context = await self._build_thesis_context(event, mode=3)

                if not auto_enabled:
                    await self._handle_manual_mode(
                        event=event, mode=3, context=context, calendar_flag="triggered"
                    )
                    continue

                result = await agent.run(mode=3, message=context)
                parsed = agent.extract_json(result["content"])
                if parsed:
                    parsed = _normalize_monitoring_result(parsed, event.get("thesis_json"))

                async with get_db_session() as db:
                    session_row = await db.fetchrow(
                        """
                        INSERT INTO monitoring_sessions
                            (ticker_id, thesis_id, trigger_type, trigger_label, mode, status,
                             result_json, model_used, calendar_event_id, completed_at)
                        VALUES ($1,$2,'scheduled',$3,3,'completed',$4,$5,$6,NOW())
                        RETURNING *
                        """,
                        ticker_id, event.get("thesis_id"),
                        event.get("label") or event.get("event_type", ""),
                        parsed or {"raw": result["content"]},
                        result.get("model"),
                        event["id"],
                    )
                    session_id = session_row["id"]
                    await db.execute(
                        "INSERT INTO monitoring_messages (session_id, role, content) VALUES ($1,'user',$2)",
                        session_id, context,
                    )
                    await db.execute(
                        """
                        INSERT INTO monitoring_messages (session_id, role, content, raw_payload)
                        VALUES ($1,'agent',$2,$3)
                        """,
                        session_id, result["content"],
                        {"tokens_input": result.get("tokens_input"),
                         "tokens_output": result.get("tokens_output"),
                         "cost_usd": result.get("cost_usd")},
                    )
                    await db.execute(
                        "UPDATE calendar_events SET triggered=TRUE WHERE id=$1",
                        event["id"],
                    )

                decision = parsed.get("decision", "?") if parsed else "?"
                conviction = parsed.get("revised_conviction", "?") if parsed else "?"
                url = f"{PORTFOLIO_BASE_URL}/ticker/{ticker_id}/monitoring/{session_id}"
                await webhook.send(
                    f"🔍 Révision conviction — {ticker_id}\n"
                    f"Décision : {decision} | Conviction : {conviction}/10\n→ {url}"
                )

                logger.info(f"EventRouterV1 Mode 3 — {ticker_id} OK (session #{session_id})")

            except Exception as e:
                logger.error(f"EventRouterV1 Mode 3 error for {ticker_id}: {e}")
