import type { PluginRegistry } from "../../core/registry";
import { orbitalPass } from "./orbitalPass";
import { phasedArrayWave } from "./phasedArrayWave";
import { rayleighScattering } from "./rayleighScattering";

export const SIMULATORS = [phasedArrayWave, orbitalPass, rayleighScattering];

export function registerSimulators(registry: PluginRegistry): void {
  for (const plugin of SIMULATORS) registry.registerSimulator(plugin);
}
