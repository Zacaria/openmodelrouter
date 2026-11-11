# Final bounded composition verification

**GO for signing the source merge only**, subject to retaining the exact staged tree below. This is not GO for release, live-provider operation, native-host acceptance, or GOAL completion.

## Composition

- Canonical HEAD: `4f80c1d4d7f626d52c24556bcc1efc1f8493c112`; MERGE_HEAD: `48e77e2f692b729962a0941837061aa1cb8b6820`; staged tree: `f6d12bc5532ca1a132edcaf009f0cf73c21f750a`.
- Recursive tree union verified exactly: only `omr.py` and `test_deadlines.py` differ from HEAD, and each equals the feature tree entry including mode and blob. All other entries exactly equal HEAD. Entries: `omr.py` mode `100644`, blob `f314c85b179e13cf3a2ead18fcd862416c25aea1`; `test_deadlines.py` mode `100644`, blob `e75f0b36f81d4d89a12ce048d638d7e2ad8132e7`. The entire stage-0 index equals the candidate tree; no unmerged entries or tracked unstaged changes. Cached whitespace check passed.
- HEAD, MERGE_HEAD, status and index SHA-256 `f7c55938f438c76323c7e0a296361a9269302c099e8223a12c8e327726269519` were unchanged before/after the suite. No source, index or ref mutation or commit was performed.
- Reused `deadline-disconnect-independent-review.md` (37 tests; bounded runtime review) and `host-evidence-preservation-review.md` (host evidence/privacy reconciliation), without repeating unchanged semantic, native or privacy reviews. Existing raw non-deadline reset versus client-cancellation classification ambiguity remains a nonblocking limitation of this bounded repair.

## Offline checks

Executed the exact candidate tree exported outside canonical with Python 3.13.5, `PYTHONDONTWRITEBYTECODE=1`, `-B`, external `TMPDIR`, and isolated HOME. Release fixture subprocesses replace their environment and omit TMPDIR; an unprivileged private mount/network namespace bound `/tmp` to external scratch, with loopback enabled, so these subprocesses also stayed outside canonical without altering source or tests. No external network was available to the test namespace. Every listed command exited 0; no retry was performed.

| Suite | Result |
|---|---|
| Root `python3 -B -m unittest discover -v` | 64 passed |
| `pilot-t_f21a25b3` discover | 16 run: 15 passed, 1 skipped (real local inference requires explicitly configured generator Python and weights) |
| `loop-t_daf181c7` discover | 6 passed |
| `comparator-t_14313d5b` discover | 5 passed |
| `integrated-t_dab1958b` discover | 9 passed |
| `demo-t_a3c46d97` discover | 6 passed |
| `python3 -B host-adapters/test_launch.py` | 9 passed |
| `python3 -B tests/test_landing.py` | passed; 8 fragment links, 6 unique IDs |

Total: 115 unittest cases run, 114 passed and 1 skipped, plus the standalone landing check. The root log contains four intentional failing subprocess fixtures: `test_certification_discovers_all_expected_suites` asserts that certification rejects each injected failure; the enclosing root suite passed. These are preserved in the log, not suppressed or retried.

Persistent logs and before/after composition receipts: `/srv/omr-private/workspaces/open-model-router/deadline-integration-logs/`. The JSON results retain original external scratch paths; the corresponding named logs were copied to this persistent directory. `diff-check.log` is empty because the check passed.

Candidate.2 tag, draft, assets and historical logs were not modified or remotely rechecked. Final delivered-version host replays, real OMP qualification and release verification remain separate obligations; passing these offline checks does not discharge them.
