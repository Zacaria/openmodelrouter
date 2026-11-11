"""Subprocess transport fixtures (no native model provider)."""

import sys
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from advanced.codex import CodexStrategies, StrategyError
from advanced.rpc import StdioRPC


class Transport(unittest.TestCase):
    def test_adapter_cancel_during_active_turn_routes_ack_and_terminal(self):
        for terminal_first in (False, True):
            with self.subTest(terminal_first=terminal_first):
                program = """import sys,json,time
r=json.loads(sys.stdin.readline())
print(json.dumps({"id":r["id"],"result":{"turn":{"id":"turn"}}}),flush=True)
print(json.dumps({"method":"turn/started","params":{"threadId":"t","turn":{"id":"turn"}}}),flush=True)
c=json.loads(sys.stdin.readline())
assert c["method"] == "turn/interrupt"
ack={"id":c["id"],"result":{}}
terminal={"method":"turn/completed","params":{"threadId":"t","turn":{"id":"turn","status":"interrupted"}}}
frames=[terminal,ack] if sys.argv[1] == "True" else [ack,terminal]
for frame in frames:
 print(json.dumps(frame),flush=True); time.sleep(.08)
r=json.loads(sys.stdin.readline())
print(json.dumps({"id":r["id"],"result":{"turn":{"id":"recovery"}}}),flush=True)
print(json.dumps({"method":"turn/completed","params":{"threadId":"t","turn":{"id":"recovery","status":"completed"}}}),flush=True)
sys.stdin.read()
"""
                waiting = threading.Event()

                class ObservedRPC(StdioRPC):
                    def wait(self, predicate, timeout, _waiting=waiting):
                        _waiting.set()
                        return super().wait(predicate, timeout)

                with (
                    ObservedRPC(
                        [sys.executable, "-u", "-c", program, str(terminal_first)],
                        timeout=1,
                    ) as rpc,
                    ThreadPoolExecutor(max_workers=2) as pool,
                ):
                    adapter = CodexStrategies(rpc, timeout=1)
                    turn = pool.submit(adapter.turn, "t", "synthetic")
                    self.assertTrue(waiting.wait(1))
                    # Put the synchronous turn in its notification wait before cancel.
                    time.sleep(0.04)
                    cancel = pool.submit(adapter.cancel, "t", "turn")
                    self.assertEqual(
                        cancel.result(timeout=2)["status"], "interrupt_requested"
                    )
                    with self.assertRaisesRegex(StrategyError, "interrupted"):
                        turn.result(timeout=2)
                    self.assertEqual(
                        adapter.turn("t", "recovery")["status"], "completed"
                    )

    def test_concurrent_requests_out_of_order(self):
        program = """import sys,json
requests=[json.loads(sys.stdin.readline()) for _ in range(3)]
for r in reversed(requests):
 print(json.dumps({"id":r["id"],"result":{"method":r["method"]}}),flush=True)
sys.stdin.read()
"""
        with (
            StdioRPC([sys.executable, "-u", "-c", program], timeout=1) as rpc,
            ThreadPoolExecutor(max_workers=3) as pool,
        ):
            futures = [pool.submit(rpc.request, name, {}) for name in ("a", "b", "c")]
            self.assertEqual(
                [f.result(timeout=2) for f in futures],
                [{"method": name} for name in ("a", "b", "c")],
            )

    def test_eof_wakes_all_waiters(self):
        program = "import sys; sys.stdin.readline(); sys.stdin.readline()"
        with (
            StdioRPC([sys.executable, "-u", "-c", program], timeout=1) as rpc,
            ThreadPoolExecutor(max_workers=2) as pool,
        ):
            futures = [pool.submit(rpc.request, name, {}) for name in ("a", "b")]
            for future in futures:
                with self.assertRaises(EOFError):
                    future.result(timeout=2)

    def test_interleaved_notification_and_denied_server_request(self):
        program = """import sys,json
r=json.loads(sys.stdin.readline())
print(json.dumps({"method":"event","params":{"threadId":"t"}}),flush=True)
print(json.dumps({"id":"server", "method":"item/commandExecution/requestApproval","params":{}}),flush=True)
answer=json.loads(sys.stdin.readline())
print(json.dumps({"id":r["id"],"result":{"denied": "error" in answer}}),flush=True)
sys.stdin.read()
"""
        with StdioRPC([sys.executable, "-u", "-c", program], timeout=2) as rpc:
            self.assertEqual(rpc.request("test", {}), {"denied": True})
            self.assertEqual(
                rpc.wait(lambda e: e["method"] == "event", 1)["params"]["threadId"], "t"
            )
        self.assertIsNotNone(rpc.process.poll())

    def test_explicit_handler_does_not_authorize_other_tools(self):
        program = """import sys,json
r=json.loads(sys.stdin.readline())
print(json.dumps({"id":"s1", "method":"fixture/read", "params":{"tool":"fixture"}}),flush=True)
a=json.loads(sys.stdin.readline())
print(json.dumps({"id":"s2", "method":"unknown/tool", "params":{}}),flush=True)
b=json.loads(sys.stdin.readline())
print(json.dumps({"id":r["id"],"result":{"value":a["result"],"denied":"error" in b}}),flush=True)
sys.stdin.read()
"""

        def handler(method, params):
            return {"value": "synthetic"} if method == "fixture/read" else None

        with StdioRPC(
            [sys.executable, "-u", "-c", program], timeout=2, handle_request=handler
        ) as rpc:
            self.assertEqual(
                rpc.request("test", {}),
                {"value": {"value": "synthetic"}, "denied": True},
            )

    def test_rpc_error_is_failure(self):
        program = """import sys,json
r=json.loads(sys.stdin.readline()); print(json.dumps({"id":r["id"],"error":{"code":-1,"message":"synthetic"}}),flush=True)
sys.stdin.read()
"""
        with (
            StdioRPC([sys.executable, "-u", "-c", program], timeout=2) as rpc,
            self.assertRaises(RuntimeError),
        ):
            rpc.request("test", {})

    def test_timeout_cleanup(self):
        with (
            StdioRPC(
                [sys.executable, "-c", "import time; time.sleep(20)"], timeout=0.05
            ) as rpc,
            self.assertRaises(TimeoutError),
        ):
            rpc.request("test", {})
        self.assertIsNotNone(rpc.process.poll())

    def test_eof_fails_promptly(self):
        with (
            StdioRPC([sys.executable, "-c", "pass"], timeout=2) as rpc,
            self.assertRaises(EOFError),
        ):
            rpc.wait(lambda e: True, 2)


if __name__ == "__main__":
    unittest.main()
