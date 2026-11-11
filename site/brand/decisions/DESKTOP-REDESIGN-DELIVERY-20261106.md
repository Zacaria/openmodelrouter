# Desktop redesign 0.3.1 delivery — 6 November 2026

## Shipped

The existing public landing now distributes the redesigned **0.3.1 macOS Apple Silicon prerelease**. Intel, Windows and Linux packages retain their previous identities and bytes. No personal application installation, connection store or session was replaced during qualification.

- Public origin: `https://open-model-router.vercel.app`.
- Package: `/downloads/0.3.1/omr-0.3.1-macos-arm64.dmg`.
- Package size: **147399172 bytes**.
- SHA-256: `a3c9f45362552936a465d7499f63a8e5392e214cb92154d38d8e09ea0396ae23`.
- Vercel deployment: `APG42DpGsRSEK6ScGFS3HU4BV3ob`; previous ready deployment: `dpl_ESavJ2xxyZ4b8FDHKJJQyWfeXWQZ`.

## Bound source and review

Product: signed commit `fdc83fc014755b4432072fce31b8f6802cd658ed`, tree `b4148b0518ef43b5672b7c01205e82e7142d2647`.

Signing: signed commit `4a68baa408206f9ea71146569434f2fdf3ef593b`, successful Apple workflow `42263670002`. The previous attempt failed after Apple accepted its submissions; its precise failure cause remains unknown. No unchanged retry or trust-check bypass was introduced.

Publication source: signed commit `8f6d62c24f40c954980b484ed68863c3aed5f39f`, accepted tree `96ffc9f4f3907fb3e99a23e0a92601a52082f10a`; offline CI `42269244621` passed. Independent review `deleg_8a88d7f7` accepted the ten-file delta and pinned inputs. The reviewer ran `git write-tree` despite read-only instructions; this scope violation was retained, and the parent independently rechecked unchanged index, blobs, paths and tree before its own signed commit.

Signed tag `desktop-v0.3.1` targets the product commit, not the publication tooling commit. Private GitHub release `436838133` was read back as `draft:false`, `prerelease:true`, `immutable:true`; its four assets match their expected sizes and server digests. Repository visibility was verified private and not changed.

## Executed verification

1. Publication used the existing fail-closed guard, including source/tag/notes identity, immutable-release checks, historical provenance, exact static rebuild, new-path collision refusals and retention checks.
2. All **30 public files**, including **12 download files**, were anonymously downloaded and matched to payload manifest SHA-256 `1efac9d688b594ec89754ae6e08bb7916d1a668e669e13b3ed5d7f72539f59da`. The ten preceding downloads remain byte-identical to retention manifest `7c029fc2f2e72cc39bdfedb0ddb36fc2dfe58b1ab9022f604cd5c62f8399f6ae`.
3. The production-origin browser suite passed: 10 layouts, 40 scenarios, seven detection checks, 82 screenshots, no reported errors or skipped checks. It used sandboxed Brave.
4. Before publication, the exact signed DMG passed app/DMG ticket validation, Developer ID checks, Gatekeeper, four packaged-engine tests and background native AX navigation of the four primary pages in an isolated profile.
5. A second anonymous download directly on the Mac matched the same SHA. Its trust checks and four packaged-engine tests passed; native AppKit/WebCore execution was observed. This post-publication AX repeat was **inconclusive**: no AX windows were exposed, and the console was confirmed locked. This does not establish the lock as the cause. Both owned test attempts were stopped and the image detached; earlier same-byte GUI evidence remains distinct.

## Limits and custody

Real-provider generation was not re-exercised for this release: `generation: synthetic-only`. No claim is made that the image-generation service exposed the requested exact model version; the actual concept was generated through Codex's available `image_gen.imagegen` tool.

Detailed non-secret receipts live under `/srv/omr-private/artifacts/open-model-router/desktop-redesign-20261106/release-0.3.1/`, including `public-readback.json`, `public-browser/report.json`, `github-published-readback.json` and `public-native-evidence.zip` (SHA-256 `97fab4b1b4769f997869cd57c6c2d6feb7da5dcae12708ca11319a173927fd23`). Original pre-publication native qualification is retained separately. These are evidence paths, not current build dependencies.

The independent hero-compat landing work must preserve this release's catalog and all 12 downloads. Its implementation was not changed by this delivery; the publication window was handed back after exact public readback. No new provider session, credential provisioning, purchase or billing-setting change was performed.
