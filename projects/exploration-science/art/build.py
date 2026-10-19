"""Build the assets of one scene file: model → check → bake AO → export GLB → report.

Usage (from the project root):
  art/.venv/bin/python art/build.py --scene art/scenes/<scene>.json [--out DIR]

Exits 1 when a geometric check fails: nothing is exported then.
"""

import argparse
import importlib
import json
import sys
import time
from pathlib import Path

ART = Path(__file__).resolve().parent
sys.path[:0] = [str(ART / "lib"), str(ART)]

import bpy  # noqa: E402

from xs import checks  # noqa: E402
from xs.bake import bake_ao  # noqa: E402
from xs.export import export_asset  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", required=True)
    parser.add_argument("--out", help="output directory (default: the scene file's `out`)")
    args = parser.parse_args()

    scene_path = Path(args.scene).resolve()
    scene = json.loads(scene_path.read_text())
    project = ART.parent
    out = Path(args.out).resolve() if args.out else project / scene["out"]

    bpy.ops.wm.read_factory_settings(use_empty=True)
    started = time.monotonic()

    assets = {}
    for entry in scene["assets"]:
        module = importlib.import_module(entry["script"])
        asset = module.build(**entry.get("params", {}))
        if asset.id != entry["id"]:
            raise SystemExit(f"{entry['script']} built '{asset.id}', scene expects '{entry['id']}'")
        asset.place(tuple(entry.get("position", (0, 0, 0))), entry.get("rotationZ", 0))
        assets[asset.id] = asset

    errors = [e for a in assets.values() for e in checks.check_asset(a)]
    errors += checks.check_scene(assets, scene["assets"])
    if errors:
        print("GEOMETRY CHECKS FAILED", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    parts = [p for a in assets.values() for p in a.parts]
    bake = scene.get("bake", {})
    bake_ao(parts, samples=bake.get("samples", 64), distance=bake.get("distance", 1.0))
    baked_at = time.monotonic()

    report = {"scene": scene["id"], "assets": {}}
    for aid, asset in assets.items():
        path = out / f"{aid}.envelope.glb"
        stats = export_asset(asset, path)
        report["assets"][aid] = {"main": asset.main, "airborne": asset.airborne, "envelope": path.name, **stats}
    report["timings_s"] = {"model_and_bake": round(baked_at - started, 2), "total": round(time.monotonic() - started, 2)}
    reports = ART / ".build"
    reports.mkdir(exist_ok=True)
    (reports / f"{scene['id']}.report.json").write_text(json.dumps({**report, "out": str(out)}, indent=2) + "\n")
    print(json.dumps(report["timings_s"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
