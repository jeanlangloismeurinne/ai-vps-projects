// Checks on the built v2 assets (roadmap v2 §1): integrity, palette, baked AO, budgets.
// Pure functions over the manifest and the GLB bytes, so tests can feed broken inputs.
import { createHash } from "node:crypto";
import { NodeIO } from "@gltf-transform/core";
import { EXTMeshoptCompression, KHRMeshQuantization } from "@gltf-transform/extensions";
import { MeshoptDecoder, MeshoptEncoder } from "meshoptimizer";

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

export interface Manifest {
  version: 1;
  assets: Record<string, { main: boolean; airborne: boolean; representations: Record<string, Representation> }>;
  totals: { bytes: number; triangles: number };
}

export interface Budgets {
  totalBytesMax: number;
  sceneTrianglesMax: number;
  mainObject: { minParts: number; minTriangles: number; maxTriangles: number };
}

export function sha256(bytes: Uint8Array): string {
  return createHash("sha256").update(bytes).digest("hex");
}

export async function makeIO(): Promise<NodeIO> {
  await Promise.all([MeshoptDecoder.ready, MeshoptEncoder.ready]);
  return new NodeIO()
    .registerExtensions([EXTMeshoptCompression, KHRMeshQuantization])
    .registerDependencies({ "meshopt.decoder": MeshoptDecoder, "meshopt.encoder": MeshoptEncoder });
}

/** Every error found; empty means the assets pass. `read` returns a GLB's bytes or null. */
export async function checkAssets(
  manifest: Manifest,
  read: (file: string) => Uint8Array | null,
  palette: Set<string>,
  budgets: Budgets,
): Promise<string[]> {
  const errors: string[] = [];
  const io = await makeIO();
  let bytes = 0;
  let triangles = 0;
  for (const [id, asset] of Object.entries(manifest.assets)) {
    for (const [kind, rep] of Object.entries(asset.representations)) {
      const where = `${id}.${kind}`;
      const data = read(rep.file);
      if (!data) {
        errors.push(`${where}: file ${rep.file} missing`);
        continue;
      }
      if (sha256(data) !== rep.sha256) errors.push(`${where}: content differs from the manifest (rebuild with npm run assets)`);
      bytes += data.byteLength;
      if (kind === "envelope") triangles += rep.triangles;

      const doc = await io.readBinary(data);
      for (const mat of doc.getRoot().listMaterials()) {
        if (!palette.has(mat.getName())) errors.push(`${where}: material "${mat.getName()}" is not a palette swatch`);
      }
      for (const mesh of doc.getRoot().listMeshes()) {
        for (const prim of mesh.listPrimitives()) {
          if (!prim.getAttribute("COLOR_0")) errors.push(`${where}: mesh ${mesh.getName()} has no baked AO (COLOR_0)`);
        }
      }
      const nodes = new Set(doc.getRoot().listNodes().map((n) => n.getName()));
      for (const a of rep.anchors) if (!nodes.has(`${id}#${a}`)) errors.push(`${where}: anchor node ${id}#${a} missing from the GLB`);
      if (asset.main && kind === "envelope") {
        const b = budgets.mainObject;
        if (rep.parts < b.minParts) errors.push(`${where}: ${rep.parts} named parts, a main object needs ≥ ${b.minParts}`);
        if (rep.triangles < b.minTriangles) errors.push(`${where}: ${rep.triangles} triangles, below ${b.minTriangles} (block-like)`);
        if (rep.triangles > b.maxTriangles) errors.push(`${where}: ${rep.triangles} triangles, above ${b.maxTriangles}`);
      }
    }
  }
  if (bytes > budgets.totalBytesMax) errors.push(`models weigh ${bytes} bytes, budget ${budgets.totalBytesMax}`);
  if (triangles > budgets.sceneTrianglesMax) errors.push(`scene has ${triangles} triangles, budget ${budgets.sceneTrianglesMax}`);
  return errors;
}
