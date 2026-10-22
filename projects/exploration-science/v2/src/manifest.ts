// Shape of public/v2/models/manifest.json, written by scripts/v2/assets.ts.
export interface Representation {
  file: string;
  bytes: number;
  sha256: string;
  parts: number;
  triangles: number;
  materials: string[];
  /** Attachment points, exported as empty nodes `<id>#<anchor>`. */
  anchors: string[];
  /** Exploded view only: offset of each layer (glTF frame of the asset, metres). Its nodes
   * `<id>.<layer>.<material>` are exported exploded; the app moves them back to assemble. */
  layers?: Record<string, [number, number, number]>;
  /** Antenna array of the model (anchor `array`: x along the columns' pitch, y along the rows'). */
  array?: { columns: number; rows: number; pitch: number; spacingOverLambda: number };
}

/** Where the build placed the asset's root, in the glTF frame (Y up, metres). */
export interface Transform {
  position: [number, number, number];
  rotationYDeg: number;
}

export interface Manifest {
  version: 1;
  assets: Record<string, { main: boolean; airborne: boolean; transform: Transform; representations: Record<string, Representation> & { envelope: Representation } }>;
  totals: { bytes: number; triangles: number };
}

export const MODELS_BASE = "./v2/models";
