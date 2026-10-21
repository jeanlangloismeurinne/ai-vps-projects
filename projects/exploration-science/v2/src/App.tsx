import { Canvas, useFrame, useThree, type ThreeEvent } from "@react-three/fiber";
import { Html, Line, useGLTF } from "@react-three/drei";
import { Suspense, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  Box3,
  Color,
  MathUtils,
  Mesh as MeshObj,
  MeshBasicMaterial,
  NeutralToneMapping,
  PCFShadowMap,
  PMREMGenerator,
  Raycaster,
  SphereGeometry,
  Vector2,
  Vector3,
  type Camera,
  type DirectionalLight,
  type Mesh,
  type MeshStandardMaterial,
  type Object3D,
  type PerspectiveCamera,
  type Scene as Scene3,
} from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { frameInWindow, viewDirection, type Rect } from "./camera";
import { Card, dockFor } from "./Card";
import { mainIds, render, swatch, system, texts, type Shot } from "./content/data";
import { debug, exposeRenderer } from "./debug";
import { FlowPulses } from "./Flows";
import { connectionPath, flowPath, Polyline, type FlowLike, type LinkShape } from "./links";
import { MODELS_BASE, type Manifest } from "./manifest";
import { coveredShare } from "./overlap";

const FOV = render.limits.fovDeg;

// View requested by the URL (captures, and later navigation): `?shot=object:house`,
// `&silhouette` for the silhouette sheet (the framed objects alone, flat, no links),
// `&select=<id>` to open a card, `&t=<seconds>` to pin the flows' phase.
const params = new URLSearchParams(window.location.search);
const SHOT_KEY = params.get("shot") ?? "global";
const SILHOUETTE = params.has("silhouette");
const shots = render.shots as Record<string, Shot>;
if (!shots[SHOT_KEY]) throw new Error(`unknown shot: ${SHOT_KEY}`);
const SHOT = shots[SHOT_KEY]!;
const INITIAL_SELECTION = mainIds.includes(params.get("select") ?? "") ? params.get("select") : null;
const TIME = params.has("t") ? Number(params.get("t")) : null;

export function App() {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(INITIAL_SELECTION);
  const [free, setFree] = useState<Rect | null>(null);
  const [viewport, setViewport] = useState({ width: window.innerWidth, height: window.innerHeight });

  useEffect(() => {
    fetch(`${MODELS_BASE}/manifest.json`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`manifest: HTTP ${r.status}`))))
      .then(setManifest)
      .catch((e: Error) => setError(e.message));
    const resize = () => setViewport({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, []);

  const select = useCallback((id: string | null) => {
    setSelected((cur) => {
      if (cur !== id) setFree(null);
      return id;
    });
  }, []);
  const close = useCallback(() => select(null), [select]);
  useEffect(() => {
    debug.selected = selected;
    debug.select = (id) => select(id && mainIds.includes(id) ? id : null);
  }, [selected, select]);

  if (error) return <p className="fatal">{error}</p>;
  return (
    <>
      <Canvas
        // Always drawing, the flows being animated; on demand when their phase is pinned
        // (captures: software rendering would otherwise starve the browser).
        frameloop={TIME === null ? "always" : "demand"}
        shadows={{ type: PCFShadowMap }}
        dpr={[1, 2]}
        gl={{ antialias: true, alpha: true, toneMapping: NeutralToneMapping }}
        camera={{ fov: FOV, near: 0.5, far: 400 }}
        onPointerMissed={close}
      >
        <Environment />
        <Suspense fallback={null}>
          {manifest && <Scene manifest={manifest} selected={selected} onSelect={select} free={selected ? free : null} />}
        </Suspense>
      </Canvas>
      {selected && !SILHOUETTE && <Card id={selected} dock={dockFor(viewport.width, viewport.height)} onClose={close} onFree={setFree} />}
    </>
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

function Scene({ manifest, selected, onSelect, free }: { manifest: Manifest; selected: string | null; onSelect: (id: string) => void; free: Rect | null }) {
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
      if (!SILHOUETTE && mainIds.includes(id)) addHitProxy(root);
      out[id] = root;
    });
    return out;
  }, [gltfs, ids, manifest]);

  const setting = useMemo(() => {
    const box = new Box3();
    for (const o of system.objects) if (o.role === "setting" && roots[o.id]) box.expandByObject(roots[o.id]!);
    return box;
  }, [roots]);

  const [hovered, setHovered] = useState<string | null>(null);
  useHighlight(roots, selected, hovered);
  useEffect(() => {
    document.body.style.cursor = hovered ? "pointer" : "";
  }, [hovered]);

  useCameraRig(roots, free);

  const interactive = (id: string) => !SILHOUETTE && mainIds.includes(id);
  return (
    <>
      <Sun bounds={setting} />
      {ids
        .filter((id) => !SILHOUETTE || SHOT.fit.includes(id))
        .map((id) =>
          interactive(id) ? (
            <primitive
              key={id}
              object={roots[id]!}
              onClick={(e: ThreeEvent<MouseEvent>) => {
                e.stopPropagation();
                onSelect(id);
              }}
              onPointerOver={(e: ThreeEvent<PointerEvent>) => {
                e.stopPropagation();
                if (e.pointerType === "mouse") setHovered(id);
              }}
              onPointerOut={() => setHovered((h) => (h === id ? null : h))}
            />
          ) : (
            <primitive key={id} object={roots[id]!} />
          ),
        )}
      {!SILHOUETTE && <Links roots={roots} setting={setting} />}
      {selected && roots[selected] && <SelectionPin root={roots[selected]!} />}
    </>
  );
}

/** Frames the shot of the URL in the part of the screen left free by the card, and eases
 * the camera there when the card opens or closes (the first pose is taken at once). */
function useCameraRig(roots: Record<string, Object3D>, free: Rect | null) {
  const { camera, gl, scene, size, invalidate } = useThree();
  const goal = useRef<{ position: Vector3; target: Vector3; offset: [number, number] } | null>(null);
  const pose = useRef<{ position: Vector3; target: Vector3; offset: [number, number] } | null>(null);
  const frames = useRef(0);

  useLayoutEffect(() => {
    const points: Vector3[] = [];
    for (const id of SHOT.fit) {
      const box = objectBox(roots[id]!);
      for (const x of [box.min.x, box.max.x]) for (const y of [box.min.y, box.max.y]) for (const z of [box.min.z, box.max.z]) points.push(new Vector3(x, y, z));
    }
    const area = free ?? { x: 0, y: 0, width: size.width, height: size.height };
    goal.current = frameInWindow(points, SHOT.azimuthDeg, SHOT.elevationDeg, FOV, size.width, size.height, area, SHOT.margin ?? 0);
    if (!pose.current) pose.current = { position: goal.current.position.clone(), target: goal.current.target.clone(), offset: [...goal.current.offset] };
    debug.ready = false;
    frames.current = 0;
    invalidate();
    exposeRenderer(gl);
    debug.overlap = () => overlapOfCard(roots, camera, size.width, size.height);
    debug.pickPoint = (id) => pickPoint(roots, id, camera, scene, size.width, size.height);
  }, [roots, camera, gl, scene, size, free, invalidate]);

  useFrame((_, dt) => {
    const [g, p] = [goal.current, pose.current];
    if (!g || !p) return;
    // Critically damped approach, ~0.5 s; snaps when close.
    const k = TIME === null ? 1 - Math.exp(-dt * 9) : 1;
    p.position.lerp(g.position, k);
    p.target.lerp(g.target, k);
    p.offset[0] += (g.offset[0] - p.offset[0]) * k;
    p.offset[1] += (g.offset[1] - p.offset[1]) * k;
    const settled = p.position.distanceTo(g.position) < 1e-3 && Math.abs(p.offset[0] - g.offset[0]) + Math.abs(p.offset[1] - g.offset[1]) < 0.5;
    if (settled) {
      p.position.copy(g.position);
      p.target.copy(g.target);
      p.offset = [...g.offset];
    }
    camera.position.copy(p.position);
    camera.lookAt(p.target);
    (camera as PerspectiveCamera).setViewOffset(size.width, size.height, p.offset[0], p.offset[1], size.width, size.height);
    if (settled && ++frames.current >= 5) debug.ready = true;
    else invalidate();
  });
}

/** Tries points of the object's surface, from the middle of its bounding box outward,
 * until rays from the camera through that point and through points 3 px around it all hit
 * the object first: a point safely inside its silhouette (click coordinates are rounded). */
function pickPoint(roots: Record<string, Object3D>, id: string, camera: Camera, scene: Scene3, width: number, height: number) {
  const root = roots[id];
  if (!root) return null;
  const centre = objectBox(root).getCenter(new Vector3());
  const candidates: Vector3[] = [centre];
  root.traverse((o) => {
    const mesh = o as Mesh;
    if (!mesh.isMesh || mesh.name === HIT_PROXY) return;
    const pos = mesh.geometry.getAttribute("position");
    for (let i = 0; i < pos.count; i += Math.max(1, Math.floor(pos.count / 40))) candidates.push(new Vector3().fromBufferAttribute(pos, i).applyMatrix4(mesh.matrixWorld));
  });
  candidates.sort((a, b) => a.distanceTo(centre) - b.distanceTo(centre));
  const ray = new Raycaster();
  const hitsObject = (x: number, y: number) => {
    ray.setFromCamera(new Vector2((x / width) * 2 - 1, 1 - (y / height) * 2), camera);
    const hit = ray.intersectObjects(scene.children, true).find((h) => (h.object as Mesh).isMesh && h.object.visible);
    let o: Object3D | null = hit?.object ?? null;
    while (o && o !== root) o = o.parent;
    return o === root;
  };
  for (const p of candidates) {
    const ndc = p.clone().project(camera);
    if (Math.abs(ndc.x) > 0.95 || Math.abs(ndc.y) > 0.95) continue;
    const [x, y] = [Math.round(((ndc.x + 1) / 2) * width), Math.round(((1 - ndc.y) / 2) * height)];
    if ([[0, 0], [3, 0], [-3, 0], [0, 3], [0, -3]].every(([dx, dy]) => hitsObject(x + dx!, y + dy!))) return { x, y };
  }
  return null;
}

/** Share of each main object under the open card (debug, captures). */
function overlapOfCard(roots: Record<string, Object3D>, camera: Camera, width: number, height: number): Record<string, number> {
  const el = document.querySelector(".card");
  const out: Record<string, number> = {};
  if (!el) return out;
  const r = el.getBoundingClientRect();
  for (const id of mainIds) out[id] = coveredShare(roots[id]!, camera, width, height, { x: r.left, y: r.top, width: r.width, height: r.height });
  return out;
}

/** Selected object tinted with the signal accent, hovered one more lightly. Materials that
 * already glow (status lights) keep their own emission. */
function useHighlight(roots: Record<string, Object3D>, selected: string | null, hovered: string | null) {
  const invalidate = useThree((s) => s.invalidate);
  useEffect(() => {
    if (SILHOUETTE) return;
    const accent = new Color(swatch("signal"));
    for (const id of mainIds) {
      const level = id === selected ? 0.1 : id === hovered ? 0.05 : 0;
      roots[id]?.traverse((o) => {
        const mesh = o as Mesh;
        if (!mesh.isMesh) return;
        for (const m of [mesh.material].flat() as MeshStandardMaterial[]) {
          if (!m.emissive) continue;
          m.userData.baseEmissive ??= { color: m.emissive.clone(), intensity: m.emissiveIntensity };
          const base = m.userData.baseEmissive as { color: Color; intensity: number };
          if (base.color.getHex() !== 0 && base.intensity > 0) continue;
          if (level > 0) m.emissive.copy(accent);
          m.emissiveIntensity = level;
        }
      });
    }
    invalidate();
  }, [roots, selected, hovered, invalidate]);
}

const flat = new MeshBasicMaterial({ color: swatch("graphite") });

/** Smallest pick target of a main object, as a radius in metres: about 100 CSS px across in
 * the global view on an iPad, well above the 44 px of a comfortable tap. */
const MIN_HIT_RADIUS = 0.6;
const hitMaterial = new MeshBasicMaterial({ visible: false });
const HIT_PROXY = "hit-proxy";

/** World bounding box of what is drawn of an object (its hit proxy left out). */
function objectBox(root: Object3D): Box3 {
  const box = new Box3();
  root.updateMatrixWorld(true);
  root.traverse((o) => {
    const mesh = o as Mesh;
    if (!mesh.isMesh || mesh.name === HIT_PROXY) return;
    mesh.geometry.computeBoundingBox();
    box.union(mesh.geometry.boundingBox!.clone().applyMatrix4(mesh.matrixWorld));
  });
  return box;
}

/** A small object (the terminal on its roof) gets an invisible sphere around it, so that a
 * tap near it selects it rather than what lies behind. Not drawn, only ray-cast. */
function addHitProxy(root: Object3D) {
  if (root.getObjectByName(HIT_PROXY)) return;
  const box = objectBox(root);
  const half = box.getSize(new Vector3()).length() / 2;
  if (half >= MIN_HIT_RADIUS) return;
  const proxy = new MeshObj(new SphereGeometry(MIN_HIT_RADIUS, 16, 12), hitMaterial);
  proxy.name = HIT_PROXY;
  proxy.position.copy(root.worldToLocal(box.getCenter(new Vector3())));
  root.add(proxy);
}

/** Marker above the selected object, in the accent of the card's own mark. */
function SelectionPin({ root }: { root: Object3D }) {
  const box = objectBox(root);
  const top = new Vector3((box.min.x + box.max.x) / 2, box.max.y + 0.3, (box.min.z + box.max.z) / 2);
  return (
    <Html position={top} center zIndexRange={[10, 0]} className="selection-pin">
      <span />
    </Html>
  );
}

const anchorPosition = (roots: Record<string, Object3D>, ref: string): Vector3 | null => {
  const [id] = ref.split("#");
  const node = roots[id!]?.getObjectByName(ref);
  return node ? node.getWorldPosition(new Vector3()) : null;
};

type Style = { shape: LinkShape; color: string; width?: number };
const styles = render.linkStyles as Record<string, Style>;
const externals = new Set((system.externals ?? []).map((e) => e.id));

/** Connections of the system drawn in their render.json style, the flows running along
 * them, the labels of the endpoints outside the scene, and the arc of each orbit. */
function Links({ roots, setting }: { roots: Record<string, Object3D>; setting: Box3 }) {
  const paths = useMemo(() => {
    const out: Record<string, Vector3[] | null> = {};
    for (const c of system.connections) {
      const from = anchorPosition(roots, c.from);
      out[c.id] = from ? connectionPath(styles[c.kind]!.shape, from, anchorPosition(roots, c.to), setting) : null;
    }
    return out;
  }, [roots, setting]);

  const drawn = system.connections.map((c) => {
    const style = styles[c.kind]!;
    const color = swatch(style.color);
    const path = paths[c.id];
    if (!path) return null;
    if (style.shape === "beam-dashed") {
      return (
        <group key={c.id}>
          <Line points={path} color={color} lineWidth={7} transparent opacity={0.14} />
          <Line points={path} color={color} lineWidth={2.2} dashed dashSize={0.22} gapSize={0.14} />
        </group>
      );
    }
    return <Ribbon key={c.id} points={path} width={style.width ?? 0.04} color={color} />;
  });

  const labels = system.connections.flatMap((c) => {
    const path = paths[c.id];
    const ext = [c.to, c.from].map((e) => e.split("#")[0]!).find((id) => externals.has(id));
    if (!path || !ext) return [];
    const end = c.to.startsWith(`${ext}#`) ? path[path.length - 1]! : path[0]!;
    const text = (texts.entries as Record<string, string>)[`external.${ext}`] ?? ext;
    return [
      <Html key={`label-${c.id}`} position={end} center zIndexRange={[10, 0]} className="external-label">
        <span className="external-label__dot" aria-hidden="true" />
        {text}
      </Html>,
    ];
  });

  const flows = (system.flows ?? []).map((f) => {
    const { points, hidden } = flowPath(f as FlowLike, paths);
    const line = new Polyline(points, hidden);
    if (line.length <= 0) return null;
    return <FlowPulses key={`flow-${f.id}`} path={line} color={swatch("signal")} radius={0.05} time={TIME} />;
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
      {flows}
      {labels}
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
