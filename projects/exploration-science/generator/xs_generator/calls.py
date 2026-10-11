"""What a model call is, what it costs, and how it is recorded."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


class GeneratorError(Exception):
    """A failure the operator can act on; the message says what to do."""


@dataclass(frozen=True)
class Request:
    """Everything that decides a model's answer. Its fingerprint keys the replay."""

    step: str
    model: str
    effort: str
    max_tokens: int
    system: str
    messages: tuple[dict, ...]

    def fingerprint(self) -> str:
        canonical = json.dumps(asdict(self), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


@dataclass
class Response:
    text: str
    runner: str
    model: str | None = None
    stop_reason: str | None = None
    usage: Usage = field(default_factory=Usage)
    cost_usd: float | None = None


# USD per million tokens (Claude API, 2026-10). Cache writes use the 5-minute TTL rate
# (1.25 x input). Thinking tokens are billed as output and are included in output_tokens.
PRICES = {
    "claude-opus-5-5": {"input": 4.00, "output": 20.00, "cache_read": 0.20},
    "claude-sonnet-5-5": {"input": 2.00, "output": 10.00, "cache_read": 0.20},
    "claude-haiku-5-5": {"input": 0.10, "output": 0.50, "cache_read": 0.01},
}


def cost_usd(model: str, usage: Usage) -> float | None:
    """Cost of one call; None for a model without a known price (never guessed)."""
    price = PRICES.get(model)
    if price is None:
        return None
    per_token = 1e-6
    return round(
        usage.input_tokens * price["input"] * per_token
        + usage.cache_creation_input_tokens * price["input"] * 1.25 * per_token
        + usage.cache_read_input_tokens * price["cache_read"] * per_token
        + usage.output_tokens * price["output"] * per_token,
        6,
    )


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def record(call_dir: Path, request: Request, response: Response) -> None:
    """One folder per call: the request with its fingerprint, then the response."""
    write_json(call_dir / "request.json", {"fingerprint": request.fingerprint(), **asdict(request)})
    write_json(call_dir / "response.json", asdict(response))


def load_response(call_dir: Path) -> tuple[str, Response]:
    """The recorded fingerprint and response of a call."""
    try:
        request = json.loads((call_dir / "request.json").read_text(encoding="utf-8"))
        data = json.loads((call_dir / "response.json").read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise GeneratorError(f"replay: no recorded call in {call_dir} ({error.filename} missing)") from None
    data["usage"] = Usage(**data.get("usage") or {})
    return request["fingerprint"], Response(**data)
