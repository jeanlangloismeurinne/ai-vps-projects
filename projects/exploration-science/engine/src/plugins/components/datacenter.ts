import { BoxGeometry, Group, Mesh, type BufferGeometry } from "three";
import type { ComponentPlugin } from "../../core/registry";

// Low windowless hall with a glazed band and rooftop cooling units. Origin at
// the ground centre; proportions follow the width.
export const datacenter: ComponentPlugin = {
  id: "datacenter",
  create(params, ctx) {
    const { width: w } = params as { width: number };
    const d = w * 0.6;
    const h = w * 0.3;
    const geometries: BufferGeometry[] = [];
    const group = new Group();

    const hall = new BoxGeometry(w, h, d);
    hall.translate(0, h / 2, 0);
    geometries.push(hall);
    group.add(new Mesh(hall, ctx.palette.material("wall")));

    const band = new BoxGeometry(w * 1.002, h * 0.12, d * 1.002);
    band.translate(0, h * 0.75, 0);
    geometries.push(band);
    group.add(new Mesh(band, ctx.palette.material("glass")));

    const unit = new BoxGeometry(w * 0.12, h * 0.15, d * 0.18);
    geometries.push(unit);
    for (let i = 0; i < 6; i++) {
      const m = new Mesh(unit, ctx.palette.material("metal"));
      m.position.set(((i % 3) - 1) * w * 0.28, h + h * 0.075, (Math.floor(i / 3) - 0.5) * d * 0.4);
      group.add(m);
    }

    return { object: group, dispose: () => geometries.forEach((g) => g.dispose()) };
  },
};
