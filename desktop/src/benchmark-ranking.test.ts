import { describe, expect, it } from "vitest";
import {
  applyBenchmarks,
  benchmarkMatch,
  modelListKey,
  chooseQuality,
} from "./benchmark-ranking";
import { newModel } from "./components/model-catalogue";
import type { Config } from "./types";

const data = {
  version: "5",
  fetched_at: 100,
  retry_at: 0,
  configured: true,
  error: null,
  models: [{ slug: "exact-model", name: "Exact model", score: 45, quality: 3 }],
};
const config = {
  connections: [
    {
      id: "c",
      name: "Local",
      url: "http://localhost:1/v1",
      models: [newModel("exact-model"), newModel("unknown-quantized")],
    },
  ],
} as Config;

describe("external benchmark routing", () => {
  it("only matches exact identities or an explicit reference, never a guessed family", () => {
    expect(benchmarkMatch(newModel("exact-model"), data)?.score).toBe(45);
    expect(benchmarkMatch(newModel("exact-model:4b"), data)).toBeUndefined();
    expect(
      benchmarkMatch(
        { ...newModel("private-alias"), benchmark_model: "exact-model" },
        data,
      )?.quality,
    ).toBe(3);
  });
  it("applies fresh source tiers to automatic models, preserves overrides, and keeps unknowns unranked", () => {
    const ranked = applyBenchmarks(config, data);
    expect(ranked.connections[0].models.map((m) => m.quality)).toEqual([3, 0]);
    expect(applyBenchmarks(ranked, data)).toBe(ranked);
    const manual = structuredClone(ranked);
    manual.connections[0].models[0] = chooseQuality(
      manual.connections[0].models[0],
      "1",
    );
    expect(applyBenchmarks(manual, data)).toBe(manual);
    expect(
      chooseQuality(
        manual.connections[0].models[0],
        "benchmark",
        data.models[0],
      ).quality,
    ).toBe(3);
  });
  it("debounce keys change with membership/identity/enabled state, not manual ratings or list order", () => {
    const changed = structuredClone(config);
    changed.connections[0].models[0].quality = 2;
    expect(modelListKey(changed)).toBe(modelListKey(config));
    changed.connections[0].models.reverse();
    expect(modelListKey(changed)).toBe(modelListKey(config));
    changed.connections[0].models[0].enabled = false;
    expect(modelListKey(changed)).not.toBe(modelListKey(config));
    changed.connections[0].models.pop();
    expect(modelListKey(changed)).not.toBe(modelListKey(config));
  });
});
