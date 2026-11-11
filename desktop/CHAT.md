# Chat playground

## Contract

Chat uses the real Vercel AI SDK `useChat` with a custom `ChatTransport`, not a second Node server or browser fetch. Native commands `chat_start`, `chat_poll`, `chat_cancel` travel through the existing Tauri allowlist / private sidecar JSONL. The sidecar calls its authenticated loopback OMR gateway; provider credentials stay native. CSP, Origin rejection and CORS remain unchanged. Polls drain a bounded in-memory queue every 40 ms, not persisted transcripts.

Enabled direct routes are grouped by connection/provider. With a consented decider and at least one enabled text model, an OMR group also offers Economy, Balanced and Quality. Profiles reuse the gateway's existing selection policy, quality floors and continuity rules; direct routes bypass the decider. Text protocols are Chat Completions, Responses and Anthropic Messages, in that preference order. A profile uses the first protocol supported by an enabled model and selects only among models compatible with that displayed protocol; no protocol conversion is introduced.

No tools, attachments, agent loops, retries, fallback or resume. Each turn submits the complete text conversation. An SDK conversation is pinned to the selected direct route or virtual profile and configuration revision: the native preflight and gateway selection reject revision drift. Automatic profiles may select a different concrete model on a later turn when the existing policy permits it. Changing model/profile or starting a new conversation clears the transcript; leaving Chat stops the request and forgets it. Failed/aborted conversations require New conversation before another send, so partial replies are not silently treated as completed context.

Sending explicitly authorizes that turn to the configured direct destination or automatic routing policy and may consume quota or incur charges. In automatic mode the consented decider also receives the configured decision context. Saving settings or selecting a profile never starts inference. Missing consent, invalid decisions or unavailable quality requirements are explicit refusals, not permission to fall back to a direct route.

## Bounds and completion

One active Chat request per sidecar; maximum 64 text messages, 128 KiB UTF-8 input, 1 MiB upstream SSE, 64 KiB per event, 120 seconds wall clock, 15 seconds without polling. Output token ceiling 4096, no forced reasoning setting. Exceeding a bound is an explicit error, never silent truncation. Arrêter, unmount and stale consumers shut down the native loopback socket; the gateway disconnect watcher then cancels the upstream HTTP/provider process. Shutdown also cancels Chat.

Success requires non-whitespace text, the protocol's normal text completion marker, clean stream termination and the completed gateway receipt identified by that response's exact `X-OMR-Request` header. A Responses stream may end with `[DONE]` only after a valid `response.completed`; the marker alone is not completion. The provider-observed identity must match the exact direct model, or the concrete model selected in that request's automatic gateway receipt, without any contradictory identity in the same response, including through pi-ai. Missing identity is unverified, not inferred from an encoder default. Refusal, length limit, tool-only output, empty text, invalid/missing terminal event and HTTP refusal are errors. Partial text remains visibly incomplete in the UI. The gateway receipt measures transport completion; the Chat result additionally reports semantic validation without changing or duplicating gateway usage receipts. The UI shows the request ID and confirmed identity only from that receipt. Provider error bodies are never sent to React or logs.

## SDK sources and checks

HTTP refusals retain their exact gateway receipt through `X-OMR-Request`, including the native safe refusal code. Chat displays that reason and HTTP status without reading or exposing a provider error body.

Official references consulted: https://ai-sdk.dev/docs/ai-sdk-ui/transport and https://ai-sdk.dev/docs/ai-sdk-ui/chatbot. Installed versions are exact-pinned in package.json / package-lock.json; their shipped ChatTransport and UIMessageChunk interfaces are the implementation authority. Dependency notices are collected by the existing build-notices path.

`python3 -m unittest test_desktop_chat` exercises the real sidecar/gateway against fragmented synthetic SSE, two turns, refusals, identity, limits and cancellation. Frontend tests exercise the SDK transport and real UI; repository tests, typecheck, notices, build and formatting must also pass. Native macOS packaged replay remains the composition/release lane's check, not a claim from Linux source fixtures.

`uv run --with playwright python desktop/scripts/chat_replay.py <evidence-dir>` exercises the production UI with the actual sidecar/gateway and synthetic generation/SystemOne endpoints, including two turns through each profile. Set `OMR_TEST_ENGINE` to an exact packaged engine to exercise those bytes instead of the source sidecar. The Tauri invoke boundary is substituted in this browser replay; it is not a native WebView or live-model qualification. The runner uses an isolated headless Brave profile on Linux or macOS, without touching the personal browser profile or saved OMR settings.
