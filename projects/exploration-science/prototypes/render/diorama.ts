// Still mockup of the "miniature diorama" direction: the whole system on a small
// island seen from high above, the Earth's limb behind, glowing links, a tilt-shift
// lens. Everything here is procedural (terrain, water, forest, sky): no asset to
// fetch, so a generator only has to say where the objects of the system stand.
// Not to scale on purpose, like the format's own notToScale entities.
import {
  AdditiveBlending,
  BackSide,
  BufferAttribute,
  BufferGeometry,
  Color,
  ConeGeometry,
  CylinderGeometry,
  DataTexture,
  DirectionalLight,
  DodecahedronGeometry,
  Fog,
  HemisphereLight,
  IcosahedronGeometry,
  InstancedMesh,
  Line,
  LineDashedMaterial,
  MathUtils,
  Matrix4,
  Mesh,
  MeshBasicMaterial,
  MeshPhysicalMaterial,
  MeshStandardMaterial,
  Object3D,
  PlaneGeometry,
  PMREMGenerator,
  Quaternion,
  RepeatWrapping,
  Scene,
  ShaderMaterial,
  SphereGeometry,
  Vector2,
  Vector3,
  type Material,
} from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { ShaderPass } from "three/examples/jsm/postprocessing/ShaderPass.js";
import { UnrealBloomPass } from "three/examples/jsm/postprocessing/UnrealBloomPass.js";
import { HorizontalTiltShiftShader } from "three/examples/jsm/shaders/HorizontalTiltShiftShader.js";
import { VerticalTiltShiftShader } from "three/examples/jsm/shaders/VerticalTiltShiftShader.js";
import { createStage, entity, hide, random, run, type Stage } from "./common";
import { place } from "./kenney";
import { cameraLook, worldUVs } from "./mockups";
import { houseMaterials } from "./photo";

const SEA = -2.2;
const CENTRE = new Vector2(-65, -45);
/** Flat pads where the system's buildings stand: x, z, radius, level. */
const PADS: [number, number, number, number][] = [
  [0, 0, 15, 0],
  [-90, -60, 20, 0.3],
  [-130, -90, 22, 0.3],
];
const PEAKS: [number, number, number, number][] = [
  [-150, -185, 78, 75],
  [-60, -205, 60, 62],
  [-235, -100, 52, 58],
  [20, -150, 26, 45],
  [-205, -10, 22, 40],
];

// ---------- noise ----------
function hash(x: number, y: number): number {
  const s = Math.sin(x * 127.1 + y * 311.7) * 43758.5453;
  return s - Math.floor(s);
}
function noise(x: number, y: number): number {
  const xi = Math.floor(x);
  const yi = Math.floor(y);
  const xf = x - xi;
  const yf = y - yi;
  const u = xf * xf * (3 - 2 * xf);
  const v = yf * yf * (3 - 2 * yf);
  const a = hash(xi, yi);
  const b = hash(xi + 1, yi);
  const c = hash(xi, yi + 1);
  const d = hash(xi + 1, yi + 1);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}
function fbm(x: number, y: number, octaves = 5): number {
  let sum = 0;
  let amp = 0.5;
  let f = 1;
  for (let i = 0; i < octaves; i++) {
    sum += amp * noise(x * f, y * f);
    f *= 2.03;
    amp *= 0.5;
  }
  return sum;
}
/** 0 at `a`, 1 at `b` (either order), smooth in between. */
const smooth = (a: number, b: number, x: number) => (a < b ? MathUtils.smoothstep(x, a, b) : 1 - MathUtils.smoothstep(x, b, a));

/** Height of the island at (x, z): coastline, hills, mountains, flattened pads. */
export function height(x: number, z: number): number {
  const u = x - CENTRE.x;
  const v = z - CENTRE.y;
  const angle = Math.atan2(v, u);
  const coast = 150 + 30 * (fbm(Math.cos(angle) * 1.6 + 7, Math.sin(angle) * 1.6 + 3, 4) - 0.5) * 2 + (v < 0 ? 50 * smooth(0, -1, Math.sin(angle)) : 0);
  const r = Math.hypot(u, v * 1.1) / coast;
  const mask = smooth(1.04, 0.8, r);
  let land = 1.2 + 7 * fbm(x * 0.012, z * 0.012) * smooth(0.6, 1, 1 - r * 0.6);
  for (const [px, pz, ph, pr] of PEAKS) {
    const d = Math.hypot(x - px, z - pz) / pr;
    const ridge = 1 - Math.abs(fbm(x * 0.03 + 11, z * 0.03 + 5, 4) * 2 - 1);
    land += ph * Math.exp(-d * d * 1.6) * (0.65 + 0.55 * ridge);
  }
  let h = MathUtils.lerp(-16, land, mask);
  for (const [px, pz, pr, level] of PADS) {
    const d = Math.hypot(x - px, z - pz);
    h = MathUtils.lerp(level, h, smooth(pr, pr * 2.2, d));
  }
  return h;
}

function slopeAt(x: number, z: number): number {
  const e = 1.5;
  const dx = (height(x + e, z) - height(x - e, z)) / (2 * e);
  const dz = (height(x, z + e) - height(x, z - e)) / (2 * e);
  return Math.hypot(dx, dz);
}

/** Paths painted on the terrain: from the house to the gateway, round the coast. */
const PATHS: [number, number][][] = [
  [
    [0, 9],
    [-25, 15],
    [-55, -10],
    [-78, -48],
    [-90, -60],
  ],
  [
    [-90, -60],
    [-112, -78],
    [-130, -90],
  ],
];
function distanceToPaths(x: number, z: number): number {
  let best = Infinity;
  const p = new Vector2(x, z);
  const a = new Vector2();
  const b = new Vector2();
  for (const path of PATHS) {
    for (let i = 0; i + 1 < path.length; i++) {
      a.set(...path[i]!);
      b.set(...path[i + 1]!);
      const ab = b.clone().sub(a);
      const t = MathUtils.clamp(p.clone().sub(a).dot(ab) / ab.lengthSq(), 0, 1);
      best = Math.min(best, p.distanceTo(a.clone().addScaledVector(ab, t)));
    }
  }
  return best;
}

// ---------- terrain ----------
function terrain(): Mesh {
  const size = 760;
  const seg = 300;
  const geo = new PlaneGeometry(size, size, seg, seg).rotateX(-Math.PI / 2);
  geo.translate(CENTRE.x, 0, CENTRE.y);
  const pos = geo.attributes.position!;
  for (let i = 0; i < pos.count; i++) pos.setY(i, height(pos.getX(i), pos.getZ(i)));
  geo.computeVertexNormals();
  const nor = geo.attributes.normal!;
  const colors = new Float32Array(pos.count * 3);
  const c = new Color();
  const grassA = new Color("#4f8a34");
  const grassB = new Color("#8db04c");
  const forest = new Color("#2f5a26");
  const sand = new Color("#e2cf9c");
  const wetSand = new Color("#b49c6a");
  const rock = new Color("#7b7568");
  const rockLight = new Color("#a39c8d");
  const snow = new Color("#f4f7fb");
  const path = new Color("#c8b48a");
  const seabed = new Color("#0b2f55");
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const z = pos.getZ(i);
    const y = pos.getY(i);
    const steep = 1 - nor.getY(i);
    const n = fbm(x * 0.02 + 3, z * 0.02 + 9, 3);
    c.copy(grassA).lerp(grassB, MathUtils.clamp(n * 1.6 - 0.3, 0, 1));
    c.lerp(forest, MathUtils.clamp((forestDensity(x, z) - 0.3) * 1.5, 0, 0.8));
    c.lerp(rock, smooth(0.18, 0.4, steep));
    c.lerp(rockLight, smooth(14, 40, y) * 0.5);
    const snowLine = 46 + 16 * (n - 0.5);
    c.lerp(snow, smooth(snowLine, snowLine + 5, y) * (1 - smooth(0.35, 0.6, steep)));
    const pd = distanceToPaths(x, z);
    if (pd < 3.5) c.lerp(path, smooth(3.5, 1.5, pd) * 0.85);
    c.lerp(sand, smooth(SEA + 1.6, SEA + 0.7, y));
    if (y < SEA + 0.2) c.copy(wetSand).lerp(sand, MathUtils.clamp((y - SEA + 3) / 3, 0, 1));
    // The sea floor sinks into the colour of deep water, so the terrain's edge never shows through.
    if (y < SEA) c.lerp(seabed, smooth(1, 12, SEA - y));
    colors.set([c.r, c.g, c.b], i * 3);
  }
  geo.setAttribute("color", new BufferAttribute(colors, 3));
  const mesh = new Mesh(geo, new MeshStandardMaterial({ vertexColors: true, roughness: 0.95 }));
  mesh.receiveShadow = true;
  mesh.castShadow = true;
  mesh.name = "island";
  return mesh;
}

function forestDensity(x: number, z: number): number {
  return fbm(x * 0.009 + 21, z * 0.009 + 4, 4);
}

// ---------- water ----------
function waveNormals(): DataTexture {
  const n = 128;
  const data = new Uint8Array(n * n * 4);
  const h = (x: number, y: number) => fbm(x / 9, y / 9, 3) + 0.5 * fbm(x / 4 + 30, y / 4 + 10, 2);
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      const dx = h((x + 1) % n, y) - h((x - 1 + n) % n, y);
      const dy = h(x, (y + 1) % n) - h(x, (y - 1 + n) % n);
      const v = new Vector3(-dx * 2.5, -dy * 2.5, 1).normalize();
      const i = (y * n + x) * 4;
      data.set([(v.x * 0.5 + 0.5) * 255, (v.y * 0.5 + 0.5) * 255, (v.z * 0.5 + 0.5) * 255, 255], i);
    }
  }
  const t = new DataTexture(data, n, n);
  t.wrapS = t.wrapT = RepeatWrapping;
  t.repeat.set(36, 36);
  t.needsUpdate = true;
  return t;
}

/** Sea coloured by depth (turquoise shallows, foam on the shore, deep blue), transparent near the beach. */
function sea(radius: number): Mesh {
  const geo = new PlaneGeometry(radius * 2, radius * 2, 300, 300).rotateX(-Math.PI / 2);
  geo.translate(CENTRE.x, SEA, CENTRE.y);
  const pos = geo.attributes.position!;
  const colors = new Float32Array(pos.count * 4);
  const foam = new Color("#f2fbff");
  const shallow = new Color("#3cc6c4");
  const mid = new Color("#1679a8");
  const deep = new Color("#0a3566");
  const c = new Color();
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const z = pos.getZ(i);
    const depth = SEA - height(x, z);
    c.copy(deep).lerp(mid, smooth(16, 6, depth)).lerp(shallow, smooth(6, 1.2, depth));
    const f = smooth(0.9, 0.15, depth) * (0.7 + 0.3 * noise(x * 0.3, z * 0.3));
    c.lerp(foam, f);
    // Fades out at the rim, where the painted far ocean of the backdrop takes over.
    const rim = smooth(radius, radius * 0.7, Math.hypot(x - CENTRE.x, z - CENTRE.y));
    const alpha = (depth < 0 ? 0 : MathUtils.lerp(0.55, 1, smooth(0, 6, depth)) + f * 0.3) * rim;
    colors.set([c.r, c.g, c.b, Math.min(alpha, 1)], i * 4);
  }
  geo.setAttribute("color", new BufferAttribute(colors, 4));
  const mat = new MeshPhysicalMaterial({ vertexColors: true, transparent: true, roughness: 0.42, metalness: 0, normalMap: waveNormals(), normalScale: new Vector2(0.35, 0.35), depthWrite: false });
  const mesh = new Mesh(geo, mat);
  mesh.receiveShadow = true;
  mesh.renderOrder = 1;
  return mesh;
}

// ---------- sky and the Earth's limb ----------
const HAZE = new Color("#8fb7d8");
function backdrop(dip: number, sun: Vector3, sea = { height: 300, near: 1e6, far: 2e6 }): Mesh {
  const mat = new ShaderMaterial({
    side: BackSide,
    depthWrite: false,
    fog: false,
    uniforms: { dip: { value: dip }, haze: { value: HAZE }, sun: { value: sun }, seaColour: { value: new Color("#123257") }, seaFog: { value: new Vector3(sea.height, sea.near, sea.far) }, forward: { value: new Vector2(0, -1) }, curve: { value: 0 } },
    vertexShader: "varying vec3 vDir; void main(){ vDir = normalize((modelMatrix * vec4(position, 1.0)).xyz - cameraPosition); gl_Position = projectionMatrix * viewMatrix * modelMatrix * vec4(position, 1.0); gl_Position.z = gl_Position.w; }",
    fragmentShader: `
      uniform float dip; uniform vec3 seaColour; uniform vec3 seaFog; uniform vec3 haze; uniform vec3 sun; uniform vec2 forward; uniform float curve; varying vec3 vDir;
      float hash(vec3 p){ return fract(sin(dot(p, vec3(12.9898, 78.233, 37.719))) * 43758.5453); }
      void main(){
        vec3 d = normalize(vDir);
        // The limb drops away from the view direction: an exaggerated curvature, as in an illustration.
        float side = 1.0 - dot(normalize(d.xz), forward);
        float el = asin(clamp(d.y, -1.0, 1.0)) + dip + curve * side;   // 0 on the limb
        vec3 col;
        if (el < 0.0) {
          // The far ocean: the flat sea carried on past its rim, under the same fog.
          float reach = d.y < -0.001 ? seaFog.x / -d.y : 1e9;
          col = mix(seaColour, haze, clamp((reach - seaFog.y) / (seaFog.z - seaFog.y), 0.0, 1.0));   // linear, as three's Fog
          col = mix(col, haze * 0.95, smoothstep(0.06, 0.0, -el));
        } else {
          vec3 limb = vec3(0.95, 0.97, 1.0) * 1.3;
          vec3 blue = vec3(0.18, 0.42, 0.95);
          vec3 space = vec3(0.004, 0.012, 0.04);
          col = mix(limb, blue, smoothstep(0.0, 0.018, el));
          col = mix(col, space, smoothstep(0.015, 0.16, el));
          vec3 cell = floor(d * 420.0);
          float s = step(0.9975, hash(cell)) * smoothstep(0.08, 0.2, el);
          col += vec3(s) * (0.4 + 0.6 * hash(cell + 3.0));
        }
        gl_FragColor = vec4(col, 1.0);
      }`,
  });
  const m = new Mesh(new SphereGeometry(15000, 64, 32), mat);
  m.frustumCulled = false;
  m.renderOrder = -1;
  m.name = "backdrop";
  return m;
}

// ---------- forest and rocks ----------
function coloured(geo: BufferGeometry, color: string): BufferGeometry {
  const g = geo.index ? geo.toNonIndexed() : geo;
  const c = new Color(color);
  const a = new Float32Array(g.attributes.position!.count * 3);
  for (let i = 0; i < a.length; i += 3) a.set([c.r, c.g, c.b], i);
  g.setAttribute("color", new BufferAttribute(a, 3));
  g.deleteAttribute("uv");
  return g;
}
function conifer(): BufferGeometry {
  const parts = [coloured(new CylinderGeometry(0.12, 0.18, 1.2, 6).translate(0, 0.6, 0), "#5b3f2a")];
  [
    [1.0, 2.6, 1.9],
    [0.8, 2.2, 3.1],
    [0.55, 1.8, 4.2],
  ].forEach(([r, h, y]) => parts.push(coloured(new ConeGeometry(r!, h!, 7).translate(0, y!, 0), "#ffffff")));
  return mergeGeometries(parts).scale(1, 1 / 5.1, 1);
}
function broadleaf(): BufferGeometry {
  const parts = [coloured(new CylinderGeometry(0.1, 0.16, 1.4, 6).translate(0, 0.7, 0), "#6a4a30")];
  [
    [0, 2.3, 0, 1.15],
    [0.55, 2.0, 0.3, 0.8],
    [-0.45, 2.1, -0.35, 0.85],
    [0.1, 2.9, -0.1, 0.75],
  ].forEach(([x, y, z, r]) => parts.push(coloured(new IcosahedronGeometry(r!, 1).translate(x!, y!, z!), "#ffffff")));
  return mergeGeometries(parts).scale(1 / 1.6, 1 / 3.65, 1 / 1.6);
}

function forest(stage: Stage): void {
  const rnd = random(5);
  const spots: { x: number; z: number; y: number; kind: number }[] = [];
  for (let gx = -300; gx < 170; gx += 2.6) {
    for (let gz = -300; gz < 140; gz += 2.6) {
      const x = gx + (rnd() - 0.5) * 2.4;
      const z = gz + (rnd() - 0.5) * 2.4;
      const y = height(x, z);
      if (y < SEA + 1.4 || y > 36) continue;
      if (PADS.some(([px, pz, pr]) => Math.hypot(x - px, z - pz) < pr + 4)) continue;
      if (distanceToPaths(x, z) < 4) continue;
      const s = slopeAt(x, z);
      if (s > 0.9) continue;
      const d = forestDensity(x, z);
      const p = MathUtils.clamp((d - 0.38) * 3.2, 0, 1) * (y > 18 ? 0.8 : 1) + (rnd() < 0.015 ? 1 : 0);
      if (rnd() > p) continue;
      spots.push({ x, z, y, kind: y > 12 || s > 0.45 || rnd() < 0.35 ? 0 : 1 });
    }
  }
  const kinds = [
    { geo: conifer(), tints: ["#1f4d2b", "#2a5e33", "#305f2a", "#244a30"], h: [7, 12] },
    { geo: broadleaf(), tints: ["#3f7a2e", "#4f8a34", "#5f9536", "#3a6b2a", "#6b9a3a"], h: [5.5, 8.5] },
  ];
  const m = new Matrix4();
  const q = new Quaternion();
  const up = new Vector3(0, 1, 0);
  const tint = new Color();
  kinds.forEach((k, kind) => {
    const list = spots.filter((s) => s.kind === kind);
    const mesh = new InstancedMesh(k.geo, new MeshStandardMaterial({ vertexColors: true, roughness: 0.85, flatShading: true }), list.length);
    list.forEach((s, i) => {
      const h = MathUtils.lerp(k.h[0]!, k.h[1]!, rnd());
      q.setFromAxisAngle(up, rnd() * Math.PI * 2);
      m.compose(new Vector3(s.x, s.y - 0.2, s.z), q, new Vector3(h * (0.85 + rnd() * 0.3), h, h * (0.85 + rnd() * 0.3)));
      mesh.setMatrixAt(i, m);
      mesh.setColorAt(i, tint.set(k.tints[Math.floor(rnd() * k.tints.length)]!).offsetHSL(0, 0, (rnd() - 0.5) * 0.06));
    });
    mesh.castShadow = mesh.receiveShadow = true;
    stage.scene.add(mesh);
  });
  // Boulders on the slopes and along the shore.
  const rocks: Vector3[] = [];
  for (let i = 0; i < 3000 && rocks.length < 420; i++) {
    const x = -300 + rnd() * 470;
    const z = -300 + rnd() * 440;
    const y = height(x, z);
    if (y < SEA - 0.3 || y > 50) continue;
    if ((slopeAt(x, z) > 0.35 || Math.abs(y - SEA) < 0.8) && !PADS.some(([px, pz, pr]) => Math.hypot(x - px, z - pz) < pr + 3)) rocks.push(new Vector3(x, y, z));
  }
  const rockMesh = new InstancedMesh(new DodecahedronGeometry(1, 0), new MeshStandardMaterial({ color: "#8c867a", roughness: 0.9, flatShading: true }), rocks.length);
  rocks.forEach((p, i) => {
    const s = 0.6 + rnd() * 2.2;
    q.setFromAxisAngle(new Vector3(rnd(), rnd(), rnd()).normalize(), rnd() * 3);
    rockMesh.setMatrixAt(i, m.compose(p, q, new Vector3(s, s * 0.6, s * (0.8 + rnd() * 0.4))));
  });
  rockMesh.castShadow = rockMesh.receiveShadow = true;
  stage.scene.add(rockMesh);
}

// ---------- the system's links ----------
function glow(color: string, strength: number, opacity: number): Material {
  return new MeshBasicMaterial({ color: new Color(color).multiplyScalar(strength), transparent: true, opacity, blending: AdditiveBlending, depthWrite: false, fog: false, toneMapped: false });
}
function beamBetween(a: Vector3, b: Vector3, rA: number, rB: number, mat: Material): Mesh {
  const len = a.distanceTo(b);
  const geo = new CylinderGeometry(rB, rA, len, 20, 1, true).translate(0, len / 2, 0);
  const mesh = new Mesh(geo, mat);
  mesh.position.copy(a);
  mesh.quaternion.setFromUnitVectors(new Vector3(0, 1, 0), b.clone().sub(a).normalize());
  return mesh;
}
/** A radio link: a wide translucent cone and a bright core. */
function radioBeam(stage: Stage, from: Vector3, to: Vector3, spread: number): void {
  // Narrow where it leaves the antenna, wide at the satellite (the beam spreads with distance).
  stage.scene.add(beamBetween(from, to, 0.3, spread, glow("#3f9bff", 1.4, 0.16)), beamBetween(from, to, 0.08, 0.3, glow("#8fd0ff", 5, 0.9)));
}
function tubeAlong(points: Vector3[], radius: number, mat: Material): Object3D {
  const g = new Object3D();
  for (let i = 0; i + 1 < points.length; i++) g.add(beamBetween(points[i]!, points[i + 1]!, radius, radius, mat));
  return g;
}

function placeSatellite(stage: Stage, id: string, at: Vector3, scale: number): Vector3 {
  const node = entity(stage, id);
  node.position.copy(at);
  node.scale.setScalar(scale);
  node.rotation.set(0.2, 0.6, 0.1);
  return at;
}

function links(stage: Stage): void {
  const root = stage.built.root;
  root.updateMatrixWorld(true);
  const terminal = entity(stage, "terminal").getWorldPosition(new Vector3());
  const gateway = entity(stage, "gateway").getWorldPosition(new Vector3());
  const internet = entity(stage, "internet").getWorldPosition(new Vector3());
  const satA = placeSatellite(stage, "sat-a", new Vector3(-20, 250, -260), 6);
  const satB = placeSatellite(stage, "sat-b", new Vector3(-210, 265, -320), 6);
  const satC = placeSatellite(stage, "sat-c", new Vector3(170, 235, -300), 6);
  // Start just above the antenna, so the glow does not hide it.
  radioBeam(stage, terminal.clone().lerp(satA, 1.2 / terminal.distanceTo(satA)), satA, 7);
  radioBeam(stage, gateway.clone().add(new Vector3(0, 6, 0)), satB, 10);
  // Laser between satellites, and the orbit they follow (dashed).
  stage.scene.add(beamBetween(satA, satB, 0.35, 0.35, glow("#a6d8ff", 4, 0.8)));
  // The orbit they follow: a wide arc through the satellites, dipping towards the limb on both sides.
  const orbit: Vector3[] = [];
  for (let x = -700; x <= 600; x += 8) orbit.push(new Vector3(x, 262 - 0.00028 * (x + 40) ** 2, -300 - 0.04 * x));
  const dashed = new Line(new BufferGeometry().setFromPoints(orbit), new LineDashedMaterial({ color: new Color("#9fd2ff").multiplyScalar(3), dashSize: 6, gapSize: 5, transparent: true, opacity: 0.8, toneMapped: false, fog: false }));
  dashed.computeLineDistances();
  stage.scene.add(dashed);
  void satC;
  // Buried fibre from the gateway to the data centre, glowing along the ground.
  const fibre: Vector3[] = [];
  for (let t = 0; t <= 1.0001; t += 0.05) {
    const x = MathUtils.lerp(gateway.x, internet.x, t);
    const z = MathUtils.lerp(gateway.z, internet.z, t);
    fibre.push(new Vector3(x, height(x, z) + 0.4, z));
  }
  stage.scene.add(tubeAlong(fibre, 0.45, glow("#47e0ff", 5, 0.9)));
}

/** Warm lit windows, so the house reads as lived-in from far away. */
function windows(stage: Stage): void {
  // Plaster walls and slate roof, as in the reference illustration.
  (stage.built.palette.material("wall") as MeshStandardMaterial).color.set("#ece5d6");
  const { roof } = houseMaterials();
  (roof as MeshStandardMaterial).color.set("#7b8494");
  for (const t of [(roof as MeshStandardMaterial).map, (roof as MeshStandardMaterial).bumpMap]) t?.repeat.set(1, 1);
  const roofMat = stage.built.palette.material("roof");
  entity(stage, "house").traverse((o) => {
    if (o instanceof Mesh && o.material === roofMat) {
      worldUVs(o, 1.6);
      o.material = roof;
    }
  });
  const lit = new MeshStandardMaterial({ color: "#2a1d10", emissive: new Color("#ffb867"), emissiveIntensity: 1.1 });
  const frame = new MeshStandardMaterial({ color: "#3b3530", roughness: 0.6 });
  const house = entity(stage, "house");
  const add = (w: number, h: number, x: number, y: number, z: number, ry: number) => {
    const m = new Mesh(new PlaneGeometry(w, h), lit);
    m.position.set(x, y, z);
    m.rotation.y = ry;
    house.add(m);
    // Frame and glazing bars.
    for (const [bw, bh, bx, by] of [[w, 0.08, 0, 0], [0.08, h, 0, 0], [w + 0.1, 0.1, 0, h / 2], [w + 0.1, 0.1, 0, -h / 2], [0.1, h, -w / 2, 0], [0.1, h, w / 2, 0]] as const) {
      const bar = new Mesh(new PlaneGeometry(bw, bh), frame);
      bar.position.set(bx, by, 0.005);
      m.add(bar);
    }
  };
  for (const x of [-3, 0.2, 3.2]) add(1.6, 1.5, x, 1.5, 4.01, 0);
  add(2.4, 2.2, -0.2 + 0, 1.2, 4.011, 0);
  for (const z of [-2, 1.5]) add(1.4, 1.4, 5.01, 1.6, z, Math.PI / 2);
}

/** A garden round the house: hedges, a fence, planters (fence and planters are free Kenney models). */
async function garden(stage: Stage): Promise<void> {
  const rnd = random(9);
  const jobs: Promise<Object3D>[] = [];
  for (let x = -9; x <= 9; x += 3.6) jobs.push(place("fence", 3.6, "width", [x, 0, -8], 0));
  jobs.push(place("planter", 1.4, "width", [3, 0, 5.5], 0), place("planter", 1.4, "width", [-3.4, 0, 5.5], 0));
  stage.scene.add(...(await Promise.all(jobs)));
  const spots: Vector3[] = [];
  for (let z = -6.5; z <= 7; z += 1.3) spots.push(new Vector3(-9.5, 0, z), new Vector3(9.5, 0, z));
  const hedge = new InstancedMesh(broadleaf(), new MeshStandardMaterial({ vertexColors: true, roughness: 0.85, flatShading: true }), spots.length);
  const m = new Matrix4();
  const tint = new Color();
  spots.forEach((p, i) => {
    const s = 1.6 + rnd() * 0.5;
    hedge.setMatrixAt(i, m.compose(p.setY(-0.9), new Quaternion().setFromAxisAngle(new Vector3(0, 1, 0), rnd() * 6), new Vector3(s * 1.4, s, s * 1.4)));
    hedge.setColorAt(i, tint.set("#4d8a33").offsetHSL(0, 0, (rnd() - 0.5) * 0.08));
  });
  hedge.castShadow = hedge.receiveShadow = true;
  stage.scene.add(hedge);
}

// ---------- lens ----------
function tiltShift(stage: Stage, focus: number, amount: number): void {
  const w = stage.renderer.domElement.width;
  const h = stage.renderer.domElement.height;
  for (let pass = 0; pass < 2; pass++) {
    const hp = new ShaderPass(HorizontalTiltShiftShader);
    hp.uniforms.h!.value = amount / w;
    hp.uniforms.r!.value = focus;
    const vp = new ShaderPass(VerticalTiltShiftShader);
    vp.uniforms.v!.value = amount / h;
    vp.uniforms.r!.value = focus;
    stage.composer.addPass(hp);
    stage.composer.addPass(vp);
  }
}

// ---------- shots ----------
const SHOTS = {
  overview: { target: new Vector3(-62, 0, -70), azimuthDeg: 32, elevationDeg: 27, distance: 410, lookUp: 115, fov: 52, focus: 0.35, blur: 2.4 },
  house: { target: new Vector3(1, 2, 0), azimuthDeg: 28, elevationDeg: 34, distance: 21, lookUp: 1, fov: 40, focus: 0.45, blur: 3 },
} as const;

export async function diorama(app: HTMLElement, shotName: string, ready: () => void): Promise<void> {
  const shot = SHOTS[shotName as keyof typeof SHOTS] ?? SHOTS.overview;
  const stage = createStage(app, { ao: true, bloom: 0, exposure: 0.95, fov: shot.fov });
  hide(stage, ["ground"]);
  for (const id of ["link-user-a", "link-user-b", "link-feeder", "link-backbone"]) entity(stage, id).visible = false;

  // Camera first: the limb's dip depends on its height.
  const el = MathUtils.degToRad(shot.elevationDeg);
  const az = MathUtils.degToRad(shot.azimuthDeg);
  const off = new Vector3(Math.sin(az) * Math.cos(el), Math.sin(el), Math.cos(az) * Math.cos(el)).multiplyScalar(shot.distance);
  stage.camera.position.copy(shot.target).add(off);
  stage.camera.lookAt(shot.target.clone().add(new Vector3(0, shot.lookUp, 0)));
  stage.camera.near = Math.max(shot.distance * 0.01, 0.1);
  stage.camera.updateProjectionMatrix();
  const camHeight = stage.camera.position.y - SEA;
  const seaRadius = 1300;
  const dip = Math.atan(camHeight / (seaRadius + shot.distance)) * 0.85;

  const sun = new Vector3(-0.7, 0.6, 0.45).normalize();
  const fogNear = shot.distance + 250;
  const fogFar = seaRadius + shot.distance;
  const sky = backdrop(dip, sun, { height: camHeight, near: fogNear, far: fogFar });
  stage.scene.add(sky);
  const fwd = stage.camera.getWorldDirection(new Vector3());
  const skyUniforms = (sky.material as ShaderMaterial).uniforms;
  skyUniforms.forward!.value = new Vector2(fwd.x, fwd.z).normalize();
  skyUniforms.curve!.value = 0.75;
  stage.tickers.push(() => sky.position.copy(stage.camera.position));
  // Image-based light from the same sky, for reflections on the water and metal.
  const envScene = new Scene();
  envScene.add(backdrop(0.05, sun));
  const pmrem = new PMREMGenerator(stage.renderer);
  stage.scene.environment = pmrem.fromScene(envScene, 0, 1, 20000).texture;
  stage.scene.environmentIntensity = 0.55;
  stage.scene.fog = new Fog(HAZE, fogNear, fogFar);

  const light = new DirectionalLight("#ffe0b5", 3.4);
  const span = shotName === "house" ? 32 : 260;
  light.position.copy(shot.target).addScaledVector(sun, 600);
  light.target.position.copy(shot.target);
  light.castShadow = true;
  light.shadow.mapSize.set(4096, 4096);
  Object.assign(light.shadow.camera, { left: -span, right: span, top: span, bottom: -span, near: 100, far: 1200 });
  light.shadow.bias = -0.0005;
  light.shadow.normalBias = shotName === "house" ? 0.03 : 0.4;
  light.shadow.radius = 3;
  stage.scene.add(light, light.target, new HemisphereLight("#cfe3ff", "#4d5a3c", 0.55));

  stage.scene.add(terrain());
  if (!location.search.includes("nosea")) stage.scene.add(sea(seaRadius));
  forest(stage);
  windows(stage);
  await garden(stage);
  links(stage);
  stage.built.root.traverse((o) => {
    if (o instanceof Mesh) o.castShadow = o.receiveShadow = true;
  });

  // Bloom only on what is brighter than the lit scene (beams, windows), then the camera look, then tilt-shift.
  const passes = stage.composer.passes;
  const output = passes.pop()!;
  passes.push(new UnrealBloomPass(new Vector2(app.clientWidth, app.clientHeight), 0.9, 0.55, 1.1));
  passes.push(output);
  cameraLook(stage, {});
  tiltShift(stage, shot.focus, shot.blur);

  let frames = 0;
  run(stage, () => ++frames === 30 && ready());
}
