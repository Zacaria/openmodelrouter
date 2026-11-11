"""Offline contracts; synthetic weights never count as model qualification."""

import copy
import hashlib
import io
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from desktop_engine import Runtime, default_config, decider_identity, validate_config
from test_desktop import connection


def wait_idle(manager):
    end = time.monotonic() + 3
    while manager.snapshot()["active"] and time.monotonic() < end:
        time.sleep(0.01)
    assert not manager.snapshot()["active"], manager.snapshot()
    return manager.snapshot()


class DeciderModesTest(unittest.TestCase):
    def test_managed_config_persists_exact_consent_without_starting(self):
        from desktop_managed import CHECKPOINT

        with tempfile.TemporaryDirectory() as d:
            runtime = Runtime(d, "k" * 48)
            config = default_config()
            config["connections"] = [connection()]
            config["decider"] = {
                "mode": "managed",
                "model": CHECKPOINT,
                "consent": True,
            }
            runtime.save_config(config, 0, decider_identity(config))
            resumed = Runtime(d, "k" * 48)
            self.assertTrue(resumed.config["decider"]["consent"])
            self.assertEqual(resumed.snapshot()["managed"]["status"], "absent")
            self.assertFalse(resumed.snapshot()["managed"]["active"])
            direct = resumed.catalogue()["data"][3]["id"]
            self.assertEqual(
                resumed.select({"model": direct}, "chat", None, {}, None, 0)[1][
                    "model"
                ],
                "synthetic-small",
            )
            self.assertFalse(resumed.history[-1]["config"].get("decider"))

    def test_mode_protocol_changes_revoke_consent(self):
        with tempfile.TemporaryDirectory() as d:
            runtime = Runtime(d, "k" * 48)
            config = default_config()
            c = connection()
            config["connections"] = [c]
            config["decider"] = {
                "mode": "byok",
                "protocol": "chat-json",
                "connection": c["id"],
                "model": "real-id",
                "consent": True,
            }
            runtime.save_config(config, 0, decider_identity(config))
            self.assertTrue(runtime.config["decider"]["consent"])
            config["decider"]["mode"] = "server"
            runtime.save_config(config, 1)
            self.assertFalse(runtime.config["decider"]["consent"])
            config["decider"]["protocol"] = "unknown"
            with self.assertRaisesRegex(ValueError, "invalid_config"):
                validate_config(config)

    def test_jev_cannot_be_misrepresented_as_chat(self):
        config = default_config()
        c = connection()
        config["connections"] = [c]
        config["decider"] = {
            "mode": "byok",
            "protocol": "chat-json",
            "connection": c["id"],
            "model": "jev-1.13.0",
            "consent": True,
        }
        with self.assertRaisesRegex(ValueError, "invalid_config"):
            validate_config(config)
        config["decider"]["protocol"] = "jev"
        validate_config(config)

    def test_jev_uses_real_systemone_decoder(self):
        with tempfile.TemporaryDirectory() as d:
            runtime = Runtime(d, "k" * 48)
            config = default_config()
            c = connection()
            config["connections"] = [c]
            config["decider"] = {
                "mode": "byok",
                "protocol": "jev",
                "connection": c["id"],
                "model": "jev-1.13.0",
                "consent": True,
            }
            runtime.secrets[c["id"]] = "synthetic-key"
            runtime.save_config(config, 0, decider_identity(config))
            response = {
                "model": "jev-1.13.0",
                "answers": {
                    "route": {
                        "type": "choice",
                        "choice": "reasoning",
                        "probabilities": {"direct": 0.1, "reasoning": 0.9},
                        "confidence": 0.9,
                    }
                },
                "usage": {"input_tokens": 11, "output_tokens": 1},
            }
            with patch.object(runtime, "api", return_value=response) as api:
                result = runtime.http_classify(
                    {"messages": [{"role": "user", "content": "public fixture"}]},
                    runtime.config,
                    threading.Event(),
                    time.monotonic() + 3,
                    {},
                )
            self.assertEqual(result["required_quality"], 3)
            args = api.call_args.args
            self.assertEqual(args[2], "/systemone")
            self.assertIn("questions", args[3])
            self.assertNotIn("messages", args[3])
            response["answers"]["route"]["abstained"] = True
            response["answers"]["route"]["unknown_probability"] = 0.95
            with patch.object(
                runtime, "api", return_value=response
            ), self.assertRaisesRegex(ValueError, "invalid_decision"):
                runtime.http_classify(
                    {"messages": [{"role": "user", "content": "public fixture"}]},
                    runtime.config,
                    threading.Event(),
                    time.monotonic() + 3,
                    {},
                )

    def test_imajev_never_uses_chat_and_honors_abstention(self):
        with tempfile.TemporaryDirectory() as d:
            runtime = Runtime(d, "k" * 48)
            config = default_config()
            c = connection()
            config["connections"] = [c]
            config["decider"] = {
                "mode": "server",
                "protocol": "chat-json",
                "connection": c["id"],
                "model": "imajev-2b",
                "consent": True,
            }
            with self.assertRaisesRegex(ValueError, "invalid_config"):
                validate_config(config)
            config["decider"]["protocol"] = "imajev"
            runtime.save_config(config, 0, decider_identity(config))
            answer = {
                "type": "choice",
                "choice": "2",
                "probabilities": {"1": 0.1, "2": 0.8, "3": 0.1},
                "confidence": 0.7,
                "unknown_probability": 0.05,
                "abstained": False,
            }
            with patch.object(
                runtime,
                "api",
                return_value={"model": "imajev-2b", "answers": {"quality": answer}},
            ) as api:
                result = runtime.http_classify(
                    {"messages": [{"role": "user", "content": "public fixture"}]},
                    runtime.config,
                    threading.Event(),
                    time.monotonic() + 3,
                    {},
                )
                self.assertEqual(result["required_quality"], 2)
                self.assertEqual(api.call_args.args[2], "/systemone")
                self.assertIn("criteria", api.call_args.args[3]["questions"]["quality"])
                for field, value in (
                    ("abstained", True),
                    ("unknown_probability", 0.9),
                    ("probabilities", {"1": 0.1, "2": float("nan"), "3": 0.1}),
                ):
                    bad = {**answer, field: value}
                    api.return_value = {
                        "model": "imajev-2b",
                        "answers": {"quality": bad},
                    }
                    with self.assertRaisesRegex(ValueError, "invalid_decision"):
                        runtime.http_classify(
                            {
                                "messages": [
                                    {"role": "user", "content": "public fixture"}
                                ]
                            },
                            runtime.config,
                            threading.Event(),
                            time.monotonic() + 3,
                            {},
                        )

    def test_recorded_imajev_abstentions_remain_fail_closed(self):
        from desktop_deciders import decode_imajev

        fixture = Path(__file__).parent / "evidence/imajev-t_5794a3e9/native-probe.jsonl"
        rows = [json.loads(line) for line in fixture.read_text().splitlines()]
        self.assertEqual(len(rows), 3)
        self.assertEqual(decode_imajev(rows[0]["response"], "imajev-4b")["required_quality"], 1)
        for row in rows[1:]:
            self.assertTrue(row["response"]["answers"]["quality"]["abstained"])
            with self.assertRaisesRegex(ValueError, "invalid_decision"):
                decode_imajev(row["response"], "imajev-4b")

    def test_ollama_observed_contract_and_refusals(self):
        from desktop_deciders import decode_imajev, decode_ollama_systemone

        fixture = Path(__file__).parent / "evidence/ollama-systemone-t_0622f1f2/d3-observed.ndjson"
        self.assertEqual(hashlib.sha256(fixture.read_bytes()).hexdigest(), "37cfe753c8352cee734f6fe4a39f6ed215e052289b5d988beadfe9865a927b2d")
        rows = [json.loads(line) for line in fixture.read_text().splitlines()]
        self.assertEqual(len(rows), 3)
        for row in rows:
            response = json.loads(row["body"])
            with self.assertRaisesRegex(ValueError, "invalid_decision"):
                decode_imajev(response, "d3:4b")
            result = decode_ollama_systemone(response, "d3:4b")
            self.assertEqual(result["required_quality"], row["case"])
            self.assertEqual(result["usage"], response["usage"])
        response = json.loads(rows[0]["body"])
        del response["usage"]
        self.assertNotIn("usage", decode_ollama_systemone(response, "d3:4b"))
        for field, value in [("abstained", True), ("abstained", None), ("unknown_probability", None), ("unknown_probability", 0.26), ("confidence", float("nan")), ("confidence", 1.1), ("choice", "2"), ("type", "text"), ("probabilities", {"1": 0.7, "2": 0.1, "3": 0.1})]:
            bad = copy.deepcopy(response)
            bad["answers"]["quality"][field] = value
            with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, "invalid_decision"):
                decode_ollama_systemone(bad, "d3:4b")
        for bad in [{**response, "model": "other"}, {"model": "d3:4b", "answers": {}}]:
            with self.assertRaisesRegex(ValueError, "invalid_decision"):
                decode_ollama_systemone(bad, "d3:4b")

    def test_ollama_explicit_transport_and_budget(self):
        with tempfile.TemporaryDirectory() as d:
            runtime = Runtime(d, "k" * 48)
            c = connection()
            config = default_config()
            config["connections"] = [c]
            config["decider"] = {"mode": "server", "protocol": "ollama-systemone", "connection": c["id"], "model": "d3:4b", "consent": True}
            runtime.save_config(config, 0, decider_identity(config))
            row = json.loads((Path(__file__).parent / "evidence/ollama-systemone-t_0622f1f2/d3-observed.ndjson").read_text().splitlines()[0])
            deadline = time.monotonic() + 75
            stopped = threading.Event()
            with patch.object(runtime, "api", return_value=json.loads(row["body"])) as api:
                result = runtime.http_classify({"messages": [{"role": "user", "content": "fixture"}]}, runtime.config, stopped, deadline, {})
            self.assertEqual(result["required_quality"], 1)
            self.assertEqual(api.call_args.args[2], "/systemone")
            self.assertEqual(api.call_args.args[4:6], (stopped, deadline))
            self.assertEqual(api.call_args.kwargs["max_timeout"], 60)

    def test_ollama_transport_deadline_and_cancellation(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        received = threading.Event()
        release = threading.Event()
        class Stall(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_POST(self):
                received.set()
                release.wait(3)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Stall)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as d:
                runtime = Runtime(d, "k" * 48)
                c = connection()
                c["url"] = f"http://127.0.0.1:{server.server_port}/v1"
                config = default_config()
                config["connections"] = [c]
                config["decider"] = {"mode": "server", "protocol": "ollama-systemone", "connection": c["id"], "model": "d3:4b", "consent": True}
                runtime.save_config(config, 0, decider_identity(config))
                for cancel in (False, True):
                    received.clear()
                    stopped = threading.Event()
                    timer = None
                    if cancel:
                        timer = threading.Thread(target=lambda: (received.wait(2), stopped.set()), daemon=True)
                        timer.start()
                    start = time.monotonic()
                    with self.assertRaisesRegex(ValueError, "upstream_unavailable"):
                        runtime.http_classify({"messages": [{"role": "user", "content": "synthetic"}]}, runtime.config, stopped, start + (2 if cancel else .2), {})
                    self.assertTrue(received.is_set())
                    self.assertLess(time.monotonic() - start, 1.5)
                    if timer:
                        timer.join(1)
        finally:
            release.set()
            server.shutdown()
            server.server_close()

    def test_imajev_cold_start_budget_and_deadline(self):
        with tempfile.TemporaryDirectory() as d:
            runtime = Runtime(d, "k" * 48)
            c = connection()
            answer = {"type": "choice", "choice": "1", "probabilities": {"1": 0.8, "2": 0.1, "3": 0.1}, "confidence": 0.8, "unknown_probability": 0.1, "abstained": False}
            config = default_config()
            config["connections"] = [c]
            config["decider"] = {"mode": "server", "protocol": "imajev", "connection": c["id"], "model": "imajev-2b", "consent": True}
            deadline = time.monotonic() + 50
            with patch.object(runtime, "api", return_value={"model": "imajev-2b", "answers": {"quality": answer}}) as api:
                runtime.http_classify({"messages": [{"role": "user", "content": "fixture"}]}, config, threading.Event(), deadline, {})
                self.assertEqual(api.call_args.kwargs["max_timeout"], 30)
                self.assertEqual(api.call_args.args[-1], deadline)
            with patch("desktop_engine.http.client.HTTPConnection") as client:
                response = client.return_value.getresponse.return_value
                response.status = 200
                response.getheader.return_value = "identity"
                response.read.return_value = b'{}'
                runtime.api(c, "POST", "/systemone", {}, None, time.monotonic() + 60, max_timeout=30)
                self.assertGreater(client.call_args.kwargs["timeout"], 29)
                runtime.api(c, "POST", "/systemone", {}, None, time.monotonic() + 2, max_timeout=30)
                self.assertLessEqual(client.call_args.kwargs["timeout"], 2)
                runtime.api(c, "POST", "/other", {})
                self.assertLessEqual(client.call_args.kwargs["timeout"], 15)

    def test_generation_test_uses_responses_when_it_is_the_declared_contract(self):
        with tempfile.TemporaryDirectory() as d:
            runtime = Runtime(d, "k" * 48)
            config = default_config()
            c = connection()
            c["models"][0]["protocols"] = ["responses"]
            config["connections"] = [c]
            runtime.save_config(config, 0)
            direct = runtime.catalogue()["data"][3]["id"]
            with patch("desktop_engine.http.client.HTTPConnection") as client:
                response = client.return_value.getresponse.return_value
                response.status = 200
                response.read.return_value = json.dumps(
                    {
                        "model": "synthetic-small",
                        "status": "completed",
                        "output": [
                            {
                                "type": "message",
                                "content": [{"type": "output_text", "text": "OK"}],
                            }
                        ],
                    }
                ).encode()
                runtime.verify_generation(direct, True)
                args = client.return_value.request.call_args.args
            self.assertEqual(args[1], "/v1/responses")
            self.assertIn("input", json.loads(args[2]))
            self.assertNotIn("messages", json.loads(args[2]))

    def test_explicit_decision_test_needs_fresh_click_and_records_no_text(self):
        with tempfile.TemporaryDirectory() as d:
            runtime = Runtime(d, "k" * 48)
            with self.assertRaisesRegex(ValueError, "consent_required"):
                runtime.verify_decision(False)
            with self.assertRaisesRegex(ValueError, "decider_not_configured"):
                runtime.verify_decision(True)
            self.assertEqual(runtime.rows, [])


class ManagedModelTest(unittest.TestCase):
    def fixture(self, d):
        from desktop_managed import ManagedModel, download_files

        manager = ManagedModel(Path(d))
        # Exercise the real staging/hash/install path with an offline byte source.
        manager._fetch = lambda stage: download_files(stage, manager._check_cancel)
        return manager

    def test_install_is_whole_checkpoint_atomic_and_restart_does_not_launch(self):
        import desktop_managed as managed

        files = {"a": b"first", "b": b"second"}
        hashes = {k: hashlib.sha256(v).hexdigest() for k, v in files.items()}
        with tempfile.TemporaryDirectory() as d, patch.object(
            managed, "FILES", hashes
        ), patch.object(
            managed, "open_download", side_effect=lambda name: io.BytesIO(files[name])
        ):
            manager = self.fixture(d)
            with self.assertRaisesRegex(ValueError, "consent_required"):
                manager.command({"action": "download", "consent": False})
            manager.command({"action": "download", "consent": True})
            self.assertEqual(wait_idle(manager)["status"], "installed")
            self.assertEqual({p.name for p in manager.directory.iterdir()}, set(files))
            resumed = self.fixture(d)
            self.assertEqual(resumed.snapshot()["status"], "installed")
            self.assertIsNone(resumed.process)
            manager.shutdown()

    def test_bad_hash_never_installs_and_explicit_retry_recovers(self):
        import desktop_managed as managed

        with tempfile.TemporaryDirectory() as d, patch.object(
            managed, "FILES", {"a": hashlib.sha256(b"good").hexdigest()}
        ):
            manager = self.fixture(d)
            with patch.object(
                managed, "open_download", return_value=io.BytesIO(b"bad")
            ):
                manager.command({"action": "download", "consent": True})
                state = wait_idle(manager)
            self.assertEqual(state["error"], "managed_integrity_failed")
            self.assertFalse(manager.directory.exists())
            self.assertEqual(list(Path(d).glob(".managed-*")), [])
            with patch.object(
                managed, "open_download", return_value=io.BytesIO(b"good")
            ):
                manager.command({"action": "download", "consent": True})
                self.assertEqual(wait_idle(manager)["status"], "installed")

    def test_cancel_cannot_publish_partial_checkpoint(self):
        import desktop_managed as managed

        started, release = threading.Event(), threading.Event()

        class Slow(io.BytesIO):
            def read1(self, count):
                started.set()
                release.wait(2)
                return super().read(count)

        with tempfile.TemporaryDirectory() as d, patch.object(
            managed, "FILES", {"a": hashlib.sha256(b"good").hexdigest()}
        ), patch.object(managed, "open_download", return_value=Slow(b"good")):
            manager = self.fixture(d)
            manager.command({"action": "download", "consent": True})
            self.assertTrue(started.wait(1))
            manager.command({"action": "cancel"})
            release.set()
            self.assertEqual(wait_idle(manager)["status"], "cancelled")
            self.assertFalse(manager.directory.exists())
            self.assertEqual(list(Path(d).glob(".managed-*")), [])

    def test_corrupt_or_symlink_weights_refused_before_start(self):
        import desktop_managed as managed

        with tempfile.TemporaryDirectory() as d, patch.object(
            managed, "FILES", {"a": hashlib.sha256(b"good").hexdigest()}
        ):
            manager = self.fixture(d)
            manager.directory.mkdir(parents=True)
            (manager.directory / "a").write_bytes(b"bad")
            manager.command({"action": "start"})
            self.assertEqual(wait_idle(manager)["error"], "managed_integrity_failed")
            self.assertIsNone(manager.process)
            if sys.platform == "linux":
                (manager.directory / "a").unlink()
                source = Path(d) / "external-weight"
                source.write_bytes(b"good")
                (manager.directory / "a").symlink_to(source)
                manager.command({"action": "start"})
                self.assertEqual(
                    wait_idle(manager)["error"], "managed_integrity_failed"
                )
                self.assertIsNone(manager.process)

    @unittest.skipUnless(
        sys.platform == "linux", "managed process cleanup is qualified on Linux only"
    )
    def test_shutdown_never_acknowledges_stalled_download_with_live_stage(self):
        import desktop_managed as managed
        import subprocess
        import sys

        real_popen = subprocess.Popen
        with tempfile.TemporaryDirectory() as d, patch.object(
            managed, "FILES", {"a": hashlib.sha256(b"good").hexdigest()}
        ):
            manager = managed.ManagedModel(Path(d))

            def spawn(argv, **kwargs):
                # Stalled resolver/download and its child share one owned group.
                return real_popen(
                    [sys.executable, "-I", "-c", "import time;time.sleep(30)"], **kwargs
                )

            with patch(
                "desktop_managed.subprocess.Popen", side_effect=spawn
            ), patch.object(managed, "open_download", return_value=io.BytesIO(b"good")):
                manager.command({"action": "download", "consent": True})
                end = time.monotonic() + 1
                while manager.process is None and time.monotonic() < end:
                    time.sleep(0.01)
                self.assertIsNotNone(manager.process)
                process = manager.process
                start = time.monotonic()
                manager.shutdown()
                self.assertLess(time.monotonic() - start, 2)
                self.assertFalse(manager.snapshot()["active"])
                self.assertIsNotNone(process.poll())
                self.assertFalse(manager.directory.exists())
                self.assertEqual(list(manager.directory.parent.glob(".managed-*")), [])

    def test_prompt_selection_refuses_multimodal_and_uses_last_complete_user(self):
        from desktop_managed import prompt_text

        self.assertEqual(
            prompt_text(
                {
                    "messages": [
                        {"role": "user", "content": "old"},
                        {
                            "role": "user",
                            "content": [{"type": "input_text", "text": "latest"}],
                        },
                    ]
                }
            ),
            "latest",
        )
        with self.assertRaisesRegex(ValueError, "unsupported_decision_context"):
            prompt_text(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_image",
                                    "image_url": "https://example.com",
                                }
                            ],
                        }
                    ]
                }
            )

    def test_decoder_is_nonconstant_and_refuses_nonfinite_outputs(self):
        from desktop_managed import decode_quality

        self.assertEqual(
            [decode_quality(x)["required_quality"] for x in (-2, 0, 2)], [1, 2, 3]
        )
        for value in (float("nan"), float("inf"), "1", True):
            with self.assertRaisesRegex(ValueError, "invalid_decision"):
                decode_quality(value)


@unittest.skipUnless(
    sys.platform == "linux", "managed process cleanup is qualified on Linux only"
)
class ManagedWorkerLifecycleTest(unittest.TestCase):
    def launch_fixture(self, manager, response, *, read_requests=True):
        import subprocess
        import sys

        real_popen = subprocess.Popen
        code = "import sys,json,time;print('{\"ready\":true}',flush=True)\n"
        code += ("for line in sys.stdin:\n " if read_requests else "") + response

        def spawn(argv, **kwargs):
            self.assertNotIn("PATH", kwargs["env"])
            self.assertNotIn("OPENAI_API_KEY", kwargs["env"])
            self.assertEqual(kwargs["env"]["HOME"], kwargs["cwd"])
            return real_popen([sys.executable, "-I", "-c", code], **kwargs)

        with patch("desktop_managed.subprocess.Popen", side_effect=spawn):
            manager.command({"action": "start"})
            self.assertEqual(wait_idle(manager)["status"], "ready")
        assert manager.process is not None
        return manager.process

    def test_owned_worker_start_stop_and_home_cleanup(self):
        import desktop_managed as managed

        with tempfile.TemporaryDirectory() as d, patch.object(
            managed, "FILES", {"a": hashlib.sha256(b"good").hexdigest()}
        ):
            manager = managed.ManagedModel(Path(d))
            manager.directory.mkdir(parents=True)
            (manager.directory / "a").write_bytes(b"good")
            process = self.launch_fixture(
                manager,
                'print(json.dumps({"required_quality":2,"reason":"task_requirement","usage":{"input_tokens":3,"output_tokens":0}}),flush=True)',
            )
            home = Path(manager.home.name)
            self.assertEqual(
                manager.classify(
                    {"messages": [{"role": "user", "content": "fixture"}]},
                    [],
                    threading.Event(),
                    time.monotonic() + 2,
                )["required_quality"],
                2,
            )
            manager.shutdown()
            self.assertIsNotNone(process.poll())
            self.assertFalse(home.exists())
            self.assertIsNone(manager.process)

    def test_stop_reaps_grandchild_after_leader_exits(self):
        import desktop_managed as managed

        with tempfile.TemporaryDirectory() as d, patch.object(
            managed, "FILES", {"a": hashlib.sha256(b"good").hexdigest()}
        ):
            manager = managed.ManagedModel(Path(d))
            manager.directory.mkdir(parents=True)
            (manager.directory / "a").write_bytes(b"good")
            process = self.launch_fixture(
                manager,
                'import subprocess;child=subprocess.Popen([sys.executable,"-I","-c","import time;time.sleep(30)"]);print(json.dumps({"required_quality":2,"reason":"task_requirement","child_pid":child.pid}),flush=True);sys.exit(0)',
            )
            result = manager.classify(
                {"messages": [{"role": "user", "content": "fixture"}]},
                [],
                threading.Event(),
                time.monotonic() + 2,
            )
            process.wait(timeout=2)
            manager.shutdown()
            pid = result["child_pid"]

            def running():
                try:
                    return Path(f"/proc/{pid}/stat").read_text().split()[2] != "Z"
                except FileNotFoundError:
                    return False

            end = time.monotonic() + 2
            while running() and time.monotonic() < end:
                time.sleep(0.01)
            self.assertFalse(
                running(), "group cleanup must retain the exited leader anchor"
            )

    def test_nonreading_worker_write_is_bounded_and_cancellable(self):
        import desktop_managed as managed
        import fcntl

        for cancel, phase in (
            (False, "write"),
            (True, "write"),
            (False, "flush"),
            (True, "flush"),
        ):
            with self.subTest(
                cancel=cancel, phase=phase
            ), tempfile.TemporaryDirectory() as d, patch.object(
                managed, "FILES", {"a": hashlib.sha256(b"good").hexdigest()}
            ):
                manager = managed.ManagedModel(Path(d))
                manager.directory.mkdir(parents=True)
                (manager.directory / "a").write_bytes(b"good")
                process = self.launch_fixture(
                    manager, "time.sleep(30)", read_requests=False
                )
                assert manager.home is not None and process.stdin is not None
                home = Path(manager.home.name)
                # Force partial writes even on hosts with larger default pipes.
                capacity = fcntl.fcntl(process.stdin.fileno(), fcntl.F_SETPIPE_SZ, 4096)
                text = "😀" * 7000 if phase == "write" else "fixture"
                self.assertLess(len(text.encode()), 65536)
                if phase == "write":
                    self.assertGreater(
                        len(json.dumps({"prompt": text}).encode()), capacity
                    )
                else:
                    import os

                    # The small request fits in BufferedWriter; only flush blocks.
                    self.assertEqual(
                        os.write(process.stdin.fileno(), b"x" * capacity), capacity
                    )
                stopped, errors = threading.Event(), []

                def classify():
                    try:
                        manager.classify(
                            {"messages": [{"role": "user", "content": text}]},
                            [],
                            stopped,
                            time.monotonic() + (5 if cancel else 0.15),
                        )
                    except Exception as error:
                        errors.append(error)

                call = threading.Thread(target=classify, daemon=True)
                timer = threading.Timer(0.1, stopped.set)
                call.start()
                if cancel:
                    timer.start()
                try:
                    call.join(0.8)
                    self.assertFalse(
                        call.is_alive(),
                        "IPC write exceeded deadline/cancellation bound",
                    )
                    self.assertEqual(len(errors), 1)
                    self.assertIsNotNone(process.poll())
                    self.assertTrue(process.stdin.closed)
                    assert process.stdout is not None
                    self.assertTrue(process.stdout.closed)
                    self.assertIsNone(manager.process)
                    self.assertIsNone(manager.home)
                    self.assertFalse(home.exists())
                    self.assertEqual(manager.snapshot()["status"], "stopped")
                finally:
                    timer.cancel()
                    # Rescue the intentionally failing RED without blocking close()
                    # behind a BufferedWriter still held by the classification.
                    managed.kill_worker(process)
                    call.join(2)
                    manager.shutdown()

    def test_partial_writes_deliver_one_complete_request(self):
        import desktop_managed as managed

        with tempfile.TemporaryDirectory() as d, patch.object(
            managed, "FILES", {"a": hashlib.sha256(b"good").hexdigest()}
        ):
            manager = managed.ManagedModel(Path(d))
            manager.directory.mkdir(parents=True)
            (manager.directory / "a").write_bytes(b"good")
            process = self.launch_fixture(
                manager,
                'print(json.dumps({"required_quality":2 if json.loads(line)["prompt"] == "partial 😀" else 0}),flush=True)',
            )
            assert process.stdin is not None
            write = process.stdin.write
            try:
                with patch.object(
                    process.stdin, "write", side_effect=lambda data: write(data[:3])
                ) as short_write:
                    result = manager.classify(
                        {"messages": [{"role": "user", "content": "partial 😀"}]},
                        [],
                        threading.Event(),
                        time.monotonic() + 2,
                    )
                self.assertEqual(result["required_quality"], 2)
                self.assertGreater(short_write.call_count, 1)
                self.assertIsNone(process.poll())
                self.assertEqual(manager.snapshot()["status"], "ready")
            finally:
                manager.shutdown()

    def test_old_classification_error_cannot_reap_restarted_worker(self):
        import desktop_managed as managed

        with tempfile.TemporaryDirectory() as d, patch.object(
            managed, "FILES", {"a": hashlib.sha256(b"good").hexdigest()}
        ):
            manager = managed.ManagedModel(Path(d))
            manager.directory.mkdir(parents=True)
            (manager.directory / "a").write_bytes(b"good")
            response = 'print(json.dumps({"required_quality":2}),flush=True)'
            old = self.launch_fixture(manager, response)
            entered, release, errors = threading.Event(), threading.Event(), []
            read = manager._read

            def delayed_read(process, *args, **kwargs):
                if process is old:
                    entered.set()
                    if not release.wait(3):
                        raise AssertionError("test barrier timed out")
                    raise ValueError("managed_runtime_unavailable")
                return read(process, *args, **kwargs)

            def classify():
                try:
                    manager.classify(
                        {"messages": [{"role": "user", "content": "fixture"}]},
                        [],
                        threading.Event(),
                        time.monotonic() + 5,
                    )
                except Exception as error:
                    errors.append(error)

            call = threading.Thread(target=classify, daemon=True)
            try:
                with patch.object(manager, "_read", side_effect=delayed_read):
                    call.start()
                    self.assertTrue(entered.wait(1))
                    manager.command({"action": "stop"})
                    self.assertIsNotNone(old.poll())
                    new = self.launch_fixture(manager, response)
                    assert manager.home is not None
                    home = Path(manager.home.name)
                    self.assertIsNot(new, old)
                    self.assertTrue(manager.snapshot()["running"])
                    release.set()
                    call.join(1)
                    self.assertFalse(call.is_alive())
                self.assertEqual(
                    [str(e) for e in errors], ["managed_runtime_unavailable"]
                )
                self.assertIs(manager.process, new)
                self.assertIsNone(new.poll())
                self.assertTrue(home.exists())
                self.assertEqual(manager.snapshot()["status"], "ready")
                self.assertTrue(manager.snapshot()["running"])
                self.assertEqual(
                    manager.classify(
                        {"messages": [{"role": "user", "content": "retry"}]},
                        [],
                        threading.Event(),
                        time.monotonic() + 2,
                    )["required_quality"],
                    2,
                )
            finally:
                release.set()
                call.join(2)
                manager.shutdown()

    def test_deadline_and_cancellation_kill_reap_worker(self):
        import desktop_managed as managed

        for cancel in (False, True):
            with self.subTest(
                cancel=cancel
            ), tempfile.TemporaryDirectory() as d, patch.object(
                managed, "FILES", {"a": hashlib.sha256(b"good").hexdigest()}
            ):
                manager = managed.ManagedModel(Path(d))
                manager.directory.mkdir(parents=True)
                (manager.directory / "a").write_bytes(b"good")
                process = self.launch_fixture(manager, "time.sleep(10)")
                stopped = threading.Event()
                timer = threading.Timer(0.1, stopped.set)
                if cancel:
                    timer.start()
                try:
                    with self.assertRaises(ValueError):
                        manager.classify(
                            {"messages": [{"role": "user", "content": "fixture"}]},
                            [],
                            stopped,
                            time.monotonic() + (0.2 if not cancel else 5),
                        )
                    self.assertIsNotNone(process.poll())
                    self.assertIsNone(manager.process)
                    self.assertEqual(manager.snapshot()["status"], "stopped")
                finally:
                    timer.cancel()
                    manager.shutdown()


if __name__ == "__main__":
    unittest.main()
