# pi-ai runtime distribution materials

## Boundary

This contract covers the provider runtime introduced in candidate `b55ce49`:
`omr-pi` (Bun + bundled JavaScript) and the host's baseline/default
`pi_natives*.node`. It does not change the application, provider semantics,
installer, UI, or release authority. A Linux engine kit is not a native GUI
installer qualification. macOS arm64/x64 and Windows x64 require their own native
build, archive inspection and execution; cross-compilation is not qualification.

## Primary sources and obligations

Bun 1.4.4 is commit `38afee6c84fcf48c0edb2466aa4b27d287a59c30`.
Its [LICENSE.md](https://github.com/oven-sh/bun/blob/38afee6c84fcf48c0edb2466aa4b27d287a59c30/LICENSE.md)
is an MIT declaration and third-party inventory, **not** an MIT permission text.
The generated runtime notices pair that declaration with the complete standard
MIT text from SPDX's `license-list-data` revision
`31846481de7ea17d92f2f46fad76abe58b2e9bb0`, `text/MIT.txt`. Its URL and SHA-256
are pinned in `bun_mit_terms` in the source lock; its original template copyright
placeholders are retained and explicitly **not** asserted as Bun attribution.
Actual upstream copyright statements remain verbatim with their source paths.
The standard text identifies the declared license; it does not invent a new
upstream grant, copyright holder or year.

The collector preserves named license files and leading block/line-comment
copyright or license notices in C/C++, Objective-C, Rust, Zig, JavaScript and
TypeScript sources across the archives, not just WebKit directories. In
particular it retains Bun's `MoveOnlyFunction.h`, `FormatStackTraceForJS.h` and
`src/glob/matcher.rs` notices, including their complete terms and source paths.
Both the standard MIT text and the generated notices accompany the source kit;
the identical generated notice payload is embedded in the frozen engine.
The full upstream sources and their notices must remain available for inspection.

The pinned Bun build recipes select:

| Component                | Revision                                     | Primary terms and concrete requirement                                                                                                                                                                                    |
| ------------------------ | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| JavaScriptCore/WebKit    | `d6375c72affe0f70222cdcb45012b10f0bf3a9d5`   | `Source/JavaScriptCore/COPYING.LIB` contains GNU **Library GPL v2**. Individual files include v2-or-later and BSD notices. Preserve them, the exact corresponding source, build scripts and prominent library-use notice. |
| TinyCC                   | `05f0fafaa3be31e31d7b4b5c17dc60f62c991171`   | `COPYING` contains **LGPL 2.1**; `libtcc.c` grants v2-or-later. Preserve the source and Bun's `patches/tinycc/tcc.h.patch`, not an unpatched substitute.                                                                  |
| ICU                      | WebKit's `icu/source.json`                   | Linux/Windows bundle ICU statically; macOS uses system ICU. Preserve the pinned ICU source, Unicode terms and WebKit's data/filter/decompression scripts.                                                                 |
| Bun's other dependencies | Bun's `scripts/build/deps/` and `Cargo.lock` | Preserve their actual notices and sources, including nested license texts. The root Bun inventory is not a substitute for these texts.                                                                                    |
| pi-ai / pi-natives       | npm lock, 18.14.2                            | Preserve npm license files and the native addon's `THIRD-PARTY-NOTICES.txt`. MIT on pi-ai does not license Bun or JavaScriptCore.                                                                                         |

Both library licenses' §6(a) permit the complete work using the library in
object **and/or source** form, provided modification and relinking are possible.
Accordingly the kit carries Bun, library sources and OMR bridge compilation
inputs, rather than pretending an opaque standalone executable is a relink kit.
It must permit modification for the recipient's own use and reverse engineering
for debugging those modifications. OMR imposes no restriction on those acts for
this runtime. Preserve all applicable upstream terms and disclaimers.

The reconstruction path must support a replacement Bun executable explicitly;
`--target` alone can silently download the upstream runtime instead of using a
locally modified build. The bridge build therefore supplies
`--compile-executable-path`. A working replacement must also be repackaged into
the frozen engine, which extracts its own embedded bridge rather than using an
adjacent arbitrary executable.

## Onboarding composition (Linux)

The composed Linux kit must rebuild the managed worker as well as pi-ai. For Linux builds, set `OMR_WORKER_WHEELS` to the wheelhouse for the build interpreter: the build installs only those wheels, with network access disabled and every package checked against `desktop/s1d1-requirements.lock`. Root-level NumPy PyInstaller symlinks are accepted only when their exact relative target is a regular archive member whose bytes match the hash-pinned NumPy wheel; malformed paths, duplicate archive members, modified targets and unknown root libraries are rejected. The Debian shared-library checks remain in force for every other root library. It includes the exact `requirements-s1d1.txt` versions and their locked build inputs, corresponding source materials and embedded notices; model weights remain outside the kit. Its manifest must cover `desktop_managed.py`, `desktop_deciders.py`, `jev_decider.py`, and the requirements input. Reconstruction and runtime qualification are separate: the extracted kit must be rebuilt and the resulting frozen worker exercised with an isolated HOME and empty PATH. Synthetic loopback pi-ai checks are not local ONNX inference, and neither establishes qualification on another OS or permission to publish.

The composed kit remains blocked until corresponding source provenance for the native worker wheels is established; the generator refuses to emit a manifest in the meantime. `desktop/licenses/worker-pypi-inventory.json` records PyPI wheel and sdist hashes as an inventory only, not as evidence that those sources produced the wheels. PyPI supplies no sdist for the pinned ONNX Runtime or FlatBuffers distributions; native transitive sources and wheel build options still require proof.

## Packaging contract

`desktop/scripts/pi_ai_distribution.py` prepares content-addressed source
materials from `desktop/licenses/pi-ai-sources.lock.json` and the npm lock.
Downloads are verified on every reuse, writes are atomic, and an unavailable or
corrupt required source fails the preparation. WebKit's GitHub source-archive
endpoint returned HTTP 422 during preparation; its fallback is a shallow Git
fetch of the exact revision and deterministic `git archive`, not another branch.
No source history, build output or dependency tree is committed to OMR Git.

Generated notices are small and go into `.sidecar-build/licenses/`, already
included by Tauri's resources mapping. Large source materials live separately in
`.sidecar-build/pi-ai-distribution/`. They must accompany any future distribution,
not merely be linked to a private repository. The manifest binds notices,
compilation inputs, sources, runtime, addon and frozen engine by SHA-256.
A deterministic standalone Linux tar kit contains those exact inputs and engine;
it is a preparation artifact, not an existing installer modification.

## Reconstruction and qualification

1. Install the pinned Python build dependencies with `uv pip install --require-hashes -r desktop/sidecar-requirements.txt` in an isolated environment, and provide the host Node/npm/Rust toolchain.
2. Run `python desktop/scripts/build_sidecar.py`. It installs the npm lock, selects the hash-pinned host Bun executable, prepares source/notice materials and freezes the engine.
3. Run `python desktop/scripts/pi_ai_distribution.py kit --engine desktop/src-tauri/binaries/omr-engine-x86_64-unknown-linux-gnu`. This verifies the inputs again and emits the Linux kit plus manifest.
4. Extract the kit, verify every manifest entry, and run `OMR_TEST_ENGINE=<extracted engine> python -B -m unittest test_pi_ai_packaged -v` with synthetic loopback providers. That test empties runtime PATH and isolates HOME.
5. To replace libraries, unpack the supplied Bun/WebKit/TinyCC sources, retain the upstream patches and follow Bun's `CONTRIBUTING.md`, `scripts/build/README.md` and WebKit's `.github/scripts/lanes.mjs`. Build the modified libraries and Bun with the matching upstream toolchains. Set `OMR_BUN_EXECUTABLE_PATH` to that executable when rebuilding the bridge and frozen engine. This intentionally records a local replacement, not upstream binary provenance. The supplied source tree is `omr-pi-ai/rebuild`; run `OMR_PI_SOURCE_CACHE=<absolute extracted omr-pi-ai/sources> <build-python> omr-pi-ai/rebuild/desktop/scripts/build_sidecar.py` to reuse the accompanying archives. Node/npm, Python, Rust and the native compiler are build-host prerequisites, not user-machine runtime dependencies; `npm ci` still obtains the pinned build tools from npm.

The Linux kit produced here is a **Debian 13 x86_64 build-host preparation**.
It inventories the shared libraries actually copied by PyInstaller (including
CPython, OpenSSL, libffi, expat, bzip2, xz, zlib, zstd, libuuid and GCC runtime
libraries), matches each extracted hash to its local package, and preserves the
package copyright files plus referenced common license texts. GCC 14.2.0-19's
source descriptor, upstream source and Debian patches accompany its runtime
libraries conservatively; the runtime exception is retained, not assumed to
cover every copied library. An unrecognised copied-library origin or another GCC
source version fails kit creation. Ubuntu CI's source-package versions need
native qualification and corresponding pins before its kit is admitted. Bun's
four existing desktop matrix targets have hash-pinned runtime inputs, not
four successful native qualification results. Full upstream source archives
and package notices are intentionally a superset of the compiled code; they do
not mean every file in WebKit or a Debian source package is linked into OMR.

## Library-replacement recipe (not executed here)

Use a separate build directory and the supplied verified archives. Bun requires
LLVM/Clang **23.1.1** and Rust **nightly-2026-09-15** at these pins, plus the prerequisites in
its `CONTRIBUTING.md`. Missing those toolchains is not evidence that a relink
succeeded. After extracting Bun, WebKit and TinyCC into `$work/bun`,
`$work/webkit` and `$work/tinycc` with their archive root removed:

```sh
# Local-deps bypass upstream fetch/patch handling: apply this patch yourself.
(cd "$work/tinycc" && patch -p1 < "$work/bun/patches/tinycc/tcc.h.patch")
# Make your library modifications in those directories and record changes/dates.
(cd "$work/bun" && bun install --frozen-lockfile)
(cd "$work/bun" && GIT_SHA=38afee6c84fcf48c0edb2466aa4b27d287a59c30 \
  BUN_WEBKIT_PATH="$work/webkit" bun scripts/build.ts \
  --profile=release-local --baseline=on --local-deps="tinycc=$work/tinycc")
# Use build/release/bun (or the output named by the upstream build log).
OMR_BUN_EXECUTABLE_PATH="$work/bun/build/release/bun" \
  OMR_PI_SOURCE_CACHE="$kit/sources" \
  "$build_python" "$kit/rebuild/desktop/scripts/build_sidecar.py"
```

`--webkit=local` is selected by `release-local`; without that profile Bun can
reuse a prebuilt JSC. `--local-deps=tinycc=...` prevents the fetch rule from
replacing modified TinyCC sources. Do not run `sync-webkit-source` on a modified
source tree. The source-only archive has no `.git`; `GIT_SHA` supplies its source
identity without inventing a repository history. A modified candidate must carry
its changed corresponding sources too; the unchanged upstream kit is not a
corresponding-source claim for arbitrary future modifications.

Source preparation and an unmodified executable replacement test do **not** prove
that Bun/JavaScriptCore/TinyCC were rebuilt from source. Record that distinct
qualification explicitly. Before public distribution, review the actual notices,
source completeness, replacement route and applicable upstream grant texts;
missing grant or relinking evidence blocks only that distribution, not offline
preparation. No publication, real inference, tag or release is performed here.
