# Chat playground — source verification (4 November 2026)

## Candidate scope

Base: `8cf9a7f02a9c8bb77cc7cd6c505ab8f6b7a94795`. The signed commit containing this report is the source candidate; its exact SHA/tree, remote readback and evidence archive digest are in the Kanban handoff. No sibling candidate is included. Shared hotspot `desktop/src/App.tsx` has only eight added navigation/render lines. `desktop_engine.py`, `api.ts`, `types.ts`, provider setup, CSP and CORS are unchanged.

- Actual `useChat` from exact-pinned `@ai-sdk/react` 4.0.166 with `ai` 7.0.162 and a custom native `ChatTransport`.
- Separate frontend Chat, transport and CSS; native ephemeral worker in `desktop_chat.py`; three allowlisted Rust/sidecar commands.
- Native authenticated OMR gateway, direct selected route, credentials resolved natively, existing usage receipts retained. Optional revision fence is atomic with direct route selection; ordinary gateway callers retain the existing selection path and locking behavior.
- Text streaming over Chat Completions, Responses and Anthropic Messages; no retry, fallback, resume, tools, agent loop, Node server or persistent transcript.
- Stop/unmount/lease/deadline close the loopback socket; the gateway cancels the upstream socket/process. Semantic failure preserves partial text but locks further sends until New conversation. A user cancellation racing native completion cannot display success.

Contract: [CHAT.md](CHAT.md). No whole source file, database or user data was deleted; no migration or compatibility layer was introduced.

## Fresh verification

| Check | Result |
| --- | --- |
| RED before implementation | Missing native module and transport/UI tests failed before implementation; cancellation/completion race and malformed revision-fence request reproduced RED, then GREEN. |
| Canonical Python CI suites | Six suite discovery runs: 292 + 16 + 6 + 5 + 9 + 6 cases; host adapters: 9. All non-skipped tests pass. Four expected skips: three frozen-engine cases without `OMR_TEST_ENGINE`, one real pilot inference without weights/runtime. Landing verifier passes. |
| New native Chat tests | 12 tests, including fragmented Unicode SSE, two turns, three protocols, real compiled pi-ai adapter, exact/missing/mismatched identity, empty/refused/length/truncated output, native synthetic credential isolation, limits/deadline/abandonment, stop and revision fencing. Responses contradictory/incomplete terminal metadata is rejected. |
| Frontend | `npm test`: 42 tests across 11 files. `npm run check`, `format:check`, `build`, `test:build` pass. Real SDK streaming and two-turn state are tested, not just transport-shaped objects. |
| Dependencies/notices | Both lockfile installs and pi-ai typecheck/production build pass. Frontend build collects 118 dependency notices, retaining Vercel copyright/Apache headers and the full Apache-2.0 terms. `npm audit --omit=dev --audit-level=high`: zero vulnerabilities. |
| Python source checks | Black and Ruff on four changed Python modules pass; fatal Ruff checks on legacy-style `omr.py` pass. Pyright on four Chat/sidecar/test/replay paths: zero errors/warnings with Playwright available. |
| Rust source checks | Rustfmt, one allowlist regression and Clippy `-D warnings` pass with `TAURI_CONFIG='{"bundle":{"externalBin":[],"resources":[]}}'`. This invocation checks native source only, not a distributable bundle. |
| Built UI replay | `uv run --with playwright python desktop/scripts/chat_replay.py <evidence-dir>` passes in Brave against production assets, real private JSONL sidecar and OMR gateway, synthetic HTTP provider. Eleven check groups; five actual provider requests and five receipts; no browser page errors. |
| Actual UI inspection | Production screenshots checked: model grouping, two turns, live fragments, stopped/partial status, explicit refusal, receipt and exact identity, model-switch/new reset, unmount cancellation, no persisted transcript. Selector/button alignment and send helper spacing corrected. |
| Artifact/whitespace | Frontend assets and complete notices verified; evidence archive is hash-pinned in the handoff; `git diff --check` passes. |

## Reproduced environment limits and warnings

- Plain system-Python discovery initially lacked PyInstaller metadata and the compiled pi-ai runtime. Installing the locked sidecar requirements in an isolated `uv` environment and building the existing locked runtime resolved those failures; all canonical suites were rerun successfully.
- Plain `cargo test --locked` stops in the existing Tauri build script because `src-tauri/binaries/omr-engine-x86_64-unknown-linux-gnu` is absent. No dummy sidecar, fake package or production-config change was used. The source-only Rust checks above pass; frozen-engine/native package verification belongs to the existing Mac release lane.
- Vite reports a non-blocking 599 kB minified entry chunk warning (about 181 kB gzip). There is no runtime CDN or extra server.
- The fixture intentionally streams `Bonjour 🌲` to verify UTF-8 fragmentation. Its tree emoji is a missing glyph in the minimal Linux font image, not lost UTF-8; exact string assertions pass. User/provider content is not rewritten to hide missing system fonts.
- No paid provider call, real key read, OS-vault write, personal profile mutation, deployment, app installation, signing/notarization or Mac GUI qualification occurred in this source lane. The browser replay substitutes Tauri invoke only at the WebView boundary; it is not represented as a packaged-native replay.

## Exact next release step

Independent reviewer must approve this exact source SHA/tree and report. That review is a prerequisite of `t_820b8958`. The existing release owner then composes this delta with the approved UX `6c635d558968e2f0d867e82d6034af38126b1db5` and generation engine `4f2a28707b08a401578679d5adb04a50652deb35`, reusing the current `t_0fcc8c66` composition where applicable. Rebuild/replay the native Mac DEV application, preserving the personal vault/settings. The already-owned Ollama Mac loopback `http://127.0.0.1:11434/v1` and model `omr-hermes-qwen3-4b:ctx8192` can exercise the product without an imported API key; keep its owned tunnel alive until all consumers finish. Source fixtures do not qualify that real provider/GUI path.
