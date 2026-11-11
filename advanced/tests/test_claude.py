"""Claude stream-json fixtures, not native evidence."""

import unittest

from advanced.claude import ClaudeStrategies
from advanced.codex import StrategyError


def result(**kw):
    return {"type": "result", "session_id": "s", "is_error": False, "usage": None, **kw}


def delegate_events():
    return [
        {
            "type": "assistant",
            "session_id": "s",
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Agent", "id": "a", "input": {}}
                ]
            },
        },
        {
            "type": "user",
            "session_id": "s",
            "message": {
                "content": [
                    {"type": "tool_result", "tool_use_id": "a", "content": "synthetic"}
                ]
            },
        },
        result(
            subagent_stats={
                "spawned": 1,
                "completed": 1,
                "max_depth": 1,
                "spawned_by_subagents": 0,
                "failed": 0,
            }
        ),
    ]


class ClaudeContract(unittest.TestCase):
    def test_accounting_tracks_operations_and_loses_baseline_after_missing_result(self):
        def compact_events(cost):
            return [
                {"type": "system", "subtype": "compact_boundary", "session_id": "s"},
                result(local_command="compact", total_cost_usd=cost, modelUsage={}),
            ]

        batches = iter(
            [
                compact_events(0.1),
                compact_events(0.3),
                [],
                compact_events(0.7),
                compact_events(0.9),
            ]
        )
        adapter = ClaudeStrategies(lambda *_: next(batches), "s", session_start=True)
        self.assertEqual(
            adapter.compact()["accounting"]["action_delta"]["native_equivalent_usd"],
            0.1,
        )
        self.assertEqual(
            adapter.compact()["accounting"]["action_delta"]["native_equivalent_usd"],
            0.2,
        )
        with self.assertRaises(StrategyError):
            adapter.compact()
        self.assertIsNone(adapter.compact()["accounting"]["action_delta"])
        self.assertEqual(
            adapter.compact()["accounting"]["action_delta"]["native_equivalent_usd"],
            0.2,
        )

    def test_compact_uses_previous_resume_snapshot_not_local_usage_zero(self):
        previous = result(
            total_cost_usd=0.003768,
            modelUsage={"haiku": {"inputTokens": 448, "outputTokens": 664}},
        )
        current = result(
            local_command="compact",
            total_cost_usd=0.013443,
            modelUsage={"haiku": {"inputTokens": 3008, "outputTokens": 2087}},
            usage={"input_tokens": 0},
        )
        events = [
            {"type": "system", "subtype": "compact_boundary", "session_id": "s"},
            current,
        ]
        r = ClaudeStrategies(lambda *_: events, "s", previous_result=previous).compact()
        self.assertEqual(
            r["accounting"]["action_delta"]["native_equivalent_usd"], 0.009675
        )
        self.assertEqual(
            r["accounting"]["action_delta"]["modelUsage"]["haiku"]["inputTokens"], 2560
        )
        self.assertTrue(r["auxiliary_equivalent_cost_known"])
        self.assertIsNone(r["usage"])

    def test_compact_requires_boundary_and_local_result_same_session(self):
        events = [
            {
                "type": "system",
                "subtype": "compact_boundary",
                "session_id": "s",
                "compact_metadata": {
                    "trigger": "manual",
                    "pre_tokens": 100,
                    "post_tokens": 120,
                },
            },
            result(local_command="compact"),
        ]
        calls = []

        def execute(sid, prompt):
            calls.append((sid, prompt))
            return events

        r = ClaudeStrategies(execute, "s").compact()
        self.assertEqual(r["status"], "completed")
        self.assertEqual(calls, [("s", "/compact")])
        self.assertFalse(r["context_reduced"])

    def test_compaction_native_zero_is_not_known_auxiliary_usage(self):
        events = [
            {
                "type": "system",
                "subtype": "compact_boundary",
                "session_id": "s",
                "compact_metadata": {},
            },
            result(
                local_command="compact", usage={"input_tokens": 0, "output_tokens": 0}
            ),
        ]
        self.assertIsNone(ClaudeStrategies(lambda *_: events, "s").compact()["usage"])

    def test_zero_exit_or_not_enough_messages_is_not_compaction(self):
        for events in [
            [result(local_command="compact", result="Not enough messages to compact.")],
            [
                {
                    "type": "system",
                    "subtype": "compact_boundary",
                    "session_id": "other",
                },
                result(local_command="compact"),
            ],
        ]:
            with self.assertRaises(StrategyError):
                ClaudeStrategies(lambda *_, events=events: events, "s").compact()

    def test_native_agent_tool_pair_and_terminal_child_stats(self):
        self.assertEqual(
            ClaudeStrategies(lambda *_: delegate_events(), "s").delegate("g", "ctx")[
                "status"
            ],
            "completed",
        )
        for change in ["missing_result", "recursive", "error"]:
            events = delegate_events()
            if change == "missing_result":
                events.pop(1)
            elif change == "recursive":
                events[-1]["subagent_stats"]["spawned_by_subagents"] = 1
            else:
                events[-1]["is_error"] = True
            with self.subTest(change=change), self.assertRaises(StrategyError):
                ClaudeStrategies(lambda *_, events=events: events, "s").delegate(
                    "g", "ctx"
                )


if __name__ == "__main__":
    unittest.main()
