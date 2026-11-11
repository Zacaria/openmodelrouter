import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import {
  DeciderPanel,
  Onboarding,
  deciderTarget,
  initialStep,
  needsOnboarding,
  readOnboarding,
  writeOnboarding,
} from "./onboarding";
import App from "../App";
import type { Config, Snapshot } from "../types";
const config: Config = {
  connections: [],
  reevaluate: true,
  context_tokens: 1024,
  total_tokens: 2048,
  max_messages: null,
  expected_output: 256,
  switch_margin: 0.1,
  baseline: null,
  decider: null,
};
const state = {
  config,
  managed: {
    status: "absent",
    active: false,
    running: false,
    downloaded_bytes: 0,
  },
  secret_states: [],
} as unknown as Snapshot;
const props = {
  config,
  state,
  busy: false,
  change: () => {},
  grant: () => {},
  persist: async () => true,
  act: async <T,>(action: () => Promise<T>) => action(),
  close: () => {},
};
describe("resumable onboarding", () => {
  it("persists only progress and distinguishes an unfinished wizard from an old valid config", () => {
    const values = new Map<string, string>();
    vi.stubGlobal("localStorage", {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
    });
    try {
      expect(readOnboarding()).toBeNull();
      writeOnboarding(true, 1);
      expect(readOnboarding()).toEqual({ open: true, step: 1 });
      writeOnboarding(false);
      expect(readOnboarding()).toEqual({ open: false, step: 1 });
      expect([...values.values()].join("")).not.toContain("connections");
    } finally {
      vi.unstubAllGlobals();
    }
  });
  it("does not tell a supported native runtime that macOS is disabled", () => {
    const html = renderToStaticMarkup(
      <DeciderPanel
        {...props}
        config={{
          ...config,
          decider: { mode: "managed", model: "s1d1-dac13b5", consent: false },
        }}
        state={{
          ...state,
          managed: {
            checkpoint: "s1d1-dac13b5",
            status: "absent",
            error: null,
            active: false,
            running: false,
            downloaded_bytes: 0,
            supported: true,
          },
        }}
      />,
    );
    expect(html).not.toContain("macOS et Windows ne sont pas activés");
    expect(html).not.toContain("indisponible sur cet appareil");
  });
  it("starts without configuration and never calls a provider during render", () => {
    const html = renderToStaticMarkup(<Onboarding {...props} />);
    expect(html).toContain("Continuer en accès direct");
    expect(html).toContain("1. Modèles répondants");
    expect(html).toContain("4. Test explicite");
    expect(html).toContain("Responses est le contrat de génération");
    expect(html).toContain('type="password"');
    expect(html).toContain("HTTP ne chiffre ni les requêtes ni la clé API");
    expect(initialStep(config)).toBe(0);
  });
  it("keeps valid direct configurations out of forced onboarding", () => {
    expect(
      needsOnboarding({
        ...config,
        connections: [
          {
            id: "c",
            name: "local",
            url: "http://localhost:1/v1",
            models: [
              {
                id: "m",
                upstream: "actual",
                protocols: ["responses"],
                enabled: true,
                tools: false,
                quality: 3,
                input_price: null,
                output_price: null,
                effort: null,
              },
            ],
          },
        ],
      }),
    ).toBe(false);
    expect(renderToStaticMarkup(<App />)).toContain(
      "Reprendre la configuration",
    );
  });
  it("keeps direct access unconsented and requires a separate explicit test", () => {
    const html = renderToStaticMarkup(<DeciderPanel {...props} />);
    for (const text of [
      "Aucun · accès direct",
      "Tester le décideur · coût API possible",
      "Enregistrer ne lance aucun test",
    ])
      expect(html).toContain(text);
  });
  it("binds managed consent to checkpoint and external consent to mode/protocol", () => {
    expect(
      deciderTarget({
        ...config,
        decider: { mode: "managed", model: "s1d1-dac13b5", consent: true },
      }),
    ).toEqual({ mode: "managed", model: "s1d1-dac13b5" });
    const c = {
      id: "c",
      name: "local",
      url: "http://localhost:1/v1",
      models: [],
    };
    expect(
      deciderTarget({
        ...config,
        connections: [c],
        decider: {
          mode: "byok",
          protocol: "jev",
          connection: "c",
          model: "jev-1.13.0",
          consent: true,
        },
      }),
    ).toEqual({
      connection: "c",
      url: c.url,
      model: "jev-1.13.0",
      mode: "byok",
      protocol: "jev",
    });
  });
  it("offers explicit Ollama SystemOne without disguising it as chat", () => {
    const html = renderToStaticMarkup(
      <DeciderPanel
        {...props}
        config={{
          ...config,
          decider: {
            mode: "server",
            protocol: "ollama-systemone",
            model: "d3:4b",
            consent: false,
          },
        }}
      />,
    );
    expect(html).toContain("Ollama · SystemOne");
    expect(html).toContain("/systemone");
    expect(html).toContain("d3:4b");
  });
  it("discloses managed input limits, integrity and explicit lifecycle", () => {
    const html = renderToStaticMarkup(
      <DeciderPanel
        {...props}
        config={{
          ...config,
          decider: { mode: "managed", model: "s1d1-dac13b5", consent: false },
        }}
      />,
    );
    for (const text of [
      "1024 tokens",
      "SHA-256",
      "Télécharger et vérifier",
      "Démarrer le modèle géré",
      "Arrêter le modèle géré",
      "Aucun démarrage automatique",
    ])
      expect(html).toContain(text);
  });
});
