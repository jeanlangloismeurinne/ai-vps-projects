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
  // Simulators, lenses, links and tours are read by later milestones.
  simulators?: unknown[];
  lenses?: unknown[];
  links?: unknown[];
  tours: unknown[];
}

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
