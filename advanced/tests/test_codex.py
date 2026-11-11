"""Contract fixtures, not native integration evidence."""

import unittest
from collections import deque

from advanced.codex import CodexStrategies, StrategyError


def event(method, thread="t", turn_id="u", **kw):
    return {"method": method, "params": {"threadId": thread, "turnId": turn_id, **kw}}


def item(item_type, **kw):
    return event("item/completed", item={"id": "i", "type": item_type, **kw})


def done(status="completed"):
    return event("turn/completed", turn={"id": "u", "status": status, "error": None})


def collab(tool, ids, states=None):
    return item(
        "collabAgentToolCall",
        tool=tool,
        status="completed",
        senderThreadId="t",
        receiverThreadIds=ids,
        agentsStates=states or {},
        model="model-child",
    )


class RPC:
    def __init__(self, events, response=None):
        self.events = deque(events)
        self.calls = []
        self.response = response if response is not None else {"turn": {"id": "u"}}

    def request(self, method, params):
        self.calls.append((method, params))
        return self.response

    def wait(self, predicate, timeout):
        while self.events:
            e = self.events.popleft()
            if predicate(e):
                return e
        raise TimeoutError("fixture exhausted")


class CodexContract(unittest.TestCase):
    def test_compact_requires_item_and_successful_matching_turn(self):
        r = RPC(
            [
                event(
                    "item/completed", thread="other", item={"type": "contextCompaction"}
                ),
                event("turn/started", turn={"id": "u"}),
                item("contextCompaction"),
                done(),
            ],
            {},
        )
        result = CodexStrategies(r).compact("t")
        self.assertEqual(r.calls, [("thread/compact/start", {"threadId": "t"})])
        self.assertEqual(result["status"], "completed")
        self.assertIsNone(result["usage"])

    def test_acknowledgement_and_text_are_not_compaction(self):
        r = RPC(
            [
                event("turn/started", turn={"id": "u"}),
                item("agentMessage", text="compacted"),
                done(),
            ],
            {},
        )
        with self.assertRaisesRegex(StrategyError, "compaction"):
            CodexStrategies(r).compact("t")

    def test_compaction_rejects_failure_after_completed_item(self):
        r = RPC(
            [
                event("turn/started", turn={"id": "u"}),
                item("contextCompaction"),
                done("failed"),
            ],
            {},
        )
        with self.assertRaises(StrategyError):
            CodexStrategies(r).compact("t")

    def test_unrelated_turn_cannot_complete(self):
        r = RPC(
            [event("turn/completed", turn={"id": "old", "status": "completed"}), done()]
        )
        self.assertEqual(CodexStrategies(r).turn("t", "synthetic")["turn_id"], "u")
        self.assertEqual(
            r.calls[0][1],
            {"threadId": "t", "input": [{"type": "text", "text": "synthetic"}]},
        )

    def test_switch_only_sets_model_no_permissions_or_history_override(self):
        r = RPC([done()])
        CodexStrategies(r).turn("t", "synthetic", model="other")
        self.assertEqual(set(r.calls[0][1]), {"threadId", "input", "model"})

    def test_usage_last_snapshot_not_sum(self):
        usage = {"total": {"totalTokens": 100}, "last": {"totalTokens": 40}}
        r = RPC(
            [
                event("thread/tokenUsage/updated", tokenUsage=usage),
                event("thread/tokenUsage/updated", tokenUsage=usage),
                done(),
            ]
        )
        self.assertEqual(CodexStrategies(r).turn("t", "x")["usage"], usage)

    def test_native_delegation_requires_spawn_and_completed_child(self):
        r = RPC(
            [
                collab("spawnAgent", ["child"]),
                collab(
                    "wait",
                    ["child"],
                    {"child": {"status": "completed", "message": "answer"}},
                ),
                done(),
            ]
        )
        result = CodexStrategies(r).delegate("t", "goal", "untrusted input")
        self.assertEqual(
            result["children"],
            {"child": {"model": "model-child", "status": "completed"}},
        )
        self.assertNotIn("sandboxPolicy", r.calls[0][1])

    def test_prose_is_not_delegation(self):
        r = RPC([item("agentMessage", text="I delegated"), done()])
        with self.assertRaisesRegex(StrategyError, "delegation"):
            CodexStrategies(r).delegate("t", "goal", "ctx")

    def test_spawn_without_completion_or_wrong_child_is_not_success(self):
        for states in [
            {},
            {"different": {"status": "completed"}},
            {"child": {"status": "errored"}},
        ]:
            with self.subTest(states=states):
                r = RPC(
                    [
                        collab("spawnAgent", ["child"]),
                        collab("wait", ["child"], states),
                        done(),
                    ]
                )
                with self.assertRaises(StrategyError):
                    CodexStrategies(r).delegate("t", "goal", "ctx")

    def test_native_v2_activity_requires_same_child_started_and_completed(self):
        r = RPC(
            [
                item("subAgentActivity", kind="started", agentThreadId="child"),
                item("subAgentActivity", kind="completed", agentThreadId="child"),
                done(),
            ]
        )
        self.assertEqual(
            CodexStrategies(r).delegate("t", "goal", "ctx")["children"],
            {"child": {"model": None, "status": "completed"}},
        )
        for kind in ["interrupted", "errored"]:
            r = RPC(
                [
                    item("subAgentActivity", kind="started", agentThreadId="child"),
                    item("subAgentActivity", kind=kind, agentThreadId="child"),
                    done(),
                ]
            )
            with self.assertRaises(StrategyError):
                CodexStrategies(r).delegate("t", "goal", "ctx")

    def test_activity_completion_without_start_or_wrong_child_rejected(self):
        for events in [
            [item("subAgentActivity", kind="completed", agentThreadId="child"), done()],
            [
                item("subAgentActivity", kind="started", agentThreadId="child"),
                item("subAgentActivity", kind="completed", agentThreadId="other"),
                done(),
            ],
        ]:
            with self.assertRaises(StrategyError):
                CodexStrategies(RPC(events)).delegate("t", "goal", "ctx")

    def test_timeout_is_not_success(self):
        with self.assertRaises(TimeoutError):
            CodexStrategies(RPC([])).turn("t", "x")

    def test_cancel_only_forwards_interrupt(self):
        r = RPC([], {})
        result = CodexStrategies(r).cancel("t", "u")
        self.assertEqual(result["status"], "interrupt_requested")
        self.assertEqual(
            r.calls, [("turn/interrupt", {"threadId": "t", "turnId": "u"})]
        )


if __name__ == "__main__":
    unittest.main()
