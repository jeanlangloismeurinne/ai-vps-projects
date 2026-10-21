"""A stylised conifer: a trunk and stacked cones. Decor, varied by its seed."""

import random

from xs.geom import Asset, cone, cylinder, merged


def build(seed: int = 1, id: str = "pine-01", height: float = 1.5) -> Asset:
    rnd = random.Random(seed)
    h = height * rnd.uniform(0.85, 1.15)
    a = Asset(id, main=False)
    a.add("trunk", cylinder(0.05, h * 0.3, 10), "warm", (0, 0, h * 0.15))
    tiers = []
    for i in range(3):
        r = 0.36 * (1 - i * 0.22) * rnd.uniform(0.92, 1.08)
        z = h * (0.22 + i * 0.22)
        tiers.append((cone(r, 0.012, h * 0.42, 14), (0, 0, z + h * 0.21), (0, 0, rnd.uniform(0, 30))))
    a.add("crown", merged(tiers), "foliage")
    return a
