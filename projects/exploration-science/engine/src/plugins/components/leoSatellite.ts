import { BoxGeometry, CylinderGeometry, Group, Mesh, type BufferGeometry } from "three";
import type { ComponentPlugin } from "../../core/registry";

// Flat-pack bus with a single solar wing on a boom along +X. Origin at the bus centre.
export const leoSatellite: ComponentPlugin = {
  id: "leo-satellite",
  create(params, ctx) {
    const p = params as { busLength: number; solarSpan: number };
    const bus = ctx.metres(p.busLength);
    const span = ctx.metres(p.solarSpan);
    const geometries: BufferGeometry[] = [];
    const group = new Group();

    const body = new BoxGeometry(bus, bus * 0.12, bus * 0.6);
    geometries.push(body);
    group.add(new Mesh(body, ctx.palette.material("metal")));
    const antennas = new BoxGeometry(bus * 0.9, bus * 0.02, bus * 0.5);
    antennas.translate(0, -bus * 0.07, 0);
    geometries.push(antennas);
    group.add(new Mesh(antennas, ctx.palette.material("plastic-light")));

    if (span > 0) {
      const boomLength = bus * 0.4;
      const boom = new CylinderGeometry(bus * 0.02, bus * 0.02, boomLength, 8);
      boom.rotateZ(Math.PI / 2);
      boom.translate(bus / 2 + boomLength / 2, 0, 0);
      geometries.push(boom);
      group.add(new Mesh(boom, ctx.palette.material("metal")));
      const wing = new BoxGeometry(span, bus * 0.02, bus * 0.55);
      wing.translate(bus / 2 + boomLength + span / 2, 0, 0);
      geometries.push(wing);
      group.add(new Mesh(wing, ctx.palette.material("solar-cell")));
    }

    return { object: group, dispose: () => geometries.forEach((g) => g.dispose()) };
  },
};
