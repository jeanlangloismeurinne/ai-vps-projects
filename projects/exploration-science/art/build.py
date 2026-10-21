"""Build the models of one system file: model → place → check → bake AO → export GLB → report.

Usage (from the project root):
  art/.venv/bin/python art/build.py --system <system>.json [--out DIR]

Scripts come from art/assets.json; placements, roles and anchors from the system file
(schemas/v2/system.schema.json, validated by `npm run assets` before Blender runs).
Exits 1 when a check fails: nothing is exported then.
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
from mathutils import Vector  # noqa: E402

from xs import checks  # noqa: E402
from xs.bake import bake_ao  # noqa: E402
from xs.export import export_asset  # noqa: E402

RAY_HEIGHT = 1000.0


def support_order(objects: list[dict]) -> list[dict]:
    """Supports before what stands on them (the schema validator refuses cycles)."""
    by_id = {o["id"]: o for o in objects}
    done: list[str] = []

    def visit(o: dict) -> None:
        if o["id"] in done:
            return
        on = o.get("placement", {}).get("on")
        if on:
            visit(by_id[on])
        done.append(o["id"])

    for o in objects:
        visit(o)
    return [by_id[i] for i in done]


def place(asset, placement: dict, assets: dict) -> str | None:
    """Sets the asset's root from its placement. Returns an error message or None."""
    rotation = placement.get("rotationZDeg", 0)
    if not placement:
        asset.place((0, 0, 0))
    elif placement.get("airborne"):
        asset.place(tuple(placement["position"]), rotation)
    elif "anchor" in placement:
        support = assets[placement["on"]]
        empty = support.anchors.get(placement["anchor"])
        if empty is None:
            return f"unknown anchor: {support.id}#{placement['anchor']} (placement of {asset.id})"
        bpy.context.view_layer.update()
        asset.place(tuple(empty.matrix_world.translation), rotation)
    else:
        x, y = placement["position"]
        bpy.context.view_layer.update()
        hit = checks.Shape(assets[placement["on"]].parts).tree.ray_cast(Vector((x, y, RAY_HEIGHT)), Vector((0, 0, -1)))[0]
        if hit is None:
            return f"no support: nothing of {placement['on']} under {asset.id} at ({x}, {y})"
        asset.place((x, y, hit.z), rotation)
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", required=True)
    parser.add_argument("--out", help="output directory (default: art/assets.json `out`)")
    args = parser.parse_args()

    project = ART.parent
    system = json.loads(Path(args.system).read_text())
    registry = json.loads((ART / "assets.json").read_text())
    out = Path(args.out).resolve() if args.out else project / registry["out"]

    bpy.ops.wm.read_factory_settings(use_empty=True)
    started = time.monotonic()

    assets = {}
    errors: list[str] = []
    for obj in support_order(system["objects"]):
        oid = obj["id"]
        reps = obj.get("representations", ["envelope"])
        if reps != ["envelope"]:
            # Representations are built one scene at a time; the detail view comes with roadmap §6.
            return fail([f"{oid}: only the envelope representation is built for now, got {reps}"])
        entry = registry["assets"].get(oid)
        if entry is None:
            return fail([f"{oid}: no entry in art/assets.json"])
        module = importlib.import_module(entry["envelope"]["script"])
        asset = module.build(**entry["envelope"].get("params", {}))
        if asset.id != oid:
            return fail([f"{entry['envelope']['script']} built '{asset.id}', the system expects '{oid}'"])
        asset.main = obj["role"] == "main"
        asset.airborne = bool(obj.get("placement", {}).get("airborne"))
        missing = sorted(set(obj.get("anchors", [])) - set(asset.anchors))
        errors += [f"missing anchor: {oid}#{a} is declared by the system but not built" for a in missing]
        assets[oid] = asset
        error = place(asset, obj.get("placement", {}), assets)
        if error:
            errors.append(error)
    if errors:
        return fail(errors)

    placements = [{"id": o["id"], "on": o.get("placement", {}).get("on")} for o in system["objects"]]
    errors = [e for a in assets.values() for e in checks.check_asset(a)]
    errors += checks.check_scene(assets, placements)
    if errors:
        return fail(errors)

    parts = [p for a in assets.values() for p in a.parts]
    bake = registry["bake"]
    bake_ao(parts, samples=bake["samples"], distance=bake["distance"])
    baked_at = time.monotonic()

    report = {"system": system["id"], "assets": {}}
    for aid, asset in assets.items():
        path = out / f"{aid}.envelope.glb"
        stats = export_asset(asset, path)
        report["assets"][aid] = {"main": asset.main, "airborne": asset.airborne, "envelope": path.name, **stats}
    report["timings_s"] = {"model_and_bake": round(baked_at - started, 2), "total": round(time.monotonic() - started, 2)}
    reports = ART / ".build"
    reports.mkdir(exist_ok=True)
    (reports / f"{system['id']}.report.json").write_text(json.dumps({**report, "out": str(out)}, indent=2) + "\n")
    print(json.dumps(report["timings_s"]))
    return 0


def fail(errors: list[str]) -> int:
    print("GEOMETRY CHECKS FAILED", file=sys.stderr)
    for e in errors:
        print(f"  - {e}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
