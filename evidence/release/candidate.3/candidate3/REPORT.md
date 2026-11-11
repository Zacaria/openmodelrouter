# Candidate 0.1.0-candidate.3 — private, not publication GO

## Identity and artifacts

- Signed commit `63e517c25caa503b02eb38b2be994f8e2c32e142`; tree `f6d12bc5532ca1a132edcaf009f0cf73c21f750a`. `git verify-commit` returned a good SSH signature. Detached linked worktree; tracked source unchanged.
- Private artifact directory: `/srv/omr-private/workspaces/open-model-router/release-deadline-candidate/.candidate3/` (permissions 0700). Two independent output directories `build1/` and `build2/` contain the archive, manifest and SHA256SUMS.
- Archive SHA-256: `44328fc6175cd1ac82527db0fd0b5d0788e381e1973643f55b082069261170bc`.
- Both manifest SHA-256: `cec82d993febb274152d1c93326758a1e56804118edc82856311e9f0b7e8f287`.
- Both SHA256SUMS SHA-256: `4678ed864d97eea47ce789562f399504c7b6dd3a0109f275fd55e9a4d5d2b94a`.
- The three output files are byte-identical across builds. Independent stdlib checker `independent_verify.py`, using canonical Git's blob objects rather than build tool internals, verified all 458 entries' names, regular types, exact modes and bytes against the trusted commit for each archive; see `independent-verify.log`.

## Commands and results

Executed from `/srv/omr-private/workspaces/open-model-router/release-deadline-candidate`; `TMPDIR=/home/operator/.hermes/cache/scratch` as provided by the environment. Build outputs were created outside the repository as required by the existing tool, then copied unmodified into `.candidate3/`.

```
python3 -B build_release.py build --repo "$PWD" --revision 63e517c25caa503b02eb38b2be994f8e2c32e142 --version 0.1.0-candidate.3 --output "$TMPDIR/candidate3-work/build1"
python3 -B build_release.py build --repo "$PWD" --revision 63e517c25caa503b02eb38b2be994f8e2c32e142 --version 0.1.0-candidate.3 --output "$TMPDIR/candidate3-work/build2"
```

Both exited 0; full outputs are `build1.log`, `build2.log`. Reinstallation and certification used the existing tool and trusted repository, in an unprivileged user/mount/network namespace with only loopback enabled. Binding `/tmp` to external scratch covers child test fixtures that replace their environment and omit TMPDIR. No test source edits, no provider calls, no retries.

```
unshare -Urnm sh -c 'mount --bind "$1" /tmp && ip link set lo up && export TMPDIR="$1" HOME="$1/home" PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 && mkdir -p "$HOME" && exec python3 -B build_release.py certify --repo "$2" --revision 63e517c25caa503b02eb38b2be994f8e2c32e142 --bundle "$2/.candidate3/build1" --scratch "$1/certified-install"' sh "$TMPDIR/candidate3-work" "$PWD"
```

Exit 0; complete `certify.log`. This validates the archive and manifest against the expected trusted Git commit, extracts to an isolated source directory, creates an isolated stdlib venv and runs installed `omr.py --help`, root unittest discovery (64 passed, including `test_deadlines.py`), host adapters (9 passed) and landing standalone check. Four failing subprocess fixture results in the root log are deliberately injected and asserted by passing `test_build_release.py` tests; they are retained, not suppressed.

The following additional suite ran against that same installed archive source in a fresh loopback-only namespace, with `/tmp` bound to external scratch:

```
unshare -Urnm sh -c 'mount --bind "$1" /tmp && ip link set lo up && export TMPDIR="$1" HOME="$1/home" PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1; cd "$1/certified-install/source" || exit 1; for d in pilot-t_f21a25b3 loop-t_daf181c7 comparator-t_14313d5b integrated-t_dab1958b demo-t_a3c46d97; do "$1/certified-install/venv/bin/python" -B -m unittest discover -v -s "$d" > "$2/.candidate3/$d.log" 2>&1; printf "%s %s\n" "$d" "$?"; done' sh "$TMPDIR/candidate3-work" "$PWD"
```

All five exits 0 (`subsuite-results.txt`): pilot 15 passed/1 skipped (real local inference requires explicitly configured generator and weights); loop 6, comparator 5, integrated 9, demo 6 passed. Across all suites: 115 tests run, 114 passed, 1 skipped, plus standalone landing check. Complete logs retained. A copy of the extracted installed source is retained as `installed-source/`; the test execution used the original scratch installation at `/home/operator/.hermes/cache/scratch/candidate3-work/certified-install/`, which is subject to scratch cleanup. Venv is not claimed portable.

## Scope and remaining gates

`candidate2-diff.txt` is the full Git inventory relative to `v0.1.0-candidate.2`: 107 added and 4 modified paths, including `omr.py`, `test_deadlines.py`, `.gitattributes`, `DELIVERY-STATUS.md`, and numerous added native evidence and candidate.2 release records. This broader inventory must be reconciled with the prior 92-document/2-runtime scope description: do not assume prior bounded GO covers any new member. **Final artifact-level privacy review is required before any publication**, especially the added logs, JSONL, evidence, paths and scripts. We did not repeat or assert privacy approval. No candidate.2 archive, tag or draft was altered; no tag, push, release or network spending was performed.

`GOAL.md` and `build_release.py` were read. A canonical `RELEASE.md` was not present in the worktree, canonical checkout, or candidate.2 Git tree; it could not be read. This is a documentation gap, not an implied approval. CI was not queried. Parent retains the CI, privacy, publication and delivered-version host replay gates.

## Proposed release notes (private draft)

Prototype candidate from signed commit above; includes bounded deadline/disconnect repair and offline archive verification. Offline certification passed as described, with one inference-dependent test skipped. This is not final four-host qualification: no host integration was tested during this certification, and previous host evidence cannot substitute for delivered-version replays. No claim of completed GOAL, production readiness, or final release.
