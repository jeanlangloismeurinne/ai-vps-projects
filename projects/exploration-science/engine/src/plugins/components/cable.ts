import { CatmullRomCurve3, Mesh, TubeGeometry, Vector3, type Object3D } from "three";
import type { ComponentPlugin } from "../../core/registry";

// Hangs between two entities' origins; `sag` is the dip as a fraction of the span.
export const cable: ComponentPlugin = {
  id: "cable",
  create(params, ctx) {
    const p = params as { from: string; to: string; sag: number };
    const mesh = new Mesh(undefined, ctx.palette.material("cable"));
    let geometry: TubeGeometry | null = null;
    return {
      object: mesh,
      resolve(entity) {
        const ends = [entity(p.from), entity(p.to)].filter((o): o is Object3D => o !== undefined);
        if (ends.length !== 2) throw new Error(`cable: unknown endpoint '${p.from}' or '${p.to}'`);
        const [a, b] = ends.map((o) => mesh.worldToLocal(o.getWorldPosition(new Vector3()))) as [Vector3, Vector3];
        const middle = a.clone().lerp(b, 0.5);
        middle.y -= a.distanceTo(b) * p.sag;
        geometry = new TubeGeometry(new CatmullRomCurve3([a, middle, b]), 48, ctx.metres(0.008), 6);
        mesh.geometry = geometry;
      },
      dispose: () => geometry?.dispose(),
    };
  },
};
