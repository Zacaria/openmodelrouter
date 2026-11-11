// Invoked only on the private native sidecar channel; never a WebView response.
import { loginOpenAICodexDevice } from "@oh-my-pi/pi-ai/registry/oauth/openai-codex";
import { refreshOAuthToken } from "@oh-my-pi/pi-ai/registry/oauth/index";
import { fetchCodexModels } from "@oh-my-pi/pi-catalog/discovery/codex";

const frame = (value: unknown) => process.stdout.write(JSON.stringify(value) + "\n");

export async function subscriptionAction(request: {
  action: string;
  credentials?: Parameters<typeof refreshOAuthToken>[1];
}) {
  if (request.action === "codex_login") {
    const credentials = await loginOpenAICodexDevice({
      signal: AbortSignal.timeout(600_000),
      onAuth: ({ url, instructions }) => {
        const code = instructions?.match(/^Enter code: ([A-Za-z0-9-]{4,32})$/)?.[1];
        if (!code || url !== "https://auth.openai.com/codex/device") throw new Error();
        frame({ auth: { url, code } });
      },
    });
    frame({ credentials });
  } else if (request.action === "codex_refresh" && request.credentials) {
    frame({ credentials: await refreshOAuthToken("openai-codex", request.credentials, AbortSignal.timeout(25_000)) });
  } else if (request.action === "codex_catalogue" && request.credentials) {
    let fetched = false;
    const catalogue = await fetchCodexModels({
      accessToken: request.credentials.access, accountId: request.credentials.accountId as string | undefined,
      baseUrl: "https://chatgpt.com/backend-api", paths: ["/codex/models"],
      signal: AbortSignal.timeout(20_000),
      fetchFn: async (input, init) => {
        const url = new URL(input instanceof Request ? input.url : String(input));
        if (fetched || url.origin !== "https://chatgpt.com" || url.pathname !== "/backend-api/codex/models") throw new Error();
        fetched = true;
        return fetch(input, { ...init, redirect: "manual" });
      },
    });
    if (!catalogue || catalogue.rejectedStatus) throw new Error();
    frame({ models: catalogue.models.map(({ id }) => id) });
  } else throw new Error();
}
