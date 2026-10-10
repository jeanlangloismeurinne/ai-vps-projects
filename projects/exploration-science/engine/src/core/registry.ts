import type { Object3D } from "three";
import type { Params } from "../content/types";
import type { Palette } from "./style";

export interface ComponentContext {
  palette: Palette;
  /** Converts a length in metres (catalogue unit "m") to scene units. */
  metres(m: number): number;
}

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
  dispose?(): void;
}

export interface ComponentPlugin {
  /** Catalogue component id. */
  id: string;
  /** `params` already carry the catalogue defaults. */
  create(params: Params, ctx: ComponentContext): ComponentInstance;
}

/** Plugins register here; the core never imports a plugin (design rule 2). */
export class PluginRegistry {
  private readonly components = new Map<string, ComponentPlugin>();

  registerComponent(plugin: ComponentPlugin): void {
    if (this.components.has(plugin.id)) throw new Error(`component '${plugin.id}' registered twice`);
    this.components.set(plugin.id, plugin);
  }

  component(id: string): ComponentPlugin | undefined {
    return this.components.get(id);
  }
}
