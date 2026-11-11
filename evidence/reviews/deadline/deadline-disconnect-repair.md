# Deadline disconnect repair

- Worktree: `/srv/omr-private/workspaces/open-model-router/deadline-disconnect-repair`; branch `work/deadline-disconnect-repair`; HEAD `cefd2bd6823d7c4c11a4fd6cbeab2e96ee3167e6`; original tree `3cb93f7d8d60abeb395f66cd569124712ff822fa`; staged tree `b464bf7ad7887d37c79e1e90ed2b784110a80ffe`.
- Staged only `omr.py` and `test_deadlines.py`. No commit, canonical edit, publication, provider call, or change to downloaded candidate/log. No untracked worktree files observed.
- SHA-256 `omr.py`: old `ec9c11ac447bf37eb5919d98e535d4c91b82a0b39e36202030d01fd8b8eabb0c`; new `6670df32c589ea6a3324eeff79dd10e45c9eaddb5d62f8526c7bf3e5e0b33a3b`.
- SHA-256 `test_deadlines.py`: old `c26548fb9182d4a2cc666fe02006afc62a106a55916b9eb4eb0f8c829fbab495`; new `9608f05a059897beb20abd22062d02d657cfecd3c95b2a812a4c864fb01cb4bc`.

## Root cause and repair

`http.client.RemoteDisconnected` inherits `ConnectionResetError`. When the deadline watcher shuts down the upstream before headers arrive, `getresponse()` can raise that exception, and the earlier broad reset handler overwrote timeout with cancelled and sent no reply. A synchronized loopback test reproduced the original `RemoteDisconnected` at the client before the fix. The repair preserves the watcher's stop reason independently of the mutable receipt, sends sanitized 504 for pre-header timeout, and preserves true cancellation. RemoteDisconnected without watcher timeout is handled as an upstream failure rather than a client cancellation.

A second synchronized real-socket regression showed that watcher shutdown after streaming headers can yield EOF instead of an exception, silently skipping the timeout event. It failed before the EOF fix and now receives the generic timeout SSE event. Existing truncation, SSE, authorization, and disconnect checks remain in the core run.

## Verification and limits

`PYTHONDONTWRITEBYTECODE=1 TMPDIR=/home/operator/.hermes/cache/scratch python3 -B -m unittest -v test_headerless_native test_codex_native test_omr test_transport test_review_regressions test_deadlines test_router test_compare test_download`: **37 tests passed**, 14.899s. Output: `/home/operator/.hermes/cache/scratch/deadline-repair-core.log` (scratch, subject to pruning). `git diff --cached --check` passed. No full release fixture suite was run, per instruction; this is not release or live provider validation.

Residual: a non-deadline raw upstream `ConnectionResetError` (as distinct from `RemoteDisconnected`) is still classified as cancellation by pre-existing behavior; no claim that general reset-origin classification is solved. The synchronized tests cover the watcher-induced disconnect and streaming EOF paths, not all possible OS scheduling races. The running gateway process observed was in the separate pre-existing `router-gateway` worktree, not this worktree, and was left untouched.
