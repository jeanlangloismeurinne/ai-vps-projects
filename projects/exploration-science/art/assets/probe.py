"""Toolchain probe (roadmap v2 §1): a bevelled box with a door and a roof cap.
Not a v0 object — it only proves the pipeline from script to browser."""

from xs.geom import Asset, box


def build() -> Asset:
    a = Asset("probe", main=False)
    a.add("body", box(1.2, 0.8, 0.6, bevel=0.03), "white", (0, 0, 0.3))
    a.add("cap", box(1.3, 0.9, 0.06, bevel=0.015), "signal", (0, 0, 0.63))
    a.add("door", box(0.3, 0.04, 0.42, bevel=0.01), "graphite", (0.25, -0.41, 0.21))
    a.anchor("top", (0, 0, 0.66))
    return a
