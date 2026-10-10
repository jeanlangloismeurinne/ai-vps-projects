import { BoxGeometry, InstancedMesh, Matrix4 } from "three";
import type { ComponentPlugin } from "../../core/registry";

// Chips in a 3:2 grid in the board plane (x, z). The catalogue does not give the
// pitch: it is a display convention of five chip sides.
const PITCH_IN_CHIPS = 5;
const ASPECT = 1.5;

export const icChipGrid: ComponentPlugin = {
  id: "ic-chip-grid",
  create(params, ctx) {
    const p = params as { count: number; chipSize: number };
    const chip = ctx.metres(p.chipSize);
    const pitch = chip * PITCH_IN_CHIPS;
    const cols = Math.max(1, Math.ceil(Math.sqrt(p.count * ASPECT)));
    const rows = Math.ceil(p.count / cols);
    const geometry = new BoxGeometry(chip, chip * 0.2, chip);
    const mesh = new InstancedMesh(geometry, ctx.palette.material("chip"), p.count);
    const m = new Matrix4();
    for (let i = 0; i < p.count; i++) {
      const c = i % cols;
      const r = Math.floor(i / cols);
      mesh.setMatrixAt(i, m.makeTranslation((c - (cols - 1) / 2) * pitch, 0, (r - (rows - 1) / 2) * pitch));
    }
    mesh.computeBoundingSphere();
    mesh.computeBoundingBox();
    return { object: mesh, dispose: () => geometry.dispose() };
  },
};
