import { Color, Light, Mesh, type Material, type Object3D } from "three";

// Convention between a component and the simulator that colours it from physics
// (a star's light, a sky): the component flags what may be tinted with
// userData.tint; the simulator never needs to know the component's structure.

const scratch = new Color();

/** Sets the colour (linear sRGB) of every flagged material and light; lights also get an intensity factor. */
export function tint(object: Object3D, linear: readonly number[], intensity = 1): void {
  scratch.setRGB(linear[0]!, linear[1]!, linear[2]!);
  object.traverse((o) => {
    if (o instanceof Light && o.userData.tint) {
      o.color.copy(scratch);
      o.intensity = (o.userData.baseIntensity as number) * intensity;
    } else if (o instanceof Mesh && o.userData.tint) {
      for (const m of (Array.isArray(o.material) ? o.material : [o.material]) as (Material & { color?: Color })[]) m.color?.copy(scratch);
    }
  });
}
