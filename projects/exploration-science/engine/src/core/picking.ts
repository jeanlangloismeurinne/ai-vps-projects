import { InstancedMesh, Mesh, Raycaster, Vector2, type Camera, type Object3D } from "three";
import type { BuiltScene } from "./sceneBuilder";

const raycaster = new Raycaster();
const pointer = new Vector2();

function visibleInScene(o: Object3D): boolean {
  for (let p: Object3D | null = o; p; p = p.parent) if (!p.visible) return false;
  return true;
}

/**
 * The selectable entity under a point of the canvas (normalised device
 * coordinates): the innermost selectable entity around the first visible surface hit.
 */
export function pickEntity(built: BuiltScene, camera: Camera, ndcX: number, ndcY: number): string | null {
  raycaster.setFromCamera(pointer.set(ndcX, ndcY), camera);
  for (const hit of raycaster.intersectObject(built.root, true)) {
    if (!(hit.object instanceof Mesh || hit.object instanceof InstancedMesh) || !visibleInScene(hit.object)) continue;
    for (let o: Object3D | null = hit.object; o; o = o.parent) {
      const id = o.userData.entityId as string | undefined;
      if (id && built.entities.get(id)?.entity.selectable) return id;
    }
    return null; // the first surface hit hides whatever is behind it
  }
  return null;
}
