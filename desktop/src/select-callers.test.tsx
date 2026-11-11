import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ConnectionCard } from "./App";
import type { Snapshot, Connection } from "./types";

const connection: Connection = {
  id: "connection",
  name: "Synthetic",
  url: "http://127.0.0.1:1/v1",
  transport: "pi-ai",
  models: [
    {
      id: "model",
      upstream: "vendor/model",
      protocols: ["chat"],
      enabled: true,
      tools: false,
      quality: 2,
      effort: null,
      input_price: null,
      output_price: null,
    },
  ],
};
const state = {
  connection_states: {},
  model_states: {},
  secret_states: [],
} as unknown as Snapshot;

describe("shared Select callers", () => {
  it("leaves no native select popup in the app, setup or native strategies", () => {
    for (const file of [
      "App.tsx",
      "provider-setup.tsx",
      "components/onboarding.tsx",
      "components/native-strategies.tsx",
    ]) {
      expect(
        /<select\b/.test(readFileSync(new URL(file, import.meta.url), "utf8")),
        file,
      ).toBe(false);
    }
  });
  it("preserves selected transport and keeps model settings collapsed until opened", () => {
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
    expect(html.match(/role="combobox"/g)).toHaveLength(1);
    expect(html).toContain("pi-ai · adaptateurs fournisseurs");
    expect(html).toContain("vendor/model");
    expect(html).toContain("Réglages</span></summary>");
    expect(html).not.toContain("Effort transmis");
    expect(
      (html.match(/<select\b[^>]*>/g) ?? []).every((tag) =>
        tag.includes('aria-hidden="true"'),
      ),
    ).toBe(true);
  });
});
