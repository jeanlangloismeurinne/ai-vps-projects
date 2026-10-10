import { BoxGeometry, CylinderGeometry, Group, MathUtils, Mesh, type BufferGeometry } from "three";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";
import type { ComponentPlugin, RevealMode } from "../../core/registry";

// Origin at the panel centre. The panel faces up, tilted towards -Z. Child
// entities attach to the tilted panel frame (y: across the thickness).
// Cutaway: the closed housing gives way to an open tray, so the children show.
// Explode: the same, with the children lifted apart along the panel normal.
const PIPE_LENGTH_M = 0.6; // display value: the catalogue does not size the mount
const TRAY_FLOOR_M = 0.003;
const TRAY_WALL_M = 0.006;
const EXPLODE_STEP = 2; // children spread to this many panel thicknesses apart

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
    group.add(panel);

    const closed = new RoundedBoxGeometry(w, t, l, 4, Math.min(t / 2, ctx.metres(0.015)));
    geometries.push(closed);
    const housing = new Mesh(closed, ctx.palette.material("plastic-light"));
    panel.add(housing);

    const tray = new Group();
    tray.visible = false;
    const floorT = ctx.metres(TRAY_FLOOR_M);
    const wallT = ctx.metres(TRAY_WALL_M);
    for (const [gw, gh, gd, y, x, z] of [
      [w, floorT, l, -t / 2 + floorT / 2, 0, 0],
      [w, t, wallT, 0, 0, l / 2 - wallT / 2],
      [w, t, wallT, 0, 0, -l / 2 + wallT / 2],
      [wallT, t, l, 0, w / 2 - wallT / 2, 0],
      [wallT, t, l, 0, -w / 2 + wallT / 2, 0],
    ] as const) {
      const g = new BoxGeometry(gw, gh, gd);
      g.translate(x, y, z);
      geometries.push(g);
      tray.add(new Mesh(g, ctx.palette.material("plastic-light")));
    }
    panel.add(tray);

    const mastRadius = ctx.metres(0.018);
    if (p.mount === "pipe") {
      const pipeLength = ctx.metres(PIPE_LENGTH_M);
      const pipe = new CylinderGeometry(mastRadius, mastRadius, pipeLength, 16);
      pipe.translate(0, -pipeLength / 2, 0);
      geometries.push(pipe);
      group.add(new Mesh(pipe, ctx.palette.material("metal")));
      // Under the panel, so it never pokes through the radome.
      const collar = new CylinderGeometry(mastRadius * 1.6, mastRadius * 1.6, t * 1.5, 16);
      collar.translate(0, -t * 0.75, 0);
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

    // Children are added to the panel after creation: remember their resting height on first use.
    const rest = new Map<object, number>();
    const children = () => panel.children.filter((c) => c !== housing && c !== tray);

    return {
      object: group,
      anchor: panel,
      reveal(mode: RevealMode) {
        housing.visible = mode === "none";
        tray.visible = mode !== "none";
        const sorted = children().sort((a, b) => a.position.y - b.position.y);
        sorted.forEach((child, i) => {
          if (!rest.has(child)) rest.set(child, child.position.y);
          child.position.y = rest.get(child)! + (mode === "explode" ? i * t * EXPLODE_STEP : 0);
        });
      },
      dispose: () => geometries.forEach((g) => g.dispose()),
    };
  },
};
