import { BoxGeometry, CylinderGeometry, Group, Mesh, type BufferGeometry } from "three";
import type { ComponentPlugin } from "../../core/registry";
import type { Surface } from "../../core/style";

type Role = "modem" | "power" | "heater" | "generic";

// A board in the (x, z) plane, parts on its +y face. Parts are placed in
// fractions of the board so any size reads the same.
interface Part {
  shape: "box" | "cylinder";
  surface: Surface;
  x: number; // fraction of width, from the centre
  z: number; // fraction of depth
  size: number; // fraction of the shorter side
  height: number; // fraction of size
}

const PARTS: Record<Role, Part[]> = {
  modem: [
    { shape: "box", surface: "chip", x: -0.15, z: 0, size: 0.45, height: 0.12 },
    { shape: "box", surface: "chip", x: 0.28, z: -0.22, size: 0.2, height: 0.15 },
    { shape: "box", surface: "chip", x: 0.28, z: 0.22, size: 0.2, height: 0.15 },
    { shape: "box", surface: "metal", x: 0.45, z: 0, size: 0.12, height: 0.8 },
  ],
  power: [
    { shape: "cylinder", surface: "metal", x: -0.25, z: -0.15, size: 0.3, height: 0.9 },
    { shape: "cylinder", surface: "metal", x: -0.25, z: 0.22, size: 0.22, height: 1.1 },
    { shape: "box", surface: "plastic-dark", x: 0.12, z: 0, size: 0.35, height: 0.5 },
    { shape: "box", surface: "chip", x: 0.38, z: -0.2, size: 0.16, height: 0.15 },
  ],
  heater: [
    { shape: "box", surface: "copper", x: 0, z: -0.3, size: 0.9, height: 0.03 },
    { shape: "box", surface: "copper", x: 0, z: 0, size: 0.9, height: 0.03 },
    { shape: "box", surface: "copper", x: 0, z: 0.3, size: 0.9, height: 0.03 },
  ],
  generic: [
    { shape: "box", surface: "chip", x: -0.2, z: 0, size: 0.3, height: 0.15 },
    { shape: "box", surface: "chip", x: 0.25, z: 0, size: 0.2, height: 0.15 },
  ],
};

const BOARD_THICKNESS_M = 0.0016;

export const electronicsModule: ComponentPlugin = {
  id: "electronics-module",
  create(params, ctx) {
    const p = params as { role: Role; width: number; depth: number };
    const w = ctx.metres(p.width);
    const d = ctx.metres(p.depth);
    const boardT = ctx.metres(BOARD_THICKNESS_M);
    const short = Math.min(w, d);
    const geometries: BufferGeometry[] = [];
    const group = new Group();

    const board = new BoxGeometry(w, boardT, d);
    geometries.push(board);
    group.add(new Mesh(board, ctx.palette.material("circuit-board")));

    for (const part of PARTS[p.role]) {
      const size = part.size * short;
      const height = part.height * size;
      // A heater trace is a long strip across the board.
      const length = p.role === "heater" ? part.size * w : size;
      const geometry = part.shape === "box" ? new BoxGeometry(length, height, p.role === "heater" ? size * 0.08 : size) : new CylinderGeometry(size / 2, size / 2, height, 16);
      geometry.translate(part.x * w, boardT / 2 + height / 2, part.z * d);
      geometries.push(geometry);
      group.add(new Mesh(geometry, ctx.palette.material(part.surface)));
    }

    return { object: group, dispose: () => geometries.forEach((g) => g.dispose()) };
  },
};
