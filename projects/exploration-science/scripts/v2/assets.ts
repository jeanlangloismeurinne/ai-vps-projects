// npm run assets [-- --out DIR] [-- --system ID] : validates then builds every system listed in
// art/assets.json `build` (or only system ID) with Blender (art/build.py), compresses the GLBs
// (meshopt) and writes DIR/<system id>/manifest.json. Each system gets its own models: the
// scripts are a shared library, but placement and baked occlusion belong to one scene.
// Empty leaf nodes are kept: they are the anchors.
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { dedup, meshopt, prune, weld } from "@gltf-transform/functions";
import { MeshoptEncoder } from "meshoptimizer";
import { assetsErrors, systemErrors } from "../../v2/src/content/validate.ts";
import { makeIO, sha256, type Manifest } from "./assetChecks.ts";

const root = resolve(import.meta.dirname, "../..");
const python = join(root, "art/.venv/bin/python");
const outArg = process.argv.indexOf("--out");
const outRoot = outArg > 0 ? resolve(process.argv[outArg + 1]!) : join(root, "public/v2/models");
const systemArg = process.argv.indexOf("--system");
const onlySystem = systemArg > 0 ? process.argv[systemArg + 1] : undefined;

if (!existsSync(python)) {
  console.error("Blender venv missing: python3.13 -m venv art/.venv && art/.venv/bin/pip install -r art/requirements.txt");
  process.exit(1);
}

const registry = JSON.parse(readFileSync(join(root, "art/assets.json"), "utf8"));
const built: string[] = [];
const io = await makeIO();
await MeshoptEncoder.ready;

for (const file of registry.build as string[]) {
  const systemPath = join(root, file);
  const system = JSON.parse(readFileSync(systemPath, "utf8"));
  const invalid = [...systemErrors(system), ...assetsErrors(registry, system)];
  if (invalid.length) {
    for (const e of invalid) console.error(`  - ${e}`);
    console.error(`RESULT: failure — ${file} is not valid`);
    process.exit(1);
  }
  const id = system.id as string;
  if (onlySystem && id !== onlySystem) continue;
  const out = join(outRoot, id);
  mkdirSync(out, { recursive: true });
  const manifest: Manifest = { version: 1, assets: {}, totals: { bytes: 0, triangles: 0 } };
  try {
    execFileSync(python, [join(root, "art/build.py"), "--system", systemPath, "--out", out], { stdio: ["ignore", "ignore", "inherit"] });
  } catch {
    console.error(`RESULT: failure — Blender build of ${file} failed (see the checks above)`);
    process.exit(1);
  }
  const report = JSON.parse(readFileSync(join(root, "art/.build", `${id}.report.json`), "utf8"));
  console.log(`${file}: built in ${report.timings_s.total} s`);
  for (const [assetId, a] of Object.entries<any>(report.assets)) {
    const representation = async (file: string, stats: any) => {
      const path = join(out, file);
      const doc = await io.read(path);
      await doc.transform(dedup(), prune({ keepLeaves: true }), weld(), meshopt({ encoder: MeshoptEncoder, level: "medium" }));
      const bytes = await io.writeBinary(doc);
      writeFileSync(path, bytes);
      manifest.totals.bytes += bytes.byteLength;
      const rep = { file, bytes: bytes.byteLength, sha256: sha256(bytes), parts: stats.parts, triangles: stats.triangles, materials: stats.materials, anchors: stats.anchors };
      return { ...rep, ...(stats.layers && { layers: stats.layers }), ...(stats.array && { array: stats.array }) };
    };
    const envelope = await representation(a.envelope, a);
    manifest.assets[assetId] = {
      main: a.main,
      airborne: a.airborne,
      // Blender (x, y, z) Z-up → glTF (x, z, −y) Y-up; a turn about Blender Z is a turn about glTF Y.
      transform: { position: [a.world.position[0], a.world.position[2], -a.world.position[1]], rotationYDeg: a.world.rotationZDeg },
      representations: a.detail ? { envelope, detail: await representation(a.detail.file, a.detail) } : { envelope },
    };
    // The scene draws one representation at a time: the envelopes are its triangle count.
    manifest.totals.triangles += a.triangles;
  }
  writeFileSync(join(out, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
  built.push(`${id}: ${Object.keys(manifest.assets).length} assets, ${manifest.totals.bytes} bytes, ${manifest.totals.triangles} triangles`);
}

if (!built.length) {
  console.error(`RESULT: failure — no system built${onlySystem ? ` (is ${onlySystem} listed in art/assets.json build?)` : ""}`);
  process.exit(1);
}
console.log(`RESULT: success — ${built.join(" ; ")} → ${outRoot}`);
