import { InstancedMesh, Mesh, type Object3D } from "three";

/** Triangles an object tree would draw with everything shown (instances counted). */
export function countTriangles(root: Object3D): number {
  let total = 0;
  root.traverse((o) => {
    if (!(o instanceof Mesh)) return;
    const g = o.geometry;
    const vertices = g.index ? g.index.count : (g.attributes.position?.count ?? 0);
    const range = Math.min(vertices, g.drawRange.count);
    total += Math.floor(range / 3) * (o instanceof InstancedMesh ? o.count : 1);
  });
  return total;
}

/**
 * Lowers the rendering resolution when frames take too long, and raises it back
 * when they are fast again (iPad: the cost is per pixel, not per triangle).
 * Each drop doubles the wait before the next climb, so a resolution that keeps
 * proving too slow is not retried every few seconds.
 * Pure logic: fed with real frame times, it returns the pixel ratio to use.
 */
export class AdaptiveResolution {
  static readonly WINDOW_S = 1.5;
  static readonly SLOW_FPS = 48;
  static readonly FAST_FPS = 57;
  static readonly STEP = 0.25;
  static readonly HOLD_S = 8;
  static readonly MAX_HOLD_S = 64;

  ratio: number;
  /** Frames per second over the last full window (0 before the first one). */
  fps = 0;
  private elapsed = 0;
  private frames = 0;
  private sinceDrop = Infinity;
  private hold = AdaptiveResolution.HOLD_S / 2;

  constructor(
    readonly max: number,
    readonly min = 1,
  ) {
    this.ratio = max;
  }

  /** Real duration of the last frame, in seconds; returns true when the ratio changed. */
  sample(dt: number): boolean {
    // A long gap (tab hidden, scene loading) says nothing about rendering speed.
    if (dt <= 0 || dt > 0.5) return false;
    this.elapsed += dt;
    this.frames += 1;
    this.sinceDrop += dt;
    if (this.elapsed < AdaptiveResolution.WINDOW_S) return false;
    this.fps = this.frames / this.elapsed;
    this.elapsed = 0;
    this.frames = 0;
    const before = this.ratio;
    if (this.fps < AdaptiveResolution.SLOW_FPS && this.ratio > this.min) {
      this.ratio = Math.max(this.min, this.ratio - AdaptiveResolution.STEP);
      this.hold = Math.min(AdaptiveResolution.MAX_HOLD_S, this.hold * 2);
      this.sinceDrop = 0;
    } else if (this.fps > AdaptiveResolution.FAST_FPS && this.ratio < this.max && this.sinceDrop > this.hold) {
      this.ratio = Math.min(this.max, this.ratio + AdaptiveResolution.STEP);
    }
    return this.ratio !== before;
  }
}
