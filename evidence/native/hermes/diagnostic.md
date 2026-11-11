# Hermes HTTP 400 — synthetic diagnostic, 2026-10-27

## Cause and correction

With the original gateway on `127.0.0.1:38245`, frozen gateway SHA-256 `f9d0f4c32cb354e06c0d0113c340322018b275747f94ed51b10905599c1771fd`, Hermes `--ignore-user-config --reasoning none` reproduced HTTP 400. A disposable local proxy inspected only request parameters; it retained neither credentials nor system/message text. The chat request had 2 messages, 8 tools, `stream=true`, and `stream_options.include_usage=true`. Replaying that same in-memory request directly to the original Ollama OpenAI Chat Completions endpoint, replacing only the virtual model with the configured actual model, returned:

`request (4433 tokens) exceeds the available context size (4096 tokens), try increasing it`

Ollama `/api/ps` reported the original model's `context_length` was 4096. The gateway's response masked this upstream detail. A preceding separate Hermes metadata request had no messages and was not a Chat Completions request; replaying it at `/v1/chat/completions` returned an unrelated missing-messages error. No claim is made that it caused the generation failure.

Created Ollama alias `omr-hermes-qwen3-4b:ctx8192` from the same base model with `num_ctx=8192`, retaining inherited settings. `/api/show` confirmed `num_ctx 8192`; `/api/ps` after generation confirmed `context_length 8192` and `size_vram=3877571133`. Started a separate frozen gateway at 38246 using `gateway-config.json`; existing gateway and core were not changed. This is a gateway/backend configuration correction, not an alteration to the wrapper or removal of tools/permissions. The alias remains installed on Ollama and the separate gateway may be stopped after the pass. The absolute endpoint and receipt path in this evidence config are specific to this VM; use the README instructions to configure a native host.

## Results

- `simple.jsonl`: streamed actual `OMR_HERMES_OK`, exit 0; initial prompt usage 4433 tokens. Gateway session `1bf4bf4c-e53c-4b8d-a3fd-825806d998d8`, receipt `b378ce77-76e9-4ff3-9b29-e39548bb1dfc`.
- `tool.jsonl`: model chose `read_file` despite prompt requesting terminal; actual tool call and response correctly read the synthetic fixture, and the answer contained its value. Gateway session `944dd912-2f4f-450f-9b38-f0729be3bda6`, tool request receipts `bd7759de-badc-4f21-8546-f0a1cb9a9baa` and `2a9ec1a2-7df5-4161-be18-01dc82f540d9`. This verifies read tool use, not execution of terminal.
- `multiturn.jsonl`: attempted second user turn with `--resume` of the synthetic tool session and same gateway UUID. It failed before generation: the wrapper's newly allocated proxy base URL differed from the saved session base URL. Thus multi-user-turn remains unverified, not a success.
- `python3 -B host-adapters/test_launch.py`: 2 tests passed. No production Python changes. Effort was transmitted `none`; actual application is not acknowledged by this backend.

Each one-shot used the README launcher with the described gateway port, a fresh UUID, synthetic project `evidence/native/project`, `--ignore-user-config --reasoning none --format stream-json`; prompts and event output are in the adjacent JSONL. The resume command used the same gateway UUID and the synthetic Hermes session ID in `tool.jsonl`. `receipts.jsonl` includes some separate metadata/auxiliary calls; it is not evidence that each line is a user turn.

Limits: 8192 is sufficient for these probes, not unbounded chat or a universal hardware setting. No cancellation, controlled-error coverage, Mac, full policy preservation under all configurations, or cross-process resume was proven. Credentials were not stored in these artifacts.
