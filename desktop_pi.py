"""Private one-shot IPC to the compiled pi-ai adapter; no ambient credentials."""

import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time


def executable():
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    suffix = ".exe" if os.name == "nt" else ""
    return root / "desktop" / "provider-runtime" / ("omr-pi" + suffix)


def spawn_adapter():
    """One bundled adapter, isolated from ambient credentials and dotfiles."""
    if not executable().is_file():
        raise ValueError("pi_ai_unavailable")
    directory = tempfile.TemporaryDirectory(prefix="omr-pi-")
    env = {k: os.environ[k] for k in ("SystemRoot", "WINDIR") if k in os.environ}
    env.update(
        HOME=directory.name,
        USERPROFILE=directory.name,
        TMPDIR=directory.name,
        TEMP=directory.name,
        TMP=directory.name,
        NO_PROXY="*",
        no_proxy="*",
        PI_REQUEST_COMPRESSION="0",
    )
    try:
        process = subprocess.Popen(
            [str(executable())],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=directory.name,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return directory, process
    except BaseException:
        directory.cleanup()
        raise


class PiConnection:
    sock = None
    length = None

    def __init__(self, route, protocol, stopped, deadline):
        self.route, self.protocol = route, protocol
        self.stopped, self.deadline = stopped, deadline
        self.process = None
        self.done = threading.Event()
        self.watcher = None
        self.directory = None
        self.metadata = {}
        self.buffer = b""
        self.closed = False

    def connect(self):
        if not executable().is_file():
            raise ValueError("pi_ai_unavailable")

    def request(self, method, endpoint, payload, headers):
        self.directory, self.process = spawn_adapter()

        process = self.process
        assert process.stdin is not None and process.stdout is not None

        def watch():
            while not self.done.wait(0.025):
                if self.stopped.is_set() or time.monotonic() >= self.deadline:
                    try:
                        process.kill()
                    except OSError:
                        pass
                    return

        self.watcher = threading.Thread(target=watch, daemon=True)
        self.watcher.start()
        request = {
            "protocol": self.protocol,
            "url": self.route["url"],
            "key": self.route.get("_secret"),
            "body": json.loads(payload),
            "subscription": self.route.get("subscription"),
        }
        process.stdin.write(json.dumps(request).encode())
        process.stdin.close()

    def getresponse(self):
        assert self.process is not None and self.process.stdout is not None
        line = self.process.stdout.readline(4097)
        if time.monotonic() >= self.deadline:
            raise TimeoutError()
        if not line or len(line) > 4096:
            raise ValueError("pi_ai_failed")
        head = json.loads(line)
        if head.get("status") not in (200, 400, 502) or head.get("type") not in (
            "application/json",
            "text/event-stream",
        ):
            raise ValueError("pi_ai_failed")
        self.status, self.content_type = head["status"], head["type"]
        if self.status != 200:
            while self.read1(16384):
                pass
        return self

    def getheader(self, name, default=None):
        return self.content_type if name.lower() == "content-type" else default

    def read1(self, count):
        assert self.process is not None and self.process.stdout is not None
        while not self.buffer:
            line = self.process.stdout.readline(100001)
            if not line:
                if self.process.wait() != 0 and not self.stopped.is_set():
                    raise ValueError("pi_ai_failed")
                return b""
            if len(line) > 100000 or not line.endswith(b"\n"):
                raise ValueError("pi_ai_failed")
            frame = json.loads(line)
            if set(frame) == {"metadata"} and isinstance(frame["metadata"], dict):
                self.metadata = frame["metadata"]
            elif set(frame) == {"chunk"} and isinstance(frame["chunk"], str):
                self.buffer = base64.b64decode(frame["chunk"], validate=True)
            else:
                raise ValueError("pi_ai_failed")
        chunk, self.buffer = self.buffer[:count], self.buffer[count:]
        return chunk

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.done.set()
        if self.process:
            if self.process.poll() is None:
                self.process.kill()
            self.process.wait()
            for stream in (self.process.stdin, self.process.stdout):
                if stream and not stream.closed:
                    stream.close()
        if self.watcher:
            self.watcher.join(0.2)
        if self.directory:
            self.directory.cleanup()
