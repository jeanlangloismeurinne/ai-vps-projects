import { CylinderGeometry, Group, MathUtils, Mesh, type BufferGeometry } from "three";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";
import type { ComponentPlugin } from "../../core/registry";

// Origin at the panel centre. The panel faces up, tilted towards -Z. Child
// entities attach to the tilted panel frame (y: across the thickness).
const PIPE_LENGTH_M = 0.6; // display value: the catalogue does not size the mount

export const flatPanelTerminal: ComponentPlugin = {
  id: "flat-panel-terminal",
  create(params, ctx) {
    const p = params as { width: number; height: number; thickness: number; mount: "kickstand" | "pipe" | "none"; tiltDeg: number };
    const w = ctx.metres(p.width);
    const l = ctx.metres(p.height);
    const t = ctx.metres(p.thickness);
    const geometries: BufferGeometry[] = [];
    const group = new Group();

    const panel = new Group();
    panel.name = "panel";
    panel.rotation.x = -MathUtils.degToRad(p.tiltDeg);
    const housing = new RoundedBoxGeometry(w, t, l, 4, Math.min(t / 2, ctx.metres(0.015)));
    geometries.push(housing);
    panel.add(new Mesh(housing, ctx.palette.material("plastic-light")));
    group.add(panel);

    const mastRadius = ctx.metres(0.018);
    if (p.mount === "pipe") {
      const pipeLength = ctx.metres(PIPE_LENGTH_M);
      const pipe = new CylinderGeometry(mastRadius, mastRadius, pipeLength, 16);
      pipe.translate(0, -pipeLength / 2, 0);
      geometries.push(pipe);
      group.add(new Mesh(pipe, ctx.palette.material("metal")));
      const collar = new CylinderGeometry(mastRadius * 1.6, mastRadius * 1.6, t * 1.5, 16);
      geometries.push(collar);
      group.add(new Mesh(collar, ctx.palette.material("plastic-dark")));
    } else if (p.mount === "kickstand") {
      const legLength = l * 0.6;
      const leg = new CylinderGeometry(mastRadius, mastRadius, legLength, 12);
      leg.translate(0, -legLength / 2, 0);
      geometries.push(leg);
      const stand = new Mesh(leg, ctx.palette.material("plastic-dark"));
      stand.rotation.x = MathUtils.degToRad(25);
      group.add(stand);
    }

    return { object: group, anchor: panel, dispose: () => geometries.forEach((g) => g.dispose()) };
  },
};
