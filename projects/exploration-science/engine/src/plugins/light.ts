// Light as a spectrum, and how it looks: shared by the plugins that compute
// colours from physics (a star's colour, the sky's colour) instead of picking them.

/** Visible range sampled by the plugins, in nm. */
export const VISIBLE_MIN_NM = 380;
export const VISIBLE_MAX_NM = 750;
export const SAMPLE_STEP_NM = 10;
export const WAVELENGTHS_NM: number[] = [];
for (let l = VISIBLE_MIN_NM; l <= VISIBLE_MAX_NM; l += SAMPLE_STEP_NM) WAVELENGTHS_NM.push(l);

const H = 6.62607015e-34; // Planck constant, J·s
const C = 299_792_458; // speed of light, m/s
const K_B = 1.380649e-23; // Boltzmann constant, J/K

/** Black-body spectral radiance (Planck's law), W·sr⁻¹·m⁻³. */
export function planck(wavelengthNm: number, temperatureK: number): number {
  const l = wavelengthNm * 1e-9;
  return (2 * H * C * C) / l ** 5 / Math.expm1((H * C) / (l * K_B * temperatureK));
}

// CIE 1931 2° colour-matching functions, multi-lobe Gaussian fit
// (Wyman, Sloan & Shirley, JCGT 2(2), 2013).
const lobe = (x: number, mu: number, s1: number, s2: number) => {
  const t = (x - mu) / (x < mu ? s1 : s2);
  return Math.exp(-0.5 * t * t);
};
export function cmf(nm: number): [number, number, number] {
  return [
    1.056 * lobe(nm, 599.8, 37.9, 31.0) + 0.362 * lobe(nm, 442.0, 16.0, 26.7) - 0.065 * lobe(nm, 501.1, 20.4, 26.2),
    0.821 * lobe(nm, 568.8, 46.9, 40.5) + 0.286 * lobe(nm, 530.9, 16.3, 31.1),
    1.217 * lobe(nm, 437.0, 11.8, 36.0) + 0.681 * lobe(nm, 459.0, 26.0, 13.8),
  ];
}

/** Tristimulus XYZ of a spectrum sampled on WAVELENGTHS_NM. */
export function spectrumToXyz(spectrum: readonly number[]): [number, number, number] {
  let x = 0;
  let y = 0;
  let z = 0;
  WAVELENGTHS_NM.forEach((nm, i) => {
    const [cx, cy, cz] = cmf(nm);
    const s = spectrum[i] ?? 0;
    x += cx * s;
    y += cy * s;
    z += cz * s;
  });
  return [x * SAMPLE_STEP_NM, y * SAMPLE_STEP_NM, z * SAMPLE_STEP_NM];
}

/** XYZ to linear sRGB (IEC 61966-2-1 matrix), negatives clipped. */
export function xyzToLinearRgb([x, y, z]: readonly number[]): [number, number, number] {
  return [
    Math.max(0, 3.2406 * x! - 1.5372 * y! - 0.4986 * z!),
    Math.max(0, -0.9689 * x! + 1.8758 * y! + 0.0415 * z!),
    Math.max(0, 0.0557 * x! - 0.204 * y! + 1.057 * z!),
  ];
}

/** Hue of a colour at full brightness: the largest channel set to 1. */
export function normalised(rgb: readonly number[]): [number, number, number] {
  const m = Math.max(...rgb, 1e-12);
  return [rgb[0]! / m, rgb[1]! / m, rgb[2]! / m];
}

/** Colour of one wavelength, at full brightness (linear sRGB). */
export function wavelengthColour(nm: number): [number, number, number] {
  return normalised(xyzToLinearRgb(cmf(nm)));
}

/** Hex string of a linear sRGB colour (values clipped to [0, 1]). */
export function toHex(linear: readonly number[]): string {
  const encode = (c: number) => {
    const v = Math.min(1, Math.max(0, c));
    const s = v <= 0.0031308 ? 12.92 * v : 1.055 * v ** (1 / 2.4) - 0.055;
    return Math.round(s * 255)
      .toString(16)
      .padStart(2, "0");
  };
  return `#${linear.map(encode).join("")}`;
}
