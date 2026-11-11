# Third-party notices

## Vercel AI SDK

`ai` 7.0.162 and `@ai-sdk/react` 4.0.166 are exact-pinned, Apache-2.0 Vercel packages, Copyright 2023 Vercel, Inc. Chat uses their native `ChatTransport` and `useChat` APIs. `scripts/build_notices.mjs` retains their shipped copyright/license headers and transitive dependency notices, and appends the complete terms from `licenses/Apache-2.0.txt` (standard text, identical to Debian's `/usr/share/common-licenses/Apache-2.0`). These notices ship in the existing native inventory; no hosted Vercel service or API key is required.

## tauri-ui / create-tauri-ui

Source: https://github.com/agmmnn/tauri-ui
Revision inspected: `8eb86d894c19b6df04ff883ab28b412b1e5f23ea` (create-tauri-ui 1.2.0).
Package manifest declares MIT, author agmmnn. Only the `flash-prevention.ts` page-load hook and hidden initial window configuration are adapted in `src-tauri/src/main.rs` and `tauri.conf.json`. The Vite adapter and scroll-container battery were inspected; no CLI, template dashboard, release workflow or debug panel is executed or bundled. Initial repository inspection did not expose a standalone LICENSE file; the MIT grant below preserves the package's declared attribution.

Copyright (c) agmmnn

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## shadcn/ui

The local Button/Field/Card/Dialog/Switch compositions follow shadcn/ui's editable source approach, backed by pinned Radix primitives and class-variance-authority. Styling is specific to OMR; no registry code generation runs during builds. shadcn/ui is MIT, Copyright (c) 2023 shadcn. The MIT terms above apply to adapted compositions with that attribution.

React, Radix, Tauri, keyring and the remaining build dependencies retain their respective licenses in the package registries. `package-lock.json`, `Cargo.lock` and `sidecar-requirements.txt` record the exact dependencies. The frozen sidecar bundles CPython (PSF license) and the PyInstaller bootloader (GPL with its bootloader distribution exception); it does not change the application source license. Release packaging must retain these notices and the dependency license files provided by the toolchains.

## macOS ARM64 0.3.0 notice inventory

The macOS build collects complete notice texts from the installed locked Python
packages, including ONNX Runtime's package-local LICENSE and ThirdPartyNotices.
`PYTHON-NOTICES.json` records their exact bytes. The FlatBuffers and tokenizers
wheels omit license files: `licenses/sidecar-notices.lock.json` binds reviewed
upstream texts to those exact versions. The tokenizers supplement includes its
Apache license and a conservative Cargo.lock notice inventory (including unused
build/dev/other-target packages); `Tokenizers-0.23.3-sources.json` records crate
checksums and paths. The three source archives without standalone texts are
r-efi 5.3.0/6.0.0 (UEFI-only) and defmt-parser 1.0.0 (optional embedded logging
build tooling); they are not claimed as macOS wheel components.

`MACOS-LIBRARY-NOTICES.json` maps the libraries actually selected by PyInstaller
to the build host's CPython, OpenSSL, liblzma and mpdecimal texts and SQLite's
public-domain header. These are macOS inputs, not evidence about Linux or Windows.
Full texts and inventories ship in the frozen engine and app resources. The
installed PyInstaller build's COPYING text is retained as
`licenses/dependencies/PyInstaller-BUILD-COPYING.txt`; the separately maintained
runtime notice remains `licenses/runtime/PyInstaller-COPYING.txt`. Their bytes
need not be identical. The builder removes only the obsolete generated
`dependencies/PyInstaller-COPYING.txt` when reusing a build directory, so the
package verifier can still require exactly one runtime notice by that name.

`RUST-NOTICES.json` covers the resolved macOS Cargo graph, conservatively
including build dependencies, plus the installed Rust standard-library notices.
Missing crate-level files use the original repository notices at the revision
recorded in each crate's `.cargo_vcs_info.json`; their complete texts are in
`MacOS-Rust-Upstream-NOTICES.txt`. The selectors MPL-2.0 grant and full terms are
retained; the inventory gives direct source archive URLs for the unmodified
covered code. `react-remove-scroll-bar` 2.3.8 declares MIT without shipping a
separate grant text; its package attribution and pinned standard MIT terms are
included explicitly, without claiming recovery of a missing upstream grant.

## pi-ai provider runtime

`@oh-my-pi/pi-ai` 18.14.2 and its pinned OhMyPi dependencies are MIT, Copyright Stencil Labs, Inc. and the upstream contributors. Their complete shipped license texts and the native addon's third-party notices are collected into `licenses/dependencies/NPM-LICENSES.txt` at build time. Source and package integrity: `provider-runtime/package-lock.json`; upstream: https://github.com/can1357/oh-my-pi.

The compiled bridge includes Bun 1.4.4 (commit `38afee6c84fcf48c0edb2466aa4b27d287a59c30`). Its upstream inventory is retained as `licenses/runtime/Bun-LICENSE.md`; that declaration is not a substitute for the dependency license texts. `PI-AI-NOTICES.txt` pairs Bun's MIT declaration with the complete standard MIT terms from the hash-pinned SPDX source named in `licenses/pi-ai-sources.lock.json`. Standard-template copyright placeholders are not asserted as Bun attribution. Actual upstream block/line-comment grants, including Bun's vendored and Rust source headers outside WebKit, are preserved verbatim with source paths. JavaScriptCore's pinned `COPYING.LIB` contains GNU Library GPL v2, while TinyCC supplies LGPL 2.1; individual file grants remain authoritative. The build embeds these generated notices and produces `PI-AI-MATERIALS.json` binding the corresponding source kit. The source archives, patches, bridge inputs and replacement-executable build path are described in `PI-AI-DISTRIBUTION.md`. They must accompany any future distribution. This preparation is not public-release approval; no library source rebuild or other-OS qualification is implied.
