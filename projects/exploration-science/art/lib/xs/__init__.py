"""Procedural modelling toolkit for the v2 assets (Blender driven by Python, no UI).

An asset script builds named parts under one root empty; the build driver bakes,
checks and exports them. Everything is deterministic: no randomness without an
explicit seeded `random.Random`.
"""
