import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import {
  ModelCatalogue,
  catalogueGroups,
  selectModels,
  newModel,
} from "./model-catalogue";
import type { Connection } from "../types";
const catalogue = Array.from(
  { length: 604 },
  (_, i) => `${i % 2 ? "openai" : "anthropic"}/model-${i}`,
);
const connection: Connection = {
  id: "fixture",
  name: "OpenRouter",
  url: "https://openrouter.ai/api/v1",
  models: [],
};

describe("large discovered catalogue", () => {
  it("renders 604 accessible choices, counts and explicit filtered bulk scope in a scroll region", () => {
    const html = renderToStaticMarkup(
      <ModelCatalogue
        connection={connection}
        catalogue={catalogue}
        change={() => {}}
      />,
    );
    expect((html.match(/role="checkbox"/g) ?? []).length).toBe(604);
    expect(html).toContain("0 / 604 sélectionnés");
    expect(html).toContain("604 résultats de recherche");
    expect(html).toContain("actions sur ces 604 modèles");
    expect(html).toContain("Rechercher un modèle");
    expect(html).toContain("Tout sélectionner");
    expect(html).toContain("Effacer");
    expect(html).toContain('class="catalogue-scroll"');
  });
  it("groups OpenRouter by prefix, filters case insensitively and keeps other providers together", () => {
    expect(
      catalogueGroups(connection, catalogue, "OPENAI/model-1").map(
        (g) => g.name,
      ),
    ).toEqual(["openai"]);
    expect(catalogueGroups(connection, catalogue, "missing")).toEqual([]);
    expect(
      catalogueGroups(
        { ...connection, name: "Local", url: "http://localhost:11434/v1" },
        catalogue,
        "",
      ),
    ).toHaveLength(1);
  });
  it("preserves hidden selections, manual entries, existing IDs/settings, and adds enabled but unverified models", () => {
    const existing = {
      ...newModel(catalogue[0]),
      enabled: false,
      tools: true,
      quality: 3,
    };
    const manual = newModel("manual/outside");
    const selected = selectModels(
      [existing, manual],
      catalogue.slice(0, 20),
      true,
    );
    expect(selected).toHaveLength(21);
    expect(selected[0]).toBe(existing);
    expect(selected[1]).toBe(manual);
    expect(selected[2]).toMatchObject({
      enabled: true,
      tools: false,
      protocols: ["chat"],
      input_price: null,
    });
    expect(selected[2]).not.toHaveProperty("verified");
    const cleared = selectModels(selected, catalogue.slice(1, 20), false);
    expect(cleared).toEqual([existing, manual]);
    expect(selectModels(selected, [], false)).toEqual(selected);
    expect(newModel().enabled).toBe(true);
  });
});
