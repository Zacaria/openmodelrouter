import type { Config, Model } from "./types";

export type BenchmarkModel = {
  slug: string;
  name: string;
  score: number | null;
  quality: number;
};
export type Benchmarks = {
  version: string | null;
  models: BenchmarkModel[];
  fetched_at: number | null;
  retry_at: number;
  configured: boolean;
  error: string | null;
};
export const benchmarkSecret = "benchmark-artificial-analysis";

export function modelListKey(config: Config) {
  return JSON.stringify(
    config.connections
      .flatMap((c) => c.models.map((m) => [c.id, m.id, m.upstream, m.enabled]))
      .sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b))),
  );
}
export function benchmarkMatch(model: Model, data?: Benchmarks) {
  const reference = model.benchmark_model || model.upstream;
  return data?.models.find((record) => record.slug === reference);
}
export function chooseQuality(
  model: Model,
  value: string,
  record?: BenchmarkModel,
): Model {
  if (value === "benchmark")
    return {
      ...model,
      quality_mode: "benchmark",
      quality: record?.quality ?? 0,
    };
  const quality = Number(value);
  if (![1, 2, 3].includes(quality)) throw Error("invalid_config");
  return { ...model, quality_mode: "manual", quality };
}
export function applyBenchmarks(config: Config, data: Benchmarks): Config {
  const records = new Map(data.models.map((r) => [r.slug, r]));
  let changed = false;
  const connections = config.connections.map((c) => ({
    ...c,
    models: c.models.map((m) => {
      if (m.quality_mode !== "benchmark") return m;
      const quality =
        records.get(m.benchmark_model || m.upstream)?.quality ?? 0;
      if (m.quality === quality) return m;
      changed = true;
      return { ...m, quality };
    }),
  }));
  return changed ? { ...config, connections } : config;
}
