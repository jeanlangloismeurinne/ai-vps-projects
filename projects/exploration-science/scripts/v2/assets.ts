// npm run assets [-- --out DIR] : validates then builds every system listed in
// art/assets.json `build` with Blender (art/build.py), compresses the GLBs (meshopt)
// and writes DIR/manifest.json. Empty leaf nodes are kept: they are the anchors.
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { dedup, meshopt, prune, weld } from "@gltf-transform/functions";
import { MeshoptEncoder } from "meshoptimizer";
import { assetsErrors, systemErrors } from "../../v2/src/content/validate.ts";
import { makeIO, sha256, type Manifest } from "./assetChecks.ts";

const root = resolve(import.meta.dirname, "../..");
const python = join(root, "art/.venv/bin/python");
const outArg = process.argv.indexOf("--out");
const out = outArg > 0 ? resolve(process.argv[outArg + 1]!) : join(root, "public/v2/models");

if (!existsSync(python)) {
  console.error("Blender venv missing: python3.13 -m venv art/.venv && art/.venv/bin/pip install -r art/requirements.txt");
  process.exit(1);
}

const registry = JSON.parse(readFileSync(join(root, "art/assets.json"), "utf8"));
const manifest: Manifest = { version: 1, assets: {}, totals: { bytes: 0, triangles: 0 } };
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
  try {
    execFileSync(python, [join(root, "art/build.py"), "--system", systemPath, "--out", out], { stdio: ["ignore", "ignore", "inherit"] });
  } catch {
    console.error(`RESULT: failure — Blender build of ${file} failed (see the checks above)`);
    process.exit(1);
  }
  const report = JSON.parse(readFileSync(join(root, "art/.build", `${id}.report.json`), "utf8"));
  console.log(`${file}: built in ${report.timings_s.total} s`);
  for (const [assetId, a] of Object.entries<any>(report.assets)) {
    const path = join(out, a.envelope);
    const doc = await io.read(path);
    await doc.transform(dedup(), prune({ keepLeaves: true }), weld(), meshopt({ encoder: MeshoptEncoder, level: "medium" }));
    const bytes = await io.writeBinary(doc);
    writeFileSync(path, bytes);
    manifest.assets[assetId] = {
      main: a.main,
      airborne: a.airborne,
      // Blender (x, y, z) Z-up → glTF (x, z, −y) Y-up; a turn about Blender Z is a turn about glTF Y.
      transform: { position: [a.world.position[0], a.world.position[2], -a.world.position[1]], rotationYDeg: a.world.rotationZDeg },
      representations: {
        envelope: {
          file: a.envelope,
          bytes: bytes.byteLength,
          sha256: sha256(bytes),
          parts: a.parts,
          triangles: a.triangles,
          materials: a.materials,
          anchors: a.anchors,
        },
      },
    };
    manifest.totals.bytes += bytes.byteLength;
    manifest.totals.triangles += a.triangles;
  }
}

writeFileSync(join(out, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
console.log(`RESULT: success — ${Object.keys(manifest.assets).length} assets, ${manifest.totals.bytes} bytes, ${manifest.totals.triangles} triangles → ${out}`);
