"""Negative fixture: a part hanging 5 cm above the body. The build must refuse it."""

from xs.geom import Asset, box


def build() -> Asset:
    a = Asset("floating")
    a.add("body", box(0.6, 0.6, 0.6, bevel=0.02), "white", (0, 0, 0.3))
    a.add("ghost", box(0.3, 0.3, 0.1, bevel=0.01), "signal", (0, 0, 0.7))
    return a
