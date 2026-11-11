"""Remote native OMP RPC driver, executed only by probe_omp."""

import json
import os
import queue
import signal
import subprocess
import tempfile
import threading
import time
from collections import deque
from pathlib import Path

from advanced.omp import OMPStrategies


def public_frame(value):
    if isinstance(value, dict):
        return {
            k: public_frame(v)
            for k, v in value.items()
            if k not in {"accountAccess", "credentialId"}
        }
    if isinstance(value, list):
        return [public_frame(v) for v in value]
    return value


class RPC:
    def __init__(self, process):
        self.p = process
        self.q = queue.Queue()
        self.pending = deque()
        self.events = []
        self.serial = 0
        threading.Thread(target=self.read, daemon=True).start()

    def read(self):
        assert self.p.stdout is not None
        try:
            for line in self.p.stdout:
                self.q.put(public_frame(json.loads(line)))
        finally:
            self.q.put(None)

    def receive(self, timeout):
        e = self.q.get(timeout=timeout)
        if e is None:
            raise EOFError("OMP stopped")
        self.events.append(e)
        # No extension UI is enabled, but never approve if the native client asks.
        if e.get("type") == "extension_ui_request":
            self.send(
                {"type": "extension_ui_response", "id": e["id"], "cancelled": True}
            )
        return e

    def send(self, payload):
        assert self.p.stdin is not None
        self.p.stdin.write(json.dumps(payload) + "\n")
        self.p.stdin.flush()

    def request(self, command, params):
        self.serial += 1
        rid = str(self.serial)
        self.send({"id": rid, "type": command, **params})
        return self.wait(
            lambda e: e.get("type") == "response" and e.get("id") == rid, 90
        )

    def wait(self, predicate, timeout):
        for e in list(self.pending):
            if predicate(e):
                self.pending.remove(e)
                return e
        deadline = time.monotonic() + timeout
        while True:
            e = self.receive(max(0.001, deadline - time.monotonic()))
            if predicate(e):
                return e
            self.pending.append(e)
            if time.monotonic() >= deadline:
                raise TimeoutError("OMP RPC timeout")


def main():
    result = {}
    with tempfile.TemporaryDirectory(prefix="omr-advanced-rpc-") as project:
        env = {
            "HOME": os.path.expanduser("~"),
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
            "LANG": "en_US.UTF-8",
        }
        overlay = Path(project) / "qualification.json"
        overlay.write_text(json.dumps({"compaction": {"keepRecentTokens": 256}}))
        command = [
            "/Users/operator/omr-host-adapters-task/bin/omp",
            "--mode",
            "rpc",
            "--no-session",
            "--model",
            "openai-codex/gpt-6-luna",
            "--smol",
            "openai-codex/gpt-6-luna",
            "--slow",
            "openai-codex/gpt-6-luna",
            "--config",
            str(overlay),
            "--thinking",
            "low",
            "--system-prompt",
            "Synthetic qualification. No tools. Remember the permanent marker and specification. Answer French with prefix RAPPORT:.",
            "--cwd",
            project,
            "--no-tools",
            "--no-lsp",
            "--no-extensions",
            "--no-skills",
            "--no-rules",
            "--no-context-files",
            "--no-title",
        ]
        p = subprocess.Popen(
            command,
            env=env,
            cwd=project,
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        assert p.stdin is not None and p.stdout is not None and p.stderr is not None
        rpc = RPC(p)
        adapter = OMPStrategies(rpc, timeout=90)
        result["command"] = command
        try:
            result["protocol"] = rpc.request(
                "negotiate_protocol", {"protocolVersion": 2}
            )
            result["initial_state"] = rpc.request("get_state", {})
            if result["initial_state"]["data"]["model"]["provider"] != "openai-codex":
                raise RuntimeError("native subscription provider mismatch")
            seed = "OMR_SYNTHETIC_FIXTURE=blue-otter-73. label(w): LIGHT if w < 10 else HEAVY, reject negative. Remember this.\n"
            noise = "\n".join(
                f"Synthetic archived note {i}: no change to the permanent fixture or label specification."
                for i in range(120)
            )
            result["seed"] = adapter.turn(seed + noise + "\nReply LIGHT only.")
            result["maintain"] = adapter.turn(
                "Recall the marker and label(10), one sentence."
            )
            result["switch_model"] = adapter.switch("openai-codex", "gpt-6.1-sol")
            result["switch"] = adapter.turn(
                "Recall the marker and label(10), one sentence."
            )
            result["compaction"] = adapter.compact(
                "Preserve the permanent marker, label specification and system instructions."
            )
            result["switch_back"] = adapter.switch("openai-codex", "gpt-6-luna")
            result["compact_switch"] = adapter.turn(
                "Recall the marker and label(10), one sentence."
            )
            result["stats"] = rpc.request("get_session_stats", {})
            result["status"] = "completed"
        except (RuntimeError, OSError, ValueError, KeyError, queue.Empty) as exc:
            result["status"] = "failed"
            result["error"] = type(exc).__name__ + ": " + str(exc)
        finally:
            if p.poll() is None:
                os.killpg(p.pid, signal.SIGTERM)
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                p.wait(timeout=3)
            result["events"] = rpc.events
            result["stderr"] = p.stderr.read()
            p.stdin.close()
            p.stdout.close()
            p.stderr.close()
    print(json.dumps(result))


if __name__ == "__main__":
    main()
