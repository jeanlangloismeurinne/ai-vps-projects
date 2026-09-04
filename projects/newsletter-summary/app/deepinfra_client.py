"""
Client DeepInfra pour newsletter-summary — endpoint OpenAI-compatible.

Interface publique :
  - chat(messages, model, temperature, max_tokens) -> str

Règles de robustesse :
  - Timeout explicite.
  - 1 retry automatique sur erreur réseau ou 5xx ; jamais de retry sur 4xx.
  - Aucun secret loggé.
  - DEEPINFRA_API_KEY vide -> RuntimeError à l'appel, pas à l'import.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

TIMEOUT_S: int = 120
_MAX_RETRIES: int = 1


def _get_headers() -> dict[str, str]:
    key = settings.DEEPINFRA_API_KEY
    if not key:
        raise RuntimeError(
            "DEEPINFRA_API_KEY est vide — configure-la dans les variables d'env Coolify."
        )
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _endpoint() -> str:
    base = (settings.DEEPINFRA_API_BASE or "https://api.deepinfra.com/v1/openai").rstrip("/")
    return f"{base}/chat/completions"


async def _post_with_retry(payload: dict[str, Any], timeout: int = TIMEOUT_S) -> dict[str, Any]:
    url = _endpoint()
    last_exc: Optional[Exception] = None

    for attempt in range(_MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.post(url, headers=_get_headers(), json=payload)

            if r.status_code >= 500:
                logger.error(
                    "DeepInfra %s (attempt %d/%d): %s",
                    r.status_code, attempt + 1, _MAX_RETRIES + 1, r.reason_phrase,
                )
                if attempt < _MAX_RETRIES:
                    last_exc = httpx.HTTPStatusError(
                        f"HTTP {r.status_code}", request=r.request, response=r
                    )
                    continue
                r.raise_for_status()

            if r.status_code >= 400:
                logger.error(
                    "DeepInfra %s (4xx, no retry): %s", r.status_code, r.reason_phrase
                )
                r.raise_for_status()

            return r.json()

        except httpx.TimeoutException as exc:
            logger.error("DeepInfra timeout (attempt %d/%d)", attempt + 1, _MAX_RETRIES + 1)
            last_exc = exc
            if attempt < _MAX_RETRIES:
                continue
            raise RuntimeError(
                "DeepInfra n'a pas répondu dans le délai imparti."
            ) from exc

        except httpx.HTTPStatusError:
            raise

        except httpx.RequestError as exc:
            logger.error(
                "DeepInfra réseau (attempt %d/%d): %s",
                attempt + 1, _MAX_RETRIES + 1, type(exc).__name__,
            )
            last_exc = exc
            if attempt < _MAX_RETRIES:
                continue
            raise RuntimeError(
                "DeepInfra : erreur réseau après retry."
            ) from exc

    raise RuntimeError("DeepInfra : échec inattendu après retry.") from last_exc


async def chat(
    messages: list[dict[str, Any]],
    model: str,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
    timeout: int = TIMEOUT_S,
) -> str:
    """Appel texte simple vers DeepInfra."""
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    data = await _post_with_retry(payload, timeout=timeout)

    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    content = msg.get("content") or ""

    usage = data.get("usage") or {}
    logger.debug(
        "DeepInfra chat — model=%s tokens_in=%s tokens_out=%s",
        data.get("model", model),
        usage.get("prompt_tokens", "?"),
        usage.get("completion_tokens", "?"),
    )

    # Troncature : le modèle a atteint max_tokens → sortie coupée. Le corps est de toute
    # façon rendu déterministe/équilibré côté digest, mais on le signale pour ajuster
    # max_tokens ou le prompt si ça se reproduit.
    if choice.get("finish_reason") == "length":
        logger.warning(
            "DeepInfra : sortie tronquée (finish_reason=length, max_tokens=%s, tokens_out=%s).",
            max_tokens, usage.get("completion_tokens", "?"),
        )

    return content
