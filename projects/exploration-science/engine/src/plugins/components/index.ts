import type { PluginRegistry } from "../../core/registry";
import { cable } from "./cable";
import { dataLink } from "./dataLink";
import { flatPanelTerminal } from "./flatPanelTerminal";
import { house } from "./house";
import { leoSatellite } from "./leoSatellite";
import { terrain } from "./terrain";

export const COMPONENTS = [terrain, house, flatPanelTerminal, leoSatellite, cable, dataLink];

export function registerComponents(registry: PluginRegistry): void {
  for (const plugin of COMPONENTS) registry.registerComponent(plugin);
}
