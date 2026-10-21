"""Negative fixture: a closed part whose faces point inward. The build must refuse it."""

import bmesh

from xs.geom import Asset, box


def build() -> Asset:
    a = Asset("inverted")
    a.add("body", box(0.6, 0.6, 0.6, bevel=0.02), "white", (0, 0, 0.3))
    lid = box(0.4, 0.4, 0.1)
    bmesh.ops.reverse_faces(lid, faces=list(lid.faces))
    a.add("lid", lid, "signal", (0, 0, 0.65))
    return a
