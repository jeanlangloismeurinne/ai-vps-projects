"""The `node` step: question + parent + sources -> scene.json and texts.fr.json, validated.

The step is JSON in, JSON out (spec, Pipeline): a person can take its place through the
manual runner. The output goes through the same validator as hand-written content; its
errors go back to the model, a bounded number of times, in the same conversation.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .calls import GeneratorError, Request, Response, load_response, record, write_json
from .profiles import Profile
from .runners import Runner

PROJECT = Path(__file__).resolve().parents[2]
PROMPTS = Path(__file__).resolve().parents[1] / "prompts"
LANG = "fr"


@dataclass(frozen=True)
class StepConfig:
    name: str
    #: Default profile (generator/profiles.toml); a run may choose another one.
    profile: str


# One profile per step (spec): the reference is Anthropic's; others are measured against it.
NODE_STEP = StepConfig(name="node", profile="anthropic-opus")


def prompt_file(name: str, variant: str | None = None) -> Path:
    """prompts/<variant>/<name> when the profile's variant overrides it, else prompts/<name>."""
    if variant and (PROMPTS / variant / name).exists():
        return PROMPTS / variant / name
    return PROMPTS / name


@dataclass(frozen=True)
class NodeTask:
    node_id: str
    question: str
    kind: str  # "system" | "principle"
    sources: Path
    #: (parent node id, entity it zooms into), for a child node.
    parent: tuple[str, str] | None = None
    #: Finished nodes shown as examples; the parent is always added.
    examples: tuple[str, ...] = ("wave-interference",)


@dataclass
class CallLog:
    name: str
    fingerprint: str
    runner: str
    model: str | None
    usage: dict
    cost_usd: float | None


@dataclass
class RunResult:
    run_dir: Path
    output_dir: Path
    errors: list[str]
    calls: list[CallLog] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _fill(template: str, values: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            raise GeneratorError(f"prompt template: no value for '{{{{{key}}}}}'")
        return values[key]

    return re.sub(r"\{\{(\w+)\}\}", replace, template)


def _node_files(node_id: str) -> str:
    folder = PROJECT / "content" / "nodes" / node_id
    if not folder.is_dir():
        raise GeneratorError(f"example node '{node_id}' does not exist in content/nodes")
    parts = [f"### `{node_id}`"]
    for name in ("scene.json", f"texts.{LANG}.json"):
        parts += ["", f"`{name}`", "", "```json", _read(folder / name).strip(), "```"]
    return "\n".join(parts)


def existing_nodes() -> list[str]:
    return sorted(d.name for d in (PROJECT / "content" / "nodes").iterdir() if d.is_dir())


def system_prompt(task: NodeTask, variant: str | None = None) -> str:
    """Stable across calls of a run (and across runs with the same examples): cached by the API."""
    examples = list(dict.fromkeys(([task.parent[0]] if task.parent else []) + list(task.examples)))
    if task.node_id in examples:
        raise GeneratorError(f"'{task.node_id}' cannot be its own example: the model would copy the answer")
    return _fill(
        _read(prompt_file("node.system.md", variant)),
        {
            "scene_schema": _read(PROJECT / "schemas" / "scene.schema.json").strip(),
            "texts_schema": _read(PROJECT / "schemas" / "texts.schema.json").strip(),
            "catalogue": _read(PROJECT / "catalogue" / "catalogue.json").strip(),
            "examples": "\n\n".join(_node_files(n) for n in examples),
        },
    )


def user_prompt(task: NodeTask, variant: str | None = None) -> str:
    parent_line = (
        f"- Child node of `{task.parent[0]}`: the user dives into its entity `{task.parent[1]}`."
        if task.parent
        else "- Root node: no parent."
    )
    # A term can only lead to a node that carries its own one-sentence summary (node.summaryKey).
    def describe(node_id: str) -> str:
        if node_id == task.node_id:
            return f"`{node_id}` (this node)"
        scene = json.loads(_read(PROJECT / "content" / "nodes" / node_id / "scene.json"))
        return f"`{node_id}` ({'explorable terms may point to it' if scene['node'].get('summaryKey') else 'no summaryKey: links only, no explorable term'})"

    others = [n for n in existing_nodes() if n != task.node_id] + [task.node_id]
    return _fill(
        _read(prompt_file("node.user.md", variant)),
        {
            "node_id": task.node_id,
            "question": task.question,
            "kind": task.kind,
            "parent_line": parent_line,
            "existing_nodes": "; ".join(describe(n) for n in sorted(others)),
            "sources": _read(task.sources).strip(),
        },
    )


def extract_node(text: str) -> tuple[dict, dict]:
    """The {"scene", "texts"} object of an answer; tolerates a fenced block, nothing else."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("the answer holds no JSON object")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, dict) or not isinstance(data.get("scene"), dict) or not isinstance(data.get("texts"), dict):
        raise ValueError('the JSON object must have "scene" and "texts" objects')
    return data["scene"], data["texts"]


def validate(folder: Path) -> list[str]:
    """The content validator (scripts/validate-node.ts), in the context of the hand-written graph."""
    try:
        done = subprocess.run(
            ["node", "scripts/validate-node.ts", str(folder)], cwd=PROJECT, capture_output=True, text=True, timeout=120
        )
    except FileNotFoundError:
        raise GeneratorError("validation needs Node.js (node) on the PATH") from None
    try:
        return json.loads(done.stdout)["errors"]
    except (json.JSONDecodeError, KeyError):
        raise GeneratorError(f"validator crashed: {done.stderr.strip()[-500:]}") from None


def _call(runner: Runner, request: Request, call_dir: Path) -> Response:
    # Resume: a call already answered for this exact request is not paid twice.
    if (call_dir / "response.json").exists():
        fingerprint, response = load_response(call_dir)
        if fingerprint == request.fingerprint():
            return response
    response = runner.complete(request, call_dir)
    record(call_dir, request, response)
    return response


def generate_node(task: NodeTask, runner: Runner, run_dir: Path, profile: Profile, max_repairs: int = 2, step: StepConfig = NODE_STEP) -> RunResult:
    output = run_dir / "output" / task.node_id
    result = RunResult(run_dir=run_dir, output_dir=output, errors=[])
    variant = profile.prompt_variant
    system = system_prompt(task, variant)
    messages: list[dict] = [{"role": "user", "content": user_prompt(task, variant)}]

    for attempt in range(max_repairs + 1):
        name = f"{attempt + 1:02d}-{step.name}" if attempt == 0 else f"{attempt + 1:02d}-{step.name}-repair"
        request = Request(step.name, profile.name, profile.settings(), system, tuple(messages))
        response = _call(runner, request, run_dir / "calls" / name)
        result.calls.append(CallLog(name, request.fingerprint(), response.runner, response.model, asdict(response.usage), response.cost_usd))
        try:
            scene, texts = extract_node(response.text)
        except ValueError as error:
            errors = [f"answer is not usable JSON: {error}"]
        else:
            write_json(output / "scene.json", scene)
            write_json(output / f"texts.{LANG}.json", texts)
            (output / "sources.json").write_text(_read(task.sources), encoding="utf-8")
            errors = validate(output)
        result.errors = errors
        if not errors:
            break
        # Append-only conversation: the model sees its answer and what was wrong with it.
        messages += [
            {"role": "assistant", "content": response.text},
            {"role": "user", "content": _fill(_read(prompt_file("node.repair.md", variant)), {"errors": "\n".join(f"- {e}" for e in errors)})},
        ]

    costs = [c.cost_usd for c in result.calls]
    write_json(
        run_dir / "run.json",
        {
            "task": {**asdict(task), "sources": str(task.sources.relative_to(PROJECT)) if task.sources.is_relative_to(PROJECT) else str(task.sources)},
            "step": step.name,
            "profile": profile.name,
            "settings": profile.settings(),
            "runner": runner.name,
            # A manual answer stays manual when replayed: no model produced it.
            "reproducible": all(c.runner != "manual" for c in result.calls),
            "calls": [asdict(c) for c in result.calls],
            "total_cost_usd": None if any(c is None for c in costs) else round(sum(costs), 6),
            "valid": result.ok,
            "errors": result.errors,
        },
    )
    return result
