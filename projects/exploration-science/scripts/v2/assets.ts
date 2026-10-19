// npm run assets [-- --out DIR] : builds every scene of art/scenes with Blender
// (art/build.py), compresses the GLBs (meshopt) and writes DIR/manifest.json.
import { execFileSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { dedup, meshopt, prune, weld } from "@gltf-transform/functions";
import { MeshoptEncoder } from "meshoptimizer";
import { makeIO, sha256, type Manifest } from "./assetChecks.ts";

const root = resolve(import.meta.dirname, "../..");
const python = join(root, "art/.venv/bin/python");
const outArg = process.argv.indexOf("--out");
const out = outArg > 0 ? resolve(process.argv[outArg + 1]!) : join(root, "public/v2/models");

if (!existsSync(python)) {
  console.error("Blender venv missing: python3.13 -m venv art/.venv && art/.venv/bin/pip install -r art/requirements.txt");
  process.exit(1);
}

const scenes = readdirSync(join(root, "art/scenes")).filter((f) => f.endsWith(".json")).sort();
const manifest: Manifest = { version: 1, assets: {}, totals: { bytes: 0, triangles: 0 } };
const io = await makeIO();
await MeshoptEncoder.ready;

for (const file of scenes) {
  const scene = join(root, "art/scenes", file);
  const id = JSON.parse(readFileSync(scene, "utf8")).id as string;
  try {
    execFileSync(python, [join(root, "art/build.py"), "--scene", scene, "--out", out], { stdio: ["ignore", "ignore", "inherit"] });
  } catch {
    console.error(`RESULT: failure — Blender build of ${file} failed (see the checks above)`);
    process.exit(1);
  }
  const report = JSON.parse(readFileSync(join(root, "art/.build", `${id}.report.json`), "utf8"));
  console.log(`${file}: built in ${report.timings_s.total} s`);
  for (const [assetId, a] of Object.entries<any>(report.assets)) {
    const path = join(out, a.envelope);
    const doc = await io.read(path);
    await doc.transform(dedup(), prune(), weld(), meshopt({ encoder: MeshoptEncoder, level: "medium" }));
    const bytes = await io.writeBinary(doc);
    writeFileSync(path, bytes);
    manifest.assets[assetId] = {
      main: a.main,
      airborne: a.airborne,
      representations: {
        envelope: { file: a.envelope, bytes: bytes.byteLength, sha256: sha256(bytes), parts: a.parts, triangles: a.triangles, materials: a.materials },
      },
    };
    manifest.totals.bytes += bytes.byteLength;
    manifest.totals.triangles += a.triangles;
  }
}

writeFileSync(join(out, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
console.log(`RESULT: success — ${Object.keys(manifest.assets).length} assets, ${manifest.totals.bytes} bytes, ${manifest.totals.triangles} triangles → ${out}`);
