import type { Connection } from "./types";

export const providerPresets = {
  codex: {
    name: "Codex · abonnement ChatGPT",
    url: "https://chatgpt.com/backend-api/codex",
    subscription: "codex",
  },
  nous: {
    name: "Nous Portal · abonnement",
    url: "http://127.0.0.1:8645/v1",
    subscription: "nous",
    transport: "http",
  },
  jev: { name: "Jev · décideur", url: "https://api.typesafe.ai/v1" },
  ollama: { name: "Ollama", url: "http://127.0.0.1:11434/v1" },
  litellm: { name: "LiteLLM", url: "http://127.0.0.1:4000/v1" },
  openrouter: { name: "OpenRouter", url: "https://openrouter.ai/api/v1" },
} as const;
export type ApiProvider = keyof typeof providerPresets;

export function createProvider(type: ApiProvider): Connection {
  return {
    id: crypto.randomUUID(),
    transport: "pi-ai",
    ...providerPresets[type],
    models: [],
  };
}
