import { CanvasTexture, Mesh, PlaneGeometry, type MeshStandardMaterial } from "three";
import type { ComponentPlugin } from "../../core/registry";

// Square patch whose outer ring fades out, so its edge melts into the background.
const FADE_FROM = 0.6; // fraction of the half-side where the fade starts

function fadeTexture(): CanvasTexture | null {
  if (typeof document === "undefined") return null; // tests run without a DOM
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 256;
  const g = canvas.getContext("2d");
  if (!g) return null;
  const gradient = g.createRadialGradient(128, 128, 128 * FADE_FROM, 128, 128, 128);
  gradient.addColorStop(0, "#fff");
  gradient.addColorStop(1, "#000");
  g.fillStyle = gradient;
  g.fillRect(0, 0, 256, 256);
  return new CanvasTexture(canvas);
}

export const terrain: ComponentPlugin = {
  id: "terrain",
  create(params, ctx) {
    const { size, surface } = params as { size: number; surface: "grass" | "concrete" | "sand" };
    const geometry = new PlaneGeometry(size, size);
    geometry.rotateX(-Math.PI / 2);
    const fade = fadeTexture();
    const material = (ctx.palette.material(`ground-${surface}`) as MeshStandardMaterial).clone();
    if (fade) {
      material.alphaMap = fade;
      material.transparent = true;
      material.depthWrite = true;
    }
    const mesh = new Mesh(geometry, material);
    mesh.renderOrder = -1;
    return {
      object: mesh,
      dispose() {
        geometry.dispose();
        material.dispose();
        fade?.dispose();
      },
    };
  },
};
