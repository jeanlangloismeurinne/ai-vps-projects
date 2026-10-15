// Option B, "realistic": a photographed sky (CC0 Poly Haven panorama "Quarry 01")
// lights the scene and fills the background; ground, street and houses get
// physically based, textured materials; sun direction read from the photo.
// No photographed 3D decor (trees, houses) could be fetched from this
// environment: the neighbourhood is option A's layout with realistic materials.
import {
  CanvasTexture,
  Color,
  DirectionalLight,
  EquirectangularReflectionMapping,
  Mesh,
  MeshStandardMaterial,
  RepeatWrapping,
  Fog,
  SRGBColorSpace,
  Vector3,
  type Material,
} from "three";
import { HDRLoader } from "three/examples/jsm/loaders/HDRLoader.js";
import hdrUrl from "./assets/quarry_01_1k.hdr?url";
import { random, type Stage } from "./common";

/** Direction of the brightest pixel of an equirectangular HDR: the sun. */
export async function sunDirection(url = hdrUrl): Promise<Vector3> {
  const tex = await new HDRLoader().loadAsync(url);
  const { data, width, height } = tex.image as { data: ArrayLike<number>; width: number; height: number };
  const half = data instanceof Uint16Array;
  const f = (v: number) => (half ? halfToFloat(v) : v);
  let best = 0;
  let at = 0;
  for (let i = 0; i < width * height; i++) {
    const l = f(data[i * 4]!) + f(data[i * 4 + 1]!) + f(data[i * 4 + 2]!);
    if (l > best) [best, at] = [l, i];
  }
  // Inverse of three.js equirectUv: u = atan2(z, x) / 2π + 0.5, v = asin(y) / π + 0.5; rows run top-down.
  const u = ((at % width) + 0.5) / width;
  const lat = (0.5 - (Math.floor(at / width) + 0.5) / height) * Math.PI;
  const theta = (u - 0.5) * Math.PI * 2;
  return new Vector3(Math.cos(theta) * Math.cos(lat), Math.sin(lat), Math.sin(theta) * Math.cos(lat)).normalize();
}

function halfToFloat(h: number): number {
  const s = (h & 0x8000) >> 15;
  const e = (h & 0x7c00) >> 10;
  const m = h & 0x03ff;
  const v = e === 0 ? m / 1024 / 16384 : e === 31 ? Infinity : (1 + m / 1024) * 2 ** (e - 15);
  return s ? -v : v;
}

function canvasTexture(size: number, draw: (g: CanvasRenderingContext2D, s: number) => void, repeat: number): CanvasTexture {
  const c = document.createElement("canvas");
  c.width = c.height = size;
  draw(c.getContext("2d")!, size);
  const t = new CanvasTexture(c);
  t.wrapS = t.wrapT = RepeatWrapping;
  t.repeat.set(repeat, repeat);
  t.colorSpace = SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}

/** Rendered plaster and clay tiles, drawn procedurally (no texture file). */
export function houseMaterials(): { wall: Material; roof: Material } {
  const rnd = random(3);
  const plaster = canvasTexture(512, (g, s) => {
    g.fillStyle = "#e8dfd0";
    g.fillRect(0, 0, s, s);
    for (let i = 0; i < 9000; i++) {
      const l = 200 + rnd() * 40;
      g.fillStyle = `rgba(${l},${l - 8},${l - 22},0.25)`;
      g.fillRect(rnd() * s, rnd() * s, 2 + rnd() * 3, 2 + rnd() * 3);
    }
  }, 3);
  const tiles = canvasTexture(512, (g, s) => {
    g.fillStyle = "#4a231a"; // joints between tiles
    g.fillRect(0, 0, s, s);
    const rows = 16;
    const cols = 12;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const x = ((c + (r % 2) * 0.5) / cols) * s;
        const y = (r / rows) * s;
        const shade = 0.85 + rnd() * 0.25;
        const grad = g.createLinearGradient(0, y, 0, y + s / rows);
        grad.addColorStop(0, `rgb(${170 * shade},${80 * shade},${55 * shade})`);
        grad.addColorStop(1, `rgb(${110 * shade},${48 * shade},${35 * shade})`);
        g.fillStyle = grad;
        g.fillRect(x, y, s / cols - 2, s / rows - 1);
        if (x + s / cols > s) g.fillRect(x - s, y, s / cols - 2, s / rows - 1); // wrap the shifted row
      }
    }
  }, 7);
  return {
    wall: new MeshStandardMaterial({ map: plaster, roughness: 0.95, bumpMap: plaster, bumpScale: 0.6 }),
    roof: new MeshStandardMaterial({ map: tiles, roughness: 0.7, bumpMap: tiles, bumpScale: 1.2 }),
  };
}

/** Lawn: several greens at two scales, so the repeat does not show. */
function grassMaterial(): Material {
  const rnd = random(5);
  const grass = canvasTexture(512, (g, size) => {
    g.fillStyle = "#5f8a3c";
    g.fillRect(0, 0, size, size);
    for (let i = 0; i < 26000; i++) {
      const v = rnd();
      g.fillStyle = v < 0.33 ? "rgba(120,160,70,0.5)" : v < 0.66 ? "rgba(70,110,45,0.5)" : "rgba(150,170,90,0.35)";
      g.fillRect(rnd() * size, rnd() * size, 1 + rnd() * 2, 2 + rnd() * 5);
    }
  }, 220);
  return new MeshStandardMaterial({ map: grass, roughness: 1, bumpMap: grass, bumpScale: 0.8 });
}

export async function addPhotographedSky(stage: Stage): Promise<void> {
  const panorama = await new HDRLoader().loadAsync(hdrUrl);
  panorama.mapping = EquirectangularReflectionMapping;
  stage.scene.background = panorama;
  stage.scene.environment = panorama;
  stage.scene.environmentIntensity = 0.8;
  stage.scene.backgroundIntensity = 1;

  const sun = await sunDirection();
  const light = new DirectionalLight(new Color("#fff2df"), 3.4);
  light.position.copy(sun).multiplyScalar(200);
  light.castShadow = true;
  light.shadow.mapSize.set(4096, 4096);
  const cam = light.shadow.camera;
  cam.left = cam.bottom = -60;
  cam.right = cam.top = 60;
  cam.near = 10;
  cam.far = 500;
  light.shadow.bias = -0.0004;
  light.shadow.normalBias = 0.04;
  light.shadow.radius = 4;
  stage.scene.add(light, light.target);
  stage.scene.fog = new Fog(new Color("#c9d3d8"), 250, 2200);
}

/** Realistic materials where the flat palette was: lawn, hero house, neighbours (keeping their tints). */
export function realisticMaterials(stage: Stage, meadow: Mesh): void {
  const { wall, roof } = houseMaterials();
  const palette = stage.built.palette;
  const flat = new Map<Material, "wall" | "roof">([
    [palette.material("wall"), "wall"],
    [palette.material("roof"), "roof"],
  ]);
  const tinted = new Map<Material, Material>();
  meadow.material = grassMaterial();
  stage.scene.traverse((o) => {
    if (!(o instanceof Mesh) || Array.isArray(o.material)) return;
    const m = o.material as MeshStandardMaterial;
    const role = flat.get(m) ?? (m.userData.role as "wall" | "roof" | undefined);
    if (!role) return;
    let r = tinted.get(m);
    if (!r) {
      const base = (role === "wall" ? wall : roof) as MeshStandardMaterial;
      r = base.clone();
      // Keep each neighbour's colour, as a tint over the texture.
      if (!flat.has(m)) (r as MeshStandardMaterial).color.copy(m.color).multiplyScalar(role === "wall" ? 1.05 : 1.6);
      tinted.set(m, r);
    }
    o.material = r;
  });
}
