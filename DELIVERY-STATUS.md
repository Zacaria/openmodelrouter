# Delivery status — candidate, not complete

The GOAL contract is not met. Candidate.3 is published as a private prerelease and its downloaded installation passed. New journeys cover Codex Mac and both VM hosts, with Hermes transport cancellation established by a separate targeted replay. oh-my-pi Mac still lacks a verified usable route. Candidate.2 remains an unchanged draft with its original failed evidence.

## Current published source

- Signed merge `63e517c25caa503b02eb38b2be994f8e2c32e142`, independently reviewed tree `f6d12bc5532ca1a132edcaf009f0cf73c21f750a`; remote master matched. GitHub Actions `40459266741` succeeded on this exact commit.
- The bounded deadline repair preserves watcher timeout classification after upstream disconnect and reports timeout after streaming EOF. Core SHA-256: `6670df32c589ea6a3324eeff79dd10e45c9eaddb5d62f8526c7bf3e5e0b33a3b`. The pre-existing ambiguity of raw non-deadline upstream resets remains a disclosed limitation.
- Exact-composition offline checks: 114 passed, one inference-dependent test skipped, plus the landing check. These are not real host acceptance. Review and logs are retained under `/srv/omr-private/workspaces/open-model-router/deadline-integration-result.md` and `deadline-integration-logs/`.

## Candidate.3 installation and current host replay

Two builds from `63e517c25caa503b02eb38b2be994f8e2c32e142` were identical. Archive SHA-256: `44328fc6175cd1ac82527db0fd0b5d0788e381e1973643f55b082069261170bc`; manifest SHA-256: `cec82d993febb274152d1c93326758a1e56804118edc82856311e9f0b7e8f287`. Independent Git and privacy reconciliation covered all 458 archive entries. Both local and fresh GitHub-downloaded installation checks passed 114 tests, skipped one inference-dependent test, and passed the landing check. The three assets were published as a private prerelease under signed tag `v0.1.0-candidate.3` at 06:25:15 UTC on 27 October 2026. Remote readback confirmed draft=false and prerelease=true; a second download after publication matched the freshly certified downloaded assets byte-for-byte. Evidence: `evidence/release/candidate.3/`.

Fresh journeys use the new core bytes, not inherited historical results:

- **Codex Mac:** the parent reran `python3 -P verify.py` successfully in `mac-deadline-accept/`. Tool/result, separate-process same-thread resume, streaming, observed model, local invalid-session HTTP 400 without generation, active SIGINT and recovery are established. Five cancelled, one completed and one invalid-request gateway receipts remain distinct from native completion.
- **Claude Code VM:** the new replay reports tool/result, resume, streaming, controlled error and active interruption/recovery, including a cancelled transport receipt. Association remains serial-session based; socket closure does not prove GPU stop.
- **Hermes VM:** the first new replay establishes native interruption/recovery but has no cancelled transport receipt; its original verifier still exits 1. A separate targeted replay now passes, independently rerun by the parent: a flushed text delta and active upstream socket correlate by exact request ID to receipt `3b8880a9-f5d2-40cb-a0ec-bd009406cba0`, status `cancelled`; native exit 130, subsequent socket/group absence and same-session recovery are established. The earlier inconclusive run is unchanged, and socket closure does not prove GPU stop. Evidence: `vm-deadline-accept/hermes-cancel-closure/` in the external evidence workspace.
- **oh-my-pi Mac:** a separate native preflight on 27 October 2026 at 06:18 UTC returned OMP `18.13.0` and zero available models; both commands exited 0. This does not prove all credential stores are empty. Usable native authentication/backend and the full journey remain unestablished; owner login is still required. Receipt: `evidence/native/omp-current-preflight.json`.

VM and Mac raw evidence is preserved under `evidence/native/host-replay-63e517c/`: 93 exact source files plus manifest and reconciliation. Synthetic homes, auth/session stores, caches and an unrelated process inventory are excluded. The Mac and Hermes closure verifiers pass from the relocated packet; the original VM failed-first attempt remains unchanged. The reports below retain their original historical runtime scope.

## Historical SSE source checkpoint

- Signed commit `7e25c6e7e6547fb9d3bf1f2f1d71602dd3950f3b`, independently reconciled tree `dfd45901284f6948d7d86d23b5a38fbb9773afb1`; private `master` readback matched.
- GitHub Actions run `40455653619` succeeded on that exact commit. Local checks: 62 root tests, 9 host-adapter tests, and landing checks passed.
- Native headerless SSE validation is included. Core SHA-256: `ec9c11ac447bf37eb5919d98e535d4c91b82a0b39e36202030d01fd8b8eabb0c`. The validator is restricted to the pinned native route when Content-Type is absent; explicit wrong MIME types and malformed frames remain rejected.
- Review records, including the initial rejection and repaired-source closure, are preserved in `evidence/reviews/native-sse/`. The final-tree verdict permits signing, not final release acceptance.

## Candidate.2 publication hold

Signed tag `v0.1.0-candidate.2` points to `7e25c6e7e6547fb9d3bf1f2f1d71602dd3950f3b`. The private GitHub draft contains the archive, manifest and checksum file; its draft/prerelease state and all three downloaded assets were read back. Archive SHA-256: `3a8ffe5f2557903cd3132f938c0df8a9a118772aa339b6f8ea17ad3637f8c02c`. Two builds matched and all 351 members matched Git bytes and modes. Initial offline certification passed 62 root tests, 9 adapter tests and landing checks; the bounded content/privacy review found no publication blocker for those exact private assets.

The separate downloaded-install check passed `omr.py --help`, then failed one of 35 core tests: `test_no_headers_deadline_closes_backend_and_next_request_recovers` received `http.client.RemoteDisconnected` rather than the expected HTTP response. Adapter and landing checks in that attempt were not reached. The draft is **not published**; its signed tag and failed evidence are retained. The later repair is in candidate.3, not in these unchanged candidate.2 assets. See `evidence/release/candidate.2/publication-hold.json` and `download-check-1.log`. Checksums, source review and privacy approval do not establish runtime correctness.

## Historical archive checkpoint

- Signed source commit: `91a3e54376994f95aa525bdd1e2d1bd3f23324e7`.
- Independently reviewed tree: `bce6175363b432326ca65ed127ef48409aa46c43`.
- Private repository `Zacaria/open-model-router`: `master` was read back at that commit.
- GitHub Actions run `40436364509`: completed successfully on that exact SHA; regression-test and whitespace steps both succeeded.
- Candidate archive `open-model-router-0.1.0-candidate.1.tar.gz`: SHA-256 `cdb1745f4eba63b6d81fc9723e02f65a40dada20f5c45b6ae941e1c2e1158fd1`. Built from the commit and certified against an independently supplied repository/revision in a fresh virtual environment. Root 54 tests, adapter 9 tests and landing checks passed. This is an offline installation check, not four-host acceptance. The archive has not been published as a final release.

The candidate archive is currently retained at `/srv/omr-private/workspaces/open-model-router/release-91a3e543/`; certification output is in `integrated-checks/certify-91a3e543.log` under that workspace root. These are operator evidence locations, not prerequisites for running the source package. `INSTALL.md` describes reconstruction from a trusted Git revision.

## Historical host evidence on 7e25c6e7

The current VM replay and Codex controlled-error closure are preserved in `evidence/native/host-replay-7e25c6e7/`, with a 79-file manifest and reconciliation report. They bind to the core bytes of published runtime `7e25c6e7e6547fb9d3bf1f2f1d71602dd3950f3b`; no later repair or final release inherits them automatically. Older evidence on `97d2b77d1fd804531e6820800cc2f03bea4aec65` remains separately identified.

| Host | Established evidence | Still required |
| --- | --- | --- |
| Hermes VM | Runtime 7e25c6e7: real fixture read/result, streaming, resumed conversation, effective model, adapter-visible 502/timeout cleanup, active SIGINT and same-session recovery | Reconcile the deadline repair and bind to the final delivered runtime |
| Claude Code VM | Runtime 7e25c6e7: real fixture read/result, streaming, resumed conversation, effective model, native retry on gateway 502, active SIGINT and same-session recovery | Reconcile the deadline repair and bind to the final delivered runtime |
| Codex Mac | Runtime 7e25c6e7: real tool/result, separate-process continuation, streaming, effective model, active SIGINT/recovery and deterministic local HTTP 400/recovery | Reconcile the deadline repair and bind to the final delivered runtime |
| oh-my-pi Mac | Installed native CLI supports login; native available-model listing returned zero models | Establish usable authentication or an explicitly configured backend, then the complete host journey |

Historical VM identities and limits are in `evidence/native/final-vm/REPORT.md`, `evidence/native/error-visibility/REPORT.md` and `evidence/native/hermes/diagnostic.md`. They are not retroactively assigned to the integrated candidate.

Earlier observations remain in `evidence/native/vm-accept/REPORT.md`, including an inconclusive first Hermes cancellation and its separate positive retry. The current replay is `evidence/native/host-replay-7e25c6e7/vm-native-sse/REPORT.md`. Its failed first Claude cancellation observer and first generic Hermes recovery prompt are preserved alongside successful targeted retries. Hermes's HTTP 502 is adapter output, not a proven native Hermes API 502. Marker-to-receipt association is sequence/session based, not a shared request ID; socket closure does not prove GPU computation stopped.

For Codex 0.162.1, probes needed request compression disabled and an explicit gateway session UUID. Historical Accept-only failures and a complete upstream-only stream observation remain in `evidence/native/codex-headerless-observation/REPORT.md`; those were not successful client journeys. The current incremental validator subsequently enabled real client journeys using the same core bytes now published.

`evidence/native/codex-validated/REPORT.md` records the real Mac run: tool/result and sentinel, separate-process resume without the sentinel in the prompt, model `gpt-6.1-terra`, forwarded text deltas, and SIGINT after an active text delta before the terminal event, followed by same-thread recovery. Six generation requests were made. The controlled loopback network-error attempt timed out; retained evidence does not establish connection refused or a provider 502. Events are privacy-filtered metadata, not complete response bodies; the operator records the extraction logic. Original evidence and failed attempts remain unchanged.

All six gateway receipts from that initial Mac journey say `cancelled`, including successful native turns. Five forwarded `response.completed` events and native turn completion/usage establish native success, not gateway EOF completion. A client disconnect after a terminal event but before verified upstream EOF can produce this transport status. Do not relabel the receipts or infer user cancellation from that field alone. The genuine SIGINT attempt is established separately by its observer and process evidence.

The distinct closure in `evidence/native/host-replay-7e25c6e7/codex-validated/error-closure/REPORT.md` establishes a local HTTP 400 for an invalid synthetic gateway session, zero generation POSTs during that error phase, and one subsequent successful recovery generation on the same native thread. It does not establish a provider error or retroactively resolve the earlier network-timeout classification. Offline socket reproductions preserve the distinction between native completion, gateway EOF completion and truncated-frame rejection; they establish a possible mechanism, not the exact disconnect timing of the original receipts.

OMP's empty model list does not prove that every possible credential store is empty. A Codex login is not an OMP login. No authentication was copied between clients, and no new billing was enabled.

## Benchmark and public page

`evidence/campaign/analysis/REPORT.md` contains the repeated local campaign, raw-data references, negative results and diagnostic-oracle ambiguity. Development and validation sets and the initial failed attempt remain distinct. No general quality, latency or cost advantage has been established; token-price equivalents and subscription invoices are not measured.

The public landing was fetched after the source push: HTTP 200 and unchanged reviewed HTML SHA-256 `3ab910b3d6ce0e333037976bc4c773f1fde2af0d927c6683cbe4a5d2a440a054`. It remains a prototype page. Desktop/mobile evidence is in `evidence/landing/`; social drafts remain unpublished.

## Acceptance remains open

Establish the oh-my-pi route and its full real journey before claiming four-host delivery. The targeted Hermes cancellation proof, candidate.3 private publication/readback and fresh downloaded installation now pass. Its 458-member privacy reconciliation covers this exact private prerelease only. The deadline repair does not repair candidate.2 retroactively. This checkpoint is not final GOAL acceptance; source and release success cannot substitute for the missing fourth host or unsupported claims about effort, cost and general routing quality.
