// The v2 content the app reads, bundled at build time (validated by `npm test`). Every system
// of content/v2/ is bundled; `?system=<id>` picks the one shown (default: starlink-home).
import palette from "../../../art/palette.json";
import type starlinkRender from "../../../content/v2/render/starlink-home.json";
import type starlinkSources from "../../../content/v2/sources/starlink-home.json";
import type starlinkSystem from "../../../content/v2/systems/starlink-home.json";
import type starlinkTexts from "../../../content/v2/texts/starlink-home.fr.json";
import type starlinkTour from "../../../content/v2/tours/starlink-home.json";

export const DEFAULT_SYSTEM = "starlink-home";

const byId = <T>(files: Record<string, unknown>, suffix: string): Record<string, T> =>
  Object.fromEntries(Object.entries(files).map(([path, json]) => [path.split("/").pop()!.slice(0, -suffix.length), json as T]));

const systems = byId<typeof starlinkSystem>(import.meta.glob("../../../content/v2/systems/*.json", { eager: true, import: "default" }), ".json");
const renders = byId<typeof starlinkRender>(import.meta.glob("../../../content/v2/render/*.json", { eager: true, import: "default" }), ".json");
const tours = byId<typeof starlinkTour>(import.meta.glob("../../../content/v2/tours/*.json", { eager: true, import: "default" }), ".json");
const allSources = byId<typeof starlinkSources>(import.meta.glob("../../../content/v2/sources/*.json", { eager: true, import: "default" }), ".json");
/** Texts of the interface language (French only for now, the structure is per language). */
const textsFr = byId<typeof starlinkTexts>(import.meta.glob("../../../content/v2/texts/*.fr.json", { eager: true, import: "default" }), ".fr.json");

/** Ids of the bundled systems. */
export const systemIds = Object.keys(systems);
const requested = new URLSearchParams(window.location.search).get("system") ?? DEFAULT_SYSTEM;
if (!systems[requested]) throw new Error(`unknown system: ${requested} (known: ${systemIds.join(", ")})`);
export const systemId = requested;

export const system = systems[systemId]!;
export const render = renders[systemId]!;
export const tour = tours[systemId]!;
export const sources = allSources[systemId]!;
export const texts = textsFr[systemId]!;
export type Card = (typeof starlinkTexts.cards)["house"];

export const mainIds: string[] = system.objects.filter((o) => o.role === "main").map((o) => o.id);

/** Publishers behind the figures of a card, and whether some figures are computed. */
export function cardSources(card: Card): { publishers: string[]; computed: boolean } {
  const publishers = new Set<string>();
  let computed = false;
  for (const fig of card.figures) {
    const fact = sources.facts.find((f) => f.id === fig.factId);
    if (!fact) continue;
    if (fact.status === "computed") computed = true;
    for (const id of fact.sources) {
      const src = sources.sources.find((s) => s.id === id);
      if (src) publishers.add(src.publisher);
    }
  }
  return { publishers: [...publishers], computed };
}

export type Swatch = keyof typeof palette.neutrals | keyof typeof palette.accents | keyof typeof palette.special;

const swatches: Record<string, { color: string }> = { ...palette.neutrals, ...palette.accents, ...palette.special };

/** sRGB hex of a palette swatch. */
export function swatch(name: string): string {
  const s = swatches[name];
  if (!s) throw new Error(`unknown palette swatch: ${name}`);
  return s.color;
}

export const background = palette.background;

export type Shot = (typeof render.shots)["global"];
