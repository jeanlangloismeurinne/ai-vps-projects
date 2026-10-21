"""A single-storey house with a gabled roof, a garage and a terrace (Z up, front = −y).

Diorama scale ≈ 1:3.3 (a 10 × 7 m house is 3 × 2.2 units). The roof ridge runs along x;
the anchor `roof` sits on the ridge cap, where the Starlink terminal is mounted."""

from math import cos, radians, sin, tan

from mathutils import Vector

from xs.geom import Asset, box, cylinder, merged, prism, sphere

W, D, H = 3.0, 2.2, 0.95  # body width (x), depth (y), wall height
BASE = 0.1  # foundation height above the ground (sunk 0.04 below it)
PITCH = 30.0
OVERHANG = 0.22
ROOF_T = 0.06


def build(pitch: float = PITCH) -> Asset:
    a = Asset("house")
    p = radians(pitch)
    z_wall = BASE + H
    rise = D / 2 * tan(p)
    ridge = Vector((0, 0, z_wall + rise))

    a.add("foundation", box(W + 0.08, D + 0.08, BASE + 0.04, bevel=0.01), "mid", (0, 0, (BASE - 0.04) / 2))
    a.add("walls", box(W, D, H, bevel=0.02), "white", (0, 0, BASE + H / 2))
    attic = prism([(-D / 2, 0), (D / 2, 0), (0, rise)], W - 0.002)
    a.add("gables", attic, "white", (0, 0, z_wall), (0, 0, 90), smooth=False)

    # Roof: two slabs whose underside lies on the gable slopes, meeting under the ridge cap.
    length = (D / 2 + OVERHANG) / cos(p)
    for side, sign in (("front", -1), ("back", 1)):
        d = Vector((0, sign * cos(p), -sin(p)))
        n = Vector((0, sign * sin(p), cos(p)))
        c = ridge + d * (length / 2) + n * (ROOF_T / 2)
        a.add(f"roof-{side}", box(W + 2 * OVERHANG, length, ROOF_T, bevel=0.012), "graphite", tuple(c), (-sign * pitch, 0, 0))
    cap_z = ridge.z + ROOF_T / cos(p)
    a.add("ridge-cap", box(W + 2 * OVERHANG + 0.02, 0.14, 0.05, bevel=0.012), "mid", (0, 0, cap_z - 0.005))
    eave_z = z_wall - OVERHANG * tan(p) - 0.01
    a.add(
        "gutters",
        merged([(cylinder(0.035, W + 2 * OVERHANG, 12), (0, s * (D / 2 + OVERHANG + 0.02), eave_z), (0, 90, 0)) for s in (-1, 1)]),
        "light",
    )
    a.add("downpipes", merged([(cylinder(0.022, eave_z - BASE, 10), (s * (W / 2 + 0.06), -(D / 2 + 0.02), (eave_z + BASE) / 2), (0, 0, 0)) for s in (-1, 1)]), "light")
    a.add("chimney", box(0.26, 0.26, 0.55, bevel=0.015), "light", (-0.85, 0.45, z_wall + rise - 0.1))
    a.add("chimney-cap", box(0.34, 0.34, 0.05, bevel=0.01), "graphite", (-0.85, 0.45, z_wall + rise + 0.2))

    # Openings on the front (−y), the sides and the back: glass panes in graphite frames.
    yf, zc = -D / 2, BASE + 0.5
    panes = [  # (x or y, z, width, height, face)
        (-1.0, zc, 0.52, 0.55, "front"), (0.45, zc - 0.08, 0.95, 0.72, "front"), (1.15, zc, 0.3, 0.55, "front"),
        (-0.35, zc, 0.7, 0.55, "back"), (0.7, zc, 0.7, 0.55, "back"),
        (0.0, zc, 0.8, 0.55, "east"),
    ]
    frames, glass = [], []
    for u, z, w, h, face in panes:
        loc, rot = _on_face(face, u, z)
        frames.append((box(w + 0.07, 0.035, h + 0.07, bevel=0.008), loc, rot))
        frames.append((box(0.03, 0.05, h, bevel=0.005), loc, rot))  # mullion
        glass.append((box(w, 0.045, h), _push(face, loc, -0.004), rot))
    a.add("window-frames", merged(frames), "graphite")
    a.add("windows", merged(glass), "glass", smooth=False)
    a.add("sills", merged([(box(w + 0.12, 0.08, 0.03, bevel=0.006), _push(f, _on_face(f, u, z - h / 2 - 0.05)[0], 0.02), _on_face(f, u, 0)[1]) for u, z, w, h, f in panes if h < 0.7]), "light")
    a.add("door", box(0.34, 0.04, 0.66, bevel=0.01), "warm", (-0.35, yf - 0.005, BASE + 0.33))
    a.add("door-canopy", box(0.6, 0.32, 0.04, bevel=0.01), "light", (-0.35, yf - 0.15, BASE + 0.76))
    a.add("doorstep", box(0.6, 0.3, 0.06, bevel=0.01), "light", (-0.35, yf - 0.17, 0.03))

    # Garage on the west side, flat roof with a parapet, sectional door.
    gx = -W / 2 - 0.55
    a.add("garage", box(1.1, 1.8, 0.78, bevel=0.02), "light", (gx, -0.18, 0.39))
    a.add("garage-roof", box(1.2, 1.9, 0.06, bevel=0.012), "mid", (gx, -0.18, 0.8))
    a.add("garage-door", merged([(box(0.8, 0.03, 0.11, bevel=0.008), (gx, -1.085, 0.1 + i * 0.125), (0, 0, 0)) for i in range(5)]), "white")

    # Terrace on the east side: decking boards, two planters with shrubs.
    tx = W / 2 + 0.5
    a.add("deck", merged([(box(0.11, 1.6, 0.05, bevel=0.008), (tx - 0.42 + i * 0.12, -0.1, 0.03), (0, 0, 0)) for i in range(8)]), "warm")
    a.add("deck-joists", box(0.98, 1.56, 0.03), "mid", (tx, -0.1, -0.005))
    a.add("planters", merged([(box(0.22, 0.22, 0.2, bevel=0.015), (tx + 0.33, y, 0.15), (0, 0, 0)) for y in (-0.72, 0.52)]), "graphite")
    a.add("shrubs", merged([(sphere(0.15, 12, 8), (tx + 0.33, y, 0.36), (0, 0, 0)) for y in (-0.72, 0.52)]), "foliage")
    a.add("wall-light", box(0.06, 0.04, 0.08, bevel=0.01), "emissive", (-0.1, yf - 0.02, BASE + 0.72))

    a.anchor("roof", (0.55, 0.0, cap_z + 0.02))
    return a


def _on_face(face: str, u: float, z: float):
    if face == "front":
        return (u, -D / 2, z), (0, 0, 0)
    if face == "back":
        return (u, D / 2, z), (0, 0, 0)
    if face == "east":
        return (W / 2, u, z), (0, 0, 90)
    return (-W / 2, u, z), (0, 0, 90)


def _push(face: str, loc, amount: float):
    """Moves a point along the outward normal of a face."""
    x, y, z = loc
    return {"front": (x, y - amount, z), "back": (x, y + amount, z), "east": (x + amount, y, z), "west": (x - amount, y, z)}[face]
