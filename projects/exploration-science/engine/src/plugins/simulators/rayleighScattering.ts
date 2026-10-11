import { BufferAttribute, Mesh, Vector3, type Object3D } from "three";
import type { BoundEntity, SimulatorPlugin } from "../../core/registry";
import { WAVE_FIELD, type WaveField } from "../channels";
import { normalised, planck, spectrumToXyz, toHex, VISIBLE_MIN_NM, WAVELENGTHS_NM, wavelengthColour, xyzToLinearRgb } from "../light";
import { tint } from "../tint";

// Single scattering of sunlight by air molecules (Rayleigh regime), catalogue
// equations: scattered intensity ∝ I0/λ⁴, direct light I0·e^(−βs), β ∝ λ⁻⁴.
// The air is an exponential atmosphere over a flat ground; colours come from the
// computed spectra through the CIE colour-matching functions, never picked by hand.

const DEG = Math.PI / 180;
/** Rayleigh optical depth of the whole atmosphere, vertically, at 550 nm (sea level). */
export const TAU_550 = 0.0973;
/** Scale height of the air density, m. */
export const SCALE_HEIGHT_M = 8000;
export const R_EARTH_M = 6_371_000;
/** Effective temperature of the Sun, K: its light is close to a black body's. */
export const SUN_TEMPERATURE_K = 5772;
/** Apparent radius of the solar disc, deg. */
const SUN_RADIUS_DEG = 0.27;

/** Vertical optical depth τ(λ) = τ550·(550/λ)⁴, times the density factor. */
export function opticalDepth(wavelengthNm: number, densityFactor = 1): number {
  return TAU_550 * densityFactor * (550 / wavelengthNm) ** 4;
}

/** Relative air mass along a line of sight at this elevation (Kasten & Young, 1989); 1 at the zenith. */
export function airMass(elevationDeg: number): number {
  const h = Math.max(elevationDeg, 0);
  return 1 / (Math.sin(h * DEG) + 0.50572 * (h + 6.07995) ** -1.6364);
}

/** Direct sunlight left after crossing the air: I/I0 = e^(−τ m). */
export function transmittance(wavelengthNm: number, sunElevationDeg: number, densityFactor = 1): number {
  return Math.exp(-opticalDepth(wavelengthNm, densityFactor) * airMass(sunElevationDeg));
}

/**
 * Share of the column's optical depth still in sunlight. With the Sun below the
 * horizon, the Earth's shadow covers the air up to z = R(1/cos h − 1).
 */
export function litFraction(sunElevationDeg: number): number {
  if (sunElevationDeg >= 0) return 1;
  const z = R_EARTH_M * (1 / Math.cos(sunElevationDeg * DEG) - 1);
  return Math.exp(-z / SCALE_HEIGHT_M);
}

/** Rayleigh phase function, mean 1 over the sphere: ¾(1 + cos²Θ). */
export const rayleighPhase = (cosTheta: number) => 0.75 * (1 + cosTheta * cosTheta);

/**
 * Sky radiance relative to the sunlight, for one wavelength, seen along a line of
 * sight at elevation e (air mass mv) with scattering angle Θ. x is the vertical
 * optical depth above a scattering point: sunlight reaches it as e^(−m x), the
 * scattered light reaches the observer as e^(−mv (τ − x)), and the line of sight
 * gathers mv·dx of scattering:
 *   L = P(Θ) · mv · ∫₀^xs e^(−m x) e^(−mv (τ − x)) dx
 */
export function skyRadiance(wavelengthNm: number, sunElevationDeg: number, viewElevationDeg: number, cosTheta: number, densityFactor = 1): number {
  const tau = opticalDepth(wavelengthNm, densityFactor);
  if (tau === 0) return 0;
  const m = airMass(sunElevationDeg);
  const mv = airMass(viewElevationDeg);
  const xs = tau * litFraction(sunElevationDeg);
  const d = mv - m;
  const integral = Math.abs(d) < 1e-9 ? Math.exp(-mv * tau) * xs : (Math.exp(-mv * tau) * Math.expm1(d * xs)) / d;
  return rayleighPhase(cosTheta) * mv * integral;
}

/** Unit vector towards the Sun, seen from the observer: horizontal direction (x, z), elevation h. */
function sunDirection(horizontal: Vector3, elevationDeg: number, out = new Vector3()): Vector3 {
  const c = Math.cos(elevationDeg * DEG);
  return out.set(horizontal.x * c, Math.sin(elevationDeg * DEG), horizontal.z * c);
}

// Sunlight is normalised so its luminance Y is 1: colours are relative to it.
const SUN_SPECTRUM = WAVELENGTHS_NM.map((nm) => planck(nm, SUN_TEMPERATURE_K));
const SUN_Y = spectrumToXyz(SUN_SPECTRUM)[1];
const I0 = SUN_SPECTRUM.map((v) => v / SUN_Y);

/** Linear sRGB of the sky along a line of sight, before exposure. */
export function skyColour(sunElevationDeg: number, viewElevationDeg: number, cosTheta: number, densityFactor = 1): [number, number, number] {
  const spectrum = WAVELENGTHS_NM.map((nm, i) => I0[i]! * skyRadiance(nm, sunElevationDeg, viewElevationDeg, cosTheta, densityFactor));
  return xyzToLinearRgb(spectrumToXyz(spectrum));
}

/** Linear sRGB of the direct sunlight reaching the ground (its luminance is the share left). */
export function sunColour(sunElevationDeg: number, densityFactor = 1): [number, number, number] {
  const visible = Math.min(1, Math.max(0, (sunElevationDeg + SUN_RADIUS_DEG) / (2 * SUN_RADIUS_DEG)));
  const spectrum = WAVELENGTHS_NM.map((nm, i) => I0[i]! * transmittance(nm, sunElevationDeg, densityFactor) * visible);
  return xyzToLinearRgb(spectrumToXyz(spectrum));
}

/** Fixed exposure: the zenith sky with the Sun at 45° shows at this luminance. Twilight is darker, as it is. */
const SKY_DISPLAY_Y = 0.42;
const REFERENCE_Y = (() => {
  const [r, g, b] = skyColour(45, 90, Math.cos(45 * DEG));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
})();
export const SKY_EXPOSURE = SKY_DISPLAY_Y / REFERENCE_Y;

/** Displayed colour: exposed, and brought back into gamut by its largest channel (hue kept). */
export function exposed(rgb: readonly number[]): [number, number, number] {
  const scaled = rgb.map((c) => c * SKY_EXPOSURE);
  const m = Math.max(1, ...scaled);
  return [scaled[0]! / m, scaled[1]! / m, scaled[2]! / m];
}

/** Scattered amplitude of one molecule, relative to the shortest visible wavelength: ∝ 1/λ² (intensity ∝ 1/λ⁴). */
export const scatteredAmplitude = (wavelengthNm: number) => (VISIBLE_MIN_NM / wavelengthNm) ** 2;

interface SkyMesh {
  colours: BufferAttribute;
  /** Unit directions from the observer to each vertex. */
  directions: Vector3[];
}

export const rayleighScattering: SimulatorPlugin = {
  id: "rayleigh-scattering",
  create(initial, ctx) {
    const params = { ...initial } as { sunElevationDeg: number; wavelengthNm: number; airDensityFactor: number };
    const [sun] = ctx.bound("sun");
    const [atmosphere] = ctx.bound("atmosphere");
    const [observer] = ctx.bound("observer");
    const molecules = ctx.bound("molecules");
    if (!sun || !atmosphere || !observer) throw new Error("rayleigh-scattering: sun, atmosphere and observer must be bound");

    const eye = new Vector3();
    const toSun = new Vector3();
    const world = new Vector3();
    observer.node.updateWorldMatrix(true, true);
    observer.node.getWorldPosition(eye);
    // The Sun keeps the azimuth and distance the scene gives it; the simulator sets its elevation.
    sun.node.updateWorldMatrix(true, false);
    const initialOffset = sun.node.getWorldPosition(new Vector3()).sub(eye);
    const sunDistance = initialOffset.length();
    const horizontal = new Vector3(initialOffset.x, 0, initialOffset.z);
    if (horizontal.lengthSq() < 1e-12) horizontal.set(0, 0, -1);
    horizontal.normalize();

    // Each sky vertex is a line of sight from the observer.
    atmosphere.node.updateWorldMatrix(true, true);
    const skies: SkyMesh[] = [];
    atmosphere.object.traverse((o: Object3D) => {
      if (!(o instanceof Mesh) || !o.userData.sky) return;
      const position = o.geometry.getAttribute("position") as BufferAttribute;
      const colours = o.geometry.getAttribute("color") as BufferAttribute | undefined;
      if (!colours) return;
      const directions: Vector3[] = [];
      for (let i = 0; i < position.count; i++) directions.push(world.fromBufferAttribute(position, i).applyMatrix4(o.matrixWorld).sub(eye).normalize().clone());
      skies.push({ colours, directions });
    });

    let shown = "";
    const refresh = () => {
      const h = params.sunElevationDeg;
      const density = params.airDensityFactor;
      sunDirection(horizontal, h, toSun);
      const position = eye.clone().addScaledVector(toSun, sunDistance);
      sun.node.parent ? sun.node.position.copy(sun.node.parent.worldToLocal(position)) : sun.node.position.copy(position);
      for (const m of molecules) m.object.visible = density > 0;

      const key = `${h}|${density}`;
      if (key === shown) return;
      shown = key;
      const direct = sunColour(h, density);
      const luminance = 0.2126 * direct[0] + 0.7152 * direct[1] + 0.0722 * direct[2];
      tint(sun.object, normalised(direct), luminance);
      // Colours depend on elevation and scattering angle only: sample them once per (row, angle) bucket.
      const cache = new Map<string, [number, number, number]>();
      for (const sky of skies) {
        sky.directions.forEach((d, i) => {
          const e = Math.asin(Math.max(-1, Math.min(1, d.y))) / DEG;
          const cosTheta = d.dot(toSun);
          const k = `${e.toFixed(1)}|${cosTheta.toFixed(3)}`;
          let c = cache.get(k);
          if (!c) cache.set(k, (c = exposed(skyColour(h, Math.max(e, 0), cosTheta, density))));
          sky.colours.setXYZ(i, c[0], c[1], c[2]);
        });
        sky.colours.needsUpdate = true;
      }
    };
    refresh();

    const visibleBubble = (): BoundEntity | undefined =>
      molecules.find((m) => {
        if (!m.magnifier) return false;
        for (let o: Object3D | null = m.node; o; o = o.parent) if (!o.visible) return false;
        return m.object.visible;
      });

    return {
      params,
      set(param, value) {
        (params as Record<string, unknown>)[param] = value;
        refresh();
      },
      update() {
        refresh();
      },
      outputs() {
        const h = params.sunElevationDeg;
        sunDirection(horizontal, h, toSun);
        const zenith = WAVELENGTHS_NM.map((nm, i) => I0[i]! * skyRadiance(nm, h, 90, toSun.y, params.airDensityFactor));
        const peak = Math.max(...zenith, 1e-30);
        return {
          skyColor: toHex(exposed(xyzToLinearRgb(spectrumToXyz(zenith)))),
          sunColor: toHex(normalised(sunColour(h, params.airDensityFactor))),
          spectrum: zenith.map((v) => v / peak),
        };
      },
      channel(name) {
        if (name !== WAVE_FIELD) return undefined;
        const bubble = visibleBubble();
        if (!bubble?.magnifier || params.airDensityFactor <= 0) return undefined;
        const origin = bubble.node.getWorldPosition(new Vector3());
        const incident = origin.clone().sub(sun.node.getWorldPosition(new Vector3())).normalize();
        // The slice holds the incoming light and the line towards the observer: the light that reaches the eye.
        const normal = eye.clone().sub(origin).normalize();
        const axis = incident.clone().addScaledVector(normal, -incident.dot(normal));
        if (axis.lengthSq() < 1e-9) axis.set(1, 0, 0).addScaledVector(normal, -normal.x);
        axis.normalize();
        const field: WaveField = {
          wavelength: (params.wavelengthNm * 1e-9) / bubble.magnifier.metersPerUnit,
          origin,
          normal,
          axis,
          count: 1,
          spacing: 0,
          phaseStep: 0,
          steeringDeg: null,
          gratingLobesDeg: [],
          amplitude: scatteredAmplitude(params.wavelengthNm),
          colour: wavelengthColour(params.wavelengthNm),
          incident: { direction: incident, amplitude: 1 },
          discRadius: bubble.magnifier.radius,
        };
        return field;
      },
    };
  },
};
