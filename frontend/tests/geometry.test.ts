import { describe, expect, it } from "vitest";
import {
  displayToNormalized,
  fitContain,
  normalizedToDisplay,
} from "@/lib/geometry";

describe("letterboxed frame mapping", () => {
  const fit = fitContain(200, 100, 100, 100);

  it("puts the unused width in side margins", () => {
    expect(fit.offsetX).toBe(50);
    expect(fit.offsetY).toBe(0);
    expect(fit.drawnWidth).toBe(100);
    expect(fit.drawnHeight).toBe(100);
  });

  it("rejects a click in the margin and maps a click on the frame", () => {
    expect(displayToNormalized({ x: 10, y: 50 }, fit)).toBeNull();
    expect(displayToNormalized({ x: 150, y: 50 }, fit)).toEqual({
      x: 1,
      y: 0.5,
    });
  });

  it("round-trips a normalized point through the display box", () => {
    const display = normalizedToDisplay({ x: 0.25, y: 0.5 }, fit);
    expect(display).toEqual({ x: 75, y: 50 });
    expect(displayToNormalized(display, fit)).toEqual({ x: 0.25, y: 0.5 });
  });
});
