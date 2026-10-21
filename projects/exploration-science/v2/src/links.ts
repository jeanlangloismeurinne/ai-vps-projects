// Geometry of the system's connections and flows, shared by the drawn links and the
// animated flows. Pure: anchor positions in, polylines out (tested in tests/v2/links.test.ts).
import { Box3, Vector3 } from "three";

export type LinkShape = "beam-dashed" | "ground-line";

export interface ConnectionLike {
  id: string;
  from: string;
  to: string;
}

export interface FlowLike {
  id: string;
  path: string[];
  direction: "forward" | "reverse";
}

/** Polyline of a connection, from its `from` end to its `to` end. A beam is a straight
 * line; a ground line runs on top of the setting, and toward an endpoint outside the scene
 * (`to` null) leaves the setting by its nearest edge and goes down the cut face. */
export function connectionPath(shape: LinkShape, from: Vector3, to: Vector3 | null, setting: Box3): Vector3[] | null {
  if (shape === "beam-dashed") return to ? [from.clone(), to.clone()] : null;
  const y = setting.max.y + 0.006;
  const start = new Vector3(from.x, y, from.z);
  if (to) return [start, new Vector3(to.x, y, to.z)];
  const exits = [
    new Vector3(setting.min.x, y, from.z),
    new Vector3(setting.max.x, y, from.z),
    new Vector3(from.x, y, setting.min.z),
    new Vector3(from.x, y, setting.max.z),
  ];
  const edge = exits.reduce((a, b) => (a.distanceTo(start) < b.distanceTo(start) ? a : b));
  return [start, edge, new Vector3(edge.x, setting.min.y + 0.15, edge.z)];
}

/** Path travelled by a flow: its connections in order, each one reversed for a `reverse`
 * flow. Consecutive connections may meet at different anchors of the same object (the
 * station's fibre and dish): that stretch is inside the object, so it is marked `hidden`
 * (the flow takes the time to cross it but is not drawn there). */
export function flowPath(flow: FlowLike, paths: Record<string, Vector3[] | null>): { points: Vector3[]; hidden: boolean[] } {
  const points: Vector3[] = [];
  const hidden: boolean[] = [];
  for (const id of flow.path) {
    const p = paths[id];
    if (!p) continue;
    const pts = flow.direction === "reverse" ? [...p].reverse() : p;
    pts.forEach((v, i) => {
      const last = points[points.length - 1];
      if (last && last.distanceToSquared(v) <= 1e-8) return;
      if (last) hidden.push(i === 0);
      points.push(v.clone());
    });
  }
  return { points, hidden };
}

/** Arc-length parametrisation of a polyline. */
export class Polyline {
  readonly points: Vector3[];
  readonly lengths: number[];
  readonly length: number;
  /** Per segment: true where the flow runs hidden (inside an object). */
  readonly hidden: boolean[];

  constructor(points: Vector3[], hidden: boolean[] = []) {
    this.points = points;
    this.hidden = hidden;
    this.lengths = [0];
    for (let i = 1; i < points.length; i++) this.lengths.push(this.lengths[i - 1]! + points[i]!.distanceTo(points[i - 1]!));
    this.length = this.lengths[this.lengths.length - 1]!;
  }

  /** Point, unit tangent and visibility at distance `s` from the start (clamped). */
  at(s: number, point = new Vector3(), tangent = new Vector3()): { point: Vector3; tangent: Vector3; hidden: boolean } {
    const d = Math.min(Math.max(s, 0), this.length);
    let i = 1;
    while (i < this.lengths.length - 1 && this.lengths[i]! < d) i++;
    const a = this.points[i - 1]!;
    const b = this.points[i]!;
    const seg = this.lengths[i]! - this.lengths[i - 1]!;
    const t = seg > 0 ? (d - this.lengths[i - 1]!) / seg : 0;
    point.lerpVectors(a, b, t);
    tangent.subVectors(b, a).normalize();
    return { point, tangent, hidden: this.hidden[i - 1] ?? false };
  }
}
