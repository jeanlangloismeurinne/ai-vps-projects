"""
Runner agent V2 — exécute un `ResolvedAgent` en mode JSON strict et VALIDE la sortie contre son
contrat Pydantic figé (G1). Point de passage unique des agents métier de la chaîne d'analyse.

Deux voies :
  - **run_json_agent** : voie nominale. Appelle `.complete(response_format=json_object)`, extrait le
    JSON, le valide contre le schéma Pydantic du contrat. En cas d'échec (JSON illisible ou champ
    hors contrat / manquant — `extra='forbid'` verrouille Q2), UNE tentative de réparation en
    réinjectant l'erreur au modèle. Au-delà : `AgentOutputInvalid` (sous-classe de RuntimeError)
    qui PORTE la dépense réellement engagée et le texte fautif — un abandon est facturé comme un
    succès, il doit être comptabilisé comme tel.
  - **run_tool_agent** : boucle tool-calling brute (search-worker) — `tool_executors` fournis par
    l'appelant. Rend le texte du dernier tour, sans validation.
  - **run_tool_json_agent** : voie réellement utilisée par le search-worker. Même boucle d'outils,
    suivie d'un tour de CLÔTURE en JSON strict validé contre le contrat. Ce tour final est émis par
    un clone de l'agent SANS outils : tant que `tools` est exposé, un modèle peut répondre par un
    tool_call de plus au lieu du JSON demandé, et on n'aurait alors ni sortie ni erreur claire.

Le runner ne touche PAS la DB : il renvoie la sortie validée + le coût. La persistance
(investment_analyses / research_memos + snapshot des refs) est à la charge de l'agent appelant.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, replace
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


class AgentOutputInvalid(RuntimeError):
    """Sortie non conforme au contrat après épuisement des réparations — AVEC la télémétrie.

    Le runner levait auparavant un `RuntimeError` nu. Les tours étaient pourtant bel et bien
    facturés : l'appelant persistait donc un échec à **0 token / $0**, et le texte fautif — la
    seule pièce qui permette de diagnostiquer *pourquoi* le modèle est sorti du contrat — était
    jeté. Un échec qui ne coûte rien dans les comptes est un échec qu'on ne cherche pas à réduire.

    Sous-classe de `RuntimeError` **à dessein** : les appelants existants font `except RuntimeError`
    et continuent de fonctionner sans modification. Les attributs portent exactement les noms lus
    par les `_persister_echec` (`tokens_in`, `tokens_out`, `cost_usd`, `raw_content`), si bien que
    l'exception peut être passée telle quelle en `run=`.
    """

    def __init__(
        self,
        *,
        agent_name: str,
        schema_name: str,
        attempts: int,
        last_error: Optional[str],
        raw_content: str,
        tokens_in: int,
        tokens_out: int,
        cost_usd: float,
    ) -> None:
        super().__init__()
        self.agent_name = agent_name
        self.schema_name = schema_name
        self.attempts = attempts
        self.last_error = last_error
        self.raw_content = raw_content
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.cost_usd = cost_usd

    def add_upstream(self, tokens_in: int, tokens_out: int, cost_usd: float, iterations: int) -> "AgentOutputInvalid":
        """Ajoute la dépense d'une phase AMONT (boucle d'outils) à l'échec de la clôture.

        Sans ce report, `run_tool_json_agent` perd la part la PLUS grosse de la facture : la boucle
        d'outils compte plusieurs tours à gros contexte, la clôture un seul. Ne touche pas
        `raw_content`, qui doit rester le texte du tour fautif — celui de la clôture.
        """
        self.tokens_in += tokens_in
        self.tokens_out += tokens_out
        self.cost_usd += cost_usd
        self.attempts += iterations
        return self

    def __str__(self) -> str:  # recalculé : `add_upstream` peut avoir bougé les compteurs
        return (
            f"Agent {self.agent_name} : sortie non conforme à {self.schema_name} après "
            f"{self.attempts} tentative(s), {self.tokens_in} tokens in / {self.tokens_out} out "
            f"facturés (${self.cost_usd:.6f}). Dernière erreur : {self.last_error}"
        )


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
    json_object: bool = True,
) -> AgentRunResult:
    """Exécute `agent`, valide la sortie contre `schema` (Pydantic). Réparation ≤ max_repair fois.

    `json_object=False` désactive `response_format={"type":"json_object"}` et s'en remet au JSON
    demandé en prompt + `extract_json` (tolérant fences/texte autour). ⚠️ Mesuré le 2026-08-26 :
    DeepSeek-V4-Flash est NON FIABLE en mode json_object (il collapse sur `{}`, ou emballe la sortie
    dans un objet parasite `{"./": "<json échappé>"}`) alors qu'en prompt-only il rend un JSON propre.
    À garder à l'esprit pour la chaîne d'analyse (qui appelle ce runner)."""
    convo = list(messages)
    total_in = total_out = 0
    total_cost = 0.0
    last: Optional[CompletionResult] = None
    resp_fmt = {"type": "json_object"} if json_object else None

    for attempt in range(1, max_repair + 2):
        last = await agent.complete(
            convo,
            response_format=resp_fmt,
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
            logger.error(
                "run_json_agent(%s): échec validation après %d essais — %d/%d tokens facturés ($%.6f)",
                agent.agent_name, attempt, total_in, total_out, total_cost,
            )
            raise AgentOutputInvalid(
                agent_name=agent.agent_name,
                schema_name=schema.__name__,
                attempts=attempt,
                last_error=err,
                raw_content=last.content or "",
                tokens_in=total_in,
                tokens_out=total_out,
                cost_usd=total_cost,
            )
        # feedback de réparation : on montre la sortie fautive puis l'erreur (tour utilisateur)
        convo = convo + [
            {"role": "assistant", "content": last.content},
            {"role": "user", "content": err},
        ]

    raise RuntimeError(f"Agent {agent.agent_name} : échec inattendu du runner")  # pragma: no cover


# ── Boucle tool-calling (search-worker) ──────────────────────────────────────────────────────────
ToolExecutor = Callable[[dict[str, Any]], Awaitable[Any]]


@dataclass
class _ToolLoopState:
    convo: list[dict[str, Any]]
    tokens_in: int
    tokens_out: int
    cost_usd: float
    last: CompletionResult
    iterations: int
    exhausted: bool  # sorti sur max_iterations alors que le modèle appelait encore des outils


async def _tool_loop(
    agent: ResolvedAgent,
    messages: list[dict[str, Any]],
    tool_executors: dict[str, ToolExecutor],
    *,
    max_iterations: int,
    temperature: float,
    timeout: int,
) -> _ToolLoopState:
    """Tant que le modèle émet des tool_calls : exécuter, réinjecter en `role=tool`, reboucler.

    Un exécuteur qui lève ne casse PAS la boucle — l'erreur est rendue au modèle comme résultat
    d'outil, à lui d'en tirer les conséquences (chercher autrement, ou déclarer non couvert).
    """
    convo = list(messages)
    total_in = total_out = 0
    total_cost = 0.0
    last: Optional[CompletionResult] = None
    iterations = 0
    exhausted = True

    for iterations in range(1, max_iterations + 1):
        last = await agent.complete(convo, temperature=temperature, timeout=timeout)
        total_in += last.tokens_in
        total_out += last.tokens_out
        total_cost += last.cost_usd

        if not last.tool_calls:
            exhausted = False
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
                    logger.warning("outil %s en échec : %s", name, e)
                    result = {"error": str(e)}
            convo.append({
                "role": "tool",
                "tool_call_id": call.get("id"),
                "name": name,
                "content": result if isinstance(result, str) else json.dumps(result, ensure_ascii=False),
            })

    if last is None:  # pragma: no cover
        raise RuntimeError(f"Agent {agent.agent_name} : boucle tool vide")
    return _ToolLoopState(convo, total_in, total_out, total_cost, last, iterations, exhausted)


async def run_tool_agent(
    agent: ResolvedAgent,
    messages: list[dict[str, Any]],
    tool_executors: dict[str, ToolExecutor],
    *,
    max_iterations: int = 6,
    temperature: float = 0.2,
    timeout: int = 720,
) -> AgentRunResult:
    """Boucle d'outils brute : renvoie le texte du dernier tour, sans validation de contrat.
    Pour un agent qui doit rendre un JSON contractuel, utiliser `run_tool_json_agent`."""
    st = await _tool_loop(
        agent, messages, tool_executors,
        max_iterations=max_iterations, temperature=temperature, timeout=timeout,
    )
    return AgentRunResult(
        parsed=None,  # type: ignore[arg-type]  — voie non-JSON, parsing à la charge de l'appelant
        data={},
        raw_content=st.last.content or "",
        completion=st.last,
        tokens_in=st.tokens_in,
        tokens_out=st.tokens_out,
        cost_usd=st.cost_usd,
        attempts=st.iterations,
    )


async def run_tool_json_agent(
    agent: ResolvedAgent,
    messages: list[dict[str, Any]],
    tool_executors: dict[str, ToolExecutor],
    schema: Type[T],
    *,
    closing_instruction: str,
    max_iterations: int = 6,
    temperature: float = 0.2,
    max_repair: int = 1,
    timeout: int = 720,
) -> AgentRunResult:
    """Boucle d'outils PUIS tour de clôture en JSON strict validé contre `schema`.

    Le tour de clôture est joué par un clone de l'agent **sans `tools`** : c'est ce qui garantit
    qu'il ne peut pas repartir en tool_call. On y réutilise l'intégralité de la conversation (donc
    les résultats d'outils), et la réparation de `run_json_agent` s'applique — mais elle ne redonne
    jamais accès aux outils : le modèle corrige la FORME de ce qu'il a déjà collecté, il ne relance
    pas de recherche pour combler un manque, sans quoi le plafond de `max_iterations` ne voudrait
    plus rien dire.

    Les coûts de la boucle et de la clôture sont cumulés — un run d'ouvrier a un coût unique auditable.
    """
    st = await _tool_loop(
        agent, messages, tool_executors,
        max_iterations=max_iterations, temperature=temperature, timeout=timeout,
    )
    if st.exhausted:
        logger.warning(
            "run_tool_json_agent(%s): %d itérations d'outils épuisées — clôture sur ce qui a été "
            "collecté", agent.agent_name, max_iterations,
        )

    # `st.convo` contient déjà les tours assistant→outils exécutés. Le dernier message assistant
    # sans tool_call, lui, n'y est pas : c'est du texte libre que la clôture doit remplacer, pas
    # prolonger — on ne le réinjecte donc pas.
    closing = st.convo + [{"role": "user", "content": closing_instruction}]

    closer = replace(agent, tools=None)
    try:
        final = await run_json_agent(
            closer, closing, schema,
            temperature=temperature, max_repair=max_repair, timeout=timeout,
        )
    except AgentOutputInvalid as e:
        # La boucle d'outils a été payée AVANT que la clôture n'échoue. Ne pas la reporter ici
        # revient à déclarer gratuit un run d'ouvrier qui a pu coûter plusieurs tours à gros
        # contexte — c'est la part dominante de la facture, pas un arrondi.
        raise e.add_upstream(st.tokens_in, st.tokens_out, st.cost_usd, st.iterations)
    return AgentRunResult(
        parsed=final.parsed,
        data=final.data,
        raw_content=final.raw_content,
        completion=final.completion,
        tokens_in=st.tokens_in + final.tokens_in,
        tokens_out=st.tokens_out + final.tokens_out,
        cost_usd=st.cost_usd + final.cost_usd,
        attempts=st.iterations + final.attempts,
    )
