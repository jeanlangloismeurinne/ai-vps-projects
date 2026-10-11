"""Runners: who answers a request. The pipeline does not know which one it uses."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .calls import GeneratorError, Request, Response, load_response
from .providers import Provider


class Runner(Protocol):
    name: str

    def complete(self, request: Request, call_dir: Path) -> Response: ...


class ApiRunner:
    """A real API call, through the provider the profile names. Reproducible once recorded."""

    name = "api"

    def __init__(self, provider: Provider) -> None:
        self.provider = provider

    def complete(self, request: Request, call_dir: Path) -> Response:
        return self.provider.complete(request)


class PendingManualStep(GeneratorError):
    """The request is on disk and waits for a written response."""


class ManualRunner:
    """A person (or Claude Code while developing) answers. Not reproducible: no model ran.

    First pass: writes ``request.md`` (system prompt + messages) and the request's
    fingerprint in the call folder, and stops. Once ``response.txt`` is written next to
    it, the next pass picks it up, if the request has not changed meanwhile.
    """

    name = "manual"

    def complete(self, request: Request, call_dir: Path) -> Response:
        answer = call_dir / "response.txt"
        asked = call_dir / "request.fingerprint"
        if answer.exists():
            # An answer is only valid for the request it was written for.
            if asked.exists() and asked.read_text(encoding="utf-8").strip() != request.fingerprint():
                raise GeneratorError(f"manual: {answer} answers an older request (the prompt changed); move it away and answer the new request.md")
            return Response(text=answer.read_text(encoding="utf-8"), runner=self.name, profile=request.profile)
        call_dir.mkdir(parents=True, exist_ok=True)
        asked.write_text(request.fingerprint() + "\n", encoding="utf-8")
        parts = [f"# Step `{request.step}` — standing in for profile `{request.profile}` ({request.settings.get('model')})", "", "## System", "", request.system]
        for message in request.messages:
            parts += ["", f"## {message['role']}", "", message["content"]]
        (call_dir / "request.md").write_text("\n".join(parts) + "\n", encoding="utf-8")
        raise PendingManualStep(f"manual step waiting: answer {call_dir / 'request.md'} in {answer}, then run again")


class ReplayRunner:
    """Answers from a recorded run, call by call. Refuses if a request changed."""

    name = "replay"

    def __init__(self, recorded_run: Path) -> None:
        #: The run folder (holding calls/), as written by a previous run.
        self.recorded_run = recorded_run

    def complete(self, request: Request, call_dir: Path) -> Response:
        recorded = self.recorded_run / "calls" / call_dir.name
        fingerprint, response = load_response(recorded)
        if fingerprint != request.fingerprint():
            raise GeneratorError(
                f"replay: the request of call '{call_dir.name}' differs from the recorded one "
                "(prompt, profile or input changed). Record a new run instead of replaying."
            )
        return response
