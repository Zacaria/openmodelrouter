import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from test_desktop import connection
from desktop_engine import Runtime, default_config, decision_context


class DesktopBoundariesTest(unittest.TestCase):
    def test_validation_is_not_removed_by_python_optimization(self):
        result = subprocess.run(
            [
                sys.executable,
                "-O",
                "-c",
                "from desktop_engine import validate_config,default_config; c=default_config(); c['secret']='canary'; validate_config(c)",
            ],
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_api_context_budgets_and_atomic_anthropic_tool_turn(self):
        config = default_config()
        config.update(max_messages=None)
        data = {
            "messages": [
                {"role": "user", "content": "public"},
                {"role": "assistant", "content": [{"type": "tool_use", "id": "a"}]},
                {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "a", "content": "result"}
                    ],
                },
            ]
        }
        context, metadata = decision_context(data, config, [])
        self.assertEqual(context["messages"], data["messages"])
        self.assertLessEqual(metadata["total_estimated_tokens"], config["total_tokens"])
        config["max_messages"] = 2
        with self.assertRaisesRegex(ValueError, "current_turn_over_budget"):
            decision_context(data, config, [])

    def test_no_switch_for_tiny_saving_and_no_quality_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            runtime = Runtime(Path(d), "k" * 48)
            requirement = [1]
            runtime.classifier = lambda *args: {
                "required_quality": requirement[0],
                "reason": "simple",
            }
            config = default_config()
            first, second = connection(price=1), connection("alternative", 1, 0.99)
            second["models"][0]["enabled"] = False
            config["connections"] = [first, second]
            runtime.save_config(config, 0)
            row = {}
            data = {
                "model": "omr/economy",
                "messages": [{"role": "user", "content": "public"}],
            }
            session = "synthetic-session"
            runtime.select(
                copy.deepcopy(data),
                "chat",
                session,
                row,
                threading.Event(),
                time.monotonic() + 2,
            )
            second["models"][0]["enabled"] = True
            runtime.save_config(config, 1)
            route = runtime.select(
                copy.deepcopy(data),
                "chat",
                session,
                row,
                threading.Event(),
                time.monotonic() + 2,
            )[1]
            self.assertEqual(route["model"], "synthetic-small")
            self.assertEqual(row["reason"], "continuity_cost")
            requirement[0] = 3
            with self.assertRaisesRegex(ValueError, "quality_requirement_unavailable"):
                runtime.select(
                    copy.deepcopy(data),
                    "chat",
                    session,
                    {},
                    threading.Event(),
                    time.monotonic() + 2,
                )

    def test_invalid_decision_preserves_known_usage_and_no_freeform_reason(self):
        with tempfile.TemporaryDirectory() as d:
            runtime = Runtime(Path(d), "k" * 48)
            config = default_config()
            c = connection()
            config["connections"] = [c]
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
            runtime.api = lambda *args: {
                "model": "synthetic-decider",
                "choices": [{"message": {"content": "private-response-canary"}}],
                "usage": {"prompt_tokens": 11, "completion_tokens": 2},
            }
            row = {"usage": {}, "status": "invalid_request"}
            with self.assertRaisesRegex(ValueError, "invalid_decision"):
                runtime.select(
                    {
                        "model": "omr/economy",
                        "messages": [
                            {"role": "user", "content": "private-request-canary"}
                        ],
                    },
                    "chat",
                    None,
                    row,
                    threading.Event(),
                    time.monotonic() + 2,
                )
            self.assertEqual(
                row["decision_usage"], {"input_tokens": 11, "output_tokens": 2}
            )
            runtime.record(row)
            self.assertNotIn("private-", Path(d, "receipts.jsonl").read_text())

    def test_frozen_engine_requires_and_uses_bundled_certificate_roots(self):
        import ssl
        import shutil
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with (
                patch.object(sys, "frozen", True, create=True),
                patch.object(sys, "_MEIPASS", d, create=True),
            ):
                with self.assertRaises(FileNotFoundError):
                    Runtime(root / "data", "k" * 48)
                (root / "certifi").mkdir()
                shutil.copyfile(
                    Path(__file__).parent / "desktop" / "fixtures" / "test-ca.pem",
                    root / "certifi" / "cacert.pem",
                )
                runtime = Runtime(root / "data", "k" * 48)
                self.assertTrue(runtime.tls_context.check_hostname)
                self.assertEqual(runtime.tls_context.verify_mode, ssl.CERT_REQUIRED)
                self.assertGreater(runtime.tls_context.cert_store_stats()["x509_ca"], 0)

    def test_malformed_effort_is_a_controlled_error(self):
        with tempfile.TemporaryDirectory() as d:
            runtime = Runtime(Path(d), "k" * 48)
            config = default_config()
            c = connection()
            c["models"][0]["protocols"] = ["responses"]
            config["connections"] = [c]
            runtime.save_config(config, 0)
            direct = runtime.catalogue()["data"][3]["id"]
            for value in (None, [], "private-canary"):
                with self.assertRaisesRegex(ValueError, "invalid_effort"):
                    runtime.select(
                        {"model": direct, "reasoning": value},
                        "responses",
                        None,
                        {},
                        None,
                        0,
                    )

    def test_receipt_storage_failure_is_visible_without_transcript(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as d:
            runtime = Runtime(Path(d), "k" * 48)
            with patch(
                "desktop_engine.os.open",
                side_effect=OSError("SYNTHETIC-PRIVATE-CANARY"),
            ):
                runtime.record({"usage": {}, "status": "completed"})
            self.assertEqual(runtime.snapshot()["receipt_storage"], "unavailable")
            self.assertNotIn("SYNTHETIC-PRIVATE-CANARY", json.dumps(runtime.snapshot()))

    def test_configuration_change_invalidates_generation_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            runtime = Runtime(Path(d), "k" * 48)
            config = default_config()
            c = connection()
            config["connections"] = [c]
            runtime.save_config(config, 0)
            runtime.model_states[c["models"][0]["id"]] = {"generation": "verified"}
            c["models"][0]["upstream"] = "different-model"
            runtime.save_config(config, 1)
            self.assertNotIn(c["models"][0]["id"], runtime.model_states)


if __name__ == "__main__":
    unittest.main()
