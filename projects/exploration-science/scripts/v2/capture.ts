// npm run capture [-- --out DIR] [-- --only global,...] [-- --formats ipad-landscape,...]
// Starts the Vite dev server, opens v2.html in headless Chromium (software WebGL:
// valid for composition and materials, NOT for frame rate) and saves one PNG per
// view and screen format, plus render stats (draw calls, triangles) in captures.json.
import { mkdirSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { chromium } from "@playwright/test";
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
export const VIEWS: Record<string, string> = {
  global: "",
  ...Object.fromEntries(MAIN.map((id) => [`object-${id}`, `shot=object:${id}`])),
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
      await page.screenshot({ path: join(out, file), timeout: 180_000 });
      results[`${view}/${format}`] = { file, render: await page.evaluate(() => window.__xs!.renderInfo()), errors: [...errors] };
      if (errors.length) failed = true;
      errors.length = 0;
    }
    await page.close();
  }
} finally {
  await browser.close();
  await server.close();
}
writeFileSync(join(out, "captures.json"), JSON.stringify(results, null, 2) + "\n");
console.log(`${failed ? "RESULT: failure — page errors (see captures.json)" : "RESULT: success"} — ${Object.keys(results).length} captures → ${out}`);
process.exit(failed ? 1 : 0);
