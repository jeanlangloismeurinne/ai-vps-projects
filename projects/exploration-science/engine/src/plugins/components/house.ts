import { BoxGeometry, ExtrudeGeometry, Group, MathUtils, Mesh, Shape, type BufferGeometry } from "three";
import type { ComponentPlugin } from "../../core/registry";

// Origin at the centre of the ground floor. The ridge runs along X (the facade
// width), the roof slopes down towards ±Z.
export const house: ComponentPlugin = {
  id: "house",
  create(params, ctx) {
    const p = params as { width: number; depth: number; wallHeight: number; roofPitchDeg: number };
    const w = ctx.metres(p.width);
    const d = ctx.metres(p.depth);
    const h = ctx.metres(p.wallHeight);
    const pitch = MathUtils.degToRad(p.roofPitchDeg);
    const rise = Math.tan(pitch) * (d / 2);
    const geometries: BufferGeometry[] = [];
    const group = new Group();

    // Walls and gables: the cross-section extruded along the ridge.
    const section = new Shape();
    section.moveTo(-d / 2, 0);
    section.lineTo(d / 2, 0);
    section.lineTo(d / 2, h);
    section.lineTo(0, h + rise);
    section.lineTo(-d / 2, h);
    section.closePath();
    const body = new ExtrudeGeometry(section, { depth: w, bevelEnabled: false });
    body.translate(0, 0, -w / 2);
    body.rotateY(Math.PI / 2);
    geometries.push(body);
    group.add(new Mesh(body, ctx.palette.material("wall")));

    // Two roof slabs, each lying on the gable line with an overhang at the eave.
    const thickness = ctx.metres(0.15);
    const overhang = ctx.metres(0.4);
    const slope = d / 2 / Math.cos(pitch);
    const slab = new BoxGeometry(w + 2 * overhang, thickness, slope + overhang);
    geometries.push(slab);
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
    }

    return { object: group, dispose: () => geometries.forEach((g) => g.dispose()) };
  },
};
