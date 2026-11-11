# Hermes transport cancellation closure — 27 October 2026

**Result: PASS for one targeted synthetic Hermes replay of runtime `63e517c25caa503b02eb38b2be994f8e2c32e142`, fixed local alias, not a runtime audit or global acceptance.** `python -B verify.py` exited 0; `verify.log` records the result. The original failed-first run and its exit-1 verifier remain unchanged; this new result does not retroactively turn that receipt into cancellation.

## Prior inconclusive run

The original `hermes-cancel.jsonl` records a `write_file` call for the list, a successful tool result, then later text before SIGINT. Its marker had no request ID; the preceding receipt `4808b958-8be5-43a6-a4af-86fab8b137fc` was `completed` with 2,329 completion tokens. There was no Hermes `cancelled` receipt. These facts do not establish which request was active at the marker or why a cancelled receipt was absent: timing/correlation were insufficient. No root cause is asserted. Original evidence hashes before/after are in `preflight.txt` and `after.txt`.

## Targeted replay

Reused the prior `vm-final-accept/hermes-cancel-replay` serial native strategy, with the deadline run's verified-byte observer. This isolated home/project has all native tools and permissions; the synthetic prompt requests direct chat without tool use, but does not disable tools. The single cancellation attempt and same native-session recovery ran without paid routes, bypass, fallback or artificially introduced stream delay. Initial synthetic setup precedes the one cancellation; recovery follows it. No Claude or Codex replay occurred.

The observer compiles the exact source bytes it SHA-256 checked in the gateway process (`runtime-*.json`): `6670df32c589ea6a3324eeff79dd10e45c9eaddb5d62f8526c7bf3e5e0b33a3b`, matching the commit blob and source before/after. It traces the existing gateway line immediately after write and flush, parses the current SSE event rather than a possibly stale event, and triggers only for nonempty text with terminal not seen. It checks the actual request's upstream socket file descriptor is established and captures the actual request row ID and session before sending SIGINT to the launcher. Tracing and inspection add observation overhead, but no deliberate delay or runtime/source modification.

* Marker: request `3b8880a9-f5d2-40cb-a0ec-bd009406cba0`, session `66b78358-bc3c-4812-8c3f-7a5cf55c3635`, upstream HTTP 200 and established socket `10.77.0.10:59848 → 10.77.0.11:11434`, no terminal observed. Native stream contained `1`; native result and launcher exit were 130.
* The exact ID and session match one gateway receipt: status **`cancelled`**, upstream 200, requested/observed alias `omr-hermes-qwen3-4b:ctx8192`, effort transmitted `none` (acknowledgment and application unknown). Other completed receipts, including those from recovery, are not attributed to cancellation.
* One second after launcher exit, no gateway established upstream socket and no live non-zombie process in observed child group 3680597 remained. This demonstrates socket closure at the later check, **not GPU computation stopping**.
* Same native session `local-6cf365d8b27b4cf3ba13321650f35350a267b57bde04dde913a63fe06ca841d6` resumed with exit 0 and recalled `blue-otter-73`. The same launcher session was used.
* Before: Ollama had no loaded model; GPU 796/16303 MiB, 0%. After: alias digest `814d45e79cc776294ae4fafa9a7acd47cbe3e614d20b80ee83e4096fdf9e1782`, context 8192, GPU 4733/16303 MiB, 0%. The model was not unloaded and unrelated sessions/services were not stopped.

## Artifacts and boundaries

`replay.py`, `observe.py`, `verify.py`, `verify.log`, `checks.json`, marker, runtime record, receipts, native event streams, commands/results, gateway log, and preflight/after snapshots are retained here. Synthetic session homes are not cleared or approved for publication. No Git writes, Kanban calls, or changes to canonical source, refs, or candidate.2 were made by this task; refs and source hashes match before/after. Canonical status changed concurrently from clean to modified `DELIVERY-STATUS.md` and untracked `evidence/reviews/deadline/`; these were not touched or reverted by this task. The observed result qualifies only this bounded run, not why the older run lacked a cancellation receipt.
