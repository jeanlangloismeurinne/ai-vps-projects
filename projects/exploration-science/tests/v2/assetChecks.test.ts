import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
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
    m.assets.probe!.main = true;
    const errors = await checkAssets(m, fromDisk, palette, budgets);
    expect(errors.some((e) => e.includes("probe.envelope: 3 named parts"))).toBe(true);
  });

  it("refuse a mesh without baked AO", async () => {
    const io = await makeIO();
    const doc = await io.readBinary(fromDisk("probe.envelope.glb")!);
    for (const mesh of doc.getRoot().listMeshes()) for (const prim of mesh.listPrimitives()) prim.setAttribute("COLOR_0", null);
    const stripped = await io.writeBinary(doc);
    const m = load();
    m.assets.probe!.representations.envelope!.sha256 = sha256(stripped);
    const read = (file: string) => (file === "probe.envelope.glb" ? stripped : fromDisk(file));
    const errors = await checkAssets(m, read, palette, budgets);
    expect(errors.some((e) => e.includes("no baked AO"))).toBe(true);
  });

  it("refuse an over-budget scene", async () => {
    const errors = await checkAssets(load(), fromDisk, palette, { ...budgets, totalBytesMax: 100 });
    expect(errors.some((e) => e.includes("budget 100"))).toBe(true);
  });

  const python = join(root, "art/.venv/bin/python");
  it.skipIf(!existsSync(python))("Blender build refuses a floating part", () => {
    let stderr = "";
    try {
      execFileSync(python, [join(root, "art/build.py"), "--scene", join(root, "art/fixtures/floating.json")], { stdio: "pipe" });
    } catch (e) {
      stderr = String((e as { stderr: Buffer }).stderr);
    }
    expect(stderr).toContain("floating part: floating.ghost");
  });
});
