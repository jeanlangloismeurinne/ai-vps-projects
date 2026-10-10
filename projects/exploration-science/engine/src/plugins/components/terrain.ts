import { Mesh, PlaneGeometry } from "three";
import type { ComponentPlugin } from "../../core/registry";

export const terrain: ComponentPlugin = {
  id: "terrain",
  create(params, ctx) {
    const { size, surface } = params as { size: number; surface: "grass" | "concrete" | "sand" };
    const geometry = new PlaneGeometry(size, size);
    geometry.rotateX(-Math.PI / 2);
    const mesh = new Mesh(geometry, ctx.palette.material(`ground-${surface}`));
    return { object: mesh, dispose: () => geometry.dispose() };
  },
};
