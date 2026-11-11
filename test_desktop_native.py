"""Offline contracts only; these fixtures do not qualify a native host."""

import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from desktop_native import NativeController, safe_receipt, isolated_command
from desktop_engine import Runtime


class FakeSession:
    def __init__(self, observe, context):
        self.observe = observe
        self.context = context
        self.closed = False
        self.cancelled = threading.Event()
        self.waiting = threading.Event()
        self.models = ["model-a", "model-b"]
        self.model = "model-a"
        self.turn_id = "fake-turn"
        self.thread_id = "fake-thread"

    def run(self, action, prompt, model):
        self.turn_id = "fake-turn"
        self.observe(
            {
                "method": "turn/started",
                "params": {"threadId": self.thread_id, "turn": {"id": self.turn_id}},
            }
        )
        self.waiting.set()
        if prompt == "WAIT":
            self.cancelled.wait(2)
            self.observe(
                {
                    "method": "turn/completed",
                    "params": {
                        "threadId": self.thread_id,
                        "turn": {"status": "interrupted"},
                    },
                }
            )
            raise RuntimeError("interrupted private@example.com")
        if prompt == "ERROR":
            raise RuntimeError("provider error contains secret")
        self.model = model or self.model
        return {
            "status": "completed",
            "thread_id": "private-thread",
            "turn_id": "private-turn",
            "items": [
                {"type": "agentMessage", "text": "private reply"},
                {"type": "contextCompaction"},
            ],
            "usage": {
                "total": {"inputTokens": 100, "outputTokens": 8},
                "last": {"inputTokens": 3, "outputTokens": 2},
            },
            "children": {"private-child": {"status": "completed", "model": None}},
        }

    def cancel(self, turn_id):
        self.cancelled.set()
        return True

    def close(self):
        self.closed = True
        self.cancelled.set()


class NativeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.rows = []
        self.sessions = []

        def factory(observe, context, on_transport, instructions):
            s = FakeSession(observe, context)
            self.sessions.append(s)
            return s

        self.controller = NativeController(
            Path(self.tmp.name), self.rows.append, factory=factory
        )

    def tearDown(self):
        self.controller.shutdown()
        self.tmp.cleanup()

    def wait(self):
        end = time.monotonic() + 3
        while self.controller.snapshot()["active"]:
            if time.monotonic() > end:
                self.fail("worker did not finish")
            time.sleep(0.005)
        return self.controller.snapshot()

    def connect(self):
        self.controller.command(
            {"action": "connect", "consent": True, "context": "private context"}
        )
        self.assertEqual(self.wait()["status"], "ready")

    def test_no_implicit_process_or_provider_and_consent_required(self):
        self.assertEqual(self.sessions, [])
        with self.assertRaisesRegex(ValueError, "consent_required"):
            self.controller.command({"action": "connect", "context": "x"})
        self.assertEqual(self.sessions, [])

    def test_explicit_session_instructions_are_forwarded_without_receipt_content(self):
        captured = []

        def factory(observe, context, register, instructions):
            captured.append(instructions)
            return FakeSession(observe, context)

        self.controller.factory = factory
        self.controller.command(
            {
                "action": "connect",
                "consent": True,
                "instructions": "private session policy",
            }
        )
        self.assertEqual(self.wait()["status"], "ready")
        self.assertEqual(captured, ["private session policy"])
        self.assertNotIn("private session policy", json.dumps(self.rows))

    def test_explicit_actions_and_unknown_costs_without_transcript(self):
        self.connect()
        for action in ("maintain", "switch", "compact", "delegate"):
            self.controller.command(
                {"action": action, "prompt": "private prompt", "model": "model-b"}
            )
            self.assertEqual(self.wait()["status"], "ready")
            row = self.rows[-1]
            self.assertEqual(row["native"]["action"], action)
            self.assertEqual(row["status"], "completed")
            self.assertIsNone(row["native"]["auxiliary_cost_usd"])
            self.assertEqual(row["usage"], {})
        self.assertEqual(self.controller.snapshot()["reply"], "private reply")
        stored = json.dumps(self.rows)
        for private in (
            "private context",
            "private prompt",
            "private reply",
            "private-thread",
            "private-child",
        ):
            self.assertNotIn(private, stored)

    def test_cancel_is_concurrent_and_ack_is_not_completion(self):
        self.connect()
        self.controller.command({"action": "maintain", "prompt": "WAIT"})
        self.sessions[0].waiting.wait(1)
        with self.assertRaisesRegex(ValueError, "native_busy"):
            self.controller.command({"action": "compact"})
        self.controller.command({"action": "cancel"})
        self.wait()
        self.assertEqual(self.rows[-1]["status"], "cancelled")
        self.assertIsNone(self.rows[-1]["native"]["auxiliary_cost_usd"])

    def test_invalid_commands_never_reach_transport(self):
        self.connect()
        for request in (
            {"action": "resume", "thread_id": "existing"},
            {"action": "maintain", "prompt": "ok", "command": "sh"},
            {"action": "switch", "prompt": "ok", "model": "unadvertised"},
            {"action": "maintain", "prompt": "x" * 32001},
        ):
            with self.assertRaises(ValueError):
                self.controller.command(request)
        self.assertFalse(self.sessions[0].waiting.is_set())

    def test_errors_are_bounded_and_close_destroys_session(self):
        self.connect()
        self.controller.command({"action": "maintain", "prompt": "ERROR"})
        self.wait()
        self.assertNotIn("secret", json.dumps(self.controller.snapshot()))
        self.assertEqual(self.rows[-1]["error"], "native_failed")
        self.controller.command({"action": "close"})
        self.wait()
        self.assertTrue(self.sessions[0].closed)
        self.assertEqual(self.controller.snapshot()["reply"], "")

    def test_receipt_numeric_allowlist_discards_raw_events_and_nan(self):
        row = safe_receipt(
            "compact",
            {
                "thread_id": "secret",
                "items": [{"type": "contextCompaction", "text": "secret"}],
                "usage": {
                    "total": {
                        "inputTokens": float("nan"),
                        "outputTokens": 5,
                        "secret": 1,
                    }
                },
                "children": {},
            },
            0.5,
            "completed",
        )
        self.assertNotIn("secret", json.dumps(row))
        self.assertEqual(row["native"]["thread_usage"], {"outputTokens": 5})
        self.assertIsNone(row["native"]["full_cost_usd"])

    def test_launcher_masks_native_home_and_workspaces_with_readonly_auth(self):
        cmd = isolated_command(
            Path("/isolated"), Path("/native/bin/codex"), Path("/home/tester")
        )
        self.assertIn("/home/tester/.codex/auth.json", cmd)
        self.assertIn("--tmpfs", cmd)
        self.assertIn("--unshare-pid", cmd)
        self.assertEqual(cmd[-2:], ["app-server", "--stdio"])
        self.assertNotIn("bash", cmd)
        self.assertIn("features.shell_tool=false", cmd)

    def test_stale_cancellation_cannot_target_new_operation(self):
        self.connect()
        old = self.controller.generation
        self.controller.command({"action": "maintain", "prompt": "WAIT"})
        self.sessions[0].waiting.wait(1)
        self.controller._cancel(old, self.sessions[0], "old-turn", None)
        self.assertFalse(self.sessions[0].cancelled.is_set())
        self.controller.command({"action": "cancel"})
        self.wait()

    def test_failed_interrupt_detaches_session(self):
        self.connect()

        def fail(turn_id):
            raise OSError("transport gone")

        self.sessions[0].cancel = fail
        self.controller.command({"action": "maintain", "prompt": "WAIT"})
        self.sessions[0].waiting.wait(1)
        self.controller.command({"action": "cancel"})
        state = self.wait()
        self.assertEqual(state["status"], "disconnected")
        self.assertIsNone(self.controller.session)

    def test_close_reconnect_keeps_one_durable_owner(self):
        self.connect()
        owner = self.controller.worker
        for _ in range(4):
            self.controller.command({"action": "close"})
            self.wait()
            self.connect()
            self.assertIs(self.controller.worker, owner)

    def test_connect_cancellation_closes_pending_transport(self):
        entered, stopped = threading.Event(), threading.Event()

        class Transport:
            def close(self):
                stopped.set()

        def pending(observe, context, register, instructions):
            register(Transport())
            entered.set()
            stopped.wait(2)
            raise EOFError("setup aborted")

        self.controller.factory = pending
        self.controller.command({"action": "connect", "consent": True})
        self.assertTrue(entered.wait(1))
        self.controller.command({"action": "cancel"})
        self.assertTrue(stopped.wait(1))
        self.assertEqual(self.wait()["status"], "disconnected")
        self.assertEqual(self.rows[-1]["status"], "cancelled")

    def test_launcher_has_no_host_root_bind(self):
        cmd = isolated_command(
            Path("/isolated"), Path("/native/bin/codex"), Path("/home/tester")
        )
        self.assertNotIn(
            ["--ro-bind", "/", "/"], [cmd[i : i + 3] for i in range(len(cmd) - 2)]
        )
        self.assertEqual(cmd[cmd.index("--tmpfs") + 1], "/")

    def test_sidecar_shutdown_finishes_native_cleanup_before_ack(self):
        import io
        from types import SimpleNamespace
        import desktop_sidecar

        output = io.StringIO()
        observed = []
        native = SimpleNamespace(
            snapshot=lambda: {"active": False},
            shutdown=lambda: observed.append('"ok": true' not in output.getvalue()),
        )
        runtime = SimpleNamespace(
            native=native,
            managed=native,
            lock=threading.RLock(),
            active=0,
            stopping=False,
            snapshot=lambda: {"native": {"active": False}},
        )
        requests = io.StringIO(
            json.dumps({"command": "init", "key": "s" * 64})
            + "\n"
            + json.dumps({"command": "shutdown", "force": False})
            + "\n"
        )
        with (
            patch.object(desktop_sidecar, "Runtime", return_value=runtime),
            patch("sys.argv", ["sidecar", self.tmp.name]),
            patch("sys.stdin", requests),
            patch("sys.stdout", output),
        ):
            desktop_sidecar.main()
        self.assertTrue(
            observed[0],
            "cleanup must complete before Tauri may exit and kill the sidecar",
        )
        self.assertTrue(
            observed[1], "managed cleanup must also precede shutdown acknowledgement"
        )

    def test_native_server_requests_fail_closed_except_exact_parent_data_tool(self):
        from desktop_native import CodexSession

        session = CodexSession.__new__(CodexSession)
        events = []
        session.thread_id = "parent"
        session._context = "only explicit context"
        session._observe = events.append
        allowed = {"threadId": "parent", "tool": "read_context", "arguments": {}}
        allowed_result = session.handle_request("item/tool/call", allowed)
        assert allowed_result is not None
        self.assertEqual(
            allowed_result["contentItems"][0]["text"], "only explicit context"
        )
        for method, params in [
            ("item/tool/requestUserInput", allowed),
            ("item/commandExecution/requestApproval", allowed),
            ("item/tool/call", dict(allowed, threadId="child")),
            ("item/tool/call", dict(allowed, tool="shell")),
            ("item/tool/call", dict(allowed, arguments={"path": "/etc/passwd"})),
        ]:
            self.assertIsNone(session.handle_request(method, params))
        self.assertEqual(len(events), 5)
        self.assertNotIn("/etc/passwd", json.dumps(events))

    def test_other_platform_availability_needs_no_home_or_credentials(self):
        from desktop_native import availability

        for system in ("Windows", "Darwin"):
            with (
                patch("desktop_native.platform.system", return_value=system),
                patch("desktop_native.Path.home", side_effect=RuntimeError("no home")),
            ):
                self.assertEqual(set(availability().values()), {"unavailable"})

    def test_snapshot_runtime_includes_native_and_http_config_unchanged(self):
        with patch("desktop_native.NativeController", return_value=self.controller):
            runtime = Runtime(Path(self.tmp.name) / "runtime", "k" * 64)
        before = json.dumps(runtime.config, sort_keys=True)
        self.assertIn("native", runtime.snapshot())
        self.connect()
        self.assertEqual(json.dumps(runtime.config, sort_keys=True), before)


if __name__ == "__main__":
    unittest.main()
