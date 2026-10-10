import type { PluginRegistry } from "../../core/registry";
import { waves } from "./waves";

export const LENSES = [waves];

export function registerLenses(registry: PluginRegistry): void {
  for (const plugin of LENSES) registry.registerLens(plugin);
}
