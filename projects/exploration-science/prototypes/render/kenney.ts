// Option C's neighbourhood: free (CC0) Kenney models for the decor, around the
// format's own parametric house and terminal. Models are fitted to a target size
// in metres, so they could be listed in a decor kit by role ("house", "tree"…).
import { Box3, Group, Mesh, MeshStandardMaterial, Vector3, type Object3D } from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { group, random, type Stage } from "./common";
import { addTreeLine, treeMaterials } from "./neighbourhood";

const models = import.meta.glob("./assets/kenney/*.glb", { query: "?url", import: "default", eager: true }) as Record<string, string>;
const colormap = (import.meta.glob("./assets/kenney/Textures/colormap.png", { query: "?url", import: "default", eager: true }) as Record<string, string>)[
  "./assets/kenney/Textures/colormap.png"
]!;

const loader = new GLTFLoader();
// Suburban models point at "Textures/colormap.png" next to them.
loader.manager.setURLModifier((url) => (url.endsWith("Textures/colormap.png") ? colormap : url));

const cache = new Map<string, Promise<Object3D>>();
function load(name: string): Promise<Object3D> {
  const url = models[`./assets/kenney/${name}.glb`];
  if (!url) throw new Error(`missing model ${name}`);
  let p = cache.get(name);
  if (!p) cache.set(name, (p = loader.loadAsync(url).then((g) => g.scene)));
  return p;
}

/** A copy of a model, scaled so its largest horizontal side (or its height) measures `metres`. */
async function place(name: string, metres: number, by: "width" | "height", at: [number, number, number], rotationY = 0): Promise<Object3D> {
  const model = (await load(name)).clone(true);
  const size = new Box3().setFromObject(model).getSize(new Vector3());
  model.scale.setScalar(metres / (by === "width" ? Math.max(size.x, size.z) : size.y));
  model.position.set(...at);
  model.rotation.y = rotationY;
  model.traverse((o) => {
    if (o instanceof Mesh) {
      o.castShadow = o.receiveShadow = true;
      const m = o.material as MeshStandardMaterial;
      if (m.map) m.map.anisotropy = 4;
    }
  });
  return model;
}

const HOUSES = ["building-type-a", "building-type-b", "building-type-c", "building-type-d", "building-type-e", "building-type-f", "building-type-g", "building-type-h", "building-type-k", "building-type-l"];
const TREES = ["tree_oak", "tree_default", "tree_detailed", "tree_fat", "tree-large", "tree-small"];

export async function addKenneyNeighbourhood(stage: Stage, plot: { streetZ: number }): Promise<void> {
  const rnd = random(42);
  const root: Group = group("kenney-neighbourhood");
  const jobs: Promise<Object3D>[] = [];
  let i = 0;
  for (const x of [-54, -36, -18, 18, 36, 54, 72, -72]) jobs.push(place(HOUSES[i++ % HOUSES.length]!, 11 + rnd() * 3, "width", [x, 0, 0], 0));
  for (const x of [-63, -45, -27, 27, 45, 63]) jobs.push(place(HOUSES[i++ % HOUSES.length]!, 11 + rnd() * 3, "width", [x, 0, plot.streetZ * 2], Math.PI));
  const trees: [number, number, number][] = [
    [-7, -9, 9], [9, -10, 8], [-11, 9, 7], [13, 10, 6], [-27, 9, 8], [27, -8, 9], [-45, -9, 7], [46, 9, 8], [0, plot.streetZ + 9, 7],
    [-18, plot.streetZ + 9, 8], [20, plot.streetZ + 9, 7], [-36, plot.streetZ - 9, 6], [36, plot.streetZ - 9, 7],
  ];
  trees.forEach(([x, z, h], k) => jobs.push(place(TREES[k % TREES.length]!, h, "height", [x, 0, z], rnd() * Math.PI * 2)));
  // Bushes along the hero plot, a fence at the back, the garden path.
  for (let z = -4; z <= 6; z += 2.5) {
    jobs.push(place("plant_bushLarge", 1.6, "width", [-8.5, 0, z], rnd() * 6));
    jobs.push(place("plant_bush", 1.3, "width", [8.5, 0, z], rnd() * 6));
  }
  for (let x = -7; x <= 7; x += 3.5) jobs.push(place("fence", 3.5, "width", [x, 0, -6.5], 0));
  jobs.push(place("planter", 1.4, "width", [2.5, 0, 5.2], 0));
  for (let z = 6; z < plot.streetZ - 5; z += 2) jobs.push(place("path-long", 2, "width", [0, 0.01, z], Math.PI / 2));
  root.add(...(await Promise.all(jobs)));
  stage.scene.add(root);
  addTreeLine(stage, rnd, treeMaterials());
}
