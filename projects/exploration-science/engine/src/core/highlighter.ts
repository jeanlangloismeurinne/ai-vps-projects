import { Color, Mesh, MeshStandardMaterial, type Material, type Object3D } from "three";

const PULSE_HZ = 0.8;

/**
 * Makes entities glow in the accent colour, pulsing. Meshes get a glowing clone
 * of their material while highlighted; shared palette materials stay untouched.
 */
export class Highlighter {
  private readonly originals = new Map<Mesh, Material | Material[]>();
  private readonly clones = new Map<Material, MeshStandardMaterial>();
  private readonly accent: Color;
  private time = 0;

  constructor(accent: Color) {
    this.accent = accent.clone();
  }

  set(objects: Object3D[]): void {
    const wanted = new Set<Mesh>();
    for (const o of objects) o.traverse((child) => child instanceof Mesh && wanted.add(child));
    for (const [mesh, original] of this.originals) {
      if (!wanted.has(mesh)) {
        mesh.material = original;
        this.originals.delete(mesh);
      }
    }
    for (const mesh of wanted) {
      if (this.originals.has(mesh) || Array.isArray(mesh.material) || !(mesh.material instanceof MeshStandardMaterial)) continue;
      this.originals.set(mesh, mesh.material);
      mesh.material = this.glowing(mesh.material);
    }
  }

  update(dt: number): void {
    this.time += dt;
    const intensity = 0.35 + 0.25 * Math.sin(2 * Math.PI * PULSE_HZ * this.time);
    for (const clone of this.clones.values()) clone.emissiveIntensity = intensity;
  }

  dispose(): void {
    this.set([]);
    for (const clone of this.clones.values()) clone.dispose();
    this.clones.clear();
  }

  private glowing(material: MeshStandardMaterial): MeshStandardMaterial {
    let clone = this.clones.get(material);
    if (!clone) {
      clone = material.clone();
      clone.emissive.copy(this.accent);
      this.clones.set(material, clone);
    }
    return clone;
  }
}
