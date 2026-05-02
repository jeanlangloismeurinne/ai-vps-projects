import logging
from slack_sdk.web.async_client import AsyncWebClient
from app.config import settings

logger = logging.getLogger(__name__)


class SlackNotifier:
    def __init__(self):
        self.client = AsyncWebClient(token=settings.SLACK_BOT_TOKEN)
        self.channel = settings.SLACK_PORTFOLIO_CHANNEL_ID

    async def send_pre_event_brief(self, ticker: str, brief: dict, event: dict):
        checklist = "\n".join(
            f"• *{i['hypothesis_code']}* : {i['what_to_look_for']}\n"
            f"  ✅ {i['confirmation_signal']} | 🚨 {i['alert_signal']}"
            for i in brief.get("reading_checklist", [])
        )
        await self._send([
            {"type": "header", "text": {"type": "plain_text", "text": f"⚡ Brief Pré-Event — {ticker}"}},
            {"type": "section", "text": {"type": "mrkdwn",
             "text": f"*Événement demain :* {event['event_type']}\n\n{checklist}"}},
        ])

    async def send_regime2_report(self, ticker: str, review: dict):
        emoji = {"green": "🟢", "orange": "🟡", "red": "🔴"}.get(review.get("alert_level", "green"), "⚪")
        scores = "\n".join(
            f"• *{s['code']}* : {s['status'].upper()} — {s.get('evidence', '')}"
            for s in review.get("hypotheses_scores", [])
        )
        await self._send([
            {"type": "header", "text": {"type": "plain_text",
             "text": f"{emoji} Revue Trimestrielle — {ticker}"}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*Flag :* {review.get('flag', 'RAS')}"},
                {"type": "mrkdwn", "text": f"*Recommandation :* {review.get('recommendation', '').upper()}"},
            ]},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Hypothèses :*\n{scores}"}},
        ])

    async def send_regime3_decision(self, ticker: str, review: dict):
        d = review.get("decision", {})
        munger = review.get("munger_test", {})
        urgency_emoji = {"immediate": "🚨", "next_session": "⚡", "week": "📅"}.get(d.get("urgency", "week"), "📅")
        await self._send([
            {"type": "header", "text": {"type": "plain_text", "text": f"🔍 DÉCISION REQUISE — {ticker}"}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*Nature :* {review.get('diagnosis', {}).get('nature', '')}"},
                {"type": "mrkdwn", "text": f"*Force thèse :* {review.get('thesis_revision', {}).get('strength_change', '')}"},
            ]},
            {"type": "section", "text": {"type": "mrkdwn",
             "text": f"*Diagnostic :* {review.get('diagnosis', {}).get('explanation', '')}"}},
            {"type": "section", "text": {"type": "mrkdwn",
             "text": f"*Test Munger :* {'✅ OUI' if munger.get('answer') == 'yes' else '❌ NON'} — {munger.get('rationale', '')}"}},
            {"type": "section", "text": {"type": "mrkdwn",
             "text": f"{urgency_emoji} *RECOMMANDATION : {d.get('recommendation', '').upper()}*\n{d.get('rationale', '')}"}},
        ])

    async def send_sector_pulse_escalation(self, main_ticker: str, peer_ticker: str, pulse: dict):
        await self._send([{"type": "section", "text": {"type": "mrkdwn",
            "text": f"🚨 *Sector Pulse Escalation* — {main_ticker}\n"
                    f"Pair *{peer_ticker}* score {pulse.get('pulse_score')}\n"
                    f"{pulse.get('peer_result_summary', '')}\n*Action :* Régime 3 déclenché"}}])

    async def send_watchlist_alert(self, ticker: str, current_price: float, target_price: float):
        gap_pct = round((current_price / target_price - 1) * 100, 1)
        await self._send([{"type": "section", "text": {"type": "mrkdwn",
            "text": f"🎯 *Watchlist Alert* — {ticker}\n"
                    f"Prix actuel : *{current_price}* | Cible : {target_price} | Écart : {gap_pct:+.1f}%"}}])

    async def send_weekly_digest(self, snapshot: dict):
        positions_text = "\n".join(
            f"• *{p['ticker']}* : {p.get('recommendation', 'maintain')} "
            f"| Score : {p.get('thesis_score', '?')}/7 | P&L : {p.get('unrealized_pnl_pct', 0):.1f}%"
            for p in snapshot.get("positions", [])
        )
        flags = snapshot.get("concentration_flags", [])
        flags_text = ("\n⚠️ *Flags :*\n" + "\n".join(
            f"• {f['type'].upper()} {f.get('sector', '')} = {f.get('total_pct', 0):.0f}%"
            for f in flags)) if flags else ""
        await self._send([
            {"type": "header", "text": {"type": "plain_text", "text": "📊 Revue Hebdomadaire Portfolio"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Positions :*\n{positions_text}{flags_text}"}},
        ])

    async def send_budget_alert(self, spent: float, budget: float):
        await self._send([{"type": "section", "text": {"type": "mrkdwn",
            "text": f"⚠️ *Budget Dust 80% atteint* : ${spent:.2f}/${budget:.2f}\n"
                    f"Régimes 1 et 3 suspendus si dépassement."}}])

    async def send_error_alert(self, ticker: str, error: str):
        await self._send([{"type": "section", "text": {"type": "mrkdwn",
            "text": f"❌ *Erreur* — {ticker}\n```{error[:500]}```"}}])

    async def _send(self, blocks: list):
        try:
            await self.client.chat_postMessage(channel=self.channel, blocks=blocks)
        except Exception as e:
            logger.error(f"Slack error: {e}")
