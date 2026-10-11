import type { PluginRegistry } from "../../core/registry";
import { antennaElementArray } from "./antennaElementArray";
import { atmosphereLayer } from "./atmosphereLayer";
import { cable } from "./cable";
import { dataLink } from "./dataLink";
import { datacenter } from "./datacenter";
import { electronicsModule } from "./electronicsModule";
import { flatPanelTerminal } from "./flatPanelTerminal";
import { groundStation } from "./groundStation";
import { house } from "./house";
import { icChipGrid } from "./icChipGrid";
import { leoSatellite } from "./leoSatellite";
import { moleculeCloud } from "./moleculeCloud";
import { observer } from "./observer";
import { patchElement } from "./patchElement";
import { star } from "./star";
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
  patchElement,
  star,
  atmosphereLayer,
  moleculeCloud,
  observer,
];

export function registerComponents(registry: PluginRegistry): void {
  for (const plugin of COMPONENTS) registry.registerComponent(plugin);
}
