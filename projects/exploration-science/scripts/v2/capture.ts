// npm run capture [-- --system ID] [-- --out DIR] [-- --only global,...] [-- --formats ipad-landscape,...] [-- --video]
// Starts the Vite dev server, opens v2.html in headless Chromium (software WebGL:
// valid for composition and materials, NOT for frame rate) and saves one PNG per
// view and screen format, plus render stats (draw calls, triangles) in captures.json.
// Then, per format, clicks (or taps) each main object for real and checks its card:
// right object, right title, at most 10 % of any main object under it (roadmap §4).
// Then walks global → object → detail → back twice, twice over, with real clicks (or taps)
// and drags / pinches (or wheel), and checks that pose and card come back as they were; and,
// in one format, saves a transition frame by frame (`transition/`: frames and a contact
// sheet, the one inspected; `--video` adds a WebM for a person to watch) (roadmap §5).
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { chromium, type Page } from "@playwright/test";
import { createServer } from "vite";

const root = resolve(import.meta.dirname, "../..");
const arg = (name: string) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > 0 ? process.argv[i + 1] : undefined;
};

export const FORMATS = {
  "ipad-landscape": { width: 1366, height: 1024 },
  "ipad-portrait": { width: 1024, height: 1366 },
  phone: { width: 390, height: 844 },
  desktop: { width: 1920, height: 1080 },
} as const;

// The system captured (default starlink-home), its main objects, and the object the
// transitions walk through: the one with an exploded view, else the first main object.
const SYSTEM = arg("system") ?? "starlink-home";
const content = (dir: string, suffix = ".json") => JSON.parse(readFileSync(join(root, "content/v2", dir, `${SYSTEM}${suffix}`), "utf8"));
const objects = content("systems").objects as { id: string; role: string; representations?: string[] }[];
const MAIN = objects.filter((o) => o.role === "main").map((o) => o.id);
const DETAILED = objects.find((o) => o.role === "main" && o.representations?.includes("detail"))?.id ?? null;
const FOCUS = DETAILED ?? MAIN[0]!;
const TOUR_STEPS = (content("tours").steps as { id: string }[]).map((s) => s.id);
const appUrl = (query = "") => `http://localhost:5199/v2.html?system=${SYSTEM}${query ? `&${query}` : ""}`;
// View name → query string understood by the v2 app. Grows with the roadmap.
// `t` pins the phase of the animated flows, so that captures are comparable.
const T = "t=1.5";
export const VIEWS: Record<string, string> = {
  global: T,
  ...Object.fromEntries(MAIN.map((id) => [`card-${id}`, `select=${id}&${T}`])),
  ...Object.fromEntries(MAIN.map((id) => [`object-${id}`, `shot=object:${id}&${T}`])),
  ...Object.fromEntries(MAIN.map((id) => [`silhouette-${id}`, `shot=object:${id}&silhouette`])),
  ...(DETAILED ? { [`detail-${DETAILED}`]: `shot=detail:${DETAILED}&select=${DETAILED}&${T}` } : {}),
  // Each step of the guided tour, held (roadmap §7).
  ...Object.fromEntries(TOUR_STEPS.map((id, i) => [`tour-${i}-${id}`, `tour=${i}&${T}`])),
};

const stamp = new Date().toISOString().slice(0, 16).replace(/[:T]/g, "-");
const out = resolve(arg("out") ?? join(root, "captures/v2", SYSTEM === "starlink-home" ? stamp : `${SYSTEM}-${stamp}`));
const only = arg("only")?.split(",");
const formats = (arg("formats")?.split(",") ?? Object.keys(FORMATS)) as (keyof typeof FORMATS)[];
mkdirSync(out, { recursive: true });

const server = await createServer({ root, logLevel: "error", server: { port: 5199, strictPort: true } });
await server.listen();
const browser = await chromium.launch({
  executablePath: process.env.XS_CHROMIUM ?? "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
});

const cards = content("texts", ".fr.json").cards as Record<string, { title: string }>;
const MAX_OVERLAP = 0.1;
const ready = (page: Page) => page.waitForFunction(() => window.__xs?.ready === true, null, { timeout: 120_000 });

/** Clicks each main object from the global view; returns the problems found. */
async function checkSelection(page: Page, touch: boolean): Promise<{ checks: Record<string, unknown>; problems: string[] }> {
  const checks: Record<string, unknown> = {};
  const problems: string[] = [];
  await page.goto(appUrl(T), { timeout: 120_000 });
  await ready(page);
  for (const id of MAIN) {
    console.log(`${new Date().toISOString().slice(11, 19)}   click ${id}`);
    const point = await page.evaluate((id) => window.__xs!.pickPoint(id), id);
    if (!point) {
      problems.push(`${id}: no visible point to click`);
      continue;
    }
    if (touch) await page.touchscreen.tap(point.x, point.y);
    else await page.mouse.click(point.x, point.y);
    const card = page.locator(".card");
    await card.waitFor({ timeout: 10_000 }).catch(() => {});
    const opened = (await card.count()) ? await card.getAttribute("data-object") : null;
    const title = opened ? await card.locator("h2").textContent() : null;
    await ready(page);
    const overlap = await page.evaluate(() => window.__xs!.overlap());
    checks[id] = { point, opened, title, overlap };
    if (opened !== id) problems.push(`${id}: clicked, card opened for ${opened}`);
    if (title !== cards[id]!.title) problems.push(`${id}: card title '${title}'`);
    for (const [obj, share] of Object.entries(overlap)) if (share > MAX_OVERLAP) problems.push(`${id}: card covers ${(share * 100).toFixed(1)} % of ${obj}`);
    await page.locator(".card__close").click();
    await card.waitFor({ state: "detached", timeout: 5_000 }).catch(() => problems.push(`${id}: card did not close`));
    await ready(page);
  }
  return { checks, problems };
}

type Pose = NonNullable<ReturnType<NonNullable<Window["__xs"]>["pose"]>>;
const state = (page: Page) => page.evaluate(() => ({ pose: window.__xs!.pose()!, nav: window.__xs!.nav, selected: window.__xs!.selected }));

/** Largest difference between two poses, relative to the camera distance (angles in degrees,
 * offset in px kept apart). */
function poseDiff(a: Pose, b: Pose): number {
  const d = Math.max(...a.position.map((v, i) => Math.abs(v - b.position[i]!)), ...a.target.map((v, i) => Math.abs(v - b.target[i]!))) / b.distance;
  return Math.max(d, Math.abs(a.azimuthDeg - b.azimuthDeg) / 100, Math.abs(a.elevationDeg - b.elevationDeg) / 100, ...a.offset.map((v, i) => Math.abs(v - b.offset[i]!) / 1000));
}
const EPSILON = 1e-4;

/** Drags one finger (or the mouse) by (dx, dy) from (x, y), in small steps. */
async function drag(page: Page, touch: boolean, x: number, y: number, dx: number, dy: number) {
  const steps = 8;
  if (!touch) {
    await page.mouse.move(x, y);
    await page.mouse.down();
    for (let i = 1; i <= steps; i++) await page.mouse.move(x + (dx * i) / steps, y + (dy * i) / steps);
    await page.mouse.up();
    return;
  }
  const cdp = await page.context().newCDPSession(page);
  await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x, y, id: 1 }] });
  for (let i = 1; i <= steps; i++) await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [{ x: x + (dx * i) / steps, y: y + (dy * i) / steps, id: 1 }] });
  await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
  await cdp.detach();
}

/** Two fingers from `gap` px apart to `gap * factor` (factor > 1 spreads them: closer view),
 * or the wheel for the mouse. */
async function pinch(page: Page, touch: boolean, x: number, y: number, factor: number) {
  if (!touch) {
    await page.mouse.move(x, y);
    await page.mouse.wheel(0, -Math.log(factor) / 0.0015);
    return;
  }
  const cdp = await page.context().newCDPSession(page);
  const gap = 80;
  const at = (g: number) => [{ x: x - g / 2, y, id: 1 }, { x: x + g / 2, y, id: 2 }];
  await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: at(gap) });
  for (let i = 1; i <= 8; i++) await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: at(gap * (1 + ((factor - 1) * i) / 8)) });
  await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
  await cdp.detach();
}

/** A point of the scene away from the card and the objects, to start gestures on. */
const emptyPoint = (page: Page) => {
  const v = page.viewportSize()!;
  return { x: Math.round(v.width * 0.12), y: Math.round(v.height * 0.2) };
};

/** global → object → detail → back → back (no detail: global → object → back), twice, from the
 * selected FOCUS object in a view the user
 * has turned and zoomed; gestures are checked against render.json limits on the way. */
async function checkTransitions(page: Page, touch: boolean): Promise<{ checks: Record<string, unknown>; problems: string[] }> {
  const checks: Record<string, unknown> = {};
  const problems: string[] = [];
  const limits = content("render").limits;
  await page.goto(appUrl(T), { timeout: 120_000 });
  await ready(page);
  const at = emptyPoint(page);
  const s0 = await state(page);
  // Gestures in the global view: a drag turns it, a pinch (wheel) brings it closer.
  await drag(page, touch, at.x, at.y, 120, 40);
  await ready(page);
  const s1 = await state(page);
  if (!(s1.nav.view.orbitDeg < 0 && s1.nav.view.elevationDeg > s0.nav.view.elevationDeg)) problems.push(`drag did not turn the view: ${JSON.stringify(s1.nav.view)}`);
  if (poseDiff(s1.pose, s0.pose) < 1e-3) problems.push("drag did not move the camera");
  if (s1.selected) problems.push(`drag selected ${s1.selected}`);
  await pinch(page, touch, at.x + 60, at.y + 40, 1.25);
  await ready(page);
  const s2 = await state(page);
  if (!(s2.nav.view.zoom < 1)) problems.push(`pinch did not zoom in: ${s2.nav.view.zoom}`);
  if (s2.pose.distance >= s1.pose.distance) problems.push("pinch did not bring the camera closer");
  // Beyond the limits, the view stops at them.
  await drag(page, touch, at.x, at.y, -3000, -3000);
  await ready(page);
  await pinch(page, touch, at.x + 60, at.y + 40, 0.2);
  await ready(page);
  const s3 = await state(page);
  const v = s3.nav.view;
  if (v.orbitDeg !== limits.azimuthRangeDeg[1] || v.elevationDeg !== limits.elevationRangeDeg[0] || v.zoom !== limits.zoomRange[1]) problems.push(`limits not held: ${JSON.stringify(v)}`);
  checks.gestures = { s0: s0.nav.view, drag: s1.nav.view, pinch: s2.nav.view, limits: v };
  await drag(page, touch, at.x, at.y, 600, 200);
  await ready(page);

  const point = await page.evaluate((id) => window.__xs!.pickPoint(id), FOCUS);
  if (!point) return { checks, problems: [...problems, `${FOCUS}: no visible point to tap`] };
  if (touch) await page.touchscreen.tap(point.x, point.y);
  else await page.mouse.click(point.x, point.y);
  await ready(page);
  const start = await state(page);
  if (start.selected !== FOCUS) problems.push(`tap on ${FOCUS} selected ${start.selected}`);
  const press = async (selector: string) => {
    log(`press ${selector}`);
    const button = page.locator(selector);
    if (touch) await button.tap({ timeout: 180_000 });
    else await button.click({ timeout: 180_000 });
    await ready(page);
    return state(page);
  };
  for (let round = 1; round <= 2; round++) {
    log(`round ${round}`);
    const object = await press(".card__closer");
    if (object.nav.shot !== `object:${FOCUS}` || object.selected !== FOCUS) problems.push(`round ${round}: closer → ${object.nav.shot} / ${object.selected}`);
    const near = await state(page);
    await drag(page, touch, at.x, at.y + 40, -80, 0); // turn the object view a little
    await ready(page);
    const turned = await state(page);
    if (poseDiff(turned.pose, near.pose) < 1e-3) problems.push(`round ${round}: drag did not turn the object view`);
    let detail = null;
    let objectGap = 0;
    if (DETAILED) {
      detail = await press(".card__closer");
      if (detail.nav.shot !== `detail:${FOCUS}`) problems.push(`round ${round}: closer → ${detail.nav.shot}`);
      if (await page.locator(".card__closer").count()) problems.push(`round ${round}: a closer view is offered beyond the detail`);
      const backToObject = await press(".card__back");
      objectGap = poseDiff(backToObject.pose, turned.pose);
      if (backToObject.nav.shot !== `object:${FOCUS}` || objectGap > EPSILON) problems.push(`round ${round}: back to object view off by ${objectGap.toExponential(2)}`);
    } else if (await page.locator(".card__closer").count()) problems.push(`round ${round}: a closer view is offered without a detail`);
    // The second step back by the keyboard on a computer.
    let end;
    if (touch) end = await press(".card__back");
    else {
      await page.keyboard.press("Escape");
      await ready(page);
      end = await state(page);
    }
    const gap = poseDiff(end.pose, start.pose);
    checks[`round-${round}`] = { object: object.nav, detail: detail?.nav ?? null, objectGap, globalGap: gap, end: end.nav, selected: end.selected };
    if (end.nav.depth !== 1 || end.selected !== FOCUS || gap > EPSILON) problems.push(`round ${round}: back to global off by ${gap.toExponential(2)}, depth ${end.nav.depth}, selected ${end.selected}`);
  }
  return { checks, problems };
}

/** Global (FOCUS selected) → object view → detail view, frame by frame at 30 frames per
 * second of the transition's own clock: PNG frames and a contact sheet; a WebM with `--video`. */
/** Plays the tour from a bare URL, as on arrival: the first step is about the system with
 * nothing selected and no card; steps follow in order at their reading pace; a tap on the
 * scene hands over (roadmap §7). */
async function checkTour(page: Page, touch: boolean): Promise<{ checks: Record<string, unknown>; problems: string[] }> {
  const problems: string[] = [];
  await page.goto(appUrl(), { timeout: 120_000 });
  await page.waitForFunction(() => window.__xs?.tour != null, null, { timeout: 120_000 });
  const state = () => page.evaluate(() => ({ tour: window.__xs!.tour, selected: window.__xs!.selected, card: !!document.querySelector(".card"), text: document.querySelector(".tour__text")?.textContent ?? null, t: performance.now() }));
  const first = await state();
  if (first.tour?.index !== 0) problems.push(`tour starts at step ${first.tour?.index}`);
  if (first.selected !== null || first.card) problems.push(`an object is put forward on the first step (selected ${first.selected}, card ${first.card})`);
  if (!first.text) problems.push("no subtitle on the first step");
  const timeline = await page.evaluate(() => window.__xs!.timeline());
  // Follow the tour through its object steps: order and timing (±1.5 s, the page being slow).
  const seen: { index: number; at: number; selected: string | null }[] = [{ index: 0, at: 0, selected: first.selected }];
  const until = first.t + (timeline[timeline.length - 1]!.start + 30) * 1000;
  for (let now = first.t; now < until && seen.length < timeline.length; ) {
    await page.waitForTimeout(150);
    const s = await state();
    now = s.t;
    if (s.tour && s.tour.index !== seen[seen.length - 1]!.index) seen.push({ index: s.tour.index, at: (s.t - first.t) / 1000, selected: s.selected });
  }
  // Each step lasts its reading time (±1 s, sampling and a slow page); the first one counts
  // from the scene's loading, before which its clock does not run.
  seen.forEach((s, k) => {
    if (s.index !== k) problems.push(`step ${k} expected, ${s.index} played`);
    const next = seen[k + 1];
    if (!next || k === 0) return;
    const lasted = next.at - s.at;
    if (Math.abs(lasted - timeline[k]!.duration) > 1) problems.push(`step ${k} lasted ${lasted.toFixed(1)} s, expected ${timeline[k]!.duration.toFixed(1)} s`);
  });
  if (seen.length < timeline.length) problems.push(`only ${seen.length} of ${timeline.length} steps played`);
  // Hand over: a tap on the scene stops the tour where it is.
  const box = page.viewportSize()!;
  if (touch) await page.touchscreen.tap(box.width / 2, 40);
  else await page.mouse.click(box.width / 2, 40);
  await page.waitForTimeout(300);
  const after = await state();
  if (after.tour !== null) problems.push("tour still playing after a tap on the scene");
  return { checks: { first, steps: seen, timeline, handedOver: after.tour === null }, problems };
}

async function recordTransition(page: Page, dir: string) {
  mkdirSync(dir, { recursive: true });
  await page.goto(appUrl(`${T}&step&select=${FOCUS}`), { timeout: 120_000 });
  const settle = async () => {
    for (let i = 0; i < 200 && !(await page.evaluate(() => window.__xs?.ready === true)); i++) await advance(page);
  };
  const advance = (page: Page) => page.evaluate(() => new Promise<void>((r) => (window.__xs?.advance(), requestAnimationFrame(() => requestAnimationFrame(() => r())))));
  await page.waitForFunction(() => !!window.__xs?.pose(), null, { timeout: 120_000 });
  await settle();
  let n = 0;
  const shoot = () => page.screenshot({ path: join(dir, `frame-${String(n++).padStart(3, "0")}.png`), timeout: 180_000 });
  await shoot();
  for (const selector of DETAILED ? [".card__closer", ".card__closer", ".card__back", ".card__back"] : [".card__closer", ".card__back"]) {
    console.log(`${new Date().toISOString().slice(11, 19)}   transition ${selector}`);
    await page.locator(selector).click({ timeout: 180_000 });
    for (let i = 0; i < 60 && !(await page.evaluate(() => window.__xs?.ready === true)); i++) {
      await advance(page);
      await shoot();
    }
  }
  const frames = join(dir, "frame-%03d.png");
  if (process.argv.includes("--video")) {
    execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-framerate", "30", "-i", frames, "-vf", "scale=1366:-2", "-c:v", "libvpx-vp9", "-b:v", "2M", join(dir, "transition.webm")]);
  }
  // One frame in three, small, on a grid (ffmpeg: ImageMagick runs out of cache on full frames).
  const rows = Math.ceil(Math.ceil(n / 3) / 6);
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-i", frames, "-vf", `select=not(mod(n\\,3)),scale=456:-2,tile=6x${rows}:padding=4:color=white`, "-frames:v", "1", "-update", "1", join(dir, "contact-sheet.png")]);
  return n;
}

const results: Record<string, unknown> = {};
const log = (what: string) => console.log(`${new Date().toISOString().slice(11, 19)}   ${what}`);
let failed = false;
/** Keeps a result, reports its problems at once and saves the results so far: a run cut
 * short (time limit) still leaves what it checked. */
const keep = (key: string, result: Record<string, unknown> & { errors: string[]; problems?: string[] }) => {
  results[key] = result;
  const bad = [...(result.problems ?? []), ...result.errors];
  if (bad.length) failed = true;
  for (const b of bad) log(`PROBLEM ${key}: ${b}`);
  writeFileSync(join(out, "captures.json"), JSON.stringify(results, null, 2) + "\n");
};
try {
  for (const format of formats) {
    const page = await browser.newPage({ viewport: FORMATS[format], deviceScaleFactor: Number(arg("dpr") ?? 1), hasTouch: format !== "desktop" });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
    page.on("response", (r) => r.status() >= 400 && errors.push(`HTTP ${r.status()} ${r.url()}`));
    for (const [view, query] of Object.entries(VIEWS)) {
      if (only && !only.includes(view)) continue;
      await page.goto(appUrl(query), { timeout: 120_000 });
      await page.waitForFunction(() => window.__xs?.ready === true, null, { timeout: 120_000 });
      const file = `${view}-${format}.png`;
      console.log(`${new Date().toISOString().slice(11, 19)} ${view}/${format}`);
      await page.screenshot({ path: join(out, file), timeout: 180_000 });
      const overlap = view.startsWith("card-") ? await page.evaluate(() => window.__xs!.overlap()) : undefined;
      keep(`${view}/${format}`, { file, render: await page.evaluate(() => window.__xs!.renderInfo()), overlap, errors: [...errors] });
      errors.length = 0;
    }
    if (!only || only.includes("selection")) {
      const { checks, problems } = await checkSelection(page, format !== "desktop");
      keep(`selection/${format}`, { checks, problems, errors: [...errors] });
      errors.length = 0;
    }
    if (!only || only.includes("transitions")) {
      const { checks, problems } = await checkTransitions(page, format !== "desktop");
      keep(`transitions/${format}`, { checks, problems, errors: [...errors] });
      errors.length = 0;
    }
    if (!only || only.includes("tour")) {
      const { checks, problems } = await checkTour(page, format !== "desktop");
      keep(`tour/${format}`, { checks, problems, errors: [...errors] });
      errors.length = 0;
    }
    if ((!only || only.includes("transition-video")) && format === formats[0]) {
      try {
        const frames = await recordTransition(page, join(out, "transition"));
        keep(`transition-video/${format}`, { frames, errors: [...errors] });
      } catch (e) {
        keep(`transition-video/${format}`, { problems: [String(e).slice(0, 500)], errors: [...errors] });
      }
      errors.length = 0;
    }
    await page.close();
  }
} finally {
  await browser.close();
  await server.close();
}
writeFileSync(join(out, "captures.json"), JSON.stringify(results, null, 2) + "\n");
console.log(`${failed ? "RESULT: failure — page errors or selection problems (see captures.json)" : "RESULT: success"} — ${Object.keys(results).length} captures → ${out}`);
process.exit(failed ? 1 : 0);
