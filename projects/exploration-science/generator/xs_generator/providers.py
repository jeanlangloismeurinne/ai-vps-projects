"""Providers: one object per API, hiding what it takes to make that API answer a step
as well as the reference (Anthropic) does.

Every provider takes the same Request (system prompt, conversation, profile settings)
and returns the same Response (text, stop reason, usage, cost). What differs stays
inside: how the system prompt and caching are expressed, how JSON output is enforced,
how a truncated or declined answer shows up, how usage and cost are reported.
"""

from __future__ import annotations

import os
from typing import Protocol

from .calls import GeneratorError, Request, Response, Usage, cost_usd
from .profiles import Profile


class Provider(Protocol):
    profile: Profile

    def complete(self, request: Request) -> Response: ...

    def models(self) -> list[str]:
        """Model ids the API serves (to check a profile's `model`)."""
        ...


def _api_key(profile: Profile) -> str:
    variable = profile.api_key_env
    key = os.environ.get(variable) if variable else None
    if not key:
        raise GeneratorError(
            f"profile '{profile.name}': no {variable or 'api_key_env'} in the environment. "
            "Put the key in generator/.env on the VPS (chmod 600), or use --runner manual / replay."
        )
    return key


class AnthropicProvider:
    """The reference: official SDK, streaming, adaptive thinking, effort, cached system prompt."""

    def __init__(self, profile: Profile, http_client=None) -> None:
        import anthropic

        self.profile = profile
        self._anthropic = anthropic
        # The base URL is pinned on purpose: development shells may export ANTHROPIC_BASE_URL
        # for their own tooling, and generator calls must not silently go through it.
        base_url = profile.fields.get("base_url") or os.environ.get("XS_ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        # http_client: tests plug a fake transport here.
        self._client = anthropic.Anthropic(api_key=_api_key(profile), base_url=base_url, http_client=http_client)

    def complete(self, request: Request) -> Response:
        anthropic = self._anthropic
        settings = request.settings
        try:
            # Server-side fallback ("default" mode): a declined request is re-run on the
            # recommended model instead of coming back as a refusal.
            with self._client.beta.messages.stream(
                model=settings["model"],
                max_tokens=settings["max_tokens"],
                system=[{"type": "text", "text": request.system, "cache_control": {"type": "ephemeral"}}],
                messages=list(request.messages),
                thinking={"type": "adaptive"},
                output_config={"effort": settings.get("effort", "high")},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            ) as stream:
                message = stream.get_final_message()
        except anthropic.AuthenticationError:
            raise GeneratorError(f"profile '{self.profile.name}': the API rejected the key (401).") from None
        except anthropic.RateLimitError:
            raise GeneratorError(f"profile '{self.profile.name}': rate limited (429). Run again later; recorded steps are kept.") from None
        except anthropic.APIStatusError as error:
            raise GeneratorError(f"profile '{self.profile.name}': API error {error.status_code}: {error.message}") from None
        except anthropic.APIConnectionError:
            raise GeneratorError(f"profile '{self.profile.name}': cannot reach the API (network).") from None

        if message.stop_reason == "refusal":
            raise GeneratorError(f"profile '{self.profile.name}': the request was declined ({message.stop_details}).")
        if message.stop_reason == "max_tokens":
            raise GeneratorError(f"profile '{self.profile.name}': output cut at max_tokens={settings['max_tokens']}; raise it.")
        u = message.usage
        usage = Usage(
            input_tokens=u.input_tokens or 0,
            output_tokens=u.output_tokens or 0,
            cache_creation_input_tokens=u.cache_creation_input_tokens or 0,
            cache_read_input_tokens=u.cache_read_input_tokens or 0,
        )
        text = "".join(block.text for block in message.content if block.type == "text")
        # A fallback may have answered: it is priced like the profile's model (an approximation, recorded as such by `model`).
        return Response(text=text, runner="api", profile=self.profile.name, model=message.model, stop_reason=message.stop_reason, usage=usage, cost_usd=cost_usd(self.profile.prices, usage))

    def models(self) -> list[str]:
        return sorted(m.id for m in self._client.models.list())


class OpenAICompatibleProvider:
    """Any Chat Completions API (DeepInfra, …), through the `openai` SDK pointed at its base URL.

    Brought to the reference's level here: the system prompt goes first (providers that cache
    prompt prefixes cache it), JSON output is enforced when the profile says `json_mode`, a
    truncated answer is an error (not a silently cut JSON), provider-specific options pass
    through `extra_body`, and the provider's own cost figure is used when it reports one.
    """

    def __init__(self, profile: Profile, http_client=None) -> None:
        import openai

        self.profile = profile
        self._openai = openai
        base_url = profile.fields.get("base_url")
        if not base_url:
            raise GeneratorError(f"profile '{profile.name}': an openai-compatible profile needs base_url")
        self._client = openai.OpenAI(api_key=_api_key(profile), base_url=base_url, timeout=float(profile.fields.get("timeout_s", 600)), http_client=http_client)

    def complete(self, request: Request) -> Response:
        openai = self._openai
        settings = request.settings
        options: dict = {}
        if settings.get("json_mode"):
            options["response_format"] = {"type": "json_object"}
        if "temperature" in settings:
            options["temperature"] = settings["temperature"]
        if "reasoning_effort" in settings:
            options["reasoning_effort"] = settings["reasoning_effort"]
        if settings.get("extra_body"):
            options["extra_body"] = settings["extra_body"]
        try:
            completion = self._client.chat.completions.create(
                model=settings["model"],
                max_tokens=settings["max_tokens"],
                messages=[{"role": "system", "content": request.system}, *request.messages],
                **options,
            )
        except openai.AuthenticationError:
            raise GeneratorError(f"profile '{self.profile.name}': the API rejected the key (401).") from None
        except openai.RateLimitError:
            raise GeneratorError(f"profile '{self.profile.name}': rate limited (429). Run again later; recorded steps are kept.") from None
        except openai.APIStatusError as error:
            raise GeneratorError(f"profile '{self.profile.name}': API error {error.status_code}: {error.message}") from None
        except openai.APIConnectionError:
            raise GeneratorError(f"profile '{self.profile.name}': cannot reach the API (network or timeout).") from None

        if not completion.choices:
            raise GeneratorError(f"profile '{self.profile.name}': the API returned no answer.")
        choice = completion.choices[0]
        if choice.finish_reason == "length":
            raise GeneratorError(f"profile '{self.profile.name}': output cut at max_tokens={settings['max_tokens']}; raise it.")
        if choice.finish_reason == "content_filter":
            raise GeneratorError(f"profile '{self.profile.name}': the request was declined (content filter).")

        u = completion.usage
        cached = (u.prompt_tokens_details.cached_tokens or 0) if u and u.prompt_tokens_details else 0
        usage = Usage(
            # Chat Completions counts cached tokens inside prompt_tokens; ours are uncached input only.
            input_tokens=(u.prompt_tokens - cached) if u else 0,
            output_tokens=u.completion_tokens if u else 0,
            cache_read_input_tokens=cached,
        )
        reported = getattr(u, "estimated_cost", None) if u else None
        cost = round(float(reported), 6) if isinstance(reported, (int, float)) else cost_usd(self.profile.prices, usage)
        return Response(text=choice.message.content or "", runner="api", profile=self.profile.name, model=completion.model, stop_reason=choice.finish_reason, usage=usage, cost_usd=cost)

    def models(self) -> list[str]:
        return sorted(m.id for m in self._client.models.list())


def make_provider(profile: Profile, http_client=None) -> Provider:
    if profile.provider == "anthropic":
        return AnthropicProvider(profile, http_client)
    return OpenAICompatibleProvider(profile, http_client)
