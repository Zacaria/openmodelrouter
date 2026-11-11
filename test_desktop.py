import json
import tempfile
import unittest
import uuid
from pathlib import Path


def connection(model="synthetic-small", quality=1, price=1):
    return {
        "id": str(uuid.uuid4()),
        "name": "Synthetic",
        "url": "http://127.0.0.1:9999/v1",
        "models": [
            {
                "id": str(uuid.uuid4()),
                "upstream": model,
                "protocols": ["chat"],
                "enabled": True,
                "tools": True,
                "quality": quality,
                "input_price": price,
                "output_price": price,
                "effort": None,
            }
        ],
    }


class DesktopCatalogueTest(unittest.TestCase):
    def test_catalogue_mixes_profiles_and_exact_direct_identity(self):
        from desktop_engine import Runtime, default_config

        with tempfile.TemporaryDirectory() as d:
            runtime = Runtime(Path(d), "x" * 48)
            config = default_config()
            config["connections"] = [connection("vendor/model:exact")]
            runtime.save_config(config, 0)
            items = runtime.catalogue()["data"]
            self.assertEqual(
                [x["id"] for x in items[:3]],
                ["omr/economy", "omr/balanced", "omr/quality"],
            )
            c = config["connections"][0]
            direct = f"direct/{c['id']}/{c['models'][0]['id']}"
            self.assertEqual(items[3]["id"], direct)
            row = {}
            selected, route = runtime.select(
                {
                    "model": direct,
                    "messages": [{"role": "user", "content": "private-canary"}],
                },
                "chat",
                None,
                row,
                None,
                0,
            )
            self.assertEqual(route["model"], "vendor/model:exact")
            self.assertEqual(row["mode"], "direct")
            self.assertEqual(row["decision_ms"], 0)
            self.assertNotIn("private-canary", json.dumps(row))
            self.assertEqual(selected, c["models"][0]["id"])


class DesktopConfigTest(unittest.TestCase):
    def test_provider_urls_are_strict_for_both_transports(self):
        from desktop_engine import default_config, validate_config

        invalid = [
            "ht\ttp://127.0.0.2:1234/v1", "\nhttp://127.0.0.2/v1",
            "http://127.0.0.2\r/v1", "http://127.0.0.2\x7f/v1",
            "http://@127.0.0.2/v1", "http://user@127.0.0.2/v1",
            "http://127.0.0.2:/v1", "http://127.0.0.2:0/v1",
            "http://127.0.0.2:99999/v1", "http://bad host/v1",
            "http://127.0.0.2\\evil/v1", "http://127.0.0.2/v1?",
            "http://127.0.0.2/v1#", "http:///v1", "ftp://host/v1",
            "http://foo..bar/v1", "http://256.1.2.3/v1", "http://127.1/v1",
            "http://-bad.example/v1", "http://" + "a" * 64 + ".test/v1",
        ]
        for transport in ("http", "pi-ai"):
            config = default_config()
            c = connection()
            c["transport"] = transport
            config["connections"] = [c]
            for url in invalid:
                with self.subTest(transport=transport, url=url):
                    c["url"] = url
                    with self.assertRaisesRegex(ValueError, "invalid_config"):
                        validate_config(config)
            for url in ("http://127.0.0.2:1234/v1", "HTTP://localhost/v1", "https://example.com/v1", "http://[::1]:1234/v1"):
                with self.subTest(transport=transport, url=url):
                    c["url"] = url
                    validate_config(config)

    def test_config_cas_restore_and_no_secret_fields(self):
        from desktop_engine import Runtime, default_config

        with tempfile.TemporaryDirectory() as d:
            runtime = Runtime(Path(d), "k" * 48)
            config = default_config()
            config["connections"] = [connection()]
            runtime.save_config(config, 0)
            with self.assertRaisesRegex(ValueError, "configuration_conflict"):
                runtime.save_config(default_config(), 0)
            poisoned = json.loads(json.dumps(config))
            poisoned["connections"][0]["api_key"] = "secret-canary"
            with self.assertRaisesRegex(ValueError, "invalid_config"):
                runtime.save_config(poisoned, 1)
            poisoned = json.loads(json.dumps(config))
            poisoned["connections"][0]["url"] = "ftp://remote.example/v1"
            with self.assertRaisesRegex(ValueError, "invalid_config"):
                runtime.save_config(poisoned, 1)
            runtime.save_config(default_config(), 1)
            runtime.save_config(runtime.history[1]["config"], 2)
            reloaded = Runtime(Path(d), "k" * 48)
            self.assertEqual(reloaded.config, config)
            self.assertNotIn("secret-canary", Path(d, "config.json").read_text())

    def test_direct_capability_effort_and_snapshot_no_substitution(self):
        from desktop_engine import Runtime, default_config

        with tempfile.TemporaryDirectory() as d:
            runtime = Runtime(Path(d), "k" * 48)
            config = default_config()
            c = connection()
            c["models"][0]["effort"] = "low"
            config["connections"] = [c]
            runtime.save_config(config, 0)
            id_ = runtime.catalogue()["data"][3]["id"]
            with self.assertRaisesRegex(ValueError, "effort_conflict"):
                runtime.select(
                    {"model": id_, "reasoning_effort": "high"},
                    "chat",
                    None,
                    {},
                    None,
                    0,
                )
            with self.assertRaisesRegex(ValueError, "incompatible_protocol"):
                runtime.select({"model": id_}, "responses", None, {}, None, 0)
            _, route = runtime.select({"model": id_}, "chat", None, {}, None, 0)
            c["models"][0]["enabled"] = False
            runtime.save_config(config, 1)
            self.assertEqual(route["model"], "synthetic-small")
            with self.assertRaisesRegex(ValueError, "model_unavailable"):
                runtime.select({"model": id_}, "chat", None, {}, None, 0)


class DesktopPolicyTest(unittest.TestCase):
    def test_bounded_context_preserves_turns_and_rejects_oversize(self):
        from desktop_engine import decision_context, default_config

        config = default_config()
        config.update(context_tokens=256, total_tokens=1024, max_messages=2)
        messages = [
            {"role": "user", "content": "old"},
            {"role": "assistant", "tool_calls": [{"id": "a"}]},
            {"role": "tool", "tool_call_id": "a", "content": "large" * 100},
            {"role": "user", "content": "current"},
        ]
        result, info = decision_context({"messages": messages}, config, [])
        self.assertEqual(result["messages"], [messages[-1]])
        self.assertTrue(info["reduced"])
        self.assertLessEqual(info["total_estimated_tokens"], 1024)
        self.assertEqual(messages[1]["tool_calls"][0]["id"], "a")
        with self.assertRaisesRegex(ValueError, "current_turn_over_budget"):
            decision_context(
                {"messages": [{"role": "user", "content": "x" * 257}]}, config, []
            )

    def test_profiles_reevaluate_cost_switch_tools_and_freeze(self):
        from desktop_engine import Runtime, default_config
        import threading
        import time

        calls = []
        requirement = [1]

        def classify(context, candidates, stopped, deadline):
            calls.append(context)
            return {
                "required_quality": requirement[0],
                "reason": "task_requirement",
                "usage": {"input_tokens": 20, "output_tokens": 5},
            }

        with tempfile.TemporaryDirectory() as d:
            runtime = Runtime(Path(d), "k" * 48)
            runtime.classifier = (
                classify  # synthetic contract test, not a shipped classifier
            )
            config = default_config()
            small, large = connection(price=1), connection("synthetic-large", 3, 10)
            config["connections"] = [small, large]
            runtime.save_config(config, 0)
            session = str(uuid.uuid4())

            def choose(profile="economy", tools=False):
                row = {}
                payload = {
                    "model": "omr/" + profile,
                    "messages": [{"role": "user", "content": "synthetic task"}],
                }
                if tools:
                    payload["messages"].append(
                        {"role": "tool", "tool_call_id": "a", "content": "result"}
                    )
                route = runtime.select(
                    payload,
                    "chat",
                    session,
                    row,
                    threading.Event(),
                    time.monotonic() + 5,
                )[1]
                return route, row

            self.assertEqual(choose()[0]["model"], "synthetic-small")
            requirement[0] = 3
            self.assertEqual(choose()[0]["model"], "synthetic-large")
            requirement[0] = 1
            self.assertEqual(choose(tools=True)[0]["model"], "synthetic-large")
            self.assertEqual(len(calls), 2)
            self.assertEqual(choose()[0]["model"], "synthetic-small")
            self.assertEqual(choose("quality")[0]["model"], "synthetic-large")
            config["reevaluate"] = False
            runtime.save_config(config, 1)
            requirement[0] = 3
            self.assertEqual(choose()[0]["model"], "synthetic-small")
            self.assertNotIn("synthetic task", json.dumps(choose()[1]))
            runtime.classifier = None
            config["decider"] = None
            runtime.save_config(config, 2)
            with self.assertRaisesRegex(ValueError, "decider_not_configured"):
                runtime.select(
                    {
                        "model": "omr/balanced",
                        "messages": [{"role": "user", "content": "public"}],
                    },
                    "chat",
                    None,
                    {},
                    threading.Event(),
                    time.monotonic() + 3,
                )


class DesktopGatewayTest(unittest.TestCase):
    def test_config_and_discovery_with_non_localhost_http_provider(self):
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from desktop_engine import Runtime, default_config

        class Upstream(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                body = b'{"data":[{"id":"synthetic-small"}]}'
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        # IPv4-mapped IPv6 reaches loopback without requiring a 127.0.0.2 alias;
        # its URL host is still outside the former localhost-only allowlist.
        upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
        threading.Thread(target=upstream.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as d:
                runtime = Runtime(Path(d), "x" * 48)
                c = connection()
                c["url"] = f"http://[::ffff:127.0.0.1]:{upstream.server_port}/v1"
                config = default_config()
                config["connections"] = [c]
                runtime.save_config(config, 0)
                self.assertEqual(runtime.discover(c["id"]), ["synthetic-small"])
        finally:
            upstream.shutdown()
            upstream.server_close()

    def test_real_gateway_auth_direct_decider_usage_and_safe_receipts(self):
        import http.client
        import threading
        import time
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import omr
        from desktop_engine import Runtime, default_config

        seen = []

        class Upstream(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                body = json.dumps({"data": [{"id": "synthetic-small"}]}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                payload = json.loads(
                    self.rfile.read(int(self.headers["Content-Length"]))
                )
                seen.append((payload, self.headers.get("Authorization")))
                if payload["model"] == "synthetic-decider":
                    body = {
                        "model": payload["model"],
                        "choices": [
                            {
                                "message": {
                                    "content": json.dumps(
                                        {"required_quality": 1, "reason": "simple"}
                                    )
                                }
                            }
                        ],
                        "usage": {"prompt_tokens": 10, "completion_tokens": 4},
                    }
                else:
                    body = {
                        "model": payload["model"],
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {"content": "private-response-canary"},
                            }
                        ],
                        "usage": {
                            "prompt_tokens": 100,
                            "completion_tokens": 20,
                            "prompt_tokens_details": {"cached_tokens": 30},
                            "completion_tokens_details": {"reasoning_tokens": 5},
                        },
                    }
                encoded = json.dumps(body).encode()
                self.send_response(200)
                if payload.get("stream"):
                    encoded = b"data: " + encoded + b"\n\ndata: [DONE]\n\n"
                    self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

        upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
        threading.Thread(target=upstream.serve_forever, daemon=True).start()
        with tempfile.TemporaryDirectory() as d:
            runtime = Runtime(Path(d), "gateway-canary" * 4)
            c = connection()
            c["url"] = f"http://127.0.0.1:{upstream.server_port}/v1"
            config = default_config()
            config["connections"] = [c]
            config["baseline"] = c["models"][0]["id"]
            config["decider"] = {
                "connection": c["id"],
                "model": "synthetic-decider",
                "consent": True,
            }
            runtime.save_config(
                config,
                0,
                consent_for={
                    "connection": c["id"],
                    "url": c["url"],
                    "model": "synthetic-decider",
                },
            )
            runtime.secrets[c["id"]] = "provider-secret-canary"
            server = ThreadingHTTPServer(
                ("127.0.0.1", 0),
                omr.handler(
                    {
                        "routes": {
                            "unused": {
                                "url": c["url"],
                                "model": "unused",
                                "protocol": "chat",
                            }
                        },
                        "default_route": "unused",
                    },
                    desktop=runtime,
                ),
            )
            runtime.port = server.server_port
            threading.Thread(target=server.serve_forever, daemon=True).start()

            def request(method, path, data=None, auth=True, origin=False):
                client = http.client.HTTPConnection(
                    "127.0.0.1", server.server_port, timeout=4
                )
                headers = {"Content-Type": "application/json"}
                if auth:
                    headers["Authorization"] = "Bearer " + runtime.key
                if origin:
                    headers["Origin"] = "https://malicious.example"
                client.request(
                    method,
                    path,
                    json.dumps(data) if data is not None else None,
                    headers,
                )
                response = client.getresponse()
                status = response.status
                body = response.read()
                client.close()
                return status, body

            try:
                self.assertEqual(request("GET", "/v1/models", auth=False)[0], 401)
                self.assertEqual(request("GET", "/v1/models", origin=True)[0], 401)
                direct = json.loads(request("GET", "/v1/models")[1])["data"][3]["id"]
                payload = {
                    "model": direct,
                    "messages": [{"role": "user", "content": "private-request-canary"}],
                    "tools": [{"type": "function", "function": {"name": "synthetic"}}],
                }
                self.assertEqual(
                    request("POST", "/v1/chat/completions", payload)[0], 200
                )
                self.assertEqual(len(seen), 1)
                self.assertEqual(seen[0][1], "Bearer provider-secret-canary")
                self.assertEqual(seen[0][0]["tools"], payload["tools"])
                payload["model"] = "omr/economy"
                payload["stream"] = True
                status, body = request("POST", "/v1/chat/completions", payload)
                self.assertEqual(status, 200)
                self.assertIn(b"[DONE]", body)
                for _ in range(100):
                    if len(runtime.rows) >= 2:
                        break
                    time.sleep(0.01)
                self.assertEqual(len(seen), 3)
                self.assertEqual(
                    runtime.rows[-1]["decision_usage"],
                    {"input_tokens": 10, "output_tokens": 4},
                )
                self.assertEqual(runtime.summary()["observed_input_tokens"], 200)
                self.assertEqual(runtime.summary()["observed_output_tokens"], 40)
                self.assertEqual(runtime.rows[-1]["comparison"]["baseline_revision"], 1)
                persisted = Path(d, "receipts.jsonl").read_text()
                for canary in (
                    "private-request-canary",
                    "private-response-canary",
                    "provider-secret-canary",
                    "gateway-canary",
                ):
                    self.assertNotIn(canary, persisted)
                discovery = runtime.discover(c["id"])
                self.assertEqual(discovery, ["synthetic-small"])
                runtime.verify_generation(direct, True)
                self.assertEqual(
                    runtime.snapshot()["model_states"][c["models"][0]["id"]][
                        "generation"
                    ],
                    "verified",
                )
            finally:
                server.shutdown()
                server.server_close()
                upstream.shutdown()
                upstream.server_close()


if __name__ == "__main__":
    unittest.main()
