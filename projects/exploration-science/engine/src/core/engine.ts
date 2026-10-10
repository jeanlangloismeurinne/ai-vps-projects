import { Box3, MathUtils, Sphere, Timer, PerspectiveCamera, Scene as ThreeScene, SRGBColorSpace, ACESFilmicToneMapping, WebGLRenderer, Vector3, Color } from "three";
import type { ContentSource, NodeBundle } from "../content/contentSource";
import type { Catalogue, RevealModeSpec, Shot } from "../content/types";
import type { Stage } from "../play/player";
import { CameraRig, type TargetProvider } from "./camera";
import { attachCameraInput, type InputHandlers } from "./cameraInput";
import { backgroundColor, createLighting } from "./environment";
import { Highlighter } from "./highlighter";
import { pickEntity } from "./picking";
import type { PluginRegistry } from "./registry";
import { buildScene, type BuiltScene } from "./sceneBuilder";
import { buildSimulation, type Simulation } from "./simulation";

export interface LoadedNode {
  bundle: NodeBundle;
  built: BuiltScene;
  simulation: Simulation;
  /** Lenses referenced by the scene but not implemented yet. */
  missingLenses: string[];
}

interface Current extends LoadedNode {
  rig: CameraRig;
  detachInput: () => void;
  highlighter: Highlighter;
  anchors: Map<string, TargetProvider>;
}

const SELECT_FLIGHT_S = 1.2;
const SELECT_MARGIN = 1.6; // camera distance, in bounding-sphere radii over the fit distance

/**
 * Displays whatever a scene file describes (design rule 1): no subject-specific
 * logic lives here. Content comes through a ContentSource, geometry and physics
 * from plugins. The engine is also the Stage a tour plays on.
 */
export class Engine implements Stage {
  readonly renderer: WebGLRenderer;
  /** Called after each frame is drawn, e.g. to move DOM labels. */
  onFrame: (() => void) | null = null;
  private readonly three = new ThreeScene();
  private readonly camera = new PerspectiveCamera(45, 1, 0.1, 1000);
  private readonly timer = new Timer();
  private catalogue: Catalogue | null = null;
  private current: Current | null = null;
  private readonly resizeObserver: ResizeObserver;
  private frozen = false;
  private tourHighlights: string[] = [];
  private selected: string | null = null;
  private frameListeners: ((dt: number) => void)[] = [];

  constructor(
    private readonly container: HTMLElement,
    private readonly source: ContentSource,
    private readonly registry: PluginRegistry,
    private readonly input: InputHandlers = {},
  ) {
    this.renderer = new WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.outputColorSpace = SRGBColorSpace;
    this.renderer.toneMapping = ACESFilmicToneMapping;
    container.appendChild(this.renderer.domElement);
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(container);
    this.resize();
    this.renderer.setAnimationLoop((time) => this.frame(time));
  }

  async load(nodeId: string): Promise<LoadedNode> {
    this.catalogue ??= await this.source.catalogue();
    const bundle = await this.source.node(nodeId);
    const { scene } = bundle;
    const built = buildScene(scene, this.catalogue, this.registry);
    const simulation = buildSimulation(scene, this.catalogue, this.registry, built);
    // No lens plugin yet (milestone 4): lens actions are accepted and ignored.
    const missingLenses = [...new Set((scene.lenses ?? []).map((l) => l.lens))].sort();

    this.unload();
    this.three.background = backgroundColor(scene.environment);
    this.three.add(createLighting(scene.environment), built.root);

    const anchors = new Map<string, TargetProvider>();
    const anchor = (id: string) => {
      let provider = anchors.get(id);
      if (!provider) anchors.set(id, (provider = this.targetOf(built, id)));
      return provider;
    };
    const rig = new CameraRig(this.camera, scene.camera.constraints, scene.camera.home, anchor);
    const detachInput = attachCameraInput(this.renderer.domElement, rig, {
      onGesture: () => this.input.onGesture?.(),
      onTap: (x, y) => this.input.onTap?.(x, y),
    });
    const highlighter = new Highlighter(new Color(scene.style?.accent ?? "#ffb000"));
    this.current = { bundle, built, simulation, missingLenses, rig, detachInput, highlighter, anchors };
    this.frozen = false;
    this.tourHighlights = [];
    this.selected = null;
    return { bundle, built, simulation, missingLenses };
  }

  /** Back to the scene's home shot. */
  goHome(durationS = 1.2): void {
    if (this.current) this.current.rig.flyTo(this.current.bundle.scene.camera.home, durationS);
  }

  /** Runs every frame with the real time step (the tour player hangs here). */
  addFrameListener(listener: (dt: number) => void): void {
    this.frameListeners.push(listener);
  }

  /** True while the camera flies between shots. */
  get cameraFlying(): boolean {
    return this.current?.rig.flying ?? false;
  }

  /** Selectable entity under a client point, or null. */
  pick(clientX: number, clientY: number): string | null {
    if (!this.current) return null;
    const rect = this.renderer.domElement.getBoundingClientRect();
    return pickEntity(this.current.built, this.camera, ((clientX - rect.left) / rect.width) * 2 - 1, -((clientY - rect.top) / rect.height) * 2 + 1);
  }

  /** Selects an entity (glow + camera orbit around it), or clears the selection. */
  select(id: string | null): void {
    this.selected = id;
    this.refreshHighlights();
    if (!id || !this.current) return;
    const { rig, built } = this.current;
    const sphere = new Box3().setFromObject(built.entities.get(id)!.node).getBoundingSphere(new Sphere());
    const fit = sphere.radius / Math.sin(MathUtils.degToRad(this.camera.fov / 2));
    rig.flyTo(
      { target: id, azimuthDeg: MathUtils.radToDeg(rig.view.azimuth), elevationDeg: MathUtils.radToDeg(rig.view.elevation), distance: fit * SELECT_MARGIN },
      SELECT_FLIGHT_S,
    );
  }

  /** Where an entity's centre is on the canvas, in CSS pixels; null when behind the camera. */
  screenPosition(id: string): { x: number; y: number } | null {
    if (!this.current?.built.entities.has(id)) return null;
    const anchors = this.current.anchors;
    let provider = anchors.get(id);
    if (!provider) anchors.set(id, (provider = this.targetOf(this.current.built, id)));
    const p = provider().clone().project(this.camera);
    if (p.z > 1 || p.z < -1) return null;
    const { clientWidth: w, clientHeight: h } = this.renderer.domElement;
    return { x: ((p.x + 1) / 2) * w, y: ((1 - p.y) / 2) * h };
  }

  // ---- Stage (driven by the tour player) ----

  reset(): void {
    const c = this.current;
    if (!c) return;
    for (const { entity, node, instance } of c.built.entities.values()) {
      node.visible = entity.visible ?? true;
      instance.reveal?.("none");
    }
    c.simulation.reset();
    c.built.root.updateMatrixWorld(true);
  }

  advanceSim(simSeconds: number): void {
    this.current?.simulation.advance(simSeconds);
  }

  setFrozen(frozen: boolean): void {
    this.frozen = frozen;
  }

  flyTo(shot: Shot, durationS: number): void {
    this.current?.rig.flyTo(shot, durationS);
  }

  setVisible(ids: string[], visible: boolean): void {
    for (const id of ids) {
      const e = this.current?.built.entities.get(id);
      if (e) e.node.visible = visible;
    }
  }

  reveal(id: string, mode: RevealModeSpec): void {
    this.current?.built.entities.get(id)?.instance.reveal?.(mode);
  }

  setLens(_id: string, _on: boolean): void {
    // Lens plugins arrive with milestone 4.
  }

  getParam(simulator: string, param: string): unknown {
    return this.current?.simulation.instances.get(simulator)?.params[param];
  }

  setParam(simulator: string, param: string, value: unknown): void {
    this.current?.simulation.instances.get(simulator)?.set(param, value);
  }

  setTimeScale(value: number): void {
    if (this.current) this.current.simulation.timeScale = value;
  }

  setHighlights(ids: string[]): void {
    this.tourHighlights = ids;
    this.refreshHighlights();
  }

  setLabels(_ids: string[]): void {
    // Labels are DOM elements: the overlay draws them from screenPosition().
  }

  dispose(): void {
    this.renderer.setAnimationLoop(null);
    this.resizeObserver.disconnect();
    this.unload();
    this.renderer.dispose();
    this.renderer.domElement.remove();
  }

  private refreshHighlights(): void {
    const c = this.current;
    if (!c) return;
    const ids = new Set(this.tourHighlights);
    if (this.selected) ids.add(this.selected);
    c.highlighter.set([...ids].flatMap((id) => c.built.entities.get(id)?.node ?? []));
  }

  // Follows the entity as it moves, aimed at the centre of its bounds at the time of the call.
  private targetOf(built: BuiltScene, id: string): TargetProvider {
    const node = built.entities.get(id)?.node;
    if (!node) throw new Error(`camera target: unknown entity '${id}'`);
    const centreOffset = built.focusPoint(id).sub(node.getWorldPosition(new Vector3()));
    const out = new Vector3();
    return () => node.getWorldPosition(out).add(centreOffset);
  }

  private unload(): void {
    if (!this.current) return;
    this.current.detachInput();
    this.current.highlighter.dispose();
    this.current.simulation.dispose();
    this.current.built.dispose();
    this.current = null;
    this.three.clear();
  }

  private resize(): void {
    const { clientWidth: w, clientHeight: h } = this.container;
    if (w === 0 || h === 0) return;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  private frame(time: number): void {
    this.timer.update(time);
    const dt = Math.min(this.timer.getDelta(), 0.1);
    for (const listener of this.frameListeners) listener(dt);
    const c = this.current;
    if (c) {
      if (!this.frozen) c.simulation.update(dt);
      c.built.update(this.frozen ? 0 : dt);
      c.highlighter.update(dt);
      c.rig.update(dt);
    }
    this.renderer.render(this.three, this.camera);
    this.onFrame?.();
  }
}
