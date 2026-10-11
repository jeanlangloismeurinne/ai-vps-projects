import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import type { Catalogue, Scene } from "../engine/src/content/types";
import { aboveGround } from "../engine/src/core/camera";
import { PluginRegistry } from "../engine/src/core/registry";
import { buildScene } from "../engine/src/core/sceneBuilder";
import { buildSimulation } from "../engine/src/core/simulation";
import { WAVE_FIELD, type WaveField } from "../engine/src/plugins/channels";
import { registerComponents } from "../engine/src/plugins/components";
import { blackBodyColour } from "../engine/src/plugins/components/star";
import { scatteredAt } from "../engine/src/plugins/lenses/waves";
import { cmf, wavelengthColour } from "../engine/src/plugins/light";
import { registerSimulators } from "../engine/src/plugins/simulators";
import {
  airMass,
  bandIntensities,
  BANDS_NM,
  litFraction,
  opticalDepth,
  scatteredAmplitude,
  skyColour,
  skyRadiance,
  sunColour,
  transmittance,
} from "../engine/src/plugins/simulators/rayleighScattering";

const ROOT = join(import.meta.dirname, "..");
const readJson = (path: string) => JSON.parse(readFileSync(join(ROOT, path), "utf8"));
const catalogue: Catalogue = readJson("catalogue/catalogue.json");
const sky: Scene = readJson("content/nodes/blue-sky/scene.json");
const registry = new PluginRegistry();
registerComponents(registry);
registerSimulators(registry);

const blueOverRed = ([r, , b]: number[]) => b! / r!;

describe("colour from spectra", () => {
  it("CIE ȳ peaks near 555 nm", () => {
    let best = 380;
    for (let nm = 380; nm <= 750; nm++) if (cmf(nm)[1] > cmf(best)[1]) best = nm;
    expect(Math.abs(best - 555)).toBeLessThan(10);
  });

  it("a 6500 K black body is close to white, a 3000 K one is orange", () => {
    const [r, g, b] = blackBodyColour(6500);
    expect(Math.min(r, g, b)).toBeGreaterThan(0.85);
    const warm = blackBodyColour(3000);
    expect(warm[0]).toBe(1);
    expect(warm[2]).toBeLessThan(0.4);
  });

  it("450 nm looks blue, 700 nm looks red", () => {
    expect(blueOverRed(wavelengthColour(450))).toBeGreaterThan(5);
    expect(blueOverRed(wavelengthColour(700))).toBeLessThan(0.05);
  });
});

// Design rule 4: the simulator follows its catalogue equations.
describe("rayleigh-scattering", () => {
  it("scatters blue (450 nm) (700/450)⁴ ≈ 5.9 times more than red (700 nm): I_s ∝ I0/λ⁴", () => {
    expect(opticalDepth(450) / opticalDepth(700)).toBeCloseTo((700 / 450) ** 4, 9);
    expect(opticalDepth(450) / opticalDepth(700)).toBeCloseTo(5.86, 2);
    expect((scatteredAmplitude(450) / scatteredAmplitude(700)) ** 2).toBeCloseTo(5.86, 2);
  });

  it("sends back white sunlight as mostly blue light (band by band: I0/λ⁴)", () => {
    const { incoming, outgoing } = bandIntensities();
    expect(Math.min(...incoming)).toBeGreaterThan(0.6); // sunlight: every colour about as strong
    const blue = BANDS_NM.indexOf(450);
    const red = BANDS_NM.indexOf(700);
    expect(outgoing[blue]! / outgoing[red]! / (incoming[blue]! / incoming[red]!)).toBeCloseTo((700 / 450) ** 4, 9);
    expect(outgoing[red]).toBeLessThan(0.2);
  });

  it("removes direct light as I = I0 e^(−β s)", () => {
    for (const h of [90, 30, 5]) expect(transmittance(500, h)).toBeCloseTo(Math.exp(-opticalDepth(500) * airMass(h)), 12);
    expect(transmittance(500, 90, 0)).toBe(1);
  });

  it("air mass is 1 at the zenith, 2 at 30°, about 38 at the horizon (Kasten & Young)", () => {
    expect(airMass(90)).toBeCloseTo(1, 2);
    expect(airMass(30)).toBeCloseTo(2, 1);
    expect(airMass(0)).toBeGreaterThan(37);
    expect(airMass(0)).toBeLessThan(39);
  });

  it("matches the closed form of the single-scattering integral (numerical check)", () => {
    const [lambda, h, e, cos] = [480, 20, 35, 0.3];
    const tau = opticalDepth(lambda);
    const m = airMass(h);
    const mv = airMass(e);
    let sum = 0;
    const n = 20000;
    for (let i = 0; i < n; i++) {
      const x = ((i + 0.5) / n) * tau;
      sum += Math.exp(-m * x) * Math.exp(-mv * (tau - x)) * (tau / n);
    }
    expect(skyRadiance(lambda, h, e, cos)).toBeCloseTo(0.75 * (1 + cos * cos) * mv * sum, 10);
  });

  it("makes a blue sky by day, a black one without air, and a red Sun at sunset", () => {
    expect(blueOverRed(skyColour(45, 90, Math.cos(Math.PI / 4)))).toBeGreaterThan(1.5);
    expect(skyColour(45, 90, 0.7, 0)).toEqual([0, 0, 0]);
    expect(blueOverRed(sunColour(60))).toBeGreaterThan(0.6);
    expect(blueOverRed(sunColour(2))).toBeLessThan(0.3);
  });

  it("darkens the sky once the Sun is below the horizon (Earth's shadow)", () => {
    expect(litFraction(10)).toBe(1);
    expect(litFraction(-2)).toBeLessThan(1);
    expect(litFraction(-5)).toBeLessThan(litFraction(-2));
    const y = (h: number) => skyColour(h, 90, 0)[1];
    expect(y(-4)).toBeLessThan(y(1));
  });

  it("in the scene: places the Sun at its elevation, colours the sky, and sends a wave field in the magnifier", () => {
    const built = buildScene(sky, catalogue, registry);
    const simulation = buildSimulation(sky, catalogue, registry, built);
    const sim = simulation.instances.get("scattering")!;
    expect(simulation.missing).toEqual([]);
    const sun = built.entities.get("sun")!.node.position;
    expect((Math.atan2(sun.y, Math.hypot(sun.x, sun.z)) * 180) / Math.PI).toBeCloseTo(45, 6);
    sim.set("sunElevationDeg", 10);
    expect((Math.atan2(sun.y, Math.hypot(sun.x, sun.z)) * 180) / Math.PI).toBeCloseTo(10, 6);

    built.entities.get("air")!.node.visible = false;
    expect(sim.channel!(WAVE_FIELD)).toBeUndefined(); // the bubble is hidden
    built.entities.get("air")!.node.visible = true;
    const field = sim.channel!(WAVE_FIELD) as WaveField;
    const magnifier = built.entities.get("air")!.instance.magnifier!;
    expect(field.wavelength * magnifier.metersPerUnit).toBeCloseTo(450e-9, 15);
    expect(field.discRadius).toBe(magnifier.radius);
    sim.set("airDensityFactor", 0);
    expect(sim.channel!(WAVE_FIELD)).toBeUndefined(); // no air, nothing scatters
    expect(sim.outputs().skyColor).toBe("#000000");
  });
});

describe("waves lens around a scatterer", () => {
  it("follows the Rayleigh pattern: side scattering is √½ of forward and back", () => {
    const inc = { u: 1, v: 0 };
    expect(scatteredAt({ amplitude: 1 }, inc, 2, 0)).toBeCloseTo(1, 9);
    expect(scatteredAt({ amplitude: 1 }, inc, -2, 0)).toBeCloseTo(1, 9);
    expect(scatteredAt({ amplitude: 1 }, inc, 0, 3)).toBeCloseTo(Math.SQRT1_2, 9);
  });
});

describe("camera above the ground", () => {
  it("raises a view that would sink under y = 0, leaves others alone", () => {
    const low = aboveGround({ azimuth: 0, elevation: -0.5, distance: 10 }, 1);
    expect(1 + Math.sin(low.elevation) * 10).toBeGreaterThanOrEqual(10 * 0.005 - 1e-9);
    const sky = { azimuth: 0, elevation: -1.4, distance: 170 };
    expect(aboveGround(sky, 170)).toBe(sky);
  });
});
