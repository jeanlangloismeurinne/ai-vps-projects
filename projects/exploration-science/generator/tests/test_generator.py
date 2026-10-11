import json
from dataclasses import replace
from pathlib import Path

import pytest

from xs_generator.calls import GeneratorError, Request, Response, Usage, cost_usd
from xs_generator.pipeline import PROJECT, PROMPTS, NodeTask, extract_node, generate_node, prompt_file, system_prompt
from xs_generator.profiles import Profile, get_profile, load_profiles
from xs_generator.providers import AnthropicProvider, OpenAICompatibleProvider
from xs_generator.runners import ManualRunner, PendingManualStep, ReplayRunner

OPUS = get_profile("anthropic-opus")
REFERENCE = PROJECT / "content" / "nodes" / "starlink-phased-array"
TASK = NodeTask(
    node_id="starlink-phased-array",
    question="Comment le réseau d'antennes de Starlink oriente-t-il son faisceau ?",
    kind="system",
    sources=REFERENCE / "sources.json",
    parent=("starlink-terminal", "phased-array"),
)


def reference_answer() -> str:
    scene = json.loads((REFERENCE / "scene.json").read_text(encoding="utf-8"))
    texts = json.loads((REFERENCE / "texts.fr.json").read_text(encoding="utf-8"))
    return "```json\n" + json.dumps({"scene": scene, "texts": texts}, ensure_ascii=False) + "\n```"


class ScriptedRunner:
    """Answers from a list, and keeps the requests it saw."""

    name = "scripted"
    reproducible = True

    def __init__(self, answers: list[str]) -> None:
        self.answers = list(answers)
        self.requests: list[Request] = []

    def complete(self, request: Request, call_dir: Path) -> Response:
        self.requests.append(request)
        usage = Usage(input_tokens=1000, output_tokens=500)
        return Response(text=self.answers.pop(0), runner=self.name, profile=request.profile, usage=usage, cost_usd=cost_usd(request.settings.get("prices"), usage))


def files(folder: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in sorted(folder.iterdir())}


def test_fingerprint_changes_with_anything_that_decides_the_answer():
    base = Request("node", "anthropic-opus", {"model": "claude-opus-5-5", "effort": "high"}, "system", ({"role": "user", "content": "q"},))
    assert base.fingerprint() == replace(base).fingerprint()
    for changed in (
        replace(base, settings={"model": "claude-sonnet-5-5", "effort": "high"}),
        replace(base, settings={"model": "claude-opus-5-5", "effort": "low"}),
        replace(base, profile="other"),
        replace(base, system="other"),
        replace(base, messages=({"role": "user", "content": "q2"},)),
    ):
        assert changed.fingerprint() != base.fingerprint()


def test_cost_uses_the_price_table_and_never_guesses():
    usage = Usage(input_tokens=1_000_000, output_tokens=100_000, cache_read_input_tokens=1_000_000, cache_creation_input_tokens=0)
    assert cost_usd(OPUS.prices, usage) == pytest.approx(4.0 + 2.0 + 0.2)
    assert cost_usd(None, usage) is None


def test_extract_node_accepts_a_fenced_object_only_with_scene_and_texts():
    assert extract_node('```json\n{"scene": {}, "texts": {}}\n```') == ({}, {})
    with pytest.raises(ValueError):
        extract_node("no json here")
    with pytest.raises(ValueError):
        extract_node('{"scene": {}}')


def test_the_target_node_is_never_its_own_example():
    with pytest.raises(GeneratorError, match="own example"):
        system_prompt(replace(TASK, examples=("starlink-phased-array",)))


def test_a_valid_answer_is_written_validated_and_replayed_byte_for_byte(tmp_path):
    first = generate_node(TASK, ScriptedRunner([reference_answer()]), tmp_path / "run", OPUS)
    assert first.ok, first.errors
    assert len(first.calls) == 1
    run = json.loads((tmp_path / "run" / "run.json").read_text())
    assert run["valid"] and run["reproducible"] and run["total_cost_usd"] == pytest.approx(0.004 + 0.01)

    again = generate_node(TASK, ReplayRunner(tmp_path / "run"), tmp_path / "replay", OPUS)
    assert again.ok
    assert files(again.output_dir) == files(first.output_dir)


def test_replay_refuses_a_request_that_changed(tmp_path):
    generate_node(TASK, ScriptedRunner([reference_answer()]), tmp_path / "run", OPUS)
    changed = replace(TASK, question="Une autre question ?")
    with pytest.raises(GeneratorError, match="differs from the recorded one"):
        generate_node(changed, ReplayRunner(tmp_path / "run"), tmp_path / "replay", OPUS)


def test_validator_errors_go_back_to_the_model_until_it_fixes_them(tmp_path):
    broken = reference_answer().replace('"phased-array-wave"', '"no-such-simulator"')
    runner = ScriptedRunner([broken, reference_answer()])
    result = generate_node(TASK, runner, tmp_path / "run", OPUS)
    assert result.ok
    assert [c.name for c in result.calls] == ["01-node", "02-node-repair"]
    repair = runner.requests[1].messages
    assert [m["role"] for m in repair] == ["user", "assistant", "user"]
    assert "no-such-simulator" in repair[2]["content"]


def test_repairs_are_bounded(tmp_path):
    result = generate_node(TASK, ScriptedRunner(["not json"] * 2), tmp_path / "run", OPUS, max_repairs=1)
    assert not result.ok and len(result.calls) == 2
    assert "not usable JSON" in result.errors[0]


def test_a_recorded_call_is_not_paid_twice_when_a_run_resumes(tmp_path):
    generate_node(TASK, ScriptedRunner([reference_answer()]), tmp_path / "run", OPUS)
    runner = ScriptedRunner([])
    assert generate_node(TASK, runner, tmp_path / "run", OPUS).ok
    assert runner.requests == []


def test_manual_runner_writes_the_request_then_takes_the_written_answer(tmp_path):
    with pytest.raises(PendingManualStep):
        generate_node(TASK, ManualRunner(), tmp_path / "run", OPUS)
    call = tmp_path / "run" / "calls" / "01-node"
    request = (call / "request.md").read_text()
    assert "## System" in request and TASK.question in request
    (call / "response.txt").write_text(reference_answer(), encoding="utf-8")
    result = generate_node(TASK, ManualRunner(), tmp_path / "run", OPUS)
    assert result.ok
    run = json.loads((tmp_path / "run" / "run.json").read_text())
    assert run["reproducible"] is False and run["total_cost_usd"] is None


def test_a_provider_without_its_key_says_what_to_do(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(GeneratorError, match="no ANTHROPIC_API_KEY"):
        AnthropicProvider(OPUS)
    monkeypatch.delenv("DEEPINFRA_API_KEY", raising=False)
    with pytest.raises(GeneratorError, match="no DEEPINFRA_API_KEY"):
        OpenAICompatibleProvider(get_profile("deepinfra-deepseek-v4.1-flash"))


def test_env_file_fills_missing_variables_only(tmp_path, monkeypatch):
    from xs_generator.cli import load_env

    env = tmp_path / ".env"
    env.write_text("# comment\nXS_TEST_A='from-file'\nXS_TEST_B=from-file\n", encoding="utf-8")
    monkeypatch.delenv("XS_TEST_A", raising=False)
    monkeypatch.setenv("XS_TEST_B", "from-shell")
    load_env(env)
    import os

    assert os.environ["XS_TEST_A"] == "from-file"
    assert os.environ["XS_TEST_B"] == "from-shell"
    monkeypatch.delenv("XS_TEST_A")


def test_anthropic_provider_sends_the_documented_request(monkeypatch):
    import httpx2 as httpx  # the HTTP client the anthropic 1.x SDK is built on

    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["headers"] = dict(request.headers)
        seen["body"] = json.loads(request.content)
        return httpx.Response(400, json={"type": "error", "error": {"type": "invalid_request_error", "message": "stop here"}})

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("XS_ANTHROPIC_BASE_URL", raising=False)
    provider = AnthropicProvider(OPUS, http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    request = Request("node", OPUS.name, OPUS.settings(), "the system prompt", ({"role": "user", "content": "q"},))
    with pytest.raises(GeneratorError, match="API error 400"):
        provider.complete(request)
    body = seen["body"]
    assert seen["url"].startswith("https://api.anthropic.com/v1/messages")
    assert "server-side-fallback-2026-07-01" in seen["headers"]["anthropic-beta"]
    assert body["model"] == "claude-opus-5-5" and body["max_tokens"] == 64000 and body["stream"] is True
    assert body["thinking"] == {"type": "adaptive"}
    assert body["output_config"] == {"effort": "high"}
    assert body["fallbacks"] == "default"
    assert body["system"] == [{"type": "text", "text": "the system prompt", "cache_control": {"type": "ephemeral"}}]
    assert body["messages"] == [{"role": "user", "content": "q"}]


def test_manual_answer_to_an_older_request_is_refused(tmp_path):
    with pytest.raises(PendingManualStep):
        generate_node(TASK, ManualRunner(), tmp_path / "run", OPUS)
    (tmp_path / "run" / "calls" / "01-node" / "response.txt").write_text(reference_answer(), encoding="utf-8")
    with pytest.raises(GeneratorError, match="older request"):
        generate_node(replace(TASK, question="Une autre question ?"), ManualRunner(), tmp_path / "run", OPUS)


DEEPINFRA = get_profile("deepinfra-deepseek-v4.1-flash")


def openai_provider(monkeypatch, handler, profile=DEEPINFRA):
    import httpx2 as httpx  # the HTTP client the openai SDK is built on

    monkeypatch.setenv("DEEPINFRA_API_KEY", "test-key")
    return OpenAICompatibleProvider(profile, http_client=httpx.Client(transport=httpx.MockTransport(handler)))


def completion(content: str, finish_reason: str = "stop", **usage_extra) -> dict:
    usage = {"prompt_tokens": 30000, "completion_tokens": 8000, "total_tokens": 38000, "prompt_tokens_details": {"cached_tokens": 20000}, **usage_extra}
    return {
        "id": "x", "object": "chat.completion", "created": 0, "model": DEEPINFRA.model,
        "choices": [{"index": 0, "finish_reason": finish_reason, "message": {"role": "assistant", "content": content}}],
        "usage": usage,
    }


def test_openai_compatible_provider_sends_system_first_and_enforces_json(monkeypatch):
    import httpx2 as httpx

    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=completion('{"scene": {}, "texts": {}}'))

    provider = openai_provider(monkeypatch, handler)
    request = Request("node", DEEPINFRA.name, DEEPINFRA.settings(), "the system prompt", ({"role": "user", "content": "q"},))
    response = provider.complete(request)
    assert seen["url"] == "https://api.deepinfra.com/v1/openai/chat/completions"
    assert seen["auth"] == "Bearer test-key"
    body = seen["body"]
    assert body["model"] == DEEPINFRA.model and body["max_tokens"] == DEEPINFRA.max_tokens
    assert body["messages"] == [{"role": "system", "content": "the system prompt"}, {"role": "user", "content": "q"}]
    assert body["response_format"] == {"type": "json_object"}
    assert response.text == '{"scene": {}, "texts": {}}' and response.runner == "api" and response.profile == DEEPINFRA.name
    # 30 000 prompt tokens of which 20 000 cached: 10 000 uncached input, 20 000 cache reads.
    assert (response.usage.input_tokens, response.usage.cache_read_input_tokens, response.usage.output_tokens) == (10000, 20000, 8000)
    assert response.cost_usd == pytest.approx(10000 * 0.20e-6 + 20000 * 0.006e-6 + 8000 * 0.60e-6)


def test_openai_compatible_provider_prefers_the_cost_the_api_reports(monkeypatch):
    import httpx2 as httpx

    provider = openai_provider(monkeypatch, lambda request: httpx.Response(200, json=completion("{}", estimated_cost=0.0123)))
    request = Request("node", DEEPINFRA.name, DEEPINFRA.settings(), "s", ({"role": "user", "content": "q"},))
    assert provider.complete(request).cost_usd == pytest.approx(0.0123)


def test_openai_compatible_provider_reports_a_cut_answer_instead_of_returning_it(monkeypatch):
    import httpx2 as httpx

    provider = openai_provider(monkeypatch, lambda request: httpx.Response(200, json=completion('{"scene": {', finish_reason="length")))
    request = Request("node", DEEPINFRA.name, DEEPINFRA.settings(), "s", ({"role": "user", "content": "q"},))
    with pytest.raises(GeneratorError, match="output cut"):
        provider.complete(request)


def test_profiles_are_checked_and_secrets_stay_out_of_the_recorded_settings(tmp_path):
    assert {"anthropic-opus", "deepinfra-deepseek-v4.1-flash"} <= load_profiles().keys()
    assert "api_key_env" not in OPUS.settings() and OPUS.settings()["model"] == "claude-opus-5-5"
    bad = tmp_path / "profiles.toml"
    bad.write_text('[x]\nprovider = "somewhere"\nmodel = "m"\nmax_tokens = 10\n', encoding="utf-8")
    with pytest.raises(GeneratorError, match="unknown provider"):
        load_profiles(bad)
    with pytest.raises(GeneratorError, match="unknown profile"):
        get_profile("nope")


def test_a_profile_prompt_variant_overrides_only_the_files_it_has(tmp_path, monkeypatch):
    variant = PROMPTS / "_test_variant"
    variant.mkdir()
    try:
        (variant / "node.repair.md").write_text("override", encoding="utf-8")
        assert prompt_file("node.repair.md", "_test_variant") == variant / "node.repair.md"
        assert prompt_file("node.system.md", "_test_variant") == PROMPTS / "node.system.md"
        assert prompt_file("node.system.md", None) == PROMPTS / "node.system.md"
    finally:
        (variant / "node.repair.md").unlink()
        variant.rmdir()


def test_changing_profile_changes_the_request_so_replay_refuses(tmp_path):
    generate_node(TASK, ScriptedRunner([reference_answer()]), tmp_path / "run", OPUS)
    with pytest.raises(GeneratorError, match="differs from the recorded one"):
        generate_node(TASK, ReplayRunner(tmp_path / "run"), tmp_path / "replay", DEEPINFRA)
