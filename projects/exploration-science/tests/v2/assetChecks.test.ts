import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { checkAssets, makeIO, sha256, type Budgets, type Manifest } from "../../scripts/v2/assetChecks";

const root = resolve(import.meta.dirname, "../..");
const models = join(root, "public/v2/models");
const palette = (() => {
  const p = JSON.parse(readFileSync(join(root, "art/palette.json"), "utf8"));
  return new Set([...Object.keys(p.neutrals), ...Object.keys(p.accents), ...Object.keys(p.special)]);
})();
const budgets: Budgets = JSON.parse(readFileSync(join(root, "art/budgets.json"), "utf8"));
const load = (): Manifest => JSON.parse(readFileSync(join(models, "manifest.json"), "utf8"));
const fromDisk = (file: string) => (existsSync(join(models, file)) ? new Uint8Array(readFileSync(join(models, file))) : null);

describe("v2 asset checks", () => {
  it("accept the committed assets", async () => {
    expect(await checkAssets(load(), fromDisk, palette, budgets)).toEqual([]);
  });

  it("refuse a GLB that differs from its manifest entry", async () => {
    const read = (file: string) => {
      const bytes = fromDisk(file)!.slice();
      bytes[bytes.length - 1]! ^= 0xff;
      return bytes;
    };
    const errors = await checkAssets(load(), read, palette, budgets);
    expect(errors.some((e) => e.includes("differs from the manifest"))).toBe(true);
  });

  it("refuse a material outside the palette", async () => {
    const errors = await checkAssets(load(), fromDisk, new Set(["ground"]), budgets);
    expect(errors.some((e) => e.includes('"white" is not a palette swatch'))).toBe(true);
  });

  it("refuse a main object made of too few parts (block-like)", async () => {
    const m = load();
    m.assets["pine-01"]!.main = true;
    const errors = await checkAssets(m, fromDisk, palette, budgets);
    expect(errors.some((e) => e.includes("pine-01.envelope: 2 named parts"))).toBe(true);
  });

  it("refuse a mesh without baked AO", async () => {
    const io = await makeIO();
    const doc = await io.readBinary(fromDisk("terminal.envelope.glb")!);
    for (const mesh of doc.getRoot().listMeshes()) for (const prim of mesh.listPrimitives()) prim.setAttribute("COLOR_0", null);
    const stripped = await io.writeBinary(doc);
    const m = load();
    m.assets.terminal!.representations.envelope!.sha256 = sha256(stripped);
    const read = (file: string) => (file === "terminal.envelope.glb" ? stripped : fromDisk(file));
    const errors = await checkAssets(m, read, palette, budgets);
    expect(errors.some((e) => e.includes("no baked AO"))).toBe(true);
  });

  it("refuse a declared anchor missing from the GLB", async () => {
    const m = load();
    m.assets.terminal!.representations.envelope!.anchors = ["beam", "side"];
    const errors = await checkAssets(m, fromDisk, palette, budgets);
    expect(errors).toEqual(["terminal.envelope: anchor node terminal#side missing from the GLB"]);
  });

  it("refuse an over-budget scene", async () => {
    const errors = await checkAssets(load(), fromDisk, palette, { ...budgets, totalBytesMax: 100 });
    expect(errors.some((e) => e.includes("budget 100"))).toBe(true);
  });

  const python = join(root, "art/.venv/bin/python");
  const buildErrors = (fixture: string) => {
    let stderr = "";
    const out = mkdtempSync(join(tmpdir(), "xs-fixture-"));
    try {
      execFileSync(python, [join(root, "art/build.py"), "--system", join(root, `art/fixtures/${fixture}.system.json`), "--out", out], { stdio: "pipe" });
    } catch (e) {
      stderr = String((e as { stderr: Buffer }).stderr);
    } finally {
      rmSync(out, { recursive: true, force: true });
    }
    return stderr;
  };

  it.skipIf(!existsSync(python))("Blender build refuses a floating part", () => {
    expect(buildErrors("floating")).toContain("floating part: floating.ghost");
  });

  it.skipIf(!existsSync(python))("Blender build refuses inward-facing normals", () => {
    expect(buildErrors("inverted")).toContain("inverted normals: inverted.lid");
  });
});
