# Landing correction v3 — local candidate

## Authority and provenance

Read the repository's `GOAL.md` and `AGENT_PROMPT_TERRA.md` from the supplied `Open_Model_Router_Correction_v3_Terra.zip`. The archive is a functional/visual reference, not a replacement website. Start from signed landing candidate `c9954673d9da71f93d60bd39c957a7238efa0f2c`. No production deployment, tags or release-triggering push is authorized by this card.

Anonymous EN/FR HTML readback matches `.release-macos/approved-source/site/dist` in `desktop-downloads-v1` byte for byte. That approved-source folder has untracked site files: its Git HEAD alone is not a source identity. Preserve the published content and the newer baseline's manifest validation instead of copying the dirty canonical checkout or `version-landing-t_e413d989`.

The public site offers four real 0.1.0 packages. Their historical input lives at `/srv/omr-private/workspaces/open-model-router/desktop-downloads-v1/.release-macos/input/manifest.json`; it lacks the now-required `prerelease` field. The GitHub draft `desktop-v0.1.0-candidate.1` is a prerelease and names the same source `74695fbbd290f8875dbf569254ede228bdfc4150`. Local preview input may conservatively add `prerelease: true` to a separate copy, with the exact existing binaries, hashes and caveats. It is not a newly qualified release manifest or permission to publish. The newer private 0.2.0 release is not substituted for the public 0.1.0 packages.

## Implementation contract

1. Keep prerendered React, shadcn Button/Card/Badge, self-hosted fonts, indexable EN/FR and native scenario radios. Add one small progressive-enhancement script, not hydration or a second app.
2. Render the same DownloadPanel in hero and availability. One client selection drives both, installation notes and SHA-256. Only staged, hash-verified Download entries provide URLs, version, size, source and qualification. A complete static all-packages list remains usable without JS.
3. Detect OS provisionally using UA hints/platform/UA. Do not infer Apple Silicon from a generic Mac UA. Keep Intel/Silicon selectable, explain how to find the chip, surface Windows/Linux ARM limitations, and prevent late detection from replacing manual choices. Unknown/mobile asks for the target system. Storage is not required. A Windows hint `architecture: x86, bitness: 32` identifies an unsupported x86 target: retain that identity without selecting x64, explain that x64 cannot run on 32-bit Windows, and require an explicit architecture choice for another computer. Selecting or reselecting Windows alone must not bypass this restriction. The generic `Win32` platform alone does not establish a 32-bit OS; an x86/64 hint remains x64.
4. Replace the framed perspective diagram with native nodes and connective SVG. The same four illustrative scenario radios drive model category, path, rationale and inspector. Distinguish scenario examples from actual Economy/Balanced/Quality profiles and direct mode. No API calls, invented model names, scores, savings, failover guarantees or live status.
5. Retain the editorial product story and honest qualification warnings. Keep diagrams readable by reflowing on mobile, native disclosures, keyboard focus, reduced motion, menu dismissal and no-JS fallbacks.

## Fidelity correction

The hero uses direct product language, without qualification-process commentary or a redundant example label. Keep material release and installation limitations in package details without presenting illustrative decisions as live. OS selectors and the four illustrative model categories use distinct recognizable symbols. The routing diagram names intent and compatibility, offers a direct-model choice, and announces selection accessibly without a duplicate visible legend. Examples are tasks rather than modes; categories are not providers. Preserve the source logo without an opaque rectangular field.

Apply the same separation across the whole page in both languages: omit redundant routing-example labels, not just internal disclaimers. Package-specific generation limits must appear beside the selected download and in the static package list; synthetic-only evidence does not establish real generation for any provider, local or remote, or depend on prerelease status. The routing diagram identifies its model categories and routes as illustrative in the visible header, including while the selected route changes. Its routing criteria describe allowed models generically rather than suggesting the visitor's actual configuration. Retain security warnings and genuine availability boundaries.

## Verification plan

Write regression tests first for shared SSR, scenario synchronization and safe detection/selection. Run them red before implementation. Then run canonical tests, type/format checks, build and manifest/payload verification. Browser checks cover both languages at 320, 390, 768, 1024, 1440 and 1920 px; all OS/architecture states, unknown/mobile, late hints, keyboard, menus, no JS, blocked storage, reduced motion and zero outbound calls from the demo. Inspect actual desktop/mobile screenshots. Hash actual downloaded bytes where claimed; HEAD or checksum text alone is not a verified remote binary.

## Release boundary

The deliverable is a signed local candidate with a reproducible build, evidence and limitations, followed by independent review on the same card. Do not alter other worktrees, release data or the public site. A future authorized release must supply an approved manifest, rebuild/verify the exact candidate and pass the existing publication guard immediately before deployment.
