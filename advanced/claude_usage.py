"""Claude session snapshots and observable action deltas, never subscription bills."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

# Only cumulative counters: contextWindow/maxOutputTokens are capacities, not usage.
COUNTERS = (
    "inputTokens",
    "outputTokens",
    "cacheReadInputTokens",
    "cacheCreationInputTokens",
    "thinkingTokens",
    "webSearchRequests",
    "costUSD",
)


def _difference(current, previous):
    if (
        isinstance(current, bool)
        or isinstance(previous, bool)
        or not isinstance(current, (int, float))
        or not isinstance(previous, (int, float))
    ):
        return None
    now, before = Decimal(str(current)), Decimal(str(previous))
    if not now.is_finite() or not before.is_finite() or not 0 <= before <= now:
        return None
    difference = now - before
    return (
        int(difference)
        if isinstance(current, int) and isinstance(previous, int)
        else float(difference)
    )


def claude_accounting(result, previous_result=None, *, session_start=False):
    """Caller attests immediate predecessor, or a fresh UUID with session_start.

    Never infer zero origin from the absence of a predecessor. Missing counters,
    changed sessions and counter resets cannot establish an action's consumption.
    modelUsage includes child/auxiliary work that the local `usage` may omit.
    """
    sid = result.get("session_id")
    same_session = (
        bool(sid) and bool(previous_result) and previous_result.get("session_id") == sid
    )
    fresh = bool(sid) and previous_result is None and session_start
    delta = None
    if same_session or fresh:
        previous = (previous_result or {}) if same_session else {}
        models, old_models = result.get("modelUsage"), previous.get("modelUsage")
        model_delta = None
        if isinstance(models, dict) and (fresh or isinstance(old_models, dict)):
            old_models = old_models or {}
            model_delta = {}
            for model in sorted(models.keys() | old_models.keys()):
                current_counts, old_counts = (
                    models.get(model, {}),
                    old_models.get(model, {}),
                )
                model_delta[model] = {
                    key: _difference(
                        current_counts.get(key),
                        0 if fresh or model not in old_models else old_counts.get(key),
                    )
                    for key in COUNTERS
                    if key in current_counts or key in old_counts
                }
        delta = {
            "native_equivalent_usd": _difference(
                result.get("total_cost_usd"),
                0 if fresh else previous.get("total_cost_usd"),
            ),
            "modelUsage": model_delta,
        }
    return {
        "session_snapshot": deepcopy(
            {
                "session_id": sid,
                "total_cost_usd": result.get("total_cost_usd"),
                "modelUsage": result.get("modelUsage"),
            }
        ),
        "action_delta": delta,
        "delta_scope": "immediate_previous_same_session"
        if same_session
        else "attested_session_start"
        if fresh
        else "unknown_baseline",
        "actual_billed_usd": None,
    }
