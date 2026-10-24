import { describe, expect, it } from "vitest";
import render from "../../content/v2/render/starlink-home.json";
import texts from "../../content/v2/texts/starlink-home.fr.json";
import tour from "../../content/v2/tours/starlink-home.json";
import { current, type NavRules } from "../../v2/src/nav";
import { MIN_STEP_S, READING_CPS, readingTime, stepAt, stepNav, timeline, type StepLike } from "../../v2/src/tour";

const rules = render as unknown as NavRules;
const steps = tour.steps as StepLike[];
const text = (key: string) => (texts.entries as Record<string, string>)[key]!;

describe("v2 guided tour", () => {
  it("gives each step the time to read its subtitle, no more", () => {
    const line = timeline(steps, text);
    steps.forEach((s, i) => {
      const chars = text(s.textKey).length;
      expect(line.durations[i]).toBeCloseTo(Math.max(chars / READING_CPS, MIN_STEP_S), 6);
    });
    expect(readingTime("ab")).toBe(MIN_STEP_S);
    // Fast: the whole tour reads in well under a minute.
    expect(line.total).toBeLessThan(45);
  });

  it("finds the step played at a given time, and none after the end", () => {
    const line = timeline(steps, text);
    expect(stepAt(line, 0)).toBe(0);
    expect(stepAt(line, line.starts[2]! + 0.01)).toBe(2);
    expect(stepAt(line, line.total)).toBeNull();
  });

  it("shows the system before any object: nothing selected until a system step is over", () => {
    expect(steps[0]!.focus.kind).toBe("system");
    const first = steps.findIndex((s) => s.focus.kind === "object");
    for (const s of steps.slice(0, first)) {
      const nav = stepNav(rules, s);
      expect(current(nav).shot).toBe("global");
      expect(current(nav).selected).toBeNull();
      expect(nav.stack).toHaveLength(1);
    }
  });

  it("reaches each object step as if walked there, so that back still works", () => {
    const inside = stepNav(rules, steps.find((s) => s.shot === "detail:terminal")!);
    expect(inside.stack.map((e) => e.shot)).toEqual(["global", "object:terminal", "detail:terminal"]);
    expect(current(inside).selected).toBe("terminal");
  });
});
