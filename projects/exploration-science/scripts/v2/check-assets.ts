// npm run check:assets [-- --determinism]
// Checks the models of every system (public/v2/models/<system id>/) against the palette and
// the budgets (per scene). With --determinism, also rebuilds everything twice in temporary
// directories and compares the hashes.
import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, readdirSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { checkAssets, type Manifest } from "./assetChecks.ts";

const root = resolve(import.meta.dirname, "../..");
const models = join(root, "public/v2/models");

function paletteNames(): Set<string> {
  const p = JSON.parse(readFileSync(join(root, "art/palette.json"), "utf8"));
  return new Set([...Object.keys(p.neutrals), ...Object.keys(p.accents), ...Object.keys(p.special)]);
}

const systems = readdirSync(models).filter((d) => existsSync(join(models, d, "manifest.json")));

function hashes(dir: string): Record<string, string> {
  return Object.fromEntries(
    systems.flatMap((system) => {
      const path = join(dir, system, "manifest.json");
      if (!existsSync(path)) return [];
      const m: Manifest = JSON.parse(readFileSync(path, "utf8"));
      return Object.entries(m.assets).flatMap(([id, a]) => Object.entries(a.representations).map(([k, r]) => [`${system}/${id}.${k}`, r.sha256]));
    }),
  );
}

const errors: string[] = [];
const summary: string[] = [];
for (const system of systems) {
  const dir = join(models, system);
  const manifest: Manifest = JSON.parse(readFileSync(join(dir, "manifest.json"), "utf8"));
  const found = await checkAssets(
    manifest,
    (file) => (existsSync(join(dir, file)) ? readFileSync(join(dir, file)) : null),
    paletteNames(),
    JSON.parse(readFileSync(join(root, "art/budgets.json"), "utf8")),
  );
  errors.push(...found.map((e) => `${system}: ${e}`));
  summary.push(`${system}: ${Object.keys(manifest.assets).length} assets, ${manifest.totals.bytes} bytes, ${manifest.totals.triangles} triangles`);
}

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
console.log(`RESULT: success — ${summary.join(" ; ")}`);
