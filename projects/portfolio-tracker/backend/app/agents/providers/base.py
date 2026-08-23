"""
Abstraction provider V2 (provider-agnostic) — spec 01-spec-v2-unifiee.md §5.1, constitution §6.

Interface commune `AgentProvider` par laquelle passe TOUT agent V2. Aucun appel direct à un SDK de
modèle dans la logique métier : on change de provider/modèle en changeant une valeur en DB
(`agent_prompts.provider` / `.model` / `.tools_json`), pas du code (§5.1).

Ce module ne dépend d'aucun provider concret : il définit le contrat (`AgentProvider`), le résultat
normalisé (`CompletionResult`) et la table de coûts. Les implémentations vivent dans
`deepinfra_provider.py` (cible V2) et `dust_provider.py` (compat V1). La factory est dans `__init__.py`.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional


# ── Coûts par modèle ($ / 1M tokens) ─────────────────────────────────────────
# Source : table « Décision modèles DeepInfra » (00-REPRISE.md, arrêtée 2026-08-21).
# À reconfirmer à chaque changement de tarif DeepInfra. Le fallback couvre un modèle inconnu
# (on ne bloque pas un appel pour un coût non tabulé — on l'estime prudemment).
MODEL_COSTS: dict[str, dict[str, float]] = {
    # model_id DeepInfra                          input   output
    "deepseek-ai/DeepSeek-V4-Flash-0731": {"input": 0.08, "output": 0.18},
    "zai-org/GLM-4.7-Flash":              {"input": 0.06, "output": 0.40},
    "google/gemma-4-26B-A4B-it":          {"input": 0.07, "output": 0.34},
    "Qwen/Qwen3.6-35B-A3B":               {"input": 0.10, "output": 0.95},
}
_FALLBACK_COST = {"input": 0.10, "output": 0.95}  # le plus cher de la liste — prudent


def compute_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Coût USD d'un appel. Prix exprimés en $/1M tokens."""
    c = MODEL_COSTS.get(model, _FALLBACK_COST)
    return tokens_in * c["input"] / 1_000_000 + tokens_out * c["output"] / 1_000_000


# ── Résultat normalisé ───────────────────────────────────────────────────────
@dataclass
class CompletionResult:
    """Sortie normalisée d'un appel provider, indépendante du provider concret.

    `content` est le texte brut du modèle (JSON strict attendu pour les agents V2 — le parsing/
    validation Pydantic est à la charge de l'appelant, pas du provider). `tool_calls` porte les
    appels d'outils émis par le modèle (search-worker) au format OpenAI, ou None.
    """
    content: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    tool_calls: Optional[list[dict[str, Any]]] = None
    finish_reason: Optional[str] = None
    raw: dict[str, Any] = field(default_factory=dict)


# ── Contrat provider ─────────────────────────────────────────────────────────
class AgentProvider(abc.ABC):
    """Interface unique des providers de modèle (§5.1). Deux méthodes : `complete` (bloquant,
    voie nominale des agents V2 qui émettent du JSON) et `stream` (SSE, pour l'UX de dialogue).

    Conventions communes à toutes les implémentations :
      - `system` : bloc système figé (préambule + rôle) — placé en TÊTE pour le prompt caching (§5.3).
      - `messages` : liste OpenAI-like `[{"role": "user"|"assistant"|"tool", "content": ...}, …]`.
      - `tools` / `tool_choice` : schémas d'outils OpenAI (search-worker) ; None sinon.
      - `response_format` : ex `{"type": "json_object"}` pour forcer le JSON strict (G1).
      - Aucun retry : en cas d'échec on lève une RuntimeError à message clair (l'appelant relance).
    """

    name: str = "base"

    @abc.abstractmethod
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
        ...

    @abc.abstractmethod
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
        """Générateur d'events compat UI : `{"type": "started"}`, `{"type": "tokens", "text": …}`
        (incrémental), `{"type": "done", "content": …, "tokens_input": …, "tokens_output": …,
        "cost_usd": …, "model": …}`. Aligné sur `DustClient.run_agent_streaming`."""
        raise NotImplementedError
        yield  # pragma: no cover  (marque la coroutine comme async generator)
