"""Real pi-ai integration against synthetic, loopback-only providers."""

import base64
import copy
import http.client
import json
import os
import subprocess
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import desktop_pi
import omr
from desktop_engine import Runtime, default_config, validate_config
from test_desktop import connection

CANARY = "synthetic-secret-canary-not-a-real-key"


class PiAiTest(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.wires = []
        self.behavior = "text"
        self.arrived = threading.Event()
        self.release = threading.Event()
        owner = self

        class Provider(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                raw = self.rfile.read(int(self.headers["Content-Length"]))
                owner.wires.append(raw)
                body = json.loads(raw)
                owner.calls.append((self.path, dict(self.headers), body))
                owner.arrived.set()
                if owner.behavior == "error":
                    self.send_response(401)
                    self.end_headers()
                    self.wfile.write(CANARY.encode())
                    return
                if owner.behavior == "redirect":
                    self.send_response(307)
                    self.send_header(
                        "Location", f"http://127.0.0.1:{self.server.server_port}/stolen"
                    )
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()

                def event(kind, **fields):
                    item = dict(type=kind, **fields)
                    self.wfile.write(
                        (f"event: {kind}\ndata: " + json.dumps(item) + "\n\n").encode()
                    )
                    self.wfile.flush()

                if self.path in ("/v1/chat/completions", "/api/v1/chat/completions"):
                    for chunk in [
                        {
                            "id": "chat_synthetic",
                            "model": body["model"],
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {
                                        "role": "assistant",
                                        "content": "Synthetic reply",
                                    },
                                    "finish_reason": None,
                                }
                            ],
                        },
                        {
                            "id": "chat_synthetic",
                            "model": body["model"],
                            "choices": [
                                {"index": 0, "delta": {}, "finish_reason": "stop"}
                            ],
                            "usage": {
                                "prompt_tokens": 7,
                                "completion_tokens": 3,
                                "total_tokens": 10,
                            },
                        },
                    ]:
                        self.wfile.write(
                            ("data: " + json.dumps(chunk) + "\n\n").encode()
                        )
                        self.wfile.flush()
                        if owner.behavior == "hold_chat" and chunk["choices"][0]["delta"]:
                            owner.release.wait(5)
                    self.wfile.write(b"data: [DONE]\n\n")
                    return
                if self.path == "/v1/messages":
                    event(
                        "message_start",
                        message={
                            "id": "msg_synthetic",
                            "type": "message",
                            "role": "assistant",
                            "model": body["model"],
                            "content": [],
                            "stop_reason": None,
                            "usage": {"input_tokens": 7, "output_tokens": 0},
                        },
                    )
                    event(
                        "content_block_start",
                        index=0,
                        content_block={"type": "text", "text": ""},
                    )
                    event(
                        "content_block_delta",
                        index=0,
                        delta={"type": "text_delta", "text": "Synthetic reply"},
                    )
                    event("content_block_stop", index=0)
                    if owner.behavior == "contradictory":
                        event("message_delta", message={"model": "different-model"},
                              delta={"stop_reason": "end_turn", "stop_sequence": None},
                              usage={"output_tokens": 3})
                    else:
                        event(
                            "message_delta",
                            delta={"stop_reason": "end_turn", "stop_sequence": None},
                            usage={"output_tokens": 3},
                        )
                    event("message_stop")
                    return
                response = {
                    "id": "resp_synthetic",
                    "object": "response",
                    "status": "in_progress",
                    "model": body["model"],
                    "output": [],
                }
                if owner.behavior == "no_metadata":
                    response.pop("model")
                if owner.behavior == "alias":
                    response["model"] = "synthetic-served-alias"
                try:
                    event("response.created", response=response)
                    if owner.behavior == "stall":
                        owner.release.wait(5)
                        return
                    if owner.behavior == "tool":
                        item = {
                            "id": "fc_synthetic",
                            "type": "function_call",
                            "call_id": "call_synthetic",
                            "name": "lookup",
                            "arguments": "",
                        }
                        event("response.output_item.added", output_index=0, item=item)
                        event(
                            "response.function_call_arguments.delta",
                            output_index=0,
                            item_id=item["id"],
                            delta='{"city":"Paris"}',
                        )
                        item["arguments"] = '{"city":"Paris"}'
                        event(
                            "response.function_call_arguments.done",
                            output_index=0,
                            item_id=item["id"],
                            arguments=item["arguments"],
                        )
                    else:
                        item = {
                            "id": "msg_synthetic",
                            "type": "message",
                            "role": "assistant",
                            "content": [],
                        }
                        event("response.output_item.added", output_index=0, item=item)
                        event(
                            "response.content_part.added",
                            output_index=0,
                            content_index=0,
                            part={"type": "output_text", "text": "", "annotations": []},
                        )
                        event(
                            "response.output_text.delta",
                            output_index=0,
                            content_index=0,
                            item_id=item["id"],
                            delta="Synthetic reply",
                        )
                        item["content"] = [
                            {
                                "type": "output_text",
                                "text": "Synthetic reply",
                                "annotations": [],
                            }
                        ]
                    if owner.behavior == "truncated":
                        return
                    if owner.behavior == "stream_error":
                        event("error", message=CANARY, code="synthetic_error")
                        return
                    event("response.output_item.done", output_index=0, item=item)
                    response.update(
                        status="completed",
                        output=[item],
                        usage={
                            "input_tokens": 7,
                            "output_tokens": 3,
                            "total_tokens": 10,
                        },
                    )
                    if owner.behavior == "no_metadata":
                        response.pop("usage")
                    if owner.behavior == "contradictory":
                        response["model"] = "different-model"
                    event("response.completed", response=response)
                except (OSError, BrokenPipeError):
                    pass

        self.provider = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
        self.provider.daemon_threads = True
        threading.Thread(target=self.provider.serve_forever, daemon=True).start()
        self.addCleanup(self.provider.server_close)
        self.addCleanup(self.provider.shutdown)
        self.addCleanup(self.release.set)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.runtime = Runtime(Path(self.directory.name), "k" * 48)
        self.config = default_config()
        self.conn = connection("synthetic-pi-model")
        self.conn.update(
            url=f"http://[::ffff:127.0.0.1]:{self.provider.server_port}/v1", transport="pi-ai"
        )
        self.conn["models"][0]["protocols"] = ["responses"]
        self.config["connections"] = [self.conn]

    def start(self):
        self.runtime.save_config(self.config, 0)
        self.runtime.secrets[self.conn["id"]] = CANARY
        self.gateway = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            omr.handler(
                {
                    "routes": {
                        "unused": {
                            # Match desktop_sidecar: selection comes from Runtime,
                            # not this unused legacy route's URL contract.
                            "url": "http://127.0.0.1:1/v1",
                            "model": "unused",
                            "protocol": "responses",
                        }
                    },
                    "default_route": "unused",
                    "timeout_seconds": 3,
                },
                self.runtime,
            ),
        )
        threading.Thread(target=self.gateway.serve_forever, daemon=True).start()
        self.addCleanup(self.gateway.server_close)
        self.addCleanup(self.gateway.shutdown)

    def request(self, _path="/v1/responses", **fields):
        client = http.client.HTTPConnection(
            "127.0.0.1", self.gateway.server_port, timeout=10
        )
        context = (
            {"input": "Synthetic task"}
            if _path == "/v1/responses"
            else {"messages": [{"role": "user", "content": "Synthetic task"}]}
        )
        data = {
            "model": f"direct/{self.conn['id']}/{self.conn['models'][0]['id']}",
            **context,
            **fields,
        }
        client.request(
            "POST",
            _path,
            json.dumps(data),
            {"Authorization": "Bearer " + "k" * 48, "Content-Type": "application/json"},
        )
        response = client.getresponse()
        result = response.status, response.read()
        client.close()
        end = time.monotonic() + 3
        while self.runtime.active and time.monotonic() < end:
            time.sleep(0.01)
        return result

    def test_direct_http_routes_to_loopback_provider_with_synthetic_key(self):
        self.conn["transport"] = "http"
        self.conn["models"][0]["protocols"] = ["chat"]
        self.start()
        status, body = self.request("/v1/chat/completions", stream=True)
        self.assertEqual(status, 200)
        self.assertIn(b"Synthetic reply", body)
        self.assertEqual(len(self.calls), 1)
        path, headers, sent = self.calls[0]
        self.assertEqual(path, "/v1/chat/completions")
        self.assertEqual(headers["Authorization"], "Bearer " + CANARY)
        self.assertEqual(sent["model"], "synthetic-pi-model")
        self.assertNotIn(CANARY.encode(), body)

    def test_configuration_and_route_keep_the_transport(self):
        validate_config(self.config)
        self.start()
        _, route = self.runtime.select(
            {"model": f"direct/{self.conn['id']}/{self.conn['models'][0]['id']}"},
            "responses",
            None,
            {},
            None,
            0,
        )
        self.assertEqual(route["transport"], "pi-ai")
        for value in ("typo", None, {}):
            invalid = copy.deepcopy(self.config)
            invalid["connections"][0]["transport"] = value
            with self.assertRaisesRegex(ValueError, "invalid_config"):
                validate_config(invalid)

    def test_openrouter_official_base_is_accepted_only_by_pi_ai(self):
        self.conn["url"] = "https://openrouter.ai/api/v1"
        validate_config(self.config)
        self.conn["transport"] = "http"
        with self.assertRaisesRegex(ValueError, "invalid_config"):
            validate_config(self.config)
        self.conn.pop("transport")
        with self.assertRaisesRegex(ValueError, "invalid_config"):
            validate_config(self.config)

    def test_openrouter_base_keeps_url_security_restrictions(self):
        for url in (
            "https://user@openrouter.ai/api/v1",
            "https://user:pass@openrouter.ai/api/v1",
            "https://openrouter.ai/api/v1?key=synthetic",
            "https://openrouter.ai/api/v1#synthetic",
            "https://openrouter.ai:0/api/v1",
            "https://openrouter.ai:bad/api/v1",
            "https://openrouter.ai/api/v1/",
            "https://openrouter.ai/other/v1",
        ):
            with self.subTest(url=url):
                self.conn["url"] = url
                with self.assertRaisesRegex(ValueError, "invalid_config"):
                    validate_config(self.config)
        for host in ("localhost", "127.0.0.1", "[::1]", "192.168.1.211", "ollama.lan"):
            for path in ("/v1", "/api/v1"):
                self.conn["url"] = f"http://{host}:9999{path}"
                validate_config(self.config)

    @staticmethod
    def provider_pin():
        return {
            "only": ["cohere"],
            "allow_fallbacks": False,
            "max_price": {"prompt": 0, "completion": 0},
        }

    def test_openrouter_pin_survives_pi_ai_parser_on_v1_base(self):
        self.conn["models"][0]["protocols"] = ["chat"]
        self.start()
        status, raw = self.request(
            _path="/v1/chat/completions", provider=self.provider_pin()
        )
        self.assertEqual(status, 200, raw)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(json.loads(self.wires[-1])["provider"], self.provider_pin())

    def test_openrouter_path_and_provider_pin_reach_actual_wire_json_and_sse(self):
        self.conn["url"] = f"http://[::ffff:127.0.0.1]:{self.provider.server_port}/api/v1"
        self.conn["models"][0].update(
            protocols=["chat"], upstream="cohere/north-mini-code:free"
        )
        self.start()
        for streaming in (False, True):
            with self.subTest(streaming=streaming):
                pin = self.provider_pin()
                before = len(self.calls)
                status, raw = self.request(
                    _path="/v1/chat/completions", stream=streaming,
                    max_tokens=24, provider=pin,
                    stream_options={"include_usage": True},
                )
                self.assertEqual(status, 200, raw)
                self.assertIn(b"Synthetic reply", raw)
                self.assertEqual(len(self.calls), before + 1)
                path, headers, sent = self.calls[-1]
                self.assertEqual(path, "/api/v1/chat/completions")
                self.assertEqual(headers["Authorization"], "Bearer " + CANARY)
                self.assertEqual(sent["model"], "cohere/north-mini-code:free")
                wire = json.loads(self.wires[-1])
                self.assertEqual(wire["provider"], pin)
                self.assertIs(wire["provider"]["allow_fallbacks"], False)
                self.assertIs(type(wire["provider"]["max_price"]["prompt"]), int)
                self.assertTrue(sent["stream"])
                self.assertEqual(sent["max_completion_tokens"], 24)
                self.assertEqual(self.runtime.rows[-1]["status"], "completed")
                self.assertEqual(self.runtime.rows[-1]["transport"], "pi-ai")
                if streaming:
                    self.assertIn(b"data: [DONE]", raw)
                else:
                    data = json.loads(raw)
                    self.assertEqual(data["choices"][0]["message"]["content"], "Synthetic reply")

    def test_openrouter_stream_arrives_before_upstream_terminal(self):
        self.conn["url"] = f"http://[::ffff:127.0.0.1]:{self.provider.server_port}/api/v1"
        self.conn["models"][0]["protocols"] = ["chat"]
        self.behavior = "hold_chat"
        self.start()
        client = http.client.HTTPConnection("127.0.0.1", self.gateway.server_port, timeout=3)
        self.addCleanup(client.close)
        client.request("POST", "/v1/chat/completions", json.dumps({
            "model": f"direct/{self.conn['id']}/{self.conn['models'][0]['id']}",
            "messages": [{"role": "user", "content": "Synthetic task"}],
            "stream": True, "provider": self.provider_pin(),
        }), {"Authorization": "Bearer " + self.runtime.key, "Content-Type": "application/json"})
        response = client.getresponse()
        self.assertEqual(response.status, 200)
        observed = bytearray()
        while b"Synthetic reply" not in observed:
            chunk = response.read(1)
            self.assertTrue(chunk, observed)
            observed.extend(chunk)
        self.assertFalse(self.release.is_set(), "delta must arrive while terminal is held")
        self.assertNotIn(b"[DONE]", observed)
        self.assertEqual(json.loads(self.wires[-1])["provider"], self.provider_pin())
        self.release.set()
        self.assertIn(b"data: [DONE]", response.read())

    def test_openrouter_provider_variants_fail_before_network(self):
        self.conn["models"][0]["protocols"] = ["chat", "responses", "anthropic"]
        self.start()
        pin = self.provider_pin()
        variants = [None, False, "cohere", [], {},
            {k: v for k, v in pin.items() if k != "only"},
            {k: v for k, v in pin.items() if k != "allow_fallbacks"},
            {k: v for k, v in pin.items() if k != "max_price"},
            {**pin, "order": ["cohere"]},
            {**pin, "data_collection": "deny"},
        ]
        variants += [{**pin, "only": value} for value in (
            [], ["cohere", "google"], "cohere", [""], [None], [1],
            ["Cohere"], [" cohere"], ["cohere\n"], ["x" * 129],
        )]
        variants += [{**pin, "allow_fallbacks": value} for value in (True, None, 0, "false")]
        variants += [{**pin, "max_price": value} for value in (
            None, 0, [], {}, {"prompt": 0}, {"completion": 0},
            {"prompt": 0, "completion": 0, "request": 0},
        )]
        for name in ("prompt", "completion"):
            variants += [{**pin, "max_price": {**pin["max_price"], name: value}}
                         for value in (None, False, "0", -1, 0.01)]
        for value in variants:
            with self.subTest(provider=value):
                self.assert_preflight_refused("/v1/chat/completions", provider=value)
        for path in ("/v1/responses", "/v1/messages"):
            with self.subTest(path=path):
                self.assert_preflight_refused(path, provider=pin, max_tokens=16)
        self.assertEqual(self.calls, [])

    def test_openrouter_pin_never_retries_or_follows_redirect(self):
        self.conn["url"] = f"http://[::ffff:127.0.0.1]:{self.provider.server_port}/api/v1"
        self.conn["models"][0]["protocols"] = ["chat"]
        self.start()
        for behavior in ("error", "redirect"):
            with self.subTest(behavior=behavior):
                self.behavior = behavior
                before = len(self.calls)
                status, raw = self.request(_path="/v1/chat/completions", provider=self.provider_pin())
                self.assertEqual(status, 502, raw)
                self.assertEqual(len(self.calls), before + 1)
                self.assertNotIn(CANARY.encode(), raw)
                self.assertEqual(json.loads(self.wires[-1])["provider"], self.provider_pin())

    def test_chat_without_pin_does_not_inject_provider_control(self):
        self.conn["models"][0]["protocols"] = ["chat"]
        self.start()
        status, raw = self.request(_path="/v1/chat/completions")
        self.assertEqual(status, 200, raw)
        self.assertNotIn("provider", json.loads(self.wires[-1]))

    def test_responses_really_uses_pi_ai_and_preserves_model_usage(self):
        self.start()
        status, raw = self.request()
        self.assertEqual(status, 200, raw)
        data = json.loads(raw)
        self.assertEqual(data["output"][0]["content"][0]["text"], "Synthetic reply")
        path, headers, sent = self.calls[0]
        self.assertEqual(path, "/v1/responses")
        self.assertEqual(headers["Authorization"], "Bearer " + CANARY)
        self.assertTrue(
            sent["stream"],
            "pi-ai always requests upstream streaming, even for JSON clients",
        )
        self.assertEqual(sent["model"], "synthetic-pi-model")
        self.assertEqual(self.runtime.rows[-1]["transport"], "pi-ai")
        self.assertEqual(self.runtime.rows[-1]["status"], "completed")
        self.assertNotIn(CANARY, json.dumps(self.runtime.snapshot()))

    def test_responses_contradictory_identity_is_unverified(self):
        self.behavior = "contradictory"
        self.start()
        status, _ = self.request(stream=True)
        self.assertEqual(status, 200)
        self.assertIsNone(self.runtime.rows[-1]["model_observed"])
        self.assertTrue(self.runtime.rows[-1]["model_identity_unrecognized"])

    def test_anthropic_contradictory_identity_is_unverified(self):
        self.behavior = "contradictory"
        self.conn["models"][0]["protocols"] = ["anthropic"]
        self.start()
        status, _ = self.request("/v1/messages", stream=True, max_tokens=100)
        self.assertEqual(status, 200)
        self.assertIsNone(self.runtime.rows[-1]["model_observed"])
        self.assertTrue(self.runtime.rows[-1]["model_identity_unrecognized"])

    def test_pi_ai_encoder_model_is_not_provider_identity_evidence(self):
        self.behavior = "no_metadata"
        self.start()
        status, raw = self.request()
        self.assertEqual(status, 200, raw)
        self.assertIsNone(self.runtime.rows[-1]["model_observed"])
        self.assertEqual(self.runtime.rows[-1]["upstream_status"], 200)
        self.assertEqual(self.runtime.rows[-1]["pi_ai_bridge_status"], 200)
        self.assertEqual(self.runtime.rows[-1]["model_identity_source"], "not_reported")
        self.assertEqual(self.runtime.rows[-1]["usage"], {})
        self.assertIsNone(self.runtime.rows[-1]["observed_input_tokens"])
        self.behavior = "alias"
        status, raw = self.request(stream=True)
        self.assertEqual(status, 200, raw)
        self.assertIsNone(self.runtime.rows[-1]["model_observed"])
        self.assertTrue(self.runtime.rows[-1]["model_identity_unrecognized"])
        self.assertEqual(self.runtime.rows[-1]["usage"]["input_tokens"], 7)

    def test_model_effort_and_output_limit_reach_pi_ai(self):
        self.conn["models"][0]["effort"] = "high"
        self.start()
        status, raw = self.request(max_output_tokens=48)
        self.assertEqual(status, 200, raw)
        self.assertEqual(self.calls[-1][2]["reasoning"]["effort"], "high")
        self.assertEqual(self.calls[-1][2]["max_output_tokens"], 48)
        self.assertEqual(self.runtime.rows[-1]["effort_transmitted"], "high")

    def test_responses_done_marker_cannot_erase_completed_terminal(self):
        self.start()
        status, raw = self.request(stream=True)
        self.assertEqual(status, 200, raw)
        self.assertNotIn(b"event: error", raw)
        self.assertEqual(self.runtime.rows[-1]["status"], "completed")

    def test_streaming_and_tool_roundtrip(self):
        self.start()
        self.behavior = "tool"
        tools = [
            {
                "type": "function",
                "name": "lookup",
                "description": "Synthetic lookup",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            }
        ]
        status, raw = self.request(stream=True, tools=tools)
        self.assertEqual(status, 200, raw)
        self.assertIn(b"response.function_call_arguments.delta", raw)
        self.assertIn(b"response.completed", raw)
        frames = [
            json.loads(line[6:])
            for line in raw.splitlines()
            if line.startswith(b"data: ") and line != b"data: [DONE]"
        ]
        completed = next(
            frame["response"]
            for frame in frames
            if frame["type"] == "response.completed"
        )
        call = next(
            item for item in completed["output"] if item["type"] == "function_call"
        )
        self.behavior = "text"
        status, raw = self.request(
            input=[
                {"role": "user", "content": "Synthetic task"},
                call,
                {
                    "type": "function_call_output",
                    "call_id": call["call_id"],
                    "output": "Synthetic result",
                },
            ],
            tools=tools,
        )
        self.assertEqual(status, 200, raw)
        sent = self.calls[-1][2]
        self.assertTrue(
            any(
                item.get("type") == "function_call_output"
                and item["output"] == "Synthetic result"
                for item in sent["input"]
            )
        )
        self.assertEqual(len(self.calls), 2)

    def test_errors_and_redirects_do_not_retry_or_leak(self):
        self.start()
        for behavior in ("error", "redirect", "stream_error", "truncated"):
            self.behavior = behavior
            before = len(self.calls)
            status, raw = self.request(stream=behavior == "stream_error")
            self.assertEqual(status, 200 if behavior == "stream_error" else 502, raw)
            self.assertNotIn(CANARY.encode(), raw)
            self.assertEqual(len(self.calls), before + 1)
            self.assertNotEqual(self.runtime.rows[-1]["status"], "completed")
            self.assertNotIn(CANARY, json.dumps(self.runtime.snapshot()))

    def test_chat_anthropic_streaming_and_json_use_their_pi_adapters(self):
        self.conn["models"][0]["protocols"] = ["chat", "anthropic"]
        self.start()
        for path in ("/v1/chat/completions", "/v1/messages"):
            for streaming in (False, True):
                status, raw = self.request(_path=path, stream=streaming, max_tokens=16)
                self.assertEqual(status, 200, raw)
                self.assertIn(b"Synthetic reply", raw)
                self.assertEqual(self.calls[-1][0], path)
                auth_headers = {k.lower(): v for k, v in self.calls[-1][1].items()}
                # pi-ai uses Bearer on non-official Anthropic-compatible URLs;
                # the official Anthropic host's x-api-key policy is inspected,
                # not exercised by these loopback-only tests.
                self.assertEqual(auth_headers["authorization"], "Bearer " + CANARY)
                self.assertEqual(self.calls[-1][2]["model"], "synthetic-pi-model")
                self.assertEqual(
                    self.calls[-1][2][
                        "max_tokens"
                        if path.endswith("messages")
                        else "max_completion_tokens"
                    ],
                    16,
                )
                self.assertEqual(self.runtime.rows[-1]["status"], "completed")
        direct = f"direct/{self.conn['id']}/{self.conn['models'][0]['id']}"
        self.runtime.port = self.gateway.server_port
        self.runtime.verify_generation(direct, True)
        self.assertEqual(self.runtime.rows[-1]["transport"], "pi-ai")

    def test_transport_change_invalidates_generation_qualification(self):
        self.start()
        model_id = self.conn["models"][0]["id"]
        self.runtime.model_states[model_id] = {"generation": "verified"}
        updated = copy.deepcopy(self.config)
        updated["connections"][0]["transport"] = "http"
        self.runtime.save_config(updated, 1)
        self.assertNotIn(model_id, self.runtime.model_states)

    def test_no_key_means_no_ambient_credentials(self):
        self.start()
        self.runtime.secrets.clear()
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": CANARY,
                "ANTHROPIC_API_KEY": CANARY,
                "HTTPS_PROXY": "http://127.0.0.1:1",
            },
        ):
            status, raw = self.request()
        self.assertEqual(status, 200, raw)
        self.assertNotIn("Authorization", self.calls[-1][1])
        self.assertNotIn(CANARY, json.dumps(self.calls))

    def test_disconnect_kills_the_private_process_and_reaps_it(self):
        self.start()
        self.behavior = "stall"
        spawned = []
        real_popen = desktop_pi.subprocess.Popen

        def spawn(*args, **kwargs):
            proc = real_popen(*args, **kwargs)
            spawned.append(proc)
            self.assertNotIn(CANARY, repr(args) + repr(kwargs))
            return proc

        with patch.object(desktop_pi.subprocess, "Popen", side_effect=spawn):
            client = http.client.HTTPConnection(
                "127.0.0.1", self.gateway.server_port, timeout=5
            )
            payload = {
                "model": f"direct/{self.conn['id']}/{self.conn['models'][0]['id']}",
                "input": "Synthetic cancellation",
            }
            client.request(
                "POST",
                "/v1/responses",
                json.dumps(payload),
                {
                    "Authorization": "Bearer " + self.runtime.key,
                    "Content-Type": "application/json",
                },
            )
            self.assertTrue(self.arrived.wait(3))
            client.close()
            end = time.monotonic() + 2
            while self.runtime.active and time.monotonic() < end:
                time.sleep(0.01)
            self.assertEqual(self.runtime.active, 0)
            self.assertEqual(self.runtime.rows[-1]["status"], "cancelled")
            self.assertIsNotNone(spawned[0].poll())

    def test_engine_stop_cancels_provider_before_acknowledgement(self):
        self.start()
        self.behavior = "stall"
        client = http.client.HTTPConnection(
            "127.0.0.1", self.gateway.server_port, timeout=5
        )
        client.request(
            "POST",
            "/v1/responses",
            json.dumps(
                {
                    "model": f"direct/{self.conn['id']}/{self.conn['models'][0]['id']}",
                    "input": "Synthetic engine stop",
                }
            ),
            {
                "Authorization": "Bearer " + self.runtime.key,
                "Content-Type": "application/json",
            },
        )
        self.assertTrue(self.arrived.wait(2))
        self.runtime.stopping = True
        end = time.monotonic() + 1
        while self.runtime.active and time.monotonic() < end:
            time.sleep(0.01)
        client.close()
        self.assertEqual(self.runtime.active, 0)
        self.assertEqual(self.runtime.rows[-1]["status"], "cancelled")

    def test_store_false_reaches_each_supported_upstream(self):
        self.conn["models"][0]["protocols"] = ["responses", "chat"]
        self.start()
        for path in ("/v1/responses", "/v1/chat/completions"):
            with self.subTest(path=path):
                before = len(self.calls)
                status, raw = self.request(_path=path, store=False)
                self.assertEqual(status, 200, raw)
                self.assertEqual(len(self.calls), before + 1)
                self.assertIs(self.calls[-1][2].get("store"), False)

    def test_codex_long_private_requests_keep_plain_json_before_wire(self):
        root = Path(__file__).parent / "desktop/provider-runtime"
        bun = root / "node_modules/.bin/bun"
        self.assertTrue(bun.is_file(), "The pinned build-time Bun is required")
        payload = base64.urlsafe_b64encode(
            json.dumps({"https://api.openai.com/auth": {"chatgpt_account_id": "synthetic-account"}}).encode()
        ).decode().rstrip("=")
        preload = Path(self.directory.name) / "closed-codex-fetch.ts"
        preload.write_text(
            "const nativeFetch=globalThis.fetch;\n"
            "globalThis.WebSocket=class{constructor(){throw new Error('unexpected_test_websocket')}} as any;\n"
            "globalThis.fetch=(input,init)=>{\n"
            "const url=input instanceof Request?input.url:String(input);\n"
            "if(url!=='https://chatgpt.com/backend-api/codex/responses')throw new Error('unexpected_test_network');\n"
            "return nativeFetch("
            + json.dumps(f"http://127.0.0.1:{self.provider.server_port}/v1/responses")
            + ",init);};\n"
        )
        original_popen = subprocess.Popen

        def launch(_command, **kwargs):
            return original_popen(
                [str(bun), "--preload", str(preload), str(root / "bridge.ts")],
                **kwargs,
            )

        route = {
            "url": "https://chatgpt.com/backend-api/codex",
            "subscription": "codex",
            "_secret": "synthetic." + payload + ".synthetic",
        }
        for protocol in ("chat", "responses"):
            with self.subTest(protocol=protocol), patch.object(
                desktop_pi, "executable", return_value=root / "bridge.ts"
            ), patch.object(desktop_pi.subprocess, "Popen", side_effect=launch), patch.dict(
                os.environ, {"PI_REQUEST_COMPRESSION": "1"}
            ):
                body = {"model": "gpt-6.1-sol", "stream": True, "store": False}
                body.update(
                    {"messages": [{"role": "user", "content": "Synthetic task " * 1024}]}
                    if protocol == "chat"
                    else {"input": "Synthetic task " * 1024}
                )
                before = len(self.calls)
                connection = desktop_pi.PiConnection(
                    route, protocol, threading.Event(), time.monotonic() + 20
                )
                try:
                    connection.request("POST", "/unused", json.dumps(body), {})
                    response = connection.getresponse()
                    self.assertEqual(response.status, 200)
                    chunks = []
                    while chunk := response.read1(16384):
                        chunks.append(chunk)
                    self.assertIn(b"Synthetic reply", b"".join(chunks))
                    self.assertEqual(len(self.calls), before + 1)
                    headers = {key.lower(): value for key, value in self.calls[-1][1].items()}
                    self.assertNotIn("content-encoding", headers)
                    self.assertIs(self.calls[-1][2]["store"], False)
                finally:
                    connection.close()

    def test_codex_store_policy_is_preserved_or_refused_before_wire(self):
        root = Path(__file__).parent / "desktop/provider-runtime"
        bun = root / "node_modules/.bin/bun"
        self.assertTrue(bun.is_file(), "The pinned build-time Bun is required")
        payload = base64.urlsafe_b64encode(
            json.dumps(
                {
                    "https://api.openai.com/auth": {
                        "chatgpt_account_id": "synthetic-account"
                    }
                }
            ).encode()
        ).decode().rstrip("=")
        token = "synthetic." + payload + ".synthetic"
        preload = Path(self.directory.name) / "synthetic-codex-fetch.ts"
        # Mock only the public network boundary, never the production URL guard.
        preload.write_text(
            "const nativeFetch = globalThis.fetch;\n"
            "globalThis.fetch = (input, init) => {\n"
            " const url = input instanceof Request ? input.url : String(input);\n"
            " if (url !== 'https://chatgpt.com/backend-api/codex/responses') throw new Error('unexpected_test_network');\n"
            " return nativeFetch("
            + json.dumps(f"http://127.0.0.1:{self.provider.server_port}/v1/responses")
            + ", init);\n};\n"
        )
        for protocol, store in (
            (protocol, store)
            for protocol in ("responses", "chat")
            for store in (False, True, None, 0, 1, "false", [], {})
        ):
            with self.subTest(protocol=protocol, store=store):
                body = {
                    "model": "synthetic-pi-model", "stream": True, "store": store
                }
                body.update(
                    {"input": "Synthetic task"}
                    if protocol == "responses"
                    else {"messages": [{"role": "user", "content": "Synthetic task"}]}
                )
                before = len(self.calls)
                result = subprocess.run(
                    [str(bun), "--preload", str(preload), str(root / "bridge.ts")],
                    input=json.dumps(
                        {
                            "protocol": protocol,
                            "url": "https://chatgpt.com/backend-api/codex",
                            "key": token,
                            "subscription": "codex",
                            "body": body,
                        }
                    ),
                    env={
                        "HOME": self.directory.name,
                        "TMPDIR": self.directory.name,
                        "PATH": "",
                        "NO_PROXY": "*",
                        "no_proxy": "*",
                    },
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                packets = [json.loads(line) for line in result.stdout.splitlines()]
                self.assertEqual(
                    packets[0]["status"], 200 if store is False else 400, packets
                )
                if store is not False:
                    self.assertEqual(len(self.calls), before)
                    continue
                self.assertEqual(len(self.calls), before + 1)
                self.assertIs(self.calls[-1][2].get("store"), False)
                headers = {k.lower(): v for k, v in self.calls[-1][1].items()}
                self.assertEqual(headers.get("authorization"), "Bearer " + token)
                self.assertEqual(headers.get("chatgpt-account-id"), "synthetic-account")
                wire = b"".join(
                    base64.b64decode(p["chunk"]) for p in packets if "chunk" in p
                )
                self.assertIn(b"Synthetic reply", wire)

    def test_store_true_and_malformed_values_never_contact_upstream(self):
        self.conn["models"][0]["protocols"] = ["responses", "chat"]
        self.start()
        for path in ("/v1/responses", "/v1/chat/completions"):
            for value in (True, None, 0, 1, "false", [], {}):
                with self.subTest(path=path, store=value):
                    self.assert_preflight_refused(path, store=value)

    def test_unsupported_options_fail_before_provider_call(self):
        self.start()
        status, raw = self.request(previous_response_id="resp_private")
        self.assertGreaterEqual(status, 400, raw)
        self.assertEqual(self.calls, [])

    def test_unsupported_nested_option_is_not_silently_dropped(self):
        self.start()
        status, raw = self.request(reasoning={"effort": "high", "summary": "detailed"})
        self.assertGreaterEqual(status, 400, raw)
        self.assertEqual(self.calls, [])

    def assert_preflight_refused(self, path="/v1/responses", **fields):
        before = len(self.calls)
        status, raw = self.request(_path=path, **fields)
        self.assertEqual(status, 400, raw)
        self.assertEqual(
            len(self.calls), before, "refusal must precede provider contact"
        )
        self.assertNotIn(CANARY.encode(), raw)

    def test_responses_allowed_tools_cannot_weaken_required_allowlist(self):
        self.start()
        self.assert_preflight_refused(
            tools=[
                {"type": "function", "name": name, "parameters": {"type": "object"}}
                for name in ("safe", "danger")
            ],
            tool_choice={
                "type": "allowed_tools",
                "mode": "required",
                "tools": [{"type": "function", "name": "safe"}],
            },
        )

    def test_anthropic_parallel_control_cannot_be_dropped(self):
        self.conn["models"][0]["protocols"] = ["anthropic"]
        self.start()
        for value in (True, False):
            with self.subTest(value=value):
                self.assert_preflight_refused(
                    "/v1/messages",
                    tool_choice={"type": "auto", "disable_parallel_tool_use": value},
                    max_tokens=16,
                )

    def test_chat_explicit_strictness_cannot_be_rewritten(self):
        self.conn["models"][0]["protocols"] = ["chat"]
        self.start()
        for value in (False, True):
            with self.subTest(value=value):
                self.assert_preflight_refused(
                    "/v1/chat/completions",
                    tools=[
                        {
                            "type": "function",
                            "function": {
                                "name": "safe",
                                "strict": value,
                                "parameters": {
                                    "type": "object",
                                    "properties": {"optional": {"type": "string"}},
                                },
                            },
                        }
                    ],
                )

    def test_anthropic_does_not_request_cache_without_client_policy(self):
        self.conn["models"][0]["protocols"] = ["anthropic"]
        self.start()
        status, raw = self.request(
            _path="/v1/messages",
            max_tokens=16,
            system=[{"type": "text", "text": "Synthetic instructions"}],
            tools=[
                {"name": "safe", "input_schema": {"type": "object", "properties": {}}}
            ],
        )
        self.assertEqual(status, 200, raw)
        sent = self.calls[-1][2]
        self.assertNotIn("cache_control", json.dumps(sent))
        self.assertNotIn("prompt_cache_retention", sent)

    def test_explicit_cache_policy_is_refused_at_every_envelope(self):
        self.conn["models"][0]["protocols"] = ["anthropic"]
        self.start()
        for ttl in ("1h", "5m", None):
            cc = {"type": "ephemeral", **({"ttl": ttl} if ttl else {})}
            for fields in (
                {
                    "system": [
                        {"type": "text", "text": "Synthetic", "cache_control": cc}
                    ]
                },
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Synthetic",
                                    "cache_control": cc,
                                }
                            ],
                        }
                    ]
                },
                {
                    "tools": [
                        {
                            "name": "safe",
                            "input_schema": {"type": "object"},
                            "cache_control": cc,
                        }
                    ]
                },
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": "call_synthetic",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": "Synthetic",
                                            "cache_control": cc,
                                        }
                                    ],
                                }
                            ],
                        }
                    ]
                },
            ):
                with self.subTest(ttl=ttl, envelope=next(iter(fields))):
                    self.assert_preflight_refused(
                        "/v1/messages", max_tokens=16, **fields
                    )

    def test_unqualified_content_tools_and_nested_controls_fail_before_network(self):
        self.conn["models"][0]["protocols"] = ["chat", "responses", "anthropic"]
        self.start()
        png = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6lVQAAAAASUVORK5CYII="
        cases = [
            (
                "/v1/chat/completions",
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "image_url", "image_url": {"url": png}}
                            ],
                        }
                    ]
                },
            ),
            ("/v1/responses", {"tools": [{"type": "web_search_preview"}]}),
            (
                "/v1/responses",
                {
                    "input": [
                        {
                            "role": "user",
                            "content": [{"type": "input_image", "image_url": png}],
                        }
                    ]
                },
            ),
            (
                "/v1/responses",
                {
                    "input": [
                        {
                            "type": "function_call_output",
                            "call_id": "call_synthetic",
                            "output": [{"type": "input_image", "image_url": png}],
                        }
                    ]
                },
            ),
            (
                "/v1/responses",
                {"input": [{"type": "item_reference", "id": "msg_synthetic"}]},
            ),
            (
                "/v1/responses",
                {
                    "tool_choice": {
                        "type": "function",
                        "name": "safe",
                        "future_control": True,
                    }
                },
            ),
            (
                "/v1/chat/completions",
                {
                    "messages": [
                        {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_synthetic",
                                    "type": "custom",
                                    "custom": {"name": "safe", "input": "Synthetic"},
                                }
                            ],
                        }
                    ]
                },
            ),
            (
                "/v1/chat/completions",
                {
                    "tools": [
                        {
                            "type": "function",
                            "function": {
                                "name": "safe",
                                "parameters": {},
                                "future_control": True,
                            },
                        }
                    ]
                },
            ),
            (
                "/v1/messages",
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "document",
                                    "source": {"type": "text", "data": "Synthetic"},
                                }
                            ],
                        }
                    ]
                },
            ),
            (
                "/v1/messages",
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": "call_synthetic",
                                    "content": [
                                        {
                                            "type": "image",
                                            "source": {
                                                "type": "base64",
                                                "media_type": "image/png",
                                                "data": png.split(",")[1],
                                            },
                                        }
                                    ],
                                }
                            ],
                        }
                    ]
                },
            ),
            (
                "/v1/messages",
                {"tools": [{"type": "web_search_20250305", "name": "web_search"}]},
            ),
        ]
        for path, fields in cases:
            with self.subTest(path=path, fields=fields):
                self.assert_preflight_refused(path, **fields)

    def test_qualified_text_function_choices_and_results_still_reach_provider(self):
        self.conn["models"][0]["protocols"] = ["chat", "responses", "anthropic"]
        self.start()
        # Transport-looking names inside user JSON are data, not cache/options.
        schema = {
            "type": "object",
            "properties": {"cache_control": {"type": "string"}},
            "required": ["cache_control"],
            "additionalProperties": False,
        }
        for path, tools, choice, history in (
            (
                "/v1/responses",
                [{"type": "function", "name": "safe", "parameters": schema}],
                {"type": "function", "name": "safe"},
                {
                    "input": [
                        {
                            "role": "user",
                            "content": [{"type": "input_text", "text": "Synthetic"}],
                        },
                        {
                            "type": "function_call",
                            "call_id": "call_synthetic",
                            "name": "safe",
                            "arguments": '{"cache_control":"data"}',
                        },
                        {
                            "type": "function_call_output",
                            "call_id": "call_synthetic",
                            "output": "Synthetic result",
                        },
                    ]
                },
            ),
            (
                "/v1/chat/completions",
                [
                    {
                        "type": "function",
                        "function": {"name": "safe", "parameters": schema},
                    }
                ],
                {"type": "function", "function": {"name": "safe"}},
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": "Synthetic"}],
                        },
                        {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_synthetic",
                                    "type": "function",
                                    "function": {
                                        "name": "safe",
                                        "arguments": '{"cache_control":"data"}',
                                    },
                                }
                            ],
                        },
                        {
                            "role": "tool",
                            "tool_call_id": "call_synthetic",
                            "content": "Synthetic result",
                        },
                    ]
                },
            ),
            (
                "/v1/messages",
                [{"name": "safe", "input_schema": schema}],
                {"type": "tool", "name": "safe"},
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": "Synthetic"}],
                        },
                        {
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": "call_synthetic",
                                    "name": "safe",
                                    "input": {"cache_control": "data"},
                                }
                            ],
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": "call_synthetic",
                                    "content": [
                                        {"type": "text", "text": "Synthetic result"}
                                    ],
                                }
                            ],
                        },
                    ],
                    "max_tokens": 16,
                },
            ),
        ):
            for streaming in (False, True):
                with self.subTest(path=path, streaming=streaming):
                    status, raw = self.request(
                        _path=path,
                        tools=tools,
                        tool_choice=choice,
                        stream=streaming,
                        **history,
                    )
                    self.assertEqual(status, 200, raw)
                    sent = self.calls[-1][2]
                    self.assertIn("Synthetic result", json.dumps(sent))
                    self.assertIn("cache_control", json.dumps(sent))
                    expected_choice = {
                        "/v1/responses": {"type": "function", "name": "safe"},
                        "/v1/chat/completions": {
                            "type": "function",
                            "function": {"name": "safe"},
                        },
                        "/v1/messages": {"type": "tool", "name": "safe"},
                    }[path]
                    self.assertEqual(sent["tool_choice"], expected_choice)
                    for tool in sent["tools"]:
                        self.assertNotIn("cache_control", tool)

    def test_chat_stream_usage_is_returned_only_when_requested(self):
        self.conn["models"][0]["protocols"] = ["chat"]
        self.start()
        for include in (True, False, None):
            with self.subTest(include=include):
                fields = (
                    {}
                    if include is None
                    else {"stream_options": {"include_usage": include}}
                )
                status, raw = self.request(
                    _path="/v1/chat/completions", stream=True, **fields
                )
                self.assertEqual(status, 200, raw)
                frames = [
                    json.loads(line[6:])
                    for line in raw.splitlines()
                    if line.startswith(b"data: ") and line != b"data: [DONE]"
                ]
                usage = [
                    frame["usage"] for frame in frames if frame.get("usage") is not None
                ]
                if include:
                    self.assertEqual(len(usage), 1, raw)
                    self.assertEqual(usage[0]["prompt_tokens"], 7)
                    self.assertEqual(usage[0]["completion_tokens"], 3)
                    self.assertEqual(usage[0]["total_tokens"], 10)
                else:
                    self.assertEqual(usage, [])

    def test_deadline_terminates_a_stalled_provider(self):
        self.start()
        self.behavior = "stall"
        started = time.monotonic()
        status, raw = self.request()
        self.assertEqual(status, 504, raw)
        self.assertLess(time.monotonic() - started, 6)
        self.assertEqual(self.runtime.active, 0)


if __name__ == "__main__":
    unittest.main()
