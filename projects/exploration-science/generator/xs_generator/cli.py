"""Command line: `python -m xs_generator node …` (see --help)."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from .calls import GeneratorError
from .pipeline import PROJECT, NodeTask, generate_node
from .runners import AnthropicRunner, ManualRunner, PendingManualStep, ReplayRunner

RUNS = Path(__file__).resolve().parents[1] / "runs"
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def load_env(path: Path = ENV_FILE) -> None:
    """KEY=VALUE lines of generator/.env (chmod 600, never committed); the shell environment wins."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="xs_generator", description="Explorateur de systèmes: node generator.")
    commands = parser.add_subparsers(dest="command", required=True)
    node = commands.add_parser("node", help="write one node (scene + French texts) and validate it")
    node.add_argument("--id", required=True, help="node id, e.g. starlink-phased-array")
    node.add_argument("--question", required=True, help="the question the node answers, in French")
    node.add_argument("--kind", choices=["system", "principle"], default="system")
    node.add_argument("--parent", help="parent node and entity, as <node>:<entity>")
    node.add_argument("--sources", required=True, type=Path, help="sources.json to use (until the sources step exists)")
    node.add_argument("--example", action="append", default=None, help="finished node shown as an example (repeatable)")
    node.add_argument("--runner", choices=["anthropic", "manual", "replay"], required=True)
    node.add_argument("--replay-from", type=Path, help="recorded run folder, with --runner replay")
    node.add_argument("--run-id", help="run folder name under generator/runs (default: timestamp); reuse it to resume")
    node.add_argument("--max-repairs", type=int, default=2)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    load_env()
    try:
        if args.runner == "anthropic":
            runner = AnthropicRunner()
        elif args.runner == "manual":
            runner = ManualRunner()
        else:
            if not args.replay_from:
                raise GeneratorError("--runner replay needs --replay-from <recorded run folder>")
            runner = ReplayRunner(args.replay_from.resolve())
        parent = None
        if args.parent:
            node_id, _, entity = args.parent.partition(":")
            if not entity:
                raise GeneratorError("--parent is <node>:<entity>")
            parent = (node_id, entity)
        task = NodeTask(
            node_id=args.id,
            question=args.question,
            kind=args.kind,
            sources=args.sources.resolve(),
            parent=parent,
            examples=tuple(args.example) if args.example else NodeTask.examples,
        )
        run_id = args.run_id or f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{args.id}-{args.runner}"
        result = generate_node(task, runner, RUNS / run_id, max_repairs=args.max_repairs)
    except PendingManualStep as pending:
        print(f"PENDING: {pending}")
        return 3
    except GeneratorError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    costs = [c.cost_usd for c in result.calls]
    cost = "cost unknown (no priced model call)" if any(c is None for c in costs) else f"cost ${sum(costs):.4f}"
    where = result.output_dir.relative_to(PROJECT)
    if result.ok:
        print(f"OK: {where} valid after {len(result.calls)} call(s), {cost}")
        return 0
    print(f"INVALID: {where} still has {len(result.errors)} error(s) after {len(result.calls)} call(s):")
    for error in result.errors:
        print(f"  - {error}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
