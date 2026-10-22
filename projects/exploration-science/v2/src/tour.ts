// Guided tour, pure: each step lasts as long as its subtitle takes to read, no longer (the
// camera flies while the viewer reads), and puts the navigation where the step says, as if
// the user had walked there, so that the hand-over keeps a working "back".
import { initialNav, type Nav, type NavRules } from "./nav";

/** Reading speed of a subtitle, in characters per second (spaces included): the usual
 * ceiling for adult subtitles, so the tour goes as fast as a reader can follow. */
export const READING_CPS = 17;
/** Shortest step, in seconds: time for the camera's flight (~1.1 s) and a glance. */
export const MIN_STEP_S = 2;

export interface StepLike {
  id: string;
  shot: string;
  focus: { kind: "system" } | { kind: "object"; id: string };
  highlight?: string[];
  flows?: string[];
  textKey: string;
}

export const readingTime = (text: string): number => Math.max(text.trim().length / READING_CPS, MIN_STEP_S);

export interface Timeline {
  /** Start of each step, in seconds from the start of the tour. */
  starts: number[];
  durations: number[];
  total: number;
}

export function timeline(steps: StepLike[], text: (key: string) => string): Timeline {
  const durations = steps.map((s) => readingTime(text(s.textKey)));
  const starts: number[] = [];
  let t = 0;
  for (const d of durations) {
    starts.push(t);
    t += d;
  }
  return { starts, durations, total: t };
}

/** Step played at `t` seconds, or null once the tour is over. */
export function stepAt(line: Timeline, t: number): number | null {
  if (t < 0 || t >= line.total) return null;
  let i = 0;
  while (i + 1 < line.starts.length && line.starts[i + 1]! <= t) i++;
  return i;
}

/** Navigation of a step: its shot reached from the global view, its subject selected. A
 * system step selects nothing: no object is put forward before the system is shown. */
export function stepNav(rules: NavRules, step: StepLike): Nav {
  return initialNav(rules, step.shot, step.focus.kind === "object" ? step.focus.id : null);
}
