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
    """Everything that decides a model's answer. Its fingerprint keys the replay.

    `settings` is the profile without secrets (provider, model, parameters, prices):
    changing any of them changes the fingerprint.
    """

    step: str
    profile: str
    settings: dict
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
    profile: str | None = None
    model: str | None = None
    stop_reason: str | None = None
    usage: Usage = field(default_factory=Usage)
    cost_usd: float | None = None


def cost_usd(prices: dict | None, usage: Usage) -> float | None:
    """Cost of one call from the profile's prices (USD per million tokens); None when unknown, never guessed.

    `input_tokens` counts only uncached input; cache writes default to 1.25 x input, cache reads
    to the input price when the profile gives no specific rate.
    """
    if not prices:
        return None
    per_token = 1e-6
    return round(
        usage.input_tokens * prices["input"] * per_token
        + usage.cache_creation_input_tokens * prices.get("cache_write", prices["input"] * 1.25) * per_token
        + usage.cache_read_input_tokens * prices.get("cache_read", prices["input"]) * per_token
        + usage.output_tokens * prices["output"] * per_token,
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
    data = {k: v for k, v in data.items() if k in Response.__dataclass_fields__}
    return request["fingerprint"], Response(**data)
