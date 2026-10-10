import { readdirSync, readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { ContentValidator, type NodeFiles } from "../engine/src/content/validation";

const ROOT = join(import.meta.dirname, "..");
const NODES_DIR = join(ROOT, "content", "nodes");

const readJson = (path: string) => JSON.parse(readFileSync(path, "utf8"));

function loadNode(dir: string): NodeFiles {
  const base = join(NODES_DIR, dir);
  const texts: NodeFiles["texts"] = {};
  for (const file of readdirSync(base)) {
    const match = /^texts\.([a-z]{2})\.json$/.exec(file);
    if (match) texts[match[1]!] = readJson(join(base, file));
  }
  return { dir, scene: readJson(join(base, "scene.json")), texts, sources: readJson(join(base, "sources.json")) };
}

const catalogue = readJson(join(ROOT, "catalogue", "catalogue.json"));
const validator = new ContentValidator(catalogue);
const nodeDirs = readdirSync(NODES_DIR, { withFileTypes: true })
  .filter((d) => d.isDirectory())
  .map((d) => d.name);

describe("catalogue", () => {
  it("is valid", () => {
    expect(validator.catalogueErrors()).toEqual([]);
  });
});

describe("nodes", () => {
  it("exist", () => {
    expect(nodeDirs.length).toBeGreaterThan(0);
  });

  describe.each(nodeDirs)("%s", (dir) => {
    it("has scene.json, sources.json and French texts", () => {
      for (const file of ["scene.json", "sources.json", "texts.fr.json"]) {
        expect(existsSync(join(NODES_DIR, dir, file)), file).toBe(true);
      }
    });

    it("is valid against schemas and catalogue", () => {
      expect(validator.nodeErrors(loadNode(dir))).toEqual([]);
    });
  });
});

describe("validator catches broken content", () => {
  const broken = (mutate: (node: NodeFiles) => void): string[] => {
    const node = structuredClone(loadNode("starlink-terminal"));
    mutate(node);
    return validator.nodeErrors(node);
  };
  const entity = (node: NodeFiles, id: string) => node.scene.entities.find((e: { id: string }) => e.id === id);

  it.each<[string, (node: NodeFiles) => void, RegExp]>([
    ["raw text in a scene", (n) => (entity(n, "terminal").label = "Antenne"), /additional properties/],
    ["wrong formatVersion", (n) => (n.scene.formatVersion = "0.1"), /constant/],
    ["unknown component", (n) => (entity(n, "house").component = "castle"), /unknown component 'castle'/],
    ["param outside validity range", (n) => (entity(n, "terminal").params.tiltDeg = 120), /must be <= 90/],
    ["dangling entity reference", (n) => (entity(n, "terminal-cable").params.to = "nowhere"), /unknown entity 'nowhere'/],
    ["role bound to wrong component", (n) => (n.scene.simulators[0].bind.array = "terminal"), /expected antenna-element-array/],
    ["control wider than catalogue", (n) => (n.scene.lenses[0].controls[0].max = 89), /max above validity range/],
    ["unsupported reveal", (n) => n.scene.tours[1].steps[0].actions.push({ type: "reveal", target: "router", mode: "cutaway" }), /cannot 'cutaway'/],
    ["setParam out of range", (n) => n.scene.tours[1].steps[0].actions.push({ type: "setParam", target: "beam", param: "spacingOverLambda", value: 5 }), /must be <= 2/],
    ["missing text for a level", (n) => delete n.texts.fr!.levels.essential["play.contact"], /'play.contact' missing for level 'essential'/],
    ["unused text key", (n) => (n.texts.fr!.common["orphan.key"] = "x"), /'orphan.key' is not used/],
    ["intro tour too long", (n) => (n.scene.tours[0].steps[0].durationS = 40), /expected 20-30 s/],
    ["equation without terms", (n) => delete n.texts.fr!.levels.advanced["play.contact"].terms, /equation without terms/],
    ["undefined symbol", (n) => n.texts.fr!.levels.advanced["play.contact"].terms.pop(), /symbol 'T' is not defined/],
    ["unused term", (n) => n.texts.fr!.levels.advanced["play.contact"].terms.push({ symbol: "x", meaning: "x" }), /term 'x' does not appear/],
    ["notation in spoken text", (n) => (n.texts.fr!.levels.advanced["play.contact"].text = "v = $\\sqrt{\\mu}$"), /must not contain notation/],
    ["explorable phrase absent", (n) => (n.texts.fr!.levels.advanced["play.contact"].links[0].phrase = "orbite elliptique"), /not found in the displayed text/],
    ["explorable node undeclared", (n) => (n.texts.fr!.levels.advanced["play.contact"].links[0].node = "kepler-laws"), /not declared in the scene links/],
    ["verified fact without source", (n) => (n.sources.facts[0].sources = []), /verified without source/],
  ])("%s", (_name, mutate, expected) => {
    expect(broken(mutate).join("\n")).toMatch(expected);
  });
});

describe("validator catches broken catalogue", () => {
  it("rejects an equation term that is not defined", () => {
    const broken = structuredClone(catalogue);
    broken.simulators[0].equations[0].terms.pop();
    expect(new ContentValidator(broken).catalogueErrors().join("\n")).toMatch(/is not defined in terms/);
  });
});
