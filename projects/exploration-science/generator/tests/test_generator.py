import json
from dataclasses import replace
from pathlib import Path

import pytest

from xs_generator.calls import GeneratorError, Request, Response, Usage, cost_usd
from xs_generator.pipeline import PROJECT, NodeTask, extract_node, generate_node, system_prompt
from xs_generator.runners import AnthropicRunner, ManualRunner, PendingManualStep, ReplayRunner

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
        return Response(text=self.answers.pop(0), runner=self.name, model=request.model, usage=usage, cost_usd=cost_usd(request.model, usage))


def files(folder: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in sorted(folder.iterdir())}


def test_fingerprint_changes_with_anything_that_decides_the_answer():
    base = Request("node", "claude-opus-5-5", "high", 1000, "system", ({"role": "user", "content": "q"},))
    assert base.fingerprint() == replace(base).fingerprint()
    for changed in (replace(base, model="claude-sonnet-5-5"), replace(base, effort="low"), replace(base, system="other"), replace(base, messages=({"role": "user", "content": "q2"},))):
        assert changed.fingerprint() != base.fingerprint()


def test_cost_uses_the_price_table_and_never_guesses():
    usage = Usage(input_tokens=1_000_000, output_tokens=100_000, cache_read_input_tokens=1_000_000, cache_creation_input_tokens=0)
    assert cost_usd("claude-opus-5-5", usage) == pytest.approx(4.0 + 2.0 + 0.2)
    assert cost_usd("some-unknown-model", usage) is None


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
    first = generate_node(TASK, ScriptedRunner([reference_answer()]), tmp_path / "run")
    assert first.ok, first.errors
    assert len(first.calls) == 1
    run = json.loads((tmp_path / "run" / "run.json").read_text())
    assert run["valid"] and run["reproducible"] and run["total_cost_usd"] == pytest.approx(0.004 + 0.01)

    again = generate_node(TASK, ReplayRunner(tmp_path / "run"), tmp_path / "replay")
    assert again.ok
    assert files(again.output_dir) == files(first.output_dir)


def test_replay_refuses_a_request_that_changed(tmp_path):
    generate_node(TASK, ScriptedRunner([reference_answer()]), tmp_path / "run")
    changed = replace(TASK, question="Une autre question ?")
    with pytest.raises(GeneratorError, match="differs from the recorded one"):
        generate_node(changed, ReplayRunner(tmp_path / "run"), tmp_path / "replay")


def test_validator_errors_go_back_to_the_model_until_it_fixes_them(tmp_path):
    broken = reference_answer().replace('"phased-array-wave"', '"no-such-simulator"')
    runner = ScriptedRunner([broken, reference_answer()])
    result = generate_node(TASK, runner, tmp_path / "run")
    assert result.ok
    assert [c.name for c in result.calls] == ["01-node", "02-node-repair"]
    repair = runner.requests[1].messages
    assert [m["role"] for m in repair] == ["user", "assistant", "user"]
    assert "no-such-simulator" in repair[2]["content"]


def test_repairs_are_bounded(tmp_path):
    result = generate_node(TASK, ScriptedRunner(["not json"] * 2), tmp_path / "run", max_repairs=1)
    assert not result.ok and len(result.calls) == 2
    assert "not usable JSON" in result.errors[0]


def test_a_recorded_call_is_not_paid_twice_when_a_run_resumes(tmp_path):
    generate_node(TASK, ScriptedRunner([reference_answer()]), tmp_path / "run")
    runner = ScriptedRunner([])
    assert generate_node(TASK, runner, tmp_path / "run").ok
    assert runner.requests == []


def test_manual_runner_writes_the_request_then_takes_the_written_answer(tmp_path):
    with pytest.raises(PendingManualStep):
        generate_node(TASK, ManualRunner(), tmp_path / "run")
    call = tmp_path / "run" / "calls" / "01-node"
    request = (call / "request.md").read_text()
    assert "## System" in request and TASK.question in request
    (call / "response.txt").write_text(reference_answer(), encoding="utf-8")
    result = generate_node(TASK, ManualRunner(), tmp_path / "run")
    assert result.ok
    run = json.loads((tmp_path / "run" / "run.json").read_text())
    assert run["reproducible"] is False and run["total_cost_usd"] is None


def test_anthropic_runner_without_a_key_says_what_to_do(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    with pytest.raises(GeneratorError, match="no ANTHROPIC_API_KEY"):
        AnthropicRunner()
