import { PerspectiveCamera, Vector3 } from "three";
import { describe, expect, it } from "vitest";
import { CameraRig, clampView, interpolateView, orbitOffset, viewFromShot, wrapAngle } from "../engine/src/core/camera";

const deg = (d: number) => (d * Math.PI) / 180;
const constraints = { minDistance: 1, maxDistance: 100, minElevationDeg: -5, maxElevationDeg: 85 };

describe("orbit geometry", () => {
  it("azimuth 0 looks from +Z, 90° from +X, elevation lifts the camera", () => {
    expect(orbitOffset(viewFromShot({ azimuthDeg: 0, elevationDeg: 0, distance: 2 })).toArray().map((v) => +v.toFixed(9))).toEqual([0, 0, 2]);
    expect(orbitOffset(viewFromShot({ azimuthDeg: 90, elevationDeg: 0, distance: 2 })).x).toBeCloseTo(2);
    const up = orbitOffset(viewFromShot({ azimuthDeg: 0, elevationDeg: 30, distance: 2 }));
    expect(up.y).toBeCloseTo(1);
    expect(up.length()).toBeCloseTo(2);
  });

  it("clamps distance and elevation to the scene constraints, never to the pole", () => {
    const v = clampView(viewFromShot({ azimuthDeg: 0, elevationDeg: 89, distance: 500 }), constraints);
    expect(v.distance).toBe(100);
    expect(v.elevation).toBeCloseTo(deg(85));
    expect(clampView(viewFromShot({ azimuthDeg: 0, elevationDeg: -40, distance: 0.1 }), constraints)).toMatchObject({ distance: 1, elevation: deg(-5) });
    expect(clampView(viewFromShot({ azimuthDeg: 0, elevationDeg: 90, distance: 5 }), { minDistance: 1, maxDistance: 10 }).elevation).toBeCloseTo(deg(89));
  });

  it("wraps angles into (-π, π]", () => {
    expect(wrapAngle(deg(270))).toBeCloseTo(deg(-90));
    expect(wrapAngle(deg(-190))).toBeCloseTo(deg(170));
    expect(wrapAngle(Math.PI)).toBeCloseTo(Math.PI);
  });
});

describe("shot transitions", () => {
  const from = viewFromShot({ azimuthDeg: 170, elevationDeg: 10, distance: 100 });
  const to = viewFromShot({ azimuthDeg: -170, elevationDeg: 50, distance: 1 });

  it("start and end on the given views", () => {
    const start = interpolateView(from, to, 0);
    expect(start.elevation).toBe(from.elevation);
    expect(start.distance).toBeCloseTo(100);
    const end = interpolateView(from, to, 1);
    expect(wrapAngle(end.azimuth - to.azimuth)).toBeCloseTo(0);
    expect(end.distance).toBeCloseTo(1);
  });

  it("turn along the shortest arc and zoom in log space", () => {
    const mid = interpolateView(from, to, 0.5);
    expect(Math.abs(mid.azimuth)).toBeCloseTo(Math.PI); // through 180°, not through 0°
    expect(mid.distance).toBeCloseTo(10); // geometric mean of 100 and 1
  });
});

describe("CameraRig", () => {
  const targets: Record<string, Vector3> = { a: new Vector3(0, 0, 0), b: new Vector3(10, 0, 0) };
  const rig = () =>
    new CameraRig(new PerspectiveCamera(), constraints, { target: "a", azimuthDeg: 0, elevationDeg: 0, distance: 5 }, (id) => () => targets[id]!);

  it("places the camera on its orbit, looking at the target", () => {
    const camera = new PerspectiveCamera();
    new CameraRig(camera, constraints, { target: "b", azimuthDeg: 90, elevationDeg: 0, distance: 5 }, (id) => () => targets[id]!);
    expect(camera.position.x).toBeCloseTo(15);
    const forward = camera.getWorldDirection(new Vector3());
    expect(forward.x).toBeCloseTo(-1);
  });

  it("flies to a shot and lands exactly on it", () => {
    const r = rig();
    r.flyTo({ target: "b", azimuthDeg: 90, elevationDeg: 30, distance: 2 }, 1);
    for (let i = 0; i < 70; i++) r.update(1 / 60);
    expect(r.flying).toBe(false);
    expect(r.target.toArray()).toEqual([10, 0, 0]);
    expect(r.view.distance).toBeCloseTo(2);
  });

  it("gives the user the last word: a drag cancels the flight", () => {
    const r = rig();
    r.flyTo({ target: "b", azimuthDeg: 90, elevationDeg: 30, distance: 2 }, 2);
    r.update(0.1);
    r.orbitBy(0.1, 0, 0.016);
    expect(r.flying).toBe(false);
  });

  it("keeps user zoom inside the constraints", () => {
    const r = rig();
    for (let i = 0; i < 50; i++) r.zoomBy(0.5);
    expect(r.view.distance).toBe(1);
    for (let i = 0; i < 50; i++) r.zoomBy(2);
    expect(r.view.distance).toBe(100);
  });
});
