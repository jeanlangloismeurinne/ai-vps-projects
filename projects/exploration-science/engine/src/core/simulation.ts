import type { Catalogue, Scene } from "../content/types";
import type { BoundEntity, PluginRegistry, SimulatorContext, SimulatorInstance } from "./registry";
import type { BuiltScene } from "./sceneBuilder";
import { withDefaults } from "./sceneBuilder";

export interface Simulation {
  instances: Map<string, SimulatorInstance>;
  /** Simulators referenced by the scene but not implemented yet. */
  missing: string[];
  /** Simulated seconds since the start (or the last reset). */
  readonly time: number;
  timeScale: number;
  /** Advances by a real-time step, scaled by timeScale. */
  update(dt: number): void;
  /** Advances by simulated seconds, regardless of timeScale. */
  advance(simDt: number): void;
  /** Back to the scene's params, at time 0. */
  reset(): void;
  dispose(): void;
}

/** Instantiates the scene's simulators; time runs from 0 at the scene's clock rate. */
export function buildSimulation(scene: Scene, catalogue: Catalogue, registry: PluginRegistry, built: BuiltScene): Simulation {
  const bound = (id: string): BoundEntity | undefined => {
    const e = built.entities.get(id);
    return e && { id, node: e.node, object: e.instance.object };
  };
  const specs = scene.simulators ?? [];
  const missing = [...new Set(specs.filter((s) => !registry.simulator(s.simulator)).map((s) => s.simulator))].sort();
  const instances = new Map<string, SimulatorInstance>();

  const create = () => {
    for (const spec of specs) {
      const plugin = registry.simulator(spec.simulator);
      if (!plugin) continue;
      const ctx: SimulatorContext = {
        bound(role) {
          const ids = spec.bind[role];
          return (ids === undefined ? [] : Array.isArray(ids) ? ids : [ids]).map((id) => {
            const b = bound(id);
            if (!b) throw new Error(`simulator '${spec.id}': unknown entity '${id}' bound to '${role}'`);
            return b;
          });
        },
        entity: bound,
        metres: (m) => m / scene.scale.metersPerUnit,
      };
      const instance = plugin.create(withDefaults(catalogue, spec.simulator, spec.params, "simulators"), ctx);
      instance.update(0);
      instances.set(spec.id, instance);
    }
  };
  const destroy = () => {
    for (const s of instances.values()) s.dispose?.();
    instances.clear();
  };

  const initialScale = scene.clock?.timeScale ?? 1;
  let time = 0;
  create();
  const simulation: Simulation = {
    instances,
    missing,
    get time() {
      return time;
    },
    timeScale: initialScale,
    update(dt) {
      simulation.advance(dt * simulation.timeScale);
    },
    advance(simDt) {
      time += simDt;
      for (const s of instances.values()) s.update(simDt);
    },
    reset() {
      destroy();
      time = 0;
      simulation.timeScale = initialScale;
      create();
    },
    dispose: destroy,
  };
  return simulation;
}
