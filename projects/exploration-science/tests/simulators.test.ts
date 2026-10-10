import { readFileSync } from "node:fs";
import { join } from "node:path";
import { Vector3 } from "three";
import { describe, expect, it } from "vitest";
import type { Catalogue, Scene } from "../engine/src/content/types";
import { PluginRegistry } from "../engine/src/core/registry";
import { buildScene } from "../engine/src/core/sceneBuilder";
import { buildSimulation } from "../engine/src/core/simulation";
import { registerComponents } from "../engine/src/plugins/components";
import { SIMULATORS, registerSimulators } from "../engine/src/plugins/simulators";
import { orbitalPeriod, orbitalSpeed, passDuration, skyPosition, trainOffset } from "../engine/src/plugins/simulators/orbitalPass";
import { arrayFactor, gratingLobesDeg, phaseStepDeg, steeringDeg, wavelength } from "../engine/src/plugins/simulators/phasedArrayWave";

const ROOT = join(import.meta.dirname, "..");
const readJson = (path: string) => JSON.parse(readFileSync(join(ROOT, path), "utf8"));
const catalogue: Catalogue = readJson("catalogue/catalogue.json");
const starlink: Scene = readJson("content/nodes/starlink-terminal/scene.json");

const registry = new PluginRegistry();
registerComponents(registry);
registerSimulators(registry);

describe("simulator plugins", () => {
  it("are all declared in the catalogue (design rule 2)", () => {
    const ids = new Set(catalogue.simulators.map((s) => s.id));
    for (const plugin of SIMULATORS) expect(ids.has(plugin.id), plugin.id).toBe(true);
  });
});

// Design rule 4: each simulator is checked against its equations.
describe("phased-array-wave", () => {
  it("λ = c / f: about 2.5 cm in Ku band (12 GHz)", () => {
    expect(wavelength(12e9)).toBeCloseTo(0.025, 3);
  });

  it("puts the main beam where Δφ = 2π d sinθ / λ says", () => {
    for (const [theta, dOverLambda, n] of [
      [0, 0.5, 16],
      [20, 0.5, 16],
      [-35, 0.5, 32],
      [50, 0.4, 24],
    ] as const) {
      const phase = phaseStepDeg(theta, dOverLambda);
      expect(phase).toBeCloseTo(360 * dOverLambda * Math.sin((theta * Math.PI) / 180), 6);
      // Brute-force argmax of the array factor over visible space.
      let best = -90;
      for (let t = -90; t <= 90; t += 0.05) if (arrayFactor(t, n, dOverLambda, phase) > arrayFactor(best, n, dOverLambda, phase)) best = t;
      expect(best).toBeCloseTo(theta, 1);
      expect(arrayFactor(theta, n, dOverLambda, phase)).toBeCloseTo(1, 6);
      expect(steeringDeg(phase, dOverLambda)).toBeCloseTo(theta, 6);
    }
  });

  it("shows no grating lobe at d = λ/2, and one beyond it when steered", () => {
    expect(gratingLobesDeg(35, 0.5)).toEqual([]);
    const lobes = gratingLobesDeg(35, 1);
    expect(lobes).toHaveLength(1);
    // sinθ1 = sin35° − 1
    expect(lobes[0]).toBeCloseTo((Math.asin(Math.sin((35 * Math.PI) / 180) - 1) * 180) / Math.PI, 6);
    expect(arrayFactor(lobes[0]!, 16, 1, phaseStepDeg(35, 1))).toBeCloseTo(1, 6);
  });
});

describe("orbital-pass", () => {
  const h = 480_000;

  it("v = √(μ / (R + h)): about 7.6 km/s, i.e. more than 27 000 km/h at 480 km", () => {
    expect(orbitalSpeed(h) / 1000).toBeCloseTo(7.62, 1);
    expect(orbitalSpeed(h) * 3.6).toBeGreaterThan(27_000);
  });

  it("T = 2π √((R + h)³ / μ): about 94 min", () => {
    expect(orbitalPeriod(h) / 60).toBeCloseTo(94, 0);
  });

  it("an overhead pass above 25° lasts about 4 min", () => {
    expect(passDuration(h, 25) / 60).toBeCloseTo(4, 0);
  });

  it("culminates at the zenith and crosses 25° at ± half the pass duration", () => {
    expect(skyPosition(h, 0).elevationDeg).toBeCloseTo(90, 6);
    expect(skyPosition(h, passDuration(h, 25) / 2).elevationDeg).toBeCloseTo(25, 6);
    expect(skyPosition(h, -passDuration(h, 0) / 2).elevationDeg).toBeCloseTo(0, 6);
  });

  it("loops the train within [-loop/2, loop/2)", () => {
    expect(trainOffset(0, 1, 230, 690)).toBe(-230);
    expect(trainOffset(400, 0, 230, 690)).toBe(-290);
  });

  it("moves the bound satellites onto their true direction, hidden below the horizon", () => {
    const built = buildScene(starlink, catalogue, registry);
    const sim = buildSimulation(starlink, catalogue, registry, built);
    expect(sim.missing).toEqual([]);
    const terminal = built.entities.get("terminal")!.node.getWorldPosition(new Vector3());
    const satA = built.entities.get("sat-a")!;
    // t = 0: the first satellite culminates, straight above the terminal.
    const offset = satA.node.position.clone().sub(terminal);
    expect(offset.length()).toBeCloseTo(60, 6);
    expect(offset.y).toBeCloseTo(60, 6);
    sim.advance(120);
    const el = (sim.instances.get("orbit")!.outputs().elevationsDeg as Record<string, number>)["sat-a"]!;
    const now = satA.node.position.clone().sub(terminal);
    expect((Math.asin(now.y / now.length()) * 180) / Math.PI).toBeCloseTo(el, 6);
    expect(now.z).toBeLessThan(0); // moving along -Z
    sim.advance(343 - 120); // just past the horizon (≈ 340 s after culmination)
    expect(satA.instance.object.visible).toBe(false);
  });

  it("lets the beam follow its target: angle from the array normal", () => {
    const built = buildScene(starlink, catalogue, registry);
    const sim = buildSimulation(starlink, catalogue, registry, built);
    built.root.updateMatrixWorld(true);
    sim.advance(0);
    const beam = sim.instances.get("beam")!;
    const array = built.entities.get("phased-array")!.node;
    const normal = new Vector3(0, 1, 0).transformDirection(array.matrixWorld);
    const toSat = built.entities.get("sat-a")!.node.getWorldPosition(new Vector3()).sub(array.getWorldPosition(new Vector3())).normalize();
    const expected = (Math.acos(normal.dot(toSat)) * 180) / Math.PI;
    expect(Math.abs(beam.outputs().steeringAngleDeg as number)).toBeCloseTo(expected, 3);
    // Manual steering takes over when tracking is off.
    beam.set("tracking", false);
    beam.set("steeringAngleDeg", 35);
    sim.advance(10);
    expect(beam.outputs().steeringAngleDeg).toBe(35);
    expect(beam.outputs().phaseStepDeg).toBeCloseTo(180 * Math.sin((35 * Math.PI) / 180), 6);
  });

  it("resets to the scene's params at time 0", () => {
    const built = buildScene(starlink, catalogue, registry);
    const sim = buildSimulation(starlink, catalogue, registry, built);
    sim.instances.get("beam")!.set("tracking", false);
    sim.timeScale = 30;
    sim.advance(300);
    sim.reset();
    expect(sim.time).toBe(0);
    expect(sim.timeScale).toBe(1);
    expect(sim.instances.get("beam")!.params.tracking).toBe(true);
  });
});
