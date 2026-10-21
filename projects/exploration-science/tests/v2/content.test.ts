import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { contentErrors, systemErrors, type V2Content } from "../../v2/src/content/validate";
import { loadV2Content } from "../../scripts/v2/content";

const root = resolve(import.meta.dirname, "../..");
const load = (): V2Content => loadV2Content(root, "starlink-home");

/** Errors after a mutation of a fresh copy of the committed content. */
function errorsAfter(mutate: (c: V2Content) => void): string[] {
  const c = load();
  mutate(c);
  return contentErrors(c);
}

const object = (c: V2Content, id: string) => c.system.objects.find((o: any) => o.id === id);

describe("v2 content", () => {
  it("accepts the committed starlink-home system", () => {
    expect(contentErrors(load())).toEqual([]);
  });

  it("accepts the Blender test systems", async () => {
    const { readFileSync } = await import("node:fs");
    for (const f of ["art/fixtures/probe.system.json", "art/fixtures/floating.system.json", "art/fixtures/inverted.system.json"]) {
      expect(systemErrors(JSON.parse(readFileSync(resolve(root, f), "utf8")))).toEqual([]);
    }
  });

  it("refuses an object without representation", () => {
    const errors = errorsAfter((c) => (object(c, "house").representations = []));
    expect(errors.some((e) => e.includes("/objects/1/representations"))).toBe(true);
  });

  it("refuses representations without the envelope", () => {
    const errors = errorsAfter((c) => (object(c, "terminal").representations = ["detail"]));
    expect(errors.some((e) => e.includes("/objects/2/representations"))).toBe(true);
  });

  it("refuses an object without a model in art/assets.json", () => {
    const errors = errorsAfter((c) => delete c.assets.assets["house"]);
    expect(errors).toContain("assets: no model for 'house' in art/assets.json");
  });

  it("refuses a connection to an unknown object", () => {
    const errors = errorsAfter((c) => (c.system.connections[0].to = "moon#antenna"));
    expect(errors).toContain("system: connection 'uplink' refers to unknown object 'moon'");
  });

  it("refuses a connection to an undeclared anchor", () => {
    const errors = errorsAfter((c) => (c.system.connections[0].from = "terminal#feed"));
    expect(errors).toContain("system: connection 'uplink' refers to unknown anchor 'terminal#feed'");
  });

  it("refuses a placement on an unknown object or anchor", () => {
    expect(errorsAfter((c) => (object(c, "pine-01").placement.on = "garden"))).toContain(
      "system: 'pine-01' is placed on unknown object 'garden'",
    );
    expect(errorsAfter((c) => (object(c, "terminal").placement.anchor = "chimney"))).toContain(
      "system: 'terminal' is placed on unknown anchor 'house#chimney'",
    );
  });

  it("refuses a support cycle", () => {
    const errors = errorsAfter((c) => (object(c, "house").placement = { on: "terminal", anchor: "beam" }));
    expect(errors.some((e) => e.startsWith("system: support cycle"))).toBe(true);
  });

  it("refuses a broken flow", () => {
    const errors = errorsAfter((c) => (c.system.flows[0].path = ["backhaul", "uplink"]));
    expect(errors).toContain("system: flow 'data-down' is broken between 'backhaul' and 'uplink'");
  });

  it("refuses a tour that starts with an object", () => {
    const errors = errorsAfter((c) => c.tour.steps.splice(0, 2));
    expect(errors).toContain("tour: the first step 'ground-station' must be about the system");
  });

  it("refuses an object that is the subject before being highlighted", () => {
    const errors = errorsAfter((c) => (c.tour.steps[0].highlight = ["house", "terminal", "satellite"]));
    expect(errors).toContain("tour step 'ground-station': 'ground-station' is the subject before a system step has highlighted it");
  });

  it("refuses a main object without a card or a shot", () => {
    expect(errorsAfter((c) => delete c.texts.fr!.cards["satellite"])).toContain("texts.fr: no card for main object 'satellite'");
    expect(errorsAfter((c) => delete c.render.shots["object:satellite"])).toContain(
      "render: no shot 'object:satellite' for main object 'satellite'",
    );
  });

  it("refuses a card figure without a verified fact", () => {
    expect(errorsAfter((c) => (c.texts.fr!.cards["house"].figures[0].factId = "made-up"))).toContain(
      "texts.fr: card 'house' cites unknown fact 'made-up'",
    );
    expect(errorsAfter((c) => (c.sources.facts.find((f: any) => f.id === "power").status = "unverified"))).toContain(
      "texts.fr: card 'house' states unverified fact 'power'",
    );
  });

  it("refuses a missing tour text and a link kind without style", () => {
    expect(errorsAfter((c) => delete c.texts.fr!.entries["tour.overview"])).toContain("texts.fr: missing key 'tour.overview'");
    expect(errorsAfter((c) => delete c.render.linkStyles["fibre"])).toContain("render: no link style for connection kind 'fibre'");
  });
});
