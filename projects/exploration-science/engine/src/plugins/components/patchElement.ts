import { BoxGeometry, CylinderGeometry, Group, Mesh, type BufferGeometry } from "three";
import type { ComponentPlugin, RevealMode } from "../../core/registry";

// One radiating element: a square copper patch on an insulating tile, a copper
// ground plane underneath, and the probe that brings the signal up through the
// tile. Lies in the (x, z) plane and radiates towards +y, like the array it
// belongs to. Cutaway removes the front half (z > 0) to show the probe.
const COPPER_THICKNESS_M = 0.0001; // drawn thicker than real foil (~35 µm) so it reads on screen
const PROBE_RADIUS_M = 0.00025;
const PROBE_OFFSET = 0.3; // feed point, as a fraction of the patch side from the centre (a usual design choice)
const PROBE_BELOW_M = 0.0015; // how far the probe sticks out under the ground plane

export const patchElement: ComponentPlugin = {
  id: "patch-element",
  create(params, ctx) {
    const p = params as { patchSize: number; tileSize: number; substrateThickness: number; feed: "probe" | "none" };
    const patch = ctx.metres(p.patchSize);
    const tile = ctx.metres(p.tileSize);
    const h = ctx.metres(p.substrateThickness);
    const cu = ctx.metres(COPPER_THICKNESS_M);
    const geometries: BufferGeometry[] = [];
    const group = new Group();

    // Each layer in two halves along z, so the cutaway can drop the front one.
    const halves = (width: number, height: number, depth: number, y: number, surface: Parameters<typeof ctx.palette.material>[0]) => {
      const g = new BoxGeometry(width, height, depth / 2);
      geometries.push(g);
      const back = new Mesh(g, ctx.palette.material(surface));
      const front = new Mesh(g, ctx.palette.material(surface));
      back.position.set(0, y, -depth / 4);
      front.position.set(0, y, depth / 4);
      group.add(back, front);
      return front;
    };
    const fronts = [
      halves(tile, h, tile, -h / 2, "plastic-light"),
      halves(tile, cu, tile, -h - cu / 2, "copper"),
      halves(patch, cu, patch, cu / 2, "copper"),
    ];

    if (p.feed === "probe") {
      const length = h + cu * 2 + ctx.metres(PROBE_BELOW_M);
      const probe = new CylinderGeometry(ctx.metres(PROBE_RADIUS_M), ctx.metres(PROBE_RADIUS_M), length, 12);
      probe.translate(0, cu - length / 2, 0);
      geometries.push(probe);
      const mesh = new Mesh(probe, ctx.palette.material("copper"));
      mesh.position.x = patch * PROBE_OFFSET;
      group.add(mesh);
    }

    return {
      object: group,
      reveal(mode: RevealMode) {
        for (const f of fronts) f.visible = mode === "none";
      },
      dispose: () => geometries.forEach((g) => g.dispose()),
    };
  },
};
