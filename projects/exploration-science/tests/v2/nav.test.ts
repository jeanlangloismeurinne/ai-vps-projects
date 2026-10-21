import { describe, expect, it } from "vitest";
import render from "../../content/v2/render.json";
import { back, closerShot, current, enter, initialNav, orbit, select, zoom, type NavRules } from "../../v2/src/nav";

const rules = render as unknown as NavRules;
const start = () => initialNav(rules, "global", null);

describe("v2 navigation", () => {
  it("goes global → object → detail and back twice to the same view and card", () => {
    let nav = select(rules, start(), "terminal");
    nav = orbit(rules, nav, 12, -5);
    nav = zoom(rules, nav, 0.8);
    const before = current(nav);
    nav = enter(rules, nav, "terminal");
    expect(current(nav).shot).toBe("object:terminal");
    nav = orbit(rules, nav, -20, 10);
    nav = enter(rules, nav, "terminal");
    expect(current(nav).shot).toBe("detail:terminal");
    nav = back(back(nav));
    expect(nav.stack).toHaveLength(1);
    expect(current(nav)).toEqual(before);
  });

  it("keeps the orbit of a closer view when coming back to it", () => {
    let nav = enter(rules, start(), "terminal");
    nav = orbit(rules, nav, 7, 0);
    const object = current(nav);
    nav = back(enter(rules, nav, "terminal"));
    expect(current(nav)).toEqual(object);
  });

  it("closes the card when going back from the global view, and only then", () => {
    let nav = select(rules, start(), "house");
    nav = back(nav);
    expect(current(nav).selected).toBeNull();
    expect(back(nav)).toBe(nav);
  });

  it("does not enter a shot render.json lacks", () => {
    const nav = enter(rules, start(), "house");
    expect(closerShot(rules, nav, "house")).toBeNull(); // no detail:house
    expect(enter(rules, nav, "house")).toBe(nav);
  });

  it("selecting another object from a close view goes to that object's view", () => {
    let nav = enter(rules, start(), "terminal");
    nav = select(rules, nav, "satellite");
    expect(nav.stack.map((e) => [e.shot, e.selected])).toEqual([
      ["global", "satellite"],
      ["object:satellite", "satellite"],
    ]);
    expect(select(rules, nav, null)).toBe(nav); // a tap in the void does not leave a close view
  });

  it("keeps orbit and zoom within render.json limits", () => {
    let nav = orbit(rules, start(), 500, 500);
    nav = zoom(rules, nav, 100);
    const { view } = current(nav);
    expect(view.orbitDeg).toBe(rules.limits.azimuthRangeDeg[1]);
    expect(view.elevationDeg).toBe(rules.limits.elevationRangeDeg[1]);
    expect(view.zoom).toBe(rules.limits.zoomRange[1]);
    nav = zoom(rules, orbit(rules, nav, -1000, -1000), 1e-6);
    expect(current(nav).view).toEqual({
      orbitDeg: rules.limits.azimuthRangeDeg[0],
      elevationDeg: rules.limits.elevationRangeDeg[0],
      zoom: rules.limits.zoomRange[0],
    });
  });

  it("opens a URL shot as if walked to from the global view", () => {
    const nav = initialNav(rules, "detail:terminal", null);
    expect(nav.stack.map((e) => [e.shot, e.selected])).toEqual([
      ["global", "terminal"],
      ["object:terminal", "terminal"],
      ["detail:terminal", "terminal"],
    ]);
    expect(() => initialNav(rules, "object:moon", null)).toThrow();
  });
});
