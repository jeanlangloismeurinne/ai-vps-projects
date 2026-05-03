import uuid
import json
import re
import logging
import httpx
from datetime import datetime
from typing import Optional
from app.config import settings
from app.db.database import get_db_session

logger = logging.getLogger(__name__)
DUST_API_BASE = "https://dust.tt/api/v1"

SCOUT_PROMPT = """Tu analyses une opportunité d'investissement potentielle pour décider si elle mérite d'être suivie.

Ticker : {ticker}
Données quantitatives (M1) : {m1_data}
Contexte sectoriel (M3) : {m3_data}

Produis une analyse structurée avec exactement ces sections :
1. SCHÉMA ANALYTIQUE : liste les 5-7 KPIs sectoriels clefs à surveiller, les red flags éliminatoires, et les peers Tier 1 (analogie directe) et Tier 2 (bellwethers) avec les métriques à extraire pour chacun.
2. COMPARAISON PEERS : tableau comparatif sur 4-5 métriques de valorisation clefs vs les peers identifiés.
3. PRIX D'ENTRÉE CIBLE : fourchette de prix d'entrée avec la méthode de valorisation utilisée (DCF, multiple sectoriel, etc.) et les hypothèses principales.
4. THÈSE PRÉLIMINAIRE : paragraphe de 150-200 mots résumant la thèse d'investissement potentielle, les catalyseurs et les risques principaux.
5. SIGNAL DE CONVICTION : strong | moderate | weak | avoid, avec justification en 2 phrases."""


async def _get_agent_version(agent_id: str, headers: dict) -> Optional[int]:
    url = f"{DUST_API_BASE}/w/{settings.DUST_WORKSPACE_ID}/assistant/agent_configurations/{agent_id}?variant=light"
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url, headers=headers)
        if r.status_code == 200:
            return r.json().get("agentConfiguration", {}).get("version")
    return None


async def _call_dust_blocking(message: str, ticker: str, headers: dict) -> dict:
    """Crée une conversation Dust avec blocking=True et retourne le résultat."""
    payload = {
        "message": {
            "content": message,
            "mentions": [{"configurationId": settings.DUST_RESEARCH_AGENT_ID}],
            "context": {
                "username": "portfolio-tracker",
                "timezone": "Europe/Paris",
                "fullName": "Portfolio Tracker",
            }
        },
        "title": f"Scout {ticker} — {datetime.now().strftime('%Y-%m-%d')}",
        "blocking": True,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            f"{DUST_API_BASE}/w/{settings.DUST_WORKSPACE_ID}/assistant/conversations",
            headers=headers, json=payload,
        )
        r.raise_for_status()
        data = r.json()

    conversation = data.get("conversation", {})
    conv_id = conversation.get("sId")
    message_data = data.get("message", {})

    content_text = ""
    cost_usd = 0.0
    for group in conversation.get("content", []):
        for msg in group:
            if msg.get("type") == "agent_message" and msg.get("status") == "succeeded":
                content_text = "".join(
                    b.get("value", "") for b in msg.get("content", []) if b.get("type") == "text"
                )
                usage = msg.get("usage", {})
                ti = usage.get("promptTokens", 0)
                to = usage.get("completionTokens", 0)
                cost_usd = ti * 0.000195 / 1000 + to * 0.00078 / 1000
                break

    return {"content": content_text, "conversation_id": conv_id, "cost_usd": cost_usd}


def _parse_section(content: str, section_num: int, next_num: Optional[int] = None) -> Optional[str]:
    """Extrait une section numérotée du contenu de l'agent."""
    try:
        pattern = rf"{section_num}\.\s+[A-ZÀÂÉÈÊÎÔÙÛÜÇ\s]+"
        match = re.search(pattern, content, re.IGNORECASE)
        if not match:
            return None
        start = match.end()
        if next_num:
            next_pattern = rf"{next_num}\.\s+[A-ZÀÂÉÈÊÎÔÙÛÜÇ\s]+"
            next_match = re.search(next_pattern, content[start:], re.IGNORECASE)
            end = start + next_match.start() if next_match else len(content)
        else:
            end = len(content)
        return content[start:end].strip()
    except Exception:
        return None


def _parse_conviction(content: str) -> Optional[str]:
    """Extrait le signal de conviction de la section 5."""
    section = _parse_section(content, 5)
    if not section:
        return None
    for signal in ["strong", "moderate", "weak", "avoid"]:
        if signal in section.lower():
            return signal
    return None


def _parse_entry_price(content: str) -> Optional[float]:
    """Extrait un prix numérique de la section 3."""
    section = _parse_section(content, 3, 4)
    if not section:
        return None
    match = re.search(r'[\d]+[.,]?[\d]*', section.replace(',', '.'))
    if match:
        try:
            return float(match.group().replace(',', '.'))
        except ValueError:
            return None
    return None


async def run_scout(watchlist_id: str, ticker: str, db=None, redis=None) -> dict:
    """
    Déclenche l'analyse R0 pour un item watchlist.
    Retourne {"job_id": str, "status": "pending"}.
    Écrit le statut dans Redis : job:{job_id}.
    """
    job_id = str(uuid.uuid4())

    if redis:
        await redis.set(
            f"job:{job_id}",
            json.dumps({"status": "pending", "ticker": ticker, "regime": 0}),
            ex=86400,
        )

    # Run en arrière-plan (la fonction est appelée depuis un background task)
    await _execute_scout(job_id, watchlist_id, ticker, redis)
    return {"job_id": job_id, "status": "pending"}


async def _execute_scout(job_id: str, watchlist_id: str, ticker: str, redis=None):
    from app.data_collection.m1_quantitative import collect_quantitative
    from app.data_collection.m3_qualitative import collect_m3
    from app.agents.dust_client import DustClient

    headers = {
        "Authorization": f"Bearer {settings.DUST_API_KEY}",
        "Content-Type": "application/json",
    }

    async def _set_status(status: str, extra: dict = None):
        if redis:
            payload = {"status": status, "ticker": ticker, "regime": 0}
            if extra:
                payload.update(extra)
            await redis.set(f"job:{job_id}", json.dumps(payload), ex=86400)

    try:
        await _set_status("running")

        # Versionning
        agent_version = await _get_agent_version(settings.DUST_RESEARCH_AGENT_ID, headers)

        # Collecte données M1 + M3
        m1_data = collect_quantitative(ticker, settings.FMP_API_KEY)
        dust_client = DustClient()
        try:
            m3_result = await collect_m3(ticker, ticker, "post_earnings", {}, dust_client)
        except Exception:
            m3_result = {}

        # Construire prompt
        prompt = SCOUT_PROMPT.format(
            ticker=ticker,
            m1_data=json.dumps(m1_data, indent=2, default=str)[:3000],
            m3_data=json.dumps(m3_result, indent=2, default=str)[:2000],
        )

        # Appel Dust
        result = await _call_dust_blocking(prompt, ticker, headers)
        content = result.get("content", "")
        conv_id = result.get("conversation_id")
        cost_usd = result.get("cost_usd", 0.0)

        # Parsing par sections
        schema_json_draft = {
            "raw_section": _parse_section(content, 1, 2),
        }
        peer_snapshot_json = {
            "raw_section": _parse_section(content, 2, 3),
        }
        entry_price_target = _parse_entry_price(content)
        scout_brief = _parse_section(content, 4, 5)
        conviction_signal = _parse_conviction(content)

        # Mise à jour en base
        async with get_db_session() as db:
            await db.execute("""
                UPDATE watchlist SET
                    schema_json_draft    = $1,
                    peer_snapshot_json   = $2,
                    entry_price_target   = COALESCE($3, entry_price_target),
                    scout_brief          = $4,
                    conviction_signal    = $5,
                    scout_run_at         = NOW(),
                    scout_agent_version  = $6,
                    scout_cost_usd       = $7,
                    dust_conversation_id = $8,
                    thesis_status        = 'draft'
                WHERE id = $9
            """,
                schema_json_draft, peer_snapshot_json, entry_price_target,
                scout_brief, conviction_signal, agent_version, cost_usd,
                conv_id, watchlist_id,
            )

        await _set_status("done", {"conversation_id": conv_id})

    except Exception as e:
        logger.error(f"Scout error for {ticker}: {e}")
        await _set_status("error", {"detail": str(e)})
