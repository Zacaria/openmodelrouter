# Independent native SSE review — NO GO

Review date: 2026-10-27. Host replay: **not attempted**, as required on NO GO. This is a candidate review, not a Mac integration result.

## Frozen identity

- Workspace: `/srv/omr-private/workspaces/open-model-router/router-gateway`
- HEAD: `fbf7dc4b9cb2f8d27226ea6e9bb32d56ae31a1c1`
- Staged tree: `1c459e2d302ccf929cea084e75992e951a7cb923`
- Staged paths only: `GATEWAY-SPEC.md`, `omr.py`, `test_headerless_native.py`; no unstaged changes to tracked paths.
- `omr.py` SHA-256: `c6a0ee77bfa8c802a518d2f460e189e55952a9a74c933c8325d50b92c660d585`.
- SDK reference revision `092d3acd6bec3e3a14bdc7e7a2810ab628ab759d`; all seven reference files matched their manifest SHA-256 values.

## Blocking finding: SDK-consumed fields and nested error pass unchecked

`omr.py:240-255` validates only a subset of the fields on output items. An independent synthetic loopback exercise of the actual gateway native route sent `response.created`, followed by `response.output_item.done` with item `{ "type":"function_call", "name":"run", "arguments":"{}", "call_id":"c", "namespace":42, "error":{"message":"SYNTHETIC_SECRET"} }`, followed by `response.completed`. The gateway returned HTTP 200 and forwarded the complete malformed tool item, nested error text, and completion; it emitted no sanitized stream error. Observed: `bad_item_forwarded=true`, `synthetic_nested_error_forwarded=true`, `sanitized_stream_error=false`, `completed_forwarded=true`.

The pinned SDK `protocol/src/models.rs` defines function-call `namespace` as `Option<String>`. Its `codex-api/src/sse/responses.rs` deserializes `ResponseItem` for output-item events and, on deserialization failure, logs and does not emit that item. Thus the demonstrated numeric namespace is accepted by the gateway but is incompatible with the pinned SDK; the likely SDK consequence is a silently dropped tool event, inferred from the source rather than a real-client execution. The nested error is also forwarded rather than rejected. This fails the requested consumed-field and nested-error validation proof. The probe used only synthetic values; the marker is not a real secret. Preserve intentional tool-argument strings and supported extension behavior while correcting validation rather than blindly scanning arbitrary text.

## Checks and limits

- `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -v`: **33 tests passed**, 13.477 s; includes 6 headerless tests and native auth, session isolation, redirects, cancellation, deadlines, truncation and live incremental-delivery tests. Earlier focused run: 21 passed. An initial mistyped `test_native` module invocation produced an import error; corrected to `test_codex_native` in subsequent runs.
- Reviewed staged diff, route configuration, authentication/header allowlist, native catalog and responses callers, HTTPS connection and endpoint selection, session keying, stream loop, disconnect watcher, timeout and cleanup. Native endpoint remains pinned to `https://chatgpt.com/backend-api/codex`, HTTPS uses standard `HTTPSConnection` certificate verification, native auth and session logic unchanged in diff, and no redirect following was observed in the regression test. No live TLS connection was made in this review; mocked transport tests do not themselves prove remote TLS behavior.
- Headerless acceptance is limited to native streaming and a missing Content-Type. Offline tests reject explicit empty/wrong native MIME and non-native missing MIME; withhold downstream headers until first complete valid created frame; reject tested nested response errors, foreign lines and truncated frames; demonstrate first-frame delivery before upstream ends and disconnect-driven upstream shutdown. These checks do not cover all nested fields, as the blocking reproduction shows.
- Bounded security scan: inspected changed trust-boundary parser and native auth/endpoint/deadline/cancellation flow, `git diff --cached --check` clean. No broad architecture audit; no claims beyond examined paths.
- No source, index, Git ref, commit, canonical files, or authentication files were changed. Pre-existing untracked `__pycache__` directories were observed and left untouched. No real provider generation or spending occurred.
