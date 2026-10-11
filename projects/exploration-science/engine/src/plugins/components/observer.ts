import { CapsuleGeometry, Group, Mesh, SphereGeometry, type BufferGeometry } from "three";
import type { ComponentPlugin } from "../../core/registry";

// A stylised person standing at the origin, face towards −Z, head tilted up to
// the sky. Proportions are the usual figure-drawing ones (head ≈ 1/7.5 of the height).
export const observer: ComponentPlugin = {
  id: "observer",
  create(params, ctx) {
    const h = ctx.metres((params as { height: number }).height);
    const geometries: BufferGeometry[] = [];
    const group = new Group();
    const add = (geometry: BufferGeometry, surface: Parameters<typeof ctx.palette.material>[0], x: number, y: number, z: number) => {
      geometries.push(geometry);
      const mesh = new Mesh(geometry, ctx.palette.material(surface));
      mesh.position.set(x, y, z);
      group.add(mesh);
      return mesh;
    };
    const head = h / 7.5;
    // Legs, body, arms.
    const legR = h * 0.045;
    add(new CapsuleGeometry(legR, h * 0.45 - 2 * legR, 4, 10), "plastic-dark", -h * 0.06, h * 0.225 + legR * 0.2, 0);
    add(new CapsuleGeometry(legR, h * 0.45 - 2 * legR, 4, 10), "plastic-dark", h * 0.06, h * 0.225 + legR * 0.2, 0);
    const bodyR = h * 0.11;
    add(new CapsuleGeometry(bodyR, h * 0.32 - 2 * bodyR, 4, 12), "accent", 0, h * 0.62, 0);
    const armR = h * 0.035;
    for (const side of [-1, 1]) {
      const arm = add(new CapsuleGeometry(armR, h * 0.33, 4, 8), "accent", side * (bodyR + armR * 1.2), h * 0.6, 0);
      arm.rotation.z = side * 0.12;
    }
    // Head, looking up.
    const headMesh = add(new SphereGeometry(head / 2, 20, 14), "wall", 0, h - head / 2, 0);
    const nose = add(new SphereGeometry(head * 0.09, 8, 6), "wall", 0, 0, 0);
    headMesh.add(nose);
    nose.position.set(0, head * 0.18, -head * 0.45);
    return { object: group, dispose: () => geometries.forEach((g) => g.dispose()) };
  },
};
