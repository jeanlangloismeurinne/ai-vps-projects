// Reads the V2 content of one system from disk, in the shape the validator expects.
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
  const texts = Object.fromEntries(
    readdirSync(dir)
      .filter((f) => /^texts\.[a-z]{2}\.json$/.test(f))
      .map((f) => [f.split(".")[1]!, read(join(dir, f))]),
  );
  return {
    system: read(join(dir, "systems", `${systemId}.json`)),
    render: read(join(dir, "render.json")),
    tour: read(join(dir, "tours", `${systemId}.json`)),
    texts,
    sources: read(join(dir, "sources.json")),
    assets: read(join(root, "art/assets.json")),
    palette: paletteNames(root),
  };
}
