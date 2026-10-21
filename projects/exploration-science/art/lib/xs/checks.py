"""Geometric checks run on the assembled scene, before baking (QUALITY_BAR §3, Géométrie).

- every part of an asset touches another part of it (no floating element);
- every asset rests on its declared support (`on`), unless it is airborne;
- two assets with no support relation do not interpenetrate;
- closed parts are manifold (no missing surface).
Tolerance: 1 mm.
"""

import bmesh
import bpy
from mathutils.bvhtree import BVHTree

TOLERANCE = 0.001


def _world_bmesh(obj: bpy.types.Object) -> bmesh.types.BMesh:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    return bm


class Shape:
    def __init__(self, objs: list[bpy.types.Object]):
        bm = bmesh.new()
        for obj in objs:
            part = _world_bmesh(obj)
            tmp = bpy.data.meshes.new("_tmp")
            part.to_mesh(tmp)
            part.free()
            bm.from_mesh(tmp)
            bpy.data.meshes.remove(tmp)
        self.verts = [v.co.copy() for v in bm.verts]
        self.tree = BVHTree.FromBMesh(bm)
        bm.free()

    def touches(self, other: "Shape") -> bool:
        if self.tree.overlap(other.tree):
            return True
        return any(other.tree.find_nearest(v, TOLERANCE)[0] is not None for v in self.verts) or any(
            self.tree.find_nearest(v, TOLERANCE)[0] is not None for v in other.verts
        )


def _connected(nodes: list[str], edges: set[tuple[str, str]]) -> list[str]:
    """Nodes not reachable from the first one."""
    if not nodes:
        return []
    seen, stack = {nodes[0]}, [nodes[0]]
    while stack:
        n = stack.pop()
        for a, b in edges:
            for x, y in ((a, b), (b, a)):
                if x == n and y not in seen:
                    seen.add(y)
                    stack.append(y)
    return [n for n in nodes if n not in seen]


def check_asset(asset) -> list[str]:
    errors: list[str] = []
    bpy.context.view_layer.update()
    shapes = {p.name: Shape([p]) for p in asset.parts}
    names = list(shapes)
    edges = {(a, b) for i, a in enumerate(names) for b in names[i + 1 :] if shapes[a].touches(shapes[b])}
    for n in _connected(names, edges):
        errors.append(f"floating part: {n} touches no other part of {asset.id}")
    for p in asset.parts:
        if p["xs_open"]:
            continue
        bm = bmesh.new()
        bm.from_mesh(p.data)
        bad = sum(1 for e in bm.edges if not e.is_manifold)
        bm.free()
        if bad:
            errors.append(f"open surface: {p.name} has {bad} non-manifold edges")
    return errors


def check_scene(assets: dict, placements: list[dict]) -> list[str]:
    """`placements`: one {id, on} per system object. Support relations come from `on`."""
    errors: list[str] = []
    bpy.context.view_layer.update()
    shapes = {aid: Shape(a.parts) for aid, a in assets.items()}
    support = {(p["id"], p["on"]) for p in placements if p.get("on")}
    for p in placements:
        aid = p["id"]
        if assets[aid].airborne or not p.get("on"):
            continue
        if not shapes[aid].touches(shapes[p["on"]]):
            errors.append(f"not resting: {aid} does not touch its support {p['on']}")
    ids = list(assets)
    for i, a in enumerate(ids):
        for b in ids[i + 1 :]:
            if (a, b) in support or (b, a) in support:
                continue
            if shapes[a].tree.overlap(shapes[b].tree):
                errors.append(f"intersection: {a} and {b} interpenetrate")
    return errors
