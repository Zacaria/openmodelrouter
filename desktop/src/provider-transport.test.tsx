import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ConnectionCard } from "./App";
import type { Connection, Snapshot } from "./types";

const connection: Connection = {
  id: "synthetic",
  name: "Synthetic API",
  url: "http://127.0.0.1:8000/v1",
  models: [],
};
const state = {
  connection_states: {},
  model_states: {},
  secret_states: [],
} as unknown as Snapshot;
function render(transport?: "http" | "pi-ai", url = connection.url) {
  return renderToStaticMarkup(
    <ConnectionCard
      connection={{ ...connection, transport, url }}
      state={state}
      busy={false}
      change={() => {}}
      remove={() => {}}
      act={async (action) => action()}
    />,
  );
}

describe("provider transport", () => {
  it("warns for HTTP in both transports, but not HTTPS", () => {
    for (const transport of ["http", "pi-ai"] as const) {
      expect(render(transport, "HTTP://127.0.0.2:8000/v1")).toContain(
        "HTTP ne chiffre ni les requêtes ni la clé API",
      );
      expect(render(transport, "https://example.com/v1")).not.toContain(
        "HTTP ne chiffre ni les requêtes ni la clé API",
      );
    }
  });
  it("offers the real pi-ai adapter and names its API-key scope", () => {
    const html = render("pi-ai");
    expect(html).toContain('role="combobox"');
    expect(
      (html.match(/<select\b[^>]*>/g) ?? []).every((tag) =>
        tag.includes('aria-hidden="true"'),
      ),
    ).toBe(true);
    expect(html).toContain("pi-ai · adaptateurs fournisseurs");
    expect(html).toContain("Clé API ou serveur local sans clé");
    expect(html).toContain(
      "Les abonnements Codex et Nous Portal utilisent leurs connexions dédiées",
    );
  });
  it("allows provider actions while autosave is pending instead of requiring Apply", () => {
    const html = renderToStaticMarkup(
      <ConnectionCard
        connection={connection}
        state={state}
        busy={false}
        change={() => {}}
        remove={() => {}}
        act={async (action) => action()}
      />,
    );
    expect(html).not.toContain(
      "Enregistrez les réglages avant de gérer la clé ou tester",
    );
    expect(html).not.toMatch(/disabled=""[^>]*>Découvrir les modèles/);
  });
  it("does not hide a failed generation behind a collapsed Non testé label", () => {
    const html = renderToStaticMarkup(
      <ConnectionCard
        connection={{
          ...connection,
          models: [
            {
              id: "model",
              upstream: "exact-model",
              protocols: ["chat"],
              enabled: true,
              tools: false,
              quality: 1,
              input_price: null,
              output_price: null,
              effort: null,
            },
          ],
        }}
        state={{ ...state, model_states: { model: { generation: "failed" } } }}
        busy={false}
        change={() => {}}
        remove={() => {}}
        act={async (action) => action()}
      />,
    );
    expect(html).toContain("Génération échouée");
  });
  it("does not silently change an existing HTTP connection", () => {
    expect(render()).toContain("HTTP direct · format inchangé");
    expect(render()).not.toContain("pi-ai · adaptateurs fournisseurs");
  });
});
