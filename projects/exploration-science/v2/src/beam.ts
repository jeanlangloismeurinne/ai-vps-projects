// Beam of the terminal's planar array, computed with the equations of the Phase 0 simulator
// `phased-array-wave` (engine/src/plugins/simulators/phasedArrayWave.ts), pure.
//
// The array is a grid of columns × rows point sources, `spacingOverLambda` wavelengths apart
// both ways, in the plane (e1, e2) with its normal n. Steering toward a target, the beamformer
// gives each source a phase growing by Δφ from one neighbour to the next along each axis,
// Δφ = 2π·d·sinθ/λ with sinθ the target direction's component along that axis (d: spacing,
// λ: wavelength, θ: angle from the normal in the plane of that axis). The beam drawn is NOT
// aimed at the target: it is where the array factor of those phases peaks.
import { arrayFactor, phaseStepDeg } from "../../engine/src/plugins/simulators/phasedArrayWave";

export type Vec3 = [number, number, number];

export interface PlanarArray {
  columns: number;
  rows: number;
  spacingOverLambda: number;
}

export interface Frame {
  e1: Vec3;
  e2: Vec3;
  n: Vec3;
}

const DEG = Math.PI / 180;
const dot = (a: Vec3, b: Vec3) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const norm = (a: Vec3): Vec3 => {
  const l = Math.hypot(...a);
  return [a[0] / l, a[1] / l, a[2] / l];
};

/** Direction cosines (along e1, e2, n) of `direction` in the array's frame. */
export function directionCosines(frame: Frame, direction: Vec3): Vec3 {
  const d = norm(direction);
  return [dot(d, frame.e1), dot(d, frame.e2), dot(d, frame.n)];
}

/** Phase steps between neighbours (degrees, along columns then rows) steering toward the
 * direction with cosines (u, v): Δφ = 360°·(d/λ)·u, by the simulator's phaseStepDeg. */
export function phaseSteps(u: number, v: number, spacingOverLambda: number): { columns: number; rows: number } {
  return { columns: phaseStepDeg(Math.asin(u) / DEG, spacingOverLambda), rows: phaseStepDeg(Math.asin(v) / DEG, spacingOverLambda) };
}

/** Normalised |AF| of the planar array toward the cosines (u, v): the product of the two
 * linear array factors of the simulator (a uniform grid separates). */
export function planarFactor(array: PlanarArray, phases: { columns: number; rows: number }, u: number, v: number): number {
  if (u * u + v * v > 1) return 0;
  const s = array.spacingOverLambda;
  return arrayFactor(Math.asin(u) / DEG, array.columns, s, phases.columns) * arrayFactor(Math.asin(v) / DEG, array.rows, s, phases.rows);
}

/** Direction cosines (u, v) where the array factor peaks over the half-space in front of the
 * array: a coarse grid, then a few refinements around the best point. */
export function peak(array: PlanarArray, phases: { columns: number; rows: number }): { u: number; v: number; factor: number } {
  let best = { u: 0, v: 0, factor: -1 };
  let step = 0.02;
  const scan = (u0: number, v0: number, half: number) => {
    for (let u = u0 - half; u <= u0 + half + 1e-12; u += step) {
      for (let v = v0 - half; v <= v0 + half + 1e-12; v += step) {
        const f = planarFactor(array, phases, u, v);
        if (f > best.factor) best = { u, v, factor: f };
      }
    }
  };
  scan(0, 0, 1);
  for (let i = 0; i < 6; i++) {
    const half = step * 2;
    step /= 5;
    scan(best.u, best.v, half);
  }
  return best;
}

/** The steered beam: phases set toward the target, then the factor's peak. */
export function steer(array: PlanarArray, frame: Frame, toTarget: Vec3) {
  const [u0, v0, w0] = directionCosines(frame, toTarget);
  const phases = phaseSteps(u0, v0, array.spacingOverLambda);
  const { u, v, factor } = peak(array, phases);
  const w = Math.sqrt(Math.max(0, 1 - u * u - v * v));
  const local: Vec3 = [u, v, w];
  const world: Vec3 = [0, 1, 2].map((i) => u * frame.e1[i]! + v * frame.e2[i]! + w * frame.n[i]!) as Vec3;
  return {
    phases,
    /** Angle between the array's normal and the target, degrees. */
    targetOffNormalDeg: Math.acos(Math.min(1, w0 / Math.hypot(u0, v0, w0))) / DEG,
    local,
    world,
    factor,
  };
}

/** Surface of the radiation lobe around the beam, in the array's frame (e1, e2, n): radius
 * `length`·|AF|² (power pattern) along each direction, sampled by angle α from the beam
 * (finer near it) and turn β around it, out to `maxAngleDeg`. Returns triangle-ready arrays, the
 * array's centre at the origin. */
export function lobeMesh(
  array: PlanarArray,
  phases: { columns: number; rows: number },
  beam: Vec3,
  length: number,
  { rings = 48, turns = 48, maxAngleDeg = 30 } = {},
): { positions: Float32Array; indices: Uint32Array } {
  const b = norm(beam);
  // Two unit vectors across the beam.
  const helper: Vec3 = Math.abs(b[2]) < 0.9 ? [0, 0, 1] : [1, 0, 0];
  const c1 = norm([helper[1] * b[2] - helper[2] * b[1], helper[2] * b[0] - helper[0] * b[2], helper[0] * b[1] - helper[1] * b[0]]);
  const c2: Vec3 = [b[1] * c1[2] - b[2] * c1[1], b[2] * c1[0] - b[0] * c1[2], b[0] * c1[1] - b[1] * c1[0]];
  // The tip along the beam, then rings of growing angle α, shrinking back to the array.
  const positions = new Float32Array((1 + rings * turns) * 3);
  const tip = b[2] > 0 ? length * planarFactor(array, phases, b[0], b[1]) ** 2 : 0;
  positions.set([b[0] * tip, b[1] * tip, b[2] * tip], 0);
  for (let i = 0; i < rings; i++) {
    const alpha = maxAngleDeg * DEG * ((i + 1) / rings) ** 2;
    for (let j = 0; j < turns; j++) {
      const beta = (2 * Math.PI * j) / turns;
      const d: Vec3 = [0, 1, 2].map((k) => Math.cos(alpha) * b[k]! + Math.sin(alpha) * (Math.cos(beta) * c1[k]! + Math.sin(beta) * c2[k]!)) as Vec3;
      const r = d[2] > 0 ? length * planarFactor(array, phases, d[0], d[1]) ** 2 : 0;
      positions.set([d[0] * r, d[1] * r, d[2] * r], 3 * (1 + i * turns + j));
    }
  }
  const indices: number[] = [];
  const at = (i: number, j: number) => 1 + i * turns + (j % turns);
  for (let j = 0; j < turns; j++) indices.push(0, at(0, j), at(0, j + 1));
  for (let i = 0; i + 1 < rings; i++) {
    for (let j = 0; j < turns; j++) indices.push(at(i, j), at(i + 1, j), at(i + 1, j + 1), at(i, j), at(i + 1, j + 1), at(i, j + 1));
  }
  return { positions, indices: Uint32Array.from(indices) };
}
