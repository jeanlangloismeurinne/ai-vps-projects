// Builds the review page: one self-contained HTML file showing schemas, catalogue
// and every node in readable form. Run with `npm run review`.
// Outputs dist-review/index.html (standalone) and dist-review/review.html
// (body only, for publishing where the host adds the document skeleton).
import { execSync } from "node:child_process";
import { mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import katex from "katex";
import { ContentValidator } from "../engine/src/content/validation.ts";

const ROOT = join(import.meta.dirname, "..");
const readJson = (path: string) => JSON.parse(readFileSync(join(ROOT, path), "utf8"));

// Formulas are pre-rendered to MathML: browsers display it natively, no font or CSS to ship.
const formulas: Record<string, string> = {};
function collectFormula(tex: string): void {
  formulas[tex] ??= katex.renderToString(tex, { output: "mathml", throwOnError: false });
}

const catalogue = readJson("catalogue/catalogue.json");
const validator = new ContentValidator(catalogue);
function collectTerms(terms: { symbol: string }[] | undefined): void {
  for (const t of terms ?? []) collectFormula(t.symbol);
}
for (const sim of catalogue.simulators) {
  for (const eq of sim.equations) {
    collectFormula(eq.tex);
    collectTerms(eq.terms);
  }
}

const nodes = readdirSync(join(ROOT, "content/nodes"), { withFileTypes: true })
  .filter((d) => d.isDirectory())
  .map((d) => {
    const dir = d.name;
    const base = `content/nodes/${dir}`;
    const texts: Record<string, any> = {};
    for (const file of readdirSync(join(ROOT, base))) {
      const lang = /^texts\.([a-z]{2})\.json$/.exec(file)?.[1];
      if (lang) texts[lang] = readJson(`${base}/${file}`);
    }
    const node = { dir, scene: readJson(`${base}/scene.json`), texts, sources: readJson(`${base}/sources.json`) };
    for (const t of Object.values(texts)) {
      for (const entries of [t.common, ...Object.values<any>(t.levels)]) {
        for (const entry of Object.values<any>(entries)) {
          if (typeof entry !== "object") continue;
          for (const m of (entry.subtitle ?? "").matchAll(/\$([^$]+)\$/g)) collectFormula(m[1]);
          collectTerms(entry.terms);
        }
      }
    }
    return { ...node, errors: validator.nodeErrors(node) };
  });

let commit = "";
try {
  commit = execSync("git rev-parse --short HEAD", { cwd: ROOT }).toString().trim();
} catch {
  // Not a git checkout: leave the commit empty.
}

const data = {
  generatedAt: new Date().toISOString(),
  commit,
  catalogue,
  catalogueErrors: validator.catalogueErrors(),
  schemas: {
    scene: readJson("schemas/scene.schema.json"),
    catalogue: readJson("schemas/catalogue.schema.json"),
    texts: readJson("schemas/texts.schema.json"),
    sources: readJson("schemas/sources.schema.json"),
  },
  nodes,
  formulas,
};

const template = readFileSync(join(ROOT, "scripts/review-template.html"), "utf8");
const json = JSON.stringify(data).replace(/</g, "\\u003c");
const body = template.replace("/*__DATA__*/null", () => json);
const standalone = `<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n</head>\n<body>\n${body}\n</body>\n</html>\n`;

const out = join(ROOT, "dist-review");
mkdirSync(out, { recursive: true });
writeFileSync(join(out, "review.html"), body);
writeFileSync(join(out, "index.html"), standalone);
const errorCount = data.catalogueErrors.length + nodes.reduce((n, node) => n + node.errors.length, 0);
console.log(`dist-review/index.html — ${nodes.length} nodes, ${errorCount} validation errors`);
