// Validates one node folder (scene.json, texts.<lang>.json, sources.json) the way
// the content tests do, in the context of the hand-written graph: the candidate
// replaces the node with the same id, so parent links and continuity are checked.
// Used by the generator. Prints {"errors": [...]} on stdout; exit code 1 if any.
//
//   node scripts/validate-node.ts <folder>
import { readFileSync, readdirSync } from "node:fs";
import { basename, join, resolve } from "node:path";
import { ContentValidator, graphErrors, type NodeFiles } from "../engine/src/content/validation.ts";

const ROOT = join(import.meta.dirname, "..");
const readJson = (path: string) => JSON.parse(readFileSync(path, "utf8"));

function readNode(folder: string, dir = basename(folder)): NodeFiles {
  const texts: Record<string, any> = {};
  for (const file of readdirSync(folder)) {
    const lang = /^texts\.([a-z]{2})\.json$/.exec(file)?.[1];
    if (lang) texts[lang] = readJson(join(folder, file));
  }
  return { dir, scene: readJson(join(folder, "scene.json")), texts, sources: readJson(join(folder, "sources.json")) };
}

const folder = process.argv[2];
if (!folder) {
  console.error("usage: node scripts/validate-node.ts <folder>");
  process.exit(2);
}

let errors: string[];
try {
  const candidate = readNode(resolve(folder));
  const id: string = candidate.scene.node.id;
  // The folder name of a generated node is free; the validator checks it against the id.
  candidate.dir = id;
  const validator = new ContentValidator(readJson(join(ROOT, "catalogue/catalogue.json")));
  const nodesDir = join(ROOT, "content/nodes");
  const others = readdirSync(nodesDir, { withFileTypes: true })
    .filter((d) => d.isDirectory() && d.name !== id)
    .map((d) => readNode(join(nodesDir, d.name)));
  const graph = graphErrors([...others, candidate]).filter((e) => e.startsWith(`${id}:`) || e.includes(`'${id}'`));
  errors = [...validator.nodeErrors(candidate), ...graph];
} catch (error) {
  errors = [`cannot read the node: ${error instanceof Error ? error.message : String(error)}`];
}
console.log(JSON.stringify({ errors }, null, 2));
process.exit(errors.length > 0 ? 1 : 0);
