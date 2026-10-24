"""A Starlink gateway (ground station): parabolic antennas under white spherical radomes on
a fenced gravel pad, an equipment shelter and the fibre handhole (Z up, root at the centre
of the pad, front = −y).

Real hardware (content/v2/sources/starlink-home.json, `gateway-radome`): spherical radome 2.1 m across
over a ≈ 1.4 m Ka-band dish, concrete base 1.85 m; a Community Gateway has four antennas.
Here the radome is 0.7 unit across (≈ 1:3, the house scale). One radome is cut open on the
camera side so its dish shows (validated 2026-10-21); the anchor `dish` is at its feed, the
anchor `fibre` on the handhole lid."""

from math import atan2, radians

import bmesh
from mathutils import Euler, Matrix, Vector

from xs.geom import Asset, box, cylinder, grid_slab, merged, rounded_rect, sphere
from xs.parts import dish, fibre_handhole, struts

PAD_X, PAD_Y = 3.2, 2.6
R_DOME = 0.35
BASE_H, SKIRT_H = 0.07, 0.1
DOME_Z = BASE_H + SKIRT_H  # where the dome meets its skirt
CUT = -0.25  # the sphere is cut 0.25 R below its equator
CAMERA_SIDE_DEG = -125.0  # horizontal direction toward the default camera (azimuth −35°)


def build(radomes: int = 4, open: int = 1, aimDeg: tuple = (146.0, 22.0)) -> Asset:
    a = Asset("ground-station")
    a.add("pad", grid_slab(rounded_rect(PAD_X, PAD_Y, 0.04, 2), 0.0, 0.05, 0.2), "light")
    a.add("kerb", merged([(box(PAD_X + 0.12, 0.06, 0.07), (0, s * (PAD_Y / 2 + 0.03), 0.035), (0, 0, 0)) for s in (-1, 1)] + [(box(0.06, PAD_Y, 0.07), (s * (PAD_X / 2 + 0.03), 0, 0.035), (0, 0, 0)) for s in (-1, 1)]), "mid", smooth=False)

    spots = [(-0.95, -0.4), (-0.05, -0.4), (-0.95, 0.5), (-0.05, 0.5)][:radomes]
    z0 = 0.05
    a.add("radome-bases", merged([(box(0.58, 0.58, BASE_H, bevel=0.012), (x, y, z0 + BASE_H / 2), (0, 0, 0)) for x, y in spots]), "mid")
    a.add("radome-skirts", merged([(cylinder(R_DOME * 0.97, SKIRT_H, 32, bevel=0.01), (x, y, z0 + BASE_H + SKIRT_H / 2), (0, 0, 0)) for x, y in spots]), "white")
    domes = [(_dome(R_DOME, opened=i < open), (x, y, z0 + DOME_Z - R_DOME * CUT), (0, 0, 0)) for i, (x, y) in enumerate(spots)]
    a.add("radomes", merged(domes), "white", open_surface=False)

    # The dish inside the open radome, aimed at the satellite (heading, tilt from vertical).
    ox, oy = spots[0]
    heading, tilt = aimDeg
    pivot = Vector((ox, oy, z0 + DOME_Z + 0.12))
    m = Matrix.Translation(pivot) @ Euler((0, 0, radians(heading))).to_matrix().to_4x4() @ Euler((0, radians(tilt), 0)).to_matrix().to_4x4()

    def aimed(bm, loc=(0, 0, 0)):
        bm.transform(m @ Matrix.Translation(Vector(loc)))
        return bm

    a.add("pedestal", cylinder(0.06, pivot.z - z0 - DOME_Z + 0.02, 16, bevel=0.01), "mid", (ox, oy, (pivot.z + z0 + DOME_Z) / 2 - 0.01))
    a.add("yoke", aimed(box(0.16, 0.08, 0.06, bevel=0.01)), "graphite")
    f = 0.16
    focus = 0.04 + f
    a.add("dish", aimed(dish(f, 0.24), (0, 0, 0.04)), "white")
    a.add("feed-struts", aimed(struts(f, 0.15, 0.04, focus)), "metal", occluder=False)
    a.add("feed-horn", aimed(cylinder(0.025, 0.05, 12, bevel=0.005), (0, 0, focus)), "graphite")

    # Equipment shelter on the east side.
    sx = 1.05
    a.add("shelter", box(0.9, 1.3, 0.62, bevel=0.02), "white", (sx, 0.2, z0 + 0.31))
    a.add("shelter-roof", box(0.98, 1.38, 0.05, bevel=0.012), "mid", (sx, 0.2, z0 + 0.645))
    a.add("shelter-door", box(0.28, 0.03, 0.48, bevel=0.008), "graphite", (sx - 0.15, 0.2 - 0.66, z0 + 0.25))
    a.add("hvac", merged([(box(0.26, 0.14, 0.22, bevel=0.012), (sx + 0.2, -0.515, z0 + 0.15), (0, 0, 0))]), "light")
    a.add("hvac-fan", cylinder(0.08, 0.02, 20), "graphite", (sx + 0.2, -0.59, z0 + 0.16), (90, 0, 0))
    # Cable tray from the radomes to the shelter.
    a.add("cable-tray", merged([(box(1.05, 0.08, 0.04), (-0.5, 0.05, z0 + 0.02), (0, 0, 0)), (box(0.08, 0.9, 0.04), (-0.5, 0.05, z0 + 0.02), (0, 0, 0))]), "graphite", smooth=False)

    # Fence: posts and two rails, with a gate gap on the front framed by two gate posts
    # (every rail end rests on a post).
    posts, rails = [], []
    fx, fy = PAD_X / 2 - 0.08, PAD_Y / 2 - 0.08
    gap0, gap1 = 0.45 - 0.2, 0.45 + 0.2
    for i in range(9):
        x = -fx + 2 * fx * i / 8
        posts += [(cylinder(0.015, 0.42, 6), (x, fy, z0 + 0.21), (0, 0, 0))]
        if not gap0 - 0.12 < x < gap1 + 0.12:
            posts += [(cylinder(0.015, 0.42, 6), (x, -fy, z0 + 0.21), (0, 0, 0))]
    posts += [(cylinder(0.02, 0.46, 8), (x, -fy, z0 + 0.23), (0, 0, 0)) for x in (gap0, gap1)]
    for j in range(1, 7):
        y = -fy + 2 * fy * j / 7
        posts += [(cylinder(0.015, 0.42, 6), (s * fx, y, z0 + 0.21), (0, 0, 0)) for s in (-1, 1)]
    for z in (0.2, 0.4):
        rails += [(box(2 * fx, 0.012, 0.012), (0, fy, z0 + z), (0, 0, 0))]
        rails += [(box(0.012, 2 * fy, 0.012), (s * fx, 0, z0 + z), (0, 0, 0)) for s in (-1, 1)]
        rails += [(box(gap0 + fx, 0.012, 0.012), ((-fx + gap0) / 2, -fy, z0 + z), (0, 0, 0)), (box(fx - gap1, 0.012, 0.012), ((fx + gap1) / 2, -fy, z0 + z), (0, 0, 0))]
    a.add("fence-posts", merged(posts), "metal", smooth=False, occluder=False)
    a.add("fence-rails", merged(rails), "metal", smooth=False, occluder=False)

    # Fibre handhole and its marker, outside the fence toward the road.
    fibre = fibre_handhole(a, 1.3, -PAD_Y / 2 - 0.25)
    a.anchor("dish", tuple(m @ Vector((0, 0, focus))))
    a.anchor("fibre", fibre)
    return a


def _dome(r: float, opened: bool) -> bmesh.types.BMesh:
    """A sphere cut below its equator, bottom filled; `opened`: a window is cut on the camera
    side and the shell is given a thickness so it stays closed."""
    bm = sphere(r, 40, 20)
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), plane_co=(0, 0, CUT * r), plane_no=(0, 0, 1), clear_inner=True)
    if not opened:
        bmesh.ops.holes_fill(bm, edges=bm.edges, sides=0)
        return bm
    side = radians(CAMERA_SIDE_DEG)
    doomed = []
    for f in bm.faces:
        c = f.calc_center_median()
        az = atan2(c.y, c.x)
        d = abs((az - side + 3.14159) % 6.28318 - 3.14159)
        if d < radians(75) and CUT * r + 0.01 < c.z < 0.86 * r:
            doomed.append(f)
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    bmesh.ops.solidify(bm, geom=list(bm.faces), thickness=0.012)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    return bm
