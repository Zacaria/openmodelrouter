import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const css = readFileSync(new URL("./styles.css", import.meta.url), "utf8");
function tokens(selector: string) {
  const body = css.slice(css.indexOf(selector)).split("}")[0];
  return Object.fromEntries(
    [...body.matchAll(/--([\w-]+):\s*(#[0-9a-f]{6});/g)].map((m) => [
      m[1],
      m[2],
    ]),
  );
}
function luminance(hex: string) {
  return [1, 3, 5]
    .map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4))
    .reduce((s, c, i) => s + c * [0.2126, 0.7152, 0.0722][i], 0);
}
function contrast(a: string, b: string) {
  const x = luminance(a),
    y = luminance(b);
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
}

describe("desktop art direction", () => {
  it("uses the generated paper and forest direction without decorative topology grids", () => {
    const light = tokens(":root {");
    expect(light.bg).toBe("#f7f6f2");
    expect(light.accent).toBe("#245642");
    expect(css).toContain("--font-editorial:");
    const topology = css.split(".topology-canvas {")[1].split("}")[0];
    expect(topology).not.toContain("linear-gradient");
  });
  for (const [name, selector] of [
    ["light", ":root {"],
    ["dark", ':root[data-theme="dark"] {'],
  ]) {
    it(`${name} text and controls meet their contrast thresholds`, () => {
      const t = { ...tokens(":root {"), ...tokens(selector) };
      for (const bg of ["bg", "sidebar", "panel", "surface"]) {
        for (const fg of ["text", "muted"]) {
          expect(contrast(t[fg], t[bg]), `${fg}/${bg}`).toBeGreaterThanOrEqual(
            4.5,
          );
        }
      }
      for (const bg of ["bg", "panel"])
        expect(contrast(t["control-line"], t[bg])).toBeGreaterThanOrEqual(3);
      expect(contrast(t["accent-text"], t.accent)).toBeGreaterThanOrEqual(4.5);
      expect(contrast(t.selected, t["selected-bg"])).toBeGreaterThanOrEqual(
        4.5,
      );
    });
  }
  it("keeps system dark and explicit dark tokens identical", () => {
    expect(tokens(':root:not([data-theme="light"]) {')).toEqual(
      tokens(':root[data-theme="dark"] {'),
    );
    expect(css).toContain("prefers-reduced-motion: reduce");
    expect(css).not.toContain("https://");
  });
});
