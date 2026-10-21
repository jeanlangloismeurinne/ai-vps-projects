// The v2 content the app reads, bundled at build time (validated by `npm test`).
import palette from "../../../art/palette.json";
import render from "../../../content/v2/render.json";
import system from "../../../content/v2/systems/starlink-home.json";

export { render, system };

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
