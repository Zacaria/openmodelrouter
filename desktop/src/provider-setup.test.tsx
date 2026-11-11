import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ProviderSetup, ConfigFilePanel } from "./provider-setup";
import { createProvider } from "./provider-presets";
import type { Snapshot } from "./types";

const state = {
  config_file: { path: "/isolated/OMR/providers.json", status: "changed" },
} as Snapshot;

describe("provider setup", () => {
  it("offers the four existing provider types without guessing models", () => {
    const html = renderToStaticMarkup(
      <ProviderSetup busy={false} add={() => {}} />,
    );
    expect(html).toContain('role="combobox"');
    expect(
      (html.match(/<select\b[^>]*>/g) ?? []).every((tag) =>
        tag.includes('aria-hidden="true"'),
      ),
    ).toBe(true);
    expect(html).toContain("Choisir un fournisseur");
    expect(html).not.toContain('value="synthetic');
  });
  it("creates only API connections, with usual endpoints and no invented capability", () => {
    for (const [type, url] of [
      ["ollama", "http://127.0.0.1:11434/v1"],
      ["litellm", "http://127.0.0.1:4000/v1"],
      ["openrouter", "https://openrouter.ai/api/v1"],
    ] as const) {
      const c = createProvider(type);
      expect(c.url).toBe(url);
      expect(c.transport).toBe("pi-ai");
      expect(c.models).toEqual([]);
      expect(c.id).toMatch(/^[0-9a-f-]{36}$/);
      expect(c).not.toHaveProperty("api_key");
    }
  });
  it("shows the real file path and refuses reload while a draft exists", () => {
    const html = renderToStaticMarkup(
      <ConfigFilePanel
        state={state}
        busy={false}
        dirty={true}
        load={() => {}}
      />,
    );
    expect(html).toContain("/isolated/OMR/providers.json");
    expect(html).toContain("Fichier modifié");
    expect(html).toMatch(/disabled=""[^>]*>Charger le fichier/);
    expect(html).toContain("Attendez l’enregistrement automatique");
  });
  it("names invalidity without claiming to have replaced the valid config", () => {
    const html = renderToStaticMarkup(
      <ConfigFilePanel
        state={{
          ...state,
          config_file: { ...state.config_file!, status: "invalid" },
        }}
        busy={false}
        dirty={false}
        load={() => {}}
      />,
    );
    expect(html).toContain("dernière configuration valide conservée");
    expect(html).not.toMatch(/disabled=""[^>]*>Charger le fichier/);
  });
});
