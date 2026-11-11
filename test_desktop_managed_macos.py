"""macOS/POSIX worker ownership tests; no model, network or personal state."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import desktop_managed as managed


@unittest.skipUnless(sys.platform in ("linux", "darwin"), "POSIX process groups")
class MacOSManagedTest(unittest.TestCase):
    def test_repeated_kill_reaps_an_exited_leader_before_retrying_group_cleanup(self):
        from unittest.mock import Mock

        process = Mock(pid=12345)
        process.poll.return_value = -9
        with patch.object(
            managed.os,
            "killpg",
            side_effect=[
                PermissionError(1, "zombie-only Darwin group"),
                ProcessLookupError(3, "gone"),
            ],
        ) as kill:
            managed.kill_worker(process)
        process.poll.assert_called_once_with()
        self.assertEqual(kill.call_count, 2)

    def test_kill_permission_failure_is_not_ignored_for_a_live_worker(self):
        from unittest.mock import Mock

        process = Mock(pid=12345)
        process.poll.return_value = None
        with patch.object(
            managed.os, "killpg", side_effect=PermissionError(1, "denied")
        ) as kill:
            with self.assertRaises(PermissionError):
                managed.kill_worker(process)
        self.assertEqual(kill.call_count, 1)

    def test_macos_reports_available_but_windows_stays_unqualified(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = managed.ManagedModel(directory)
            for platform, expected in (
                ("darwin", True),
                ("linux", True),
                ("win32", False),
            ):
                with self.subTest(platform=platform), patch.object(
                    sys, "platform", platform
                ):
                    self.assertEqual(manager.snapshot()["supported"], expected)

    def exercise_worker(self, reply, check):
        real_popen = subprocess.Popen
        code = (
            "import sys,json,time,subprocess; print('{\"ready\":true}',flush=True)\nfor line in sys.stdin:\n "
            + reply
        )
        with tempfile.TemporaryDirectory() as directory, patch.object(
            managed, "FILES", {"fixture": hashlib.sha256(b"good").hexdigest()}
        ):
            manager = managed.ManagedModel(directory)
            manager.directory.mkdir(parents=True)
            (manager.directory / "fixture").write_bytes(b"good")

            def spawn(argv, **kwargs):
                self.assertTrue(kwargs["start_new_session"])
                self.assertNotIn("PATH", kwargs["env"])
                self.assertNotIn("OPENAI_API_KEY", kwargs["env"])
                self.assertEqual(kwargs["env"]["HOME"], kwargs["cwd"])
                return real_popen([sys.executable, "-I", "-c", code], **kwargs)

            try:
                with patch.object(sys, "platform", "darwin"), patch.object(
                    managed.subprocess, "Popen", side_effect=spawn
                ):
                    manager.command({"action": "start"})
                    end = time.monotonic() + 5
                    while manager.snapshot()["active"] and time.monotonic() < end:
                        time.sleep(0.01)
                    self.assertEqual(
                        manager.snapshot()["status"], "ready", manager.snapshot()
                    )
                assert manager.process is not None and manager.home is not None
                process, home = manager.process, Path(manager.home.name)
                assert process.stdin is not None and process.stdout is not None
                check(manager, process)
                manager.shutdown()
                self.assertIsNotNone(process.poll())
                self.assertFalse(home.exists())
                self.assertTrue(process.stdin.closed)
                self.assertTrue(process.stdout.closed)
            finally:
                manager.shutdown()

    def test_darwin_starts_classifies_and_reaps_its_private_group(self):
        def check(manager, process):
            result = manager.classify(
                {"messages": [{"role": "user", "content": "fixture"}]},
                [],
                threading.Event(),
                time.monotonic() + 2,
            )
            self.assertEqual(result["required_quality"], 2)
            self.assertIsNone(process.poll())

        self.exercise_worker(
            'print(json.dumps({"required_quality":2}),flush=True)', check
        )

    def test_darwin_reaps_grandchild_even_when_group_leader_exits(self):
        def check(manager, process):
            result = manager.classify(
                {"messages": [{"role": "user", "content": "fixture"}]},
                [],
                threading.Event(),
                time.monotonic() + 2,
            )
            process.wait(timeout=2)
            manager.shutdown()
            pid = result["child"]
            end = time.monotonic() + 2
            state = "unknown"
            while time.monotonic() < end:
                state = subprocess.run(
                    ["ps", "-o", "stat=", "-p", str(pid)],
                    capture_output=True,
                    text=True,
                ).stdout.strip()
                if not state or state.startswith("Z"):
                    break
                time.sleep(0.02)
            self.assertTrue(
                not state or state.startswith("Z"), "owned grandchild still running"
            )

        self.exercise_worker(
            'child=subprocess.Popen([sys.executable,"-I","-c","import time;time.sleep(30)"]);print(json.dumps({"child":child.pid}),flush=True);sys.exit(0)',
            check,
        )

    def test_darwin_watchdog_bounds_stalled_read(self):
        def check(manager, process):
            start = time.monotonic()
            with self.assertRaisesRegex(ValueError, "managed_runtime_unavailable"):
                manager.classify(
                    {"messages": [{"role": "user", "content": "fixture"}]},
                    [],
                    threading.Event(),
                    start + 0.15,
                )
            self.assertLess(time.monotonic() - start, 2)
            self.assertIsNotNone(process.poll())

        self.exercise_worker("time.sleep(30)", check)


if __name__ == "__main__":
    unittest.main()
