import { describe, expect, it } from "vitest";
import { formatLength, scaleBar, scaleUnit } from "../engine/src/ui/scale";

describe("scale bar", () => {
  it("picks the largest round length that fits", () => {
    expect(scaleBar(0.01, 120)).toMatchObject({ metres: 1, label: "1 m" }); // 1.2 m available
    expect(scaleBar(0.04, 120)).toMatchObject({ metres: 2, label: "2 m" }); // 4.8 m
    expect(scaleBar(0.0005, 120)).toMatchObject({ metres: 0.05, label: "5 cm" }); // 6 cm
    expect(scaleBar(0.00001, 120)).toMatchObject({ metres: 0.001, label: "1 mm" }); // 1.2 mm
    expect(scaleBar(2, 120)).toMatchObject({ metres: 200, label: "200 m" });
  });

  it("never draws wider than allowed, nor under 40 % of it", () => {
    for (let mpp = 1e-7; mpp < 1e4; mpp *= 1.37) {
      const bar = scaleBar(mpp, 120);
      expect(bar.pixels).toBeLessThanOrEqual(120 + 1e-6);
      expect(bar.pixels).toBeGreaterThanOrEqual(120 * 0.4 - 1e-6);
    }
  });

  it("names lengths and zoom levels in the usual unit", () => {
    expect(formatLength(0.025)).toBe("2,5 cm");
    expect(formatLength(5000)).toBe("5 km");
    expect(scaleUnit(1)).toBe("m");
    expect(scaleUnit(0.01)).toBe("cm");
    expect(scaleUnit(0.001)).toBe("mm");
  });
});
