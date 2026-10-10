import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import type { Scene, Shot, Tour } from "../engine/src/content/types";
import { TourPlayer, type Stage } from "../engine/src/play/player";

const ROOT = join(import.meta.dirname, "..");
const starlink: Scene = JSON.parse(readFileSync(join(ROOT, "content/nodes/starlink-terminal/scene.json"), "utf8"));
const main = starlink.tours.find((t) => t.id === "main")!;

// Records the state a real stage would be in.
class FakeStage implements Stage {
  simTime = 0;
  frozen = false;
  shot: Shot | null = null;
  visible = new Map<string, boolean>();
  reveals = new Map<string, string>();
  lenses = new Map<string, boolean>();
  params = new Map<string, unknown>();
  timeScale = 1;
  highlights: string[] = [];
  labels: string[] = [];
  resets = 0;
  reset() {
    this.resets++;
    this.simTime = 0;
    this.visible.clear();
    this.reveals.clear();
    this.lenses.clear();
    this.params.clear();
    this.timeScale = 1;
  }
  advanceSim(s: number) {
    this.simTime += s;
  }
  setFrozen(f: boolean) {
    this.frozen = f;
  }
  flyTo(shot: Shot) {
    this.shot = shot;
  }
  setVisible(ids: string[], v: boolean) {
    for (const id of ids) this.visible.set(id, v);
  }
  reveal(id: string, mode: string) {
    this.reveals.set(id, mode);
  }
  setLens(id: string, on: boolean) {
    this.lenses.set(id, on);
  }
  getParam(sim: string, param: string) {
    return this.params.get(`${sim}.${param}`) ?? 0;
  }
  setParam(sim: string, param: string, value: unknown) {
    this.params.set(`${sim}.${param}`, value);
  }
  setTimeScale(v: number) {
    this.timeScale = v;
  }
  setHighlights(ids: string[]) {
    this.highlights = ids;
  }
  setLabels(ids: string[]) {
    this.labels = ids;
  }
}

function run(player: TourPlayer, seconds: number, dt = 0.1) {
  for (let t = 0; t < seconds - 1e-9; t += dt) player.update(dt);
}

describe("TourPlayer on the Starlink main tour", () => {
  it("plays the steps in order, with their duration, then hands back a reset scene", () => {
    const stage = new FakeStage();
    const seen: string[] = [];
    let ended = false;
    const player = new TourPlayer(stage, { onStep: (tour, i) => seen.push(tour.steps[i]!.id), onEnd: (_, completed) => (ended = completed) });
    player.play(main);
    expect(stage.shot).toEqual(main.steps[0]!.camera!.shot);
    expect(stage.highlights).toEqual(["terminal", "sat-a"]);
    run(player, main.steps[0]!.durationS + 0.05);
    expect(player.current!.index).toBe(1);
    expect(stage.highlights).toEqual(["sat-a"]); // step-scoped
    expect(stage.labels).toEqual([]);
    expect(stage.visible.get("link-user-a")).toBe(true); // persists
    run(player, main.steps.reduce((s, step) => s + step.durationS, 0));
    expect(seen).toEqual(main.steps.map((s) => s.id));
    expect(ended).toBe(true);
    expect(player.state).toBe("idle");
    expect(stage.highlights).toEqual([]);
    expect(stage.visible.size).toBe(0); // reset
  });

  it("animates a setParam with overS", () => {
    const stage = new FakeStage();
    const player = new TourPlayer(stage);
    const steering = main.steps.findIndex((s) => s.id === "beam-steering");
    player.play(main, steering);
    run(player, 2.5);
    expect(stage.params.get("beam.steeringAngleDeg")).toBeCloseTo(17.5, 0);
    run(player, 3);
    expect(stage.params.get("beam.steeringAngleDeg")).toBe(35);
  });

  it("reaches a step in the same state however it gets there", () => {
    const direct = new FakeStage();
    new TourPlayer(direct).play(main, 4);
    const played = new FakeStage();
    const player = new TourPlayer(played);
    player.play(main);
    run(player, main.steps.slice(0, 4).reduce((s, step) => s + step.durationS, 0) + 0.05, 0.05);
    expect(player.current!.index).toBe(4);
    for (const key of ["visible", "reveals", "lenses", "params", "highlights", "labels", "timeScale"] as const) {
      expect(JSON.stringify([...Object.entries(direct[key] instanceof Map ? Object.fromEntries(direct[key] as Map<string, unknown>) : { v: direct[key] })]), key).toEqual(
        JSON.stringify([...Object.entries(played[key] instanceof Map ? Object.fromEntries(played[key] as Map<string, unknown>) : { v: played[key] })]),
      );
    }
    // Simulated time: the jump fast-forwards what playing ran, step by step at each step's time scale.
    const expectedSim = 24 * 1 + 22 * stageScale(main, 1) + 18 + 30;
    expect(direct.simTime).toBe(expectedSim);
  });

  it("freezes time on pause, flies back to the step's shot on resume", () => {
    const stage = new FakeStage();
    const player = new TourPlayer(stage);
    player.play(main, 2);
    player.pause();
    expect(stage.frozen).toBe(true);
    run(player, 100);
    expect(player.current!.index).toBe(2);
    stage.shot = null;
    player.resume();
    expect(stage.frozen).toBe(false);
    expect(stage.shot).toEqual(main.steps[2]!.camera!.shot);
  });

  it("next() past the last step ends the tour; previous() stops at the first", () => {
    const stage = new FakeStage();
    const player = new TourPlayer(stage);
    const short: Tour = { id: "t", steps: [main.steps[0]!, main.steps[1]!] };
    player.play(short);
    player.previous();
    expect(player.current!.index).toBe(0);
    player.next();
    player.next();
    expect(player.state).toBe("idle");
  });
});

/** Time scale set by the actions of step `index` (the problem step speeds time up). */
function stageScale(tour: Tour, index: number): number {
  const action = tour.steps[index]!.actions?.find((a) => a.type === "timeScale");
  return action && action.type === "timeScale" ? action.value : 1;
}

describe("jumping into a step without its own shot", () => {
  it("frames the scene with the last shot set before it", () => {
    const element: Scene = JSON.parse(readFileSync(join(ROOT, "content/nodes/starlink-radiating-element/scene.json"), "utf8"));
    const tour = element.tours.find((t) => t.id === "main")!;
    const index = tour.steps.findIndex((s) => s.id === "delay");
    expect(tour.steps[index]!.camera).toBeUndefined();
    const stage = new FakeStage();
    new TourPlayer(stage).play(tour, index);
    const last = tour.steps.slice(0, index).reverse().find((s) => s.camera)!.camera!.shot;
    expect(stage.shot).toEqual(last);
  });
});
