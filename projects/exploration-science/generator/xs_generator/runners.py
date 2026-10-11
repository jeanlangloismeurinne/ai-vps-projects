"""Runners: who answers a request. The pipeline does not know which one it uses."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

from .calls import GeneratorError, Request, Response, Usage, cost_usd, load_response


class Runner(Protocol):
    name: str
    #: True when the same request always gives the same recorded answer back.
    reproducible: bool

    def complete(self, request: Request, call_dir: Path) -> Response: ...


class AnthropicRunner:
    """The Claude API, through the official SDK. Streaming, adaptive thinking, effort per step."""

    name = "anthropic"
    reproducible = True  # once recorded: a replay of the run returns the same bytes

    def __init__(self) -> None:
        import anthropic

        if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
            raise GeneratorError(
                "runner 'anthropic': no ANTHROPIC_API_KEY in the environment. "
                "Put the key in the generator's .env on the VPS (chmod 600), or use --runner manual / replay."
            )
        # The base URL is pinned on purpose: development shells may export ANTHROPIC_BASE_URL
        # for their own tooling, and generator calls must not silently go through it.
        base_url = os.environ.get("XS_ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        self._anthropic = anthropic
        self._client = anthropic.Anthropic(base_url=base_url)

    def complete(self, request: Request, call_dir: Path) -> Response:
        anthropic = self._anthropic
        try:
            # Server-side fallback ("default" mode): a declined request is re-run on the
            # recommended model instead of coming back as a refusal.
            with self._client.beta.messages.stream(
                model=request.model,
                max_tokens=request.max_tokens,
                system=[{"type": "text", "text": request.system, "cache_control": {"type": "ephemeral"}}],
                messages=list(request.messages),
                thinking={"type": "adaptive"},
                output_config={"effort": request.effort},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            ) as stream:
                message = stream.get_final_message()
        except anthropic.AuthenticationError:
            raise GeneratorError("runner 'anthropic': the API rejected the key (401). Check ANTHROPIC_API_KEY.") from None
        except anthropic.RateLimitError:
            raise GeneratorError("runner 'anthropic': rate limited (429). Run again later; recorded steps are kept.") from None
        except anthropic.APIStatusError as error:
            raise GeneratorError(f"runner 'anthropic': API error {error.status_code}: {error.message}") from None
        except anthropic.APIConnectionError:
            raise GeneratorError("runner 'anthropic': cannot reach the API (network).") from None

        if message.stop_reason == "refusal":
            raise GeneratorError(f"runner 'anthropic': the request was declined ({message.stop_details}).")
        if message.stop_reason == "max_tokens":
            raise GeneratorError(f"runner 'anthropic': output cut at max_tokens={request.max_tokens}; raise it for step '{request.step}'.")
        text = "".join(block.text for block in message.content if block.type == "text")
        u = message.usage
        usage = Usage(
            input_tokens=u.input_tokens or 0,
            output_tokens=u.output_tokens or 0,
            cache_creation_input_tokens=u.cache_creation_input_tokens or 0,
            cache_read_input_tokens=u.cache_read_input_tokens or 0,
        )
        # A fallback may have served the turn: price it at the model that answered.
        return Response(text=text, runner=self.name, model=message.model, stop_reason=message.stop_reason, usage=usage, cost_usd=cost_usd(message.model, usage))


class PendingManualStep(GeneratorError):
    """The request is on disk and waits for a written response."""


class ManualRunner:
    """A person (or Claude Code while developing) answers. Not reproducible: no model ran.

    First pass: writes ``request.md`` (system prompt + messages) in the call folder and
    stops. Once ``response.txt`` is written next to it, the next pass picks it up.
    """

    name = "manual"
    reproducible = False

    def complete(self, request: Request, call_dir: Path) -> Response:
        answer = call_dir / "response.txt"
        if answer.exists():
            return Response(text=answer.read_text(encoding="utf-8"), runner=self.name)
        call_dir.mkdir(parents=True, exist_ok=True)
        parts = [f"# Step `{request.step}` — model {request.model}, effort {request.effort}", "", "## System", "", request.system]
        for message in request.messages:
            parts += ["", f"## {message['role']}", "", message["content"]]
        (call_dir / "request.md").write_text("\n".join(parts) + "\n", encoding="utf-8")
        raise PendingManualStep(f"manual step waiting: answer {call_dir / 'request.md'} in {answer}, then run again")


class ReplayRunner:
    """Answers from a recorded run, call by call. Refuses if a request changed."""

    name = "replay"
    reproducible = True

    def __init__(self, recorded_run: Path) -> None:
        #: The run folder (holding calls/), as written by a previous run.
        self.recorded_run = recorded_run

    def complete(self, request: Request, call_dir: Path) -> Response:
        recorded = self.recorded_run / "calls" / call_dir.name
        fingerprint, response = load_response(recorded)
        if fingerprint != request.fingerprint():
            raise GeneratorError(
                f"replay: the request of call '{call_dir.name}' differs from the recorded one "
                "(prompt, model, effort or input changed). Record a new run instead of replaying."
            )
        return response
