// Scale bar: a round length (1, 2 or 5 × 10^n metres) whose on-screen size stays
// within a readable range, labelled in the unit a reader would use for it.

export interface ScaleBar {
  metres: number;
  pixels: number;
  label: string;
}

const STEPS = [1, 2, 5];
const UNITS: [number, string][] = [
  [1000, "km"],
  [1, "m"],
  [0.01, "cm"],
  [0.001, "mm"],
  [1e-6, "µm"],
  [1e-9, "nm"],
];

/** The largest round length not wider than maxPixels, given metres per CSS pixel. */
export function scaleBar(metresPerPixel: number, maxPixels = 120): ScaleBar {
  const max = metresPerPixel * maxPixels;
  let exponent = Math.floor(Math.log10(max));
  let metres = 10 ** exponent;
  for (;;) {
    const candidates = STEPS.map((s) => s * 10 ** exponent).filter((m) => m <= max * (1 + 1e-9));
    if (candidates.length > 0) {
      metres = candidates[candidates.length - 1]!;
      break;
    }
    exponent -= 1;
  }
  return { metres, pixels: metres / metresPerPixel, label: formatLength(metres) };
}

export function formatLength(metres: number): string {
  const [factor, unit] = UNITS.find(([f]) => metres >= f * (1 - 1e-9)) ?? UNITS[UNITS.length - 1]!;
  const value = Number((metres / factor).toPrecision(3));
  return `${value.toLocaleString("fr-FR")} ${unit}`;
}

/** The unit a level of the breadcrumb is named after, from its real size per scene unit. */
export function scaleUnit(metersPerUnit: number): string {
  return (UNITS.find(([f]) => metersPerUnit >= f * (1 - 1e-9)) ?? UNITS[UNITS.length - 1]!)[1];
}
