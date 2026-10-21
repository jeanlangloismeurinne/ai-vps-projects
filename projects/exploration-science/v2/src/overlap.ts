// Share of each main object's projected area that lies under a panel (roadmap §4: ≤ 10 %).
// Triangles are projected and rasterised on a coarse grid of CELL × CELL CSS pixels;
// occlusion between objects is ignored (an object hidden by another still counts).
import { Vector3, type Camera, type Mesh, type Object3D } from "three";
import type { Rect } from "./camera";

const CELL = 4;

export function coveredShare(root: Object3D, camera: Camera, width: number, height: number, panel: Rect): number {
  const cols = Math.ceil(width / CELL);
  const rows = Math.ceil(height / CELL);
  const mask = new Uint8Array(cols * rows);
  const [a, b, c] = [new Vector3(), new Vector3(), new Vector3()];
  const toScreen = (v: Vector3) => v.set(((v.x + 1) / 2) * cols, ((1 - v.y) / 2) * rows, v.z);
  root.updateMatrixWorld(true);
  root.traverse((o) => {
    const mesh = o as Mesh;
    if (!mesh.isMesh) return;
    const pos = mesh.geometry.getAttribute("position");
    const index = mesh.geometry.getIndex();
    const n = index ? index.count : pos.count;
    const vertex = (i: number, v: Vector3) => toScreen(v.fromBufferAttribute(pos, index ? index.getX(i) : i).applyMatrix4(mesh.matrixWorld).project(camera));
    for (let t = 0; t + 2 < n; t += 3) {
      vertex(t, a);
      vertex(t + 1, b);
      vertex(t + 2, c);
      if (a.z > 1 || b.z > 1 || c.z > 1) continue;
      fill(mask, cols, rows, a, b, c);
    }
  });
  let total = 0;
  let under = 0;
  const [x0, x1, y0, y1] = [panel.x / CELL, (panel.x + panel.width) / CELL, panel.y / CELL, (panel.y + panel.height) / CELL];
  for (let y = 0; y < rows; y++)
    for (let x = 0; x < cols; x++) {
      if (!mask[y * cols + x]) continue;
      total++;
      if (x + 0.5 >= x0 && x + 0.5 <= x1 && y + 0.5 >= y0 && y + 0.5 <= y1) under++;
    }
  return total ? under / total : 0;
}

/** Marks the cells whose centre lies in the triangle (either winding). Off-screen cells are
 * kept out of the grid, so an object partly off screen is measured on its visible part. */
function fill(mask: Uint8Array, cols: number, rows: number, a: Vector3, b: Vector3, c: Vector3) {
  const minX = Math.max(0, Math.floor(Math.min(a.x, b.x, c.x)));
  const maxX = Math.min(cols - 1, Math.ceil(Math.max(a.x, b.x, c.x)));
  const minY = Math.max(0, Math.floor(Math.min(a.y, b.y, c.y)));
  const maxY = Math.min(rows - 1, Math.ceil(Math.max(a.y, b.y, c.y)));
  const area = (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
  if (Math.abs(area) < 1e-9) return;
  for (let y = minY; y <= maxY; y++)
    for (let x = minX; x <= maxX; x++) {
      const [px, py] = [x + 0.5, y + 0.5];
      const w0 = (b.x - a.x) * (py - a.y) - (b.y - a.y) * (px - a.x);
      const w1 = (c.x - b.x) * (py - b.y) - (c.y - b.y) * (px - b.x);
      const w2 = (a.x - c.x) * (py - c.y) - (a.y - c.y) * (px - c.x);
      if ((w0 >= 0 && w1 >= 0 && w2 >= 0) || (w0 <= 0 && w1 <= 0 && w2 <= 0)) mask[y * cols + x] = 1;
    }
}
