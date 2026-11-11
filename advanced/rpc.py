"""Bounded stdio JSON-RPC transport for synthetic qualification.

Server-initiated requests are denied, never run as local tools. This is not a
replacement for an interactive client's permission UI. One reader routes frames
for concurrent request waiters and the owner's notification consumer. Callbacks
run on that reader and must not block waiting for RPC replies.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import threading
import time
from collections import deque


class StdioRPC:
    def __init__(
        self,
        command,
        *,
        timeout: float = 120,
        cwd=None,
        env=None,
        observe=None,
        stderr=None,
        handle_request=None,
    ):
        self.timeout = timeout
        self.observe = observe
        self.handle_request = handle_request
        self.process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr or subprocess.DEVNULL,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        assert self.process.stdout is not None and self.process.stdin is not None
        self._condition = threading.Condition()
        self._write_lock = threading.Lock()
        self._pending = deque()
        self._serial = 0
        self._error = None
        self._reader = threading.Thread(target=self._read, daemon=True)
        self._reader.start()

    def _read(self):
        assert self.process.stdout is not None
        error = EOFError("native RPC closed")
        try:
            for line in self.process.stdout:
                event = json.loads(line)
                if self.observe is not None:
                    self.observe(event)
                if "id" in event and "method" in event:
                    self._handle_request(event)
                else:
                    with self._condition:
                        self._pending.append(event)
                        self._condition.notify_all()
        except Exception as exc:  # noqa: BLE001 — propagate callback/parser failures to every waiter
            error = exc
        finally:
            # EOF/error is persistent: every waiter must wake, not just one.
            with self._condition:
                self._error = error
                self._condition.notify_all()

    def _handle_request(self, event):
        # A trusted owner may allow an exact synthetic data tool; all else fails closed.
        result = (
            self.handle_request(event["method"], event.get("params", {}))
            if self.handle_request
            else None
        )
        if result is None:
            self.send(
                {
                    "id": event["id"],
                    "error": {
                        "code": -32601,
                        "message": "not authorized by qualification client",
                    },
                }
            )
        else:
            self.send({"id": event["id"], "result": result})

    def send(self, payload):
        assert self.process.stdin is not None
        with self._write_lock:
            self.process.stdin.write(json.dumps(payload) + "\n")
            self.process.stdin.flush()

    def notify(self, method, params=None):
        self.send({"method": method, "params": params or {}})

    def _receive(self, predicate, deadline):
        with self._condition:
            while True:
                for index, event in enumerate(self._pending):
                    if predicate(event):
                        del self._pending[index]
                        return event
                if self._error is not None:
                    raise self._error
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("RPC timeout")
                self._condition.wait(timeout=remaining)

    def request(self, method, params):
        with self._condition:
            self._serial += 1
            request_id = self._serial
        self.send({"id": request_id, "method": method, "params": params})
        event = self._receive(
            lambda e: e.get("id") == request_id and "method" not in e,
            time.monotonic() + self.timeout,
        )
        if "error" in event:
            raise RuntimeError(
                "native RPC request rejected: " + str(event["error"].get("code"))
            )
        return event["result"]

    def wait(self, predicate, timeout):
        # Notification waiters cannot steal a response, even with a broad predicate.
        return self._receive(
            lambda e: "id" not in e and predicate(e), time.monotonic() + timeout
        )

    def close(self):
        if self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGTERM)
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=2)
        self._reader.join(timeout=2)
        for stream in (self.process.stdin, self.process.stdout):
            if stream is not None:
                stream.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
