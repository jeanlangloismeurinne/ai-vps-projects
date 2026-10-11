import { BackSide, BufferAttribute, FrontSide, Group, Mesh, MeshBasicMaterial, SphereGeometry, type BufferGeometry } from "three";
import type { ComponentPlugin } from "../../core/registry";

// The sky as a dome over the ground, centred on the entity's origin. Seen from
// inside, its inner face is the sky; from outside, a translucent shell of the
// given thickness shows the layer of air. Both carry per-vertex colours, flagged
// userData.sky: a bound scattering simulator colours each vertex with the sky
// seen in that direction. Unbound, the dome stays a neutral pale blue.
const SEGMENTS = 64;
const RINGS = 24;
const SHELL_OPACITY = 0.35;
const UNBOUND = [0.45, 0.62, 0.9];

function dome(radius: number): BufferGeometry {
  const geometry = new SphereGeometry(radius, SEGMENTS, RINGS, 0, Math.PI * 2, 0, Math.PI / 2);
  const colours = new Float32Array(geometry.getAttribute("position").count * 3);
  for (let i = 0; i < colours.length; i += 3) colours.set(UNBOUND, i);
  geometry.setAttribute("color", new BufferAttribute(colours, 3));
  return geometry;
}

export const atmosphereLayer: ComponentPlugin = {
  id: "atmosphere-layer",
  create(params) {
    const p = params as { radius: number; thickness: number };
    const group = new Group();

    const innerGeometry = dome(p.radius);
    const innerMaterial = new MeshBasicMaterial({ vertexColors: true, side: BackSide, toneMapped: false, depthWrite: false });
    const inner = new Mesh(innerGeometry, innerMaterial);
    inner.userData.sky = true;
    inner.renderOrder = -2;
    // The sky is the backdrop, not something to tap: only the shell is picked, from outside.
    inner.raycast = () => {};
    group.add(inner);

    const outerGeometry = dome(p.radius + p.thickness);
    const outerMaterial = new MeshBasicMaterial({ vertexColors: true, side: FrontSide, transparent: true, opacity: SHELL_OPACITY, toneMapped: false, depthWrite: false });
    const outer = new Mesh(outerGeometry, outerMaterial);
    outer.userData.sky = true;
    group.add(outer);

    return {
      object: group,
      dispose() {
        innerGeometry.dispose();
        innerMaterial.dispose();
        outerGeometry.dispose();
        outerMaterial.dispose();
      },
    };
  },
};
