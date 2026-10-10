import { readFileSync } from "node:fs";
import { join } from "node:path";
import { Mesh, Vector3, type Object3D } from "three";
import { describe, expect, it } from "vitest";
import type { Catalogue, Scene } from "../engine/src/content/types";
import { StaticContentSource } from "../engine/src/content/staticContentSource";
import { PluginRegistry } from "../engine/src/core/registry";
import { buildScene, withDefaults } from "../engine/src/core/sceneBuilder";
import { COMPONENTS, registerComponents } from "../engine/src/plugins/components";
import { latticePositions } from "../engine/src/plugins/components/antennaElementArray";

const ROOT = join(import.meta.dirname, "..");
const readJson = (path: string) => JSON.parse(readFileSync(join(ROOT, path), "utf8"));
const catalogue: Catalogue = readJson("catalogue/catalogue.json");
const starlink: Scene = readJson("content/nodes/starlink-terminal/scene.json");

const registry = new PluginRegistry();
registerComponents(registry);

describe("component plugins", () => {
  it("are all declared in the catalogue (design rule 2)", () => {
    const ids = new Set(catalogue.components.map((c) => c.id));
    for (const plugin of COMPONENTS) expect(ids.has(plugin.id), plugin.id).toBe(true);
  });

  it("cannot be registered twice", () => {
    expect(() => registerComponents(registry)).toThrow(/registered twice/);
  });
});

describe("buildScene on the Starlink node", () => {
  const built = buildScene(starlink, catalogue, registry);

  it("creates one node per entity, with its transform and visibility", () => {
    expect(built.entities.size).toBe(starlink.entities.length);
    const terminal = built.entities.get("terminal")!.node;
    expect(terminal.position.toArray()).toEqual([2, 5.6, 0]);
    expect(built.entities.get("link-user-a")!.node.visible).toBe(false);
  });

  it("attaches children to the parent's anchor (the tilted panel)", () => {
    const array = built.entities.get("phased-array")!.node;
    expect(array.parent?.name).toBe("panel");
    expect(array.parent?.parent?.parent).toBe(built.entities.get("terminal")!.node);
  });

  it("draws placeholders only for components without a plugin", () => {
    const implemented = new Set(COMPONENTS.map((c) => c.id));
    const expected = [...new Set(starlink.entities.map((e) => e.component))].filter((c) => !implemented.has(c)).sort();
    expect(built.missingComponents).toEqual(expected);
    expect(built.entities.get("terminal")!.placeholder).toBe(false);
    expect(built.missingComponents).toEqual([]);
  });

  it("opens the terminal and the house on cutaway, and closes them back", () => {
    const meshes = (id: string) => {
      const list: Object3D[] = [];
      built.entities.get(id)!.instance.object.traverseVisible((o) => list.push(o));
      return list.length;
    };
    for (const id of ["terminal", "house"]) {
      const { instance } = built.entities.get(id)!;
      const closed = meshes(id);
      instance.reveal!("cutaway");
      expect(meshes(id), id).not.toBe(closed);
      instance.reveal!("none");
      expect(meshes(id), id).toBe(closed);
    }
  });

  it("lays out exactly the requested number of radiating elements", () => {
    for (const lattice of ["square", "hexagonal"] as const) {
      const positions = latticePositions(lattice, 1200, 0.0125);
      expect(positions).toHaveLength(1200);
      const xs = positions.map(([x]) => x);
      const zs = positions.map(([, z]) => z);
      // Fits the Starlink panel (0.594 m x 0.383 m).
      expect(Math.max(...xs) - Math.min(...xs)).toBeLessThan(0.594);
      expect(Math.max(...zs) - Math.min(...zs)).toBeLessThan(0.383);
    }
  });

  it("puts the terminal on the roof, not inside it", () => {
    const house = starlink.entities.find((e) => e.id === "house")!.params as { depth: number; wallHeight: number; roofPitchDeg: number };
    const ridge = house.wallHeight + Math.tan((house.roofPitchDeg * Math.PI) / 180) * (house.depth / 2);
    expect(built.focusPoint("terminal").y).toBeGreaterThan(ridge);
  });

  it("resolves entity references: the cable runs from the terminal to the router", () => {
    const cable = built.entities.get("terminal-cable")!.node.children[0] as Mesh;
    cable.geometry.computeBoundingBox();
    const box = cable.geometry.boundingBox!.clone().applyMatrix4(cable.matrixWorld);
    const terminal = built.entities.get("terminal")!.node.getWorldPosition(new Vector3());
    const router = built.entities.get("router")!.node.getWorldPosition(new Vector3());
    expect(box.max.y).toBeCloseTo(terminal.y, 1);
    expect(box.min.x).toBeCloseTo(router.x, 1);
  });

  it("applies catalogue defaults under the scene params", () => {
    expect(withDefaults(catalogue, "house", { width: 10, depth: 8, wallHeight: 3 })).toMatchObject({ roofPitchDeg: 30, width: 10 });
    expect(withDefaults(catalogue, "house", { width: 10, depth: 8, wallHeight: 3, roofPitchDeg: 10 })).toMatchObject({ roofPitchDeg: 10 });
  });
});

describe("buildScene stays subject-agnostic (design rule 1)", () => {
  it("builds the blue-sky control scene with the same core", () => {
    const sky: Scene = readJson("content/nodes/blue-sky/scene.json");
    const built = buildScene(sky, catalogue, registry);
    expect(built.entities.size).toBe(sky.entities.length);
    expect(built.missingComponents).toContain("star");
  });

  it("rejects a parent cycle", () => {
    const scene = structuredClone(starlink);
    const terminal = scene.entities.find((e) => e.id === "terminal")!;
    terminal.parent = "phased-array";
    expect(() => buildScene(scene, catalogue, registry)).toThrow(/parent cycle/);
  });

  it("converts metres to scene units", () => {
    const scene = structuredClone(starlink);
    scene.scale.metersPerUnit = 2;
    const built = buildScene(scene, catalogue, registry);
    let maxX = 0;
    built.entities.get("house")!.node.traverse((o: Object3D) => {
      if (o instanceof Mesh) {
        o.geometry.computeBoundingBox();
        maxX = Math.max(maxX, o.geometry.boundingBox!.max.x);
      }
    });
    expect(maxX).toBeCloseTo((10 + 2 * 0.4) / 2 / 2); // half the width with overhang, in 2 m units
  });
});

describe("StaticContentSource", () => {
  const source = new StaticContentSource();

  it("lists the content nodes", () => {
    expect(source.nodeIds()).toEqual(expect.arrayContaining(["starlink-terminal", "blue-sky"]));
  });

  it("loads a node with its scene, texts by language and sources", async () => {
    const bundle = await source.node("starlink-terminal");
    expect(bundle.scene.node.id).toBe("starlink-terminal");
    expect(Object.keys(bundle.texts)).toEqual(["fr"]);
    expect((await source.catalogue()).components.length).toBeGreaterThan(0);
  });

  it("rejects an unknown node", async () => {
    await expect(source.node("nowhere")).rejects.toThrow(/unknown node/);
  });
});

describe("picking a selectable entity", () => {
  it("returns the innermost selectable entity under the pointer, through an open casing only", async () => {
    const { PerspectiveCamera } = await import("three");
    const { pickEntity } = await import("../engine/src/core/picking");
    const built = buildScene(starlink, catalogue, registry);
    const camera = new PerspectiveCamera(45, 1, 0.01, 1000);
    // Straight down the panel normal, onto a radiating element near the centre.
    const terminal = built.entities.get("terminal")!;
    const panel = terminal.instance.anchor!;
    built.root.updateMatrixWorld(true);
    const normal = new Vector3(0, 1, 0).transformDirection(panel.matrixWorld);
    const centre = panel.getWorldPosition(new Vector3());
    camera.position.copy(centre).addScaledVector(normal, 1);
    camera.lookAt(centre);
    camera.updateMatrixWorld(true);
    expect(pickEntity(built, camera, 0, 0)).toBe("terminal");
    terminal.instance.reveal!("cutaway");
    built.root.updateMatrixWorld(true);
    // Now aim at one radiating element: it is what the pointer gets.
    const [x, z] = latticePositions("hexagonal", 1200, 0.0125)[600]!;
    const element = built.entities.get("phased-array")!.node.localToWorld(new Vector3(x, 0, z));
    camera.position.copy(element).addScaledVector(normal, 1);
    camera.lookAt(element);
    camera.updateMatrixWorld(true);
    expect(pickEntity(built, camera, 0, 0)).toBe("phased-array");
    // The sky: nothing.
    camera.position.set(0, 50, 0);
    camera.lookAt(0, 100, 0);
    camera.updateMatrixWorld(true);
    expect(pickEntity(built, camera, 0, 0)).toBeNull();
  });
});
