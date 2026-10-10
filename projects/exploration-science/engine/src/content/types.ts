// TypeScript view of the content formats. JSON Schema (schemas/) stays the source
// of truth; these types only cover what the engine reads.

export type Vec3 = [number, number, number];
export type Level = "discovery" | "essential" | "advanced";
export type Params = Record<string, unknown>;

export interface Shot {
  target: string;
  azimuthDeg: number;
  elevationDeg: number;
  distance: number;
}

export interface CameraConstraints {
  minDistance: number;
  maxDistance: number;
  minElevationDeg?: number;
  maxElevationDeg?: number;
}

export interface Entity {
  id: string;
  component: string;
  params: Params;
  transform: { position: Vec3; rotationDeg?: Vec3; scale?: number };
  parent?: string;
  visible?: boolean;
  selectable?: boolean;
  notToScale?: boolean;
  labelKey?: string;
  descriptionKey?: string;
}

export interface Style {
  theme: string;
  accent?: string;
}

export interface Scene {
  formatVersion: string;
  node: { id: string; kind: "system" | "principle"; version: number; status: string; parent?: { node: string; entity: string } };
  scale: { metersPerUnit: number };
  environment: { lighting: "daylight" | "dusk" | "space" | "studio"; background: string };
  style?: Style;
  performance?: { triangleBudget?: number };
  clock?: { timeScale?: number };
  camera: { home: Shot; constraints: CameraConstraints };
  entities: Entity[];
  simulators?: SimulatorInstanceSpec[];
  lenses?: LensInstanceSpec[];
  links?: Link[];
  tours: Tour[];
}

export interface SimulatorInstanceSpec {
  id: string;
  simulator: string;
  params: Params;
  bind: Record<string, string | string[]>;
}

export interface LensInstanceSpec {
  id: string;
  lens: string;
  labelKey?: string;
  sources: string[];
  controls: { id: string; target: string; param: string; labelKey: string; levels: Level[]; min?: number; max?: number; step?: number }[];
}

export interface Link {
  kind: "composedOf" | "reliesOn" | "freeQuestion" | "derivedFrom";
  from?: string;
  to: string;
  available?: boolean;
}

export type RevealModeSpec = "cutaway" | "explode" | "none";

export type Action =
  | { type: "highlight" | "label" | "show" | "hide"; targets: string[] }
  | { type: "reveal"; target: string; mode: RevealModeSpec }
  | { type: "lens"; lens: string; on: boolean }
  | { type: "setParam"; target: string; param: string; value: number | string | boolean; overS?: number }
  | { type: "timeScale"; value: number };

export interface Step {
  id: string;
  textKey: string;
  durationS: number;
  camera?: { shot: Shot; transitionS?: number };
  actions?: Action[];
}

export interface Tour {
  id: string;
  autoStart?: boolean;
  steps: Step[];
}

/** A text entry: plain string, or spoken text with a displayed variant, terms and explorable links. */
export type TextEntry =
  | string
  | {
      text: string;
      subtitle?: string;
      terms?: { symbol: string; meaning: string; unit?: string }[];
      links?: { phrase: string; node: string }[];
    };

export interface Texts {
  nodeId: string;
  lang: string;
  question: string;
  common: Record<string, unknown>;
  levels: Record<Level, Record<string, unknown>>;
}

export interface ParamSpec {
  type?: string;
  default?: unknown;
  "x-unit"?: string;
  "x-ref"?: string;
}

export interface CatalogueEntry {
  id: string;
  status: string;
  params: { properties: Record<string, ParamSpec> };
  capabilities?: string[];
}

export interface Catalogue {
  formatVersion: string;
  components: CatalogueEntry[];
  simulators: CatalogueEntry[];
  lenses: CatalogueEntry[];
}
