"""Synthetic identifiers only; execute the real probe persistence boundary."""

import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from advanced import probe_claude
from advanced.evidence_privacy import redact_emails
from advanced.tests.test_claude import delegate_events


class ClaudeEvidencePrivacy(unittest.TestCase):
    def test_recursive_redaction_preserves_counts_pairs_and_original(self):
        address = "synthétique.account+tag@exemple.invalid"
        original = {
            "events": [{"id": "tool-1", "tool_use_id": "tool-1", "content": address}],
            "usage": {"inputTokens": 123, "cost": 0.125, "unknown": None},
            "nested": [json.dumps({"text": address}, ensure_ascii=False)],
            "native_binary": "node_modules/@openai/codex/bin/codex",
            address: "multiple: first@example.invalid second@localhost",
        }
        safe = redact_emails(original)
        self.assertNotIn(address, json.dumps(safe, ensure_ascii=False))
        self.assertNotIn("first@example.invalid", json.dumps(safe))
        self.assertNotIn("second@localhost", json.dumps(safe))
        self.assertEqual(safe["native_binary"], original["native_binary"])
        self.assertEqual(safe["usage"], original["usage"])
        self.assertEqual(safe["events"][0]["id"], safe["events"][0]["tool_use_id"])
        self.assertEqual(original["events"][0]["content"], address)
        self.assertEqual(redact_emails(safe), safe)

    def test_success_path_redacts_adapter_copies_without_changing_accounting(self):
        address = "synthetic.success@example.invalid"
        sid = None
        calls = 0

        def execute(command, **kwargs):
            nonlocal sid, calls
            if command[-2:] == ["auth", "status"]:
                return subprocess.CompletedProcess(
                    [], 0, '{"loggedIn":true,"authMethod":"claude.ai"}', ""
                )
            calls += 1
            if "--session-id" in command:
                sid = command[command.index("--session-id") + 1]
            if calls == 4:
                events = delegate_events()
            elif calls == 2:
                events = [
                    {"type": "system", "subtype": "compact_boundary"},
                    {"type": "result", "is_error": False, "local_command": "compact"},
                ]
            else:
                events = [{"type": "result", "is_error": False}]
            for e in events:
                e["session_id"] = sid
                if e["type"] == "result":
                    e.update(
                        result=address,
                        total_cost_usd=calls * 0.125,
                        modelUsage={"haiku": {"inputTokens": calls * 100}},
                    )
            return subprocess.CompletedProcess(
                [], 0, "\n".join(map(json.dumps, events)), address
            )

        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "capture"
            with (
                patch("sys.argv", ["probe", "--output", str(output)]),
                patch.object(probe_claude.Path, "is_file", return_value=True),
                patch.object(probe_claude.subprocess, "run", side_effect=execute),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                probe_claude.main()
            text = (output / "results.json").read_text()
        self.assertNotIn(address, text)
        saved = json.loads(text)
        self.assertEqual(len(saved), 4)
        self.assertEqual(saved[-1]["adapter_validation"]["status"], "completed")
        for row in saved:
            self.assertEqual(
                row["accounting"]["action_delta"]["native_equivalent_usd"], 0.125
            )
            self.assertEqual(
                row["accounting"]["action_delta"]["modelUsage"]["haiku"]["inputTokens"],
                100,
            )

    def test_native_text_is_redacted_before_first_write_even_on_failure(self):
        address = "synthetic.account+probe@example.invalid"
        events = [
            {"type": "system", "subtype": "init", "account": address},
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": address}]},
            },
            {
                "type": "user",
                "message": {"content": [{"type": "tool_result", "content": address}]},
            },
            {
                "type": "result",
                "result": "Native account: " + address,
                "is_error": True,
                "total_cost_usd": 0.125,
                "modelUsage": {"haiku": {"inputTokens": 123, "outputTokens": 45}},
            },
        ]
        outputs = iter(
            [
                subprocess.CompletedProcess(
                    [], 0, '{"loggedIn":true,"authMethod":"claude.ai"}', ""
                ),
                subprocess.CompletedProcess(
                    [], 1, "\n".join(map(json.dumps, events)), "error " + address
                ),
            ]
        )
        writes = []
        original_write = Path.write_text

        def observe_write(path, text, *args, **kwargs):
            # Check the actual bytes offered to persistence, not a later scrub.
            writes.append(text)
            return original_write(path, text, *args, **kwargs)

        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "capture"
            with (
                patch("sys.argv", ["probe", "--output", str(output)]),
                patch.object(probe_claude.Path, "is_file", return_value=True),
                patch.object(
                    probe_claude.subprocess,
                    "run",
                    side_effect=lambda *a, **k: next(outputs),
                ),
                patch.object(Path, "write_text", observe_write),
                contextlib.redirect_stdout(io.StringIO()),
                self.assertRaises(SystemExit),
            ):
                probe_claude.main()
            text = (output / "results.json").read_text()
        self.assertEqual(len(writes), 1)
        self.assertNotIn(address, writes[0])
        self.assertNotIn(address, text)
        saved = json.loads(text)[0]
        self.assertNotIn("system", [e["type"] for e in saved["events"]])
        self.assertEqual(saved["events"][-1]["total_cost_usd"], 0.125)
        self.assertEqual(saved["events"][-1]["modelUsage"]["haiku"]["inputTokens"], 123)
        self.assertIn("[REDACTED_EMAIL]", saved["stderr"])
        self.assertIn(
            "[REDACTED_EMAIL]", saved["events"][0]["message"]["content"][0]["text"]
        )
        self.assertIn("[REDACTED_EMAIL]", saved["events"][-1]["result"])


if __name__ == "__main__":
    unittest.main()
