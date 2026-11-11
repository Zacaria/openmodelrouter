import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { createProvider } from "./provider-presets";
import { SubscriptionAccess } from "./subscription-access";

describe("subscription setup", () => {
  it("creates routable subscriptions, not a native-strategies shortcut", () => {
    const codex = createProvider("codex");
    expect(codex.subscription).toBe("codex");
    expect(codex.url).toBe("https://chatgpt.com/backend-api/codex");
    expect(codex.transport).toBe("pi-ai");
    const portal = createProvider("nous");
    expect(portal.subscription).toBe("nous");
    expect(portal.url).toBe("http://127.0.0.1:8645/v1");
    expect(portal.transport).toBe("http");
    for (const c of [codex, portal]) {
      expect(c.models).toEqual([]);
      expect(c).not.toHaveProperty("api_key");
    }
    expect(createProvider("jev").url).toBe("https://api.typesafe.ai/v1");
  });
  it("does not claim real inference or import another application's subscription", () => {
    const codex = renderToStaticMarkup(
      <SubscriptionAccess
        connection={createProvider("codex")}
        disabled={false}
      />,
    );
    expect(codex).toContain("Connecter Codex");
    expect(codex).toContain("ne sont pas importées");
    const nous = renderToStaticMarkup(
      <SubscriptionAccess
        connection={createProvider("nous")}
        disabled={false}
      />,
    );
    expect(nous).toContain("Connecter Nous Portal");
    expect(nous).toContain("Hermes doit être installé");
    expect(nous).toContain("sans changer vos réglages Hermes");
    expect(codex + nous).not.toContain("génération vérifiée");
  });
});
