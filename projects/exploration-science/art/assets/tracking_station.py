"""A satellite tracking station of Safran Data Systems: a large tracking antenna (ORION
class, Cassegrain: sub-reflector on four struts) on its concrete tower, a compact antenna
(LEGION class, feed on a tripod), the operations building and the fibre handhole (Z up,
root at the centre of the pad, front = −y).

Real hardware (content/v2/sources/safran-space.json, `sds-antenna-sizes`): antennas from
2.4 to 13.5 m, ORION 7.3 to 13.5 m, LEGION about 4 m. Scale 1:13.5 like the launcher: the
large dish is 13.5 m (1 unit), the compact one 4 m. Each antenna is aimed at its satellite
(`aimDeg`, `smallAimDeg`: heading, tilt from vertical); anchors `dish` and `dish-small` at
their feeds, `fibre` on the handhole lid. Dishes, struts and handhole come from xs.parts,
shared with the Starlink gateway."""

from math import atan2, radians

from mathutils import Euler, Matrix, Vector

from xs.geom import Asset, box, cone, cylinder, grid_slab, lathe, merged, rounded_rect
from xs.parts import dish, fibre_handhole, struts

PAD_X, PAD_Y = 3.4, 2.8
Z0 = 0.05  # top of the pad


def _aim(pivot: Vector, heading: float, tilt: float | None = None) -> Matrix:
    m = Matrix.Translation(pivot) @ Euler((0, 0, radians(heading))).to_matrix().to_4x4()
    return m if tilt is None else m @ Euler((0, radians(tilt), 0)).to_matrix().to_4x4()


def _placed(m: Matrix, bm, loc=(0, 0, 0), rot=(0, 0, 0)):
    bm.transform(m @ Matrix.Translation(Vector(loc)) @ Euler(tuple(radians(r) for r in rot)).to_matrix().to_4x4())
    return bm


def build(aimDeg: tuple = (114.4, 22.8), smallAimDeg: tuple = (165.9, 44.2)) -> Asset:
    a = Asset("tracking-station")
    a.add("pad", grid_slab(rounded_rect(PAD_X, PAD_Y, 0.04, 2), 0.0, Z0, 0.2), "light")
    kerb = [(box(PAD_X + 0.12, 0.06, 0.07), (0, s * (PAD_Y / 2 + 0.03), 0.035), (0, 0, 0)) for s in (-1, 1)]
    kerb += [(box(0.06, PAD_Y, 0.07), (s * (PAD_X / 2 + 0.03), 0, 0.035), (0, 0, 0)) for s in (-1, 1)]
    a.add("kerb", merged(kerb), "mid", smooth=False)

    # Large antenna: tower, turntable, yoke (turns in azimuth), elevation axle and dish.
    ox, oy = -0.75, 0.25
    a.add("tower", cylinder(0.26, 0.57, 40, bevel=0.015), "white", (ox, oy, Z0 + 0.285))
    a.add("tower-door", box(0.12, 0.03, 0.24, bevel=0.006), "graphite", (ox - 0.12, oy - 0.235, Z0 + 0.13), (0, 0, -30))
    a.add("tower-band", cylinder(0.265, 0.03, 40), "mid", (ox, oy, Z0 + 0.5))
    a.add("turntable", cylinder(0.3, 0.06, 40, bevel=0.01), "mid", (ox, oy, Z0 + 0.6))
    pivot = Vector((ox, oy, Z0 + 0.81))
    heading, tilt = aimDeg
    yoke = _aim(pivot, heading)
    a.add("yoke-arms", merged([(_placed(yoke, box(0.05, 0.05, 0.2, bevel=0.008), (0, s * 0.22, -0.08)), (0, 0, 0), (0, 0, 0)) for s in (-1, 1)]), "mid")
    a.add("cabin", _placed(yoke, box(0.3, 0.36, 0.1, bevel=0.01), (0, 0, -0.13)), "white")
    m = _aim(pivot, heading, tilt)
    f, r, vertex = 0.35, 0.5, 0.13
    a.add("axle", _placed(m, cylinder(0.04, 0.49, 20, bevel=0.006), rot=(90, 0, 0)), "graphite")
    a.add("hub", _placed(m, cylinder(0.09, 0.11, 24, bevel=0.008), (0, 0, 0.055)), "mid")
    a.add("dish", _placed(m, dish(f, r, inner=0.04, steps=10, rim=0.01, drop=0.012, thickness=0.02, segments=56), (0, 0, vertex)), "white")
    ribs = []
    for k in range(8):
        r0, r1 = 0.09, 0.47
        z_0, z_1 = vertex - 0.02 + r0**2 / (4 * f) - 0.03, vertex - 0.02 + r1**2 / (4 * f) - 0.03
        length = ((r1 - r0) ** 2 + (z_1 - z_0) ** 2) ** 0.5
        pitch = atan2(z_1 - z_0, r1 - r0)
        rib = box(length, 0.016, 0.03)
        rib.transform(Euler((0, 0, radians(45 * k))).to_matrix().to_4x4() @ Matrix.Translation(((r0 + r1) / 2, 0, (z_0 + z_1) / 2)) @ Euler((0, -pitch, 0)).to_matrix().to_4x4())
        ribs.append((rib, (0, 0, 0), (0, 0, 0)))
    a.add("back-ribs", _placed(m, merged(ribs)), "metal", occluder=False)
    sub = vertex + 0.3
    a.add("quadripod", _placed(m, struts(f, 0.36, vertex, sub, count=4, radius=0.008, start_deg=45)), "metal", occluder=False)
    a.add("subreflector", _placed(m, lathe([(0.065, 0.0), (0.05, 0.012), (0.03, 0.02), (0.012, 0.024), (0.012, -0.012), (0.065, -0.008)], 32), (0, 0, sub)), "white")
    a.add("feed-cone", _placed(m, cone(0.05, 0.03, 0.12, 24), (0, 0, vertex + 0.05)), "graphite")

    # Compact antenna: column, head, dish with its feed on a tripod.
    sx, sy = 1.05, 0.7
    a.add("small-column", cylinder(0.05, 0.31, 20, bevel=0.008), "mid", (sx, sy, Z0 + 0.155))
    a.add("small-base", box(0.22, 0.22, 0.04, bevel=0.008), "mid", (sx, sy, Z0 + 0.02))
    spivot = Vector((sx, sy, Z0 + 0.37))
    sh, st = smallAimDeg
    sm = _aim(spivot, sh, st)
    a.add("small-head", _placed(_aim(spivot, sh), box(0.12, 0.1, 0.1, bevel=0.01), (0, 0, -0.04)), "graphite")
    fs = 0.12
    a.add("small-dish", _placed(sm, dish(fs, 0.15), (0, 0, 0.03)), "white")
    a.add("small-struts", _placed(sm, struts(fs, 0.1, 0.03, 0.03 + fs)), "metal", occluder=False)
    a.add("small-feed", _placed(sm, cylinder(0.02, 0.04, 12, bevel=0.004), (0, 0, 0.03 + fs)), "graphite")

    # Operations building, south-east.
    bx, by = 0.75, -0.65
    a.add("building", box(1.1, 0.7, 0.42, bevel=0.02), "white", (bx, by, Z0 + 0.21))
    a.add("building-roof", box(1.18, 0.78, 0.05, bevel=0.012), "mid", (bx, by, Z0 + 0.445))
    a.add("building-door", box(0.2, 0.03, 0.32, bevel=0.008), "graphite", (bx - 0.3, by - 0.355, Z0 + 0.17))
    a.add("building-windows", merged([(box(0.16, 0.03, 0.12, bevel=0.006), (bx + x, by - 0.355, Z0 + 0.26), (0, 0, 0)) for x in (-0.02, 0.2, 0.42)]), "graphite")
    a.add("hvac", box(0.24, 0.2, 0.12, bevel=0.012), "light", (bx + 0.3, by + 0.1, Z0 + 0.53))
    a.add("hvac-fan", cylinder(0.07, 0.02, 20), "graphite", (bx + 0.3, by + 0.1, Z0 + 0.6))
    # Cable tray from the antennas to the building.
    a.add("cable-tray", merged([(box(0.08, 1.0, 0.04), (0.2, -0.05, Z0 + 0.02), (0, 0, 0)), (box(1.0, 0.08, 0.04), (-0.3, 0.45, Z0 + 0.02), (0, 0, 0)), (box(0.85, 0.08, 0.04), (0.62, 0.45, Z0 + 0.02), (0, 0, 0))]), "graphite", smooth=False)

    fibre = fibre_handhole(a, 1.45, -PAD_Y / 2 - 0.25)
    a.anchor("dish", tuple(m @ Vector((0, 0, sub))))
    a.anchor("dish-small", tuple(sm @ Vector((0, 0, 0.03 + fs))))
    a.anchor("fibre", fibre)
    return a
