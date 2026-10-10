import { CylinderGeometry, Group, Mesh, MeshBasicMaterial, TorusGeometry, type BufferGeometry } from "three";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";
import type { ComponentPlugin } from "../../core/registry";

// Upright box standing on its base (origin at the bottom centre).
export const wifiRouter: ComponentPlugin = {
  id: "wifi-router",
  create(params, ctx) {
    const p = params as { height: number; showRadiation: boolean };
    const h = ctx.metres(p.height);
    const w = h * 0.55;
    const d = h * 0.35;
    const geometries: BufferGeometry[] = [];
    const group = new Group();

    const body = new RoundedBoxGeometry(w, h, d, 4, Math.min(w, d) * 0.2);
    body.translate(0, h / 2, 0);
    geometries.push(body);
    group.add(new Mesh(body, ctx.palette.material("plastic-light")));

    const led = new CylinderGeometry(d * 0.06, d * 0.06, d * 0.02, 12);
    led.rotateX(Math.PI / 2);
    led.translate(0, h * 0.15, d / 2);
    geometries.push(led);
    const ledMaterial = new MeshBasicMaterial({ color: ctx.palette.accent });
    group.add(new Mesh(led, ledMaterial));

    if (p.showRadiation) {
      for (const k of [1, 2, 3]) {
        const ring = new TorusGeometry(h * 0.35 * k, h * 0.01, 6, 48, Math.PI * 0.6);
        ring.rotateZ(Math.PI * 0.2);
        ring.translate(0, h, 0);
        geometries.push(ring);
        group.add(new Mesh(ring, ctx.palette.material("accent")));
      }
    }

    return {
      object: group,
      dispose() {
        geometries.forEach((g) => g.dispose());
        ledMaterial.dispose();
      },
    };
  },
};
