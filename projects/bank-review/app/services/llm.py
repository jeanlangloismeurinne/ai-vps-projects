"""Helper LLM : Claude (Anthropic) en primaire, DeepInfra (DeepSeek, OpenAI-compat) en repli.

Si l'appel Anthropic échoue pour n'importe quelle raison (panne, quota, auth, réseau), la même
requête logique est rejouée contre l'endpoint OpenAI-compatible de DeepInfra. Le prompt caching
est propre à Anthropic : il est simplement abandonné sur le chemin de repli.

Variables d'environnement :
- `ANTHROPIC_API_KEY` — clé Claude (primaire).
- `DEEPINFRA_API_KEY` — clé DeepInfra (repli). Absente ⇒ pas de repli, l'erreur Claude remonte.
- `DEEPINFRA_MODEL` — défaut `deepseek-ai/DeepSeek-V4-Flash-0731`.
- `DEEPINFRA_API_BASE` — défaut `https://api.deepinfra.com/v1/openai`.
"""
import os
import logging

import httpx
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

CLAUDE_HAIKU = "claude-haiku-4-5-20251001"
DEEPINFRA_MODEL = os.getenv("DEEPINFRA_MODEL", "deepseek-ai/DeepSeek-V4-Flash-0731")
DEEPINFRA_API_BASE = os.getenv("DEEPINFRA_API_BASE", "https://api.deepinfra.com/v1/openai")


async def deepinfra_complete(*, system: str, user: str, max_tokens: int = 512,
                             temperature: float = 0.0) -> str:
    """Appel DeepInfra (OpenAI-compat). Lève si la clé est absente ou si l'appel échoue."""
    key = os.getenv("DEEPINFRA_API_KEY", "")
    if not key:
        raise RuntimeError(
            "Claude a échoué et DEEPINFRA_API_KEY est absente — aucun repli LLM disponible"
        )
    url = DEEPINFRA_API_BASE.rstrip("/") + "/chat/completions"
    payload = {
        "model": DEEPINFRA_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    async with httpx.AsyncClient(timeout=120) as http:
        r = await http.post(
            url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
        )
        r.raise_for_status()
    data = r.json()
    return ((data.get("choices") or [{}])[0].get("message", {}) or {}).get("content", "").strip()


async def complete_text(*, system: str, user: str, max_tokens: int = 512,
                        claude_model: str = CLAUDE_HAIKU, temperature: float = 0.0) -> str:
    """Renvoie le texte du modèle. Claude d'abord ; DeepInfra sur toute erreur Claude."""
    try:
        client = AsyncAnthropic()
        resp = await client.messages.create(
            model=claude_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        logger.warning("Claude indisponible (%s) — bascule sur DeepInfra", e)
        return await deepinfra_complete(
            system=system, user=user, max_tokens=max_tokens, temperature=temperature
        )
