"""HTTP logical-turn regression; optionally run the exact packaged sidecar.

OMR_TEST_ENGINE=/absolute/path/to/omr-engine python -m unittest test_desktop_packaged -v
All traffic and state are synthetic, isolated and loopback-only.
"""

import copy
import http.client
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from desktop_engine import default_config
from test_desktop import connection


def wait_for_receipt(ipc, previous_count, timeout=10):
    deadline = time.monotonic() + timeout
    while True:
        snapshot = ipc({"command": "snapshot"})
        if snapshot["active"] == 0 and len(snapshot["receipts"]) == previous_count + 1:
            return snapshot["receipts"][-1]
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("request receipt was not finalized")
        threading.Event().wait(min(0.01, remaining))


class ReceiptFinalizationTest(unittest.TestCase):
    def test_waits_for_new_receipt_after_http_response(self):
        snapshots = iter(
            [
                {"active": 1, "receipts": [{"reason": "tool_continuity"}]},
                {
                    "active": 0,
                    "receipts": [
                        {"reason": "tool_continuity"},
                        {"error": "continuity_route_unavailable"},
                    ],
                },
            ]
        )

        def ipc(_request):
            return next(snapshots)

        self.assertEqual(
            wait_for_receipt(ipc, 1)["error"],
            "continuity_route_unavailable",
        )

    def test_timeout_if_active_or_receipt_missing(self):
        for snapshot in (
            {"active": 1, "receipts": [{"error": "new"}]},
            {"active": 0, "receipts": []},
        ):
            with self.subTest(snapshot=snapshot), self.assertRaises(TimeoutError):
                wait_for_receipt(lambda _, value=snapshot: value, 0, timeout=0)


class PackagedContinuityTest(unittest.TestCase):
    def test_anthropic_tool_result_prefill_keeps_the_concrete_route(self):
        calls = []

        class API(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_POST(self):
                data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                calls.append(data["model"])
                if data["model"] == "synthetic-decider":
                    body = {
                        "model": data["model"],
                        "choices": [
                            {
                                "message": {
                                    "content": json.dumps(
                                        {"required_quality": 1, "reason": "simple"}
                                    )
                                }
                            }
                        ],
                        "usage": {"prompt_tokens": 2, "completion_tokens": 1},
                    }
                else:
                    body = {
                        "id": "synthetic-response",
                        "type": "message",
                        "role": "assistant",
                        "model": data["model"],
                        "content": [{"type": "text", "text": "synthetic response"}],
                        "stop_reason": "end_turn",
                        "usage": {"input_tokens": 2, "output_tokens": 1},
                    }
                encoded = json.dumps(body).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

        server = ThreadingHTTPServer(("127.0.0.1", 0), API)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        key = "synthetic-key-" + "x" * 48
        engine = os.environ.get("OMR_TEST_ENGINE")
        command = (
            [str(Path(engine).resolve())]
            if engine
            else [
                sys.executable,
                "-B",
                str(Path(__file__).with_name("desktop_sidecar.py")),
            ]
        )
        with tempfile.TemporaryDirectory() as state_dir:
            with subprocess.Popen(
                command + [state_dir],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=dict(os.environ, PATH="/nonexistent"),
            ) as process:
                self.addCleanup(lambda: process.poll() is None and process.kill())

                assert process.stdin is not None and process.stdout is not None
                stream_in, stream_out = process.stdin, process.stdout

                responses: queue.Queue[str] = queue.Queue()

                def read_responses():
                    for line in stream_out:
                        responses.put(line)

                reader = threading.Thread(target=read_responses, daemon=True)
                reader.start()

                def ipc(request):
                    stream_in.write(json.dumps(request) + "\n")
                    stream_in.flush()
                    response = json.loads(responses.get(timeout=20))
                    self.assertIn("ok", response)
                    return response["ok"]

                try:
                    state = ipc({"command": "init", "key": key})
                    config = default_config()
                    config["connections"] = [connection(), connection("large", 3, 10)]
                    for conn in config["connections"]:
                        conn["url"] = f"http://127.0.0.1:{server.server_port}/v1"
                        conn["models"][0]["protocols"] = ["anthropic"]
                    conn = config["connections"][0]
                    config["decider"] = {
                        "connection": conn["id"],
                        "model": "synthetic-decider",
                        "consent": True,
                    }
                    ipc(
                        {
                            "command": "save_config",
                            "config": config,
                            "revision": 0,
                            "consent_for": {
                                "connection": conn["id"],
                                "url": conn["url"],
                                "model": "synthetic-decider",
                            },
                        }
                    )

                    def request(
                        messages, session="33333333-3333-4333-8333-333333333333"
                    ):
                        previous_count = len(ipc({"command": "snapshot"})["receipts"])
                        client = http.client.HTTPConnection(
                            "127.0.0.1", state["port"], timeout=10
                        )
                        try:
                            client.request(
                                "POST",
                                "/v1/messages",
                                json.dumps(
                                    {
                                        "model": "omr/economy",
                                        "max_tokens": 20,
                                        "messages": messages,
                                    }
                                ),
                                {
                                    "Authorization": "Bearer " + key,
                                    "Content-Type": "application/json",
                                    "anthropic-version": "2023-06-01",
                                    "X-OMR-Session": session,
                                },
                            )
                            response = client.getresponse()
                            result = response.status, json.loads(response.read())
                        finally:
                            client.close()
                        return (*result, wait_for_receipt(ipc, previous_count))

                    start = [{"role": "user", "content": "synthetic task"}]
                    plain = start + [{"role": "assistant", "content": "Here is"}]
                    status, response, _ = request(plain)
                    self.assertEqual(
                        (status, response.get("model")), (200, "synthetic-small")
                    )
                    self.assertEqual(calls, ["synthetic-decider", "synthetic-small"])
                    cycle = start + [
                        {
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": "a",
                                    "name": "synthetic",
                                    "input": {},
                                }
                            ],
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": "a",
                                    "content": "synthetic result",
                                }
                            ],
                        },
                    ]
                    prefilled = cycle + [{"role": "assistant", "content": "Here is"}]
                    count = len(calls)
                    status, response, receipt = request(prefilled)
                    self.assertEqual(
                        (status, response.get("model")), (200, "synthetic-small")
                    )
                    self.assertEqual(
                        calls[count:], ["synthetic-small"], "must skip decider"
                    )
                    self.assertEqual(
                        receipt["reason"],
                        "tool_continuity",
                    )
                    config["connections"][0]["models"][0]["enabled"] = False
                    ipc({"command": "save_config", "config": config, "revision": 1})
                    for messages in (cycle, prefilled):
                        count = len(calls)
                        status, _, receipt = request(messages)
                        self.assertEqual(status, 400)
                        self.assertEqual(
                            len(calls),
                            count,
                            "no decision or upstream after revocation",
                        )
                        self.assertEqual(
                            receipt["error"],
                            "continuity_route_unavailable",
                        )
                    # New genuine user turn, with old tools retained in history.
                    new_turn = copy.deepcopy(prefilled) + [
                        {"role": "user", "content": "new synthetic task"},
                        {"role": "assistant", "content": "Here is"},
                    ]
                    for messages in (new_turn, plain):
                        count = len(calls)
                        status, response, _ = request(messages)
                        self.assertEqual(
                            (status, response.get("model")), (200, "large")
                        )
                        self.assertEqual(calls[count:], ["synthetic-decider", "large"])
                    ipc({"command": "shutdown", "force": False})
                    process.wait(timeout=10)
                    self.assertEqual(process.returncode, 0)
                finally:
                    if process.poll() is None:
                        process.terminate()
                        process.wait(timeout=10)


if __name__ == "__main__":
    unittest.main()
