# Candidate.3 private archive content/privacy review — GO (bounded)

**GO only for content of the exact private prerelease archive identified below, in the existing authorized private GitHub repository/release.** This is not permission to publish to a public landing page, social media, or another public destination; it is not a functional-delivery, host-qualification, final-release, or GOAL acceptance verdict. No publication was performed. This bounded assessment is not a guarantee that every possible sensitive fact or secret is absent.

## Exact subject and integrity

- Archive `build1/open-model-router-0.1.0-candidate.3.tar.gz`: SHA-256 `44328fc6175cd1ac82527db0fd0b5d0788e381e1973643f55b082069261170bc`.
- `build1/manifest.json`: SHA-256 `cec82d993febb274152d1c93326758a1e56804118edc82856311e9f0b7e8f287`.
- Commit `63e517c25caa503b02eb38b2be994f8e2c32e142`, tree `f6d12bc5532ca1a132edcaf009f0cf73c21f750a`. `git verify-commit` succeeded against the locally configured trusted signing identity.
- Independently compared all 458 regular tar members, names, modes, and full bytes against both manifest and Git tree blobs; no duplicate, missing, extra, unsafe path, type, mode, or byte mismatch. The manifest commit/tree and archive digest match. Also verified the candidate.2 archive and manifest against its Git tree and each of the 351 entries in the existing coverage record. Candidate.3 differs by exactly **107 added, 4 modified, 0 removed**; the other 347 members are unchanged in bytes and mode.

## Exact coverage reconciliation

`coverage.json` enumerates every one of the 458 member names, modes, byte lengths, SHA-256 hashes, delta classification, and review reference(s). The disjoint primary coverage assignment is:

| Members | Coverage and byte-binding |
|---:|---|
| 347 | Unchanged candidate.2 entries, matched to the candidate.2 archive and per-member privacy coverage. This includes its two previously visually inspected exact PNGs. |
| 17 | Thirteen `evidence/native/codex-validated/` files and four `evidence/reviews/native-sse/` files: exact blob and mode of the tree reviewed in `native-sse-evidence-review.md`. |
| 92 | `.gitattributes`, `DELIVERY-STATUS.md`, 81 `evidence/native/host-replay-7e25c6e7/` paths, and nine `evidence/release/candidate.2/` paths: exact blob and mode of the tree reviewed in `host-evidence-preservation-review.md`. |
| 2 | Modified `omr.py` and `test_deadlines.py`: candidate.2 reviewed baseline is byte-identical to the deadline review's base for these paths; the final files match the independently reviewed deadline tree. `deadline-disconnect-independent-review.md` reviewed all added lines for security and `deadline-integration-result.md` reconciled the final composition. |

**Uncovered members: 0.** Consequently no new semantic or image review was necessary; unchanged semantic reviews and host runs were not repeated. The earlier reviews are bounded and use a combination of content screening and semantic/provenance review, not a claim of manual line-by-line reading of all source. Their explicitly identified isolated synthetic fixture/session IDs are identifiers, not inherently credentials; they are distinguished from authentication tokens, private conversations and customer data. Those reviews found no actual credentials, private conversation or customer data in their respective reviewed scopes. Internal filesystem paths, technical host observations and historical evidence remain in the archive and are suitable only for the stated private scope; no public-disclosure conclusion follows.

## Remaining boundaries

Candidate.2 privacy notes and release records are historical evidence, not a current publication authorization. Parent separately reported successful CI run `40459266741` for the exact commit, installed-archive tests (114 passed, 1 skipped), and landing checks; these were not rerun or independently verified in this privacy review. Final Hermes cancellation remains inconclusive and oh-my-pi remains unqualified. This GO does not erase those limitations or establish any of the cumulative delivery requirements in `GOAL.md`.

No hosts, provider/authentication services, or publication endpoints were contacted. No archive, manifest, Git source, index, refs, candidate.2 artifacts, or historical evidence was modified. Only this report and `coverage.json` were created in the requested private review directory.
