"""Cumulative Claude resume counters: synthetic fixtures, no provider calls."""

import unittest

from advanced.claude_usage import claude_accounting


def snapshot(cost, inputs, outputs, sid="s", **counts):
    return {
        "session_id": sid,
        "total_cost_usd": cost,
        "modelUsage": {
            "haiku": {
                "inputTokens": inputs,
                "outputTokens": outputs,
                "costUSD": cost,
                "thinkingTokens": 0,
                "contextWindow": 200000,
                **counts,
            }
        },
    }


class ClaudeAccounting(unittest.TestCase):
    def test_multiresume_compaction_is_observable_despite_local_zero(self):
        results = [
            snapshot(0.003768, 448, 664),
            snapshot(0.013443, 3008, 2087),
            snapshot(0.015775, 4295, 2296),
            snapshot(0.036201, 8249, 3200),
        ]
        results[1]["usage"] = {"input_tokens": 0, "output_tokens": 0}
        previous = None
        rows = []
        for i, result in enumerate(results):
            row = claude_accounting(result, previous, session_start=i == 0)
            rows.append(row)
            previous = result
        costs = [r["action_delta"]["native_equivalent_usd"] for r in rows]
        self.assertAlmostEqual(sum(costs), 0.036201)
        self.assertEqual(costs, [0.003768, 0.009675, 0.002332, 0.020426])
        compact = rows[1]["action_delta"]["modelUsage"]["haiku"]
        self.assertEqual(compact["inputTokens"], 2560)
        self.assertEqual(compact["outputTokens"], 1423)
        self.assertNotIn("contextWindow", compact)
        self.assertEqual(
            rows[1]["session_snapshot"]["modelUsage"], results[1]["modelUsage"]
        )
        self.assertTrue(all(r["actual_billed_usd"] is None for r in rows))

    def test_no_implicit_zero_origin_or_cross_session_subtraction(self):
        result = snapshot(0.1, 10, 20)
        for previous in (None, snapshot(0.05, 5, 10, sid="other"), {}):
            row = claude_accounting(result, previous)
            self.assertIsNone(row["action_delta"])
        self.assertIsNone(
            claude_accounting({"total_cost_usd": 0.1}, session_start=True)[
                "action_delta"
            ]
        )

    def test_missing_reset_and_new_model_counters_are_not_invented(self):
        before = snapshot(0.1, 10, 20)
        after = snapshot(0.05, 3, 25)
        after["modelUsage"]["haiku"].pop("thinkingTokens")
        after["modelUsage"]["other"] = {"inputTokens": 7, "costUSD": 0.01}
        delta = claude_accounting(after, before)["action_delta"]
        self.assertIsNone(delta["native_equivalent_usd"])
        self.assertIsNone(delta["modelUsage"]["haiku"]["inputTokens"])
        self.assertEqual(delta["modelUsage"]["haiku"]["outputTokens"], 5)
        self.assertIsNone(delta["modelUsage"]["haiku"]["thinkingTokens"])
        self.assertEqual(delta["modelUsage"]["other"]["inputTokens"], 7)
        missing = claude_accounting({"session_id": "s"}, before)["action_delta"]
        self.assertIsNone(missing["native_equivalent_usd"])
        self.assertIsNone(missing["modelUsage"])


if __name__ == "__main__":
    unittest.main()
