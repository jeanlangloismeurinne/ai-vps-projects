import { BufferAttribute, BufferGeometry, Group, InstancedMesh, Line, LineBasicMaterial, Matrix4, MeshBasicMaterial, SphereGeometry, Vector3, type Object3D } from "three";
import type { ComponentPlugin } from "../../core/registry";

const MEDIUM_COLOURS: Record<string, string> = { fiber: "#3fd0ff", laser: "#ff4d6d" };
const PULSES_PER_WAY = 6;
const PULSE_SPEED = 0.35; // path lengths per second: a display rhythm, not the speed of light
const PULSE_SIZE = 0.012; // pulse radius as a fraction of the path length

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
    const pulseGeometry = new SphereGeometry(1, 10, 8);
    const pulseMaterial = new MeshBasicMaterial({ color: colour });
    const pulses = new InstancedMesh(pulseGeometry, pulseMaterial, PULSES_PER_WAY * ways);
    pulses.frustumCulled = false;
    group.add(line, pulses);

    let ends: [Object3D, Object3D] | null = null;
    let phase = 0;
    const a = new Vector3();
    const b = new Vector3();
    const at = new Vector3();
    const m = new Matrix4();

    const refresh = () => {
      if (!ends) return;
      group.worldToLocal(ends[0].getWorldPosition(a));
      group.worldToLocal(ends[1].getWorldPosition(b));
      positions.setXYZ(0, a.x, a.y, a.z);
      positions.setXYZ(1, b.x, b.y, b.z);
      positions.needsUpdate = true;
      const radius = a.distanceTo(b) * PULSE_SIZE;
      for (let way = 0; way < ways; way++) {
        for (let i = 0; i < PULSES_PER_WAY; i++) {
          // The return way is shifted by half a gap so pulses never overlap.
          let t = (phase + (i + way * 0.5) / PULSES_PER_WAY) % 1;
          if (way === 1) t = 1 - t;
          at.lerpVectors(a, b, t);
          m.makeScale(radius, radius, radius).setPosition(at);
          pulses.setMatrixAt(way * PULSES_PER_WAY + i, m);
        }
      }
      pulses.instanceMatrix.needsUpdate = true;
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
      },
    };
  },
};
