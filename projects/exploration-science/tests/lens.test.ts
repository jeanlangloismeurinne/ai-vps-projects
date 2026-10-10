import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import type { Catalogue, Scene } from "../engine/src/content/types";
import { PluginRegistry } from "../engine/src/core/registry";
import { buildScene } from "../engine/src/core/sceneBuilder";
import { buildSimulation } from "../engine/src/core/simulation";
import { WAVE_FIELD, type WaveField } from "../engine/src/plugins/channels";
import { registerComponents } from "../engine/src/plugins/components";
import { LENSES, registerLenses } from "../engine/src/plugins/lenses";
import { fieldAt, waves } from "../engine/src/plugins/lenses/waves";
import { registerSimulators } from "../engine/src/plugins/simulators";
import { gratingLobesDeg, phaseStepDeg } from "../engine/src/plugins/simulators/phasedArrayWave";

const ROOT = join(import.meta.dirname, "..");
const readJson = (path: string) => JSON.parse(readFileSync(join(ROOT, path), "utf8"));
const catalogue: Catalogue = readJson("catalogue/catalogue.json");
const starlink: Scene = readJson("content/nodes/starlink-terminal/scene.json");
const DEG = Math.PI / 180;

const registry = new PluginRegistry();
registerComponents(registry);
registerSimulators(registry);
registerLenses(registry);

/** Far-field strength |A|·√r / N in direction θ (from the normal, towards +axis). */
function strength(f: Parameters<typeof fieldAt>[0], thetaDeg: number): number {
  const r = 400 * f.wavelength;
  const { re, im } = fieldAt(f, r * Math.sin(thetaDeg * DEG), r * Math.cos(thetaDeg * DEG));
  return (Math.hypot(re, im) * Math.sqrt(r)) / f.count;
}

function brightestDeg(f: Parameters<typeof fieldAt>[0]): number {
  let best = -89;
  for (let t = -89; t <= 89; t += 0.1) if (strength(f, t) > strength(f, best)) best = t;
  return best;
}

describe("lens plugins", () => {
  it("are all declared in the catalogue (design rule 2)", () => {
    const ids = new Set(catalogue.lenses.map((l) => l.id));
    for (const plugin of LENSES) expect(ids.has(plugin.id), plugin.id).toBe(true);
  });
});

// Design rule 4: the field the Ondes lens draws comes from the superposition of the sources.
describe("waves lens field", () => {
  const lambda = 1;

  it("sends the beam where Δφ = 2π d sinθ / λ says", () => {
    for (const [theta, dOverLambda, count] of [[0, 0.5, 16], [30, 0.5, 16], [-45, 0.5, 24], [20, 0.4, 32]] as const) {
      const f = { wavelength: lambda, count, spacing: dOverLambda * lambda, phaseStep: phaseStepDeg(theta, dOverLambda) * DEG };
      expect(brightestDeg(f)).toBeCloseTo(theta, 0);
      expect(strength(f, theta)).toBeGreaterThan(0.95);
    }
  });

  it("shows a grating lobe beyond d = λ/2, at the predicted angle", () => {
    const f = { wavelength: lambda, count: 16, spacing: lambda, phaseStep: phaseStepDeg(35, 1) * DEG };
    const [lobe] = gratingLobesDeg(35, 1);
    expect(lobe).toBeDefined();
    expect(strength(f, lobe!)).toBeGreaterThan(0.95);
    // At d = λ/2 the same steering leaves that direction dark.
    const tight = { ...f, spacing: lambda / 2, phaseStep: phaseStepDeg(35, 0.5) * DEG };
    expect(strength(tight, lobe!)).toBeLessThan(0.2);
  });

  it("narrows the beam as elements are added", () => {
    const width = (count: number) => {
      const f = { wavelength: lambda, count, spacing: lambda / 2, phaseStep: 0 };
      let t = 0;
      while (strength(f, t) > Math.SQRT1_2) t += 0.05;
      return 2 * t; // half-power beamwidth
    };
    // Uniform line array at broadside: θ3dB ≈ 0.886 λ / (N d) radians.
    for (const n of [4, 16, 32]) expect(width(n)).toBeCloseTo((0.886 * 2) / n / DEG, -0.5);
    expect(width(32)).toBeLessThan(width(4) / 6);
  });
});

describe("phased-array-wave wave-field channel", () => {
  const load = () => {
    const built = buildScene(starlink, catalogue, registry);
    const simulation = buildSimulation(starlink, catalogue, registry, built);
    return { built, simulation, beam: simulation.instances.get("beam")! };
  };

  it("describes the simulated line of sources in scene units", () => {
    const { beam } = load();
    beam.set("steeringAngleDeg", 30);
    const f = beam.channel!(WAVE_FIELD) as WaveField;
    expect(f.count).toBe(16);
    expect(f.wavelength).toBeCloseTo(0.025, 3); // metersPerUnit = 1
    expect(f.spacing).toBeCloseTo(f.wavelength / 2, 6);
    expect(f.phaseStep).toBeCloseTo(phaseStepDeg(30, 0.5) * DEG, 6);
    expect(f.steeringDeg).toBeCloseTo(30, 6);
    expect(Math.abs(f.axis.dot(f.normal))).toBeLessThan(1e-9);
  });

  it("stops tracking once the beam is steered by hand, and keeps the element count whole", () => {
    const { beam } = load();
    expect(beam.params.tracking).toBe(true);
    beam.set("steeringAngleDeg", 10);
    expect(beam.params.tracking).toBe(false);
    beam.set("elementCount", 7.6);
    expect(beam.params.elementCount).toBe(8);
  });

  it("feeds the lens, which shows itself only when active", () => {
    const { built, simulation } = load();
    const lens = waves.create({ sources: [{ id: "beam", simulator: "phased-array-wave", instance: () => simulation.instances.get("beam") }], palette: built.palette, metres: (m) => m });
    lens.update(0.016);
    expect(lens.object.visible).toBe(false);
    lens.setActive(true);
    lens.update(0.016);
    expect(lens.object.visible).toBe(true);
    lens.dispose?.();
  });
});
