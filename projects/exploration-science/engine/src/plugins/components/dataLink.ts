import { BufferAttribute, BufferGeometry, Line, LineBasicMaterial, Vector3, type Object3D } from "three";
import type { ComponentPlugin } from "../../core/registry";

const MEDIUM_COLOURS: Record<string, string> = { fiber: "#3fd0ff", cable: "#d0d4da" };

// Straight path between two entities, kept up to date as they move (satellites).
export const dataLink: ComponentPlugin = {
  id: "data-link",
  create(params, ctx) {
    const p = params as { from: string; to: string; medium: string };
    const geometry = new BufferGeometry();
    const positions = new BufferAttribute(new Float32Array(6), 3);
    geometry.setAttribute("position", positions);
    const material = new LineBasicMaterial({ color: MEDIUM_COLOURS[p.medium] ?? ctx.palette.accent });
    const line = new Line(geometry, material);
    line.frustumCulled = false;
    let ends: [Object3D, Object3D] | null = null;
    const a = new Vector3();
    const b = new Vector3();
    const refresh = () => {
      if (!ends) return;
      line.worldToLocal(ends[0].getWorldPosition(a));
      line.worldToLocal(ends[1].getWorldPosition(b));
      positions.setXYZ(0, a.x, a.y, a.z);
      positions.setXYZ(1, b.x, b.y, b.z);
      positions.needsUpdate = true;
    };
    return {
      object: line,
      resolve(entity) {
        const from = entity(p.from);
        const to = entity(p.to);
        if (!from || !to) throw new Error(`data-link: unknown endpoint '${p.from}' or '${p.to}'`);
        ends = [from, to];
        refresh();
      },
      update: refresh,
      dispose() {
        geometry.dispose();
        material.dispose();
      },
    };
  },
};
