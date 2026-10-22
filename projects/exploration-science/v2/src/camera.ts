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

/** Part of the canvas left free by the panels, in CSS pixels from the top-left corner. */
export interface Rect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface WindowFraming extends Framing {
  /** For `camera.setViewOffset(W, H, offset[0], offset[1], W, H)`: moves the projection
   * centre to the centre of the free window (exact off-axis view, no parallax). */
  offset: [number, number];
}

/** Like `frame`, but fits the points in the window `free` of a `width` × `height` canvas
 * (the rest is under a panel). The vertical field of view `fovDeg` spans the whole canvas. */
export function frameInWindow(points: Vector3[], azimuthDeg: number, elevationDeg: number, fovDeg: number, width: number, height: number, free: Rect, margin = 0): WindowFraming {
  const tanFull = Math.tan(MathUtils.degToRad(fovDeg / 2));
  const fovFree = MathUtils.radToDeg(2 * Math.atan((tanFull * free.height) / height));
  const f = frame(points, azimuthDeg, elevationDeg, fovFree, free.width / free.height, margin);
  return { ...f, offset: [width / 2 - (free.x + free.width / 2), height / 2 - (free.y + free.height / 2)] };
}

/** Camera pose as the rig moves it: interpolating angles and the logarithm of the distance
 * flies around and toward the subject, where interpolating positions would cut through it. */
export interface Pose {
  target: Vector3;
  azimuthDeg: number;
  elevationDeg: number;
  distance: number;
  offset: [number, number];
}

/** Pose of a framing seen from (`azimuthDeg`, `elevationDeg`), its distance times `zoom`. */
export function poseOf(f: WindowFraming, azimuthDeg: number, elevationDeg: number, zoom = 1): Pose {
  return { target: f.target.clone(), azimuthDeg, elevationDeg, distance: f.position.distanceTo(f.target) * zoom, offset: [...f.offset] };
}

export const clonePose = (p: Pose): Pose => ({ ...p, target: p.target.clone(), offset: [...p.offset] });

export const positionOf = (p: Pose): Vector3 => p.target.clone().addScaledVector(viewDirection(p.azimuthDeg, p.elevationDeg), p.distance);

/** `a` at t = 0, `b` at t = 1. The target moves at the pace of the distance: going closer,
 * what is left of its way shrinks with the distance, so that the new subject comes to the
 * centre steadily instead of drifting to the edge mid-flight (its offset on screen goes as
 * (1 − t)); going back out, symmetrically, the subject left stays centred while the camera
 * pulls back. */
export function blendPose(a: Pose, b: Pose, t: number): Pose {
  const mix = (x: number, y: number) => x + (y - x) * t;
  if (t >= 1) return clonePose(b);
  const distance = Math.exp(mix(Math.log(a.distance), Math.log(b.distance)));
  const w = b.distance < a.distance ? 1 - ((1 - t) * distance) / a.distance : (t * distance) / b.distance;
  return {
    target: a.target.clone().lerp(b.target, w),
    azimuthDeg: mix(a.azimuthDeg, b.azimuthDeg),
    elevationDeg: mix(a.elevationDeg, b.elevationDeg),
    distance,
    offset: [mix(a.offset[0], b.offset[0]), mix(a.offset[1], b.offset[1])],
  };
}

/** Largest gap between two poses, in units comparable to a pixel on screen (1 = 1 px of
 * offset, 1/1000 of the distance, 0.05° of angle): for "settled" and round-trip checks. */
export function poseGap(a: Pose, b: Pose): number {
  return Math.max(
    (a.target.distanceTo(b.target) / Math.max(b.distance, 1e-6)) * 1000,
    Math.abs(Math.log(a.distance / b.distance)) * 1000,
    Math.abs(a.azimuthDeg - b.azimuthDeg) / 0.05,
    Math.abs(a.elevationDeg - b.elevationDeg) / 0.05,
    Math.abs(a.offset[0] - b.offset[0]),
    Math.abs(a.offset[1] - b.offset[1]),
  );
}

/** Ease-in-out (cubic): the flight leaves and lands softly. */
export const easeInOut = (t: number): number => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);
