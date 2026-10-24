"""Ariane 6 (version Ariane 62, two boosters) on its launch pad: concrete pad and flame
trench, launch table, umbilical mast with two arms (Z up, root at the centre of the pad).

Real launcher (content/v2/sources/safran-space.json, `ariane6-height`, `ariane6-core`):
56 to 62 m high, core stage 5.4 m across, P120C boosters 13.5 m long and 3.4 m across.
Scale 1:13.5 (1 unit = 13.5 m, the scale of the tracking station): long fairing, 62 m =
4.6 units. Stage lengths are rounded (core ≈ 30 m, upper stage ≈ 12 m, fairing ≈ 20 m).
The mast stands on the side away from the default camera (azimuth −35°) so it never hides
the launcher; the anchor `top` is the fairing tip."""

from math import atan2, cos, degrees, radians, sin

from xs.geom import Asset, box, cone, cylinder, grid_slab, lathe, merged, rounded_rect

UNIT = 13.5  # metres per unit
R_CORE = 5.4 / 2 / UNIT
R_ESR = 3.4 / 2 / UNIT
PAD = 2.8
PAD_H = 0.1
TABLE_H = 0.24
POST_H = 0.06
BASE = PAD_H + TABLE_H + POST_H  # bottom of the stages
CORE_L, UPPER_L, FAIRING_L, ESR_L = 30 / UNIT, 12 / UNIT, 20 / UNIT, 19 / UNIT
AWAY_DEG = 55.0  # horizontal direction away from the default camera


def build() -> Asset:
    a = Asset("launcher")
    a.add("pad", grid_slab(rounded_rect(PAD, PAD, 0.12, 3), 0.0, PAD_H, 0.2), "light", smooth=False)
    a.add("trench", box(0.5, PAD - 0.3, 0.006), "graphite", (0, 0, PAD_H + 0.003), smooth=False)
    a.add("trench-rims", merged([(box(0.04, PAD - 0.3, 0.03), (s * 0.27, 0, PAD_H + 0.015), (0, 0, 0)) for s in (-1, 1)]), "mid", smooth=False)

    # Launch table: a frame around the opening the three nozzles hang into.
    x_esr = R_CORE + R_ESR
    hole_x, hole_y, tw, td = 0.9, 0.2, 1.2, 0.7
    frame = [(box(tw, (td - hole_y) / 2, TABLE_H, bevel=0.01), (0, s * (hole_y + td) / 4, PAD_H + TABLE_H / 2), (0, 0, 0)) for s in (-1, 1)]
    frame += [(box((tw - hole_x) / 2, hole_y + 0.002, TABLE_H, bevel=0.01), (s * (hole_x + tw) / 4, 0, PAD_H + TABLE_H / 2), (0, 0, 0)) for s in (-1, 1)]
    a.add("table", merged(frame), "mid")
    posts = [(cylinder(0.03, POST_H, 10), (x, s * 0.13, PAD_H + TABLE_H + POST_H / 2), (0, 0, 0)) for x in (-x_esr, 0, x_esr) for s in (-1, 1)]
    a.add("hold-downs", merged(posts), "graphite")

    # Core stage (Vulcain 2.1 under it), upper stage (Vinci), fairing.
    z = BASE
    a.add("core", cylinder(R_CORE, CORE_L, 40, bevel=0.01), "white", (0, 0, z + CORE_L / 2))
    a.add("core-rings", merged([(cylinder(R_CORE + 0.006, 0.025, 40), (0, 0, z + h), (0, 0, 0)) for h in (0.5, 1.15, 1.8)]), "mid")
    a.add("raceway", box(0.035, 0.03, CORE_L - 0.2, bevel=0.006), "light", (0, -R_CORE - 0.01, z + CORE_L / 2))
    a.add("vulcain", lathe([(0.05, 0.0), (0.06, -0.06), (0.075, -0.13), (0.09, -0.22), (0.093, -0.25), (0.083, -0.25), (0.06, -0.12), (0.04, -0.01)], 32), "metal", (0, 0, z))
    z += CORE_L
    a.add("interstage", cylinder(R_CORE + 0.004, 0.22, 40), "graphite", (0, 0, z + 0.11))
    a.add("upper-stage", cylinder(R_CORE, UPPER_L - 0.22, 40), "white", (0, 0, z + 0.22 + (UPPER_L - 0.22) / 2))
    z += UPPER_L
    a.add("fairing-ring", cylinder(R_CORE + 0.008, 0.03, 40), "mid", (0, 0, z))
    body = FAIRING_L * 0.6
    ogive = [(max(R_CORE * cos(radians(90 * t / 8)) ** 0.7, 0.012), body + FAIRING_L * 0.4 * sin(radians(90 * t / 8))) for t in range(1, 9)]
    a.add("fairing", lathe([(R_CORE, 0.0), (R_CORE, body)] + ogive, 40), "white", (0, 0, z))
    top = z + FAIRING_L

    # Boosters (P120C) on each side, along x.
    for side, s in (("east", 1), ("west", -1)):
        x = s * x_esr
        a.add(f"esr-{side}", cylinder(R_ESR, ESR_L - 0.22, 32, bevel=0.008), "light", (x, 0, BASE + (ESR_L - 0.22) / 2))
        a.add(f"esr-{side}-nose", cone(R_ESR, 0.015, 0.22, 32), "white", (x, 0, BASE + ESR_L - 0.11))
        a.add(f"esr-{side}-band", cylinder(R_ESR + 0.005, 0.03, 32), "graphite", (x, 0, BASE + 0.12))
        a.add(f"esr-{side}-nozzle", lathe([(0.04, 0.0), (0.06, -0.07), (0.075, -0.15), (0.065, -0.15), (0.03, -0.01)], 24), "metal", (x, 0, BASE))

    # Umbilical mast, on the far side, and its two arms reaching the stages.
    d = radians(AWAY_DEG)
    mx, my = 0.82 * cos(d), 0.82 * sin(d)
    side, height = 0.32, 3.9
    a.add("mast-base", box(side + 0.12, side + 0.12, 0.08, bevel=0.01), "mid", (mx, my, PAD_H + 0.04))
    z0 = PAD_H + 0.08
    legs = [(cylinder(0.018, height, 8), (mx + u * side / 2, my + v * side / 2, z0 + height / 2), (0, 0, 0)) for u in (-1, 1) for v in (-1, 1)]
    a.add("mast-legs", merged(legs), "metal", occluder=False)
    rungs = []
    for k in range(1, 13):
        h = z0 + height * k / 13
        rungs += [(box(side, 0.014, 0.014), (mx, my + v * side / 2, h), (0, 0, 0)) for v in (-1, 1)]
        rungs += [(box(0.014, side, 0.014), (mx + u * side / 2, my, h), (0, 0, 0)) for u in (-1, 1)]
    a.add("mast-rungs", merged(rungs), "metal", smooth=False, occluder=False)
    a.add("mast-cap", box(side + 0.06, side + 0.06, 0.05, bevel=0.008), "graphite", (mx, my, z0 + height + 0.025))
    reach = (mx**2 + my**2) ** 0.5 - side / 2 - R_CORE + 0.01
    heading = degrees(atan2(my, mx))
    arms = []
    for h in (BASE + CORE_L * 0.72, BASE + CORE_L + UPPER_L * 0.55):
        r = R_CORE - 0.005 + reach / 2
        arms.append((box(reach, 0.07, 0.05, bevel=0.008), (r * cos(d), r * sin(d), h), (0, 0, heading)))
    a.add("umbilical-arms", merged(arms), "mid")
    a.anchor("top", (0, 0, top))
    return a
