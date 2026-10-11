import { AdditiveBlending, CanvasTexture, DirectionalLight, Mesh, MeshBasicMaterial, SphereGeometry, Sprite, SpriteMaterial, Group } from "three";
import type { ComponentPlugin } from "../../core/registry";
import { normalised, planck, spectrumToXyz, WAVELENGTHS_NM, xyzToLinearRgb } from "../light";

// A glowing disc with a soft corona, always not to scale. Its colour is the
// black body's at the star's temperature; a bound simulator may change it (the
// light left after crossing the air) through the tint convention. The star
// also lights the scene, from where it is.
const CORONA_SCALE = 4; // corona diameter, in disc radii
const LIGHT_INTENSITY = 1.2;

function coronaTexture(): CanvasTexture | null {
  if (typeof document === "undefined") return null; // tests run without a DOM
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 128;
  const g = canvas.getContext("2d");
  if (!g) return null;
  const gradient = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  gradient.addColorStop(0, "rgba(255,255,255,0.9)");
  gradient.addColorStop(0.3, "rgba(255,255,255,0.35)");
  gradient.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = gradient;
  g.fillRect(0, 0, 128, 128);
  return new CanvasTexture(canvas);
}

/** Linear sRGB of a black body, at full brightness. */
export function blackBodyColour(temperatureK: number): [number, number, number] {
  return normalised(xyzToLinearRgb(spectrumToXyz(WAVELENGTHS_NM.map((nm) => planck(nm, temperatureK)))));
}

export const star: ComponentPlugin = {
  id: "star",
  create(params) {
    const p = params as { displayRadius: number; colorTemperatureK: number };
    const [r, g, b] = blackBodyColour(p.colorTemperatureK);
    const group = new Group();

    const geometry = new SphereGeometry(p.displayRadius, 32, 16);
    const discMaterial = new MeshBasicMaterial({ toneMapped: false });
    discMaterial.color.setRGB(r, g, b);
    const disc = new Mesh(geometry, discMaterial);
    disc.userData.tint = true;
    group.add(disc);

    const texture = coronaTexture();
    const coronaMaterial = new SpriteMaterial({ map: texture, blending: AdditiveBlending, depthWrite: false, toneMapped: false, transparent: true });
    coronaMaterial.color.setRGB(r, g, b);
    const corona = new Sprite(coronaMaterial);
    corona.scale.setScalar(p.displayRadius * CORONA_SCALE);
    corona.userData.tint = true;
    // Never picked: the corona is light, not matter.
    corona.raycast = () => {};
    if (texture) group.add(corona);

    const light = new DirectionalLight(0xffffff, LIGHT_INTENSITY);
    light.color.setRGB(r, g, b);
    light.userData.tint = true;
    light.userData.baseIntensity = LIGHT_INTENSITY;
    group.add(light);

    return {
      object: group,
      dispose() {
        geometry.dispose();
        discMaterial.dispose();
        coronaMaterial.dispose();
        texture?.dispose();
      },
    };
  },
};
