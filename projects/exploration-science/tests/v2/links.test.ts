import { describe, expect, it } from "vitest";
import { Box3, BoxGeometry, Mesh, PerspectiveCamera, Vector3 } from "three";
import { frameInWindow } from "../../v2/src/camera";
import { connectionPath, flowPath, Polyline } from "../../v2/src/links";
import { coveredShare } from "../../v2/src/overlap";
import system from "../../content/v2/systems/starlink-home.json";

// Anchors laid out like the diorama: terminal on the roof, satellite above, station's dish
// and fibre box a little apart, the setting a 13 × 9.4 m plinth with its top at y = 0.
const setting = new Box3(new Vector3(-6.5, -1.3, -4.7), new Vector3(6.5, 0, 4.7));
const anchors: Record<string, Vector3> = {
  "terminal#beam": new Vector3(-2, 2.2, -1),
  "satellite#antenna": new Vector3(0.5, 6.4, -0.5),
  "ground-station#dish": new Vector3(3, 0.6, 2),
  "ground-station#fibre": new Vector3(4.2, 0.1, 2.6),
};
const kinds: Record<string, "beam-dashed" | "ground-line"> = { radio: "beam-dashed", fibre: "ground-line" };
const paths = Object.fromEntries(system.connections.map((c) => [c.id, connectionPath(kinds[c.kind]!, anchors[c.from]!, anchors[c.to] ?? null, setting)]));
const dataDown = system.flows.find((f) => f.id === "data-down")! as { id: string; path: string[]; direction: "reverse" };

describe("v2 links and flows", () => {
  it("runs the fibre to Internet out of the plinth by its nearest edge and down the cut face", () => {
    const p = paths["backhaul"]!;
    expect(p).toHaveLength(3);
    expect(p[1]!.z).toBeCloseTo(setting.max.z);
    expect(p[2]!.y).toBeLessThan(setting.max.y - 1);
  });

  it("orients the data flow from Internet to the terminal on the roof", () => {
    const { points } = flowPath(dataDown, paths);
    expect(points[0]!.y).toBeLessThan(setting.max.y - 1); // the Internet end, down the cut face
    expect(points[points.length - 1]!.distanceTo(anchors["terminal#beam"]!)).toBeLessThan(1e-9);
    // Through the satellite, after the station.
    const sat = points.findIndex((v) => v.distanceTo(anchors["satellite#antenna"]!) < 1e-9);
    const dish = points.findIndex((v) => v.distanceTo(anchors["ground-station#dish"]!) < 1e-9);
    expect(dish).toBeGreaterThan(0);
    expect(sat).toBeGreaterThan(dish);
  });

  it("hides the flow inside the station, between the fibre box and the dish", () => {
    const { points, hidden } = flowPath(dataDown, paths);
    expect(hidden).toHaveLength(points.length - 1);
    const gaps = hidden.flatMap((h, i) => (h ? [i] : []));
    expect(gaps).toHaveLength(1);
    const g = gaps[0]!;
    expect(points[g]!.x).toBeCloseTo(anchors["ground-station#fibre"]!.x);
    expect(points[g + 1]!.distanceTo(anchors["ground-station#dish"]!)).toBeLessThan(1e-9);
  });

  it("parametrises a polyline by arc length", () => {
    const line = new Polyline([new Vector3(0, 0, 0), new Vector3(2, 0, 0), new Vector3(2, 3, 0)], [false, true]);
    expect(line.length).toBeCloseTo(5);
    const a = line.at(1);
    expect(a.point.x).toBeCloseTo(1);
    expect(a.hidden).toBe(false);
    const b = line.at(3.5);
    expect(b.point.y).toBeCloseTo(1.5);
    expect(b.tangent.y).toBeCloseTo(1);
    expect(b.hidden).toBe(true);
  });
});

describe("v2 framing beside a panel", () => {
  const points = [...[-6.5, 6.5].flatMap((x) => [-1.3, 0].flatMap((y) => [-4.7, 4.7].map((z) => new Vector3(x, y, z)))), new Vector3(0.5, 6.5, -0.5)];

  for (const [name, W, H, free] of [
    ["right panel", 1366, 1024, { x: 0, y: 0, width: 960, height: 1024 }],
    ["bottom sheet", 390, 844, { x: 0, y: 0, width: 390, height: 520 }],
  ] as const) {
    it(`keeps every point in the free window (${name})`, () => {
      const f = frameInWindow(points, -35, 32, 20, W, H, free, 0.03);
      const cam = new PerspectiveCamera(20, W / H, 0.1, 500);
      cam.position.copy(f.position);
      cam.lookAt(f.target);
      cam.setViewOffset(W, H, f.offset[0], f.offset[1], W, H);
      cam.updateMatrixWorld();
      const px = points.map((p) => p.clone().project(cam)).map((v) => ({ x: ((v.x + 1) / 2) * W, y: ((1 - v.y) / 2) * H }));
      for (const p of px) {
        expect(p.x).toBeGreaterThanOrEqual(free.x - 0.5);
        expect(p.x).toBeLessThanOrEqual(free.x + free.width + 0.5);
        expect(p.y).toBeGreaterThanOrEqual(free.y - 0.5);
        expect(p.y).toBeLessThanOrEqual(free.y + free.height + 0.5);
      }
      // Fills the window: it touches at least one side of it on each axis.
      const xs = px.map((p) => p.x);
      const ys = px.map((p) => p.y);
      const fillX = (Math.max(...xs) - Math.min(...xs)) / free.width;
      const fillY = (Math.max(...ys) - Math.min(...ys)) / free.height;
      expect(Math.max(fillX, fillY)).toBeGreaterThan(0.9);
    });
  }
});

describe("v2 panel overlap measure", () => {
  // A 2 m cube in front of the camera fills the middle of a 400 × 400 view.
  const cube = new Mesh(new BoxGeometry(2, 2, 2));
  const cam = new PerspectiveCamera(40, 1, 0.1, 100);
  cam.position.set(0, 0, 8);
  cam.lookAt(0, 0, 0);
  cam.updateMatrixWorld();

  it("measures the share of an object under a panel", () => {
    expect(coveredShare(cube, cam, 400, 400, { x: 0, y: 0, width: 400, height: 400 })).toBeCloseTo(1, 2);
    expect(coveredShare(cube, cam, 400, 400, { x: 300, y: 0, width: 100, height: 400 })).toBe(0);
    const half = coveredShare(cube, cam, 400, 400, { x: 200, y: 0, width: 200, height: 400 });
    expect(half).toBeGreaterThan(0.45);
    expect(half).toBeLessThan(0.55);
  });
});
