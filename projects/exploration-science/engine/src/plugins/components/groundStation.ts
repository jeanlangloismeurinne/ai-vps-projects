import { BoxGeometry, CylinderGeometry, Group, Mesh, SphereGeometry, type BufferGeometry } from "three";
import type { ComponentPlugin } from "../../core/registry";

// Radomes on plinths, in two rows on a fenced concrete pad. Origin at the pad
// centre, on the ground. Sizes are display values: the entity is notToScale.
const RADOME_M = 4;
const PLINTH_M = 1.5;
const PITCH_M = 7;
const FENCE_M = 2;

export const groundStation: ComponentPlugin = {
  id: "ground-station",
  create(params, ctx) {
    const { antennaCount } = params as { antennaCount: number };
    const r = ctx.metres(RADOME_M / 2);
    const plinth = ctx.metres(PLINTH_M);
    const pitch = ctx.metres(PITCH_M);
    const cols = Math.ceil(antennaCount / 2);
    const rows = antennaCount > 1 ? 2 : 1;
    const padW = cols * pitch + pitch * 0.6;
    const padD = rows * pitch + pitch * 0.6;
    const geometries: BufferGeometry[] = [];
    const group = new Group();

    const pad = new BoxGeometry(padW, ctx.metres(0.3), padD);
    pad.translate(0, ctx.metres(0.15), 0);
    geometries.push(pad);
    group.add(new Mesh(pad, ctx.palette.material("ground-concrete")));

    const base = new CylinderGeometry(r * 0.5, r * 0.6, plinth, 16);
    const dome = new SphereGeometry(r, 24, 16);
    geometries.push(base, dome);
    for (let i = 0; i < antennaCount; i++) {
      const x = ((i % cols) - (cols - 1) / 2) * pitch;
      const z = (Math.floor(i / cols) - (rows - 1) / 2) * pitch;
      const b = new Mesh(base, ctx.palette.material("plastic-dark"));
      b.position.set(x, plinth / 2, z);
      const s = new Mesh(dome, ctx.palette.material("plastic-light"));
      s.position.set(x, plinth + r * 0.85, z);
      group.add(b, s);
    }

    // Fence: one thin wall per side.
    const fenceH = ctx.metres(FENCE_M);
    const t = ctx.metres(0.08);
    for (const [w, d, x, z] of [
      [padW, t, 0, padD / 2],
      [padW, t, 0, -padD / 2],
      [t, padD, padW / 2, 0],
      [t, padD, -padW / 2, 0],
    ] as const) {
      const g = new BoxGeometry(w, fenceH, d);
      g.translate(x, fenceH / 2, z);
      geometries.push(g);
      group.add(new Mesh(g, ctx.palette.material("metal")));
    }

    return { object: group, dispose: () => geometries.forEach((g) => g.dispose()) };
  },
};
