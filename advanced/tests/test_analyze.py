import unittest

from advanced.analyze import claude_cases, codex_arm


class Analysis(unittest.TestCase):
    def test_claude_resumes_report_deltas_not_cumulative_costs(self):
        cases = []
        for name, cost, inputs, outputs in [
            ("seed", 0.003768, 448, 664),
            ("compact", 0.013443, 3008, 2087),
            ("recall", 0.015775, 4295, 2296),
            ("delegate", 0.036201, 8249, 3200),
        ]:
            cases.append(
                {
                    "case": name,
                    "events": [
                        {
                            "type": "result",
                            "session_id": "s",
                            "total_cost_usd": cost,
                            "modelUsage": {
                                "haiku": {
                                    "inputTokens": inputs,
                                    "outputTokens": outputs,
                                }
                            },
                            "usage": {"input_tokens": 0},
                        }
                    ],
                }
            )
        rows = claude_cases(cases, session_start=True)
        costs = [r["accounting"]["action_delta"]["native_equivalent_usd"] for r in rows]
        self.assertEqual(costs, [0.003768, 0.009675, 0.002332, 0.020426])
        self.assertAlmostEqual(sum(costs), 0.036201)
        self.assertTrue(all(r["full_cost_usd"] is None for r in rows))
        self.assertIsNone(claude_cases(cases)[0]["accounting"]["action_delta"])
        cases.insert(2, {"case": "missing", "events": []})
        self.assertIsNone(
            claude_cases(cases, session_start=True)[3]["accounting"]["action_delta"]
        )

    def test_native_snapshots_not_summed_or_missing_cost_zeroed(self):
        event = {
            "method": "thread/tokenUsage/updated",
            "params": {"threadId": "t", "tokenUsage": {"total": {"totalTokens": 100}}},
        }
        action = {
            "elapsed_seconds": 1,
            "items": [{"type": "agentMessage", "text": "RAPPORT: blue-otter-73 HEAVY"}],
        }
        arm = {
            "arm": "compact_switch",
            "status": "completed",
            "actions": [action],
            "native_events": [event, event],
        }
        row = codex_arm(arm)
        self.assertEqual(row["thread_snapshots"]["t"]["totalTokens"], 100)
        self.assertIsNone(row["full_cost_usd"])
        self.assertFalse(row["full_token_cost_known"])
        self.assertTrue(row["answer_ok"])

    def test_native_delegation_is_not_instruction_adherence(self):
        cases = [
            {
                "case": "delegate",
                "exit_code": 0,
                "events": [
                    {
                        "type": "result",
                        "is_error": False,
                        "result": "blue-otter-73 HEAVY",
                        "subagent_stats": {"spawned": 1, "completed": 1},
                        "usage": {},
                    }
                ],
            }
        ]
        row = claude_cases(cases)[0]
        self.assertTrue(row["fixture_and_boundary_ok"])
        self.assertFalse(row["instruction_prefix_ok"])


if __name__ == "__main__":
    unittest.main()
