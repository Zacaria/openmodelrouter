export type Model = {
  id: string;
  upstream: string;
  protocols: string[];
  enabled: boolean;
  tools: boolean;
  quality: number;
  quality_mode?: "manual" | "benchmark";
  benchmark_model?: string;
  input_price: number | null;
  output_price: number | null;
  effort: string | null;
};
export type Connection = {
  id: string;
  name: string;
  url: string;
  transport?: "http" | "pi-ai";
  subscription?: "codex" | "nous";
  models: Model[];
};
export type Config = {
  connections: Connection[];
  reevaluate: boolean;
  context_tokens: number;
  total_tokens: number;
  max_messages: number | null;
  expected_output: number;
  switch_margin: number;
  baseline: string | null;
  decider: {
    connection?: string;
    model: string;
    consent: boolean;
    mode?: "byok" | "server" | "managed";
    protocol?: "chat-json" | "jev" | "imajev" | "ollama-systemone";
  } | null;
};
export type Usage = { [key: string]: number | Record<string, number> };
export type Receipt = {
  native?: NativeReceipt;
  request_id: string;
  timestamp: number;
  mode?: string;
  profile?: string | null;
  status: string;
  route?: string;
  connection?: string;
  model_requested?: string;
  model_observed?: string | null;
  elapsed_ms?: number;
  usage: Usage;
  decision_ms?: number;
  decision_usage?: { input_tokens?: number; output_tokens?: number };
  observed_input_tokens?: number | null;
  observed_output_tokens?: number | null;
  comparison?: {
    actual_repriced: number | null;
    reference_repriced: number | null;
    baseline_revision: number;
    baseline_id: string;
  } | null;
  error?: string;
  [key: string]: unknown;
};
export type NativeState = {
  availability: Record<string, string>;
  status: string;
  active: boolean;
  models: string[];
  model: string | null;
  reply: string;
  error: string | null;
  events: Record<string, number>;
  cancel_requested: boolean;
};
export type NativeReceipt = {
  action: string;
  event_types: string[];
  completed_children: number;
  thread_usage: Record<string, number>;
  last_call_usage: Record<string, number>;
  auxiliary_cost_usd: null;
  full_cost_usd: null;
  actual_billed_usd: null;
  permission_denials: number;
};
export type Snapshot = {
  managed?: {
    supported?: boolean;
    checkpoint: string;
    status: string;
    error: string | null;
    active: boolean;
    running: boolean;
    downloaded_bytes: number;
  };
  native: NativeState;
  receipt_storage: string;
  config: Config;
  config_file?: {
    path: string;
    status: "synced" | "changed" | "invalid" | "unavailable";
  };
  revision: number;
  history: { revision: number; config: Config }[];
  port: number;
  active: number;
  receipts: Receipt[];
  catalogue: { id: string }[];
  model_states: Record<
    string,
    {
      discovered?: boolean;
      generation?: string;
      verified_at?: number;
      generation_diagnostic?: { code: string };
    }
  >;
  connection_states: Record<string, { discovery: string }>;
  secret_states?: string[];
  summary: { direct_frequencies_30d: Record<string, number> };
};
