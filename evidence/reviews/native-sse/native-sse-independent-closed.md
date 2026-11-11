# Independent native SSE blocker closure — GO code

2026-10-27. This is a bounded code verdict, not a Mac integration result. Predecessor `native-sse-independent-review.md` SHA-256 `a882424b3b118ca8f89256360f924b34b4446830f244a661cc3f3039d83ef849` remains unchanged.

Candidate HEAD `fbf7dc4b9cb2f8d27226ea6e9bb32d56ae31a1c1`; predecessor tree `1c459e2d302ccf929cea084e75992e951a7cb923`; repaired staged tree `dbbbc6681fda17d5fc387d27f8b96015c835af02`. Index entries compared with all entries of repaired tree without writing Git objects; tracked worktree equals index. `omr.py` SHA-256 `ec9c11ac447bf37eb5919d98e535d4c91b82a0b39e36202030d01fd8b8eabb0c`.

Reviewed exact delta: specification sentence, 15 added runtime lines, 42 added test lines; no other paths. The supported item variants validate SDK-consumed optional types and reject non-null direct item errors before forwarding; null, valid argument strings, and unrelated extensions are preserved. Metadata and enum validations were inspected. This does not claim recursive error scanning or validation of unrelated extension fields.

Fresh independent execution: `PYTHONDONTWRITEBYTECODE=1 python -m unittest -v test_headerless_native.HeaderlessNativeTests.test_item_boundary_rejections_on_route test_headerless_native.HeaderlessNativeTests.test_sdk_item_optional_fields` — 2 tests pass. The first exercises the actual local gateway against a synthetic upstream, independently reproducing numeric namespace and nested item error: each is blocked, sanitized error emitted, marker and completion not forwarded. The second tests optional field types and allowed nulls, argument strings and extensions. No authenticated requests in this review.

The predecessor's 33-test passing scope and its stated security, streaming, cancellation and TLS limitations are inherited, not freshly repeated; this repair is confined to the delta above. The repair author's 35-test result is reported evidence, not an independent rerun. `git diff --cached --check` passed. Mac host proof remains a separate gate.
