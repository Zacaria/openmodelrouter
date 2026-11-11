# Production landing readback — 27 October 2026

Scope: read-only verification of the existing prototype landing, not product, release, host qualification or GOAL completion. GOAL.md and the static-site-verification guidance were read. No deployment, source edit, Git or remote mutation, external content mirroring, private data submission or browser session was performed.

## Identity and live HTTP

- Requested and effective URL: https://open-model-router.vercel.app/
- Anonymous bounded GET (`curl -sS -L --max-time 25`): HTTP 200, `text/html; charset=utf-8`, 11,230 bytes, observed 2026-10-27 approximately 06:29 UTC.
- Public `public-index.html`, canonical tracked `/home/operator/repos/open-model-router/site/index.html` (the source named by `tests/test_landing.py`), and `git show HEAD:site/index.html` all have SHA-256 `3ab910b3d6ce0e333037976bc4c773f1fde2af0d927c6683cbe4a5d2a440a054`. `cmp` of live and working-tree source passed. HEAD at check: `63e517c25caa503b02eb38b2be994f8e2c32e142`; indexed blob `b2d9607f7f5cc6f86d24f12cbf3709fcec08a89f`. Source/test had no working-tree changes at check.
- This is an HTTP byte identity, not new visual proof. The copied file is only the requested site's public HTML, not third-party content.

## Minimal checks and wording

- `PYTHONDONTWRITEBYTECODE=1 python3 tests/test_landing.py`: PASS; eight fragment links, six unique IDs, French language and required prototype disclosures. Separate parse of all href/src/action/formaction/poster/srcset/data attributes found only the eight fragment anchors; all resolve. There are **zero external destinations**, so no external destination GET exists to perform; the bounded GET above checked the public origin.
- Read the actual copy: calls itself a local prototype; private repository; comparator uses simulated data; four targeted integrations remain to validate; provider-dependent route and effort; no compatibility guaranteed; no proven savings or subscription compatibility; calculated equivalent value is not a bill. No unsupported claim of savings or all-host qualification found. Existing wording is conservative and may lag later product work; it is not evidence that the product has passed its GOAL.

## Reused desktop/mobile browser evidence — not a new session

- The existing `evidence/landing/deployment.json` binds the same exact URL and HTML SHA-256 to its earlier READY deployment and screenshots. Its recorded desktop SHA-256 `32149af5745aa341a918041a361e60c79e42e574d53d775a6094b7e3d5b44171` and mobile SHA-256 `3a34271cb4b7083d3fe719a38ee108972ecc06eeb4d6397edbdfc17b9a9d85bf` match the currently tracked image files. Existing `evidence/landing/browser.json` records desktop width 1440 and all eight anchors valid. This evidence is explicitly reused because live bytes are identical; no fresh visual or browser test is claimed.
- The existing `evidence/landing/review.md` records earlier desktop/mobile screenshot review and additional width and fragment checks on the same digest; it notes that at 320px a horizontally scrollable host `pre` has no visible scroll cue, though host names and the qualification also appear in preceding prose. That reservation remains. Its cited earlier scratch captures were not revalidated here. This is not an exhaustive accessibility, browser compatibility or design audit.

## Remaining boundary

HTTP availability can change and past browser evidence does not establish present rendering under every environment. OMP remains blocked per task context; do not call the GOAL complete. The release-evidence packet and canonical documentation are owned by other workers. Unrelated concurrent working-tree changes were left untouched.
