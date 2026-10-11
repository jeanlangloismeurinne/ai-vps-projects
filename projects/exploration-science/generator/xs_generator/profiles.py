"""Model profiles (generator/profiles.toml): provider, model, parameters, prices."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .calls import GeneratorError

PROFILES_FILE = Path(__file__).resolve().parents[1] / "profiles.toml"
PROVIDERS = ("anthropic", "openai-compatible")


@dataclass(frozen=True)
class Profile:
    name: str
    provider: str
    model: str
    max_tokens: int
    #: Every field of the profile; `settings()` drops the secret-related ones.
    fields: dict

    @property
    def api_key_env(self) -> str:
        return self.fields.get("api_key_env", "")

    @property
    def prices(self) -> dict | None:
        return self.fields.get("prices")

    @property
    def prompt_variant(self) -> str | None:
        return self.fields.get("prompt_variant")

    def settings(self) -> dict:
        """What decides the answer, without secrets: recorded and fingerprinted with each request."""
        return {k: v for k, v in sorted(self.fields.items()) if k != "api_key_env"}


def load_profiles(path: Path = PROFILES_FILE) -> dict[str, Profile]:
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise GeneratorError(f"cannot read {path}: {error}") from None
    profiles = {}
    for name, fields in raw.items():
        missing = [k for k in ("provider", "model", "max_tokens") if k not in fields]
        if missing:
            raise GeneratorError(f"profile '{name}': missing {', '.join(missing)}")
        if fields["provider"] not in PROVIDERS:
            raise GeneratorError(f"profile '{name}': unknown provider '{fields['provider']}' (known: {', '.join(PROVIDERS)})")
        prices = fields.get("prices")
        if prices is not None and not {"input", "output"} <= prices.keys():
            raise GeneratorError(f"profile '{name}': prices need at least input and output")
        profiles[name] = Profile(name, fields["provider"], fields["model"], int(fields["max_tokens"]), dict(fields))
    return profiles


def get_profile(name: str, path: Path = PROFILES_FILE) -> Profile:
    profiles = load_profiles(path)
    if name not in profiles:
        raise GeneratorError(f"unknown profile '{name}' (in {path.name}: {', '.join(profiles)})")
    return profiles[name]
