"""Offline generation qualification through the real authenticated gateway."""

import copy
import json
import tempfile
import threading
import time
import subprocess
import sys
import unittest
from typing import Any
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import omr
from desktop_engine import Runtime, default_config
from test_desktop import connection

CANARY = "provider-private-body-key-canary"
MODEL = "nvidia/nemotron-3.5-super-vl:free"


class GenerationTest(unittest.TestCase):
    result: Any

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.calls = []
        self.status = 200
        self.delay = 0
        self.drip = 0
        self.budget_sensitive = False
        test = self

        class Provider(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_POST(self):
                data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                test.calls.append((self.path, dict(self.headers), data))
                time.sleep(test.delay)
                result = copy.deepcopy(test.result)
                if test.budget_sensitive:
                    budget = data.get("max_tokens", data.get("max_output_tokens"))
                    if budget <= 16:
                        result = test.answer(
                            "responses" if "input" in data else "chat", ""
                        )
                        result["usage"] = {"prompt_tokens": 20, "completion_tokens": 16}
                        if "choices" in result:
                            result["choices"][0]["finish_reason"] = "length"
                        else:
                            result.update(
                                status="incomplete",
                                incomplete_details={"reason": "max_output_tokens"},
                            )
                body = json.dumps(result).encode()
                self.send_response(test.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    if test.drip:
                        for offset in range(0, len(body), 8):
                            self.wfile.write(body[offset : offset + 8])
                            self.wfile.flush()
                            time.sleep(test.drip)
                    else:
                        self.wfile.write(body)
                except (OSError, ValueError):
                    pass

        self.upstream = self.server(Provider)
        self.runtime = Runtime(Path(self.directory.name), "k" * 48)
        self.gateway = self.server(
            omr.handler(
                {
                    "routes": {
                        "unused": {
                            "url": "http://127.0.0.1:1/v1",
                            "model": "unused",
                            "protocol": "chat",
                        }
                    },
                    "default_route": "unused",
                },
                desktop=self.runtime,
            )
        )
        self.runtime.port = self.gateway.server_port

    def server(self, handler):
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server

    def configure(self, protocol):
        config = default_config()
        c = connection(MODEL)
        c["url"] = f"http://127.0.0.1:{self.upstream.server_port}/v1"
        c["models"][0].update(protocols=[protocol], effort="low")
        config["connections"] = [c]
        self.runtime.save_config(config, self.runtime.revision)
        self.runtime.secrets[c["id"]] = CANARY
        self.model_id = c["models"][0]["id"]
        self.direct = self.runtime.catalogue()["data"][3]["id"]
        self.result = self.answer(protocol)

    @staticmethod
    def answer(protocol, text="OK"):
        if protocol == "chat":
            return {
                "model": MODEL,
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": text},
                    }
                ],
            }
        return {
            "model": MODEL,
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": text}],
                }
            ],
        }

    def state(self):
        return self.runtime.snapshot()["model_states"][self.model_id]

    def wait_receipts(self):
        end = time.monotonic() + 2
        while self.runtime.active and time.monotonic() < end:
            time.sleep(0.01)
        self.assertEqual(self.runtime.active, 0)

    def check_failure(self, code):
        before = len(self.calls)
        with self.assertRaisesRegex(ValueError, "^" + code + "$") as error:
            self.runtime.verify_generation(self.direct, True)
        self.wait_receipts()
        self.assertEqual(len(self.calls), before + 1)
        state = self.state()
        self.assertEqual(state["generation"], "failed")
        self.assertEqual(state["generation_diagnostic"]["code"], code)
        self.assertEqual(self.runtime.safe_error(error.exception), code)
        self.assertNotIn(CANARY, json.dumps(self.runtime.snapshot()))
        self.assertNotIn(
            CANARY, Path(self.directory.name, "receipts.jsonl").read_text()
        )
        return state["generation_diagnostic"]

    def test_reasoning_budget_regression_via_gateway_both_protocols(self):
        self.budget_sensitive = True
        for protocol in ("chat", "responses"):
            with self.subTest(protocol=protocol):
                self.configure(protocol)
                self.runtime.verify_generation(self.direct, True)
                self.wait_receipts()
                self.assertEqual(self.state()["generation"], "verified")
                path, headers, sent = self.calls[-1]
                self.assertEqual(
                    path,
                    "/v1/"
                    + ("responses" if protocol == "responses" else "chat/completions"),
                )
                self.assertEqual(headers["Authorization"], "Bearer " + CANARY)
                self.assertEqual(sent["model"], MODEL)
                self.assertEqual(
                    sent.get("max_tokens", sent.get("max_output_tokens")), 1024
                )
                self.assertEqual(
                    sent.get(
                        "reasoning_effort", sent.get("reasoning", {}).get("effort")
                    ),
                    "low",
                )
                self.assertEqual(self.runtime.rows[-1]["decision_ms"], 0)
                self.assertEqual(self.runtime.rows[-1]["model_observed"], MODEL)
                self.assertEqual(len(self.calls), 1 if protocol == "chat" else 2)

    def test_codex_base_dispatches_through_private_sdk_for_both_protocols(self):
        import io
        from unittest.mock import Mock
        from test_desktop_subscriptions import CREDENTIALS

        for protocol in ("chat", "responses"):
            with self.subTest(protocol=protocol):
                config = default_config()
                c = connection(MODEL)
                c.update(url="https://chatgpt.com/backend-api/codex",
                         transport="pi-ai", subscription="codex")
                c["models"][0]["protocols"] = [protocol]
                config["connections"] = [c]
                self.runtime.save_config(config, self.runtime.revision)
                self.runtime.secrets[c["id"]] = json.dumps(CREDENTIALS)
                self.model_id = c["models"][0]["id"]
                self.direct = f'direct/{c["id"]}/{self.model_id}'
                self.result = self.answer(protocol)
                body = io.BytesIO(json.dumps(self.result).encode())
                response = Mock(status=200, length=0)
                response.getheader.side_effect = lambda name, default=None: (
                    "application/json" if name.lower() == "content-type" else default
                )
                response.read1.side_effect = body.read
                adapter = Mock(sock=None, metadata={"model": MODEL, "status": 200})
                adapter.getresponse.return_value = response
                with patch("desktop_pi.PiConnection", return_value=adapter) as sdk, patch(
                    "http.client.HTTPSConnection",
                    side_effect=AssertionError("No provider network in offline test"),
                ):
                    self.runtime.verify_generation(self.direct, True)
                self.wait_receipts()
                sdk.assert_called_once()
                route, forwarded_protocol, *_ = sdk.call_args.args
                self.assertEqual(route["url"], c["url"])
                self.assertEqual(route["subscription"], "codex")
                self.assertEqual(route["_secret"], CREDENTIALS["access"])
                self.assertEqual(forwarded_protocol, protocol)
                self.assertEqual(adapter.request.call_args.args[1],
                                 "/v1/chat/completions" if protocol == "chat" else "/v1/responses")
                self.assertEqual(self.state()["generation"], "verified")
                self.assertEqual(self.runtime.rows[-1]["status"], "completed")
                self.assertNotIn("private-", Path(self.directory.name, "receipts.jsonl").read_text())
                self.assertEqual(self.calls, [])

    def test_empty_and_partial_are_not_success_even_with_http200(self):
        for protocol in ("chat", "responses"):
            self.configure(protocol)
            for text in ("", " \n\t"):
                with self.subTest(protocol=protocol, text=text):
                    self.result = self.answer(protocol, text)
                    self.check_failure("generation_empty")
            self.result = self.answer(protocol)
            if protocol == "chat":
                self.result["choices"][0]["finish_reason"] = "length"
            else:
                self.result.update(
                    status="incomplete",
                    incomplete_details={"reason": "max_output_tokens"},
                )
            diagnostic = self.check_failure("generation_budget_exhausted")
            self.assertEqual(diagnostic["gateway_http_status"], 200)
            self.result = self.answer(protocol)
            if protocol == "chat":
                self.result["choices"][0]["finish_reason"] = None
            else:
                self.result["status"] = "in_progress"
            self.check_failure("generation_incomplete")

    def test_completed_response_with_incomplete_details_is_not_verified(self):
        self.configure("responses")
        self.result["incomplete_details"] = {
            "reason": "max_output_tokens",
            "private": CANARY,
        }
        diagnostic = self.check_failure("generation_budget_exhausted")
        self.assertEqual(diagnostic["incomplete_reason"], "max_output_tokens")
        for details in ({"reason": CANARY}, {}, CANARY):
            with self.subTest(details=details):
                self.result["incomplete_details"] = details
                self.check_failure("generation_incomplete")

    def test_completed_response_with_incomplete_reasoning_is_not_verified(self):
        self.configure("responses")
        self.result["output"].insert(
            0, {"type": "reasoning", "status": "incomplete", "summary": CANARY}
        )
        self.check_failure("generation_incomplete")
        self.result["output"][0]["status"] = "completed"
        self.result["incomplete_details"] = None
        self.runtime.verify_generation(self.direct, True)
        self.wait_receipts()
        self.assertEqual(self.state()["generation"], "verified")
        self.assertEqual(len(self.calls), 2)
        self.assertNotIn(CANARY, json.dumps(self.runtime.snapshot()))

    def test_refusals_and_http_failures_are_distinct_and_private(self):
        for protocol in ("chat", "responses"):
            self.status = 200
            self.configure(protocol)
            if protocol == "chat":
                self.result["choices"][0]["message"]["refusal"] = CANARY
            else:
                self.result["output"][0]["content"] = [
                    {"type": "refusal", "refusal": CANARY}
                ]
            self.check_failure("generation_refused")
            for status in (400, 401, 402, 403, 429, 500, 503):
                with self.subTest(protocol=protocol, status=status):
                    self.status = status
                    self.result = {"error": {"message": CANARY}}
                    diagnostic = self.check_failure(
                        "generation_upstream_rejected"
                        if status < 500
                        else "generation_unavailable"
                    )
                    self.assertEqual(diagnostic["gateway_http_status"], status)

    def test_untrusted_shapes_identity_and_tool_only_fail_closed(self):
        for protocol in ("chat", "responses"):
            self.configure(protocol)
            self.result["model"] = CANARY
            self.check_failure("generation_identity_mismatch")
            for malformed in (
                [],
                None,
                {"model": MODEL},
                {"model": MODEL, "choices": [None], "output": [None]},
            ):
                self.result = malformed
                self.check_failure("generation_failed")
            self.result = self.answer(protocol, "")
            if protocol == "chat":
                self.result["choices"][0]["message"]["tool_calls"] = [{"id": CANARY}]
            else:
                self.result["output"] = [{"type": "function_call", "name": CANARY}]
            self.check_failure("generation_empty")

    def test_safe_metadata_and_failed_test_replace_previous_verified_state(self):
        for protocol in ("chat", "responses"):
            self.configure(protocol)
            self.runtime.verify_generation(self.direct, True)
            self.wait_receipts()
            self.result = self.answer(protocol, "")
            self.result["usage"] = {
                "prompt_tokens": 20,
                "completion_tokens": 1024,
                "completion_tokens_details": {
                    "reasoning_tokens": 1024,
                    "private": CANARY,
                },
                "private": CANARY,
            }
            diagnostic = self.check_failure("generation_empty")
            self.assertEqual(diagnostic["input_tokens"], 20)
            self.assertEqual(diagnostic["output_tokens"], 1024)
            self.assertEqual(diagnostic["reasoning_tokens"], 1024)
            self.assertNotIn("private", json.dumps(diagnostic))

    def test_deadline_and_cancellation_do_not_leave_verified_state(self):
        self.configure("chat")
        self.delay = 0.5
        with patch("desktop_engine.GENERATION_TIMEOUT_SECONDS", 0.1, create=True):
            self.check_failure("generation_timeout")
        self.delay = 0.5
        self.runtime.stopping = False
        timer = threading.Timer(0.1, lambda: setattr(self.runtime, "stopping", True))
        timer.start()
        try:
            self.check_failure("generation_cancelled")
        finally:
            timer.join()
            self.runtime.stopping = False

    def test_drip_body_cannot_extend_absolute_test_deadline(self):
        self.configure("chat")
        self.result = self.answer("chat", "OK" * 100)
        self.drip = 0.02
        started = time.monotonic()
        with patch("desktop_engine.GENERATION_TIMEOUT_SECONDS", 0.1):
            self.check_failure("generation_timeout")
        self.assertLess(time.monotonic() - started, 0.4)

    def test_ipc_error_and_snapshot_expose_only_safe_diagnostic(self):
        self.configure("responses")
        self.result.update(
            status="incomplete", incomplete_details={"reason": "max_output_tokens"}
        )
        self.result["output"] = [{"type": "reasoning", "summary": CANARY}]
        requests = [
            {"command": "init", "key": "k" * 48},
            {"command": "test_generation", "model": self.direct, "consent": True},
            {"command": "snapshot"},
            {"command": "shutdown"},
        ]
        process = subprocess.run(
            [
                sys.executable,
                "-B",
                str(Path(__file__).with_name("desktop_sidecar.py")),
                self.directory.name,
            ],
            input="".join(json.dumps(request) + "\n" for request in requests),
            text=True,
            capture_output=True,
            timeout=5,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        replies = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual(len(replies), 4)
        self.assertEqual(replies[1], {"error": "generation_budget_exhausted"})
        diagnostic = replies[2]["ok"]["model_states"][self.model_id][
            "generation_diagnostic"
        ]
        self.assertEqual(diagnostic["code"], "generation_budget_exhausted")
        self.assertEqual(diagnostic["incomplete_reason"], "max_output_tokens")
        self.assertNotIn(CANARY, process.stdout + process.stderr)
        self.assertEqual(len(self.calls), 1)

    def test_invalid_metadata_and_partial_items_are_not_certified(self):
        for protocol in ("chat", "responses"):
            self.configure(protocol)
            self.result["error"] = {"message": CANARY}
            self.check_failure("generation_incomplete")
            self.result = self.answer(protocol)
            self.result["usage"] = {
                "prompt_tokens": True,
                "completion_tokens": -1,
                "output_tokens_details": {"reasoning_tokens": CANARY},
            }
            self.runtime.verify_generation(self.direct, True)
            diagnostic = self.state()["generation_diagnostic"]
            self.assertNotIn("input_tokens", diagnostic)
            self.assertNotIn("output_tokens", diagnostic)
            self.assertNotIn("reasoning_tokens", diagnostic)
            if protocol == "responses":
                self.result["output"][0]["status"] = "incomplete"
                self.check_failure("generation_incomplete")
            self.result = self.answer(protocol)
            if protocol == "chat":
                self.result["choices"][0]["finish_reason"] = CANARY
            else:
                self.result["status"] = CANARY
            self.check_failure("generation_incomplete")

    def test_no_consent_or_unknown_model_never_calls_provider(self):
        self.configure("chat")
        for direct, consent, code in (
            (self.direct, False, "consent_required"),
            ("direct/absent/model", True, "model_unavailable"),
        ):
            with self.assertRaisesRegex(ValueError, code):
                self.runtime.verify_generation(direct, consent)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
