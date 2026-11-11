# Candidate.2 — bounded content and privacy publication gate

**GO for the stated private prerelease only**, subject to using the exact assets below and retaining private repository/release visibility. This is a bounded content/privacy review, not an assurance that every possible secret or sensitive fact is absent, a professional sign-off, or acceptance of the product. No publication was performed.

## Exact subject

- Archive `build-one/open-model-router-0.1.0-candidate.2.tar.gz`: SHA-256 `3a8ffe5f2557903cd3132f938c0df8a9a118772aa339b6f8ea17ad3637f8c02c`.
- Manifest `build-one/manifest.json`: SHA-256 `108c7035bb8adb442af311e3c0695e37965d7f8351f2aba668e177f7e03e205f`.
- Proposed `publication-notes.md`: SHA-256 `34a07ebd08e6fc07d12806d39950eb7f343e64071a67e6da2d40f7e0ce0dca6c`.
- Source commit `7e25c6e7e6547fb9d3bf1f2f1d71602dd3950f3b`, tree `dfd45901284f6948d7d86d23b5a38fbb9773afb1`. SHA256SUMS SHA-256 `34cb4bcd32fafa7f0b5c3e581071c3d9d8f782021525e327038a4d44a30eefe7`.

## Coverage and findings

`coverage.json` records all 351 member paths, member hashes, types and the actual inspection methods. Content of every member was decoded or inspected as binary: 348 UTF-8 text files, one mixed-encoding console text file, and two PNGs. The text screening covered entire decoded content for common private-key, provider-token, JWT, bearer, credential-assignment and email patterns; it is a heuristic, not semantic proof. Structured JSON was parsed where applicable; JSONL was parsed line by line, with three Hermes files identified as mixed output rather than silently treated as complete JSONL. Evidence families and structured field schema were reviewed alongside their provenance reports, including the campaign study and VM replay reports. The campaign specifies synthetic cases; the VM reports identify isolated test sessions and synthetic fixtures. Structured credential-named values observed in these records are source-status metadata, not API keys. Session UUIDs are identifiers of isolated test runs, not by themselves credentials. Synthetic test keys and URL examples are not actual credentials. Two email-pattern hits were reviewed in context: a test Git identity and a URL-userinfo validation case; neither is a customer address or credential. Values are not reproduced here.

Both exact archive PNGs were visually reviewed for private material and checked as PNG chunks, including CRCs and absence of text/EXIF chunks or trailing bytes. They show the project landing prototype; no private conversation, credentials or customer data were visible. They are separately bound to their member hashes in `coverage.json`. The older landing review concerned different hash-pinned captures, so its visual conclusion was not substituted for inspection of these exact PNGs.

No actual credential, private conversation or customer record was identified in the inspected material. This conclusion relies on the stated programmatic inspection, targeted semantic/provenance review and visual inspection, not on regex alone; it is not a manual line-by-line semantic reading of every source file or a universal absence guarantee. Internal paths, technical host observations and historical evidence remain present; this gate is explicitly for an already-authorized private repository and private release, not for public disclosure.

## Publication notes

The proposed notes correctly identify a test prerelease, immutable candidate commit/tree/archive, the offline certification figures, and the continuing limitations: historical evidence is not current candidate acceptance, oh-my-pi Mac is not qualified, four-host acceptance and final release remain open, and no general savings are established. The download command names the private repository and intended tag; the certifier command pins the full commit and chooses an external scratch directory. Run the commands from the root of a separately trusted checkout containing that commit and the matching `build_release.py`, after the release/assets actually exist, with GitHub access already authorized. Obtain and compare the displayed archive hash via an independent trusted channel: the bundle's manifest/checksum alone does not authenticate itself. The notes are proposed text, not evidence that the release or tag exists. The separate `release-notes.md` is a build report and was not reviewed as publication text.

## Boundaries

Read `GOAL.md` and `INSTALL.md`. Relied on the parent's separately reported all-351 byte/mode/member comparison and the existing offline certification report (62 root tests, 9 synthetic adapter tests and landing checks); did not repeat them. Existing source, CI and runtime reviews were not reopened; no host, authentication, provider, model, network or publication action was performed. Final acceptance requires the remaining real four-host work on the delivered version; this private prerelease gate does not close it.
