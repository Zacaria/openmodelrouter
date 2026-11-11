import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { NativeStrategies } from "./native-strategies";
import type { NativeState } from "../types";

const state: NativeState = {
  availability: {
    codex: "unavailable",
    claude: "unavailable",
    omp: "unavailable",
    hermes: "unavailable",
  },
  status: "disconnected",
  active: false,
  models: [],
  model: null,
  reply: "",
  error: null,
  events: {},
  cancel_requested: false,
};
describe("native strategy controls", () => {
  it("does not advertise unsupported clients or expose unavailable actions", () => {
    const html = renderToStaticMarkup(
      <NativeStrategies state={state} run={async () => {}} />,
    );
    expect(html).toContain("Non disponible");
    expect(html).toContain("Codex 0.159.0");
    expect(html).toContain("aucune session existante");
    expect(html).not.toContain("Compacter le contexte");
  });
  it("retains cancellation while a native turn is active", () => {
    const html = renderToStaticMarkup(
      <NativeStrategies
        state={{
          ...state,
          status: "running",
          active: true,
          models: ["gpt-6.1-sol"],
          model: "gpt-6.1-sol",
        }}
        run={async () => {}}
      />,
    );
    expect(html).toContain("Demander l’annulation");
    expect(html).toContain("Coûts auxiliaires et facture non mesurés");
  });
});
