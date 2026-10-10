import { Color, MeshStandardMaterial, type Material } from "three";
import type { Style } from "../content/types";

// Named surfaces a component can ask for. A theme maps them to materials, so a
// child node that inherits its parent's style (design rule 9) looks the same.
export type Surface =
  | "accent"
  | "ground-grass"
  | "ground-concrete"
  | "ground-sand"
  | "wall"
  | "roof"
  | "plastic-light"
  | "plastic-dark"
  | "metal"
  | "solar-cell"
  | "cable";

interface SurfaceSpec {
  color: string;
  roughness?: number;
  metalness?: number;
}

const THEMES: Record<string, Record<Exclude<Surface, "accent">, SurfaceSpec>> = {
  "branch-default": {
    "ground-grass": { color: "#7fb069", roughness: 1 },
    "ground-concrete": { color: "#b8b8b0", roughness: 1 },
    "ground-sand": { color: "#e2cf9b", roughness: 1 },
    wall: { color: "#f1e9dc", roughness: 0.9 },
    roof: { color: "#a8553a", roughness: 0.8 },
    "plastic-light": { color: "#f4f5f7", roughness: 0.45 },
    "plastic-dark": { color: "#30343b", roughness: 0.6 },
    metal: { color: "#a9b1bb", roughness: 0.35, metalness: 0.8 },
    "solar-cell": { color: "#1f3a6b", roughness: 0.3, metalness: 0.4 },
    cable: { color: "#222428", roughness: 0.7 },
  },
};

const DEFAULT_THEME = "branch-default";
const DEFAULT_ACCENT = "#ffb000";

export class Palette {
  private readonly materials = new Map<Surface, Material>();
  private readonly specs: Record<string, SurfaceSpec>;
  readonly accent: Color;

  constructor(style: Style | undefined) {
    this.specs = THEMES[style?.theme ?? DEFAULT_THEME] ?? THEMES[DEFAULT_THEME]!;
    this.accent = new Color(style?.accent ?? DEFAULT_ACCENT);
  }

  /** Shared material: never mutate it, clone it if a component needs a variant. */
  material(surface: Surface): Material {
    let material = this.materials.get(surface);
    if (!material) {
      const spec: SurfaceSpec = surface === "accent" ? { color: `#${this.accent.getHexString()}`, roughness: 0.5 } : this.specs[surface]!;
      material = new MeshStandardMaterial({ color: spec.color, roughness: spec.roughness ?? 0.7, metalness: spec.metalness ?? 0 });
      this.materials.set(surface, material);
    }
    return material;
  }

  dispose(): void {
    for (const m of this.materials.values()) m.dispose();
    this.materials.clear();
  }
}
