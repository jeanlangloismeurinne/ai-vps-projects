import httpx
import logging
from fastapi import APIRouter, HTTPException
from app.config import settings

router = APIRouter(prefix="/dust-runs", tags=["dust-runs"])
logger = logging.getLogger(__name__)
DUST_API_BASE = "https://dust.tt/api/v1"


@router.get("/conversation/{dust_conversation_id}")
async def get_conversation(dust_conversation_id: str):
    headers = {"Authorization": f"Bearer {settings.DUST_API_KEY}"}
    url = f"{DUST_API_BASE}/w/{settings.DUST_WORKSPACE_ID}/assistant/conversations/{dust_conversation_id}"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, headers=headers)
    if r.status_code == 404:
        raise HTTPException(404, "Conversation not found")
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
                    "created_at": msg.get("created"),
                })
            elif msg_type == "agent_message":
                content_blocks = msg.get("content", [])
                parts = []
                for b in content_blocks:
                    if isinstance(b, str):
                        parts.append(b)
                    elif isinstance(b, dict) and b.get("type") == "text":
                        parts.append(b.get("value") or b.get("text") or "")
                content_text = "".join(parts)
                cot = msg.get("chainOfThought", "")
                actions = msg.get("actions", [])
                tools_used = []
                for action in actions:
                    name = action.get("type", "")
                    if action.get("query"):
                        tools_used.append(f"{name}: '{action['query']}'")
                    elif action.get("input"):
                        tools_used.append(f"{name}")
                    else:
                        tools_used.append(name)
                turns.append({
                    "role": "agent",
                    "content": content_text,
                    "chain_of_thought": cot if cot else None,
                    "tools_used": tools_used,
                    "created_at": msg.get("created"),
                    "agent_version": msg.get("configuration", {}).get("version"),
                })

    return {"turns": turns, "total_messages": len(turns), "conversation_id": dust_conversation_id}


@router.get("/agent-version/{agent_s_id}")
async def get_agent_version(agent_s_id: str):
    headers = {"Authorization": f"Bearer {settings.DUST_API_KEY}"}
    url = f"{DUST_API_BASE}/w/{settings.DUST_WORKSPACE_ID}/assistant/agent_configurations/{agent_s_id}?variant=light"
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url, headers=headers)
    if r.status_code == 404:
        raise HTTPException(404, "Agent not found")
    r.raise_for_status()
    data = r.json()
    cfg = data.get("agentConfiguration", {})
    return {
        "agent_id": agent_s_id,
        "version": cfg.get("version"),
        "name": cfg.get("name"),
        "status": cfg.get("status"),
    }
