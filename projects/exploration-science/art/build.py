"""Build the models of one system file: model → place → check → bake AO → export GLB → report.

Usage (from the project root):
  art/.venv/bin/python art/build.py --system <system>.json [--out DIR]

Scripts come from art/assets.json; placements, roles and anchors from the system file
(schemas/v2/system.schema.json, validated by `npm run assets` before Blender runs).
Exits 1 when a check fails: nothing is exported then.

A `detail` representation (exploded view) is built after the envelopes have been baked and
exported: checked assembled (no floating part), then exploded and checked against the scene
in place of its envelope (no intersection), baked with the envelope hidden, exported.
"""

import argparse
import importlib
import json
import math
import sys
import time
from pathlib import Path

ART = Path(__file__).resolve().parent
sys.path[:0] = [str(ART / "lib"), str(ART)]

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from xs import checks  # noqa: E402
from xs.bake import bake_ao, lift_buried  # noqa: E402
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
    details: list[tuple[dict, dict]] = []
    errors: list[str] = []
    for obj in support_order(system["objects"]):
        oid = obj["id"]
        reps = obj.get("representations", ["envelope"])
        if "envelope" not in reps:
            return fail([f"{oid}: no envelope representation, got {reps}"])
        entry = registry["assets"].get(oid)
        if entry is None:
            return fail([f"{oid}: no entry in art/assets.json"])
        if "detail" in reps:
            details.append((obj, entry))
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
    lift_buried(parts)
    baked_at = time.monotonic()

    report = {"system": system["id"], "assets": {}}
    for aid, asset in assets.items():
        path = out / f"{aid}.envelope.glb"
        stats = export_asset(asset, path)
        loc, rot = asset.root.matrix_world.translation, asset.root.matrix_world.to_euler()
        world = {"position": [round(c, 6) for c in loc], "rotationZDeg": round(math.degrees(rot.z), 6)}
        report["assets"][aid] = {"main": asset.main, "airborne": asset.airborne, "world": world, "envelope": path.name, **stats}
    for obj, entry in details:
        errors = build_detail(obj, entry, assets, placements, report, out, bake)
        if errors:
            return fail(errors)
    report["timings_s"] = {"model_and_bake": round(baked_at - started, 2), "total": round(time.monotonic() - started, 2)}
    reports = ART / ".build"
    reports.mkdir(exist_ok=True)
    (reports / f"{system['id']}.report.json").write_text(json.dumps({**report, "out": str(out)}, indent=2) + "\n")
    print(json.dumps(report["timings_s"]))
    return 0


def build_detail(obj: dict, entry: dict, assets: dict, placements: list[dict], report: dict, out: Path, bake: dict) -> list[str]:
    """Builds, checks, bakes and exports the exploded view of one object."""
    oid = obj["id"]
    envelope = assets[oid]
    # Exported already: its names are freed for the detail's parts and anchors.
    for o in [envelope.root, *envelope.parts, *envelope.anchors.values()]:
        o.name = f"{o.name}~envelope"
    module = importlib.import_module(entry["detail"]["script"])
    detail = module.build(**entry["detail"].get("params", {}))
    if detail.id != oid:
        return [f"{entry['detail']['script']} built '{detail.id}', the system expects '{oid}'"]
    detail.main, detail.airborne = envelope.main, envelope.airborne
    for part in envelope.parts:  # out of the checks and of the bake
        part.hide_render = True
    error = place(detail, obj.get("placement", {}), assets)
    if error:
        return [error]
    missing = sorted(set(obj.get("anchors", [])) - set(detail.anchors))
    errors = [f"missing anchor: {oid}#{a} (detail) is declared by the system but not built" for a in missing]
    errors += [f"{e} (detail, assembled)" for e in checks.check_asset(detail)]
    if errors:
        return errors
    detail.explode()
    scene = {**assets, oid: detail}
    errors = [f"{e} (detail, exploded)" for e in checks.check_scene(scene, placements)]
    if errors:
        return errors
    bake_ao(detail.parts, samples=bake["samples"], distance=bake["distance"])
    lift_buried(detail.parts)
    path = out / f"{oid}.detail.glb"
    report["assets"][oid]["detail"] = {"file": path.name, **export_asset(detail, path)}
    return []


def fail(errors: list[str]) -> int:
    print("GEOMETRY CHECKS FAILED", file=sys.stderr)
    for e in errors:
        print(f"  - {e}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
