import { Vector3 } from "three";
import type { SimulatorPlugin } from "../../core/registry";

// Circular-orbit kinematics, computed at true altitude (catalogue equations), then
// shown on a display arc: each satellite sits in its true direction as seen from
// the observer, at displayRadius from it (direction exact, distance not to scale).
//
// Display conventions (not physics): every pass is overhead, moving along -Z
// (rising on the +Z side); satellites follow each other spacingS apart, the
// first one culminating at t = 0; the train loops so a satellite reappears
// below the horizon once it has set.

export const MU_EARTH = 3.986004418e14; // m³/s²
export const R_EARTH = 6_371_000; // m

export const orbitalSpeed = (altitudeM: number) => Math.sqrt(MU_EARTH / (R_EARTH + altitudeM));
export const orbitalPeriod = (altitudeM: number) => 2 * Math.PI * Math.sqrt((R_EARTH + altitudeM) ** 3 / MU_EARTH);

/** Time above minElevation during an overhead pass. */
export function passDuration(altitudeM: number, minElevationDeg: number): number {
  const e = (minElevationDeg * Math.PI) / 180;
  const psi = Math.acos((R_EARTH * Math.cos(e)) / (R_EARTH + altitudeM)) - e;
  return ((2 * psi) / (2 * Math.PI)) * orbitalPeriod(altitudeM);
}

/**
 * Where a satellite is, seen from the observer, `tau` seconds after culminating
 * overhead: horizontal distance along the track and height, in metres.
 */
export function skyPosition(altitudeM: number, tau: number): { along: number; up: number; elevationDeg: number } {
  const r = R_EARTH + altitudeM;
  const phi = (2 * Math.PI * tau) / orbitalPeriod(altitudeM);
  const along = r * Math.sin(phi);
  const up = r * Math.cos(phi) - R_EARTH;
  return { along, up, elevationDeg: (Math.atan2(up, Math.abs(along)) * 180) / Math.PI };
}

/** Offset from culmination of satellite `index`, at time t, in a looping train. */
export function trainOffset(t: number, index: number, spacingS: number, loopS: number): number {
  const tau = t - index * spacingS;
  return tau - loopS * Math.floor((tau + loopS / 2) / loopS);
}

export const orbitalPass: SimulatorPlugin = {
  id: "orbital-pass",
  create(initial, ctx) {
    const params = { ...initial } as { altitudeM: number; minElevationDeg: number; displayRadius: number; spacingS: number };
    const satellites = ctx.bound("satellites");
    const [observer] = ctx.bound("observer");
    if (!observer) throw new Error("orbital-pass: no observer bound");
    let time = 0;
    const origin = new Vector3();
    const direction = new Vector3();
    const elevations = new Map<string, number>();

    // The loop is at least one horizon-to-horizon pass, so nobody jumps in plain sight.
    const loop = () => Math.max(satellites.length * params.spacingS, passDuration(params.altitudeM, 0) + params.spacingS / 10);

    const place = () => {
      observer.node.getWorldPosition(origin);
      satellites.forEach((sat, i) => {
        const { along, up, elevationDeg } = skyPosition(params.altitudeM, trainOffset(time, i, params.spacingS, loop()));
        elevations.set(sat.id, elevationDeg);
        sat.object.visible = elevationDeg > 0;
        direction.set(0, up, -along).normalize().multiplyScalar(params.displayRadius);
        const world = origin.clone().add(direction);
        sat.node.parent ? sat.node.position.copy(sat.node.parent.worldToLocal(world)) : sat.node.position.copy(world);
      });
    };

    return {
      params,
      set(param, value) {
        (params as Record<string, unknown>)[param] = value;
        place();
      },
      update(simDt) {
        time += simDt;
        place();
      },
      outputs() {
        let visible: string | null = null;
        let best = params.minElevationDeg;
        for (const [id, el] of elevations) {
          if (el >= best) {
            best = el;
            visible = id;
          }
        }
        return {
          speed: orbitalSpeed(params.altitudeM),
          period: orbitalPeriod(params.altitudeM),
          passDuration: passDuration(params.altitudeM, params.minElevationDeg),
          visibleSatellite: visible,
          elevationsDeg: Object.fromEntries(elevations),
        };
      },
    };
  },
};
