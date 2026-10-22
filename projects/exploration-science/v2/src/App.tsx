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
import { blendPose, clonePose, easeInOut, frameInWindow, poseGap, poseOf, positionOf, viewDirection, type Pose, type Rect } from "./camera";
import { Card, dockFor } from "./Card";
import { mainIds, render, swatch, system, texts, tour as tourFile, type Shot } from "./content/data";
import { debug, exposeRenderer } from "./debug";
import { Beam, explosion, LayerLabels, prepareDetail, useExplosion, type DetailModel } from "./Detail";
import { FlowPulses } from "./Flows";
import { connectionPath, flowPath, Polyline, type FlowLike, type LinkShape } from "./links";
import { MODELS_BASE, type Manifest } from "./manifest";
import { back, closerShot, current, enter, initialNav, orbit, select, zoom, type Entry, type NavRules } from "./nav";
import { coveredShare } from "./overlap";
import { Subtitle, TourButton } from "./Subtitle";
import { stepNav, timeline, type StepLike } from "./tour";

const FOV = render.limits.fovDeg;
const rules = render as unknown as NavRules;

// View requested by the URL (captures, and later navigation): `?shot=object:house`,
// `&silhouette` for the silhouette sheet (the framed objects alone, flat, no links),
// `&select=<id>` to open a card, `&t=<seconds>` to pin the flows' phase (and the camera then
// jumps to its poses), `&step` to draw a frame only on `__xs.advance()`, transitions going
// by 1/30 s per frame (frame-by-frame capture of a transition).
const params = new URLSearchParams(window.location.search);
const SHOT_KEY = params.get("shot") ?? "global";
const SILHOUETTE = params.has("silhouette");
const shots = render.shots as Record<string, Shot>;
if (!shots[SHOT_KEY]) throw new Error(`unknown shot: ${SHOT_KEY}`);
const SHOT = shots[SHOT_KEY]!;
const INITIAL_SELECTION = mainIds.includes(params.get("select") ?? "") ? params.get("select") : null;
const TIME = params.has("t") ? Number(params.get("t")) : null;
const STEP = params.has("step");
// Guided tour: played on arrival (bare URL), or from step `?tour=<i>`; with `t` pinned, that
// step is shown and held (captures).
const steps = tourFile.steps as StepLike[];
const entryText = (key: string) => (texts.entries as Record<string, string>)[key] ?? key;
const line = timeline(steps, entryText);
const TOUR_START = params.has("tour") ? Number(params.get("tour") || 0) : window.location.search === "" ? 0 : null;
const TOUR_KEY = "#tour";
/** Step on screen; `t0` (performance.now(), ms) is when the tour would have started to reach
 * it on time, so that steps keep their pace even after a slow frame. */
type Tour = { index: number; auto: boolean; t0: number };
const tourAt = (index: number, auto: boolean): Tour => ({ index, auto, t0: performance.now() - line.starts[index]! * 1000 });

export function App() {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tour, setTour] = useState<Tour | null>(() => (TOUR_START === null ? null : tourAt(TOUR_START, TIME === null && !STEP)));
  const [nav, setNav] = useState(() => (tour ? stepNav(rules, steps[tour.index]!) : initialNav(rules, SHOT_KEY, INITIAL_SELECTION)));
  // Part of the screen the card leaves free, for the card it was measured on.
  const [free, setFree] = useState<{ id: string; rect: Rect } | null>(null);
  const [viewport, setViewport] = useState({ width: window.innerWidth, height: window.innerHeight });
  const entry = current(nav);
  const selected = entry.selected;

  useEffect(() => {
    fetch(`${MODELS_BASE}/manifest.json`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`manifest: HTTP ${r.status}`))))
      .then(setManifest)
      .catch((e: Error) => setError(e.message));
    const resize = () => setViewport({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, []);

  const onSelect = useCallback((id: string | null) => setNav((n) => select(rules, n, id && mainIds.includes(id) ? id : null)), []);
  const onEnter = useCallback((id: string) => setNav((n) => enter(rules, n, id)), []);
  const onBack = useCallback(() => setNav(back), []);
  const onOrbit = useCallback((dAz: number, dEl: number) => setNav((n) => orbit(rules, n, dAz, dEl)), []);
  const onZoom = useCallback((factor: number) => setNav((n) => zoom(rules, n, factor)), []);
  const onFree = useCallback((id: string, rect: Rect) => setFree({ id, rect }), []);
  const deselect = useCallback(() => onSelect(null), [onSelect]);
  const onTourFree = useCallback((rect: Rect) => setFree({ id: TOUR_KEY, rect }), []);
  // Step and navigation change together: the subject is selected on the step's first frame.
  const startTour = useCallback((index = 0) => {
    setTour(tourAt(index, true));
    setNav(stepNav(rules, steps[index]!));
  }, []);
  const stopTour = useCallback(() => setTour(null), []);
  // The tour's clock starts once the scene is there: no step goes by on a blank screen.
  const [loaded, setLoaded] = useState(false);
  const onLoaded = useCallback(() => {
    setLoaded(true);
    setTour((t) => t && tourAt(t.index, t.auto));
  }, []);

  // Each step puts the navigation where it says, and lasts as long as its subtitle takes to
  // read; at the end the camera goes back to the whole system and the user has the hand.
  useEffect(() => {
    if (!tour?.auto || !loaded) return;
    const next = tour.index + 1;
    const timer = setTimeout(() => {
      if (next < steps.length) {
        setTour({ ...tour, index: next });
        setNav(stepNav(rules, steps[next]!));
      } else {
        setTour(null);
        setNav(initialNav(rules, "global", null));
      }
    }, tour.t0 + (line.starts[tour.index]! + line.durations[tour.index]!) * 1000 - performance.now());
    return () => clearTimeout(timer);
  }, [tour, loaded]);
  // Touching the scene (or the wheel, or a key) takes the hand back where the tour is.
  const touring = tour !== null;
  useEffect(() => {
    if (!touring) return;
    const take = (e: Event) => {
      if (!(e.target instanceof Element && e.target.closest(".tour"))) setTour(null);
    };
    window.addEventListener("pointerdown", take, true);
    window.addEventListener("wheel", take, true);
    return () => {
      window.removeEventListener("pointerdown", take, true);
      window.removeEventListener("wheel", take, true);
    };
  }, [touring]);

  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      if (touring) setTour(null);
      else onBack();
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [onBack, touring]);
  useEffect(() => {
    debug.selected = selected;
    debug.nav = { shot: entry.shot, depth: nav.stack.length, view: { ...entry.view } };
    debug.select = onSelect;
    debug.enter = onEnter;
    debug.back = onBack;
    debug.tour = tour ? { index: tour.index, step: steps[tour.index]!.id, playing: tour.auto } : null;
    debug.startTour = startTour;
    debug.timeline = () => steps.map((s, i) => ({ id: s.id, start: line.starts[i]!, duration: line.durations[i]! }));
  }, [nav, entry, selected, onSelect, onEnter, onBack, tour, startTour]);

  if (error) return <p className="fatal">{error}</p>;
  const closer = selected ? closerShot(rules, nav, selected) : null;
  const step = tour ? steps[tour.index]! : null;
  const freeRect = step ? (free?.id === TOUR_KEY ? free.rect : null) : selected && free?.id === selected ? free.rect : null;
  return (
    <>
      <Canvas
        // Always drawing, the flows being animated; on demand when their phase is pinned
        // (captures: software rendering would otherwise starve the browser).
        frameloop={TIME === null && !STEP ? "always" : "demand"}
        shadows={{ type: PCFShadowMap }}
        dpr={[1, 2]}
        gl={{ antialias: true, alpha: true, toneMapping: NeutralToneMapping }}
        camera={{ fov: FOV, near: 0.5, far: 400 }}
        onPointerMissed={deselect}
      >
        <Environment />
        <Suspense fallback={null}>
          {manifest && (
            <Scene
              manifest={manifest}
              entry={entry}
              onSelect={onSelect}
              onEnter={onEnter}
              onOrbit={onOrbit}
              onZoom={onZoom}
              free={freeRect}
              highlighted={step?.highlight ?? []}
              flowIds={step ? (step.flows ?? []) : null}
              onLoaded={onLoaded}
            />
          )}
        </Suspense>
      </Canvas>
      {step && !SILHOUETTE && (
        <Subtitle
          text={entryText(step.textKey)}
          index={tour!.index}
          count={steps.length}
          duration={tour!.auto && loaded ? line.durations[tour!.index]! : null}
          onSkip={stopTour}
          onFree={onTourFree}
        />
      )}
      {!step && !SILHOUETTE && TOUR_START !== null && <TourButton onPlay={() => startTour()} />}
      {selected && !step && !SILHOUETTE && (
        <Card
          id={selected}
          dock={dockFor(viewport.width, viewport.height)}
          depth={nav.stack.length}
          closer={closer ? (closer.startsWith("detail:") ? "detail" : "object") : null}
          onCloser={() => onEnter(selected)}
          onBack={onBack}
          onFree={onFree}
        />
      )}
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

interface SceneProps {
  manifest: Manifest;
  entry: Entry;
  onSelect: (id: string) => void;
  onEnter: (id: string) => void;
  onOrbit: (dOrbitDeg: number, dElevationDeg: number) => void;
  onZoom: (factor: number) => void;
  free: Rect | null;
  /** Objects a tour step puts forward (lightly, all at once). */
  highlighted: string[];
  /** Flows animated by a tour step; null outside the tour (all of them). */
  flowIds: string[] | null;
  /** Models in the scene and their shaders compiled. */
  onLoaded: () => void;
}

function Scene({ manifest, entry, onSelect, onEnter, onOrbit, onZoom, free, highlighted, flowIds, onLoaded }: SceneProps) {
  const selected = entry.selected;
  const ids = useMemo(() => Object.keys(manifest.assets), [manifest]);
  const urls = useMemo(() => ids.map((id) => `${MODELS_BASE}/${manifest.assets[id]!.representations.envelope.file}`), [ids, manifest]);
  // No Draco (its decoder would come from a CDN); meshopt decodes locally.
  const gltfs = useGLTF(urls, false, true);
  const detailIds = useMemo(() => ids.filter((id) => manifest.assets[id]!.representations.detail), [ids, manifest]);
  const detailGltfs = useGLTF(
    detailIds.map((id) => `${MODELS_BASE}/${manifest.assets[id]!.representations.detail!.file}`),
    false,
    true,
  );
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

  // Exploded views, placed like their envelope; the beam steers toward the far end of the
  // object's radio connection.
  const details = useMemo(() => {
    const out: Record<string, DetailModel> = {};
    detailIds.forEach((id, i) => {
      const root = detailGltfs[i]!.scene;
      const t = manifest.assets[id]!.transform;
      root.position.set(...t.position);
      root.rotation.set(0, MathUtils.degToRad(t.rotationYDeg), 0);
      root.traverse((o) => {
        const mesh = o as Mesh;
        if (mesh.isMesh) {
          mesh.castShadow = true;
          mesh.receiveShadow = true;
        }
      });
      const link = system.connections.find((c) => c.kind === "radio" && c.from.startsWith(`${id}#`));
      out[id] = prepareDetail(id, root, manifest.assets[id]!.representations.detail!, link ? anchorPosition(roots, link.to) : null);
    });
    return out;
  }, [detailGltfs, detailIds, manifest, roots]);
  // The exploded model in use: opening, open or closing (the envelope is hidden meanwhile).
  const detailId = entry.shot.startsWith("detail:") ? entry.shot.slice("detail:".length) : null;
  const [phase, setPhase] = useState<{ id: string; open: boolean } | null>(null);
  const shownId = detailId && details[detailId] ? detailId : (phase?.id ?? null);
  const onExplode = useCallback(
    (t: number) => setPhase((p) => (t === 0 ? null : p && p.id === shownId && p.open === (t === 1) ? p : { id: shownId!, open: t === 1 })),
    [shownId],
  );
  // Every shader compiled at load, not when its object first shows (a stall of seconds on a
  // slow GPU would freeze a flight and the tour): the exploded models, and what the scene
  // keeps mounted but hidden (beams, flows outside a tour step), made visible for the call
  // since compiling only sees visible objects.
  const { gl, camera, scene } = useThree();
  useEffect(() => {
    const hidden: Object3D[] = [];
    scene.traverse((o) => {
      if (!o.visible) {
        hidden.push(o);
        o.visible = true;
      }
    });
    const compiled = [gl.compileAsync(scene, camera), ...Object.values(details).map((d) => gl.compileAsync(d.root, camera, scene))];
    for (const o of hidden) o.visible = false;
    void Promise.all(compiled).then(onLoaded);
  }, [details, gl, camera, scene, onLoaded]);
  useExplosion(shownId ? details[shownId]! : null, !!detailId && detailId === shownId, onExplode, TIME !== null, STEP);
  useEffect(() => {
    for (const id of ids) roots[id]!.visible = id !== phase?.id;
  }, [ids, roots, phase]);

  const setting = useMemo(() => {
    const box = new Box3();
    for (const o of system.objects) if (o.role === "setting" && roots[o.id]) box.expandByObject(roots[o.id]!);
    return box;
  }, [roots]);

  const [hovered, setHovered] = useState<string | null>(null);
  useHighlight(roots, selected, hovered, highlighted);
  useEffect(() => {
    document.body.style.cursor = hovered ? "pointer" : "";
  }, [hovered]);

  useCameraRig(roots, details, free, entry);
  useGestures(onOrbit, onZoom);

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
                const tap = { x: e.nativeEvent.clientX, y: e.nativeEvent.clientY, t: performance.now() };
                if (e.delta > CLICK_SLOP || tap.t - gesture.endedAt < 250) return; // the end of a drag or pinch
                // A second tap at the same place goes one view closer on the object of the
                // first one (the camera may have moved under the finger in between).
                const last = gesture.lastTap;
                gesture.lastTap = { ...tap, id };
                if (last && tap.t - last.t < DOUBLE_TAP_MS && Math.hypot(tap.x - last.x, tap.y - last.y) < 24) {
                  gesture.lastTap = null;
                  onEnter(last.id);
                } else onSelect(id);
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
      {phase && (
        <primitive
          object={details[phase.id]!.root}
          onClick={(e: ThreeEvent<MouseEvent>) => {
            e.stopPropagation(); // the opened model is the selected object: a click keeps its card
            onSelect(phase.id);
          }}
        />
      )}
      {detailIds
        .filter((id) => details[id]!.beam)
        .map((id) => (
          <group key={`beam-${id}`} visible={!!phase?.open && phase.id === id}>
            <Beam detail={details[id]!} opacity={1} time={TIME} />
          </group>
        ))}
      {phase?.open && <LayerLabels detail={details[phase.id]!} />}
      {/* Hidden, not unmounted, in an exploded view: unmounting would dispose of their
          materials and recompile the shaders on the way in and out (a stall of seconds on
          a slow GPU). */}
      {!SILHOUETTE && <Links roots={roots} setting={setting} flowIds={flowIds} hidden={!!phase} />}
      {/* In a close view the object is the subject: no marker floating above it. */}
      {selected && roots[selected] && entry.shot === "global" && <SelectionPin root={roots[selected]!} />}
    </>
  );
}

/** Frames the current view (shot, plus the user's orbit and zoom) in the part of the screen
 * left free by the card. A change of shot or of free area is a flight (eased, ~1 s); a
 * gesture is followed closely (critically damped). The first pose is taken at once. */
function useCameraRig(roots: Record<string, Object3D>, details: Record<string, DetailModel>, free: Rect | null, entry: Entry) {
  const { camera, gl, scene, size, invalidate } = useThree();
  const goal = useRef<Pose | null>(null);
  const pose = useRef<Pose | null>(null);
  const flight = useRef<{ from: Pose; t: number; duration: number } | null>(null);
  const key = useRef("");
  const view = useRef("");
  const frames = useRef(0);

  useLayoutEffect(() => {
    const shot = shots[entry.shot]!;
    const points: Vector3[] = [];
    for (const id of shot.fit) {
      // A detail shot frames the opened model and its beam.
      if (entry.shot.startsWith("detail:") && details[id]) {
        points.push(...details[id]!.fit);
        continue;
      }
      const box = objectBox(roots[id]!);
      for (const x of [box.min.x, box.max.x]) for (const y of [box.min.y, box.max.y]) for (const z of [box.min.z, box.max.z]) points.push(new Vector3(x, y, z));
    }
    const area = free ?? { x: 0, y: 0, width: size.width, height: size.height };
    const [az, el] = [shot.azimuthDeg + entry.view.orbitDeg, entry.view.elevationDeg];
    goal.current = poseOf(frameInWindow(points, az, el, FOV, size.width, size.height, area, shot.margin ?? 0), az, el, entry.view.zoom);
    const k = `${entry.shot}|${area.x},${area.y},${area.width},${area.height}|${size.width}x${size.height}`;
    if (!pose.current) pose.current = clonePose(goal.current);
    else if (k !== key.current) {
      const shotChanged = !key.current.startsWith(`${entry.shot}|`);
      flight.current = { from: clonePose(pose.current), t: 0, duration: shotChanged ? 1.1 : 0.6 };
    } else if (JSON.stringify(entry.view) !== view.current) flight.current = null; // a gesture: follow it from where the camera is
    key.current = k;
    view.current = JSON.stringify(entry.view);
    debug.ready = false;
    frames.current = 0;
    invalidate();
    exposeRenderer(gl);
    debug.overlap = () => overlapOfCard(roots, camera, size.width, size.height);
    debug.pickPoint = (id) => pickPoint(roots, id, camera, scene, size.width, size.height);
    debug.advance = () => invalidate();
    debug.pose = () => {
      const p = pose.current!;
      return { position: positionOf(p).toArray(), target: p.target.toArray(), azimuthDeg: p.azimuthDeg, elevationDeg: p.elevationDeg, distance: p.distance, offset: [...p.offset] };
    };
  }, [roots, details, camera, gl, scene, size, free, entry, invalidate]);

  useFrame((_, delta) => {
    const g = goal.current;
    if (!g || !pose.current) return;
    // Pinned time (captures): the camera goes straight to its pose, software rendering being
    // too slow for a flight; with `&step`, the flight goes by fixed steps of 1/30 s.
    const dt = STEP ? 1 / 30 : Math.min(delta, 0.1);
    const f = flight.current;
    if (TIME !== null && !STEP) {
      flight.current = null;
      pose.current = clonePose(g);
    } else if (f) {
      f.t = Math.min(f.t + dt / f.duration, 1);
      pose.current = blendPose(f.from, g, easeInOut(f.t));
      if (f.t >= 1) {
        flight.current = null;
        pose.current = clonePose(g);
      }
    } else {
      pose.current = blendPose(pose.current, g, 1 - Math.exp(-dt * 14));
      if (poseGap(pose.current, g) < 0.25) pose.current = clonePose(g);
    }
    const p = pose.current;
    camera.position.copy(positionOf(p));
    camera.lookAt(p.target);
    (camera as PerspectiveCamera).setViewOffset(size.width, size.height, p.offset[0], p.offset[1], size.width, size.height);
    const settled = !flight.current && poseGap(p, g) === 0 && !explosion.busy;
    if (settled && ++frames.current >= 5) debug.ready = true;
    else if (!STEP) invalidate();
  });
}

/** Movement (CSS px) beyond which a press is a drag, not a click or tap. */
const CLICK_SLOP = 6;
const DOUBLE_TAP_MS = 400;
/** Orbit speed: dragging across the whole height of the screen turns the view by 120°. */
const DEG_PER_SCREEN = 120;
const gesture = { endedAt: -Infinity, lastTap: null as { x: number; y: number; t: number; id: string } | null };

/** One finger or the mouse drags to orbit; two fingers pinch, or the wheel turns, to zoom. */
function useGestures(onOrbit: (dOrbitDeg: number, dElevationDeg: number) => void, onZoom: (factor: number) => void) {
  const gl = useThree((s) => s.gl);
  useEffect(() => {
    const el = gl.domElement;
    const pointers = new Map<number, { x: number; y: number }>();
    let travel = 0;
    let active = false;
    const spread = () => {
      const [a, b] = [...pointers.values()];
      return Math.hypot(a!.x - b!.x, a!.y - b!.y);
    };
    const down = (e: PointerEvent) => {
      if (e.pointerType === "mouse" && e.button !== 0) return;
      pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
      travel = 0;
      active = pointers.size > 1;
    };
    const move = (e: PointerEvent) => {
      const p = pointers.get(e.pointerId);
      if (!p) return;
      const [dx, dy] = [e.clientX - p.x, e.clientY - p.y];
      if (pointers.size === 1) {
        travel += Math.hypot(dx, dy);
        if (travel > CLICK_SLOP) active = true;
        const k = DEG_PER_SCREEN / el.clientHeight;
        if (active) onOrbit(-dx * k, dy * k);
        p.x = e.clientX;
        p.y = e.clientY;
      } else if (pointers.size === 2) {
        const before = spread();
        p.x = e.clientX;
        p.y = e.clientY;
        const after = spread();
        if (before > 0 && after > 0) onZoom(before / after);
      }
    };
    const up = (e: PointerEvent) => {
      if (!pointers.delete(e.pointerId)) return;
      if (active) gesture.endedAt = performance.now();
      if (pointers.size === 0) active = false;
    };
    const wheel = (e: WheelEvent) => {
      e.preventDefault();
      onZoom(Math.exp(e.deltaY * 0.0015));
    };
    el.addEventListener("pointerdown", down);
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    window.addEventListener("pointercancel", up);
    el.addEventListener("wheel", wheel, { passive: false });
    return () => {
      el.removeEventListener("pointerdown", down);
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointercancel", up);
      el.removeEventListener("wheel", wheel);
    };
  }, [gl, onOrbit, onZoom]);
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
function useHighlight(roots: Record<string, Object3D>, selected: string | null, hovered: string | null, highlighted: string[]) {
  const invalidate = useThree((s) => s.invalidate);
  useEffect(() => {
    if (SILHOUETTE) return;
    const accent = new Color(swatch("signal"));
    for (const id of mainIds) {
      const level = id === selected ? 0.1 : id === hovered || highlighted.includes(id) ? 0.05 : 0;
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
  }, [roots, selected, hovered, highlighted.join(), invalidate]);
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
function Links({ roots, setting, flowIds, hidden }: { roots: Record<string, Object3D>; setting: Box3; flowIds: string[] | null; hidden: boolean }) {
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

  // A flow outside the tour step is hidden, not unmounted (its shader stays compiled).
  const flows = (system.flows ?? []).map((f) => {
    const { points, hidden } = flowPath(f as FlowLike, paths);
    const line = new Polyline(points, hidden);
    if (line.length <= 0) return null;
    return (
      <group key={`flow-${f.id}`} visible={!flowIds || flowIds.includes(f.id)}>
        <FlowPulses path={line} color={swatch("signal")} radius={0.05} time={TIME} />
      </group>
    );
  });

  // Points kept from one render to the next: drei's Line disposes of its material when its
  // points change, and the shader would be compiled again (a stall of seconds on a slow GPU).
  const arcs = useMemo(
    () =>
      system.objects
        .filter((o) => (o.placement as { airborne?: boolean } | undefined)?.airborne && roots[o.id])
        .map((o) => {
          const c = roots[o.id]!.position;
          const r = 30;
          const pts = Array.from({ length: 49 }, (_, i) => {
            const a = Math.PI / 2 + ((i - 24) / 24) * 0.42;
            return new Vector3(c.x + r * Math.cos(a), c.y - r + r * Math.sin(a), c.z);
          });
          return { id: o.id, pts };
        }),
    [roots],
  );
  const orbits = arcs.map(({ id, pts }) => (
    <Line key={`orbit-${id}`} points={pts} color={swatch("signal")} lineWidth={1.4} dashed dashSize={0.3} gapSize={0.25} transparent opacity={0.3} />
  ));
  return (
    <>
      <group visible={!hidden}>
        {drawn}
        {flows}
        {orbits}
      </group>
      {!hidden && labels}
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
