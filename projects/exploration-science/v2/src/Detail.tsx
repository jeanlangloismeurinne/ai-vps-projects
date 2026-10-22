// Exploded views (`detail` representation): the layers of the model open when the detail
// shot is entered and close before the envelope comes back; the antenna's beam, computed by
// v2/src/beam.ts from the model's own array, rises from the opened array toward the satellite.
import { Html, Line } from "@react-three/drei";
import { useFrame, useThree } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import { AdditiveBlending, Box3, BufferAttribute, BufferGeometry, Color, DoubleSide, Matrix4, ShaderMaterial, Vector3, type Mesh, type Object3D } from "three";
import { lobeMesh, steer, type Frame, type PlanarArray, type Vec3 } from "./beam";
import { viewDirection } from "./camera";
import { render, swatch, texts } from "./content/data";
import type { Representation } from "./manifest";

/** Duration of the opening (and closing), seconds: the camera's flight to the detail shot. */
export const EXPLODE_SECONDS = 1.1;
/** Length of the drawn lobe, metres of the diorama (≈ 1.5 × the antenna's width). */
const LOBE_LENGTH = 0.75;

export interface DetailModel {
  id: string;
  root: Object3D;
  layers: { name: string; nodes: Object3D[]; offset: Vector3 }[];
  /** World box of the opened model, plus the lobe's tip: what the detail shot frames. */
  fit: Vector3[];
  labels: { name: string; position: Vector3 }[];
  beam: { frame: Matrix4; local: Vec3; world: Vector3; origin: Vector3; target: Vector3; geometry: BufferGeometry; wavelength: number } | null;
}

/** Shared with the camera rig: the page is not ready for a capture while a model opens. */
export const explosion = { busy: false };

const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);

/** Layers, framing points, labels and beam of an exploded model placed in the scene.
 * `target`: world position the antenna steers toward (the satellite's antenna). */
export function prepareDetail(id: string, root: Object3D, rep: Representation, target: Vector3 | null): DetailModel {
  root.updateMatrixWorld(true);
  const layers = Object.entries(rep.layers ?? {}).map(([name, offset]) => ({
    name,
    // three.js strips the dots from node names; the glTF name is kept in userData.name.
    nodes: root.children.filter((n) => String(n.userData.name ?? n.name).startsWith(`${id}.${name}.`)),
    offset: new Vector3(...offset),
  }));
  for (const l of layers) for (const n of l.nodes) n.userData.openPosition ??= n.position.clone();
  const box = new Box3().setFromObject(root);
  const fit = [box.min, box.max].flatMap((a) => [box.min, box.max].flatMap((b) => [box.min, box.max].map((c) => new Vector3(a.x, b.y, c.z))));

  // A label beside each moving layer, on the side that faces left in the detail shot.
  const shot = (render.shots as Record<string, { azimuthDeg: number; elevationDeg: number }>)[`detail:${id}`]!;
  const forward = viewDirection(shot.azimuthDeg, shot.elevationDeg).negate();
  const right = new Vector3().crossVectors(forward, new Vector3(0, 1, 0)).normalize();
  const labels = layers
    .filter((l) => `detail.${id}.${l.name}` in texts.entries)
    .map((l) => {
      // The layer's leftmost point on screen, among its vertices.
      let best: Vector3 | null = null;
      const p = new Vector3();
      for (const n of l.nodes) {
        n.traverse((o) => {
          const pos = (o as Mesh).geometry?.getAttribute("position");
          if (!pos) return;
          for (let i = 0; i < pos.count; i += 7) {
            p.fromBufferAttribute(pos, i).applyMatrix4(o.matrixWorld);
            if (!best || p.dot(right) < best.dot(right)) best = p.clone();
          }
        });
      }
      return { name: l.name, position: (best ?? new Vector3()).addScaledVector(right, -0.03) };
    });

  let beam: DetailModel["beam"] = null;
  const anchor = root.getObjectByName(`${id}#array`);
  if (anchor && rep.array && target) {
    const m = anchor.matrixWorld;
    const axis = (x: number, y: number, z: number) => new Vector3(x, y, z).transformDirection(m).toArray() as Vec3;
    // glTF frame of the anchor: Blender x → x, Blender y → −z, Blender z (the normal) → y.
    const frame: Frame = { e1: axis(1, 0, 0), e2: axis(0, 0, -1), n: axis(0, 1, 0) };
    const origin = anchor.getWorldPosition(new Vector3());
    const array: PlanarArray = rep.array;
    const s = steer(array, frame, target.clone().sub(origin).toArray() as Vec3);
    const { positions, indices } = lobeMesh(array, s.phases, s.local, LOBE_LENGTH);
    const geometry = new BufferGeometry();
    geometry.setAttribute("position", new BufferAttribute(positions, 3));
    geometry.setIndex(new BufferAttribute(indices, 1));
    const basis = new Matrix4().makeBasis(new Vector3(...frame.e1), new Vector3(...frame.e2), new Vector3(...frame.n)).setPosition(origin);
    const world = new Vector3(...s.world);
    fit.push(origin.clone().addScaledVector(world, LOBE_LENGTH));
    beam = { frame: basis, local: s.local, world, origin, target: target.clone(), geometry, wavelength: rep.array.pitch / rep.array.spacingOverLambda };
  }
  return { id, root, layers, fit, labels, beam };
}

/** Opens the model while `open`, closes it otherwise; reports how open it is (0 to 1) so the
 * scene can swap envelope and exploded model. `time` pinned (captures): no animation. */
export function useExplosion(detail: DetailModel | null, open: boolean, onChange: (t: number) => void, pinned: boolean, step: boolean) {
  const t = useRef(0);
  const invalidate = useThree((s) => s.invalidate);
  const apply = () => {
    if (!detail) return;
    const k = easeInOut(t.current) - 1;
    // Exported open: a node's own position (meshopt quantization puts an offset there) is
    // its opened place; closing takes the layer's offset off it.
    for (const l of detail.layers) for (const n of l.nodes) n.position.copy(n.userData.openPosition).addScaledVector(l.offset, k);
  };
  useFrame((_, delta) => {
    if (!detail) return;
    const goal = open ? 1 : 0;
    const before = t.current;
    if (pinned && !step) t.current = goal;
    else if (t.current !== goal) {
      const dt = step ? 1 / 30 : Math.min(delta, 0.1);
      t.current = goal > t.current ? Math.min(goal, t.current + dt / EXPLODE_SECONDS) : Math.max(goal, t.current - dt / EXPLODE_SECONDS);
    }
    explosion.busy = t.current !== goal;
    if (t.current !== before || (t.current > 0 && t.current < 1)) {
      apply();
      onChange(t.current);
      if (!step && explosion.busy) invalidate();
    }
  });
}

const beamVertex = /* glsl */ `
  varying vec3 vLocal;
  void main() {
    vLocal = position;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;
// Wavefronts: bands one wavelength apart, perpendicular to the beam, running outward.
const beamFragment = /* glsl */ `
  uniform vec3 uColor;
  uniform vec3 uBeam;
  uniform float uLambda;
  uniform float uLength;
  uniform float uPhase;
  uniform float uOpacity;
  varying vec3 vLocal;
  void main() {
    float along = dot(vLocal, uBeam);
    float band = 0.5 + 0.5 * cos(6.2831853 * (along / uLambda - uPhase));
    float fade = 1.0 - smoothstep(0.55, 1.0, along / uLength);
    gl_FragColor = vec4(uColor, uOpacity * fade * (0.18 + 0.32 * band));
  }
`;

/** The lobe of the beam, its wavefronts moving out, and a thin dashed guide toward the
 * satellite: the lobe found by the array factor lies along it. */
export function Beam({ detail, opacity, time }: { detail: DetailModel; opacity: number; time: number | null }) {
  const beam = detail.beam!;
  const material = useMemo(
    () =>
      new ShaderMaterial({
        vertexShader: beamVertex,
        fragmentShader: beamFragment,
        uniforms: {
          uColor: { value: new Color(swatch("signal")) },
          uBeam: { value: new Vector3(...beam.local) },
          uLambda: { value: beam.wavelength },
          uLength: { value: LOBE_LENGTH },
          uPhase: { value: 0 },
          uOpacity: { value: 0 },
        },
        transparent: true,
        depthWrite: false,
        side: DoubleSide,
        blending: AdditiveBlending,
      }),
    [beam],
  );
  // Waves leave the array at an illustrative 1.5 wavelengths per second (12 GHz is not drawable).
  useFrame(({ clock }) => {
    material.uniforms.uPhase!.value = 1.5 * (time ?? clock.elapsedTime);
    material.uniforms.uOpacity!.value = opacity;
  });
  const guide = useMemo(() => [beam.origin, beam.origin.clone().addScaledVector(beam.target.clone().sub(beam.origin).normalize(), LOBE_LENGTH * 2.2)], [beam]);
  return (
    <>
      <mesh geometry={beam.geometry} material={material} matrixAutoUpdate={false} matrix={beam.frame} renderOrder={4} />
      <Line points={guide} color={swatch("signal")} lineWidth={1.4} dashed dashSize={0.04} gapSize={0.03} transparent opacity={0.55 * opacity} />
    </>
  );
}

/** Names of the opened layers, beside them. */
export function LayerLabels({ detail }: { detail: DetailModel }) {
  const entries = texts.entries as Record<string, string>;
  return (
    <>
      {detail.labels.map((l) => (
        <Html key={l.name} position={l.position} zIndexRange={[10, 0]} className="layer-label" style={{ transform: "translate(-100%, -50%)" }}>
          {entries[`detail.${detail.id}.${l.name}`]}
          <span className="layer-label__tick" aria-hidden="true" />
        </Html>
      ))}
    </>
  );
}
