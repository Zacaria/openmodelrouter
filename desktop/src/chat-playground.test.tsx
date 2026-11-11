import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ChatPlayground, chatRoutes } from "./chat-playground";
import type { Config, Connection } from "./types";
const model = {
  id: "model",
  upstream: "vendor/exact",
  protocols: ["chat"],
  enabled: true,
  tools: false,
  quality: 1,
  input_price: null,
  output_price: null,
  effort: null,
};
const connections: Connection[] = [
  {
    id: "provider-a",
    name: "Provider A",
    url: "https://a.invalid/v1",
    models: [model, { ...model, id: "off", enabled: false }],
  },
  {
    id: "provider-b",
    name: "Provider B",
    url: "https://b.invalid/v1",
    models: [{ ...model, id: "responses", protocols: ["responses"] }],
  },
];
describe("Chat playground", () => {
  it("offers all three profiles only with consent and enabled compatible models", () => {
    const consent = { model: "d3:4b", consent: true };
    const groups = chatRoutes({ connections, decider: consent } as Config);
    expect(groups[0]).toEqual({
      id: "omr/profiles",
      name: "OMR",
      models: [
        { route: "omr/economy", upstream: "Économie", protocol: "chat" },
        { route: "omr/balanced", upstream: "Équilibré", protocol: "chat" },
        { route: "omr/quality", upstream: "Qualité", protocol: "chat" },
      ],
    });
    expect(groups.slice(1)).toEqual(chatRoutes({ connections } as Config));
    expect(
      chatRoutes({
        connections,
        decider: { ...consent, consent: false },
      } as Config),
    ).toEqual(chatRoutes({ connections } as Config));
    expect(
      chatRoutes({ connections: [], decider: consent } as unknown as Config),
    ).toEqual([]);
    for (const protocol of ["responses", "anthropic"]) {
      const single = [
        { ...connections[0], models: [{ ...model, protocols: [protocol] }] },
      ];
      expect(
        chatRoutes({
          connections: single,
          decider: consent,
        } as Config)[0].models.every((m) => m.protocol === protocol),
      ).toBe(true);
    }
  });
  it("groups only enabled exact routes by configured provider", () => {
    expect(chatRoutes({ connections } as Config)).toEqual([
      {
        id: "provider-a",
        name: "Provider A",
        models: [
          {
            route: "direct/provider-a/model",
            upstream: "vendor/exact",
            protocol: "chat",
          },
        ],
      },
      {
        id: "provider-b",
        name: "Provider B",
        models: [
          {
            route: "direct/provider-b/responses",
            upstream: "vendor/exact",
            protocol: "responses",
          },
        ],
      },
    ]);
  });
  it("offers a real empty state without inventing a model", () => {
    const html = renderToStaticMarkup(
      <ChatPlayground
        config={{ connections: [] } as unknown as Config}
        revision={1}
      />,
    );
    expect(html).toContain("Aucun modèle activé");
    expect(html).not.toContain("Envoyer");
  });
  it("requires an explicit model selection and discloses billing and reset semantics", () => {
    const html = renderToStaticMarkup(
      <ChatPlayground config={{ connections } as Config} revision={1} />,
    );
    expect(html).toContain("Choisir un modèle");
    expect(html).toContain("Changer de modèle ou de profil efface");
    expect(html).toContain("décideur configuré");
    expect(html).toContain("facturé");
    expect(html).not.toContain("localStorage");
  });
});
