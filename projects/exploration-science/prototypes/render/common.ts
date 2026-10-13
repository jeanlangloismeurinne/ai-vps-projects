// Shared plumbing for the render prototypes: the real Starlink scene, built by
// the real engine core and plugins, in a renderer with post-processing. Each
// option only adds what surrounds it (sky, ground, neighbourhood, lighting).
import {
  ACESFilmicToneMapping,
  Group,
  MathUtils,
  PCFSoftShadowMap,
  PerspectiveCamera,
  Scene as ThreeScene,
  SRGBColorSpace,
  Vector2,
  Vector3,
  WebGLRenderer,
  type Object3D,
} from "three";
import { EffectComposer } from "three/examples/jsm/postprocessing/EffectComposer.js";
import { GTAOPass } from "three/examples/jsm/postprocessing/GTAOPass.js";
import { OutputPass } from "three/examples/jsm/postprocessing/OutputPass.js";
import { RenderPass } from "three/examples/jsm/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/examples/jsm/postprocessing/UnrealBloomPass.js";
import catalogueJson from "../../catalogue/catalogue.json";
import starlinkJson from "../../content/nodes/starlink-terminal/scene.json";
import type { Catalogue, Scene, Shot } from "../../engine/src/content/types";
import { orbitOffset, viewFromShot } from "../../engine/src/core/camera";
import { PluginRegistry } from "../../engine/src/core/registry";
import { buildScene, type BuiltScene } from "../../engine/src/core/sceneBuilder";
import { registerComponents } from "../../engine/src/plugins/components";

export const catalogue = catalogueJson as unknown as Catalogue;
export const starlink = starlinkJson as unknown as Scene;

export interface Stage {
  renderer: WebGLRenderer;
  scene: ThreeScene;
  camera: PerspectiveCamera;
  composer: EffectComposer;
  built: BuiltScene;
  /** Things that animate (clouds drifting, waves…), called every frame. */
  tickers: ((dt: number) => void)[];
  /** Drawn after ambient occlusion (clouds): transparent sprites confuse the AO pass. */
  overlay: ThreeScene;
}

export function createStage(container: HTMLElement, options: { ao?: boolean; bloom?: number; exposure?: number; fov?: number } = {}): Stage {
  const renderer = new WebGLRenderer({ antialias: true, powerPreference: "high-performance", preserveDrawingBuffer: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.outputColorSpace = SRGBColorSpace;
  renderer.toneMapping = ACESFilmicToneMapping;
  renderer.toneMappingExposure = options.exposure ?? 1;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = PCFSoftShadowMap;
  container.appendChild(renderer.domElement);

  const scene = new ThreeScene();
  const camera = new PerspectiveCamera(options.fov ?? 45, container.clientWidth / container.clientHeight, 0.05, 20000);
  const registry = new PluginRegistry();
  registerComponents(registry);
  const built = buildScene(starlink, catalogue, registry);
  scene.add(built.root);

  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  if (options.ao) {
    const ao = new GTAOPass(scene, camera, container.clientWidth, container.clientHeight);
    ao.updateGtaoMaterial({ radius: 1.2, distanceExponent: 1.5, thickness: 2, scale: 1.2 });
    ao.blendIntensity = 0.85;
    composer.addPass(ao);
  }
  const overlay = new ThreeScene();
  const overlayPass = new RenderPass(overlay, camera);
  overlayPass.clear = false;
  composer.addPass(overlayPass);
  if (options.bloom) composer.addPass(new UnrealBloomPass(new Vector2(container.clientWidth, container.clientHeight), options.bloom, 0.4, 0.92));
  composer.addPass(new OutputPass());
  return { renderer, scene, camera, composer, built, tickers: [], overlay };
}

export function entity(stage: Stage, id: string): Object3D {
  const e = stage.built.entities.get(id);
  if (!e) throw new Error(`no entity ${id}`);
  return e.node;
}

/** Hides what belongs to other steps or other scales (gateway, data centre, the format's own ground). */
export function hide(stage: Stage, ids: string[]): void {
  for (const id of ids) entity(stage, id).visible = false;
}

/**
 * Satellites far away in the sky, as seen from the roof: along one track, the
 * first one high, the next one following lower. `distance` is a display
 * distance (the real 480 km cannot be drawn), `scale` keeps them readable.
 */
export function placeSatellites(stage: Stage, track: { azimuthDeg: number; elevationsDeg: number[]; distance: number; scale: number }): void {
  const origin = entity(stage, "terminal").getWorldPosition(new Vector3());
  ["sat-a", "sat-b", "sat-c"].forEach((id, i) => {
    const node = entity(stage, id);
    const el = track.elevationsDeg[i];
    if (el === undefined) {
      node.visible = false;
      return;
    }
    const dir = new Vector3().setFromSphericalCoords(1, MathUtils.degToRad(90 - el), MathUtils.degToRad(track.azimuthDeg));
    node.position.copy(origin).addScaledVector(dir, track.distance);
    node.scale.setScalar(track.scale);
    node.lookAt(origin);
    node.rotateX(Math.PI / 2);
  });
  stage.built.root.updateMatrixWorld(true);
}

export function shoot(stage: Stage, shot: Shot): void {
  const target = stage.built.focusPoint(shot.target);
  stage.camera.position.copy(target).add(orbitOffset(viewFromShot(shot)));
  stage.camera.lookAt(target);
  stage.camera.near = Math.max(shot.distance * 0.01, 0.02);
  stage.camera.updateProjectionMatrix();
}

export function run(stage: Stage, onFrame?: () => void): void {
  let last = performance.now();
  stage.renderer.setAnimationLoop((now) => {
    const dt = Math.min((now - last) / 1000, 0.1);
    last = now;
    stage.built.update(dt);
    for (const t of stage.tickers) t(dt);
    stage.renderer.info.autoReset = false;
    stage.renderer.info.reset();
    stage.composer.render(dt);
    const r = stage.renderer.info.render;
    Object.assign(window, { protoStats: { triangles: r.triangles, calls: r.calls, textures: stage.renderer.info.memory.textures } });
    onFrame?.();
  });
}

/** Seeded random, so every capture of a prototype shows the same neighbourhood. */
export function random(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function group(name: string, ...children: Object3D[]): Group {
  const g = new Group();
  g.name = name;
  if (children.length) g.add(...children);
  return g;
}
