# OMR Desktop — build candidate contract

## Ownership and composition

This CI candidate owns `.github/workflows/desktop-build.yml`, `ci/` and
`test_desktop_ci.py`. It does not own `desktop/`, `desktop_sidecar.py` or the
engine. The app owner is t_01bf8649. Release t_a3a76415 composes the two reviewed
commits in its own linked worktree; never package a copy of a live app checkout.
`DESKTOP-DISTRIBUTION.md` remains the distribution authority.

The existing `.github/workflows/tests.yml` is unchanged. The new workflow is
manual, read-only and build-only: no push/tag publication, release creation,
credentials, signing identity or notarisation account. PR code cannot receive
secrets through it. Existing offline checks still run on pushes/PRs.

## App contract (confirmed by app owner on t_c230c679)

Run from the repository root on the target OS, with native Python and Rust:

```sh
npm --prefix desktop ci
npm --prefix desktop run check
npm --prefix desktop test
npm --prefix desktop run format:check
```

Frontend files checked by Prettier must be checked out with LF on every OS.
The scoped `.gitattributes` rules enforce that contract even with Windows
`core.autocrlf=true`; they do not alter historical evidence or binary assets.

```sh
python -m pip install --require-hashes --only-binary=:all: -r desktop/sidecar-requirements.txt
python desktop/scripts/build_sidecar.py
npm --prefix desktop run build
cargo fmt --manifest-path desktop/src-tauri/Cargo.toml --all -- --check
cargo fetch --manifest-path desktop/src-tauri/Cargo.toml --locked --target <triple>
cargo test --manifest-path desktop/src-tauri/Cargo.toml --locked
cargo clippy --manifest-path desktop/src-tauri/Cargo.toml --all-targets --locked -- -D warnings
npm --prefix desktop run native:build -- --ci --target <triple> --bundles <formats>
```

`native:build` invokes the lockfile-installed Tauri CLI; its beforeBuildCommand
builds the frontend. No `npx --yes` or floating global CLI. `Cargo.lock` and
`package-lock.json` and `desktop/sidecar-requirements.txt` must be present and
tracked. CI installs Python build tools from that app-owned universal hash lock
in its setup-python build interpreter, not from an unconstrained pip resolution.
No duplicate CI dependency lock is maintained. The app owner confirmed Python
3.13.5, PyInstaller 6.16.0, hooks 2026.9, Node 24.21.0 and Rust 1.91.1.
Rust, Node, Python and action revisions are explicit in the workflow.
The workflow exports `CARGO_NET_OFFLINE=true` for the final package build after
locked Cargo fetch/tests have populated its cache, and rejects tracked lockfile
changes afterward. It does not assume the Tauri CLI forwards `--locked`.
The explicit frontend build precedes Cargo checks because it generates bundled
`NPM-LICENSES.txt`; Tauri's beforeBuildCommand repeats the build when packaging.

The sidecar builder has no target argument: it derives `rustc -vV`'s host and
writes `desktop/src-tauri/binaries/omr-engine-<triple>[.exe]`. CI refuses a host
mismatch before building. Tauri bundles `binaries/omr-engine` as `omr-engine`
(`.exe` on Windows). All three version fields (npm, Cargo, Tauri) must match.
IPC smoke uses an isolated temporary directory, a fresh synthetic in-memory
key, and JSONL `init`, `snapshot`, `shutdown`; no provider or user data is loaded.
The frozen binary is run with an empty PATH and no PYTHON* variables. No Python
installation from an end user's machine is used to launch it.

## Native matrix and evidence

| Runner | Triple | Packages |
| --- | --- | --- |
| macos-14 | aarch64-apple-darwin | DMG |
| macos-15-intel | x86_64-apple-darwin | DMG |
| ubuntu-22.04 | x86_64-unknown-linux-gnu | deb, AppImage |
| windows-2022 | x86_64-pc-windows-msvc | NSIS exe |

No universal macOS or untested Linux/Windows arm64 claim. Runner availability
and existing free quota must be checked by release before dispatch; no paid
runner or quota upgrade is authorised. Linux uses WebKitGTK 4.1 and native Tauri
system dependencies from the runner's OS repositories. OS packages and hosted
runner images are not bit-reproducible dependency snapshots.

`ci/desktop.py contract --target <triple>` checks the app/host contract.
`ci/desktop.py smoke --target <triple> --binary <path>` checks executable format,
architecture and frozen IPC. `ci/desktop.py collect --target <triple> --output
<empty-directory>` verifies packages before creating versioned architecture
names, `SHA256SUMS` and `verification.json`. Verification mounts the DMG,
extracts the deb and AppImage, or silently installs the NSIS package into an
isolated directory; it checks the main executable's architecture, all four
app-owned notices/license files, then runs each embedded sidecar. NSIS can touch
the registry and shortcuts even with an isolated install directory: this check
refuses non-GitHub-hosted environments and must not run on user workstations.
Linux deb and Windows sidecar bytes must match the pre-bundle sidecar.
AppImage is different: linuxdeploy rewrites the ELF RPATH to `$ORIGIN/../lib`.
CI replays that transformation on a copy of the original sidecar in a minimal
`usr/bin` AppDir, using Tauri CLI 2.12.4's linuxdeploy 07333c6 from the native
Tauri cache (`$XDG_CACHE_HOME/tauri`, otherwise `~/.cache/tauri`). The tool is
SHA-256 pinned, accepting only the downloaded bytes or Tauri's documented
three-byte AppImage-marker clearing. The entire embedded binary must match the
replayed reference hash before IPC runs: matching IPC or just the Python archive
is not sufficient. A changed payload, bootloader, RPATH or unexpected bundler
transformation fails closed. No binary is copied back into the real package.
On macOS, the workflow explicitly requests Tauri's ad-hoc identity `-` so it
signs nested code and seals the complete app before creating the DMG. The
previous build at `a331805fd4b9148467bca66d3464c6a0f08b49b2` skipped that
step: the arm64 main executable had only a linker ad-hoc signature and no
resource seal, causing `codesign --verify --deep --strict` to fail. Collection
must verify the mounted app and its embedded engine with strict codesign before
accepting the package. This tests integrity, not publisher identity or trust.
Tauri's hardened runtime must be disabled for this ad-hoc candidate: the frozen
Python engine otherwise cannot load its extracted libraries because they have
different Team IDs. This is not a Developer ID configuration; a future signed
distribution must separately design and verify its hardened-runtime entitlements
and notarisation rather than reusing this candidate setting uncritically. A
missing/duplicate package or sidecar, wrong architecture, failed IPC or changed
package checksum fails the job.

After the Linux bundle build, CI runs the real-relocation regression:
`python ci/test_linuxdeploy.py --sidecar desktop/src-tauri/binaries/omr-engine-x86_64-unknown-linux-gnu`.
It exercises pinned linuxdeploy, acceptance of its changed bytes, rejection by
the deb identity contract, and rejection of a substituted or tampered binary.
Locally, `--linuxdeploy <downloaded-tool>` allows the same probe with a frozen
synthetic IPC fixture. This regression is not OMR installer qualification.

Pinned tool asset:
`https://github.com/tauri-apps/binary-releases/releases/download/linuxdeploy-07333c6/linuxdeploy-x86_64.AppImage`.
SHA-256 downloaded: `36a2d7e274d12e1050d0e9ecfe11d339ed54720b2bec464c286d53f8b07f5c62`.
SHA-256 after Tauri clears offsets 8–10: `bd9521cd5ff3ca351fecb78cd9b236a4e37b3621014ac05cac0c2d767ffa0474`.
The verifier never downloads a fallback or accepts a floating tool version.

The manifest records source SHA, package/sidecar hashes and checks exercised.
It explicitly labels signing/notarisation as unqualified. macOS ad-hoc signing
is not Developer ID signing. Windows SmartScreen and macOS Gatekeeper may warn
or refuse unsigned downloads. No success label implies GUI launch, real-provider
operation or full installation qualification. Those remain release's native
manual checks. A fixture test validates only CI logic.

## Release commands (after both independent PASS verdicts)

```sh
# In the release-owned worktree based on c9fbada2f2392a3e5db27a70c84e4f685081586c:
git merge --no-ff <reviewed-app-sha>
git merge --no-ff <reviewed-ci-sha>
# Run the documented checks, commit/sign and preserve an authorised private branch.
git push origin HEAD:refs/heads/work/desktop-release-v1
# A new workflow must first exist on GitHub's default branch for workflow_dispatch.
# Release owns that reviewed integration; do not bypass it with a publishing workflow.
gh workflow run desktop-build.yml --repo Zacaria/open-model-router --ref work/desktop-release-v1 -f existing_quota_confirmed=true
gh run list --repo Zacaria/open-model-router --workflow desktop-build.yml --branch work/desktop-release-v1
gh run watch <run-id> --repo Zacaria/open-model-router --exit-status
gh run view <run-id> --repo Zacaria/open-model-router --json headSha,event,conclusion,jobs
gh run download <run-id> --repo Zacaria/open-model-router --dir <download-directory>
python ci/desktop.py verify-download <download-directory> --source-sha <reviewed-composition-full-sha>
```

The run's `headSha` must equal the exact reviewed composition SHA and every
native job must execute successfully. The quota input defaults to false, which
skips builds; a green skipped run is not build evidence. A rerun, uploaded
fixture or successful YAML validation is not the first actual build. Download
all four matrix artifacts, verify hashes against manifests, then exercise real
installation/GUI on available native hosts. Publish only through existing
release t_a3a76415, keeping private access and actual signing status explicit.
Missing signing access does not block unsigned builds or independent OS lanes.
