import { describe, expect, it } from "vitest";
import { usageTotals, comparisonTotals, routeStats } from "./metrics";
import type { Receipt } from "./types";

const receipt = (extra: Partial<Receipt> = {}): Receipt => ({
  request_id: "synthetic",
  timestamp: 100,
  status: "completed",
  mode: "automatic",
  profile: "economy",
  route: "route-a",
  connection: "conn-a",
  model_requested: "synthetic",
  model_observed: null,
  elapsed_ms: 20,
  usage: {},
  ...extra,
});

describe("observed usage, never fabricated savings", () => {
  it("keeps overlapping cache/reasoning categories separate and unknowns visible", () => {
    const result = usageTotals([
      receipt({
        observed_input_tokens: 100,
        observed_output_tokens: 20,
        usage: {
          prompt_tokens_details: { cached_tokens: 40 },
          completion_tokens_details: { reasoning_tokens: 10 },
        },
        decision_usage: { input_tokens: 5, output_tokens: 2 },
      }),
      receipt(),
    ]);
    expect(result.input).toBe(100);
    expect(result.output).toBe(20);
    expect(result.cache).toBe(40);
    expect(result.reasoning).toBe(10);
    expect(result.unknown).toBe(1);
    expect(result.decision).toBe(7);
    expect(usageTotals([receipt()]).input).toBeNull();
  });
  it("shows a negative repricing difference and never applies it to direct routing", () => {
    const rows = [
      receipt({
        comparison: {
          actual_repriced: 0.02,
          reference_repriced: 0.01,
          baseline_revision: 1,
          baseline_id: "ref",
        },
      }),
      receipt({
        mode: "direct",
        comparison: {
          actual_repriced: 0.1,
          reference_repriced: 0.5,
          baseline_revision: 1,
          baseline_id: "ref",
        },
      }),
    ];
    expect(comparisonTotals(rows).difference).toBeCloseTo(-0.01);
    expect(comparisonTotals([receipt()]).difference).toBeNull();
    expect(routeStats(rows)[0].confirmed).toBe("Non confirmé");
  });
});
