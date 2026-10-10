import { AmbientLight, Color, DirectionalLight, Group, HemisphereLight } from "three";
import type { Scene } from "../content/types";

// Lighting presets named by the scene format (environment.lighting).
export function createLighting(environment: Scene["environment"]): Group {
  const group = new Group();
  group.name = `lighting:${environment.lighting}`;
  const sun = (color: string, intensity: number, x: number, y: number, z: number) => {
    const light = new DirectionalLight(color, intensity);
    light.position.set(x, y, z);
    group.add(light);
  };
  switch (environment.lighting) {
    case "daylight":
      group.add(new HemisphereLight("#dceeff", "#6b7a4f", 1.4));
      sun("#fff6e5", 2.4, 60, 100, 40);
      break;
    case "dusk":
      group.add(new HemisphereLight("#ffb98a", "#3b3550", 0.9));
      sun("#ff9a5c", 1.8, -80, 25, 30);
      break;
    case "space":
      group.add(new AmbientLight("#1a2238", 0.6));
      sun("#ffffff", 3.2, 100, 40, 60);
      break;
    case "studio":
      group.add(new HemisphereLight("#ffffff", "#8a8f99", 1.2));
      sun("#ffffff", 1.8, 40, 60, 50);
      sun("#cfe0ff", 0.8, -50, 30, -40);
      break;
  }
  return group;
}

export function backgroundColor(environment: Scene["environment"]): Color {
  return new Color(environment.background);
}
