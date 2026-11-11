import type { Receipt } from "./types";

function sumKnown(values: (number | null | undefined)[]) {
  const known = values.filter(
    (value): value is number => typeof value === "number",
  );
  return known.length ? known.reduce((a, b) => a + b, 0) : null;
}
function detail(row: Receipt, names: string[], field: string) {
  for (const name of names) {
    const block = row.usage[name];
    if (block && typeof block === "object" && typeof block[field] === "number")
      return block[field];
  }
  return null;
}
export function usageTotals(rows: Receipt[]) {
  return {
    input: sumKnown(rows.map((r) => r.observed_input_tokens)),
    output: sumKnown(rows.map((r) => r.observed_output_tokens)),
    cache: sumKnown(
      rows.map(
        (r) =>
          detail(
            r,
            ["input_tokens_details", "prompt_tokens_details"],
            "cached_tokens",
          ) ??
          (typeof r.usage.cache_read_input_tokens === "number"
            ? r.usage.cache_read_input_tokens
            : null),
      ),
    ),
    reasoning: sumKnown(
      rows.map((r) =>
        detail(
          r,
          ["output_tokens_details", "completion_tokens_details"],
          "reasoning_tokens",
        ),
      ),
    ),
    decision: sumKnown(
      rows.flatMap((r) => [
        r.decision_usage?.input_tokens,
        r.decision_usage?.output_tokens,
      ]),
    ),
    unknown: rows.filter(
      (r) =>
        r.observed_input_tokens == null || r.observed_output_tokens == null,
    ).length,
  };
}
export function comparisonTotals(rows: Receipt[]) {
  const measured = rows.filter(
    (r) =>
      r.mode === "automatic" &&
      r.comparison?.actual_repriced != null &&
      r.comparison.reference_repriced != null,
  );
  return {
    difference: measured.length
      ? measured.reduce(
          (total, r) =>
            total +
            r.comparison!.reference_repriced! -
            r.comparison!.actual_repriced!,
          0,
        )
      : null,
    measured: measured.length,
  };
}
export function routeStats(rows: Receipt[]) {
  const map = new Map<
    string,
    {
      key: string;
      model: string;
      confirmed: string;
      mode: string;
      calls: number;
      failures: number;
      duration: number;
      rows: Receipt[];
    }
  >();
  for (const row of rows) {
    const key = `${row.connection}/${row.route}/${row.mode}/${row.profile}`;
    const group = map.get(key) ?? {
      key,
      model: row.model_requested ?? "Non sélectionné",
      confirmed: "Non confirmé",
      mode: row.mode === "direct" ? "Direct" : (row.profile ?? "Automatique"),
      calls: 0,
      failures: 0,
      duration: 0,
      rows: [],
    };
    group.calls++;
    group.failures += row.status === "completed" ? 0 : 1;
    group.duration += row.elapsed_ms ?? 0;
    group.rows.push(row);
    group.confirmed = group.rows.every((r) => r.model_observed === group.model)
      ? group.model
      : "Non confirmé";
    map.set(key, group);
  }
  return [...map.values()].sort((a, b) => b.calls - a.calls);
}
export const number = (value: number | null | undefined) =>
  value == null
    ? "Non mesuré"
    : new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(
        value,
      );
export const money = (value: number | null) =>
  value == null
    ? "Non mesuré"
    : new Intl.NumberFormat("fr-FR", {
        style: "currency",
        currency: "USD",
        minimumFractionDigits: 4,
        maximumFractionDigits: 6,
      }).format(value);
