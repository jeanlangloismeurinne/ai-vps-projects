"""Ambient occlusion baked by Cycles (CPU) into the colour attribute "AO" of every part.

The bake runs on the assembled scene, so contact shadows between assets (a house on
its ground) are part of the result. Settings come from the scene file.
"""

import bpy

AO_ATTRIBUTE = "AO"


def bake_ao(objects: list[bpy.types.Object], *, samples: int, distance: float, seed: int = 0) -> None:
    scene = bpy.context.scene
    if scene.world is None:
        scene.world = bpy.data.worlds.new("bake")
    scene.world.light_settings.distance = distance
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.seed = seed
    scene.cycles.use_denoising = False
    scene.render.bake.target = "VERTEX_COLORS"
    for obj in objects:
        attrs = obj.data.color_attributes
        if AO_ATTRIBUTE not in attrs:
            attrs.new(AO_ATTRIBUTE, "BYTE_COLOR", "CORNER")
        attrs.active_color = attrs[AO_ATTRIBUTE]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.bake(type="AO")
