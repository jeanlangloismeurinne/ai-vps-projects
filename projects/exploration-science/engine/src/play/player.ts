import type { Action, RevealModeSpec, Shot, Step, Tour } from "../content/types";

/** What a tour drives. The engine implements it; tests use a fake. */
export interface Stage {
  /** Scene back to its initial state: visibility, reveals, lenses, params, simulated time 0. */
  reset(): void;
  /** Fast-forwards simulated time (used when jumping to a step). */
  advanceSim(simSeconds: number): void;
  /** Freezes or resumes simulated time. */
  setFrozen(frozen: boolean): void;
  flyTo(shot: Shot, durationS: number): void;
  setVisible(ids: string[], visible: boolean): void;
  reveal(id: string, mode: RevealModeSpec): void;
  setLens(id: string, on: boolean): void;
  getParam(simulator: string, param: string): unknown;
  setParam(simulator: string, param: string, value: unknown): void;
  setTimeScale(value: number): void;
  /** Step-scoped: replaced at every step, cleared at the end. */
  setHighlights(ids: string[]): void;
  setLabels(ids: string[]): void;
}

export type PlayerState = "idle" | "playing" | "paused";

export interface PlayerEvents {
  onStep?(tour: Tour, index: number): void;
  onState?(state: PlayerState): void;
  onEnd?(tour: Tour, completed: boolean): void;
}

interface Tween {
  simulator: string;
  param: string;
  from: number;
  to: number;
  elapsed: number;
  duration: number;
}

const RESUME_FLIGHT_S = 1.5;

/**
 * Plays a tour step by step (spec, Mode Play). A step's highlight and label
 * actions last for the step only; the other actions persist until changed.
 * Jumping to a step replays the scene from its initial state, so a step always
 * looks the same however it is reached.
 */
export class TourPlayer {
  private tour: Tour | null = null;
  private index = 0;
  private elapsed = 0;
  private timeScale = 1;
  private tweens: Tween[] = [];
  private _state: PlayerState = "idle";

  constructor(
    private readonly stage: Stage,
    private readonly events: PlayerEvents = {},
    private readonly initialTimeScale = 1,
  ) {}

  get state(): PlayerState {
    return this._state;
  }

  get current(): { tour: Tour; index: number; step: Step; elapsed: number } | null {
    if (!this.tour) return null;
    return { tour: this.tour, index: this.index, step: this.tour.steps[this.index]!, elapsed: this.elapsed };
  }

  play(tour: Tour, fromIndex = 0): void {
    this.tour = tour;
    this.seek(fromIndex);
  }

  pause(): void {
    if (this._state !== "playing") return;
    this.stage.setFrozen(true);
    this.setState("paused");
  }

  resume(): void {
    if (this._state !== "paused") return;
    const shot = this.current?.step.camera?.shot;
    if (shot) this.stage.flyTo(shot, RESUME_FLIGHT_S);
    this.stage.setFrozen(false);
    this.setState("playing");
  }

  next(): void {
    if (!this.tour) return;
    if (this.index + 1 >= this.tour.steps.length) this.stop(true);
    else this.seek(this.index + 1);
  }

  previous(): void {
    if (this.tour) this.seek(Math.max(0, this.index - 1));
  }

  /** Leaves the tour: the scene goes back to its initial state, the camera stays. */
  stop(completed = false): void {
    const tour = this.tour;
    if (!tour) return;
    this.tour = null;
    this.tweens = [];
    this.stage.setHighlights([]);
    this.stage.setLabels([]);
    this.stage.reset();
    this.stage.setFrozen(false);
    this.setState("idle");
    this.events.onEnd?.(tour, completed);
  }

  update(dt: number): void {
    if (this._state !== "playing" || !this.tour) return;
    this.elapsed += dt;
    this.tweens = this.tweens.filter((t) => {
      t.elapsed += dt;
      const k = Math.min(1, t.elapsed / t.duration);
      this.stage.setParam(t.simulator, t.param, t.from + (t.to - t.from) * k);
      return k < 1;
    });
    if (this.elapsed >= this.tour.steps[this.index]!.durationS) this.next();
  }

  private seek(index: number): void {
    const tour = this.tour!;
    this.stage.reset();
    this.timeScale = this.initialTimeScale;
    this.tweens = [];
    for (const step of tour.steps.slice(0, index)) {
      for (const action of step.actions ?? []) this.apply(action, true);
      this.stage.advanceSim(step.durationS * this.timeScale);
    }
    this.index = index;
    this.elapsed = 0;
    const step = tour.steps[index]!;
    if (step.camera) this.stage.flyTo(step.camera.shot, step.camera.transitionS ?? 0);
    this.stage.setHighlights([]);
    this.stage.setLabels([]);
    for (const action of step.actions ?? []) this.apply(action, false);
    this.stage.setFrozen(false);
    this.setState("playing");
    this.events.onStep?.(tour, index);
  }

  private apply(action: Action, instant: boolean): void {
    switch (action.type) {
      case "highlight":
        if (!instant) this.stage.setHighlights(action.targets);
        break;
      case "label":
        if (!instant) this.stage.setLabels(action.targets);
        break;
      case "show":
      case "hide":
        this.stage.setVisible(action.targets, action.type === "show");
        break;
      case "reveal":
        this.stage.reveal(action.target, action.mode);
        break;
      case "lens":
        this.stage.setLens(action.lens, action.on);
        break;
      case "timeScale":
        this.timeScale = action.value;
        this.stage.setTimeScale(action.value);
        break;
      case "setParam": {
        const from = this.stage.getParam(action.target, action.param);
        if (!instant && action.overS && typeof action.value === "number" && typeof from === "number") {
          this.tweens.push({ simulator: action.target, param: action.param, from, to: action.value, elapsed: 0, duration: action.overS });
        } else {
          this.stage.setParam(action.target, action.param, action.value);
        }
        break;
      }
    }
  }

  private setState(state: PlayerState): void {
    if (state === this._state) return;
    this._state = state;
    this.events.onState?.(state);
  }
}
