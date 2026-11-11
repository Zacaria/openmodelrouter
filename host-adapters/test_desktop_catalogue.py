"""Desktop adapter contract against a real authenticated synthetic gateway."""

import http.client
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer

import omr
from desktop_engine import Runtime, default_config
from test_desktop import connection

HERE = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location("desktop_adapter", HERE / "launch.py")
assert spec and spec.loader
launch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launch)


class DesktopAdapterTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.runtime = Runtime(pathlib.Path(self.temp.name), "synthetic-" + "x" * 48)
        config = default_config()
        config["connections"] = [
            connection("chat-model"),
            connection("responses-model"),
            connection("messages-model"),
        ]
        for c, protocol in zip(
            config["connections"], ["chat", "responses", "anthropic"]
        ):
            c["models"][0]["protocols"] = [protocol]
        self.runtime.save_config(config, 0)
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
                },
                desktop=self.runtime,
            ),
        )
        self.runtime.port = self.gateway.server_port
        threading.Thread(target=self.gateway.serve_forever, daemon=True).start()
        self.addCleanup(self.gateway.server_close)
        self.addCleanup(self.gateway.shutdown)

    def test_catalogue_filters_protocol_without_losing_profiles_or_direct_identity(
        self,
    ):
        for protocol in ["chat", "responses", "anthropic"]:
            models = launch.desktop_catalogue(
                self.gateway.server_port, self.runtime.key, protocol
            )
            self.assertEqual(
                [m["id"] for m in models[:3]],
                ["omr/economy", "omr/balanced", "omr/quality"],
            )
            self.assertEqual(len(models), 4)
            c = next(
                c
                for c in self.runtime.config["connections"]
                if c["models"][0]["protocols"] == [protocol]
            )
            self.assertEqual(
                models[3]["id"], f"direct/{c['id']}/{c['models'][0]['id']}"
            )
            self.assertEqual(
                models[3]["name"], c["name"] + " · " + c["models"][0]["upstream"]
            )

    def test_wrong_bearer_is_not_replaced_by_an_unauthenticated_catalogue(self):
        with self.assertRaisesRegex(ValueError, "catalogue_unavailable"):
            launch.desktop_catalogue(self.gateway.server_port, "wrong", "chat")

    def test_proxy_serves_get_catalogue_and_injects_only_desktop_bearer(self):
        proxy = launch.Server(("127.0.0.1", 0), launch.Proxy)
        proxy.session = "00000000-0000-4000-8000-000000000000"
        proxy.upstream = self.gateway.server_port
        proxy.desktop_key = self.runtime.key
        proxy.client_key = "synthetic-client-key"
        proxy.catalogue = launch.desktop_catalogue(
            self.gateway.server_port, self.runtime.key, "chat"
        )
        threading.Thread(target=proxy.serve_forever, daemon=True).start()
        self.addCleanup(proxy.server_close)
        self.addCleanup(proxy.shutdown)
        client = http.client.HTTPConnection("127.0.0.1", proxy.server_port, timeout=5)
        self.addCleanup(client.close)
        client.request(
            "GET", "/v1/models", headers={"Authorization": "Bearer must-not-forward"}
        )
        refused = client.getresponse()
        self.assertEqual(refused.status, 401)
        refused.read()
        client.request(
            "GET",
            "/v1/models",
            headers={"Authorization": "Bearer synthetic-client-key"},
        )
        result = client.getresponse()
        self.assertEqual(result.status, 200)
        self.assertEqual(json.loads(result.read())["data"], proxy.catalogue)
        # A real gateway auth success followed by routing failure proves key injection,
        # while the arbitrary host key must never be used upstream.
        client.request(
            "POST",
            "/v1/chat/completions",
            json.dumps(
                {
                    "model": "not-a-route",
                    "messages": [{"role": "user", "content": "synthetic"}],
                }
            ),
            {
                "Authorization": "Bearer synthetic-client-key",
                "Content-Type": "application/json",
            },
        )
        result = client.getresponse()
        self.assertEqual(result.status, 400)
        self.assertEqual(json.loads(result.read())["error"]["type"], "invalid_request")

    @unittest.skipUnless(
        __import__("os").environ.get("OMR_TEST_OMP_BIN"),
        "opt-in real OMP synthetic direct generation",
    )
    def test_real_omp_direct_generation_bypasses_decider_and_authenticates_proxy(self):
        import os
        from http.server import BaseHTTPRequestHandler

        calls = []

        class Backend(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                calls.append({"body": body, "auth": self.headers.get("Authorization")})
                chunks = [
                    {
                        "id": "synthetic",
                        "object": "chat.completion.chunk",
                        "created": 0,
                        "model": body["model"],
                        "choices": [
                            {
                                "index": 0,
                                "delta": {
                                    "role": "assistant",
                                    "content": "SYNTHETIC_OK",
                                },
                                "finish_reason": None,
                            }
                        ],
                    },
                    {
                        "id": "synthetic",
                        "object": "chat.completion.chunk",
                        "created": 0,
                        "model": body["model"],
                        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                        "usage": {
                            "prompt_tokens": 1,
                            "completion_tokens": 1,
                            "total_tokens": 2,
                        },
                    },
                ]
                data = (
                    "".join("data: " + json.dumps(c) + "\n\n" for c in chunks)
                    + "data: [DONE]\n\n"
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        backend = ThreadingHTTPServer(("127.0.0.1", 0), Backend)
        threading.Thread(target=backend.serve_forever, daemon=True).start()
        self.addCleanup(backend.server_close)
        self.addCleanup(backend.shutdown)
        config = json.loads(json.dumps(self.runtime.config))
        c = config["connections"][0]
        c["url"] = f"http://127.0.0.1:{backend.server_port}/v1"
        c["id"] = connection()["id"]  # New endpoint, new vault identity.
        c["models"][0]["upstream"] = "~synthetic/model:exact"
        c["models"][0]["effort"] = "high"
        self.runtime.save_config(config, 1)
        self.runtime.secrets[c["id"]] = "synthetic-upstream-only-key"
        direct = f"direct/{c['id']}/{c['models'][0]['id']}"

        def never_decide(*args):
            self.fail("direct selection called the decider")

        self.runtime.classifier = never_decide
        env = {
            k: os.environ[k]
            for k in ["PATH", "HOME", "TMPDIR", "LANG"]
            if k in os.environ
        }
        env["OMR_DESKTOP_KEY"] = self.runtime.key
        # PI_CODING_AGENT_DIR isolates auth/models; HOME + XDG also isolate the
        # CLI's machine-global daemon bookkeeping (outside its agent directory).
        env["HOME"] = self.temp.name
        for variable, leaf in [
            ("XDG_CONFIG_HOME", "config"),
            ("XDG_STATE_HOME", "state"),
            ("XDG_DATA_HOME", "data"),
            ("XDG_CACHE_HOME", "cache"),
        ]:
            env[variable] = str(pathlib.Path(self.temp.name, leaf))
        result = subprocess.run(
            [
                sys.executable,
                str(HERE / "launch.py"),
                "omp",
                "--desktop",
                "--model",
                direct,
                "--omp-bin",
                os.environ["OMR_TEST_OMP_BIN"],
                "--port",
                str(self.gateway.server_port),
                "--session",
                "00000000-0000-4000-8000-000000000001",
                "--project",
                self.temp.name,
                "--run-timeout",
                "25",
                "--",
                "--print",
                "--no-tools",
                "--no-session",
                "--no-extensions",
                "--no-skills",
                "Reply with the synthetic marker.",
            ],
            env=env,
            text=True,
            capture_output=True,
            timeout=35,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SYNTHETIC_OK", result.stdout)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["body"]["model"], "~synthetic/model:exact")
        self.assertEqual(calls[0]["body"]["reasoning_effort"], "high")
        self.assertEqual(calls[0]["auth"], "Bearer synthetic-upstream-only-key")
        self.assertEqual(self.runtime.rows[-1]["mode"], "direct")
        self.assertEqual(self.runtime.rows[-1]["decision_ms"], 0)
        self.assertNotIn(self.runtime.key, result.stdout + result.stderr)
        print(
            "OMP real CLI → authenticated proxy → Desktop → synthetic SSE backend: exact direct model/effort, one call, no decider"
        )

    def test_list_mode_does_not_invoke_a_native_client_or_expose_key(self):
        import os

        env = {**os.environ, "OMR_DESKTOP_KEY": self.runtime.key}
        result = subprocess.run(
            [
                sys.executable,
                str(HERE / "launch.py"),
                "codex",
                "--desktop",
                "--list-models",
                "--port",
                str(self.gateway.server_port),
                "--session",
                "00000000-0000-4000-8000-000000000000",
                "--project",
                self.temp.name,
            ],
            env=env,
            text=True,
            capture_output=True,
            timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        models = json.loads(result.stdout)["data"]
        self.assertEqual(len(models), 4)
        self.assertNotIn(self.runtime.key, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
