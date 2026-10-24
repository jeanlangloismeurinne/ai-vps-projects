"""Exploded view of the Starlink terminal (the `detail` representation of `terminal`).

Same mount, same pose and same outer size as the envelope (art/assets/terminal.py); the
dish is opened into four layers lifted along its normal:

- cover: the radome, drawn ghosted (radio waves cross it), as on a cut-away illustration;
- tiles: the antenna tiles, a regular grid of square patches at a pitch of λ/2;
- circuit: the board and the beamforming chips that phase each patch;
- chassis: the back shell with its ribs, which stays on the mount.

School representation, stated in content/v2/sources/starlink-home.json (`exploded-model`): the real
terminal has more than a thousand elements, round stacked patches and a different chip
layout; here 24 × 15 patches and 6 × 4 chips. The patch pitch is the one the app's beam
simulation uses (`array` anchor: centre of the patch plane, z along the normal, x along
the rows)."""

from mathutils import Matrix, Vector

from assets.terminal import FACE_D, FACE_W, dish_matrix, mount
from xs.geom import Asset, box, cylinder, merged

# Patch grid: 24 × 15 at a 0.02 pitch fills the 0.5 × 0.32 face with a margin.
COLS, ROWS, PITCH = 24, 15, 0.02
# Half a wavelength apart, the usual rule (Phase 0 fact `element-spacing`): λ = 2 × pitch in
# the model's units, the model being enlarged like the envelope.
SPACING_OVER_LAMBDA = 0.5
PATCH = 0.0115  # side of a patch, ≈ 0.58 of the pitch (Phase 0: 7.2 mm patches at 12.5 mm)
TILES = (4, 3)  # tiles across × along: 6 × 5 patches each
CHIPS = (6, 4)

# Assembled heights along the dish normal (dish frame, metres).
Z_TRAY, Z_RIM = 0.03, 0.06
Z_BOARD = 0.064
Z_CHIP = 0.068
Z_TILE = 0.074
Z_PATCH = 0.0755
Z_COVER = 0.0955

# Offsets of the layers along the normal, exploded.
LIFT = {"chassis": 0.0, "circuit": 0.13, "tiles": 0.26, "cover": 0.4}


def build(tiltDeg: float = 22.0, headingDeg: float = -60.0) -> Asset:
    a = Asset("terminal")
    m = dish_matrix(tiltDeg, headingDeg)
    normal = m.to_3x3() @ Vector((0, 0, 1))
    for name, lift in LIFT.items():
        a.layer(name, tuple(normal * lift))
    mount(a, m, layer="chassis")

    def tilted(bm, loc=(0, 0, 0)):
        bm.transform(m @ Matrix.Translation(Vector(loc)))
        return bm

    # Chassis: a tray with a rim, cross ribs and fixing bosses, a connector on its side.
    a.add("tray", tilted(box(FACE_W, FACE_D, 0.012, bevel=0.006), (0, 0, Z_TRAY + 0.006)), "light", layer="chassis")
    wall, h = 0.01, Z_RIM - Z_TRAY - 0.012
    zc = Z_TRAY + 0.012 + h / 2
    rim = [
        (box(FACE_W, wall, h), (0, (FACE_D - wall) / 2, zc), (0, 0, 0)),
        (box(FACE_W, wall, h), (0, -(FACE_D - wall) / 2, zc), (0, 0, 0)),
        (box(wall, FACE_D - 2 * wall, h), ((FACE_W - wall) / 2, 0, zc), (0, 0, 0)),
        (box(wall, FACE_D - 2 * wall, h), (-(FACE_W - wall) / 2, 0, zc), (0, 0, 0)),
    ]
    a.add("rim", tilted(merged(rim)), "light", layer="chassis")
    rib_h = Z_RIM - Z_TRAY - 0.012
    ribs = [(box(FACE_W - 2 * wall, 0.006, rib_h), (0, y, zc), (0, 0, 0)) for y in (-0.05, 0.05)]
    ribs += [(box(0.006, FACE_D - 2 * wall, rib_h), (x, 0, zc), (0, 0, 0)) for x in (-0.12, 0.0, 0.12)]
    a.add("ribs", tilted(merged(ribs)), "mid", layer="chassis")
    bosses = [(cylinder(0.009, rib_h, 12), (x, y, zc), (0, 0, 0)) for x in (-0.18, 0.18) for y in (-0.1, 0.1)]
    a.add("bosses", tilted(merged(bosses)), "mid", layer="chassis")
    connector = merged([(cylinder(0.012, 0.022, 16, bevel=0.002), (0, -FACE_D / 2 - 0.0105, Z_TRAY + 0.024), (90, 0, 0))])
    a.add("connector", tilted(connector), "graphite", layer="chassis")

    # Circuit: the board on the ribs, the beamforming chips on it, copper buses between.
    bw, bd = FACE_W - 2 * wall - 0.004, FACE_D - 2 * wall - 0.004
    a.add("board", tilted(box(bw, bd, Z_BOARD - Z_RIM, bevel=0.0015), (0, 0, (Z_RIM + Z_BOARD) / 2)), "foliage", layer="circuit")
    cx, cy = CHIPS
    chip_pitch = (bw / cx, bd / cy)
    chip_xy = [(-bw / 2 + chip_pitch[0] * (i + 0.5), -bd / 2 + chip_pitch[1] * (j + 0.5)) for i in range(cx) for j in range(cy)]
    chips = [(box(0.036, 0.036, Z_CHIP - Z_BOARD, bevel=0.001), (x, y, (Z_BOARD + Z_CHIP) / 2), (0, 0, 0)) for x, y in chip_xy]
    a.add("chips", tilted(merged(chips)), "graphite", layer="circuit")
    lids = [(box(0.02, 0.02, 0.0008), (x, y, Z_CHIP + 0.0004), (0, 0, 0)) for x, y in chip_xy]
    a.add("chip-lids", tilted(merged(lids)), "metal", layer="circuit")
    buses = [(box(bw - 0.03, 0.003, 0.0006), (0, y, Z_BOARD + 0.0003), (0, 0, 0)) for y in {round(y, 6) for _, y in chip_xy}]
    buses += [(box(0.003, bd - 0.03, 0.0006), (x, 0, Z_BOARD + 0.0003), (0, 0, 0)) for x in sorted({round(x, 6) for x, _ in chip_xy})]
    a.add("buses", tilted(merged(buses)), "warm", layer="circuit", occluder=False)

    # Tiles: substrate slabs on the chips, the patches on them at the array pitch.
    tx, ty = TILES
    tw, td = COLS * PITCH / tx, ROWS * PITCH / ty
    tiles = [(box(tw - 0.002, td - 0.002, Z_TILE - Z_CHIP, bevel=0.0012), (-COLS * PITCH / 2 + tw * (i + 0.5), -ROWS * PITCH / 2 + td * (j + 0.5), (Z_CHIP + Z_TILE) / 2), (0, 0, 0)) for i in range(tx) for j in range(ty)]
    a.add("tiles", tilted(merged(tiles)), "light", layer="tiles")
    patches = [(box(PATCH, PATCH, Z_PATCH - Z_TILE), (-COLS * PITCH / 2 + PITCH * (i + 0.5), -ROWS * PITCH / 2 + PITCH * (j + 0.5), (Z_TILE + Z_PATCH) / 2), (0, 0, 0)) for i in range(COLS) for j in range(ROWS)]
    a.add("patches", tilted(merged(patches)), "warm", layer="tiles", occluder=False)

    # Cover: the radome, ghosted, resting on the patches when assembled.
    a.add("cover", tilted(box(FACE_W, FACE_D, Z_COVER - Z_PATCH, bevel=0.008, segments=3), (0, 0, (Z_PATCH + Z_COVER) / 2)), "ghost", layer="cover", occluder=False)

    # The grid the app's beam is computed on: columns along the anchor's x, rows along its y.
    a.info["array"] = {"columns": COLS, "rows": ROWS, "pitch": PITCH, "spacingOverLambda": SPACING_OVER_LAMBDA}
    frame = m.to_3x3()
    a.anchor("array", tuple(m @ Vector((0, 0, Z_PATCH))), frame, layer="tiles")
    a.anchor("beam", tuple(m @ Vector((0, 0, Z_COVER + 0.015))), layer="cover")
    return a
