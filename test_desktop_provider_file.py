"""Bidirectional provider configuration; isolated metadata, never native credentials."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from desktop_engine import Runtime, default_config, decider_identity
from test_desktop import connection


class ProviderFileTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.runtime = Runtime(self.directory, "synthetic-" + "x" * 48)
        self.path = self.directory / "providers.json"

    def write(self, config):
        self.path.write_text(json.dumps(config, ensure_ascii=False, indent=2))

    def config(self):
        config = default_config()
        config["connections"] = [connection("vendor/model:exact")]
        return config

    def test_ui_writes_editable_config_without_secrets_or_grants(self):
        config = self.config()
        conn = config["connections"][0]
        self.runtime.secrets[conn["id"]] = "secret-canary"
        config["decider"] = {
            "connection": conn["id"],
            "model": "decider",
            "consent": True,
        }
        state = self.runtime.save_config(config, 0, decider_identity(config))
        self.assertTrue(state["config"]["decider"]["consent"])
        expected = copy.deepcopy(config)
        expected["decider"]["consent"] = False
        self.assertEqual(json.loads(self.path.read_text()), expected)
        self.assertNotIn("secret-canary", self.path.read_text())
        self.assertEqual(
            state["config_file"], {"path": str(self.path), "status": "synced"}
        )
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_manual_edit_loads_effectively_and_survives_restart(self):
        config = self.config()
        self.write(config)
        self.assertEqual(self.runtime.snapshot()["config_file"]["status"], "changed")
        state = self.runtime.reload_config(0)
        self.assertEqual(state["config"], config)
        self.assertEqual(state["revision"], 1)
        direct = state["catalogue"][3]["id"]
        self.assertEqual(
            self.runtime.select({"model": direct}, "chat", None, {}, None, 0)[1][
                "model"
            ],
            "vendor/model:exact",
        )
        self.assertEqual(Runtime(self.directory, "x" * 48).config, config)
        config["connections"][0]["name"] = "Edited while closed"
        self.write(config)
        resumed = Runtime(self.directory, "x" * 48)
        self.assertEqual(resumed.config, config)
        self.assertEqual(resumed.revision, 2)

    def test_invalid_file_keeps_last_valid_and_does_not_overwrite_edit(self):
        config = self.config()
        self.runtime.save_config(config, 0)
        for value in (
            "{not-json",
            json.dumps({**config, "api_key": "secret-canary"}),
            json.dumps({**config, "context_tokens": 0}),
            "null",
            '{"connections":[],"connections":[]}',
        ):
            with self.subTest(value=value):
                self.path.write_text(value)
                with self.assertRaisesRegex(ValueError, "invalid_config"):
                    self.runtime.reload_config(1)
                self.assertEqual(self.runtime.config, config)
                self.assertEqual(self.runtime.revision, 1)
                self.assertEqual(self.path.read_text(), value)
                resumed = Runtime(self.directory, "x" * 48)
                self.assertEqual(resumed.config, config)
                self.assertEqual(resumed.snapshot()["config_file"]["status"], "invalid")

    def test_ui_save_and_restore_refuse_external_edits_and_stale_revision(self):
        config = self.config()
        self.runtime.save_config(config, 0)
        changed = copy.deepcopy(config)
        changed["expected_output"] = 99
        self.write(changed)
        for value in (config, self.runtime.history[0]["config"]):
            with self.assertRaisesRegex(ValueError, "configuration_conflict"):
                self.runtime.save_config(value, 1)
        self.assertEqual(json.loads(self.path.read_text()), changed)
        with self.assertRaisesRegex(ValueError, "configuration_conflict"):
            self.runtime.reload_config(0)
        self.runtime.reload_config(1)
        with self.assertRaisesRegex(ValueError, "configuration_conflict"):
            self.runtime.save_config(config, 1)

    def test_reloading_file_cannot_grant_or_keep_decider_consent(self):
        config = self.config()
        conn = config["connections"][0]
        config["decider"] = {
            "connection": conn["id"],
            "model": "decider",
            "consent": True,
        }
        self.runtime.save_config(config, 0, decider_identity(config))
        self.write(config)
        self.runtime.reload_config(1)
        self.assertFalse(self.runtime.config["decider"]["consent"])
        self.assertFalse(Runtime(self.directory, "x" * 48).config["decider"]["consent"])

    def test_reload_detects_edit_during_validation(self):
        import desktop_engine

        config = self.config()
        self.write(config)
        changed = copy.deepcopy(config)
        changed["expected_output"] = 3
        validate = desktop_engine.validate_config

        def race(value):
            validate(value)
            self.write(changed)

        with patch.object(desktop_engine, "validate_config", race):
            with self.assertRaisesRegex(ValueError, "configuration_conflict"):
                self.runtime.reload_config(0)
        self.assertEqual(self.runtime.revision, 0)
        self.assertEqual(self.runtime.config, default_config())
        self.assertEqual(json.loads(self.path.read_text()), changed)

    def test_ui_save_detects_an_edit_while_the_temporary_file_is_flushed(self):
        import os

        config = self.config()
        changed = copy.deepcopy(config)
        changed["expected_output"] = 7
        fsync = os.fsync

        def edit_then_flush(fd):
            self.write(changed)
            fsync(fd)

        with patch("desktop_engine.os.fsync", edit_then_flush):
            with self.assertRaisesRegex(ValueError, "configuration_conflict"):
                self.runtime.save_config(config, 0)
        self.assertEqual(self.runtime.revision, 0)
        self.assertEqual(json.loads(self.path.read_text()), changed)

    def test_private_write_failure_keeps_last_valid_and_recovers_from_public_file(self):
        import os

        config = self.config()
        replace = os.replace

        def fail_private(source, target):
            if Path(target).name == "config.json":
                raise OSError("synthetic private write failure")
            return replace(source, target)

        with patch("desktop_engine.os.replace", fail_private):
            with self.assertRaises(OSError):
                self.runtime.save_config(config, 0)
        self.assertEqual(self.runtime.config, default_config())
        self.assertEqual(self.runtime.revision, 0)
        self.assertEqual(json.loads(self.path.read_text()), config)
        with self.assertRaisesRegex(ValueError, "configuration_conflict"):
            self.runtime.save_config(default_config(), 0)
        self.assertEqual(self.runtime.reload_config(0)["config"], config)
        self.assertFalse(list(self.directory.glob("*.pending")))

    def test_initial_file_creation_preserves_an_existing_grant_across_restarts(self):
        config = self.config()
        config["decider"] = {
            "connection": config["connections"][0]["id"],
            "model": "decider",
            "consent": True,
        }
        self.path.unlink()
        (self.directory / "config.json").write_text(
            json.dumps(
                {
                    "config": config,
                    "revision": 4,
                    "history": [],
                    "consent_for": decider_identity(config),
                }
            )
        )
        first = Runtime(self.directory, "x" * 48)
        second = Runtime(self.directory, "x" * 48)
        self.assertEqual(first.config, config)
        self.assertEqual(second.config, config)
        self.assertEqual(second.revision, 4)
        self.assertFalse(json.loads(self.path.read_text())["decider"]["consent"])

    def test_external_destination_changes_require_a_new_connection_identity(self):
        config = self.config()
        self.runtime.save_config(config, 0)
        self.runtime.secrets[config["connections"][0]["id"]] = "synthetic-native-key"
        config["connections"][0]["url"] = "https://other.example/v1"
        self.write(config)
        with self.assertRaisesRegex(ValueError, "credential_destination_changed"):
            self.runtime.reload_config(1)
        self.assertEqual(self.runtime.revision, 1)
        resumed = Runtime(self.directory, "x" * 48)
        self.assertNotEqual(resumed.config, config)
        self.assertEqual(resumed.snapshot()["config_file"]["status"], "invalid")
        with self.assertRaisesRegex(ValueError, "credential_destination_changed"):
            self.runtime.save_config(config, 1)

    def test_removed_uuid_cannot_change_destination_after_history_eviction_and_restart(
        self,
    ):
        config = self.config()
        identity = config["connections"][0]["id"]
        self.runtime.save_config(config, 0)
        self.runtime.secrets[identity] = "synthetic-vault-canary"
        self.write(default_config())
        self.runtime.reload_config(1)
        # The trust binding must outlive the bounded undo history, not just secrets.
        for _ in range(11):
            self.runtime.save_config(default_config(), self.runtime.revision)
        changed = copy.deepcopy(config)
        changed["connections"][0]["url"] = "http://127.0.0.1:9/v1"
        for restart in (False, True):
            with self.subTest(restart=restart):
                runtime = Runtime(self.directory, "x" * 48) if restart else self.runtime
                # Match Rust's UUID-indexed vault resynchronization, including a clear.
                runtime.secrets = {}
                runtime.secrets = {identity: "synthetic-vault-canary"}
                self.write(changed)
                with self.assertRaisesRegex(
                    ValueError, "credential_destination_changed"
                ):
                    runtime.reload_config(runtime.revision)
                self.assertEqual(runtime.config["connections"], [])
                with self.assertRaisesRegex(
                    ValueError, "credential_destination_changed"
                ):
                    runtime.save_config(changed, runtime.revision)
                self.write(default_config())
        # A file changed while closed must also be rejected before vault restoration.
        self.write(changed)
        resumed = Runtime(self.directory, "x" * 48)
        self.assertEqual(resumed.config["connections"], [])
        self.assertEqual(resumed.snapshot()["config_file"]["status"], "invalid")
        self.assertNotIn(
            "synthetic-vault-canary", (self.directory / "config.json").read_text()
        )
        self.assertNotIn("connection_destinations", self.path.read_text())
        # Restoring the exact original destination is still supported.
        self.write(config)
        self.assertEqual(resumed.reload_config(resumed.revision)["config"], config)

    def test_url_change_is_refused_before_vault_load_or_after_key_removal(self):
        config = self.config()
        self.runtime.save_config(config, 0)
        config["connections"][0]["url"] = "https://other.example/v1"
        with self.assertRaisesRegex(ValueError, "credential_destination_changed"):
            self.runtime.save_config(config, 1)

    def test_public_provider_alias_ids_are_not_filtered_or_rewritten(self):
        config = self.config()
        model = config["connections"][0]["models"][0]
        model["upstream"] = "~openai/gpt-sol-latest"
        self.write(config)
        state = self.runtime.reload_config(0)
        route_id = state["catalogue"][3]["id"]
        row = {}
        route = self.runtime.select({"model": route_id}, "chat", None, row, None, 0)[1]
        self.assertEqual(route["model"], "~openai/gpt-sol-latest")
        self.assertEqual(row["decision_ms"], 0)
        with patch.object(
            self.runtime, "api", return_value={"data": [{"id": model["upstream"]}]}
        ):
            self.assertEqual(
                self.runtime.discover(config["connections"][0]["id"]),
                ["~openai/gpt-sol-latest"],
            )

    def test_large_provider_catalogue_is_neither_rejected_nor_truncated(self):
        import uuid

        config = self.config()
        conn = config["connections"][0]
        template = conn["models"][0]
        # OpenRouter observed: 454 IDs; go past the former discovery slice of 500 too.
        conn["models"] = [
            {**template, "id": str(uuid.uuid4()), "upstream": f"vendor/model-{i}"}
            for i in range(601)
        ]
        self.write(config)
        state = self.runtime.reload_config(0)
        self.assertEqual(len(state["catalogue"]), 604)
        with patch.object(
            self.runtime,
            "api",
            return_value={"data": [{"id": m["upstream"]} for m in conn["models"]]},
        ):
            self.assertEqual(len(self.runtime.discover(conn["id"])), 601)
        self.assertEqual(len(Runtime(self.directory, "x" * 48).routes()), 601)

    def test_deleted_or_unreadable_file_does_not_get_recreated_by_ui_save(self):
        self.runtime.save_config(self.config(), 0)
        self.path.unlink()
        with self.assertRaisesRegex(ValueError, "configuration_conflict"):
            self.runtime.save_config(default_config(), 1)
        self.assertFalse(self.path.exists())
        with self.assertRaisesRegex(ValueError, "config_file_unavailable"):
            self.runtime.reload_config(1)


class ProviderFileSidecarTest(unittest.TestCase):
    def test_vault_sync_and_restart_cannot_retarget_a_removed_uuid(self):
        import contextlib
        import queue
        import subprocess
        import sys
        import threading
        import uuid
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        received = []

        class Destination(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_GET(self):
                received.append(self.headers.get("Authorization"))
                body = b'{"data":[{"id":"synthetic/model"}]}'
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Destination)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        @contextlib.contextmanager
        def sidecar(directory):
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-B",
                    str(Path(__file__).with_name("desktop_sidecar.py")),
                    str(directory),
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            assert process.stdin and process.stdout and process.stderr
            stdin, stdout, stderr = process.stdin, process.stdout, process.stderr

            def ipc(request):
                stdin.write(json.dumps(request) + "\n")
                stdin.flush()
                response = queue.Queue()
                threading.Thread(
                    target=lambda: response.put(stdout.readline()), daemon=True
                ).start()
                line = response.get(timeout=5)
                self.assertTrue(line, "sidecar closed unexpectedly")
                return json.loads(line)

            try:
                yield ipc
                self.assertEqual(
                    ipc({"command": "shutdown", "force": False}), {"ok": True}
                )
                self.assertEqual(process.wait(timeout=5), 0)
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
                for stream in (stdin, stdout, stderr):
                    stream.close()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "providers.json"
            config = default_config()
            config["connections"] = [connection("synthetic/model")]
            identity = config["connections"][0]["id"]
            with sidecar(directory) as ipc:
                ipc({"command": "init", "key": "x" * 48})
                self.assertIn(
                    "ok",
                    ipc({"command": "save_config", "config": config, "revision": 0}),
                )
                ipc(
                    {
                        "command": "secrets",
                        "values": {identity: "synthetic-old-vault-canary"},
                    }
                )
                path.write_text(json.dumps(default_config()))
                self.assertIn(
                    "ok",
                    ipc({"command": "save_config", "source": "file", "revision": 1}),
                )
                # Rust retains removed entries and resends the entire map on save_secret.
                ipc(
                    {
                        "command": "secrets",
                        "values": {identity: "synthetic-old-vault-canary"},
                    }
                )
                config["connections"][0]["url"] = (
                    f"http://127.0.0.1:{server.server_port}/v1"
                )
                path.write_text(json.dumps(config))
                self.assertEqual(
                    ipc({"command": "save_config", "source": "file", "revision": 2}),
                    {"error": "credential_destination_changed"},
                )
            # Leave the attack file on disk, then restore native vault values after init.
            with sidecar(directory) as ipc:
                state = ipc({"command": "init", "key": "y" * 48})["ok"]
                self.assertEqual(state["config"]["connections"], [])
                self.assertEqual(state["config_file"]["status"], "invalid")
                ipc(
                    {
                        "command": "secrets",
                        "values": {identity: "synthetic-old-vault-canary"},
                    }
                )
                self.assertEqual(
                    ipc({"command": "discover", "connection": identity}),
                    {"error": "model_unavailable"},
                )
                self.assertEqual(received, [])
                # A fresh identity plus explicit credential association still works.
                fresh = str(uuid.uuid4())
                config["connections"][0]["id"] = fresh
                path.write_text(json.dumps(config))
                self.assertIn(
                    "ok",
                    ipc({"command": "save_config", "source": "file", "revision": 2}),
                )
                ipc(
                    {
                        "command": "secrets",
                        "values": {
                            identity: "synthetic-old-vault-canary",
                            fresh: "synthetic-new-explicit-key",
                        },
                    }
                )
                self.assertEqual(
                    ipc({"command": "discover", "connection": fresh}),
                    {"ok": ["synthetic/model"]},
                )
                self.assertEqual(received, ["Bearer synthetic-new-explicit-key"])


if __name__ == "__main__":
    unittest.main()
