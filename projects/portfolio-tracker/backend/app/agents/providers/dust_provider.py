"""
Provider Dust — shim de compatibilité (spec §5.1 : la factory doit pouvoir router vers Dust).

Rôle : compléter l'abstraction pour que `provider='dust'` (agents V1, flow_version='v1') passe par la
même factory. Les classes agent V1 (`opportunity_agent`, `thesis_agent`, `monitoring_agent_v1`)
continuent d'appeler `DustClient` DIRECTEMENT et restent inchangées — ce shim n'est pas sur leur
chemin chaud. Il existe pour que le flux V2 puisse, si besoin, adresser un agent Dust de façon
uniforme.

Dust identifie l'agent par `dust_agent_id` (configuré dans l'UI Dust) et détient le prompt côté Dust :
on n'envoie donc ni `system` ni `model` (ignorés), seulement le message. Le modèle est géré par Dust.
"""
from __future__ import annotations

from typing import Any, AsyncIterator, Optional

from ..dust_client import DustClient
from .base import AgentProvider, CompletionResult, compute_cost


def _flatten(system: str, messages: list[dict[str, Any]]) -> str:
    """Aplatit la conversation en un message Dust unique (l'agent Dust est stateless : tout le
    contexte pertinent doit être dans le message). `system` est ignoré (détenu par Dust)."""
    parts: list[str] = []
    for m in messages:
        content = m.get("content")
        if isinstance(content, list):  # tool/segments OpenAI — on ne garde que le texte
            content = "".join(
                (b.get("text") or b.get("content") or "") if isinstance(b, dict) else str(b)
                for b in content
            )
        if content:
            parts.append(str(content))
    return "\n\n".join(parts)


class DustProvider(AgentProvider):
    name = "dust"

    def __init__(self, dust_agent_id: Optional[str] = None):
        self.dust_agent_id = dust_agent_id
        self._client = DustClient()

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
        if not self.dust_agent_id:
            raise RuntimeError("DustProvider : dust_agent_id manquant (agent non configuré côté Dust).")
        res = await self._client.run_agent(
            self.dust_agent_id, _flatten(system, messages),
            model_override=model or None, temperature=temperature, timeout=timeout,
        )
        return CompletionResult(
            content=res.get("content", ""),
            model=res.get("model", model),
            tokens_in=res.get("tokens_input", 0),
            tokens_out=res.get("tokens_output", 0),
            cost_usd=res.get("cost_usd", 0.0),
            tool_calls=None,
            raw=res,
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
        if not self.dust_agent_id:
            raise RuntimeError("DustProvider : dust_agent_id manquant (agent non configuré côté Dust).")
        async for event in self._client.run_agent_streaming(
            self.dust_agent_id, _flatten(system, messages),
            model_override=model or None, timeout=timeout,
        ):
            yield event
