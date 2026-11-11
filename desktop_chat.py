"""Ephemeral native text Chat over the real authenticated OMR gateway.

No provider credentials or transcripts are exposed through snapshots or persisted.
"""

import http.client
import json
import socket
import threading
import time
import uuid

from desktop_engine import PROFILES

MAX_INPUT = 128 * 1024
MAX_OUTPUT = 1024 * 1024
MAX_EVENT = 64 * 1024
TIMEOUT = 120
POLL_LEASE = 15
CHAT_ERRORS = frozenset(
    {
        "chat_invalid",
        "chat_input_limit",
        "chat_output_limit",
        "chat_route_changed",
        "chat_busy",
        "chat_expired",
        "chat_timeout",
        "chat_cancelled",
        "chat_empty",
        "chat_length",
        "chat_refused",
        "chat_tools",
        "chat_identity",
        "chat_http",
        "chat_incomplete",
        "chat_unavailable",
    }
)


def require(condition, code="chat_invalid"):
    if not condition:
        raise ValueError(code)


def identifier(value):
    require(isinstance(value, str))
    try:
        require(str(uuid.UUID(value)) == value)
    except (ValueError, AttributeError):
        raise ValueError("chat_invalid") from None
    return value


class TextStream:
    """Strict text-only completion validator, independent of frame boundaries."""

    def __init__(self, protocol):
        self.protocol = protocol
        self.terminal = False
        self.done_marker = False
        self.reason = None
        self.has_text = False

    def event(self, raw):
        if raw == b"[DONE]":
            require(
                not self.done_marker
                and (
                    (
                        self.protocol == "chat"
                        and self.reason == "stop"
                        and not self.terminal
                    )
                    or (self.protocol == "responses" and self.terminal)
                ),
                "chat_incomplete",
            )
            self.done_marker = True
            self.terminal = True
            return None
        value = json.loads(raw)
        require(isinstance(value, dict), "chat_incomplete")
        require(not self.terminal, "chat_incomplete")
        kind = value.get("type")
        require(
            "error" not in value and kind not in ("error", "response.failed"),
            "chat_incomplete",
        )
        text = None
        if self.protocol == "chat":
            choices = value.get("choices", [])
            require(isinstance(choices, list) and len(choices) <= 1, "chat_incomplete")
            for choice in choices:
                require(choice.get("index", 0) == 0, "chat_incomplete")
                delta = choice.get("delta", {})
                require(
                    self.reason is None or not delta.get("content"), "chat_incomplete"
                )
                require(not delta.get("refusal"), "chat_refused")
                require(
                    not delta.get("tool_calls") and not delta.get("function_call"),
                    "chat_tools",
                )
                text = delta.get("content")
                reason = choice.get("finish_reason")
                if reason:
                    require(reason != "length", "chat_length")
                    require(reason != "content_filter", "chat_refused")
                    require(reason == "stop", "chat_tools")
                    self.reason = reason
        elif self.protocol == "responses":
            require(
                kind != "response.refusal.delta" and kind != "response.refusal.done",
                "chat_refused",
            )
            if kind == "response.incomplete":
                raise ValueError(
                    "chat_length"
                    if value.get("response", {})
                    .get("incomplete_details", {})
                    .get("reason")
                    == "max_output_tokens"
                    else "chat_incomplete"
                )
            item = value.get("item", {})
            require(item.get("type") != "function_call", "chat_tools")
            if kind == "response.output_item.done":
                require(
                    item.get("status", "completed") == "completed", "chat_incomplete"
                )
            if kind == "response.output_text.delta":
                text = value.get("delta")
            if kind == "response.completed":
                response = value.get("response", {})
                require(
                    response.get("status") == "completed"
                    and response.get("incomplete_details") is None,
                    "chat_incomplete",
                )
                for output in response.get("output", []):
                    require(
                        output.get("status", "completed") == "completed",
                        "chat_incomplete",
                    )
                    require(output.get("type") != "function_call", "chat_tools")
                    require(
                        not any(
                            part.get("type") == "refusal"
                            for part in output.get("content", [])
                        ),
                        "chat_refused",
                    )
                self.terminal = True
        else:
            block = value.get("content_block", {})
            require(block.get("type") != "tool_use", "chat_tools")
            if (
                kind == "content_block_delta"
                and value.get("delta", {}).get("type") == "text_delta"
            ):
                text = value["delta"].get("text")
            if kind == "message_delta":
                self.reason = value.get("delta", {}).get("stop_reason")
                require(self.reason != "max_tokens", "chat_length")
                require(self.reason != "refusal", "chat_refused")
                require(self.reason in ("end_turn", "stop_sequence"), "chat_tools")
            if kind == "message_stop":
                require(self.reason in ("end_turn", "stop_sequence"), "chat_incomplete")
                self.terminal = True
        if text is not None:
            require(isinstance(text, str), "chat_incomplete")
            self.has_text |= bool(text.strip())
        return text

    def finish(self):
        require(self.terminal, "chat_incomplete")
        require(self.has_text, "chat_empty")


class Job:
    def __init__(self, request):
        self.id = request["id"]
        self.session = request["session"]
        self.events = []
        self.lock = threading.Lock()
        self.stopped = threading.Event()
        self.done = threading.Event()
        self.last_poll = time.monotonic()
        self.started = self.last_poll
        self.socket: socket.socket | None = None
        self.reason = "chat_cancelled"
        self.thread: threading.Thread | None = None

    def cancel(self, reason="chat_cancelled"):
        self.reason = reason
        self.stopped.set()
        with self.lock:
            sock = self.socket
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    def emit(self, event):
        with self.lock:
            self.events.append(event)


class ChatService:
    def __init__(self, runtime):
        self.runtime = runtime
        self.job = None
        self.lock = threading.Lock()

    def command(self, request):
        command = request.get("command")
        id_ = identifier(request.get("id"))
        with self.lock:
            if command == "chat_start":
                require(
                    set(request)
                    == {"command", "id", "session", "model", "revision", "messages"}
                )
                identifier(request["session"])
                require(self.job is None or self.job.done.is_set(), "chat_busy")
                messages = request["messages"]
                require(isinstance(messages, list) and 0 < len(messages) <= 64)
                for index, message in enumerate(messages):
                    require(
                        isinstance(message, dict)
                        and set(message) == {"role", "content"}
                    )
                    require(
                        message["role"] == ("user" if index % 2 == 0 else "assistant")
                    )
                    require(
                        isinstance(message["content"], str)
                        and bool(message["content"].strip())
                    )
                require(len(messages) % 2 == 1)
                require(
                    len(json.dumps(messages, ensure_ascii=False).encode()) <= MAX_INPUT,
                    "chat_input_limit",
                )
                with self.runtime.lock:
                    require(not self.runtime.stopping, "engine_unavailable")
                    require(
                        type(request["revision"]) is int
                        and request["revision"] == self.runtime.revision,
                        "chat_route_changed",
                    )
                    require(isinstance(request["model"], str))
                    virtual = request["model"] in {f"omr/{p}" for p in PROFILES}
                    require(
                        not virtual
                        or bool((self.runtime.config["decider"] or {}).get("consent")),
                        "chat_route_changed",
                    )
                    models = [
                        m
                        for route, _c, m in self.runtime.routes()
                        if virtual or route == request["model"]
                    ]
                    require(bool(models), "chat_route_changed")
                    protocol = next(
                        (
                            p
                            for p in ("chat", "responses", "anthropic")
                            if any(p in m["protocols"] for m in models)
                        ),
                        None,
                    )
                    require(protocol is not None, "incompatible_protocol")
                    model = None if virtual else models[0]["upstream"]
                job = Job(request)
                self.job = job
                job.thread = threading.Thread(
                    target=self._run, args=(job, request, protocol, model), daemon=True
                )
                job.thread.start()
                return True
            require(set(request) == {"command", "id"})
            job = self.job
            if command == "chat_cancel":
                if job and job.id == id_ and not job.done.is_set():
                    job.cancel()
                return True
            require(
                command == "chat_poll" and job is not None and job.id == id_,
                "chat_expired",
            )
            assert job is not None
            with job.lock:
                job.last_poll = time.monotonic()
                events, job.events = job.events, []
                return {"events": events, "done": job.done.is_set()}

    def shutdown(self):
        with self.lock:
            job = self.job
            if job and not job.done.is_set():
                job.cancel()
        if job and job.thread:
            job.thread.join(2)

    def _receipt(self, job):
        request_id = getattr(job, "request_id", None)
        if request_id is None:
            return None
        # The response header binds this turn to one gateway receipt.
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            with self.runtime.lock:
                row = next(
                    (
                        r
                        for r in reversed(self.runtime.rows)
                        if r.get("request_id") == request_id
                    ),
                    None,
                )
                if row:
                    return {
                        k: row.get(k)
                        for k in (
                            "request_id",
                            "status",
                            "model_requested",
                            "model_observed",
                            "model_identity_unrecognized",
                            "upstream_status",
                            "error",
                        )
                    }
            time.sleep(0.01)
        return None

    def _run(self, job, request, protocol, model):
        client = http.client.HTTPConnection(
            "127.0.0.1", self.runtime.port, timeout=TIMEOUT
        )
        monitor_done = threading.Event()

        def watch():
            while not monitor_done.wait(0.025):
                if time.monotonic() - job.started >= TIMEOUT:
                    job.cancel("chat_timeout")
                elif time.monotonic() - job.last_poll >= POLL_LEASE:
                    job.cancel("chat_expired")
                if job.stopped.is_set():
                    return

        watcher = threading.Thread(target=watch, daemon=True)
        watcher.start()
        error = None
        status = None
        try:
            client.connect()
            with job.lock:
                job.socket = client.sock
            if job.stopped.is_set():
                raise ValueError(job.reason)
            messages = request["messages"]
            payload = {"model": request["model"], "stream": True}
            path = {
                "chat": "/v1/chat/completions",
                "responses": "/v1/responses",
                "anthropic": "/v1/messages",
            }[protocol]
            if protocol == "responses":
                payload.update(
                    input=[
                        {"role": m["role"], "content": m["content"]} for m in messages
                    ],
                    max_output_tokens=4096,
                )
            else:
                payload.update(messages=messages, max_tokens=4096)
            client.request(
                "POST",
                path,
                json.dumps(payload),
                {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + self.runtime.key,
                    "X-OMR-Session": job.session,
                    "X-OMR-Config-Revision": str(request["revision"]),
                    "anthropic-version": "2023-06-01",
                },
            )
            response = client.getresponse()
            status = response.status
            ids = response.headers.get_all("X-OMR-Request", [])
            if status != 200 and not ids:
                raise ValueError("chat_http")
            require(len(ids) == 1, "chat_identity")
            try:
                job.request_id = identifier(ids[0])
            except ValueError:
                raise ValueError("chat_identity") from None
            require(status == 200, "chat_http")
            require(
                "text/event-stream" in response.getheader("Content-Type", ""),
                "chat_incomplete",
            )
            parser = TextStream(protocol)
            buffer = b""
            data = []
            frame_size = 0
            total = 0
            while True:
                chunk = response.read1(16384)
                if not chunk:
                    break
                if job.stopped.is_set():
                    raise ValueError(job.reason)
                total += len(chunk)
                require(total <= MAX_OUTPUT, "chat_output_limit")
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    line = line.removesuffix(b"\r")
                    frame_size += len(line)
                    require(frame_size <= MAX_EVENT, "chat_output_limit")
                    if line.startswith(b"data:"):
                        data.append(line[5:].removeprefix(b" "))
                    elif not line:
                        if data:
                            text = parser.event(b"\n".join(data))
                            if text:
                                job.emit({"type": "text", "text": text})
                        data = []
                        frame_size = 0
                require(len(buffer) <= MAX_EVENT, "chat_output_limit")
            require(not buffer and not data, "chat_incomplete")
            parser.finish()
        except (
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
            OSError,
            http.client.HTTPException,
        ) as exc:
            code = str(exc)
            error = code if code in CHAT_ERRORS else "chat_unavailable"
        finally:
            # On validation failure, closing the downstream socket propagates
            # cancellation even if the provider continues sending indefinitely.
            with job.lock:
                sock, job.socket = job.socket, None
            if sock:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            client.close()
            receipt = self._receipt(job)
            if job.stopped.is_set():
                error = job.reason
            if error is None:
                expected_model = model or (receipt or {}).get("model_requested")
                if (
                    not receipt
                    or not expected_model
                    or receipt["model_observed"] != expected_model
                    or receipt["model_identity_unrecognized"]
                ):
                    error = "chat_identity"
                elif receipt["status"] != "completed":
                    error = "chat_incomplete"
            event: dict = (
                {"type": "error", "code": error} if error else {"type": "finish"}
            )
            event.update(receipt=receipt, http_status=status)
            with job.lock:
                job.events.append(event)
                job.done.set()
            monitor_done.set()
            watcher.join(0.1)
