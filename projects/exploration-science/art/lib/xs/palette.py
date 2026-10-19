import json
from pathlib import Path

import bpy

PALETTE_PATH = Path(__file__).resolve().parents[2] / "palette.json"


def _srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_to_linear(hex_color: str) -> tuple[float, float, float, float]:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return (_srgb_to_linear(r), _srgb_to_linear(g), _srgb_to_linear(b), 1.0)


def load() -> dict[str, dict]:
    """Every swatch, keyed by name, whatever its group (neutrals, accents, special)."""
    data = json.loads(PALETTE_PATH.read_text())
    swatches: dict[str, dict] = {}
    for group in ("neutrals", "accents", "special"):
        for name, spec in data[group].items():
            swatches[name] = {**spec, "group": group}
    return swatches


def material(name: str) -> bpy.types.Material:
    """The Blender material for a palette swatch, created once. Its name is the swatch
    name, so the app can map exported materials back to the palette (palette test)."""
    existing = bpy.data.materials.get(name)
    if existing:
        return existing
    spec = load()[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = hex_to_linear(spec["color"])
    bsdf.inputs["Roughness"].default_value = spec["roughness"]
    bsdf.inputs["Metallic"].default_value = spec["metallic"]
    if "opacity" in spec:
        bsdf.inputs["Alpha"].default_value = spec["opacity"]
    if spec.get("emissive"):
        bsdf.inputs["Emission Color"].default_value = hex_to_linear(spec["color"])
        bsdf.inputs["Emission Strength"].default_value = spec["emissive"]
    # The baked occlusion lives in the colour attribute "AO"; the exporter writes the
    # active attribute as COLOR_0, which three.js multiplies with the base colour.
    return mat
