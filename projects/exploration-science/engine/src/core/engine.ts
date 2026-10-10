import { Timer, PerspectiveCamera, Scene as ThreeScene, SRGBColorSpace, ACESFilmicToneMapping, WebGLRenderer, Vector3 } from "three";
import type { ContentSource, NodeBundle } from "../content/contentSource";
import type { Catalogue, Shot } from "../content/types";
import { CameraRig, type TargetProvider } from "./camera";
import { attachCameraInput } from "./cameraInput";
import { backgroundColor, createLighting } from "./environment";
import type { PluginRegistry } from "./registry";
import { buildScene, type BuiltScene } from "./sceneBuilder";

export interface LoadedNode {
  bundle: NodeBundle;
  built: BuiltScene;
}

/**
 * Displays whatever a scene file describes (design rule 1): no subject-specific
 * logic lives here. Content comes through a ContentSource, geometry from plugins.
 */
export class Engine {
  readonly renderer: WebGLRenderer;
  private readonly three = new ThreeScene();
  private readonly camera = new PerspectiveCamera(45, 1, 0.1, 1000);
  private readonly timer = new Timer();
  private catalogue: Catalogue | null = null;
  private current: { built: BuiltScene; rig: CameraRig; detachInput: () => void; home: Shot } | null = null;
  private readonly resizeObserver: ResizeObserver;

  constructor(
    private readonly container: HTMLElement,
    private readonly source: ContentSource,
    private readonly registry: PluginRegistry,
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

    this.unload();
    this.three.background = backgroundColor(scene.environment);
    this.three.add(createLighting(scene.environment), built.root);

    const rig = new CameraRig(this.camera, scene.camera.constraints, scene.camera.home, (id) => this.targetOf(built, id));
    const detachInput = attachCameraInput(this.renderer.domElement, rig);
    this.current = { built, rig, detachInput, home: scene.camera.home };
    return { bundle, built };
  }

  /** Back to the scene's home shot. */
  goHome(durationS = 1.2): void {
    if (this.current) this.current.rig.flyTo(this.current.home, durationS);
  }

  flyTo(shot: Shot, durationS: number): void {
    this.current?.rig.flyTo(shot, durationS);
  }

  dispose(): void {
    this.renderer.setAnimationLoop(null);
    this.resizeObserver.disconnect();
    this.unload();
    this.renderer.dispose();
    this.renderer.domElement.remove();
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
    if (this.current) {
      this.current.built.update(dt);
      this.current.rig.update(dt);
    }
    this.renderer.render(this.three, this.camera);
  }
}
