import { Vector3 } from "three";
import type { SimulatorPlugin } from "../../core/registry";
import { WAVE_FIELD, type WaveField } from "../channels";

// Linear phased array: N point sources, spacing d, with a phase step Δφ between
// neighbours (catalogue equations). Pure functions first; the plugin wires them
// to the scene (tracking a target entity seen from the array).

export const SPEED_OF_LIGHT = 299_792_458; // m/s
const DEG = Math.PI / 180;

export const wavelength = (frequencyHz: number) => SPEED_OF_LIGHT / frequencyHz;

/** Δφ = 2π d sinθ0 / λ, in degrees, wrapped to [-180, 180). */
export function phaseStepDeg(steeringDeg: number, spacingOverLambda: number): number {
  const deg = 360 * spacingOverLambda * Math.sin(steeringDeg * DEG);
  return deg - 360 * Math.floor((deg + 180) / 360);
}

/** Inverse of phaseStepDeg; null when no real direction matches (|sinθ0| > 1). */
export function steeringDeg(phaseDeg: number, spacingOverLambda: number): number | null {
  const s = phaseDeg / (360 * spacingOverLambda);
  return Math.abs(s) > 1 ? null : Math.asin(s) / DEG;
}

/** Normalised |AF(θ)| = |Σ e^{i n (2π d/λ sinθ − Δφ)}| / N. */
export function arrayFactor(thetaDeg: number, count: number, spacingOverLambda: number, phaseDeg: number): number {
  const psi = 2 * Math.PI * spacingOverLambda * Math.sin(thetaDeg * DEG) - phaseDeg * DEG;
  let re = 0;
  let im = 0;
  for (let n = 0; n < count; n++) {
    re += Math.cos(n * psi);
    im += Math.sin(n * psi);
  }
  return Math.hypot(re, im) / count;
}

/** sinθm = sinθ0 + m λ/d, m ≠ 0, kept inside visible space. */
export function gratingLobesDeg(steeringDeg0: number, spacingOverLambda: number): number[] {
  const lobes: number[] = [];
  const s0 = Math.sin(steeringDeg0 * DEG);
  const maxOrder = Math.ceil(2 * spacingOverLambda) + 1;
  for (let m = -maxOrder; m <= maxOrder; m++) {
    if (m === 0) continue;
    const s = s0 + m / spacingOverLambda;
    if (Math.abs(s) <= 1) lobes.push(Math.asin(s) / DEG);
  }
  return lobes.sort((a, b) => a - b);
}

const AF_SAMPLES = 361;

export const phasedArrayWave: SimulatorPlugin = {
  id: "phased-array-wave",
  create(initial, ctx) {
    const params = { ...initial } as {
      frequencyHz: number;
      elementCount: number;
      spacingOverLambda: number;
      steeringAngleDeg: number;
      phaseStepDeg?: number;
      trackTarget?: string;
      tracking: boolean;
      showField: boolean;
    };
    const [array] = ctx.bound("array");
    if (!array) throw new Error("phased-array-wave: no array bound");
    // Which of steering angle / phase step was set last drives the other.
    let driver: "angle" | "phase" = initial.phaseStepDeg !== undefined && initial.steeringAngleDeg === undefined ? "phase" : "angle";
    const normal = new Vector3();
    const toTarget = new Vector3();
    const origin = new Vector3();
    /** Unit vector in the array plane along which the linear cut is taken (towards the target). */
    const cutAxis = new Vector3(1, 0, 0);
    // Until a target is tracked, the cut runs along the array's own x axis.
    array.node.updateWorldMatrix(true, false);
    cutAxis.transformDirection(array.node.matrixWorld);

    const track = () => {
      if (!params.tracking || !params.trackTarget) return;
      const target = ctx.entity(params.trackTarget);
      if (!target) return;
      array.node.updateWorldMatrix(true, false);
      array.node.getWorldPosition(origin);
      normal.set(0, 1, 0).transformDirection(array.node.matrixWorld);
      target.node.getWorldPosition(toTarget).sub(origin).normalize();
      // The cut plane contains the normal and the target: θ is the full off-normal angle.
      const inPlane = toTarget.clone().addScaledVector(normal, -toTarget.dot(normal));
      if (inPlane.lengthSq() > 1e-12) cutAxis.copy(inPlane.normalize());
      params.steeringAngleDeg = Math.atan2(toTarget.dot(cutAxis), toTarget.dot(normal)) / DEG;
      driver = "angle";
    };

    const derived = () => {
      if (driver === "phase" && params.phaseStepDeg !== undefined) {
        return { steering: steeringDeg(params.phaseStepDeg, params.spacingOverLambda), phase: params.phaseStepDeg };
      }
      return { steering: params.steeringAngleDeg, phase: phaseStepDeg(params.steeringAngleDeg, params.spacingOverLambda) };
    };

    return {
      params,
      set(param, value) {
        // Element count is an integer even while a slider or a tour animates it.
        (params as Record<string, unknown>)[param] = param === "elementCount" && typeof value === "number" ? Math.max(1, Math.round(value)) : value;
        // Steering by hand takes over from tracking.
        if (param === "phaseStepDeg" || param === "steeringAngleDeg") params.tracking = false;
        if (param === "phaseStepDeg") driver = "phase";
        if (param === "steeringAngleDeg") driver = "angle";
        track();
      },
      update() {
        track();
      },
      channel(name) {
        if (name !== WAVE_FIELD) return undefined;
        const { steering, phase } = derived();
        const lambda = ctx.metres(wavelength(params.frequencyHz));
        array.node.updateWorldMatrix(true, false);
        const field: WaveField = {
          wavelength: lambda,
          origin: array.node.getWorldPosition(new Vector3()),
          normal: new Vector3(0, 1, 0).transformDirection(array.node.matrixWorld),
          axis: cutAxis.clone(),
          count: params.elementCount,
          spacing: lambda * params.spacingOverLambda,
          phaseStep: phase * DEG,
          steeringDeg: steering,
          gratingLobesDeg: steering === null ? [] : gratingLobesDeg(steering, params.spacingOverLambda),
        };
        return field;
      },
      outputs() {
        const { steering, phase } = derived();
        const af: number[] = [];
        for (let i = 0; i < AF_SAMPLES; i++) af.push(arrayFactor(-90 + (180 * i) / (AF_SAMPLES - 1), params.elementCount, params.spacingOverLambda, phase));
        return {
          wavelength: wavelength(params.frequencyHz),
          steeringAngleDeg: steering,
          phaseStepDeg: phase,
          gratingLobesDeg: steering === null ? [] : gratingLobesDeg(steering, params.spacingOverLambda),
          arrayFactor: af,
          cutAxis: cutAxis.toArray(),
        };
      },
    };
  },
};
