// Reads the V2 content of one system from disk, in the shape the validator expects. One file
// per nature of data and per system: systems/<id>.json, render/<id>.json, tours/<id>.json,
// texts/<id>.<lang>.json, sources/<id>.json.
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import type { V2Content } from "../../v2/src/content/validate.ts";

const read = (path: string) => JSON.parse(readFileSync(path, "utf8"));

export function paletteNames(root: string): Set<string> {
  const p = read(join(root, "art/palette.json"));
  return new Set([...Object.keys(p.neutrals), ...Object.keys(p.accents), ...Object.keys(p.special)]);
}

export function loadV2Content(root: string, systemId: string): V2Content {
  const dir = join(root, "content/v2");
  const pattern = new RegExp(`^${systemId}\\.([a-z]{2})\\.json$`);
  const texts = Object.fromEntries(
    readdirSync(join(dir, "texts"))
      .map((f) => [f.match(pattern)?.[1], f] as const)
      .filter(([lang]) => lang)
      .map(([lang, f]) => [lang!, read(join(dir, "texts", f))]),
  );
  return {
    system: read(join(dir, "systems", `${systemId}.json`)),
    render: read(join(dir, "render", `${systemId}.json`)),
    tour: read(join(dir, "tours", `${systemId}.json`)),
    texts,
    sources: read(join(dir, "sources", `${systemId}.json`)),
    assets: read(join(root, "art/assets.json")),
    palette: paletteNames(root),
  };
}

/** Ids of the systems that have a file in content/v2/systems/. */
export function systemIds(root: string): string[] {
  return readdirSync(join(root, "content/v2/systems"))
    .filter((f) => f.endsWith(".json"))
    .map((f) => f.slice(0, -5));
}
