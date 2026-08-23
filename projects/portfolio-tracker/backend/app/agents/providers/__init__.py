"""
Factory provider V2 — lit la config en DB (`agent_prompts`) et route vers le bon provider (§5.1).

Changer de provider/modèle d'un agent = `PATCH /admin/agents/{name}` (colonnes `provider`/`model`/
`tools_json`), jamais du code. `get_agent_provider(agent_name, flow_version)` renvoie un `ResolvedAgent`
déjà lié (prompt système + modèle + outils + provider) : le call-site appelle `.complete(messages, …)`
sans connaître le provider concret.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional

from app.db.database import get_db_session
from .base import AgentProvider, CompletionResult, MODEL_COSTS, compute_cost
from .deepinfra_provider import DeepInfraProvider
from .dust_provider import DustProvider

__all__ = [
    "AgentProvider", "CompletionResult", "MODEL_COSTS", "compute_cost",
    "ResolvedAgent", "get_provider", "get_agent_provider", "AgentNotFoundError",
]


class AgentNotFoundError(Exception):
    pass


# Providers sans état par appel → singletons. DeepInfra lit la clé au moment de l'appel.
_deepinfra_singleton: Optional[DeepInfraProvider] = None


def get_provider(provider_name: str, *, dust_agent_id: Optional[str] = None) -> AgentProvider:
    """Instancie (ou réutilise) un provider par son nom. `dust_agent_id` n'est requis que pour Dust."""
    global _deepinfra_singleton
    if provider_name == "deepinfra":
        if _deepinfra_singleton is None:
            _deepinfra_singleton = DeepInfraProvider()
        return _deepinfra_singleton
    if provider_name == "dust":
        return DustProvider(dust_agent_id=dust_agent_id)
    raise ValueError(f"Provider inconnu : {provider_name!r}")


@dataclass
class ResolvedAgent:
    """Un agent lié à sa config DB. Le prompt système (préambule + rôle) est figé en tête (cache §5.3)."""
    agent_name: str
    flow_version: str
    provider: AgentProvider
    model: str
    system_prompt: str
    tools: Optional[list[dict[str, Any]]] = None
    dust_agent_id: Optional[str] = None
    synced: bool = True

    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        response_format: Optional[dict[str, Any]] = None,
        tool_choice: Optional[str | dict] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        timeout: int = 720,
    ) -> CompletionResult:
        return await self.provider.complete(
            system=self.system_prompt, messages=messages, model=self.model,
            tools=self.tools, tool_choice=tool_choice, response_format=response_format,
            temperature=temperature, max_tokens=max_tokens, timeout=timeout,
        )

    async def stream(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        timeout: int = 720,
    ) -> AsyncIterator[dict[str, Any]]:
        async for event in self.provider.stream(
            system=self.system_prompt, messages=messages, model=self.model,
            temperature=temperature, max_tokens=max_tokens, timeout=timeout,
        ):
            yield event


async def get_agent_provider(agent_name: str, flow_version: str = "v2") -> ResolvedAgent:
    """Lit `agent_prompts (agent_name, flow_version)` et renvoie l'agent lié à son provider."""
    async with get_db_session() as db:
        row = await db.fetchrow(
            """
            SELECT agent_name, flow_version, provider, model, prompt_text,
                   tools_json, dust_agent_id, synced
            FROM agent_prompts
            WHERE agent_name = $1 AND flow_version = $2
            """,
            agent_name, flow_version,
        )
    if row is None:
        raise AgentNotFoundError(f"Agent introuvable : {agent_name!r} (flow {flow_version!r})")

    provider = get_provider(row["provider"], dust_agent_id=row["dust_agent_id"])
    return ResolvedAgent(
        agent_name=row["agent_name"],
        flow_version=row["flow_version"],
        provider=provider,
        model=row["model"] or "",
        system_prompt=row["prompt_text"] or "",
        tools=row["tools_json"],  # JSONB → déjà déserialisé par le codec asyncpg
        dust_agent_id=row["dust_agent_id"],
        synced=row["synced"],
    )
