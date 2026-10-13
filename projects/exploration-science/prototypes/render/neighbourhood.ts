// Option A's neighbourhood, entirely procedural: the house plugin itself with
// other parameters and tints, stylised trees, hedges. Everything here could be
// produced by a parametric "decor kit" the generator configures.
import {
  BoxGeometry,
  Color,
  CylinderGeometry,
  DynamicDrawUsage,
  Group,
  IcosahedronGeometry,
  InstancedMesh,
  Material,
  Matrix4,
  Mesh,
  MeshStandardMaterial,
  Quaternion,
  Vector3,
} from "three";
import { house } from "../../engine/src/plugins/components/house";
import { group, random, type Stage } from "./common";

const WALLS = ["#efe6d8", "#e6dccb", "#f3efe7", "#d9cbb5", "#e9e1d3", "#cfd6d9"];
const ROOFS = ["#9c4a35", "#7d4535", "#5d5a58", "#a65a3f", "#6b6f75", "#8a3f30"];
const LEAVES = ["#4f7a3a", "#5e8a40", "#3f6b35", "#6c9446"];

/** The format's house, re-tinted: same geometry family as the hero house. */
function neighbourHouse(stage: Stage, rnd: () => number, i: number): Group {
  const width = 8 + rnd() * 5;
  const instance = house.create(
    { width, depth: 7 + rnd() * 3, wallHeight: 2.6 + rnd() * 2.6, roofPitchDeg: 25 + rnd() * 15 },
    { palette: stage.built.palette, metres: (m: number) => m },
  );
  const tint = new Map<Material, Material>();
  instance.object.traverse((o) => {
    if (!(o instanceof Mesh) || Array.isArray(o.material)) return;
    let m = tint.get(o.material);
    if (!m) {
      const c = (o.material as MeshStandardMaterial).clone();
      const name = (o.material as MeshStandardMaterial).color.getHexString();
      if (name === new Color("#f1e9dc").getHexString()) {
        c.color.set(WALLS[i % WALLS.length]!);
        c.userData.role = "wall";
      }
      if (name === new Color("#a8553a").getHexString()) {
        c.color.set(ROOFS[(i * 3) % ROOFS.length]!);
        c.userData.role = "roof";
      }
      tint.set(o.material, (m = c));
    }
    o.material = m;
  });
  return group(`neighbour-${i}`, instance.object);
}

export function stylisedTree(rnd: () => number, height: number, materials: { trunk: Material; leaves: Material[] }): Group {
  const g = new Group();
  const trunkH = height * 0.4;
  const trunk = new Mesh(new CylinderGeometry(height * 0.025, height * 0.04, trunkH, 7), materials.trunk);
  trunk.position.y = trunkH / 2;
  g.add(trunk);
  const blobs = 3 + Math.floor(rnd() * 3);
  for (let i = 0; i < blobs; i++) {
    const r = height * (0.18 + rnd() * 0.12);
    const blob = new Mesh(new IcosahedronGeometry(r, 1), materials.leaves[Math.floor(rnd() * materials.leaves.length)]!);
    blob.position.set((rnd() - 0.5) * height * 0.3, trunkH + r * 0.6 + rnd() * height * 0.3, (rnd() - 0.5) * height * 0.3);
    blob.scale.y = 0.85;
    g.add(blob);
  }
  return g;
}

export function treeMaterials() {
  return {
    trunk: new MeshStandardMaterial({ color: "#6a4a33", roughness: 1 }),
    leaves: LEAVES.map((c) => new MeshStandardMaterial({ color: c, roughness: 0.9, flatShading: true })),
  };
}

/** Houses on both sides of the street, trees, hedges around the hero plot, a tree line on the horizon. */
export function addProceduralNeighbourhood(stage: Stage, plot: { streetZ: number }): void {
  const rnd = random(42);
  const root = group("neighbourhood");
  const lots: [number, number, number][] = [];
  for (const x of [-54, -36, -18, 18, 36, 54, 72, -72]) lots.push([x, 0, 0]);
  for (const x of [-63, -45, -27, 27, 45, 63]) lots.push([x, plot.streetZ * 2, Math.PI]);
  lots.forEach(([x, z, ry], i) => {
    const h = neighbourHouse(stage, rnd, i);
    h.position.set(x + (rnd() - 0.5) * 3, 0, z + (rnd() - 0.5) * 2);
    h.rotation.y = ry;
    root.add(h);
  });

  const mats = treeMaterials();
  const trees: [number, number, number][] = [
    [-7, -9, 9], [9, -10, 8], [-11, 9, 7], [13, 10, 6], [-27, 9, 8], [27, -8, 9], [-45, -9, 7], [46, 9, 8], [0, plot.streetZ + 9, 7],
    [-18, plot.streetZ + 9, 8], [20, plot.streetZ + 9, 7], [-36, plot.streetZ - 9, 6], [36, plot.streetZ - 9, 7],
  ];
  for (const [x, z, h] of trees) {
    const t = stylisedTree(rnd, h, mats);
    t.position.set(x, 0, z);
    root.add(t);
  }

  // Hedges around the hero plot, a garden path to the street.
  const hedgeMat = new MeshStandardMaterial({ color: "#3e6233", roughness: 1 });
  for (const [w, d, x, z] of [[0.8, 15, -8.5, 1.5], [0.8, 15, 8.5, 1.5], [17.8, 0.8, 0, -6]] as const) {
    const hedge = new Mesh(new BoxGeometry(w, 1.1, d), hedgeMat);
    hedge.position.set(x, 0.55, z);
    root.add(hedge);
  }
  const path = new Mesh(new BoxGeometry(1.4, 0.04, plot.streetZ - 9), new MeshStandardMaterial({ color: "#b9b2a6", roughness: 1 }));
  path.position.set(0, 0.02, 4 + (plot.streetZ - 9) / 2);
  root.add(path);
  stage.scene.add(root);
  addTreeLine(stage, rnd, mats);
}

/** Hundreds of trees on the horizon, instanced: two draw calls whatever their number. */
export function addTreeLine(stage: Stage, rnd: () => number, mats = treeMaterials(), count = 420): void {
  const canopy = new InstancedMesh(new IcosahedronGeometry(1, 1), mats.leaves[2]!, count);
  const trunks = new InstancedMesh(new CylinderGeometry(0.06, 0.1, 1, 6), mats.trunk, count);
  canopy.instanceMatrix.setUsage(DynamicDrawUsage);
  const m = new Matrix4();
  const q = new Quaternion();
  let n = 0;
  while (n < count) {
    const a = rnd() * Math.PI * 2;
    const r = 140 + rnd() * 450;
    const x = Math.cos(a) * r;
    const z = Math.sin(a) * r;
    const h = 8 + rnd() * 9;
    canopy.setMatrixAt(n, m.compose(new Vector3(x, h * 0.62, z), q, new Vector3(h * 0.33, h * 0.36, h * 0.33)));
    trunks.setMatrixAt(n, m.compose(new Vector3(x, h * 0.25, z), q, new Vector3(h * 0.4, h * 0.5, h * 0.4)));
    n++;
  }
  canopy.castShadow = trunks.castShadow = false;
  stage.scene.add(canopy, trunks);
}
