// npm run capture [-- --out DIR] [-- --only global,...] [-- --formats ipad-landscape,...]
// Starts the Vite dev server, opens v2.html in headless Chromium (software WebGL:
// valid for composition and materials, NOT for frame rate) and saves one PNG per
// view and screen format, plus render stats (draw calls, triangles) in captures.json.
// Then, per format, clicks (or taps) each main object for real and checks its card:
// right object, right title, at most 10 % of any main object under it (roadmap §4).
import { mkdirSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { readFileSync } from "node:fs";
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

// View name → query string understood by the v2 app. Grows with the roadmap.
const MAIN = ["house", "terminal", "satellite", "ground-station"];
// `t` pins the phase of the animated flows, so that captures are comparable.
const T = "t=1.5";
export const VIEWS: Record<string, string> = {
  global: T,
  ...Object.fromEntries(MAIN.map((id) => [`card-${id}`, `select=${id}&${T}`])),
  ...Object.fromEntries(MAIN.map((id) => [`object-${id}`, `shot=object:${id}&${T}`])),
  ...Object.fromEntries(MAIN.map((id) => [`silhouette-${id}`, `shot=object:${id}&silhouette`])),
};

const stamp = new Date().toISOString().slice(0, 16).replace(/[:T]/g, "-");
const out = resolve(arg("out") ?? join(root, "captures/v2", stamp));
const only = arg("only")?.split(",");
const formats = (arg("formats")?.split(",") ?? Object.keys(FORMATS)) as (keyof typeof FORMATS)[];
mkdirSync(out, { recursive: true });

const server = await createServer({ root, logLevel: "error", server: { port: 5199, strictPort: true } });
await server.listen();
const browser = await chromium.launch({
  executablePath: process.env.XS_CHROMIUM ?? "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
});

const cards = JSON.parse(readFileSync(join(root, "content/v2/texts.fr.json"), "utf8")).cards as Record<string, { title: string }>;
const MAX_OVERLAP = 0.1;
const ready = (page: Page) => page.waitForFunction(() => window.__xs?.ready === true, null, { timeout: 120_000 });

/** Clicks each main object from the global view; returns the problems found. */
async function checkSelection(page: Page, touch: boolean): Promise<{ checks: Record<string, unknown>; problems: string[] }> {
  const checks: Record<string, unknown> = {};
  const problems: string[] = [];
  await page.goto(`http://localhost:5199/v2.html?${T}`);
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

const results: Record<string, unknown> = {};
let failed = false;
try {
  for (const format of formats) {
    const page = await browser.newPage({ viewport: FORMATS[format], deviceScaleFactor: 2, hasTouch: format !== "desktop" });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
    page.on("response", (r) => r.status() >= 400 && errors.push(`HTTP ${r.status()} ${r.url()}`));
    for (const [view, query] of Object.entries(VIEWS)) {
      if (only && !only.includes(view)) continue;
      await page.goto(`http://localhost:5199/v2.html${query ? `?${query}` : ""}`);
      await page.waitForFunction(() => window.__xs?.ready === true, null, { timeout: 120_000 });
      const file = `${view}-${format}.png`;
      console.log(`${new Date().toISOString().slice(11, 19)} ${view}/${format}`);
      await page.screenshot({ path: join(out, file), timeout: 180_000 });
      const overlap = view.startsWith("card-") ? await page.evaluate(() => window.__xs!.overlap()) : undefined;
      results[`${view}/${format}`] = { file, render: await page.evaluate(() => window.__xs!.renderInfo()), overlap, errors: [...errors] };
      if (errors.length) failed = true;
      errors.length = 0;
    }
    if (!only || only.includes("selection")) {
      const { checks, problems } = await checkSelection(page, format !== "desktop");
      results[`selection/${format}`] = { checks, problems, errors: [...errors] };
      if (problems.length || errors.length) failed = true;
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
