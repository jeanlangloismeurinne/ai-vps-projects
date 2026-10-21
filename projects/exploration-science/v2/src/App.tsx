import { Canvas, useThree } from "@react-three/fiber";
import { Line, useGLTF } from "@react-three/drei";
import { Suspense, useEffect, useLayoutEffect, useMemo, useState } from "react";
import {
  Box3,
  MathUtils,
  MeshBasicMaterial,
  NeutralToneMapping,
  PCFShadowMap,
  PMREMGenerator,
  Vector3,
  type DirectionalLight,
  type Mesh,
  type Object3D,
} from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { frame, viewDirection } from "./camera";
import { render, swatch, system, type Shot } from "./content/data";
import { exposeDebug } from "./debug";
import { MODELS_BASE, type Manifest } from "./manifest";

const FOV = render.limits.fovDeg;

// View requested by the URL (captures, and later navigation): `?shot=object:house`, and
// `&silhouette` for the silhouette sheet (the framed objects alone, flat, no links).
const params = new URLSearchParams(window.location.search);
const SHOT_KEY = params.get("shot") ?? "global";
const SILHOUETTE = params.has("silhouette");
const shots = render.shots as Record<string, Shot>;
if (!shots[SHOT_KEY]) throw new Error(`unknown shot: ${SHOT_KEY}`);
const SHOT = shots[SHOT_KEY]!;

export function App() {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${MODELS_BASE}/manifest.json`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`manifest: HTTP ${r.status}`))))
      .then(setManifest)
      .catch((e: Error) => setError(e.message));
  }, []);

  if (error) return <p className="fatal">{error}</p>;
  return (
    <Canvas
      // Static scene for now: draw on change only (the flows of roadmap §4 will animate it).
      frameloop="demand"
      shadows={{ type: PCFShadowMap }}
      dpr={[1, 2]}
      gl={{ antialias: true, alpha: true, toneMapping: NeutralToneMapping }}
      camera={{ fov: FOV, near: 0.5, far: 400 }}
    >
      <Environment />
      <Suspense fallback={null}>{manifest && <Scene manifest={manifest} />}</Suspense>
    </Canvas>
  );
}

function Environment() {
  const { gl, scene } = useThree();
  useEffect(() => {
    // Local environment for metal and glass reflections: no remote HDRI (QUALITY_BAR §2).
    const pmrem = new PMREMGenerator(gl);
    const env = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    scene.environment = env;
    scene.environmentIntensity = 0.5;
    return () => {
      env.dispose();
      pmrem.dispose();
    };
  }, [gl, scene]);
  const { hemisphere } = render.lighting;
  return <hemisphereLight args={[swatch(hemisphere.sky), swatch(hemisphere.ground), hemisphere.intensity]} />;
}

/** The sun of render.json, its shadow camera fitted to the setting (the diorama plinth). */
function Sun({ bounds }: { bounds: Box3 }) {
  const { sun } = render.lighting;
  const [light, setLight] = useState<DirectionalLight | null>(null);
  const center = bounds.getCenter(new Vector3());
  const radius = bounds.getSize(new Vector3()).length() / 2;
  const position = center.clone().addScaledVector(viewDirection(sun.azimuthDeg, sun.elevationDeg), radius * 2);
  useLayoutEffect(() => {
    if (!light) return;
    light.target.position.copy(center);
    light.target.updateMatrixWorld();
    const cam = light.shadow.camera;
    [cam.left, cam.right, cam.top, cam.bottom] = [-radius, radius, radius, -radius];
    cam.near = radius * 0.5;
    cam.far = radius * 3.5;
    cam.updateProjectionMatrix();
  }, [light, center, radius]);
  return (
    <directionalLight
      ref={setLight}
      position={position}
      intensity={sun.intensity}
      castShadow
      shadow-mapSize={[2048, 2048]}
      shadow-radius={sun.shadowSoftness}
      shadow-blurSamples={16}
      shadow-bias={-0.0005}
      shadow-normalBias={0.02}
    />
  );
}

function Scene({ manifest }: { manifest: Manifest }) {
  const ids = useMemo(() => Object.keys(manifest.assets), [manifest]);
  const urls = useMemo(() => ids.map((id) => `${MODELS_BASE}/${manifest.assets[id]!.representations.envelope.file}`), [ids, manifest]);
  // No Draco (its decoder would come from a CDN); meshopt decodes locally.
  const gltfs = useGLTF(urls, false, true);
  const roots = useMemo(() => {
    const out: Record<string, Object3D> = {};
    ids.forEach((id, i) => {
      const root = gltfs[i]!.scene;
      const t = manifest.assets[id]!.transform;
      root.position.set(...t.position);
      root.rotation.set(0, MathUtils.degToRad(t.rotationYDeg), 0);
      root.updateMatrixWorld(true);
      root.traverse((o) => {
        const mesh = o as Mesh;
        if (mesh.isMesh) {
          mesh.castShadow = true;
          mesh.receiveShadow = true;
          if (SILHOUETTE) mesh.material = flat;
        }
      });
      out[id] = root;
    });
    return out;
  }, [gltfs, ids, manifest]);

  const setting = useMemo(() => {
    const box = new Box3();
    for (const o of system.objects) if (o.role === "setting" && roots[o.id]) box.expandByObject(roots[o.id]!);
    return box;
  }, [roots]);

  const { camera, gl, size, invalidate } = useThree();
  useLayoutEffect(() => {
    const shot = SHOT;
    const points: Vector3[] = [];
    for (const id of shot.fit) {
      const box = new Box3().expandByObject(roots[id]!);
      for (const x of [box.min.x, box.max.x]) for (const y of [box.min.y, box.max.y]) for (const z of [box.min.z, box.max.z]) points.push(new Vector3(x, y, z));
    }
    const f = frame(points, shot.azimuthDeg, shot.elevationDeg, FOV, size.width / size.height, shot.margin ?? 0);
    camera.position.copy(f.position);
    camera.lookAt(f.target);
    invalidate();
    exposeDebug(gl);
  }, [roots, camera, gl, size, invalidate]);

  return (
    <>
      <Sun bounds={setting} />
      {ids
        .filter((id) => !SILHOUETTE || SHOT.fit.includes(id))
        .map((id) => (
          <primitive key={id} object={roots[id]!} />
        ))}
      {!SILHOUETTE && <Links roots={roots} setting={setting} />}
    </>
  );
}

const flat = new MeshBasicMaterial({ color: swatch("graphite") });

const anchorPosition = (roots: Record<string, Object3D>, ref: string): Vector3 | null => {
  const [id] = ref.split("#");
  const node = roots[id!]?.getObjectByName(ref);
  return node ? node.getWorldPosition(new Vector3()) : null;
};

/** Connections of the system drawn in their render.json style; airborne objects get the
 * arc of their orbit. An endpoint outside the scene (`externals`) is reached by leaving
 * the setting by its nearest edge. */
function Links({ roots, setting }: { roots: Record<string, Object3D>; setting: Box3 }) {
  const styles = render.linkStyles as Record<string, { shape: string; color: string; width?: number }>;
  const drawn = system.connections.map((c) => {
    const style = styles[c.kind]!;
    const color = swatch(style.color);
    const from = anchorPosition(roots, c.from);
    let to = anchorPosition(roots, c.to);
    if (!from) return null;
    if (style.shape === "beam-dashed" && to) {
      return (
        <group key={c.id}>
          <Line points={[from, to]} color={color} lineWidth={7} transparent opacity={0.14} />
          <Line points={[from, to]} color={color} lineWidth={2.2} dashed dashSize={0.22} gapSize={0.14} />
        </group>
      );
    }
    // Ground line: along the ground to the target, or out of the setting for an external.
    const y = setting.max.y + 0.006;
    const start = new Vector3(from.x, y, from.z);
    const path = [start];
    if (!to) {
      const exits = [
        new Vector3(setting.min.x, y, from.z),
        new Vector3(setting.max.x, y, from.z),
        new Vector3(from.x, y, setting.min.z),
        new Vector3(from.x, y, setting.max.z),
      ];
      const edge = exits.reduce((a, b) => (a.distanceTo(start) < b.distanceTo(start) ? a : b));
      path.push(edge, new Vector3(edge.x, setting.min.y + 0.15, edge.z));
    } else {
      path.push(new Vector3(to.x, y, to.z));
    }
    return <Ribbon key={c.id} points={path} width={style.width ?? 0.04} color={color} />;
  });

  const orbits = system.objects
    .filter((o) => (o.placement as { airborne?: boolean } | undefined)?.airborne && roots[o.id])
    .map((o) => {
      const c = roots[o.id]!.position;
      const r = 30;
      const pts = Array.from({ length: 49 }, (_, i) => {
        const a = Math.PI / 2 + ((i - 24) / 24) * 0.42;
        return new Vector3(c.x + r * Math.cos(a), c.y - r + r * Math.sin(a), c.z);
      });
      return <Line key={`orbit-${o.id}`} points={pts} color={swatch("signal")} lineWidth={1.4} dashed dashSize={0.3} gapSize={0.25} transparent opacity={0.3} />;
    });
  return (
    <>
      {drawn}
      {orbits}
    </>
  );
}

/** A flat band of constant width through `points` (on the ground, then down the cut face). */
function Ribbon({ points, width, color }: { points: Vector3[]; width: number; color: string }) {
  return (
    <>
      {points.slice(1).map((b, i) => {
        const a = points[i]!;
        const mid = a.clone().add(b).multiplyScalar(0.5);
        const d = b.clone().sub(a);
        const vertical = Math.abs(d.y) > Math.abs(d.x) + Math.abs(d.z);
        const len = d.length();
        const yaw = Math.atan2(d.x, d.z);
        return (
          <mesh key={i} position={mid} rotation={[0, yaw, 0]}>
            <boxGeometry args={vertical ? [width, len, width * 0.5] : [width, width * 0.4, len + width]} />
            <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.35} roughness={0.5} />
          </mesh>
        );
      })}
    </>
  );
}
