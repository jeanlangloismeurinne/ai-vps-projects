import { Box3, InstancedMesh, Matrix4, Mesh, Ray, Raycaster, Vector2, Vector3, type Camera, type Object3D } from "three";
import type { BuiltScene } from "./sceneBuilder";

const raycaster = new Raycaster();
const pointer = new Vector2();
const box = new Box3();
const part = new Box3();
const entry = new Vector3();
const toLocal = new Matrix4();
const relative = new Matrix4();
const localRay = new Ray();

/** Bounds of an entity in its own frame: tight for a tilted flat array, unlike world bounds. */
function localBounds(node: Object3D): Box3 {
  box.makeEmpty();
  toLocal.copy(node.matrixWorld).invert();
  node.traverse((o) => {
    if (!(o instanceof Mesh)) return;
    const bounds = o instanceof InstancedMesh ? o.boundingBox : (o.geometry.boundingBox ?? (o.geometry.computeBoundingBox(), o.geometry.boundingBox));
    if (bounds) box.union(part.copy(bounds).applyMatrix4(relative.multiplyMatrices(toLocal, o.matrixWorld)));
  });
  return box;
}

function visibleInScene(o: Object3D): boolean {
  for (let p: Object3D | null = o; p; p = p.parent) if (!p.visible) return false;
  return true;
}

function entityOf(built: BuiltScene, o: Object3D | null): string | null {
  for (; o; o = o.parent) {
    const id = o.userData.entityId as string | undefined;
    if (id && built.entities.get(id)?.entity.selectable) return id;
  }
  return null;
}

/**
 * The selectable entity under a point of the canvas (normalised device
 * coordinates). The first visible surface hit decides; if it lies past the
 * bounds of a selectable child (a click between the radiating elements of an
 * opened terminal lands on its floor), that child wins: the nearest along the ray.
 */
export function pickEntity(built: BuiltScene, camera: Camera, ndcX: number, ndcY: number): string | null {
  raycaster.setFromCamera(pointer.set(ndcX, ndcY), camera);
  const hit = raycaster.intersectObject(built.root, true).find((h) => h.object instanceof Mesh && visibleInScene(h.object));
  if (!hit) return null;
  let id = entityOf(built, hit.object);
  if (!id) return null;
  let best = hit.distance;
  for (const [childId, child] of built.entities) {
    if (childId === id || !child.entity.selectable || !visibleInScene(child.node)) continue;
    if (entityOf(built, child.node.parent) !== id) continue;
    child.node.updateWorldMatrix(true, true);
    localRay.copy(raycaster.ray).applyMatrix4(toLocal.copy(child.node.matrixWorld).invert());
    if (!localRay.intersectBox(localBounds(child.node), entry)) continue;
    const d = entry.applyMatrix4(child.node.matrixWorld).distanceTo(raycaster.ray.origin);
    if (d <= best) {
      best = d;
      id = childId;
    }
  }
  return id;
}
