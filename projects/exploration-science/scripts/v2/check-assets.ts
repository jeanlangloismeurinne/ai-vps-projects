// npm run check:assets [-- --determinism]
// Checks public/v2/models against the palette and the budgets. With --determinism,
// also rebuilds everything twice in temporary directories and compares the hashes.
import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { checkAssets, type Manifest } from "./assetChecks.ts";

const root = resolve(import.meta.dirname, "../..");
const models = join(root, "public/v2/models");

function paletteNames(): Set<string> {
  const p = JSON.parse(readFileSync(join(root, "art/palette.json"), "utf8"));
  return new Set([...Object.keys(p.neutrals), ...Object.keys(p.accents), ...Object.keys(p.special)]);
}

function hashes(dir: string): Record<string, string> {
  const m: Manifest = JSON.parse(readFileSync(join(dir, "manifest.json"), "utf8"));
  return Object.fromEntries(Object.entries(m.assets).flatMap(([id, a]) => Object.entries(a.representations).map(([k, r]) => [`${id}.${k}`, r.sha256])));
}

const manifest: Manifest = JSON.parse(readFileSync(join(models, "manifest.json"), "utf8"));
const errors = await checkAssets(
  manifest,
  (file) => (existsSync(join(models, file)) ? readFileSync(join(models, file)) : null),
  paletteNames(),
  JSON.parse(readFileSync(join(root, "art/budgets.json"), "utf8")),
);

if (process.argv.includes("--determinism")) {
  const runs = [0, 1].map(() => mkdtempSync(join(tmpdir(), "xs-assets-")));
  for (const dir of runs) execFileSync("node", [join(root, "scripts/v2/assets.ts"), "--out", dir], { stdio: "ignore" });
  const [a, b] = runs.map(hashes);
  const committed = hashes(models);
  for (const key of Object.keys(committed)) {
    if (a![key] !== b![key]) errors.push(`not deterministic: ${key} differs between two builds`);
    else if (a![key] !== committed[key]) errors.push(`stale: ${key} rebuilt differs from public/v2/models (run npm run assets)`);
  }
  for (const dir of runs) rmSync(dir, { recursive: true, force: true });
}

if (errors.length) {
  for (const e of errors) console.error(`  - ${e}`);
  console.error(`RESULT: failure — ${errors.length} asset check(s) failed`);
  process.exit(1);
}
console.log(`RESULT: success — ${Object.keys(manifest.assets).length} assets, ${manifest.totals.bytes} bytes, ${manifest.totals.triangles} triangles`);
