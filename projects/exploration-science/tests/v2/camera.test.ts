import { describe, expect, it } from "vitest";
import { MathUtils, PerspectiveCamera, Vector3 } from "three";
import { blendPose, frame, type Pose } from "../../v2/src/camera";

// Corners of a wide flat plinth and a point high above it, like the global shot.
const points = [
  ...[-6.5, 6.5].flatMap((x) => [-1.3, 0].flatMap((y) => [-4.7, 4.7].map((z) => new Vector3(x, y, z)))),
  new Vector3(0.5, 6.5, -0.5),
];

function ndc(aspect: number, margin: number) {
  const f = frame(points, -35, 32, 20, aspect, margin);
  const cam = new PerspectiveCamera(20, aspect, 0.1, 500);
  cam.position.copy(f.position);
  cam.lookAt(f.target);
  cam.updateMatrixWorld();
  return points.map((p) => p.clone().project(cam));
}

describe("v2 shot framing", () => {
  for (const aspect of [1366 / 1024, 1024 / 1366, 390 / 844, 1920 / 1080]) {
    it(`fits and centres the points at aspect ${aspect.toFixed(2)}`, () => {
      const margin = 0.05;
      const limit = 1 / (1 + 2 * margin) + 1e-6;
      const p = ndc(aspect, margin);
      for (const q of p) {
        expect(Math.abs(q.x)).toBeLessThanOrEqual(limit);
        expect(Math.abs(q.y)).toBeLessThanOrEqual(limit);
      }
      // Centred: the extent is symmetric, and touches the limit on at least one axis.
      const xs = p.map((q) => q.x);
      const ys = p.map((q) => q.y);
      expect(Math.max(...xs) + Math.min(...xs)).toBeCloseTo(0, 2);
      expect(Math.max(...ys) + Math.min(...ys)).toBeCloseTo(0, 2);
      expect(Math.max(...xs.map(Math.abs), ...ys.map(Math.abs))).toBeCloseTo(limit, 2);
    });
  }

  it("looks from the requested direction", () => {
    const f = frame(points, -35, 32, 20, 1, 0);
    const d = f.position.clone().sub(f.target).normalize();
    expect(MathUtils.radToDeg(Math.asin(d.y))).toBeCloseTo(32, 5);
    expect(MathUtils.radToDeg(Math.atan2(d.x, d.z))).toBeCloseTo(-35, 5);
  });
});

describe("v2 camera flight", () => {
  const pose = (x: number, distance: number): Pose => ({ target: new Vector3(x, 0, 0), azimuthDeg: -35, elevationDeg: 32, distance, offset: [0, 0] });
  // Offset of the subject from the screen centre, in units of the view's half-height.
  const drift = (p: Pose, subject: Vector3) => p.target.distanceTo(subject) / (p.distance * Math.tan(MathUtils.degToRad(10)));

  it("keeps the new subject coming steadily to the centre while flying closer", () => {
    const [from, to] = [pose(0, 65), pose(6, 5)];
    const start = drift(from, to.target);
    for (let i = 0; i <= 20; i++) {
      const t = i / 20;
      expect(drift(blendPose(from, to, t), to.target)).toBeCloseTo(start * (1 - t), 6);
    }
  });

  it("keeps the subject left centred while pulling back, and lands exactly", () => {
    const [from, to] = [pose(6, 5), pose(0, 65)];
    const end = drift(to, from.target);
    for (let i = 0; i <= 20; i++) {
      const t = i / 20;
      expect(drift(blendPose(from, to, t), from.target)).toBeCloseTo(end * t, 6);
    }
    expect(blendPose(from, to, 1).target.toArray()).toEqual(to.target.toArray());
  });
});
