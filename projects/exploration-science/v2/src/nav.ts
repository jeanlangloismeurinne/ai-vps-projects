// Navigation between shots, pure: a stack of views (global → object → detail), each with the
// card it shows and the orbit the user gave it. Going back pops the stack, so the view left
// is found again as it was (roadmap §5: same pose and selection after a round trip).

/** What the user changed of a shot by hand, within render.json `limits`. */
export interface View {
  /** Azimuth added to the shot's, in degrees. */
  orbitDeg: number;
  /** Absolute elevation, in degrees. */
  elevationDeg: number;
  /** Factor on the shot's distance (< 1 is closer). */
  zoom: number;
}

export interface Entry {
  shot: string;
  selected: string | null;
  view: View;
}

export interface Nav {
  stack: Entry[];
}

export interface ShotLike {
  elevationDeg: number;
}

export interface Limits {
  azimuthRangeDeg: [number, number] | number[];
  elevationRangeDeg: [number, number] | number[];
  zoomRange: [number, number] | number[];
}

export interface NavRules {
  shots: Record<string, ShotLike>;
  limits: Limits;
}

const clamp = (v: number, [lo, hi]: [number, number] | number[]) => Math.min(Math.max(v, lo!), hi!);

/** Object a shot is about (`object:house` → `house`), null for the global shot. */
export const subjectOf = (shot: string): string | null => (shot.includes(":") ? shot.slice(shot.indexOf(":") + 1) : null);

const levelOf = (shot: string) => (shot.startsWith("detail:") ? 2 : shot.startsWith("object:") ? 1 : 0);

const entry = (rules: NavRules, shot: string, selected: string | null): Entry => ({
  shot,
  selected,
  view: { orbitDeg: 0, elevationDeg: clamp(rules.shots[shot]!.elevationDeg, rules.limits.elevationRangeDeg), zoom: 1 },
});

export const current = (nav: Nav): Entry => nav.stack[nav.stack.length - 1]!;

/** The stack that leads to `shot` from the global view, as if the user had walked there:
 * `detail:terminal` → global (terminal selected), object:terminal, detail:terminal. */
export function initialNav(rules: NavRules, shot: string, selected: string | null): Nav {
  if (!rules.shots[shot]) throw new Error(`unknown shot: ${shot}`);
  const subject = subjectOf(shot);
  const stack = [entry(rules, "global", subject ?? selected)];
  if (subject && levelOf(shot) === 2 && rules.shots[`object:${subject}`]) stack.push(entry(rules, `object:${subject}`, subject));
  if (subject) stack.push(entry(rules, shot, subject));
  return { stack };
}

/** Shot one level closer than the current one on `id`, if render.json has it. */
export function closerShot(rules: NavRules, nav: Nav, id: string): string | null {
  const level = levelOf(current(nav).shot);
  const shot = level === 0 ? `object:${id}` : level === 1 ? `detail:${id}` : null;
  return shot && rules.shots[shot] ? shot : null;
}

/** Selects a main object (null closes the card). In the global view, the camera stays; in a
 * closer view, the camera goes to the same kind of view of the new object when there is one,
 * as if it had been selected from the global view. */
export function select(rules: NavRules, nav: Nav, id: string | null): Nav {
  const top = current(nav);
  if (nav.stack.length === 1 || id === null) {
    if (nav.stack.length > 1) return nav; // closing the card is going back, not deselecting
    return top.selected === id ? nav : { stack: [{ ...top, selected: id }] };
  }
  if (top.selected === id) return nav;
  const shot = `object:${id}`;
  if (!rules.shots[shot]) return { stack: [...nav.stack.slice(0, -1), { ...top, selected: id }] };
  return { stack: [{ ...nav.stack[0]!, selected: id }, entry(rules, shot, id)] };
}

/** One level closer on `id` (selecting it), or unchanged if there is no such shot. */
export function enter(rules: NavRules, nav: Nav, id: string): Nav {
  const shot = closerShot(rules, nav, id);
  if (!shot) return nav;
  const stack = nav.stack.map((e, i) => (i === nav.stack.length - 1 ? { ...e, selected: id } : e));
  return { stack: [...stack, entry(rules, shot, id)] };
}

/** Back one level; in the global view, closes the card. */
export function back(nav: Nav): Nav {
  if (nav.stack.length > 1) return { stack: nav.stack.slice(0, -1) };
  const top = current(nav);
  return top.selected === null ? nav : { stack: [{ ...top, selected: null }] };
}

/** Turns the current view by `dOrbitDeg` and `dElevationDeg`, within the limits. */
export function orbit(rules: NavRules, nav: Nav, dOrbitDeg: number, dElevationDeg: number): Nav {
  const top = current(nav);
  const view = {
    ...top.view,
    orbitDeg: clamp(top.view.orbitDeg + dOrbitDeg, rules.limits.azimuthRangeDeg),
    elevationDeg: clamp(top.view.elevationDeg + dElevationDeg, rules.limits.elevationRangeDeg),
  };
  return { stack: [...nav.stack.slice(0, -1), { ...top, view }] };
}

/** Multiplies the current view's distance by `factor`, within the limits. */
export function zoom(rules: NavRules, nav: Nav, factor: number): Nav {
  const top = current(nav);
  const view = { ...top.view, zoom: clamp(top.view.zoom * factor, rules.limits.zoomRange) };
  return { stack: [...nav.stack.slice(0, -1), { ...top, view }] };
}
