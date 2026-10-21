"""Mesh builders (bmesh, deterministic) and the Asset container.

Convention: Blender is Z-up, metres. The exporter converts to glTF Y-up. An asset's
root sits at the origin, its footprint on z = 0 (unless it is airborne).
"""

from math import radians

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

from . import palette

SHARP_ANGLE = radians(35)


# --- bmesh builders: each returns a new BMesh centred on the origin -----------------


def box(sx: float, sy: float, sz: float, bevel: float = 0.0, segments: int = 2) -> bmesh.types.BMesh:
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector((sx, sy, sz)), verts=bm.verts)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=segments, profile=0.5, affect="EDGES", clamp_overlap=True)
    return bm


def cylinder(radius: float, depth: float, verts: int = 32, bevel: float = 0.0, segments: int = 2) -> bmesh.types.BMesh:
    return cone(radius, radius, depth, verts, bevel, segments)


def cone(r1: float, r2: float, depth: float, verts: int = 32, bevel: float = 0.0, segments: int = 2) -> bmesh.types.BMesh:
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=verts, radius1=r1, radius2=r2, depth=depth)
    if bevel > 0:
        rims = [e for e in bm.edges if not e.is_wire and any(len(f.verts) > 4 for f in e.link_faces)]
        bmesh.ops.bevel(bm, geom=rims, offset=bevel, segments=segments, profile=0.5, affect="EDGES", clamp_overlap=True)
    return bm


def sphere(radius: float, segments: int = 24, rings: int = 12) -> bmesh.types.BMesh:
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius)
    return bm


def prism(points: list[tuple[float, float]], depth: float, bevel: float = 0.0, segments: int = 2) -> bmesh.types.BMesh:
    """A 2D polygon drawn in the XZ plane (x, z), extruded symmetrically along Y."""
    bm = bmesh.new()
    verts = [bm.verts.new((x, -depth / 2, z)) for x, z in points]
    face = bm.faces.new(verts)
    bmesh.ops.recalc_face_normals(bm, faces=[face])
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    moved = [g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=Vector((0, depth, 0)), verts=moved)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=segments, profile=0.5, affect="EDGES", clamp_overlap=True)
    return bm


def canonical_order(mesh: bpy.types.Mesh) -> None:
    """Sorts vertices and faces by position: the same shapes give the same index buffers
    whatever order the operators produced them in. Applied to every part before the
    bake (Cycles' BVH, hence the AO, depends on it) and again after the merge at export."""
    bm = bmesh.new()
    bm.from_mesh(mesh)

    def key(co):
        return (round(co.x, 5), round(co.y, 5), round(co.z, 5))

    for v in bm.verts:  # some operators (solidify) leave last-bit noise from run to run
        v.co = key(v.co)
    rank = {v.index: r for r, v in enumerate(sorted(bm.verts, key=lambda v: (key(v.co), v.index)))}
    bm.verts.sort(key=lambda v: rank[v.index])
    bm.verts.index_update()
    order = sorted(bm.faces, key=lambda f: (key(f.calc_center_median()), sorted(v.index for v in f.verts)))
    rank = {f.index: r for r, f in enumerate(order)}
    bm.faces.sort(key=lambda f: rank[f.index])
    bm.to_mesh(mesh)
    bm.free()


# --- Asset ---------------------------------------------------------------------------


class Asset:
    """One stable object id: a root empty and its named parts.

    `airborne` assets (a satellite) are exempt from the ground-contact check. A part
    flagged `open` is a deliberately open surface, exempt from the manifold check.
    """

    def __init__(self, asset_id: str, *, airborne: bool = False, main: bool = True):
        self.id = asset_id
        self.airborne = airborne
        self.main = main
        self.root = bpy.data.objects.new(asset_id, None)
        bpy.context.scene.collection.objects.link(self.root)
        self.parts: list[bpy.types.Object] = []
        self.anchors: dict[str, bpy.types.Object] = {}

    def add(
        self,
        name: str,
        bm: bmesh.types.BMesh,
        material: str,
        location: tuple[float, float, float] = (0, 0, 0),
        rotation: tuple[float, float, float] = (0, 0, 0),
        *,
        smooth: bool = True,
        open_surface: bool = False,
        occluder: bool = True,
    ) -> bpy.types.Object:
        full = f"{self.id}.{name}"
        if bpy.data.objects.get(full):
            raise ValueError(f"duplicate part name: {full}")
        mesh = bpy.data.meshes.new(full)
        bm.to_mesh(mesh)
        bm.free()
        canonical_order(mesh)
        mesh.materials.append(palette.material(material))
        if smooth:
            mesh.shade_smooth()
            mesh.set_sharp_from_angle(angle=SHARP_ANGLE)
        obj = bpy.data.objects.new(full, mesh)
        obj.parent = self.root
        obj.location = location
        obj.rotation_euler = Euler(tuple(radians(a) for a in rotation))
        obj["xs_open"] = open_surface
        # Thin parts (fence, struts) cast no baked occlusion: on the ground's coarse grid
        # their contact darkening turns into blotches. The real-time shadow draws them.
        obj["xs_occluder"] = occluder
        bpy.context.scene.collection.objects.link(obj)
        self.parts.append(obj)
        return obj

    def repeat(self, name: str, builder, material: str, placements: list[tuple[tuple, tuple]], **kw) -> list[bpy.types.Object]:
        """The same shape at several (location, rotation) placements, each a numbered part."""
        return [self.add(f"{name}{i:02d}", builder(), material, loc, rot, **kw) for i, (loc, rot) in enumerate(placements)]

    def anchor(self, name: str, location: tuple[float, float, float]) -> bpy.types.Object:
        """A named attachment point (`<id>#<name>`): where a link starts or another object sits."""
        if name in self.anchors:
            raise ValueError(f"duplicate anchor: {self.id}#{name}")
        empty = bpy.data.objects.new(f"{self.id}#{name}", None)
        empty.parent = self.root
        empty.location = location
        bpy.context.scene.collection.objects.link(empty)
        self.anchors[name] = empty
        return empty

    def place(self, location: tuple[float, float, float], rotation_z_deg: float = 0.0) -> None:
        self.root.matrix_world = Matrix.Translation(Vector(location)) @ Euler((0, 0, radians(rotation_z_deg))).to_matrix().to_4x4()


# --- compound builders --------------------------------------------------------------


def rounded_rect(sx: float, sy: float, radius: float, corner_verts: int = 6) -> list[tuple[float, float]]:
    """Counter-clockwise outline of a rectangle with rounded corners, centred on the origin."""
    from math import cos, pi, sin

    r = min(radius, sx / 2, sy / 2)
    pts = []
    for cx, cy, start in ((sx / 2 - r, sy / 2 - r, 0), (-sx / 2 + r, sy / 2 - r, 90), (-sx / 2 + r, -sy / 2 + r, 180), (sx / 2 - r, -sy / 2 + r, 270)):
        for i in range(corner_verts + 1):
            a = radians(start + 90 * i / corner_verts)
            pts.append((cx + r * cos(a), cy + r * sin(a)))
    return pts


def extrude_xy(points: list[tuple[float, float]], z0: float, z1: float, bevel: float = 0.0, segments: int = 2) -> bmesh.types.BMesh:
    """A 2D outline in the XY plane, extruded from z0 to z1."""
    bm = bmesh.new()
    verts = [bm.verts.new((x, y, z0)) for x, y in points]
    face = bm.faces.new(verts)
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    moved = [g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=Vector((0, 0, z1 - z0)), verts=moved)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    if bevel > 0:
        rims = [e for e in bm.edges if any(len(f.verts) > 4 for f in e.link_faces)]
        bmesh.ops.bevel(bm, geom=rims, offset=bevel, segments=segments, profile=0.5, affect="EDGES", clamp_overlap=True)
    return bm


def lathe(profile: list[tuple[float, float]], segments: int = 32) -> bmesh.types.BMesh:
    """A profile of (radius, z) points revolved around Z. Radii must be > 0: both ends are
    capped with a flat n-gon, so the result is closed."""
    bm = bmesh.new()
    verts = [bm.verts.new((r, 0, z)) for r, z in profile]
    edges = [bm.edges.new((verts[i], verts[i + 1])) for i in range(len(verts) - 1)]
    bmesh.ops.spin(bm, geom=verts + edges, cent=(0, 0, 0), axis=(0, 0, 1), angle=radians(360), steps=segments, use_merge=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.holes_fill(bm, edges=bm.edges, sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    return bm


def grid_slab(points: list[tuple[float, float]], z0: float, z1: float, cell: float) -> bmesh.types.BMesh:
    """An extruded outline whose top face is subdivided into ~`cell`-sized pieces, so the
    baked occlusion (stored per vertex) can draw contact shadows on it."""
    bm = extrude_xy(points, z0, z1)
    top = [f for f in bm.faces if f.normal.z > 0.99]
    bmesh.ops.triangulate(bm, faces=top)
    for _ in range(12):
        long_edges = [e for e in bm.edges if e.calc_length() > cell and all(v.co.z > z1 - 1e-6 for v in e.verts)]
        if not long_edges:
            break
        bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=1, use_grid_fill=False)
        tops = [f for f in bm.faces if f.normal.z > 0.99 and len(f.verts) > 3]
        bmesh.ops.triangulate(bm, faces=tops)
    bmesh.ops.beautify_fill(bm, faces=[f for f in bm.faces if f.normal.z > 0.99], edges=[e for e in bm.edges if all(v.co.z > z1 - 1e-6 for v in e.verts)])
    return bm


def merged(items: list[tuple[bmesh.types.BMesh, tuple, tuple]]) -> bmesh.types.BMesh:
    """Several shapes, each moved to (location, rotation in degrees), in one BMesh (one part)."""
    out = bmesh.new()
    for bm, loc, rot in items:
        m = Matrix.Translation(Vector(loc)) @ Euler(tuple(radians(a) for a in rot)).to_matrix().to_4x4()
        bm.transform(m)
        tmp = bpy.data.meshes.new("_merge")
        bm.to_mesh(tmp)
        bm.free()
        out.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    return out
