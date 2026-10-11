import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import type { Catalogue, Scene } from "../engine/src/content/types";
import { PluginRegistry } from "../engine/src/core/registry";
import { buildScene } from "../engine/src/core/sceneBuilder";
import { AdaptiveResolution, countTriangles } from "../engine/src/core/detail";
import { registerComponents } from "../engine/src/plugins/components";

const ROOT = join(import.meta.dirname, "..");
const readJson = (path: string) => JSON.parse(readFileSync(join(ROOT, path), "utf8"));
const catalogue: Catalogue = readJson("catalogue/catalogue.json");
const registry = new PluginRegistry();
registerComponents(registry);

describe("detail budget", () => {
  for (const id of readdirSync(join(ROOT, "content/nodes"))) {
    const scene: Scene = readJson(`content/nodes/${id}/scene.json`);
    it(`${id}: the built scene stays within its triangle budget`, () => {
      const built = buildScene(scene, catalogue, registry);
      const triangles = countTriangles(built.root);
      expect(scene.performance?.triangleBudget, "every scene declares a budget").toBeDefined();
      expect(triangles).toBeLessThanOrEqual(scene.performance!.triangleBudget!);
      built.dispose();
    });
  }
});

describe("adaptive resolution", () => {
  const run = (r: AdaptiveResolution, fps: number, seconds: number) => {
    for (let t = 0; t < seconds; t += 1 / fps) r.sample(1 / fps);
  };

  it("keeps the full resolution at 60 frames per second", () => {
    const r = new AdaptiveResolution(2);
    run(r, 60, 20);
    expect(r.ratio).toBe(2);
  });

  it("steps down while frames are slow, never below the minimum", () => {
    const r = new AdaptiveResolution(2);
    run(r, 30, 1.6);
    expect(r.ratio).toBe(1.75);
    run(r, 30, 30);
    expect(r.ratio).toBe(1);
  });

  it("climbs back once fast again, after a hold that grows with each drop", () => {
    const r = new AdaptiveResolution(2);
    run(r, 30, 1.6); // one drop: hold 8 s
    expect(r.ratio).toBe(1.75);
    run(r, 60, 7);
    expect(r.ratio).toBe(1.75);
    run(r, 60, 3);
    expect(r.ratio).toBe(2);
    run(r, 30, 1.6); // second drop: hold 16 s
    run(r, 60, 12);
    expect(r.ratio).toBe(1.75);
    run(r, 60, 6);
    expect(r.ratio).toBe(2);
  });

  it("ignores long gaps (hidden tab, loading)", () => {
    const r = new AdaptiveResolution(2);
    for (let i = 0; i < 10; i++) r.sample(2);
    expect(r.ratio).toBe(2);
  });
});
