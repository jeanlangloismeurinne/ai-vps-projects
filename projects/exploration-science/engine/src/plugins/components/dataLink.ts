import { BufferAttribute, BufferGeometry, DataTexture, Group, Line, LineBasicMaterial, Points, PointsMaterial, Vector3, type Object3D } from "three";
import type { ComponentPlugin } from "../../core/registry";

const MEDIUM_COLOURS: Record<string, string> = { fiber: "#3fd0ff", laser: "#ff4d6d" };
const PULSES_PER_WAY = 6;
const PULSE_SPEED = 0.35; // path lengths per second: a display rhythm, not the speed of light
const PULSE_PX = 9; // pulses keep the same size on screen at every zoom level

// A soft round dot, built without a canvas so the plugin also runs in tests.
function dotTexture(): DataTexture {
  const n = 32;
  const data = new Uint8Array(n * n * 4);
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      const r = Math.hypot(x + 0.5 - n / 2, y + 0.5 - n / 2) / (n / 2);
      const i = (y * n + x) * 4;
      data[i] = data[i + 1] = data[i + 2] = 255;
      data[i + 3] = Math.round(255 * Math.min(1, Math.max(0, (1 - r) * 4)));
    }
  }
  const texture = new DataTexture(data, n, n);
  texture.needsUpdate = true;
  return texture;
}

// Path between two entities, kept up to date as they move (satellites), with
// pulses running along it to show where data goes (both ways unless told otherwise).
export const dataLink: ComponentPlugin = {
  id: "data-link",
  create(params, ctx) {
    const p = params as { from: string; to: string; medium: string; bidirectional: boolean };
    const colour = MEDIUM_COLOURS[p.medium] ?? ctx.palette.accent;
    const group = new Group();

    const lineGeometry = new BufferGeometry();
    const positions = new BufferAttribute(new Float32Array(6), 3);
    lineGeometry.setAttribute("position", positions);
    const lineMaterial = new LineBasicMaterial({ color: colour, transparent: true, opacity: 0.6 });
    const line = new Line(lineGeometry, lineMaterial);
    line.frustumCulled = false;

    const ways = p.bidirectional ? 2 : 1;
    const pulseGeometry = new BufferGeometry();
    const pulsePositions = new BufferAttribute(new Float32Array(PULSES_PER_WAY * ways * 3), 3);
    pulseGeometry.setAttribute("position", pulsePositions);
    const dot = dotTexture();
    const pulseMaterial = new PointsMaterial({ color: colour, size: PULSE_PX, sizeAttenuation: false, map: dot, transparent: true, alphaTest: 0.1, depthWrite: false });
    const pulses = new Points(pulseGeometry, pulseMaterial);
    pulses.frustumCulled = false;
    group.add(line, pulses);

    let ends: [Object3D, Object3D] | null = null;
    let phase = 0;
    const a = new Vector3();
    const b = new Vector3();
    const at = new Vector3();

    const refresh = () => {
      if (!ends) return;
      group.worldToLocal(ends[0].getWorldPosition(a));
      group.worldToLocal(ends[1].getWorldPosition(b));
      positions.setXYZ(0, a.x, a.y, a.z);
      positions.setXYZ(1, b.x, b.y, b.z);
      positions.needsUpdate = true;
      for (let way = 0; way < ways; way++) {
        for (let i = 0; i < PULSES_PER_WAY; i++) {
          // The return way is shifted by half a gap so pulses never overlap.
          let t = (phase + (i + way * 0.5) / PULSES_PER_WAY) % 1;
          if (way === 1) t = 1 - t;
          at.lerpVectors(a, b, t);
          pulsePositions.setXYZ(way * PULSES_PER_WAY + i, at.x, at.y, at.z);
        }
      }
      pulsePositions.needsUpdate = true;
    };

    return {
      object: group,
      resolve(entity) {
        const from = entity(p.from);
        const to = entity(p.to);
        if (!from || !to) throw new Error(`data-link: unknown endpoint '${p.from}' or '${p.to}'`);
        ends = [from, to];
        refresh();
      },
      update(dt) {
        phase = (phase + dt * PULSE_SPEED) % 1;
        refresh();
      },
      dispose() {
        lineGeometry.dispose();
        lineMaterial.dispose();
        pulseGeometry.dispose();
        pulseMaterial.dispose();
        dot.dispose();
      },
    };
  },
};
