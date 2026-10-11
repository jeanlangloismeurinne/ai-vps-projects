import type { Vector3 } from "three";

// Data contracts between simulators and lenses, one per catalogue channel.
// A simulator that `provides` a channel returns this shape from channel(name);
// a lens that `consumes` it reads it.

/**
 * "wave-field": a line of identical point sources in a plane. Source n sits at
 * origin + (n − (count − 1)/2)·spacing·axis and emits with phase −n·phaseStep.
 */
export interface WaveField {
  /** Scene units. */
  wavelength: number;
  /** World position of the line's centre. */
  origin: Vector3;
  /** World unit vector the sources radiate around (the array normal). */
  normal: Vector3;
  /** World unit vector along which the sources are lined up. */
  axis: Vector3;
  count: number;
  /** Scene units. */
  spacing: number;
  /** Radians. */
  phaseStep: number;
  /** Main beam direction from the normal, towards +axis; null when no real direction matches. */
  steeringDeg: number | null;
  gratingLobesDeg: number[];
  /** Relative amplitude of the sources, 1 by default; ripples are drawn with an opacity ∝ amplitude² (the intensity). */
  amplitude?: number;
  /** Linear sRGB colour of the crests (the colour of the light); the lens default otherwise. */
  colour?: [number, number, number];
  /** A plane wave driving the sources (light arriving on a molecule). */
  incident?: {
    /** World unit vector the wave travels along. */
    direction: Vector3;
    amplitude: number;
  };
  /**
   * The field around the sources, on a disc of this radius (scene units), instead of
   * the half-plane in front of them. With an incident wave, the scattered amplitude
   * follows the Rayleigh pattern √((1 + cos²Θ) / 2), Θ from the incident direction.
   */
  discRadius?: number;
  /** World point the incident light comes from (the Sun), drawn as a ray into the sources. */
  from?: Vector3;
  /** World point the scattered light of interest goes to (the observer's eyes), drawn as a ray. */
  towards?: Vector3;
  /**
   * Colour bands of the light along those rays, for a multicolour wave: relative
   * intensity of each band arriving (from) and leaving (towards), 0 to 1.
   */
  bands?: { colour: [number, number, number]; wavelength: number; incoming: number; outgoing: number }[];
  /** Linear sRGB of all the light leaving towards `towards`, mixed (e.g. the sky's blue). */
  towardsColour?: [number, number, number];
}

export const WAVE_FIELD = "wave-field";
