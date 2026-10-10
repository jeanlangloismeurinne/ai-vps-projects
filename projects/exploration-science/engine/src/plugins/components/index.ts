import type { PluginRegistry } from "../../core/registry";
import { antennaElementArray } from "./antennaElementArray";
import { cable } from "./cable";
import { dataLink } from "./dataLink";
import { datacenter } from "./datacenter";
import { electronicsModule } from "./electronicsModule";
import { flatPanelTerminal } from "./flatPanelTerminal";
import { groundStation } from "./groundStation";
import { house } from "./house";
import { icChipGrid } from "./icChipGrid";
import { leoSatellite } from "./leoSatellite";
import { terrain } from "./terrain";
import { wifiRouter } from "./wifiRouter";

export const COMPONENTS = [
  terrain,
  house,
  flatPanelTerminal,
  antennaElementArray,
  icChipGrid,
  electronicsModule,
  wifiRouter,
  leoSatellite,
  groundStation,
  datacenter,
  cable,
  dataLink,
];

export function registerComponents(registry: PluginRegistry): void {
  for (const plugin of COMPONENTS) registry.registerComponent(plugin);
}
