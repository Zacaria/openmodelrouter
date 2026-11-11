# External model ranking

## Accepted behavior

Model capacity must come from published external benchmark data, not an LLM guessing a model's strength. Show the score, benchmark name/version, retrieval time and matching model identity. Missing or ambiguous matches remain unranked. A manual level always takes precedence and can be reset to benchmark mode.

Refresh after the selected model list changes, debounced by 750 ms. Also offer an explicit refresh action. Fetch the complete external catalogue without transmitting connection names, user model lists, prompts or conversations. A daily native cache avoids repeated network requests during catalogue edits; explicit refresh bypasses cache freshness, not quota backoff. Retain the last valid cache when a refresh fails and show the failure and data age.

Fetch every documented `pagination.page` before computing catalogue-wide levels. Reject missing pages, inconsistent versions/page counts and duplicate identities; never publish a first-page-only ranking. Coalesce a list change during an in-flight refresh into one trailing refresh. Sort the visible ranking by external score, independently of manual routing levels.

## Source boundary

Use Artificial Analysis's documented Free endpoint, `GET https://artificialanalysis.ai/api/v2/language/models/free`, with a user-supplied `x-api-key` held in the OS credential store. Do not use the Pro-only `/language/models` endpoint or silently upgrade access. API responses and keys must not be bundled into releases or published. Attribute Artificial Analysis in the ranking panel. Reference: https://artificialanalysis.ai/data-api/docs and https://artificialanalysis.ai/data-api (checked 2026-11-05).

The documented Free tier is for internal use, with attribution, and currently allows 100 requests per 24-hour window. Respect returned quota headers and `Retry-After`; never retry aggressively. A missing key is a visible setup state, not permission to synthesize scores. Live validation requires a key entered through the app, not chat.

## Routing and manual edits

The external score is authoritative only for that benchmark/version/model configuration. OMR's 1/2/3 levels are a separate routing policy: divide the scored source catalogue into thirds, using midranks for ties. Show that conversion; do not present levels as benchmark-published ratings or a guarantee on a user's tasks.

Existing declared ratings remain manual. Newly added models start in benchmark mode; a missing score cannot silently become level 1. Direct routes stay usable when a model is unranked, but automatic profiles must not select an unranked model. Never loosen profile quality floors to make a request pass.

Keep model identifiers unchanged. Match exact source identity or an explicit operator-selected match; do not infer that a family, parameter size, quantization, reasoning setting or similarly named release has an equivalent benchmark score. Changing an upstream identifier clears its explicit benchmark association and derived level; the native save boundary rejects an unchanged old association on a renamed model. A fresh explicit association requires saving the new identity first.

Pages containing only unscored models remain valid; require at least one score only after collecting the complete catalogue. Exhausted quota on a successful response prevents further pages and forced refreshes until the reset time. If the final page exhausts quota, retain the complete fresh catalogue with that backoff.

Derived levels use the existing serialized configuration autosave. Late source responses must not overwrite recent manual corrections, removed models or another configuration revision. A source refresh must not start generation, invoke the task-complexity decider, modify provider secrets or reset a conversation.

## Verification

Check incomplete/invalid responses, duplicate identities, non-finite scores, equal-score ties, missing matches, cache failures and quota backoff. Exercise debounced list edits, manual refresh, manual overrides and restoring benchmark mode. Qualify the native credential boundary and real source separately from synthetic parser/UI tests.
