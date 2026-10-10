import type { PluginRegistry } from "../../core/registry";
import { orbitalPass } from "./orbitalPass";
import { phasedArrayWave } from "./phasedArrayWave";

export const SIMULATORS = [phasedArrayWave, orbitalPass];

export function registerSimulators(registry: PluginRegistry): void {
  for (const plugin of SIMULATORS) registry.registerSimulator(plugin);
}
