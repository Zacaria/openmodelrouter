"""Offline Chat acceptance: real gateway, synthetic fragmented provider SSE."""

import json
import tempfile
import threading
import time
import unittest
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import omr
from desktop_chat import ChatService, TextStream
from desktop_engine import Runtime, decider_identity, default_config
from test_desktop import connection


class ChatTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.calls = []
        self.decision_calls = []
        self.mode = "ok"
        self.closed = threading.Event()
        owner = self

        class Provider(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_POST(self):
                data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if self.path == "/v1/systemone":
                    owner.decision_calls.append(data)
                    raw = json.dumps(
                        {
                            "model": data["model"],
                            "answers": {
                                "quality": {
                                    "type": "choice",
                                    "choice": "1",
                                    "confidence": 0.9,
                                    "probabilities": {"1": 0.9, "2": 0.05, "3": 0.05},
                                }
                            },
                        }
                    ).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)
                    return
                owner.calls.append((self.path, data, dict(self.headers)))
                if owner.mode == "http":
                    self.send_response(402)
                    self.end_headers()
                    self.wfile.write(b"private-provider-error-canary")
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                protocol = (
                    "responses"
                    if self.path.endswith("responses")
                    else "anthropic"
                    if self.path.endswith("messages")
                    else "chat"
                )
                model = (
                    "wrong"
                    if owner.mode == "identity"
                    else None
                    if owner.mode == "identity_missing"
                    else data["model"]
                )
                if owner.mode == "concurrent":
                    model = (
                        None if data["messages"][0]["content"] == "missing" else model
                    )
                text = " " if owner.mode == "empty" else "Bonjour 🌲"
                if protocol == "chat":
                    events = [
                        {
                            "model": model,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {"content": text[:3]},
                                    "finish_reason": None,
                                }
                            ],
                        },
                        {
                            "model": model,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {"content": text[3:]},
                                    "finish_reason": None,
                                }
                            ],
                        },
                        {
                            "model": model,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": (
                                        {"refusal": "private-refusal-canary"}
                                        if owner.mode == "refused"
                                        else {}
                                    ),
                                    "finish_reason": (
                                        "length" if owner.mode == "length" else "stop"
                                    ),
                                }
                            ],
                        },
                    ]
                elif protocol == "responses":
                    events = [
                        {
                            "type": "response.created",
                            "response": {"id": "synthetic", "model": model},
                        },
                        {"type": "response.output_text.delta", "delta": text},
                        {
                            "type": "response.completed",
                            "response": {
                                "id": "synthetic",
                                "model": model,
                                "status": "completed",
                            },
                        },
                    ]
                else:
                    events = [
                        {
                            "type": "message_start",
                            "message": {"id": "synthetic", "model": model},
                        },
                        {
                            "type": "content_block_delta",
                            "delta": {"type": "text_delta", "text": text},
                        },
                        {"type": "message_delta", "delta": {"stop_reason": "end_turn"}},
                        {"type": "message_stop"},
                    ]
                if owner.mode == "contradictory":
                    if protocol == "chat":
                        events[1]["model"] = "different-provider-model"
                    elif protocol == "responses":
                        events[-1]["response"]["model"] = "different-provider-model"
                    else:
                        events[1]["message"] = {"model": "different-provider-model"}
                try:
                    for event in events:
                        frame = (
                            "data: "
                            + json.dumps(event, ensure_ascii=False)
                            + "\r\n\r\n"
                        ).encode()
                        for i in range(0, len(frame), 7):
                            self.wfile.write(frame[i : i + 7])
                            self.wfile.flush()
                        if owner.mode == "stall":
                            self.connection.settimeout(4)
                            if not self.connection.recv(1):
                                owner.closed.set()
                            return
                        time.sleep(0.01)
                    if protocol == "chat" and owner.mode != "truncated":
                        self.wfile.write(b"data: [DONE]\n\n")
                        self.wfile.flush()
                except (OSError, TimeoutError):
                    owner.closed.set()

        self.provider = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
        self.server_cleanup(self.provider)
        self.runtime = Runtime(Path(self.directory.name), "k" * 64)
        config = default_config()
        self.c = connection("synthetic-exact")
        self.c["url"] = f"http://127.0.0.1:{self.provider.server_port}/v1"
        config["connections"] = [self.c]
        self.runtime.save_config(config, 0)
        self.direct = self.runtime.catalogue()["data"][3]["id"]
        self.gateway = ThreadingHTTPServer(
            ("127.0.0.1", 0),
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
                    "decision": {"type": "fixed"},
                    "timeout_seconds": 5,
                },
                desktop=self.runtime,
            ),
        )
        self.server_cleanup(self.gateway)
        self.runtime.port = self.gateway.server_port
        self.chat = ChatService(self.runtime)
        self.addCleanup(self.chat.shutdown)

    def server_cleanup(self, server):
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

    def start(self, messages=None, **extra):
        request = {
            "command": "chat_start",
            "id": str(uuid.uuid4()),
            "session": str(uuid.uuid4()),
            "model": self.direct,
            "revision": self.runtime.revision,
            "messages": messages
            or [{"role": "user", "content": "private-prompt-canary"}],
        }
        request.update(extra)
        self.chat.command(request)
        return request

    def drain(self, request):
        events = []
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            batch = self.chat.command({"command": "chat_poll", "id": request["id"]})
            assert isinstance(batch, dict)
            events.extend(batch["events"])
            if batch["done"]:
                return events
            time.sleep(0.01)
        self.fail("Chat did not terminate")

    def test_fragmented_stream_two_turns_and_private_receipts(self):
        first = self.start()
        events = self.drain(first)
        self.assertEqual("".join(e.get("text", "") for e in events), "Bonjour 🌲")
        self.assertEqual(events[-1]["type"], "finish")
        self.assertEqual(events[-1]["receipt"]["model_observed"], "synthetic-exact")
        second = self.start(
            session=first["session"],
            messages=[
                first["messages"][0],
                {"role": "assistant", "content": "Bonjour 🌲"},
                {"role": "user", "content": "Second turn"},
            ],
        )
        self.assertEqual(self.drain(second)[-1]["type"], "finish")
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.calls[1][1]["messages"], second["messages"])
        self.assertEqual(self.calls[0][1]["model"], "synthetic-exact")
        self.assertEqual(self.calls[0][1]["max_tokens"], 4096)
        self.assertEqual(len(self.runtime.rows), 2)
        stored = "".join(
            p.read_text() for p in Path(self.directory.name).glob("*.json*")
        )
        self.assertNotIn("private-prompt-canary", stored)
        self.assertNotIn("Bonjour", stored)

    def test_concurrent_same_session_uses_its_own_gateway_receipt(self):
        self.mode = "concurrent"
        second_service = ChatService(self.runtime)
        self.addCleanup(second_service.shutdown)
        session = str(uuid.uuid4())
        original = ChatService._receipt
        barrier = threading.Barrier(2)

        def synchronized(service, job):
            barrier.wait(3)
            return original(service, job)

        with patch.object(ChatService, "_receipt", synchronized):
            missing = self.start(
                session=session, messages=[{"role": "user", "content": "missing"}]
            )
            other = dict(
                missing,
                id=str(uuid.uuid4()),
                messages=[{"role": "user", "content": "present"}],
            )
            second_service.command(other)
            first_events = self.drain(missing)
            self.chat, old = second_service, self.chat
            try:
                second_events = self.drain(other)
            finally:
                self.chat = old
        self.assertEqual(first_events[-1].get("code"), "chat_identity", first_events)
        self.assertEqual(second_events[-1]["type"], "finish", second_events)
        self.assertNotEqual(
            first_events[-1]["receipt"]["request_id"],
            second_events[-1]["receipt"]["request_id"],
        )

    def test_receipt_lookup_never_substitutes_missing_or_evicted_id(self):
        actual = str(uuid.uuid4())
        other = str(uuid.uuid4())
        correct = {"request_id": actual, "model_observed": None}
        unrelated = {"request_id": other, "model_observed": "synthetic-exact"}
        with self.runtime.lock:
            saved = self.runtime.rows
            try:
                for rows in ([correct, unrelated], [unrelated, correct]):
                    self.runtime.rows = rows
                    result = self.chat._receipt(SimpleNamespace(request_id=actual))
                    assert result is not None
                    self.assertEqual(result["request_id"], actual)
                self.runtime.rows = [unrelated]
            finally:
                self.runtime.rows = saved
        self.assertIsNone(self.chat._receipt(SimpleNamespace()))
        with self.runtime.lock:
            self.runtime.rows = [unrelated]
        try:
            self.assertIsNone(self.chat._receipt(SimpleNamespace(request_id=actual)))
        finally:
            with self.runtime.lock:
                self.runtime.rows = saved

    def test_contradictory_provider_identity_is_never_confirmed(self):
        self.mode = "contradictory"
        for protocol in ("chat", "responses", "anthropic"):
            with self.subTest(protocol=protocol):
                config = self.runtime.snapshot()["config"]
                config["connections"][0]["models"][0]["protocols"] = [protocol]
                self.runtime.save_config(config, self.runtime.revision)
                events = self.drain(self.start())
                self.assertEqual(events[-1].get("code"), "chat_identity", events)

    def test_all_text_protocols(self):
        for protocol in ("responses", "anthropic"):
            with self.subTest(protocol=protocol):
                config = self.runtime.snapshot()["config"]
                config["connections"][0]["models"][0]["protocols"] = [protocol]
                self.runtime.save_config(config, self.runtime.revision)
                self.assertEqual(self.drain(self.start())[-1]["type"], "finish")

    def test_pi_ai_rejects_contradictory_raw_provider_identity(self):
        config = self.runtime.snapshot()["config"]
        config["connections"][0]["transport"] = "pi-ai"
        self.runtime.save_config(config, self.runtime.revision)
        self.mode = "contradictory"
        events = self.drain(self.start())
        self.assertEqual(events[-1].get("code"), "chat_identity", events)

    def test_real_pi_ai_chat_retains_exact_observed_identity(self):
        config = self.runtime.snapshot()["config"]
        config["connections"][0]["transport"] = "pi-ai"
        self.runtime.save_config(config, self.runtime.revision)
        events = self.drain(self.start())
        self.assertEqual(events[-1]["type"], "finish", events)
        self.assertEqual(events[-1]["receipt"]["model_observed"], "synthetic-exact")

    def test_output_limit_deadline_and_abandoned_poll_cancel_upstream(self):
        with patch("desktop_chat.MAX_OUTPUT", 50):
            self.assertEqual(self.drain(self.start())[-1]["code"], "chat_output_limit")
        for setting, code in [
            ("TIMEOUT", "chat_timeout"),
            ("POLL_LEASE", "chat_expired"),
        ]:
            with self.subTest(setting=setting), patch("desktop_chat." + setting, 0.15):
                self.mode = "stall"
                self.closed.clear()
                request = self.start()
                self.assertTrue(self.closed.wait(2))
                self.assertEqual(self.drain(request)[-1]["code"], code)

    def test_only_synthetic_native_credential_reaches_provider_not_chat_output(self):
        key = "synthetic-native-credential-canary"
        self.runtime.secrets[self.c["id"]] = key
        events = self.drain(self.start())
        self.assertEqual(self.calls[0][2]["Authorization"], "Bearer " + key)
        self.assertNotIn(key, json.dumps(events))
        self.assertNotIn(key, json.dumps(self.runtime.snapshot()))

    def test_rejects_semantic_failure_without_retry_or_raw_error(self):
        for mode, code in [
            ("empty", "chat_empty"),
            ("length", "chat_length"),
            ("refused", "chat_refused"),
            ("identity", "chat_identity"),
            ("identity_missing", "chat_identity"),
            ("http", "chat_http"),
            ("truncated", "chat_incomplete"),
        ]:
            with self.subTest(mode=mode):
                self.mode = mode
                events = self.drain(self.start())
                self.assertEqual(events[-1]["type"], "error")
                self.assertEqual(events[-1]["code"], code)
                if mode == "http":
                    self.assertEqual(events[-1]["receipt"]["upstream_status"], 402)
                self.assertNotIn("private-provider-error", json.dumps(events))
                self.assertNotIn("private-refusal", json.dumps(events))
        self.assertEqual(len(self.calls), 7)

    def test_stop_closes_upstream_and_records_cancellation(self):
        self.mode = "stall"
        request = self.start()
        deadline = time.monotonic() + 2
        while not self.calls and time.monotonic() < deadline:
            time.sleep(0.01)
        self.chat.command({"command": "chat_cancel", "id": request["id"]})
        self.assertEqual(self.drain(request)[-1]["code"], "chat_cancelled")
        self.assertTrue(self.closed.wait(2), "provider socket was not cancelled")
        self.assertEqual(self.runtime.rows[-1]["status"], "cancelled")

    def test_profiles_use_real_selection_and_confirm_the_selected_identity(self):
        decisions = []

        def decide(context, candidates, stopped, deadline):
            decisions.append(context)
            return {"required_quality": 1, "reason": "simple"}

        self.runtime.classifier = decide
        config = self.runtime.snapshot()["config"]
        config["connections"][0]["models"][0]["quality"] = 3
        config["decider"] = {
            "mode": "server",
            "protocol": "ollama-systemone",
            "connection": self.c["id"],
            "model": "d3:4b",
            "consent": True,
        }
        for protocol in ("chat", "responses", "anthropic"):
            config["connections"][0]["models"][0]["protocols"] = [protocol]
            self.runtime.save_config(
                config, self.runtime.revision, decider_identity(config)
            )
            for profile in ("economy", "balanced", "quality"):
                with self.subTest(protocol=protocol, profile=profile):
                    request = self.start(model=f"omr/{profile}")
                    events = self.drain(request)
                    self.assertEqual(events[-1]["type"], "finish", events)
                    self.assertEqual(
                        events[-1]["receipt"]["model_observed"], "synthetic-exact"
                    )
                    row = self.runtime.rows[-1]
                    self.assertEqual(row["mode"], "automatic")
                    self.assertEqual(row["profile"], profile)
                    self.assertEqual(row["protocol"], protocol)
                    self.assertEqual(self.calls[-1][1]["model"], "synthetic-exact")
                    second = self.start(
                        model=request["model"],
                        session=request["session"],
                        messages=[
                            request["messages"][0],
                            {"role": "assistant", "content": "Bonjour 🌲"},
                            {"role": "user", "content": "Second turn"},
                        ],
                    )
                    self.assertEqual(self.drain(second)[-1]["type"], "finish")
        self.assertEqual(len(decisions), 18)
        self.assertEqual(len(self.calls), 18)

    def test_profile_refusals_never_fall_back_to_a_direct_route(self):
        with self.assertRaises(ValueError):
            self.start(model="omr/economy")
        self.runtime.classifier = lambda *args: {
            "required_quality": 1,
            "reason": "not-a-valid-reason",
        }
        config = self.runtime.snapshot()["config"]
        config["decider"] = {
            "mode": "server",
            "protocol": "ollama-systemone",
            "connection": self.c["id"],
            "model": "d3:4b",
            "consent": True,
        }
        self.runtime.save_config(
            config, self.runtime.revision, decider_identity(config)
        )
        events = self.drain(self.start(model="omr/economy"))
        self.assertEqual(events[-1].get("code"), "chat_http", events)
        self.assertEqual(self.runtime.rows[-1]["error"], "invalid_decision")
        self.assertEqual(events[-1]["receipt"]["error"], "invalid_decision")
        self.assertEqual(
            events[-1]["receipt"]["request_id"], self.runtime.rows[-1]["request_id"]
        )
        self.assertFalse(self.calls)
        self.runtime.classifier = lambda *args: {
            "required_quality": 1,
            "reason": "simple",
        }
        events = self.drain(self.start(model="omr/quality"))
        self.assertEqual(events[-1].get("code"), "chat_http", events)
        self.assertEqual(
            self.runtime.rows[-1]["error"], "quality_requirement_unavailable"
        )
        self.assertEqual(
            events[-1]["receipt"]["error"], "quality_requirement_unavailable"
        )
        self.assertFalse(self.calls)
        self.mode = "identity"
        events = self.drain(self.start(model="omr/economy"))
        self.assertEqual(events[-1].get("code"), "chat_identity", events)
        self.assertEqual(len(self.calls), 1)

    def test_profiles_preserve_quality_floors_and_cancel_the_selected_stream(self):
        config = self.runtime.snapshot()["config"]
        model = config["connections"][0]["models"][0]
        config["connections"][0]["models"] = [
            {
                **model,
                "id": str(uuid.uuid4()),
                "upstream": f"synthetic-q{q}",
                "quality": q,
                "input_price": q,
                "output_price": q,
            }
            for q in (1, 2, 3)
        ]
        config["decider"] = {
            "mode": "server",
            "protocol": "ollama-systemone",
            "connection": self.c["id"],
            "model": "d3:4b",
            "consent": True,
        }
        self.runtime.save_config(
            config, self.runtime.revision, decider_identity(config)
        )
        for profile, q in (("economy", 1), ("balanced", 2), ("quality", 3)):
            events = self.drain(self.start(model=f"omr/{profile}"))
            self.assertEqual(events[-1]["type"], "finish", events)
            self.assertEqual(events[-1]["receipt"]["model_observed"], f"synthetic-q{q}")
        self.assertEqual(len(self.decision_calls), 3)
        self.mode = "stall"
        request = self.start(model="omr/balanced")
        events = []
        until = time.monotonic() + 2
        while not events and time.monotonic() < until:
            batch = self.chat.command({"command": "chat_poll", "id": request["id"]})
            assert isinstance(batch, dict)
            events.extend(batch["events"])
            time.sleep(0.01)
        self.assertEqual(events[0]["text"], "Bon")
        self.chat.command({"command": "chat_cancel", "id": request["id"]})
        events.extend(self.drain(request))
        self.assertEqual(events[-1]["code"], "chat_cancelled")
        self.assertTrue(self.closed.wait(2))
        self.assertEqual(self.runtime.rows[-1]["status"], "cancelled")

    def test_direct_chat_never_calls_a_configured_decider(self):
        def unexpected(*args):
            self.fail("direct Chat called the decider")

        self.runtime.classifier = unexpected
        self.assertEqual(self.drain(self.start())[-1]["type"], "finish")

    def test_preflight_rejects_stale_revision_invalid_routes_and_input(self):
        for extra in [
            {"revision": 0},
            {"model": "omr/unknown"},
            {"messages": [{"role": "system", "content": "bad"}]},
            {"messages": [{"role": "user", "content": "x" * 131073}]},
        ]:
            with self.subTest(extra=list(extra)), self.assertRaises(ValueError):
                self.start(**extra)
        self.assertFalse(self.calls)

    def test_gateway_revision_fence_rejects_malformed_model_without_crashing(self):
        import http.client

        client = http.client.HTTPConnection("127.0.0.1", self.runtime.port)
        self.addCleanup(client.close)
        client.request(
            "POST",
            "/v1/chat/completions",
            json.dumps(
                {"model": None, "messages": [{"role": "user", "content": "no"}]}
            ),
            {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.runtime.key,
                "X-OMR-Config-Revision": str(self.runtime.revision),
            },
        )
        self.assertEqual(client.getresponse().status, 400)
        self.assertFalse(self.calls)

    def test_gateway_revision_fence_prevents_changed_destination(self):
        import http.client

        client = http.client.HTTPConnection("127.0.0.1", self.runtime.port)
        self.addCleanup(client.close)
        client.request(
            "POST",
            "/v1/chat/completions",
            json.dumps(
                {"model": self.direct, "messages": [{"role": "user", "content": "no"}]}
            ),
            {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.runtime.key,
                "X-OMR-Config-Revision": "0",
            },
        )
        self.assertEqual(client.getresponse().status, 400)
        self.assertFalse(self.calls)


class PiAiChatIntegrationTest(unittest.TestCase):
    def setUp(self):
        from test_pi_ai import PiAiTest

        self.fixture = PiAiTest("runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def run_chat(self, protocol, behavior="text"):
        fixture = self.fixture
        fixture.behavior = behavior
        fixture.conn["models"][0]["protocols"] = [protocol]
        fixture.start()
        fixture.runtime.port = fixture.gateway.server_port
        chat = ChatService(fixture.runtime)
        self.addCleanup(chat.shutdown)
        request = {
            "command": "chat_start",
            "id": str(uuid.uuid4()),
            "session": str(uuid.uuid4()),
            "model": fixture.runtime.catalogue()["data"][3]["id"],
            "revision": fixture.runtime.revision,
            "messages": [{"role": "user", "content": "Synthetic task"}],
        }
        chat.command(request)
        events = []
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            batch = chat.command({"command": "chat_poll", "id": request["id"]})
            assert isinstance(batch, dict)
            events.extend(batch["events"])
            if batch["done"]:
                return events
            time.sleep(0.01)
        self.fail("Chat did not terminate")

    def test_responses_real_pi_ai_complete_and_exact_receipt(self):
        events = self.run_chat("responses")
        self.assertEqual(events[-1]["type"], "finish", events)
        self.assertEqual(events[-1]["receipt"]["model_observed"], "synthetic-pi-model")
        self.assertEqual("".join(e.get("text", "") for e in events), "Synthetic reply")
        self.assertEqual(
            events[-1]["receipt"]["request_id"],
            self.fixture.runtime.rows[-1]["request_id"],
        )

    def test_anthropic_real_pi_ai_complete_and_exact_receipt(self):
        events = self.run_chat("anthropic")
        self.assertEqual(events[-1]["type"], "finish", events)
        self.assertEqual(events[-1]["receipt"]["model_observed"], "synthetic-pi-model")
        self.assertEqual("".join(e.get("text", "") for e in events), "Synthetic reply")
        self.assertEqual(
            events[-1]["receipt"]["request_id"],
            self.fixture.runtime.rows[-1]["request_id"],
        )

    def test_responses_real_pi_ai_truncated_is_refused(self):
        events = self.run_chat("responses", "truncated")
        self.assertEqual(events[-1]["type"], "error", events)

    def test_responses_real_pi_ai_contradictory_identity_is_refused(self):
        events = self.run_chat("responses", "contradictory")
        self.assertEqual(events[-1].get("code"), "chat_identity", events)


class TerminalValidationTest(unittest.TestCase):
    def test_responses_done_requires_one_valid_completed_event(self):
        text = json.dumps(
            {"type": "response.output_text.delta", "delta": "text"}
        ).encode()
        completed = json.dumps(
            {"type": "response.completed", "response": {"status": "completed"}}
        ).encode()
        parser = TextStream("responses")
        parser.event(text)
        with self.assertRaises(ValueError):
            parser.event(b"[DONE]")
        parser = TextStream("responses")
        parser.event(text)
        parser.event(completed)
        parser.event(b"[DONE]")
        parser.finish()
        for late in (b"[DONE]", text, completed):
            with self.subTest(late=late), self.assertRaises(ValueError):
                parser.event(late)

    def test_responses_incomplete_output_or_details_never_succeed(self):
        variants = [
            {"status": "incomplete"},
            {
                "status": "completed",
                "incomplete_details": {"reason": "max_output_tokens"},
            },
            {"status": "completed", "incomplete_details": {}},
            {
                "status": "completed",
                "output": [{"type": "message", "status": "incomplete"}],
            },
            {
                "status": "completed",
                "output": [{"type": "message", "content": [{"type": "refusal"}]}],
            },
            {"status": "completed", "output": [{"type": "function_call"}]},
        ]
        for response in variants:
            with self.subTest(response=response):
                parser = TextStream("responses")
                parser.event(
                    json.dumps(
                        {
                            "type": "response.output_text.delta",
                            "delta": "Partial useful-looking text",
                        }
                    ).encode()
                )
                with self.assertRaises(ValueError):
                    parser.event(
                        json.dumps(
                            {"type": "response.completed", "response": response}
                        ).encode()
                    )

    def test_no_done_marker_missing_stop_tools_or_text_after_stop(self):
        cases = [
            [b"[DONE]"],
            [json.dumps({"choices": [{"delta": {"tool_calls": [{}]}}]}).encode()],
            [
                json.dumps(
                    {"choices": [{"delta": {}, "finish_reason": "stop"}]}
                ).encode(),
                json.dumps({"choices": [{"delta": {"content": "late"}}]}).encode(),
            ],
        ]
        for events in cases:
            with self.subTest(events=events), self.assertRaises(ValueError):
                parser = TextStream("chat")
                for event in events:
                    parser.event(event)
                parser.finish()


if __name__ == "__main__":
    unittest.main()
