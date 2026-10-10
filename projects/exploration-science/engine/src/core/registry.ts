import type { Object3D } from "three";
import type { Params } from "../content/types";
import type { Palette } from "./style";

export interface ComponentContext {
  palette: Palette;
  /** Converts a length in metres (catalogue unit "m") to scene units. */
  metres(m: number): number;
}

export type RevealMode = "cutaway" | "explode" | "none";

export interface ComponentInstance {
  object: Object3D;
  /** Where child entities attach (e.g. a tilted panel). Defaults to `object`. */
  anchor?: Object3D;
  /**
   * Called once every entity exists and world matrices are up to date, for
   * components whose params reference other entities (x-ref: "entity").
   */
  resolve?(entity: (id: string) => Object3D | undefined): void;
  update?(dt: number): void;
  /** Present when the catalogue grants the component a cutaway or explode capability. */
  reveal?(mode: RevealMode): void;
  dispose?(): void;
}

export interface ComponentPlugin {
  /** Catalogue component id. */
  id: string;
  /** `params` already carry the catalogue defaults. */
  create(params: Params, ctx: ComponentContext): ComponentInstance;
}

/** An entity as a simulator sees it. */
export interface BoundEntity {
  id: string;
  /** Carries the scene transform; a simulator may move it. */
  node: Object3D;
  /** The component's own object, inside `node`. A simulator may hide it (a satellite below the horizon). */
  object: Object3D;
}

export interface SimulatorContext {
  /** Entities bound to a role in the scene's `bind`, in the declared order. */
  bound(role: string): BoundEntity[];
  /** Any entity, for params that reference one (x-ref: "entity"). */
  entity(id: string): BoundEntity | undefined;
  metres(m: number): number;
}

export interface SimulatorInstance {
  /** Current params, defaults included. */
  readonly params: Params;
  set(param: string, value: unknown): void;
  /** Advances simulated time (already multiplied by the clock's time scale). */
  update(simDt: number): void;
  /** Values named in the catalogue `outputs`. */
  outputs(): Record<string, unknown>;
  dispose?(): void;
}

export interface SimulatorPlugin {
  /** Catalogue simulator id. */
  id: string;
  /** `params` already carry the catalogue defaults. */
  create(params: Params, ctx: SimulatorContext): SimulatorInstance;
}

/** Plugins register here; the core never imports a plugin (design rule 2). */
export class PluginRegistry {
  private readonly components = new Map<string, ComponentPlugin>();
  private readonly simulators = new Map<string, SimulatorPlugin>();

  registerComponent(plugin: ComponentPlugin): void {
    if (this.components.has(plugin.id)) throw new Error(`component '${plugin.id}' registered twice`);
    this.components.set(plugin.id, plugin);
  }

  registerSimulator(plugin: SimulatorPlugin): void {
    if (this.simulators.has(plugin.id)) throw new Error(`simulator '${plugin.id}' registered twice`);
    this.simulators.set(plugin.id, plugin);
  }

  component(id: string): ComponentPlugin | undefined {
    return this.components.get(id);
  }

  simulator(id: string): SimulatorPlugin | undefined {
    return this.simulators.get(id);
  }
}
