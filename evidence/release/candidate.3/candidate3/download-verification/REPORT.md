# Downloaded candidate.3 fresh installation verification

**Result: PASS for the offline downloaded-install gate only.** No host integration, privacy audit, publication, tag or push was performed. No provider, auth or model calls were made; network isolation was confined to private namespaces with loopback enabled. This does not establish completion of GOAL.md or oh-my-pi integration.

Trusted linked worktree: `/srv/omr-private/workspaces/open-model-router/release-deadline-candidate`; HEAD/revision `63e517c25caa503b02eb38b2be994f8e2c32e142`, tree `f6d12bc5532ca1a132edcaf009f0cf73c21f750a`. Bundle input exclusively `.candidate3/downloaded`, previously downloaded from GitHub by parent; this run did not access GitHub. Manifest has 458 members. Existing certifier compares archive member set, regular type, modes and content with the expected Git members, verifies manifest and SHA256SUMS, then extracts; it exited 0. Downloaded inputs were unchanged across before/final SHA-256 checks:

- `SHA256SUMS`: `4678ed864d97eea47ce789562f399504c7b6dd3a0109f275fd55e9a4d5d2b94a`
- `manifest.json`: `cec82d993febb274152d1c93326758a1e56804118edc82856311e9f0b7e8f287`
- `open-model-router-0.1.0-candidate.3.tar.gz`: `44328fc6175cd1ac82527db0fd0b5d0788e381e1973643f55b082069261170bc`

Fresh external scratch `/srv/omr-private/workspaces/open-model-router/candidate3-download-install-20261027`, with initially absent installation path `freshinstall`; extracted source `freshinstall/source`, isolated venv `freshinstall/venv`, Python 3.13.5. `/tmp` bind-mounted to scratch inside unprivileged mount namespace to cover subprocesses replacing environment; private network namespace loopback only.

## Certifier

Executed from trusted worktree, stdout/stderr in `certify.log`, exit `0` in `certify.exit`; exact command also in `certify-command.txt`:

```sh
unshare -Urnm sh -c 'mount --bind "$1" /tmp && ip link set lo up && export TMPDIR="$1" HOME="$1/home" PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 && mkdir -p "$HOME" && exec python3 -B build_release.py certify --repo "$2" --revision 63e517c25caa503b02eb38b2be994f8e2c32e142 --bundle "$2/.candidate3/downloaded" --scratch "$1/freshinstall"' sh /srv/omr-private/workspaces/open-model-router/candidate3-download-install-20261027 /srv/omr-private/workspaces/open-model-router/release-deadline-candidate
```

Actual installed help passed; root discovery ran 64 tests, OK; host-adapters ran 9 tests, OK; landing reported `OK: 8 fragment links, 6 unique IDs, French and prototype disclosures`. The root log retains four intentionally failing subprocess fixtures asserted by passing `test_build_release.py` tests; these are not suite failures. Final certifier output: `Offline certification passed; no host integration was tested.`

## Other CI suites

Ran exact CI suite working-directory/discovery form against extracted downloaded source, not cached source. Command in `ci-command.txt`; separate raw `ci-*.log`, `ci-results.txt`, `ci.exit` (0). All five exits 0: pilot 16 run, 15 passed, 1 skipped (real local inference requires explicitly configured generator and weights); loop 6 passed; comparator 5 passed; integrated 9 passed; demo 6 passed. Combined with certifier: **115 tests run, 114 passed, 1 skipped**, plus standalone landing check. Counts exclude deliberately failing subprocess fixtures and exclude duplicate earlier runs.

Before the exact CI working-directory form, the same five suites were also run successfully with `unittest discover -v -s "$d"` from the extracted source root following the prior report's recipe. These were not retries after failures; their exact command, results, exit and raw logs are preserved as `subsuites-command.txt`, `subsuite-results.txt`, `subsuites.exit` and individual suite logs. No failed gate was retried or fixture weakened.

`downloaded-sha256-before.txt`, `downloaded-sha256-after.txt`, `downloaded-sha256-final.txt` and empty `downloaded-hash-diff.txt` preserve input identity checks. Tracked worktree remained unchanged (`git status --short` showed only existing untracked `.candidate3/`). Parent retains all other release and delivered-host gates.
