import { BoxGeometry, CylinderGeometry, Group, InstancedMesh, Matrix4, Mesh, type BufferGeometry } from "three";
import type { ComponentPlugin } from "../../core/registry";

// Radiating elements laid out in the panel plane (x, z), facing +y. The catalogue
// gives the count and spacing, not the outline: elements fill a 3:2 rectangle,
// centred on the origin, row by row.
const ASPECT = 1.5;
const PATCH_FILL = 0.6; // patch size / spacing: leaves gaps through which the layers below show
const PATCH_THICKNESS_M = 0.0008;
// Display convention: the patches sit on an insulating sheet, one spacing wider than the lattice.
const SHEET_THICKNESS_M = 0.0015;

export function latticePositions(lattice: "square" | "hexagonal", count: number, spacing: number): [number, number][] {
  const rowPitch = lattice === "hexagonal" ? (spacing * Math.sqrt(3)) / 2 : spacing;
  const cols = Math.max(1, Math.ceil(Math.sqrt((count * ASPECT * rowPitch) / spacing)));
  const rows = Math.ceil(count / cols);
  const positions: [number, number][] = [];
  for (let r = 0; r < rows && positions.length < count; r++) {
    const offset = lattice === "hexagonal" && r % 2 === 1 ? spacing / 2 : 0;
    for (let c = 0; c < cols && positions.length < count; c++) {
      positions.push([(c - (cols - 1) / 2) * spacing + offset - (lattice === "hexagonal" ? spacing / 4 : 0), (r - (rows - 1) / 2) * rowPitch]);
    }
  }
  return positions;
}

export const antennaElementArray: ComponentPlugin = {
  id: "antenna-element-array",
  create(params, ctx) {
    const p = params as { lattice: "square" | "hexagonal"; count: number; spacing: number; elementShape: "square-patch" | "circular-patch" };
    const spacing = ctx.metres(p.spacing);
    const size = spacing * PATCH_FILL;
    const thickness = ctx.metres(PATCH_THICKNESS_M);
    const geometry: BufferGeometry =
      p.elementShape === "square-patch" ? new BoxGeometry(size, thickness, size) : new CylinderGeometry(size / 2, size / 2, thickness, 12);
    const positions = latticePositions(p.lattice, p.count, spacing);
    const mesh = new InstancedMesh(geometry, ctx.palette.material("copper"), positions.length);
    const m = new Matrix4();
    positions.forEach(([x, z], i) => mesh.setMatrixAt(i, m.makeTranslation(x, 0, z)));
    mesh.computeBoundingSphere();
    mesh.computeBoundingBox();
    const box = mesh.boundingBox!;
    const sheetThickness = ctx.metres(SHEET_THICKNESS_M);
    const sheetGeometry = new BoxGeometry(box.max.x - box.min.x + spacing, sheetThickness, box.max.z - box.min.z + spacing);
    sheetGeometry.translate(0, -thickness / 2 - sheetThickness / 2, 0);
    const sheet = new Mesh(sheetGeometry, ctx.palette.material("plastic-light"));
    const group = new Group();
    group.add(sheet, mesh);
    return {
      object: group,
      dispose: () => {
        geometry.dispose();
        sheetGeometry.dispose();
      },
    };
  },
};
