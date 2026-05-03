import json
import logging
import httpx
from datetime import datetime
from typing import Optional
from app.config import settings
from app.db.database import get_db_session

logger = logging.getLogger(__name__)
DUST_API_BASE = "https://dust.tt/api/v1"
AGENT_ID = "eAYsKqZ1D2"  # research-agent


def _get_headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.DUST_API_KEY}",
        "Content-Type": "application/json",
    }


def _extract_agent_response(conversation_data: dict) -> dict:
    """Extrait la dernière réponse agent d'une conversation Dust."""
    content_groups = conversation_data.get("conversation", {}).get("content", [])
    for group in reversed(content_groups):
        for msg in reversed(group):
            if msg.get("type") == "agent_message":
                content_text = "".join(
                    b.get("value", "") for b in msg.get("content", []) if b.get("type") == "text"
                )
                cot = msg.get("chainOfThought", "")
                return {
                    "agent_response": content_text,
                    "chain_of_thought": cot if cot else None,
                }
    return {"agent_response": "", "chain_of_thought": None}


def build_watchlist_context(item: dict) -> str:
    return f"""Contexte : tu as produit une analyse préliminaire pour {item.get('ticker')} ({item.get('company_name', '')}).

Voici ton analyse initiale :
SCHÉMA ANALYTIQUE : {json.dumps(item.get('schema_json_draft'), ensure_ascii=False, indent=2)}
COMPARAISON PEERS : {json.dumps(item.get('peer_snapshot_json'), ensure_ascii=False, indent=2)}
PRIX D'ENTRÉE CIBLE : {item.get('entry_price_target')}
THÈSE PRÉLIMINAIRE : {item.get('scout_brief')}
SIGNAL DE CONVICTION : {item.get('conviction_signal')}

L'utilisateur souhaite challenger ou approfondir cette analyse. Réponds de façon précise et structure ta réponse.
Si l'utilisateur demande de modifier un élément, propose la version amendée explicitement."""


def build_thesis_context(thesis: dict, hypotheses: list) -> str:
    hyp_text = "\n".join(
        [f"- {h.get('code')} ({h.get('criticality')}) : {h.get('label')}" for h in hypotheses]
    )
    return f"""Contexte : tu as produit une thèse d'investissement complète pour cette position.

THÈSE : {thesis.get('thesis_one_liner')}
BEAR STEEL MAN : {thesis.get('bear_steel_man')}
SCÉNARIOS : {json.dumps(thesis.get('scenarios_json'), ensure_ascii=False, indent=2)}
HYPOTHÈSES CLEFS :
{hyp_text}
SEUILS DE PRIX : {json.dumps(thesis.get('price_thresholds_json'), ensure_ascii=False, indent=2)}

Si tu amènes des modifications sur un ou plusieurs points, énonce explicitement la version amendée de chaque section concernée."""


async def start_watchlist_chat(watchlist_id: str, user_message: str, db) -> dict:
    item = await db.fetchrow("SELECT * FROM watchlist WHERE id = $1", watchlist_id)
    if not item:
        raise ValueError(f"Watchlist item {watchlist_id} not found")

    item_dict = dict(item)
    ticker = item_dict.get("ticker", "")
    context_message = build_watchlist_context(item_dict)

    headers = _get_headers()
    payload = {
        "message": {
            "content": context_message + "\n\n" + user_message,
            "mentions": [{"configurationId": AGENT_ID}],
            "context": {
                "username": "portfolio-tracker",
                "timezone": "Europe/Paris",
                "fullName": "Portfolio Tracker",
            }
        },
        "title": f"Analyse {ticker} — {datetime.now().strftime('%Y-%m-%d')}",
        "blocking": True,
    }

    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(
            f"{DUST_API_BASE}/w/{settings.DUST_WORKSPACE_ID}/assistant/conversations",
            headers=headers, json=payload,
        )
        if r.status_code == 429:
            raise ValueError("rate_limit")
        if r.status_code >= 500:
            raise ValueError("dust_error")
        r.raise_for_status()

    data = r.json()
    conv_id = data.get("conversation", {}).get("sId")
    response = _extract_agent_response(data)

    await db.execute(
        "UPDATE watchlist SET dust_conversation_id = $1 WHERE id = $2",
        conv_id, watchlist_id,
    )

    return {
        "agent_response": response["agent_response"],
        "chain_of_thought": response["chain_of_thought"],
        "conversation_id": conv_id,
    }


async def start_thesis_chat(position_id: str, thesis_id: str, user_message: str, db) -> dict:
    thesis = await db.fetchrow("SELECT * FROM theses WHERE id = $1", thesis_id)
    hypotheses = await db.fetch("SELECT * FROM hypotheses WHERE thesis_id = $1", thesis_id)
    pos = await db.fetchrow("SELECT ticker FROM positions WHERE id = $1", position_id)

    if not thesis:
        raise ValueError(f"Thesis {thesis_id} not found")

    thesis_dict = dict(thesis)
    hyp_list = [dict(h) for h in hypotheses]
    ticker = pos["ticker"] if pos else "?"

    context_message = build_thesis_context(thesis_dict, hyp_list)

    headers = _get_headers()
    payload = {
        "message": {
            "content": context_message + "\n\n" + user_message,
            "mentions": [{"configurationId": AGENT_ID}],
            "context": {
                "username": "portfolio-tracker",
                "timezone": "Europe/Paris",
                "fullName": "Portfolio Tracker",
            }
        },
        "title": f"Thèse {ticker} — {datetime.now().strftime('%Y-%m-%d')}",
        "blocking": True,
    }

    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(
            f"{DUST_API_BASE}/w/{settings.DUST_WORKSPACE_ID}/assistant/conversations",
            headers=headers, json=payload,
        )
        if r.status_code == 429:
            raise ValueError("rate_limit")
        if r.status_code >= 500:
            raise ValueError("dust_error")
        r.raise_for_status()

    data = r.json()
    conv_id = data.get("conversation", {}).get("sId")
    response = _extract_agent_response(data)

    await db.execute(
        "UPDATE theses SET dust_conversation_id = $1 WHERE id = $2",
        conv_id, thesis_id,
    )

    return {
        "agent_response": response["agent_response"],
        "chain_of_thought": response["chain_of_thought"],
        "conversation_id": conv_id,
    }


async def continue_chat(dust_conversation_id: str, user_message: str) -> dict:
    headers = _get_headers()
    payload = {
        "content": user_message,
        "mentions": [{"configurationId": AGENT_ID}],
        "context": {
            "username": "portfolio-tracker",
            "timezone": "Europe/Paris",
            "fullName": "Portfolio Tracker",
        },
        "blocking": True,
    }

    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(
            f"{DUST_API_BASE}/w/{settings.DUST_WORKSPACE_ID}/assistant/conversations/{dust_conversation_id}/messages",
            headers=headers, json=payload,
        )
        if r.status_code == 429:
            raise ValueError("rate_limit")
        if r.status_code >= 500:
            raise ValueError("dust_error")
        r.raise_for_status()
        data = r.json()

    response = _extract_agent_response(data)
    return {
        "agent_response": response["agent_response"],
        "chain_of_thought": response["chain_of_thought"],
    }


async def get_chat_history(dust_conversation_id: str) -> list:
    headers = _get_headers()
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{DUST_API_BASE}/w/{settings.DUST_WORKSPACE_ID}/assistant/conversations/{dust_conversation_id}",
            headers=headers,
        )
        r.raise_for_status()
        data = r.json()

    content_groups = data.get("conversation", {}).get("content", [])
    turns = []
    first_human_processed = False

    for group in content_groups:
        for msg in group:
            msg_type = msg.get("type")
            if msg_type == "user_message":
                raw_content = msg.get("content", "")
                if not first_human_processed and len(raw_content) > 1500:
                    raw_content = "[Contexte de l'analyse injecté automatiquement]"
                first_human_processed = True
                turns.append({
                    "role": "human",
                    "content": raw_content,
                    "chain_of_thought": None,
                    "created_at": msg.get("created"),
                })
            elif msg_type == "agent_message":
                content_text = "".join(
                    b.get("value", "") for b in msg.get("content", []) if b.get("type") == "text"
                )
                cot = msg.get("chainOfThought", "")
                turns.append({
                    "role": "agent",
                    "content": content_text,
                    "chain_of_thought": cot if cot else None,
                    "created_at": msg.get("created"),
                })

    return turns
