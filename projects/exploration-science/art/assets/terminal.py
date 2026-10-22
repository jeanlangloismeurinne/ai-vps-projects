"""The Starlink Standard terminal on a roof-ridge pipe mount (Z up, root on the ridge cap).

Real antenna: 594 × 383 × 39.7 mm (content/v2/sources.json, `dish-dimensions`). Here
0.5 × 0.32 units: the same aspect ratio, enlarged ≈ ×2.8 against the house so it stays
legible in the global view (diorama convention, stated in the sources). The face is tilted
toward the satellite: `tiltDeg` from the vertical, toward the local heading `headingDeg`."""

from math import radians

from mathutils import Euler, Matrix, Vector

from xs.geom import Asset, box, cylinder, merged

FACE_W, FACE_D, FACE_T = 0.5, 0.32, 0.034
MAST_TOP = 0.34


def dish_matrix(tiltDeg: float, headingDeg: float) -> Matrix:
    """The dish frame: origin on the pivot above the clamp, z along the face normal."""
    return Matrix.Translation(Vector((0, 0, MAST_TOP + 0.02))) @ (
        Euler((0, 0, radians(headingDeg))).to_matrix().to_4x4() @ Euler((0, radians(tiltDeg), 0)).to_matrix().to_4x4()
    )


def mount(a: Asset, m: Matrix, layer: str | None = None) -> None:
    """Roof saddle, mast, clamp, cable and the adapter under the dish: shared by the
    envelope and the exploded view, which keeps them in place (`layer`, no offset)."""
    a.add("saddle", box(0.2, 0.16, 0.035, bevel=0.008), "graphite", (0, 0, 0.0175), layer=layer)
    a.add("straps", merged([(box(0.025, 0.2, 0.012), (x, 0, 0.006), (0, 0, 0)) for x in (-0.07, 0.07)]), "metal", layer=layer)
    a.add("mast-foot", cylinder(0.03, 0.05, 16, bevel=0.006), "metal", (0, 0, 0.06), layer=layer)
    a.add("mast", cylinder(0.018, MAST_TOP - 0.06, 16), "metal", (0, 0, 0.06 + (MAST_TOP - 0.06) / 2), layer=layer)
    a.add("clamp", box(0.06, 0.06, 0.05, bevel=0.01), "graphite", (0, 0, MAST_TOP), layer=layer)
    adapter = box(0.07, 0.11, 0.05, bevel=0.01)
    adapter.transform(m @ Matrix.Translation(Vector((0, 0, 0.01))))
    a.add("adapter", adapter, "graphite", layer=layer)
    a.add("cable", merged([(cylinder(0.009, 0.12, 8), (0.0, -0.05, MAST_TOP - 0.03), (0, 0, 0)), (cylinder(0.009, 0.24, 8), (0.0, -0.035, 0.17), (8, 0, 0))]), "graphite", layer=layer)
    a.add("cable-clips", merged([(box(0.03, 0.03, 0.02), (0, -0.025, z), (0, 0, 0)) for z in (0.12, 0.24)]), "graphite", layer=layer)


def build(tiltDeg: float = 22.0, headingDeg: float = -60.0) -> Asset:
    a = Asset("terminal")
    # Dish assembly, modelled flat around the pivot then turned toward the sky.
    m = dish_matrix(tiltDeg, headingDeg)
    mount(a, m)

    def tilted(bm, loc):
        bm.transform(m @ Matrix.Translation(Vector(loc)))
        return bm

    a.add("back-shell", tilted(box(FACE_W - 0.06, FACE_D - 0.06, 0.03, bevel=0.012), (0, 0, 0.045)), "light")
    a.add("bezel", tilted(box(FACE_W + 0.008, FACE_D + 0.008, 0.012, bevel=0.005), (0, 0, 0.066)), "mid")
    a.add("face", tilted(box(FACE_W, FACE_D, FACE_T - 0.01, bevel=0.01, segments=3), (0, 0, 0.083)), "white")
    beam = m @ Vector((0, 0, 0.11))
    a.anchor("beam", tuple(beam))
    return a
