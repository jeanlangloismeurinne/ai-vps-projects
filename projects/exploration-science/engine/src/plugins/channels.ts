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
}

export const WAVE_FIELD = "wave-field";
