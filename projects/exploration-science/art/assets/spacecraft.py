"""Satellites built from shared parts (xs.parts: solar wings, dishes), in two variants
(Z up, root at the centre of the bus, the Earth toward −z):

- `telecom`: a geostationary telecommunications satellite with all-electric propulsion.
  Gold-blanketed bus, radiators on the ±y faces, two deployed reflectors, two solar wings
  along y, and two Hall-effect plasma thrusters (PPS 5000 type) on the anti-Earth face,
  their xenon plumes drawn as glowing tapered jets (a reading aid: the real beam widens,
  40° divergence, `pps5000-specs`).
  Anchors: `antenna` (telemetry and telecommand horn), `base` (Earth deck).
  Its `detail` representation (`detail=True`) is the same satellite with the west thruster
  exploded along its axis into five layers, after the parts a Safran (Snecma) Hall thruster
  patent lists (`pps-exploded-model`): the magnetic circuit (yoke, central core, peripheral
  bars and their coils), the anode and its xenon pipe, the ceramic channel, the poles, the
  hollow cathode. No plume on the opened thruster.
- `observation`: an Earth-observation satellite. Compact bus, one solar wing, the optical
  instrument beside the bus: a telescope tube cut open on the camera side so its primary
  mirror (Safran Reosc type) and secondary mirror show, and an X-band antenna that sends
  the images down. Anchor: `transmitter`.

Satellites are drawn at about 1:5, a larger scale than the ground (1:13.5), and their
solar wings are shortened (diorama convention, as for the Starlink satellite)."""

from math import atan2, cos, radians, sin

import bmesh
from mathutils import Matrix, Vector

from xs.geom import Asset, box, cone, cylinder, lathe, merged
from xs.parts import dish, solar_wing, struts

CAMERA_SIDE_DEG = -125.0  # horizontal direction toward the default camera (azimuth −35°)
WINDOW_DEG = 42.0  # half-width of the telescope's window, around CAMERA_SIDE_DEG


# Exploded thruster: offsets of its layers along its axis; the cathode also moves outward.
PPS_LIFT = {"magnets": 0.0, "anode": 0.07, "channel": 0.12, "poles": 0.18, "cathode": 0.27}
CATHODE_OUT = 0.02


def build(kind: str = "telecom", id: str | None = None, detail: bool = False) -> Asset:
    if kind == "telecom":
        return _telecom(id or "telecom-satellite", detail)
    if kind == "observation":
        return _observation(id or "observation-satellite")
    raise ValueError(f"unknown spacecraft kind: {kind}")


def _oriented(bm, centre, axis: Vector):
    """Turns a shape built along +z so that +z points along `axis`, then moves it to `centre`."""
    bm.transform(Matrix.Translation(Vector(centre)) @ Vector((0, 0, 1)).rotation_difference(axis.normalized()).to_matrix().to_4x4())
    return bm


def _telecom(aid: str, detail: bool = False) -> Asset:
    a = Asset(aid, airborne=True)
    bx, by, bz = 0.55, 0.55, 0.75
    a.add("bus", box(bx, by, bz, bevel=0.015), "warm")
    a.add("radiators", merged([(box(bx - 0.06, 0.012, bz - 0.12, bevel=0.003), (0, s * (by / 2 + 0.006), 0), (0, 0, 0)) for s in (-1, 1)]), "white")
    a.add("earth-deck", box(bx - 0.04, by - 0.04, 0.03, bevel=0.006), "light", (0, 0, -bz / 2 - 0.015))
    a.add("top-deck", box(bx - 0.04, by - 0.04, 0.02, bevel=0.005), "light", (0, 0, bz / 2 + 0.01))

    # Two deployed reflectors facing their feed horns on the Earth deck.
    zd = -bz / 2 - 0.03
    for side, s in (("east", 1), ("west", -1)):
        vertex = Vector((s * 0.58, 0, -0.05))
        feed = Vector((s * 0.17, 0, zd - 0.06))
        axis = feed - vertex
        a.add(f"reflector-{side}", _oriented(dish(0.32, 0.27, segments=40), vertex, axis), "white")
        back = vertex - axis.normalized() * 0.018
        arm = s * (back.x - s * bx / 2)
        a.add(f"reflector-{side}-arm", box(abs(arm) + 0.02, 0.04, 0.04, bevel=0.006), "metal", ((back.x + s * bx / 2) / 2, 0, back.z))
        a.add(f"feed-{side}", _oriented(cone(0.035, 0.055, 0.07, 16), (s * 0.17, 0, zd - 0.035), axis), "graphite")
    a.add("ttc-horn", cone(0.03, 0.045, 0.06, 16), "graphite", (0, 0, zd - 0.03), (180, 0, 0))

    # Solar wings along y, on yokes from the radiator faces.
    for side, s in (("north", 1), ("south", -1)):
        a.add(f"wing-{side}-yoke", cylinder(0.016, 0.24, 10), "metal", (0, s * (by / 2 + 0.012 + 0.12), 0), (90, 0, 0))
        solar_wing(a, f"wing-{side}", 0.9, 0.42, (6, 3), (0, s * (by / 2 + 0.012 + 0.24 + 0.45), 0), along="y")

    # Plasma thrusters on the anti-Earth face, canted outward, and their plumes.
    zt = bz / 2 + 0.02
    for side, s in (("east", 1), ("west", -1)):
        axis = Vector((s * 0.35, -0.2, 1.0)).normalized()
        base = Vector((s * 0.16, -0.12, zt))
        a.add(f"pps-{side}-bracket", box(0.17, 0.17, 0.04, bevel=0.008), "mid", tuple(base + Vector((0, 0, 0.02))))
        origin = base + Vector((0, 0, 0.03))
        opened = detail and side == "west"
        _pps(a, f"pps-{side}", origin, axis, opened)
        if not opened:
            a.add(f"pps-{side}-plume", _oriented(cone(0.044, 0.008, 0.3, 24), origin + axis * (0.08 + 0.15), axis), "emissive")

    a.add("omni", cylinder(0.008, 0.16, 8), "metal", (0.2, 0.2, zt + 0.08))
    a.anchor("antenna", (0, 0, zd - 0.06))
    a.anchor("base", (0, 0, -bz / 2 - 0.03))
    return a


def _pps(a: Asset, name: str, origin: Vector, axis: Vector, opened: bool) -> None:
    """A Hall-effect thruster built along +z from its back (z = 0) to its outlet (z ≈ 0.08),
    then turned along `axis` at `origin`. Opened: its parts go in the exploded layers."""
    turn = Vector((0, 0, 1)).rotation_difference(axis).to_matrix().to_4x4()
    m = Matrix.Translation(origin) @ turn
    # The cathode stands on the far side from the camera: opened, it rises above the poles.
    back = radians(CAMERA_SIDE_DEG + 180)
    u = Vector((cos(back), sin(back), 0))
    u = (u - axis * u.dot(axis)).normalized()
    if opened:
        for layer, lift in PPS_LIFT.items():
            a.layer(layer, tuple(axis * lift + (u * CATHODE_OUT if layer == "cathode" else Vector())))
    local = turn.inverted().to_3x3() @ u

    def put(part, bm, material, layer, loc=(0, 0, 0), **kw):
        bm.transform(m @ Matrix.Translation(Vector(loc)))
        a.add(f"{name}-{part}", bm, material, layer=layer if opened else None, **kw)

    def ring(r0, r1, z0, z1, segments=40):
        return lathe([(r1, z0), (r1, z1), (r0, z1), (r0, z0), (r1, z0)], segments)

    R = 0.075
    # Magnetic circuit: yoke, central core and inner coil, four peripheral bars and coils.
    put("yoke", cylinder(R, 0.012, 40, bevel=0.003), "mid", "magnets", (0, 0, 0.006))
    put("core", cylinder(0.011, 0.062, 16), "metal", "magnets", (0, 0, 0.043))
    put("inner-coil", cylinder(0.019, 0.04, 24, bevel=0.003), "warm", "magnets", (0, 0, 0.032))
    spots = [Vector((cos(radians(45 + 90 * k)), sin(radians(45 + 90 * k)), 0)) * 0.063 for k in range(4)]
    put("bars", merged([(cylinder(0.006, 0.058, 10), (p.x, p.y, 0.041), (0, 0, 0)) for p in spots]), "metal", "magnets")
    put("outer-coils", merged([(cylinder(0.012, 0.044, 16, bevel=0.003), (p.x, p.y, 0.038), (0, 0, 0)) for p in spots]), "warm", "magnets")
    # Anode (gas distributor) at the bottom of the channel, its xenon pipe through the yoke.
    put("anode", ring(0.031, 0.043, 0.036, 0.042), "metal", "anode")
    put("xenon-pipe", cylinder(0.0035, 0.036, 8), "metal", "anode", (0.037 * local.x, 0.037 * local.y, 0.018))
    # Ceramic discharge channel: an annular cup open toward the outlet.
    put("channel", lathe([(0.05, 0.028), (0.05, 0.08), (0.046, 0.08), (0.046, 0.034), (0.028, 0.034), (0.028, 0.08), (0.024, 0.08), (0.024, 0.028), (0.05, 0.028)], 40), "white", "channel")
    # Poles: the outer ring on the bars, the inner disc on the core.
    put("outer-pole", ring(0.052, R, 0.07, 0.08), "mid", "poles")
    put("inner-pole", cylinder(0.023, 0.008, 24, bevel=0.002), "mid", "poles", (0, 0, 0.078))
    # Hollow cathode beside the outlet, on an arm from the outer pole, leaning to the jet.
    c = local * 0.1 + Vector((0, 0, 0.1))
    lean = Matrix.Rotation(radians(-25), 4, Vector((-local.y, local.x, 0)))
    arm = box(0.04, 0.012, 0.01)
    arm.transform(Matrix.Translation(local * 0.088 + Vector((0, 0, 0.075))) @ Matrix.Rotation(atan2(local.y, local.x), 4, "Z"))
    put("cathode-arm", arm, "mid", "cathode")
    bm = cylinder(0.011, 0.06, 16, bevel=0.003)
    bm.transform(Matrix.Translation(c) @ lean)
    put("cathode", bm, "graphite", "cathode")
    tip = cone(0.011, 0.006, 0.012, 16)
    tip.transform(Matrix.Translation(c) @ lean @ Matrix.Translation((0, 0, 0.036)))
    put("cathode-tip", tip, "metal", "cathode")


def _observation(aid: str) -> Asset:
    a = Asset(aid, airborne=True)
    bx, by, bz = 0.45, 0.45, 0.42
    a.add("bus", box(bx, by, bz, bevel=0.015), "white")
    panels = [(box(0.012, by - 0.08, bz - 0.1, bevel=0.003), (-bx / 2 - 0.006, 0, 0), (0, 0, 0))]
    panels += [(box(bx - 0.08, 0.012, bz - 0.1, bevel=0.003), (0, s * (by / 2 + 0.006), 0), (0, 0, 0)) for s in (-1, 1)]
    a.add("side-panels", merged(panels), "light")
    a.add("star-trackers", merged([(box(0.06, 0.06, 0.07, bevel=0.006), (x, -0.12, bz / 2 + 0.035), (0, 0, 0)) for x in (-0.12, 0.02)]), "graphite")

    # The telescope beside the bus (+x), looking down at the Earth.
    r, z_bot, z_top = 0.17, -0.36, 0.22
    tx = bx / 2 + r
    a.add("telescope", _tube(r, z_bot, z_top), "white", (tx, 0, 0))
    # Dark liner on the far wall: what the window shows behind the mirrors.
    a.add("telescope-liner", _liner(r - 0.03, z_bot + 0.03, z_top - 0.002), "graphite", (tx, 0, 0))
    a.add("mirror-cell", cylinder(r, 0.03, 40, bevel=0.006), "mid", (tx, 0, z_top + 0.015 - 0.002))
    a.add("primary-mirror", dish(0.45, r - 0.02, segments=40), "metal", (tx, 0, z_top - 0.002 - 0.018), (180, 0, 0))
    zs = z_bot + 0.14
    a.add("secondary-mirror", lathe([(0.045, 0.0), (0.03, 0.01), (0.012, 0.014), (0.012, -0.012), (0.045, -0.008)], 24), "metal", (tx, 0, zs))
    # Three spider arms, none in the window.
    arms = []
    for k in (CAMERA_SIDE_DEG + 60, CAMERA_SIDE_DEG + 180, CAMERA_SIDE_DEG + 300):
        u = Vector((cos(radians(k)), sin(radians(k)), 0))
        arms.append((box(r, 0.01, 0.01), (tx + u.x * r / 2, u.y * r / 2, zs - 0.01), (0, 0, k)))
    a.add("spider", merged(arms), "metal", occluder=False)
    a.add("baffle-ring", lathe([(r + 0.012, 0.0), (r + 0.012, 0.03), (r - 0.004, 0.03), (r - 0.004, 0.0)], 40), "white", (tx, 0, z_bot))
    a.add("telescope-mount", box(0.06, 0.2, 0.2, bevel=0.008), "mid", (bx / 2 + 0.01, 0, 0.02))

    # One solar wing on the west side.
    a.add("wing-yoke", cylinder(0.016, 0.16, 10), "metal", (-bx / 2 - 0.012 - 0.08, 0, 0.05), (0, 90, 0))
    solar_wing(a, "wing", 1.0, 0.42, (7, 3), (-bx / 2 - 0.012 - 0.16 - 0.5, 0, 0.05), along="x")

    # X-band antenna under the bus, toward the station: built pointing up from the bus
    # bottom, then every part turned over about that point.
    zb, fx, vx = -bz / 2, 0.06, 0.078
    at, over = (-0.08, 0.08, zb), (180, 0, 0)
    a.add("xband-mast", _up(cylinder(0.014, 0.08, 10), 0.04), "metal", at, over)
    a.add("xband-dish", _up(dish(fx, 0.075, inner=0.012, rim=0.004, drop=0.005, thickness=0.01, segments=24), vx), "white", at, over)
    a.add("xband-struts", struts(fx, 0.045, vx, vx + fx, radius=0.003), "metal", at, over, occluder=False)
    a.add("xband-feed", _up(cylinder(0.012, 0.03, 10), vx + fx), "graphite", at, over)
    a.anchor("transmitter", (-0.08, 0.08, zb - vx - fx))
    return a


def _up(bm, z: float):
    bmesh.ops.translate(bm, vec=Vector((0, 0, z)), verts=bm.verts)
    return bm


def _liner(r: float, z0: float, z1: float) -> bmesh.types.BMesh:
    """A half tube facing the window from the far side of the telescope."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, cap_tris=False, segments=40, radius1=r, radius2=r, depth=z1 - z0)
    bmesh.ops.translate(bm, vec=Vector((0, 0, (z0 + z1) / 2)), verts=bm.verts)
    far = radians(CAMERA_SIDE_DEG + 180)
    doomed = [f for f in bm.faces if abs((atan2(f.calc_center_median().y, f.calc_center_median().x) - far + 3.14159) % 6.28318 - 3.14159) > radians(95)]
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    bmesh.ops.solidify(bm, geom=list(bm.faces), thickness=0.01)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    return bm


def _tube(r: float, z0: float, z1: float) -> bmesh.types.BMesh:
    """An open tube cut with a window on the camera side, given a wall thickness."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, cap_tris=False, segments=40, radius1=r, radius2=r, depth=z1 - z0)
    bmesh.ops.translate(bm, vec=Vector((0, 0, (z0 + z1) / 2)), verts=bm.verts)
    bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 1e-6], cuts=7, use_grid_fill=False)
    side = radians(CAMERA_SIDE_DEG)
    doomed = []
    for f in bm.faces:
        c = f.calc_center_median()
        d = abs((atan2(c.y, c.x) - side + 3.14159) % 6.28318 - 3.14159)
        if d < radians(WINDOW_DEG) and z0 + 0.1 < c.z < z1 - 0.05:
            doomed.append(f)
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    bmesh.ops.solidify(bm, geom=list(bm.faces), thickness=0.012)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    return bm
