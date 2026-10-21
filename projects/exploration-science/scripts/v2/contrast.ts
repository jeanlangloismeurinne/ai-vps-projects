// npm run contrast -- DIR : object/background contrast of the main objects, measured on a
// capture run (npm run capture). For each format and object, the silhouette capture (same
// camera, object alone, flat on white) gives the object's mask; on the normal capture we
// compare the object's mean relative luminance with a ring of background around it
// (WCAG ratio, threshold 3:1 — roadmap v2 §3), and report how much of the outline stands
// out locally (inside/outside luminance ratio ≥ 1.5 across the edge).
import { readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { PNG } from "pngjs";

export const MIN_RATIO = 3;
const RING_PX = 24; // ring width at the capture's 2× pixel ratio
const EDGE_RATIO = 1.5;

const linear = (c: number) => {
  const s = c / 255;
  return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
};
const luminance = (d: Buffer, i: number) => 0.2126 * linear(d[i]!) + 0.7152 * linear(d[i + 1]!) + 0.0722 * linear(d[i + 2]!);
const ratio = (a: number, b: number) => (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);

export interface Contrast {
  ratio: number;
  objectL: number;
  ringL: number;
  edgeShare: number;
}

export function measure(normal: PNG, silhouette: PNG): Contrast {
  const { width: w, height: h } = normal;
  const mask = new Uint8Array(w * h);
  for (let p = 0; p < w * h; p++) mask[p] = luminance(silhouette.data, p * 4) < 0.5 ? 1 : 0;
  // Distance to the mask by two chamfer passes (city-block), capped at the ring width.
  const dist = new Float32Array(w * h).fill(1e9);
  for (let p = 0; p < w * h; p++) if (mask[p]) dist[p] = 0;
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      const p = y * w + x;
      if (x > 0) dist[p] = Math.min(dist[p]!, dist[p - 1]! + 1);
      if (y > 0) dist[p] = Math.min(dist[p]!, dist[p - w]! + 1);
    }
  for (let y = h - 1; y >= 0; y--)
    for (let x = w - 1; x >= 0; x--) {
      const p = y * w + x;
      if (x < w - 1) dist[p] = Math.min(dist[p]!, dist[p + 1]! + 1);
      if (y < h - 1) dist[p] = Math.min(dist[p]!, dist[p + w]! + 1);
    }
  let inSum = 0, inN = 0, ringSum = 0, ringN = 0, edges = 0, edgesOk = 0;
  for (let y = 1; y < h - 1; y++)
    for (let x = 1; x < w - 1; x++) {
      const p = y * w + x;
      const L = luminance(normal.data, p * 4);
      if (mask[p]) {
        inSum += L;
        inN++;
        // An outline pixel: compare it with the background 3 px outward.
        for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]] as const) {
          if (!mask[p + dx + dy * w]) {
            const q = Math.min(w - 1, Math.max(0, x + 3 * dx)) + Math.min(h - 1, Math.max(0, y + 3 * dy)) * w;
            if (!mask[q]) {
              edges++;
              if (ratio(L, luminance(normal.data, q * 4)) >= EDGE_RATIO) edgesOk++;
            }
            break;
          }
        }
      } else if (dist[p]! <= RING_PX) {
        ringSum += L;
        ringN++;
      }
    }
  const objectL = inSum / Math.max(1, inN);
  const ringL = ringSum / Math.max(1, ringN);
  return { ratio: ratio(objectL, ringL), objectL, ringL, edgeShare: edges ? edgesOk / edges : 0 };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const dir = resolve(process.argv[2] ?? ".");
  const runs = JSON.parse(readFileSync(join(dir, "captures.json"), "utf8")) as Record<string, { file: string }>;
  const report: Record<string, Contrast & { pass: boolean }> = {};
  let failed = 0;
  for (const key of Object.keys(runs)) {
    const [view, format] = key.split("/");
    if (!view!.startsWith("silhouette-")) continue;
    const id = view!.slice("silhouette-".length);
    const normal = runs[`object-${id}/${format}`];
    if (!normal) continue;
    const m = measure(PNG.sync.read(readFileSync(join(dir, normal.file))), PNG.sync.read(readFileSync(join(dir, runs[key]!.file))));
    const pass = m.ratio >= MIN_RATIO;
    if (!pass) failed++;
    report[`${id}/${format}`] = { ...m, pass };
    console.log(`${pass ? "ok  " : "FAIL"} ${id.padEnd(15)} ${format!.padEnd(15)} ratio ${m.ratio.toFixed(2)}:1  outline ${(m.edgeShare * 100).toFixed(0)} %`);
  }
  writeFileSync(join(dir, "contrast.json"), JSON.stringify(report, null, 2) + "\n");
  console.log(failed ? `RESULT: failure — ${failed} object view(s) under ${MIN_RATIO}:1` : `RESULT: success — every object ≥ ${MIN_RATIO}:1`);
  process.exit(failed ? 1 : 0);
}
