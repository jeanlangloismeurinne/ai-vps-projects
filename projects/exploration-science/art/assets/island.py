"""The diorama plinth: a rounded slab of land cut like a cake, so its section shows the
layers (lawn, soil, rock). Its top face is the ground plane z = 0, subdivided so the baked
occlusion can draw contact shadows. Lawns and paths are thin inlays that the other
objects stand on (their placement casts a ray onto the island).

Shared by the scenes: the slab is the same, `layout` picks the inlays (`home`: the Starlink
house and its road; `spaceport`: a launch apron and a ground-station apron joined by a
service road), `id` names the asset of each scene."""

from xs.geom import Asset, box, extrude_xy, grid_slab, merged, rounded_rect


def build(width: float = 13.0, depth: float = 9.5, corner: float = 1.6, id: str = "island", layout: str = "home") -> Asset:
    a = Asset(id, main=False)
    outline = rounded_rect(width, depth, corner, 8)
    a.add("ground", grid_slab(outline, -0.12, 0.0, 0.32), "ground")
    a.add("soil", extrude_xy(rounded_rect(width - 0.02, depth - 0.02, corner, 8), -0.62, -0.12), "warm")
    a.add("rock", extrude_xy(rounded_rect(width - 0.12, depth - 0.12, corner - 0.05, 8), -1.12, -0.62, bevel=0.04), "mid")
    a.add("bedrock", extrude_xy(rounded_rect(width - 0.3, depth - 0.3, corner - 0.15, 8), -1.32, -1.12, bevel=0.03), "graphite")
    if layout == "spaceport":
        return _spaceport(a, width)
    if layout != "home":
        raise ValueError(f"unknown island layout: {layout}")
    # Lawn around the house (west) and a strip along the north edge.
    a.add("lawn-house", grid_slab(_shift(rounded_rect(5.4, 4.6, 0.6, 5), -3.3, 0.9), 0.0, 0.006, 0.3), "foliage")
    a.add("lawn-north", grid_slab(_shift(rounded_rect(3.2, 1.8, 0.5, 5), 1.4, 3.1), 0.0, 0.006, 0.3), "foliage")
    # Paths: house → road, road along the south, gravel apron of the ground station.
    a.add("road", extrude_xy(_shift(rounded_rect(width - 1.4, 0.7, 0.3, 4), 0.0, -3.75), 0.0, 0.004), "mid", smooth=False)
    a.add("road-marks", merged([(box(0.42, 0.05, 0.004), (x, -3.75, 0.004), (0, 0, 0)) for x in range(-5, 6)]), "white", smooth=False)
    # The path stops at the road's edge (y = −3.4) and is gridded like the lawns, so its
    # baked occlusion has interior samples.
    a.add("path", grid_slab(_shift(rounded_rect(0.45, 2.2, 0.15, 3), -2.6, -2.3), 0.0, 0.005, 0.2), "light", smooth=False)
    return a


def _spaceport(a: Asset, width: float) -> Asset:
    """Launch apron (west), ground-station apron (east), lawns between, a service road."""
    a.add("lawn-north", grid_slab(_shift(rounded_rect(6.4, 2.2, 0.7, 5), 0.2, 3.2), 0.0, 0.006, 0.3), "foliage")
    a.add("lawn-centre", grid_slab(_shift(rounded_rect(2.2, 3.4, 0.6, 5), 0.1, -0.4), 0.0, 0.006, 0.3), "foliage")
    a.add("apron-launch", grid_slab(_shift(rounded_rect(4.2, 4.2, 0.5, 5), -3.6, 0.0), 0.0, 0.005, 0.3), "light", smooth=False)
    a.add("apron-station", grid_slab(_shift(rounded_rect(4.0, 3.4, 0.5, 5), 3.5, -0.4), 0.0, 0.005, 0.3), "light", smooth=False)
    a.add("road", extrude_xy(_shift(rounded_rect(width - 1.4, 0.7, 0.3, 4), 0.0, -3.75), 0.0, 0.004), "mid", smooth=False)
    a.add("road-marks", merged([(box(0.42, 0.05, 0.004), (x, -3.75, 0.004), (0, 0, 0)) for x in range(-5, 6)]), "white", smooth=False)
    # Spurs from the road to each apron, gridded like the lawns for their baked occlusion.
    a.add("spurs", merged([(grid_slab(_shift(rounded_rect(0.6, 1.3, 0.15, 3), x, -2.75), 0.0, 0.004, 0.2), (0, 0, 0), (0, 0, 0)) for x in (-3.6, 3.5)]), "mid", smooth=False)
    return a


def _shift(points, dx, dy):
    return [(x + dx, y + dy) for x, y in points]
