// The v2 content the app reads, bundled at build time (validated by `npm test`).
import palette from "../../../art/palette.json";
import render from "../../../content/v2/render.json";
import sources from "../../../content/v2/sources.json";
import system from "../../../content/v2/systems/starlink-home.json";
import textsFr from "../../../content/v2/texts.fr.json";
import tour from "../../../content/v2/tours/starlink-home.json";

export { render, sources, system, tour };

/** Texts of the interface language (French only for now, the structure is per language). */
export const texts = textsFr;
export type Card = (typeof textsFr.cards)["house"];

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
