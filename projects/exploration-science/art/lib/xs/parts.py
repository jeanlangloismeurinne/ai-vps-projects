"""Shared component builders: the parts several assets are made of (a parabolic dish, its
feed struts, a solar wing, a fibre handhole). Library logic: a new scene reuses these
before modelling anything again; each builder is deterministic like `geom`."""

from math import atan2, cos, radians, sin

import bmesh
from mathutils import Matrix, Vector

from .geom import Asset, box, cylinder, lathe, merged


def dish(focal: float, radius: float, *, inner: float = 0.02, steps: int = 8, rim: float = 0.006, drop: float = 0.008, thickness: float = 0.018, segments: int = 40) -> bmesh.types.BMesh:
    """A paraboloid reflector z = r² / (4 f), opening toward +z, its vertex at the origin,
    with a rolled rim (`rim` out, `drop` down) and a back face `thickness` below."""
    face = [(inner + (radius - inner) * i / steps, ((inner + (radius - inner) * i / steps) ** 2) / (4 * focal)) for i in range(steps + 1)]
    profile = face + [(radius + rim, face[-1][1] - drop)] + [(r, z - thickness) for r, z in reversed(face)]
    return lathe(profile, segments)


def struts(focal: float, attach: float, base: float, tip: float, *, count: int = 3, radius: float = 0.006, start_deg: float = 0.0, verts: int = 6) -> bmesh.types.BMesh:
    """`count` struts from the dish surface at radius `attach` (dish vertex at height `base`)
    up to the axis at height `tip`, where the feed or the sub-reflector sits."""
    out = []
    for k in range(count):
        u = Vector((cos(radians(start_deg + k * 360 / count)), sin(radians(start_deg + k * 360 / count)), 0))
        foot = u * attach + Vector((0, 0, base + attach**2 / (4 * focal)))
        top = Vector((0, 0, tip))
        strut = cylinder(radius, (top - foot).length, verts)
        lean = atan2(attach, top.z - foot.z)
        strut.transform(Matrix.Translation((foot + top) / 2) @ Matrix.Rotation(-lean, 4, Vector((-u.y, u.x, 0))))
        out.append((strut, (0, 0, 0), (0, 0, 0)))
    return merged(out)


def solar_wing(a: Asset, name: str, length: float, width: float, cells: tuple[int, int], centre: tuple[float, float, float], *, along: str = "x", frame: str = "metal", cell: str = "graphite") -> None:
    """A flat solar panel: a metal frame and its grid of cells, `length` along `along`."""
    cx, cy, cz = centre
    sx, sy = (length, width) if along == "x" else (width, length)
    a.add(f"{name}-frame", box(sx, sy, 0.018, bevel=0.004), frame, centre)
    nl, nw = cells
    cl, cw = (length - 0.04) / nl, (width - 0.04) / nw
    items = []
    for i in range(nl):
        for j in range(nw):
            u, v = -length / 2 + 0.02 + cl * (i + 0.5), -width / 2 + 0.02 + cw * (j + 0.5)
            dx, dy = (u, v) if along == "x" else (v, u)
            bx, by = (cl - 0.012, cw - 0.012) if along == "x" else (cw - 0.012, cl - 0.012)
            items.append((box(bx, by, 0.024), (cx + dx, cy + dy, cz), (0, 0, 0)))
    a.add(f"{name}-cells", merged(items), cell, smooth=False)


def fibre_handhole(a: Asset, x: float, y: float) -> tuple[float, float, float]:
    """A fibre handhole on the ground, its duct and its signal-blue marker post. Returns
    the point on the lid where a fibre link starts."""
    a.add("handhole", box(0.3, 0.22, 0.06, bevel=0.01), "mid", (x, y, 0.02))
    a.add("handhole-lid", box(0.24, 0.16, 0.012), "graphite", (x, y, 0.056))
    a.add("fibre-duct", box(0.06, 0.22, 0.035, bevel=0.006), "graphite", (x, y + 0.17, 0.0175))
    a.add("fibre-marker", merged([(cylinder(0.02, 0.32, 10), (x + 0.165, y, 0.16), (0, 0, 0)), (box(0.06, 0.02, 0.08), (x + 0.165, y, 0.29), (0, 0, 0))]), "signal")
    return (x, y, 0.062)
