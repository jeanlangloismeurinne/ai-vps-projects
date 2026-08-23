"""
Provider DeepInfra — endpoint OpenAI-compatible (spec §5.1, cible V2, décision 2026-08-21).

Ne calque PAS `dust_client.run_agent` (consigne 00-REPRISE.md) : DeepInfra parle le dialecte
OpenAI `chat/completions` (`messages[]`, `tools[]`, `response_format`, `usage`), pas l'API Dust.
Clé `DEEPINFRA_API_KEY`. Modèle passé par appel (lu depuis `agent_prompts.model` par la factory).

Deux risques à valider au smoke-test (00-REPRISE.md) : (1) tool-calling fiable via l'endpoint
OpenAI-compat (boucle search-worker) ; (2) respect strict du JSON via `response_format`.
"""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Optional

import httpx

from app.config import settings
from .base import AgentProvider, CompletionResult, compute_cost

logger = logging.getLogger(__name__)


class DeepInfraProvider(AgentProvider):
    name = "deepinfra"

    def __init__(self):
        base = (settings.DEEPINFRA_API_BASE or "https://api.deepinfra.com/v1/openai").rstrip("/")
        self.url = f"{base}/chat/completions"
        self.api_key = settings.DEEPINFRA_API_KEY

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise RuntimeError(
                "DEEPINFRA_API_KEY absente — configure-la dans Coolify avant d'appeler un agent V2."
            )
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    @staticmethod
    def _build_messages(system: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # System figé en tête (prompt caching §5.3) ; volatile (query du tour) en fin.
        out: list[dict[str, Any]] = []
        if system:
            out.append({"role": "system", "content": system})
        out.extend(messages)
        return out

    def _payload(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        model: str,
        tools: Optional[list[dict[str, Any]]],
        tool_choice: Optional[str | dict],
        response_format: Optional[dict[str, Any]],
        temperature: float,
        max_tokens: Optional[int],
        stream: bool,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": self._build_messages(system, messages),
            "temperature": temperature,
            "stream": stream,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = tools
            if tool_choice is not None:
                payload["tool_choice"] = tool_choice
        if response_format is not None:
            payload["response_format"] = response_format
        return payload

    async def complete(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        model: str,
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Optional[str | dict] = None,
        response_format: Optional[dict[str, Any]] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        timeout: int = 720,
    ) -> CompletionResult:
        payload = self._payload(
            system=system, messages=messages, model=model, tools=tools,
            tool_choice=tool_choice, response_format=response_format,
            temperature=temperature, max_tokens=max_tokens, stream=False,
        )
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.post(self.url, headers=self._headers(), json=payload)
                if r.status_code >= 400:
                    logger.error("DeepInfra %s: %s", r.status_code, r.text[:400])
                r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"DeepInfra a retourné une erreur {e.response.status_code} — "
                f"l'appel n'a pas abouti, tu peux relancer sans risque"
            ) from e
        except httpx.TimeoutException as e:
            raise RuntimeError(
                "DeepInfra n'a pas répondu dans le délai imparti — tu peux relancer sans risque"
            ) from e

        data = r.json()
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message", {}) or {}
        usage = data.get("usage", {}) or {}
        tin = usage.get("prompt_tokens", 0) or 0
        tout = usage.get("completion_tokens", 0) or 0

        return CompletionResult(
            content=msg.get("content") or "",
            model=data.get("model", model),
            tokens_in=tin,
            tokens_out=tout,
            cost_usd=compute_cost(model, tin, tout),
            tool_calls=msg.get("tool_calls"),
            finish_reason=choice.get("finish_reason"),
            raw=data,
        )

    async def stream(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        model: str,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        timeout: int = 720,
    ) -> AsyncIterator[dict[str, Any]]:
        payload = self._payload(
            system=system, messages=messages, model=model, tools=None,
            tool_choice=None, response_format=None, temperature=temperature,
            max_tokens=max_tokens, stream=True,
        )
        yield {"type": "started"}
        parts: list[str] = []
        tin = tout = 0
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("POST", self.url, headers=self._headers(), json=payload) as r:
                    if r.status_code >= 400:
                        body = (await r.aread()).decode(errors="replace")[:400]
                        logger.error("DeepInfra stream %s: %s", r.status_code, body)
                        raise RuntimeError(f"DeepInfra a retourné une erreur {r.status_code}")
                    async for line in r.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data_str = line[len("data:"):].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        ch = (chunk.get("choices") or [{}])[0]
                        delta = ch.get("delta", {}) or {}
                        piece = delta.get("content")
                        if piece:
                            parts.append(piece)
                            yield {"type": "tokens", "text": piece}
                        if chunk.get("usage"):
                            tin = chunk["usage"].get("prompt_tokens", tin) or tin
                            tout = chunk["usage"].get("completion_tokens", tout) or tout
        except httpx.TimeoutException as e:
            raise RuntimeError("DeepInfra (stream) n'a pas répondu à temps — relance possible") from e

        content = "".join(parts)
        yield {
            "type": "done",
            "content": content,
            "tokens_input": tin,
            "tokens_output": tout,
            "cost_usd": compute_cost(model, tin, tout),
            "model": model,
        }
