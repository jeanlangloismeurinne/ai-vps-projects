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
