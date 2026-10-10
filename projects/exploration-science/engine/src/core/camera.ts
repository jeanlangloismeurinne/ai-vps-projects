import { MathUtils, Vector3, type PerspectiveCamera } from "three";
import type { CameraConstraints, Shot } from "../content/types";

// Constrained camera (spec, "Caméra contrainte"): the camera only ever orbits a
// target point. Azimuth turns around the vertical axis from +Z towards +X,
// elevation is the angle above the horizontal plane. No free flight.

export interface OrbitView {
  azimuth: number; // rad
  elevation: number; // rad
  distance: number; // scene units
}

const MAX_ELEVATION_DEG = 89; // never straight up or down: the orbit would flip.

export function viewFromShot(shot: Pick<Shot, "azimuthDeg" | "elevationDeg" | "distance">): OrbitView {
  return {
    azimuth: MathUtils.degToRad(shot.azimuthDeg),
    elevation: MathUtils.degToRad(shot.elevationDeg),
    distance: shot.distance,
  };
}

/** Camera position relative to the target. */
export function orbitOffset(view: OrbitView, out = new Vector3()): Vector3 {
  const horizontal = Math.cos(view.elevation) * view.distance;
  return out.set(horizontal * Math.sin(view.azimuth), Math.sin(view.elevation) * view.distance, horizontal * Math.cos(view.azimuth));
}

export function clampView(view: OrbitView, c: CameraConstraints): OrbitView {
  const minEl = MathUtils.degToRad(Math.max(c.minElevationDeg ?? -MAX_ELEVATION_DEG, -MAX_ELEVATION_DEG));
  const maxEl = MathUtils.degToRad(Math.min(c.maxElevationDeg ?? MAX_ELEVATION_DEG, MAX_ELEVATION_DEG));
  return {
    azimuth: wrapAngle(view.azimuth),
    elevation: MathUtils.clamp(view.elevation, minEl, maxEl),
    distance: MathUtils.clamp(view.distance, c.minDistance, c.maxDistance),
  };
}

/** Angle in (-π, π]. */
export function wrapAngle(a: number): number {
  const wrapped = a - 2 * Math.PI * Math.floor((a + Math.PI) / (2 * Math.PI));
  return wrapped === -Math.PI ? Math.PI : wrapped;
}

const easeInOutCubic = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);

/**
 * View between two views at progress t in [0, 1]: azimuth along the shortest
 * arc, distance interpolated in log space so zooming feels uniform across scales.
 */
export function interpolateView(from: OrbitView, to: OrbitView, t: number): OrbitView {
  const k = easeInOutCubic(MathUtils.clamp(t, 0, 1));
  return {
    azimuth: wrapAngle(from.azimuth + wrapAngle(to.azimuth - from.azimuth) * k),
    elevation: MathUtils.lerp(from.elevation, to.elevation, k),
    distance: Math.exp(MathUtils.lerp(Math.log(from.distance), Math.log(to.distance), k)),
  };
}

/** Returns the current world position of what the camera looks at. */
export type TargetProvider = () => Vector3;

interface Flight {
  fromView: OrbitView;
  fromTarget: Vector3;
  toView: OrbitView;
  elapsed: number;
  duration: number;
}

const ORBIT_DAMPING = 6; // 1/s, decay rate of the drag inertia

export class CameraRig {
  view: OrbitView;
  readonly target = new Vector3();
  private follow: TargetProvider;
  private flight: Flight | null = null;
  private readonly velocity = { azimuth: 0, elevation: 0 };
  private dragging = false;
  private readonly offset = new Vector3();

  constructor(
    private readonly camera: PerspectiveCamera,
    private readonly constraints: CameraConstraints,
    shot: Shot,
    private readonly resolve: (entityId: string) => TargetProvider,
  ) {
    this.follow = resolve(shot.target);
    this.view = clampView(viewFromShot(shot), constraints);
    this.target.copy(this.follow());
    this.apply();
  }

  get flying(): boolean {
    return this.flight !== null;
  }

  /** Moves to a shot. duration 0 cuts instantly. */
  flyTo(shot: Shot, durationS: number): void {
    const toView = clampView(viewFromShot(shot), this.constraints);
    this.follow = this.resolve(shot.target);
    this.velocity.azimuth = this.velocity.elevation = 0;
    if (durationS <= 0) {
      this.flight = null;
      this.view = toView;
      this.target.copy(this.follow());
    } else {
      this.flight = { fromView: { ...this.view }, fromTarget: this.target.clone(), toView, elapsed: 0, duration: durationS };
    }
    this.apply();
  }

  /** User drag, in radians. Interrupts any flight: the user always has the last word. */
  orbitBy(dAzimuth: number, dElevation: number, dt: number): void {
    this.flight = null;
    this.view = clampView({ ...this.view, azimuth: this.view.azimuth + dAzimuth, elevation: this.view.elevation + dElevation }, this.constraints);
    if (dt > 0) {
      this.velocity.azimuth = dAzimuth / dt;
      this.velocity.elevation = dElevation / dt;
    }
    this.apply();
  }

  /** factor < 1 zooms in. */
  zoomBy(factor: number): void {
    if (this.flight) this.settleFlight();
    this.view = clampView({ ...this.view, distance: this.view.distance * factor }, this.constraints);
    this.apply();
  }

  setDragging(dragging: boolean): void {
    this.dragging = dragging;
    if (dragging) this.velocity.azimuth = this.velocity.elevation = 0;
  }

  update(dt: number): void {
    if (this.flight) {
      const f = this.flight;
      f.elapsed += dt;
      const t = f.elapsed / f.duration;
      this.view = t >= 1 ? f.toView : interpolateView(f.fromView, f.toView, t);
      const k = easeInOutCubic(MathUtils.clamp(t, 0, 1));
      this.target.lerpVectors(f.fromTarget, this.follow(), k);
      if (t >= 1) this.flight = null;
    } else {
      this.target.copy(this.follow());
      if (!this.dragging && (this.velocity.azimuth !== 0 || this.velocity.elevation !== 0)) {
        this.view = clampView(
          { ...this.view, azimuth: this.view.azimuth + this.velocity.azimuth * dt, elevation: this.view.elevation + this.velocity.elevation * dt },
          this.constraints,
        );
        const decay = Math.exp(-ORBIT_DAMPING * dt);
        this.velocity.azimuth *= decay;
        this.velocity.elevation *= decay;
        if (Math.abs(this.velocity.azimuth) + Math.abs(this.velocity.elevation) < 1e-3) this.velocity.azimuth = this.velocity.elevation = 0;
      }
    }
    this.apply();
  }

  // A zoom during a flight lands it where it was heading, then zooms from there.
  private settleFlight(): void {
    this.view = this.flight!.toView;
    this.target.copy(this.follow());
    this.flight = null;
  }

  private apply(): void {
    this.camera.position.copy(this.target).add(orbitOffset(this.view, this.offset));
    // Depth range follows the distance, so the roof and the satellites both stay sharp.
    this.camera.near = Math.max(this.view.distance * 0.01, 1e-4);
    this.camera.far = this.camera.near * 1e5;
    this.camera.updateProjectionMatrix();
    this.camera.lookAt(this.target);
  }
}
