"""Export of one asset representation to GLB: parts merged by material (few draw calls),
in the asset's own frame (root at the origin), with the baked AO as COLOR_0. Anchors are
exported as empty nodes named `<id>#<anchor>`."""

from pathlib import Path

import bpy

from .geom import canonical_order


def export_asset(asset, path: Path) -> dict:
    """Returns stats measured before merging: named parts and triangles."""
    to_local = asset.root.matrix_world.inverted()
    by_material: dict[str, list[bpy.types.Object]] = {}
    triangles = 0
    for part in asset.parts:
        mesh = part.data.copy()
        mesh.transform(to_local @ part.matrix_world)
        triangles += sum(len(p.vertices) - 2 for p in mesh.polygons)
        tmp = bpy.data.objects.new(f"_x.{part.name}", mesh)
        bpy.context.scene.collection.objects.link(tmp)
        by_material.setdefault(mesh.materials[0].name, []).append(tmp)

    merged: list[bpy.types.Object] = []
    for mat_name in sorted(by_material):
        objs = by_material[mat_name]
        bpy.ops.object.select_all(action="DESELECT")
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        if len(objs) > 1:
            bpy.ops.object.join()
        target = bpy.context.view_layer.objects.active
        target.name = f"{asset.id}.{mat_name}"
        target.data.name = target.name
        target.data.color_attributes.active_color = target.data.color_attributes["AO"]
        canonical_order(target.data)
        merged.append(target)

    anchors: list[bpy.types.Object] = []
    for name in sorted(asset.anchors):
        source = asset.anchors[name]
        full = source.name
        source.name = f"_src.{full}"  # free the name: the exported node carries it
        empty = bpy.data.objects.new(full, None)
        empty.matrix_world = to_local @ source.matrix_world
        bpy.context.scene.collection.objects.link(empty)
        anchors.append(empty)

    bpy.ops.object.select_all(action="DESELECT")
    for o in merged + anchors:
        o.select_set(True)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_apply=True,
        export_texcoords=False,
        export_normals=True,
        export_tangents=False,
        export_materials="EXPORT",
        export_vertex_color="ACTIVE",
        export_extras=False,
    )
    for o in merged:
        bpy.data.meshes.remove(o.data)
    for o in anchors:
        full = o.name
        bpy.data.objects.remove(o)
        bpy.data.objects[f"_src.{full}"].name = full
    return {"parts": len(asset.parts), "triangles": triangles, "materials": sorted(by_material), "anchors": sorted(asset.anchors)}

