# Candidate build and offline installation report

**Candidate only; not final delivery, release or publication.** Source: trusted local canonical repository `/home/operator/repos/open-model-router`, externally supplied expected commit `7e25c6e7e6547fb9d3bf1f2f1d71602dd3950f3b`, tree `dfd45901284f6948d7d86d23b5a38fbb9773afb1`. Local `origin/master` contains this commit; no network verification was performed. Python 3.13.5, Git 2.47.3.

Archive: `build-one/open-model-router-0.1.0-candidate.2.tar.gz`, SHA-256 `3a8ffe5f2557903cd3132f938c0df8a9a118772aa339b6f8ea17ad3637f8c02c`. Manifest: `build-one/manifest.json`, SHA-256 `108c7035bb8adb442af311e3c0695e37965d7f8351f2aba668e177f7e03e205f`. A second independent build in `build-two` has byte-identical archive, manifest and SHA256SUMS. The release-tool, test and installation-guide hashes match the three hashes in the historical bounded review.

## Commands and results

Set `R=/home/operator/repos/open-model-router`, `D=/srv/omr-private/workspaces/open-model-router/release-native-sse-candidate`, `C=7e25c6e7e6547fb9d3bf1f2f1d71602dd3950f3b`.

```sh
python3 -B "$R/build_release.py" build --repo "$R" --revision "$C" --version 0.1.0-candidate.2 --output "$D/build-one"
python3 -B "$R/build_release.py" build --repo "$R" --revision "$C" --version 0.1.0-candidate.2 --output "$D/build-two"
cmp "$D/build-one/open-model-router-0.1.0-candidate.2.tar.gz" "$D/build-two/open-model-router-0.1.0-candidate.2.tar.gz"
cmp "$D/build-one/manifest.json" "$D/build-two/manifest.json"
cmp "$D/build-one/SHA256SUMS" "$D/build-two/SHA256SUMS"
env -i PATH="$PATH" HOME="$D/tmp" TMPDIR="$D/tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 python3 -B "$R/build_release.py" certify --repo "$R" --revision "$C" --bundle "$D/build-one" --scratch "$D/install"
```

Builds, comparisons and certification exited 0. Certification validated and extracted the archive into its own disposable scratch, created a no-pip venv and ran the following from extracted `source`:

- `venv/bin/python omr.py --help`: exit 0.
- `venv/bin/python -m unittest discover`: 62 tests, OK. Nested negative fixture failures printed in the log are intentional assertions by the existing release tests; the overall suite passed.
- `venv/bin/python host-adapters/test_launch.py`: 9 tests, OK; synthetic upstream 502 messages are expected test output.
- `venv/bin/python tests/test_landing.py`: `OK: 8 fragment links, 6 unique IDs, French and prototype disclosures`.
- No additional `tests/test*.py` modules were discovered by the certification tool.

Full raw output is `certification.log`; install and own temporary directory were removed after verification (`cleanup.log`). The existing certifier constructs a reduced subprocess environment without TMPDIR, so its nested unittest fixture temporary directories used `/tmp` and their own test cleanup; no user or peer outputs were removed. This was an offline source extraction/venv execution, not a package installation or actual host replay.

An additional independent Git-tree/manifest/tar comparison checked all 351 paths, file bytes and modes against Git blobs, with no duplicate members. Forbidden cache/dependency/secret-like path checks and a limited private-key/token-pattern scan produced no matches (`inventory-check.log`). This is not proof that credentials are absent: a complete audit of text and binary content is required before publication. Neither checksums nor manifest authenticate provenance.

Canonical repository status remained clean; HEAD/tree and raw index SHA-256 `b18e527c5daa1ceb8b92d7a56ffa9f5bd4292129f912e6a33a4a981fdc7f0953` were unchanged. No source, index, ref, candidate.1, website or remote state was intentionally changed. No host/provider generation or authenticated calls were made.

OMP native availability remains unresolved. Real host replays and publication decisions are separate. Historical evidence bundled with the source is historical, not proof of current behavior or candidate-specific integration. See `release-notes.md` and `result.json`.
