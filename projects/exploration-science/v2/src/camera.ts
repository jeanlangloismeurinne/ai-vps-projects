// Shot framing: a camera on a fixed direction (azimuth, elevation) placed so that a set of
// points fits the view, centred, whatever the screen's aspect ratio (render.schema.json).
import { MathUtils, Vector3 } from "three";

export interface Framing {
  position: Vector3;
  target: Vector3;
}

/** Unit vector from the target toward the camera. Azimuth 0 looks from the front (glTF +z),
 * positive toward +x; elevation above the horizon. */
export function viewDirection(azimuthDeg: number, elevationDeg: number): Vector3 {
  const az = MathUtils.degToRad(azimuthDeg);
  const el = MathUtils.degToRad(elevationDeg);
  return new Vector3(Math.cos(el) * Math.sin(az), Math.sin(el), Math.cos(el) * Math.cos(az));
}

/** `margin`: room kept around the points, as a fraction of the view on each side. */
export function frame(points: Vector3[], azimuthDeg: number, elevationDeg: number, fovDeg: number, aspect: number, margin = 0): Framing {
  const dir = viewDirection(azimuthDeg, elevationDeg);
  const forward = dir.clone().negate();
  const right = new Vector3().crossVectors(forward, new Vector3(0, 1, 0)).normalize();
  const up = new Vector3().crossVectors(right, forward);
  const tanV = Math.tan(MathUtils.degToRad(fovDeg / 2)) / (1 + 2 * margin);
  const tanH = (Math.tan(MathUtils.degToRad(fovDeg / 2)) * aspect) / (1 + 2 * margin);

  const target = points.reduce((s, p) => s.add(p), new Vector3()).divideScalar(Math.max(points.length, 1));
  let distance = 0;
  for (let i = 0; i < 4; i++) {
    distance = 0;
    for (const p of points) {
      const d = p.clone().sub(target);
      distance = Math.max(distance, d.dot(dir) + Math.abs(d.dot(right)) / tanH, d.dot(dir) + Math.abs(d.dot(up)) / tanV);
    }
    // Re-centre: shift the target by the middle of the projected extent.
    let [x0, x1, y0, y1] = [Infinity, -Infinity, Infinity, -Infinity];
    for (const p of points) {
      const d = p.clone().sub(target);
      const depth = distance - d.dot(dir);
      const x = d.dot(right) / depth;
      const y = d.dot(up) / depth;
      [x0, x1, y0, y1] = [Math.min(x0, x), Math.max(x1, x), Math.min(y0, y), Math.max(y1, y)];
    }
    const shiftX = ((x0 + x1) / 2) * distance;
    const shiftY = ((y0 + y1) / 2) * distance;
    if (Math.abs(shiftX) + Math.abs(shiftY) < 1e-4) break;
    target.addScaledVector(right, shiftX).addScaledVector(up, shiftY);
  }
  return { position: target.clone().addScaledVector(dir, distance), target };
}
