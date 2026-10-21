import { useFrame } from "@react-three/fiber";
import { useLayoutEffect, useMemo, useRef } from "react";
import { Color, Matrix4, Quaternion, Vector3, type InstancedMesh } from "three";
import { Polyline } from "./links";

/** Spacing of the pulses along a flow and their speed, in metres of the diorama. */
const SPACING = 1.4;
const SPEED = 1.6;
const UP = new Vector3(0, 1, 0);

/** Pulses running along a flow in its direction: elongated capsules with a white core in a
 * coloured halo, unlike the dashes of the links they run on. Two instanced draw calls per
 * flow. `time` (s) pins the animation phase (captures). */
export function FlowPulses({ path, color, radius, time }: { path: Polyline; color: string; radius: number; time: number | null }) {
  const ref = useRef<InstancedMesh>(null);
  const halo = useRef<InstancedMesh>(null);
  const count = Math.max(1, Math.floor(path.length / SPACING));
  const tmp = useMemo(() => ({ m: new Matrix4(), q: new Quaternion(), p: new Vector3(), t: new Vector3(), s: new Vector3() }), []);
  const tint = useMemo(() => new Color(color), [color]);

  const place = (elapsed: number) => {
    const [mesh, glow] = [ref.current, halo.current];
    if (!mesh || !glow) return;
    const step = path.length / count;
    for (let i = 0; i < count; i++) {
      const s = (elapsed * SPEED + i * step) % path.length;
      const { hidden } = path.at(s, tmp.p, tmp.t);
      // Grow in at the start and shrink out at the end of the path: no pop.
      const k = hidden ? 0 : Math.min(1, Math.min(s, path.length - s) / 0.5);
      tmp.q.setFromUnitVectors(UP, tmp.t);
      tmp.s.set(k, k, k);
      tmp.m.compose(tmp.p, tmp.q, tmp.s);
      mesh.setMatrixAt(i, tmp.m);
      glow.setMatrixAt(i, tmp.m);
    }
    mesh.instanceMatrix.needsUpdate = true;
    glow.instanceMatrix.needsUpdate = true;
  };

  useLayoutEffect(() => place(time ?? 0));
  useFrame(({ clock }) => {
    if (time === null) place(clock.elapsedTime);
  });

  return (
    <>
      <instancedMesh ref={halo} args={[undefined, undefined, count]} frustumCulled={false} renderOrder={2}>
        <capsuleGeometry args={[radius * 2, radius * 4, 4, 12]} />
        <meshBasicMaterial color={tint} transparent opacity={0.45} depthWrite={false} toneMapped={false} />
      </instancedMesh>
      <instancedMesh ref={ref} args={[undefined, undefined, count]} frustumCulled={false} renderOrder={3}>
        <capsuleGeometry args={[radius, radius * 4, 4, 10]} />
        <meshBasicMaterial color="#ffffff" toneMapped={false} />
      </instancedMesh>
    </>
  );
}
