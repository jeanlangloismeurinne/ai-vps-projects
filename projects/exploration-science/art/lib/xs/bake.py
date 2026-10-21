"""Ambient occlusion baked by Cycles (CPU) into the colour attribute "AO" of every part.

The bake runs on the assembled scene, so contact shadows between assets (a house on
its ground) are part of the result. Settings come from the scene file.
"""

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

AO_ATTRIBUTE = "AO"
BURIED_AO = 0.15


def bake_ao(objects: list[bpy.types.Object], *, samples: int, distance: float, seed: int = 0) -> None:
    scene = bpy.context.scene
    if scene.world is None:
        scene.world = bpy.data.worlds.new("bake")
    scene.world.light_settings.distance = distance
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.seed = seed
    scene.cycles.use_denoising = False
    scene.render.bake.target = "VERTEX_COLORS"
    for obj in objects:
        if not obj.get("xs_occluder", True):
            obj.visible_diffuse = False
            obj.visible_glossy = False
            obj.visible_shadow = False
            obj.visible_transmission = False
        attrs = obj.data.color_attributes
        if AO_ATTRIBUTE not in attrs:
            attrs.new(AO_ATTRIBUTE, "BYTE_COLOR", "CORNER")
        attrs.active_color = attrs[AO_ATTRIBUTE]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.bake(type="AO")


def lift_buried(objects: list[bpy.types.Object], reach: float = 0.04, passes: int = 40) -> None:
    """A vertex covered by another part (the ground under a lawn inlay or a house floor)
    bakes black; it is hidden, but its darkness bleeds into the visible triangles around
    it as saw teeth. A vertex is covered when a ray cast straight up from just below it
    meets another part within `reach`; covered vertices take the mean of their visible
    neighbours, spreading inward pass after pass."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    up = Vector((0, 0, 1))
    for obj in objects:
        mesh = obj.data
        to_world = obj.matrix_world
        normal_to_world = to_world.to_3x3().inverted().transposed()
        # A vertex of any upward face: a bevel corner's averaged normal can lean below 0.5.
        candidates = sorted({i for poly in mesh.polygons if (normal_to_world @ poly.normal).normalized().z > 0.5 for i in poly.vertices})
        if not candidates:
            continue
        others = _others_bvh(objects, obj, depsgraph)
        attr = mesh.color_attributes[AO_ATTRIBUTE]
        loops_of: dict[int, list[int]] = {}
        for loop in mesh.loops:
            loops_of.setdefault(loop.vertex_index, []).append(loop.index)
        neighbours: dict[int, set[int]] = {}
        for e in mesh.edges:
            a, b = e.vertices
            neighbours.setdefault(a, set()).add(b)
            neighbours.setdefault(b, set()).add(a)
        value = {v: sum(attr.data[i].color[0] for i in ls) / len(ls) for v, ls in loops_of.items()}
        # Hidden: covered by another part, or sunk inside one (it then bakes almost black;
        # no visible vertex of this open scene goes that low).
        covered = {i for i in candidates if value.get(i, 1.0) < BURIED_AO or _covered(others, to_world @ mesh.vertices[i].co, up, reach)}
        if not covered:
            continue
        upper = set(candidates)
        pending = set(covered)
        for _ in range(passes):
            done = {}
            for v in pending:
                # Only visible upper-surface neighbours: an underside vertex is buried too.
                known = [value[n] for n in neighbours.get(v, ()) if n in upper and n not in pending]
                if known:
                    done[v] = sum(known) / len(known)
            if not done:
                break
            value.update(done)
            pending -= set(done)
        # No visible upper neighbour at all (a ridge vertex under its cap, whose neighbours
        # are the ridge and the roof's edge): the lightest neighbour, as a last resort.
        for v in pending:
            value[v] = max((value[n] for n in neighbours.get(v, ())), default=value[v])
        for v in covered:
            for i in loops_of[v]:
                attr.data[i].color = (value[v], value[v], value[v], 1.0)


def _covered(others: BVHTree, point: Vector, up: Vector, reach: float) -> bool:
    """True when the first surface met going up is the underside of another part (a face
    turned toward the ray). Starting 2 mm below catches a part laid flush on this one;
    the top of the part this one rests on is met from behind and skipped."""
    origin, left = point - up * 0.002, reach + 0.002
    for _ in range(4):
        location, normal, _index, distance = others.ray_cast(origin, up, left)
        if location is None:
            return False
        if normal.dot(up) < 0:
            return True
        origin, left = location + up * 1e-4, left - distance - 1e-4
        if left <= 0:
            return False
    return False


def _others_bvh(objects: list[bpy.types.Object], skip: bpy.types.Object, depsgraph) -> BVHTree:
    bm = bmesh.new()
    for o in objects:
        if o is skip:
            continue
        tmp = o.data.copy()
        tmp.transform(o.matrix_world)
        bm.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    tree = BVHTree.FromBMesh(bm)
    bm.free()
    return tree
