"""
Runner agent V2 — exécute un `ResolvedAgent` en mode JSON strict et VALIDE la sortie contre son
contrat Pydantic figé (G1). Point de passage unique des agents métier de la chaîne d'analyse.

Deux voies :
  - **run_json_agent** : voie nominale. Appelle `.complete(response_format=json_object)`, extrait le
    JSON, le valide contre le schéma Pydantic du contrat. En cas d'échec (JSON illisible ou champ
    hors contrat / manquant — `extra='forbid'` verrouille Q2), UNE tentative de réparation en
    réinjectant l'erreur au modèle. Au-delà : RuntimeError claire (l'appelant relance).
  - **run_tool_agent** : boucle tool-calling (search-worker). Écrite ici mais non exercée tant que
    web_search n'a pas de backend (SearXNG/API absent) — `tool_executors` fournis par l'appelant.

Le runner ne touche PAS la DB : il renvoie la sortie validée + le coût. La persistance
(investment_analyses / research_memos + snapshot des refs) est à la charge de l'agent appelant.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from app.agents.providers import CompletionResult, ResolvedAgent

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_JSON_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def extract_json(content: str) -> dict[str, Any]:
    """Extrait un objet JSON du texte du modèle. Tolère un fence ```json et du texte parasite avant/
    après (on isole le premier `{` … dernier `}`). Lève json.JSONDecodeError si rien d'exploitable."""
    s = _JSON_FENCE.sub("", content.strip())
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        start, end = s.find("{"), s.rfind("}")
        if start != -1 and end > start:
            return json.loads(s[start : end + 1])
        raise


@dataclass
class AgentRunResult:
    """Sortie validée d'un agent JSON + métadonnées d'appel (pour persistance/audit)."""
    parsed: BaseModel
    data: dict[str, Any]          # dict validé (parsed.model_dump(mode='json'))
    raw_content: str              # texte brut du modèle (dernier tour)
    completion: CompletionResult  # tokens / coût / modèle du dernier appel
    tokens_in: int                # cumulés sur tentatives
    tokens_out: int
    cost_usd: float
    attempts: int


async def run_json_agent(
    agent: ResolvedAgent,
    messages: list[dict[str, Any]],
    schema: Type[T],
    *,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
    max_repair: int = 1,
    timeout: int = 720,
) -> AgentRunResult:
    """Exécute `agent`, valide la sortie contre `schema` (Pydantic). Réparation ≤ max_repair fois."""
    convo = list(messages)
    total_in = total_out = 0
    total_cost = 0.0
    last: Optional[CompletionResult] = None

    for attempt in range(1, max_repair + 2):
        last = await agent.complete(
            convo,
            response_format={"type": "json_object"},
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        total_in += last.tokens_in
        total_out += last.tokens_out
        total_cost += last.cost_usd

        err: Optional[str] = None
        try:
            data = extract_json(last.content)
        except json.JSONDecodeError as e:
            err = f"Sortie non-JSON ({e}). Réponds UNIQUEMENT avec l'objet JSON du contrat, sans texte."
        else:
            try:
                parsed = schema.model_validate(data)
                return AgentRunResult(
                    parsed=parsed,
                    data=parsed.model_dump(mode="json"),
                    raw_content=last.content,
                    completion=last,
                    tokens_in=total_in,
                    tokens_out=total_out,
                    cost_usd=total_cost,
                    attempts=attempt,
                )
            except ValidationError as e:
                err = (
                    f"Le JSON ne respecte pas le contrat {schema.__name__}. Erreurs Pydantic :\n"
                    f"{e}\nCorrige EXACTEMENT ces points et renvoie l'objet complet."
                )

        if attempt >= max_repair + 1:
            logger.error("run_json_agent(%s): échec validation après %d essais", agent.agent_name, attempt)
            raise RuntimeError(
                f"Agent {agent.agent_name} : sortie non conforme à {schema.__name__} "
                f"après {attempt} tentative(s). Dernière erreur : {err}"
            )
        # feedback de réparation : on montre la sortie fautive puis l'erreur (tour utilisateur)
        convo = convo + [
            {"role": "assistant", "content": last.content},
            {"role": "user", "content": err},
        ]

    raise RuntimeError(f"Agent {agent.agent_name} : échec inattendu du runner")  # pragma: no cover


# ── Boucle tool-calling (search-worker) — non exercée tant que web_search sans backend ───────────
ToolExecutor = Callable[[dict[str, Any]], Awaitable[Any]]


async def run_tool_agent(
    agent: ResolvedAgent,
    messages: list[dict[str, Any]],
    tool_executors: dict[str, ToolExecutor],
    *,
    max_iterations: int = 6,
    temperature: float = 0.2,
    timeout: int = 720,
) -> AgentRunResult:
    """Boucle OpenAI tool-calling : tant que le modèle émet des tool_calls, on exécute les outils
    (via `tool_executors[name]`) et on réinjecte les résultats en messages `role=tool`, jusqu'à une
    réponse finale sans tool_call ou `max_iterations`. Renvoie la dernière complétion (contenu brut).

    NB : `web_search` requiert SearXNG/API (absent) — cette voie n'est activable qu'une fois l'infra
    de recherche provisionnée. `fetch_url`/`query_knowledge` sont eux réalisables (httpx / DB).
    """
    convo = list(messages)
    total_in = total_out = 0
    total_cost = 0.0
    last: Optional[CompletionResult] = None

    for _ in range(max_iterations):
        last = await agent.complete(convo, temperature=temperature, timeout=timeout)
        total_in += last.tokens_in
        total_out += last.tokens_out
        total_cost += last.cost_usd

        if not last.tool_calls:
            break

        convo.append({"role": "assistant", "content": last.content or "", "tool_calls": last.tool_calls})
        for call in last.tool_calls:
            fn = call.get("function", {}) or {}
            name = fn.get("name", "")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            executor = tool_executors.get(name)
            if executor is None:
                result: Any = {"error": f"outil inconnu : {name}"}
            else:
                try:
                    result = await executor(args)
                except Exception as e:  # noqa: BLE001 — on renvoie l'échec au modèle, pas de crash
                    result = {"error": str(e)}
            convo.append({
                "role": "tool",
                "tool_call_id": call.get("id"),
                "name": name,
                "content": result if isinstance(result, str) else json.dumps(result, ensure_ascii=False),
            })

    if last is None:  # pragma: no cover
        raise RuntimeError(f"Agent {agent.agent_name} : boucle tool vide")
    return AgentRunResult(
        parsed=None,  # type: ignore[arg-type]  — voie non-JSON, parsing à la charge de l'appelant
        data={},
        raw_content=last.content or "",
        completion=last,
        tokens_in=total_in,
        tokens_out=total_out,
        cost_usd=total_cost,
        attempts=1,
    )
