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
    ) -> bpy.types.Object:
        full = f"{self.id}.{name}"
        if bpy.data.objects.get(full):
            raise ValueError(f"duplicate part name: {full}")
        mesh = bpy.data.meshes.new(full)
        bm.to_mesh(mesh)
        bm.free()
        mesh.materials.append(palette.material(material))
        if smooth:
            mesh.shade_smooth()
            mesh.set_sharp_from_angle(angle=SHARP_ANGLE)
        obj = bpy.data.objects.new(full, mesh)
        obj.parent = self.root
        obj.location = location
        obj.rotation_euler = Euler(tuple(radians(a) for a in rotation))
        obj["xs_open"] = open_surface
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
