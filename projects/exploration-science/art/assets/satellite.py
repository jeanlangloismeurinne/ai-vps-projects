"""A Starlink V2 Mini satellite (Z up, root at the centre of the bus).

Real proportions (content/v2/sources.json, `satellite-dimensions`): flat bus 4.1 × 2.7 m,
two solar arrays 12.8 × 4.1 m, ≈ 30 m tip to tip. Here the bus is 0.9 × 0.6 units and each
array keeps its 3.1:1 aspect at 1.25 × 0.4 units: the arrays are shortened against the bus
so the satellite reads at a glance (diorama convention, stated in the sources). The phased
arrays face the Earth (−z); the anchor `antenna` is under them."""

from xs.geom import Asset, box, cone, cylinder, merged, sphere

BUS_X, BUS_Y, BUS_Z = 0.9, 0.6, 0.12
ARRAY_L, ARRAY_W, CELLS = 1.25, 0.4, (6, 3)


def build() -> Asset:
    a = Asset("satellite", airborne=True)
    # Metal-grey bus and white top deck: on the light background a white bus had too little
    # outline contrast (scripts/v2/contrast.ts, 41 % of its outline legible).
    a.add("bus", box(BUS_X, BUS_Y, BUS_Z, bevel=0.012), "metal")
    a.add("top-deck", box(BUS_X - 0.06, BUS_Y - 0.06, 0.02, bevel=0.005), "white", (0, 0, BUS_Z / 2 + 0.01))
    # Earth-facing phased arrays: four tiles under the bus.
    tiles = [(box(0.36, 0.22, 0.02, bevel=0.004), (x, y, -BUS_Z / 2 - 0.01), (0, 0, 0)) for x in (-0.2, 0.2) for y in (-0.13, 0.13)]
    a.add("phased-arrays", merged(tiles), "mid")
    a.add("array-grid", merged([(box(0.34, 0.006, 0.006), (x, y + dy, -BUS_Z / 2 - 0.022), (0, 0, 0)) for x in (-0.2, 0.2) for y in (-0.13, 0.13) for dy in (-0.06, 0, 0.06)]), "light", smooth=False)
    # Gateway (Ka / E band) antennas and laser links on the sides.
    a.add("gateway-antennas", merged([(cylinder(0.05, 0.03, 16, bevel=0.006), (x, -BUS_Y / 2 + 0.07, -BUS_Z / 2 - 0.03), (0, 0, 0)) for x in (-0.3, 0.3)]), "light")
    a.add("lasers", merged([(sphere(0.035, 12, 8), (x, BUS_Y / 2 - 0.08, BUS_Z / 2 + 0.035), (0, 0, 0)) for x in (-0.28, 0.0, 0.28)]), "glass", smooth=True)
    a.add("laser-mounts", merged([(cylinder(0.04, 0.03, 12), (x, BUS_Y / 2 - 0.08, BUS_Z / 2 + 0.02), (0, 0, 0)) for x in (-0.28, 0.0, 0.28)]), "graphite")
    a.add("thruster", cone(0.035, 0.05, 0.06, 12), "metal", (0, -BUS_Y / 2 - 0.02, 0), (90, 0, 0))
    # Solar arrays on a mast, along x, edge-on to the camera's nadir view.
    a.add("mast", cylinder(0.025, 0.16, 12), "metal", (0, 0, BUS_Z / 2 + 0.09))
    a.add("yoke", box(0.12, 0.08, 0.05, bevel=0.01), "graphite", (0, 0, BUS_Z / 2 + 0.18))
    a.add("booms", cylinder(0.014, 2 * 0.25, 10), "metal", (0, 0, BUS_Z / 2 + 0.18), (0, 90, 0))
    for side, s in (("east", 1), ("west", -1)):
        cx = s * (0.25 + ARRAY_L / 2)
        z = BUS_Z / 2 + 0.18
        a.add(f"array-{side}-frame", box(ARRAY_L, ARRAY_W, 0.018, bevel=0.004), "metal", (cx, 0, z))
        nx, ny = CELLS
        cw, ch = (ARRAY_L - 0.04) / nx, (ARRAY_W - 0.04) / ny
        cells = [
            (box(cw - 0.012, ch - 0.012, 0.024), (cx - ARRAY_L / 2 + 0.02 + cw * (i + 0.5), -ARRAY_W / 2 + 0.02 + ch * (j + 0.5), z), (0, 0, 0))
            for i in range(nx)
            for j in range(ny)
        ]
        a.add(f"array-{side}-cells", merged(cells), "graphite", smooth=False)
    a.anchor("antenna", (0, 0, -BUS_Z / 2 - 0.04))
    return a
