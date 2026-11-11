import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { Topology, ReceiptDetails } from "./components/observability";
import type { Config, Receipt } from "./types";
import App from "./App";
import { version } from "../package.json";

export const config: Config = {
  connections: [],
  reevaluate: true,
  context_tokens: 4000,
  total_tokens: 8000,
  max_messages: null,
  expected_output: 500,
  switch_margin: 0.1,
  baseline: null,
  decider: null,
};
const receipt: Receipt = {
  request_id: "synthetic",
  timestamp: 100,
  status: "completed",
  mode: "direct",
  model_requested: "model-from-receipt",
  model_observed: null,
  usage: {},
};

describe("local routing presentation", () => {
  it("separates the local breadcrumb from the editorial page heading", () => {
    const html = renderToStaticMarkup(<App />);
    const header = html.match(/<header>[\s\S]*?<\/header>/)?.[0] ?? "";
    expect(header).toContain('aria-label="Fil de navigation"');
    expect(header).toContain("Espace local");
    expect(html).toContain("Votre routage, en un regard.");
    expect(html).toContain('class="page-intro"');
    expect(header).not.toContain("<h1>");
  });
  it("keeps everyday destinations visible and advanced pages behind a closed disclosure", () => {
    const html = renderToStaticMarkup(<App />);
    const nav = html.match(/<nav[^>]*>[\s\S]*?<\/nav>/)?.[0] ?? "";
    const advanced = nav.match(/<details[^>]*>[\s\S]*?<\/details>/)?.[0] ?? "";
    expect(advanced).toContain("Avancé</summary>");
    expect(advanced).not.toMatch(/<details[^>]*\bopen=/);
    const everyday = nav.replace(advanced, "");
    for (const name of ["État", "Fournisseurs", "Chat", "Réglages"])
      expect(everyday).toContain(`>${name}</button>`);
    for (const name of [
      "Profils &amp; règles",
      "Stratégies natives",
      "Consommation",
      "Inspecteur",
    ]) {
      expect(advanced).toContain(`>${name}</button>`);
      expect(everyday).not.toContain(`>${name}</button>`);
    }
  });
  it("renders the product version from the desktop package in the header badge", () => {
    const html = renderToStaticMarkup(<App />);
    const header = html.match(/<header>[\s\S]*?<\/header>/)?.[0] ?? "";
    expect(header).toContain(`<span class="badge">v${version}</span>`);
    expect(header).toContain("Reprendre la configuration");
  });
  it("loads the actual IPC shell with a busy state, not demo data", () => {
    const html = renderToStaticMarkup(<App />);
    expect(html).toContain('aria-busy="true"');
    expect(html).toContain("Connexion au moteur…");
    expect(html).toContain("/brand/app-128.png");
    expect(html).not.toContain("12 840");
  });
  it("shows empty topology without fabricating a route or available decider", () => {
    const html = renderToStaticMarkup(
      <Topology config={config} receipts={[]} revision={3} />,
    );
    expect(html).toContain("Aucune route observée");
    expect(html).toContain("Décideur non configuré");
    expect(html).toContain("0 modèle direct autorisé");
    expect(html).toContain("r3");
    expect(html).not.toContain('data-selected="true"');
  });
  it("highlights only the last observed route, not a configuration guess", () => {
    const html = renderToStaticMarkup(
      <Topology
        config={config}
        receipts={[
          { ...receipt, timestamp: 300, profile: "quality", mode: "automatic" },
          { ...receipt, timestamp: 200 },
        ]}
        revision={9}
      />,
    );
    expect(html).toMatch(/data-selected="true"[^>]*><span>Qualité/);
    expect(html).toContain("Dernière requête observée");
    expect(html).not.toContain("Aucune route observée");
    expect(html.match(/data-selected="true"/g)).toHaveLength(1);
  });
  it("presents unknown usage and a structured reason without inventing a model identity", () => {
    const html = renderToStaticMarkup(
      <ReceiptDetails
        receipt={{
          ...receipt,
          reason: "continuity_cost",
          candidates: ["candidate-a"],
          config_revision: 4,
        }}
      />,
    );
    expect(html).toContain("Modèle confirmé");
    expect(html).toContain("Non confirmé");
    expect(html).toContain("Non mesuré");
    expect(html).toContain("Coût de continuité");
    expect(html).toContain("candidate-a");
    expect(html).toContain("Métadonnées complètes");
  });
  it("keeps native session receipts out of HTTP topology selection", () => {
    const html = renderToStaticMarkup(
      <Topology
        config={config}
        receipts={[
          { ...receipt, timestamp: 200, mode: "native" },
          { ...receipt, timestamp: 100 },
        ]}
        revision={1}
      />,
    );
    expect(html).toMatch(/class="topology-route direct" data-selected="true"/);
  });
  it("shows native usage scope and unknown auxiliary costs in inspector", () => {
    const html = renderToStaticMarkup(
      <ReceiptDetails
        receipt={{
          ...receipt,
          mode: "native",
          native: {
            action: "compact",
            event_types: ["contextCompaction"],
            completed_children: 0,
            thread_usage: { inputTokens: 123 },
            last_call_usage: { inputTokens: 12 },
            auxiliary_cost_usd: null,
            full_cost_usd: null,
            actual_billed_usd: null,
            permission_denials: 1,
          },
        }}
      />,
    );
    expect(html).toContain("contextCompaction");
    expect(html).toContain("pas le total du tour");
    expect(html).toContain("Non mesurés · aucun gain présumé");
    expect(html).not.toContain("Trace de décision");
  });
  it("does not present unreconciled native compaction counters as zero consumption", () => {
    const html = renderToStaticMarkup(
      <ReceiptDetails
        receipt={{
          ...receipt,
          mode: "native",
          native: {
            action: "compact",
            event_types: ["contextCompaction"],
            completed_children: 0,
            thread_usage: {
              inputTokens: 100,
              outputTokens: 10,
              totalTokens: 110,
            },
            last_call_usage: {
              inputTokens: 0,
              outputTokens: 0,
              totalTokens: 634,
            },
            auxiliary_cost_usd: null,
            full_cost_usd: null,
            actual_billed_usd: null,
            permission_denials: 0,
          },
        }}
      />,
    );
    expect(html).toContain(
      "Le total natif ne correspond pas aux sous-compteurs",
    );
    expect(html).toContain("ne prouvent pas une consommation nulle");
    expect(html).toContain("634");
  });
  it("does not invent missing decider output tokens", () => {
    const html = renderToStaticMarkup(
      <ReceiptDetails
        receipt={{ ...receipt, decision_usage: { input_tokens: 5 } }}
      />,
    );
    expect(html).toContain(
      "Décideur · durée / tokens</dt><dd>Non mesuré / Non mesuré",
    );
  });
});
