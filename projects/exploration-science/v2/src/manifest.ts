// Shape of public/v2/models/manifest.json, written by scripts/v2/assets.ts.
export interface Representation {
  file: string;
  bytes: number;
  sha256: string;
  parts: number;
  triangles: number;
  materials: string[];
}

export interface Manifest {
  version: 1;
  assets: Record<string, { main: boolean; airborne: boolean; representations: Record<string, Representation> & { envelope: Representation } }>;
  totals: { bytes: number; triangles: number };
}

export const MODELS_BASE = "./v2/models";
