import { BoxGeometry, ExtrudeGeometry, Group, MathUtils, Mesh, Shape, type BufferGeometry } from "three";
import type { ComponentPlugin, RevealMode } from "../../core/registry";

// Origin at the centre of the ground floor. The ridge runs along X (the facade
// width), the roof slopes down towards ±Z. Cutaway removes the +Z wall and the
// +Z roof slab, like a doll's house; the -Z slab stays, with whatever sits on it.
const WALL_M = 0.2;

export const house: ComponentPlugin = {
  id: "house",
  create(params, ctx) {
    const p = params as { width: number; depth: number; wallHeight: number; roofPitchDeg: number };
    const w = ctx.metres(p.width);
    const d = ctx.metres(p.depth);
    const h = ctx.metres(p.wallHeight);
    const wall = ctx.metres(WALL_M);
    const pitch = MathUtils.degToRad(p.roofPitchDeg);
    const rise = Math.tan(pitch) * (d / 2);
    const geometries: BufferGeometry[] = [];
    const group = new Group();
    const add = (geometry: BufferGeometry, surface: Parameters<typeof ctx.palette.material>[0]) => {
      geometries.push(geometry);
      const mesh = new Mesh(geometry, ctx.palette.material(surface));
      group.add(mesh);
      return mesh;
    };

    // Gables: the cross-section, extruded across the wall thickness.
    const section = new Shape();
    section.moveTo(-d / 2, 0);
    section.lineTo(d / 2, 0);
    section.lineTo(d / 2, h);
    section.lineTo(0, h + rise);
    section.lineTo(-d / 2, h);
    section.closePath();
    for (const side of [1, -1]) {
      const gable = new ExtrudeGeometry(section, { depth: wall, bevelEnabled: false });
      gable.rotateY(Math.PI / 2);
      gable.translate(side > 0 ? w / 2 - wall : -w / 2, 0, 0);
      add(gable, "wall");
    }
    const longWall = (z: number) => {
      const g = new BoxGeometry(w - 2 * wall, h, wall);
      g.translate(0, h / 2, z);
      return add(g, "wall");
    };
    longWall(-d / 2 + wall / 2);
    const front = longWall(d / 2 - wall / 2);
    const floor = new BoxGeometry(w - 2 * wall, ctx.metres(0.05), d - 2 * wall);
    floor.translate(0, ctx.metres(0.025), 0);
    add(floor, "floor");

    // Two roof slabs, each lying on the gable line with an overhang at the eave.
    const thickness = ctx.metres(0.15);
    const overhang = ctx.metres(0.4);
    const slope = d / 2 / Math.cos(pitch);
    const slab = new BoxGeometry(w + 2 * overhang, thickness, slope + overhang);
    geometries.push(slab);
    let frontRoof: Mesh | null = null;
    for (const side of [1, -1]) {
      const roof = new Mesh(slab, ctx.palette.material("roof"));
      roof.rotation.x = side * pitch;
      // Midpoint of the slope, lifted by half the thickness, shifted towards the eave.
      const down = overhang / 2;
      roof.position.set(
        0,
        h + rise / 2 + (Math.cos(pitch) * thickness) / 2 - Math.sin(pitch) * down,
        side * (d / 4 + (Math.sin(pitch) * thickness) / 2 + Math.cos(pitch) * down),
      );
      group.add(roof);
      if (side > 0) frontRoof = roof;
    }

    return {
      object: group,
      reveal(mode: RevealMode) {
        const open = mode !== "none";
        front.visible = !open;
        frontRoof!.visible = !open;
      },
      dispose: () => geometries.forEach((g) => g.dispose()),
    };
  },
};
