import { Color, Group, Mesh, MeshStandardMaterial, ShaderMaterial, SphereGeometry, AdditiveBlending, type BufferGeometry } from "three";
import type { ComponentPlugin } from "../../core/registry";

// A magnifying bubble with small molecules inside. The bubble is a magnifier:
// its inside is drawn at its own scale (BUBBLE_REAL_RADIUS_M across its radius),
// which the scale bar shows when the camera looks at it, and a simulator can draw
// waves in it at that scale. Display conventions (not physics): the molecules are
// enlarged far beyond that scale (a molecule is ~0.3 nm), and only `count` of
// them are shown (the real bubble would hold close to a billion); they jiggle
// slowly, for thermal motion. Element colours are the usual CPK ones.
export const BUBBLE_REAL_RADIUS_M = 2e-6;
const ATOM_RADIUS = 0.035; // displayed, as a fraction of the bubble radius
const BOND = 1.6; // distance between the two atoms, in atom radii
const FILL = 0.85; // molecules stay inside this fraction of the radius
const JIGGLE = 0.04; // amplitude of the thermal jiggle, as a fraction of the radius
const ELEMENT_COLOURS = { N: "#3050f8", O: "#ff0d0d" } as const;
type Species = "N2" | "O2" | "H2O" | "mixed-air";

/** Deterministic pseudo-random numbers (mulberry32): the same scene always looks the same. */
function random(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Molecule n of a mixed-air sample: one in five is O₂ (air is ~78 % N₂, ~21 % O₂). */
export const speciesOf = (species: Species, n: number): "N2" | "O2" | "H2O" => (species === "mixed-air" ? (n % 5 === 4 ? "O2" : "N2") : species);

const RIM_VERTEX = /* glsl */ `
varying vec3 vNormal;
varying vec3 vView;
void main() {
  vec4 world = modelViewMatrix * vec4(position, 1.0);
  vNormal = normalize(normalMatrix * normal);
  vView = normalize(-world.xyz);
  gl_Position = projectionMatrix * world;
}`;
const RIM_FRAGMENT = /* glsl */ `
uniform vec3 uColor;
varying vec3 vNormal;
varying vec3 vView;
void main() {
  float rim = pow(1.0 - abs(dot(normalize(vNormal), normalize(vView))), 3.0);
  gl_FragColor = vec4(uColor, 0.06 + 0.8 * rim);
}`;

export const moleculeCloud: ComponentPlugin = {
  id: "molecule-cloud",
  create(params, ctx) {
    const p = params as { species: Species; count: number; bubbleRadius: number };
    const R = p.bubbleRadius;
    const geometries: BufferGeometry[] = [];
    const group = new Group();

    const bubbleGeometry = new SphereGeometry(R, 48, 24);
    geometries.push(bubbleGeometry);
    const bubbleMaterial = new ShaderMaterial({
      uniforms: { uColor: { value: new Color().copy(ctx.palette.accent) } },
      vertexShader: RIM_VERTEX,
      fragmentShader: RIM_FRAGMENT,
      transparent: true,
      depthWrite: false,
      blending: AdditiveBlending,
    });
    const bubble = new Mesh(bubbleGeometry, bubbleMaterial);
    bubble.renderOrder = 12;
    group.add(bubble);

    const molecules = new Group();
    group.add(molecules);
    const atomGeometry = new SphereGeometry(R * ATOM_RADIUS, 16, 10);
    const hydrogenGeometry = new SphereGeometry(R * ATOM_RADIUS * 0.6, 12, 8);
    geometries.push(atomGeometry, hydrogenGeometry);
    const materials = {
      N: new MeshStandardMaterial({ color: ELEMENT_COLOURS.N, roughness: 0.35 }),
      O: new MeshStandardMaterial({ color: ELEMENT_COLOURS.O, roughness: 0.35 }),
      H: new MeshStandardMaterial({ color: "#f2f2f2", roughness: 0.35 }),
    };

    const rand = random(p.count * 7919 + p.species.length);
    const homes: { group: Group; x: number; y: number; z: number; phase: number }[] = [];
    const d = R * ATOM_RADIUS * BOND;
    for (let n = 0; n < p.count; n++) {
      const m = new Group();
      const kind = speciesOf(p.species, n);
      if (kind === "H2O") {
        m.add(new Mesh(atomGeometry, materials.O));
        for (const s of [-1, 1]) {
          const h = new Mesh(hydrogenGeometry, materials.H);
          h.position.set(s * d * 0.6, d * 0.45, 0);
          m.add(h);
        }
      } else {
        for (const s of [-1, 1]) {
          const atom = new Mesh(atomGeometry, kind === "N2" ? materials.N : materials.O);
          atom.position.x = (s * d) / 2;
          m.add(atom);
        }
      }
      // The first molecule sits at the centre: it is the one a simulator makes scatter.
      let x = 0;
      let y = 0;
      let z = 0;
      if (n > 0) {
        do {
          x = rand() * 2 - 1;
          y = rand() * 2 - 1;
          z = rand() * 2 - 1;
        } while (x * x + y * y + z * z > 1 || x * x + y * y + z * z < 0.04);
        x *= R * FILL;
        y *= R * FILL;
        z *= R * FILL;
      }
      m.position.set(x, y, z);
      m.rotation.set(rand() * Math.PI, rand() * Math.PI, 0);
      molecules.add(m);
      homes.push({ group: m, x, y, z, phase: rand() * Math.PI * 2 });
    }

    let time = 0;
    return {
      object: group,
      magnifier: { metersPerUnit: BUBBLE_REAL_RADIUS_M / R, radius: R },
      update(dt) {
        time += dt;
        homes.forEach((h, i) => {
          if (i === 0) return;
          const a = R * JIGGLE;
          h.group.position.set(h.x + a * Math.sin(time * 1.3 + h.phase), h.y + a * Math.sin(time * 1.1 + 2 * h.phase), h.z + a * Math.sin(time * 0.9 + 3 * h.phase));
          h.group.rotation.y += dt * 0.4;
        });
      },
      dispose() {
        geometries.forEach((g) => g.dispose());
        bubbleMaterial.dispose();
        Object.values(materials).forEach((m) => m.dispose());
      },
    };
  },
};
