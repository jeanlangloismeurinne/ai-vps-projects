// Outdoor ingredients shared by options A and C: physical sky, haze, sun with
// soft shadows, a ground that is not one flat green, a street, drifting clouds.
import {
  BufferAttribute,
  Color,
  DirectionalLight,
  Fog,
  HemisphereLight,
  MathUtils,
  Mesh,
  MeshStandardMaterial,
  PlaneGeometry,
  PMREMGenerator,
  Scene,
  Sprite,
  SpriteMaterial,
  CanvasTexture,
  Vector3,
} from "three";
import { Sky } from "three/examples/jsm/objects/Sky.js";
import { group, random, type Stage } from "./common";

export const SUN = { elevationDeg: 34, azimuthDeg: 125 };
export const HORIZON = new Color("#cfdbe6");

export function addSkyAndLight(stage: Stage, shadowRadius = 60): Vector3 {
  const sky = new Sky();
  sky.scale.setScalar(8000);
  const u = sky.material.uniforms;
  u.turbidity!.value = 3.2;
  u.rayleigh!.value = 1.3;
  u.mieCoefficient!.value = 0.004;
  u.mieDirectionalG!.value = 0.82;
  const sun = new Vector3().setFromSphericalCoords(1, MathUtils.degToRad(90 - SUN.elevationDeg), MathUtils.degToRad(SUN.azimuthDeg));
  u.sunPosition!.value.copy(sun);
  stage.scene.add(sky);

  // Image-based lighting from the same sky, so every material picks up its colour.
  const pmrem = new PMREMGenerator(stage.renderer);
  const envScene = new Scene();
  envScene.add(sky.clone());
  stage.scene.environment = pmrem.fromScene(envScene, 0.02).texture;
  stage.scene.environmentIntensity = 0.35;
  stage.scene.fog = new Fog(HORIZON, 180, 2600);

  const light = new DirectionalLight("#fff1dc", 4.2);
  light.position.copy(sun).multiplyScalar(200);
  light.castShadow = true;
  light.shadow.mapSize.set(4096, 4096);
  const cam = light.shadow.camera;
  cam.left = cam.bottom = -shadowRadius;
  cam.right = cam.top = shadowRadius;
  cam.near = 10;
  cam.far = 500;
  light.shadow.bias = -0.0004;
  light.shadow.normalBias = 0.04;
  light.shadow.radius = 4;
  stage.scene.add(light, light.target, new HemisphereLight("#d7e7ff", "#5d6b3f", 0.35));
  return sun;
}

/** Shadows from every mesh of the built scene and of the decor. */
export function enableShadows(root: { traverse(cb: (o: unknown) => void): void }): void {
  root.traverse((o) => {
    if (o instanceof Mesh) {
      o.castShadow = true;
      o.receiveShadow = true;
    }
  });
}

/** A large meadow with low-frequency colour variation, mown lawns, a street with pavements. */
export function addGround(stage: Stage, plot: { streetZ: number }): Mesh {
  const size = 3000;
  const geo = new PlaneGeometry(size, size, 120, 120);
  geo.rotateX(-Math.PI / 2);
  const pos = geo.attributes.position!;
  const colors = new Float32Array(pos.count * 3);
  const a = new Color("#6f9a4a");
  const b = new Color("#9db567");
  const c = new Color();
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const z = pos.getZ(i);
    const n = 0.5 + 0.25 * Math.sin(x * 0.013 + Math.cos(z * 0.011) * 2) + 0.25 * Math.sin(z * 0.021 + x * 0.007);
    c.copy(a).lerp(b, MathUtils.clamp(n, 0, 1));
    colors.set([c.r, c.g, c.b], i * 3);
  }
  geo.setAttribute("color", new BufferAttribute(colors, 3));
  const meadow = new Mesh(geo, new MeshStandardMaterial({ vertexColors: true, roughness: 1 }));
  meadow.receiveShadow = true;
  meadow.position.y = -0.02;

  const flat = (w: number, d: number, color: string, x: number, z: number, y = 0) => {
    const m = new Mesh(new PlaneGeometry(w, d).rotateX(-Math.PI / 2), new MeshStandardMaterial({ color, roughness: 0.95 }));
    m.position.set(x, y, z);
    m.receiveShadow = true;
    return m;
  };
  const street = group(
    "street",
    flat(600, 8, "#4a4d52", 0, plot.streetZ, 0.01),
    flat(600, 2.2, "#c9c5bd", 0, plot.streetZ - 5.1, 0.03),
    flat(600, 2.2, "#c9c5bd", 0, plot.streetZ + 5.1, 0.03),
  );
  // Dashed centre line.
  for (let x = -300; x < 300; x += 6) street.add(flat(3, 0.15, "#e9e6dc", x, plot.streetZ, 0.02));
  stage.scene.add(meadow, street);
  return meadow;
}

/** Soft cumulus drawn from overlapping puffs (no texture file). */
function cloudTexture(): CanvasTexture {
  const c = document.createElement("canvas");
  c.width = 512;
  c.height = 256;
  const g = c.getContext("2d")!;
  const rnd = random(11);
  for (let i = 0; i < 26; i++) {
    const x = 90 + rnd() * 330;
    const y = 150 - Math.sin(((x - 90) / 330) * Math.PI) * (40 + rnd() * 50);
    const r = 35 + rnd() * 45;
    const grad = g.createRadialGradient(x, y, 0, x, y, r);
    grad.addColorStop(0, "rgba(255,255,255,0.9)");
    grad.addColorStop(1, "rgba(255,255,255,0)");
    g.fillStyle = grad;
    g.beginPath();
    g.arc(x, y, r, 0, Math.PI * 2);
    g.fill();
  }
  return new CanvasTexture(c);
}

export function addClouds(stage: Stage, count = 14): void {
  const tex = cloudTexture();
  const rnd = random(7);
  const clouds = group("clouds");
  for (let i = 0; i < count; i++) {
    const mat = new SpriteMaterial({ map: tex, transparent: true, opacity: 0.8 + rnd() * 0.2, depthWrite: false, fog: false });
    const s = new Sprite(mat);
    const angle = rnd() * Math.PI * 2;
    const dist = 700 + rnd() * 1600;
    s.position.set(Math.cos(angle) * dist, 220 + rnd() * 320, Math.sin(angle) * dist);
    const w = 350 + rnd() * 500;
    s.scale.set(w, w * 0.45, 1);
    clouds.add(s);
  }
  stage.overlay.add(clouds);
  stage.tickers.push((dt) => (clouds.rotation.y += dt * 0.002));
}
