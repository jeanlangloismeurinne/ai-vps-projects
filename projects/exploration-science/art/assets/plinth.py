"""Display plinth: a bevelled slab whose top face is the ground plane z = 0."""

from xs.geom import Asset, box


def build(width: float = 4.0, depth: float = 3.0, thickness: float = 0.3) -> Asset:
    a = Asset("plinth", main=False)
    a.add("slab", box(width, depth, thickness, bevel=0.04), "ground", (0, 0, -thickness / 2))
    return a
