import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { directionCosines, lobeMesh, phaseSteps, planarFactor, steer, type Frame, type PlanarArray, type Vec3 } from "../../v2/src/beam";
import { steeringDeg } from "../../engine/src/plugins/simulators/phasedArrayWave";

const manifest = JSON.parse(readFileSync(new URL("../../public/v2/models/manifest.json", import.meta.url), "utf8"));
const array: PlanarArray = manifest.assets.terminal.representations.detail.array;
const DEG = Math.PI / 180;
const flat: Frame = { e1: [1, 0, 0], e2: [0, 0, -1], n: [0, 1, 0] };
const angle = (a: Vec3, b: Vec3) => Math.acos(Math.min(1, (a[0] * b[0] + a[1] * b[1] + a[2] * b[2]) / (Math.hypot(...a) * Math.hypot(...b)))) / DEG;

describe("terminal beam (detail view)", () => {
  it("is computed on the exploded model's own grid, at half a wavelength", () => {
    expect(array).toMatchObject({ columns: 24, rows: 15, spacingOverLambda: 0.5 });
  });

  it("phases the columns by Δφ = 2π·d·sinθ/λ toward a target 30° off the normal", () => {
    // Target in the plane (e1, n), 30° from the normal: sinθ = 0.5, d/λ = 0.5 → Δφ = 90°.
    const toTarget: Vec3 = [Math.sin(30 * DEG), Math.cos(30 * DEG), 0];
    const [u, v] = directionCosines(flat, toTarget);
    const phases = phaseSteps(u, v, array.spacingOverLambda);
    expect(phases.columns).toBeCloseTo(360 * 0.5 * Math.sin(30 * DEG), 9);
    expect(phases.columns).toBeCloseTo(90, 9);
    expect(phases.rows).toBeCloseTo(0, 9);
    // And back: the phase step alone gives the angle (inverse of the same relation).
    expect(steeringDeg(phases.columns, array.spacingOverLambda)).toBeCloseTo(30, 9);
  });

  it("points the peak of the array factor at the target, not merely along the normal", () => {
    for (const toTarget of [[0.5, 0.8, 0.2], [-0.3, 0.9, -0.4], [0, 1, 0], [0.62, 0.55, 0.56]] as Vec3[]) {
      const beam = steer(array, flat, toTarget);
      expect(angle(beam.world, toTarget)).toBeLessThan(0.05);
      expect(beam.factor).toBeGreaterThan(0.999);
    }
  });

  it("goes along the normal when no phase is applied, and the factor falls off the beam", () => {
    const zero = { columns: 0, rows: 0 };
    expect(planarFactor(array, zero, 0, 0)).toBeCloseTo(1, 12);
    // First null of the columns: sinθ = λ/(N·d) = 1/12.
    expect(planarFactor(array, zero, 1 / (array.columns * array.spacingOverLambda), 0)).toBeLessThan(1e-9);
  });

  it("draws a lobe whose tip is the beam, at the requested length", () => {
    const beam = steer(array, flat, [0.5, 0.8, 0.2]);
    const { positions, indices } = lobeMesh(array, beam.phases, beam.local, 1.2);
    const tip: Vec3 = [positions[0]!, positions[1]!, positions[2]!];
    expect(Math.hypot(...tip)).toBeCloseTo(1.2, 3);
    expect(angle(tip, beam.local)).toBeLessThan(1e-6);
    let farthest = 0;
    for (let i = 0; i < positions.length; i += 3) farthest = Math.max(farthest, Math.hypot(positions[i]!, positions[i + 1]!, positions[i + 2]!));
    expect(farthest).toBeLessThanOrEqual(1.2 + 1e-6);
    expect(Math.max(...indices)).toBeLessThan(positions.length / 3);
  });
});
