"""Explicit, hash-pinned local classifier; no user runtimes or ambient secrets."""

import hashlib
import json
import math
import os
from pathlib import Path
import ssl
import signal
import subprocess
import sys
import tempfile
import threading
import time
from urllib.request import (
    build_opener,
    ProxyHandler,
    Request,
    HTTPSHandler,
    HTTPRedirectHandler,
)

from omr import S1D1_FILES as FILES

REPOSITORY = "scombat/s1d1-router-6src-tiny-onnx-int8"
REVISION = "dac13b5c0356864ea4501fa151d74dcd8b3ea22a"
CHECKPOINT = "s1d1-dac13b5"
MAX_FILE = 40_000_000


def open_download(name):
    # No proxy credentials, cookies, user agent identity, keys or prompt data.
    url = f"https://huggingface.co/{REPOSITORY}/resolve/{REVISION}/{name}"

    class HTTPSRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            if not newurl.startswith("https://"):
                raise ValueError("managed_download_failed")
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    ca = Path(getattr(sys, "_MEIPASS", "")) / "certifi" / "cacert.pem"
    context = ssl.create_default_context(cafile=str(ca) if ca.is_file() else None)
    response = build_opener(
        ProxyHandler({}), HTTPSHandler(context=context), HTTPSRedirect()
    ).open(Request(url), timeout=5)
    if not response.url.startswith("https://"):
        response.close()
        raise ValueError("managed_download_failed")
    return response


def verify_weights(directory):
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("managed_integrity_failed")
    for name, expected in FILES.items():
        file = directory / name
        if file.is_symlink() or not file.is_file() or file.stat().st_size > MAX_FILE:
            raise ValueError("managed_integrity_failed")
        if hashlib.sha256(file.read_bytes()).hexdigest() != expected:
            raise ValueError("managed_integrity_failed")


def decode_quality(logit):
    if type(logit) not in (int, float) or not math.isfinite(logit):
        raise ValueError("invalid_decision")
    score = min(1.0, max(0.01, 0.5 + 0.25 * logit))
    return {
        "required_quality": 1 if score < 0.375 else 2 if score < 0.625 else 3,
        "reason": "task_requirement",
        "score": score,
    }


def prompt_text(context):
    # This trained prompt classifier is not a conversation-aware chat model.
    for message in reversed(context.get("messages", [])):
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if (
            isinstance(content, list)
            and content
            and all(
                isinstance(p, dict)
                and p.get("type") in ("text", "input_text")
                and isinstance(p.get("text"), str)
                for p in content
            )
        ):
            content = "\n".join(p["text"] for p in content)
        if (
            isinstance(content, str)
            and content.strip()
            and len(content.encode()) <= 65536
        ):
            return content
        break
    raise ValueError("unsupported_decision_context")


def worker(directory):
    """Private persistent stdio worker, invoked only via the owning engine."""
    try:
        verify_weights(directory)
        import numpy as np
        import onnxruntime as ort
        from tokenizers import Tokenizer

        tokenizer = Tokenizer.from_file(str(directory / "tokenizer.json"))
        tokenizer.no_truncation()
        tokenizer.no_padding()
        vocab = np.load(directory / "vocab_map.npy", allow_pickle=False)
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        session = ort.InferenceSession(
            str(directory / "model_int8.onnx"),
            sess_options=options,
            providers=["CPUExecutionProvider"],
        )
        verify_weights(directory)
        print('{"ready":true}', flush=True)
        while raw := sys.stdin.buffer.readline(100001):
            if len(raw) > 100000 or not raw.endswith(b"\n"):
                return 2
            try:
                request = json.loads(raw)
                text = request["prompt"]
                if (
                    not isinstance(text, str)
                    or not text.strip()
                    or len(text.encode()) > 65536
                ):
                    raise ValueError("unsupported_decision_context")
                encoded = tokenizer.encode(text)
                if len(encoded.ids) > 1024:
                    raise ValueError("decision_context_too_large")
                ids = vocab[np.array([encoded.ids], dtype=np.int64)]
                mask = np.array([encoded.attention_mask], dtype=np.int64)
                logits = np.asarray(
                    session.run(None, {"input_ids": ids, "attention_mask": mask})[0]
                )
                if logits.shape != (1, 21) or not np.isfinite(logits).all():
                    raise ValueError("invalid_decision")
                result = decode_quality(float(logits[0, 0]))
                result["usage"] = {"input_tokens": len(encoded.ids), "output_tokens": 0}
                print(json.dumps(result, allow_nan=False), flush=True)
            except (KeyError, TypeError, ValueError):
                print('{"error":"decision_context_rejected"}', flush=True)
    except Exception:
        # No paths, provider output, prompts or environment in the IPC error.
        print('{"error":"managed_runtime_unavailable"}', flush=True)
        return 1
    return 0


def download_files(directory, check=lambda: None, progress=lambda value: None):
    total = 0
    for name, expected in FILES.items():
        check()
        digest, size = hashlib.sha256(), 0
        with open_download(name) as response, (directory / name).open("xb") as out:
            while chunk := response.read1(65536):
                check()
                size += len(chunk)
                if size > MAX_FILE:
                    raise ValueError("managed_integrity_failed")
                out.write(chunk)
                digest.update(chunk)
                total += len(chunk)
                progress(total)
            out.flush()
            os.fsync(out.fileno())
        if digest.hexdigest() != expected:
            raise ValueError("managed_integrity_failed")
    verify_weights(directory)


def download_worker(directory):
    last = 0

    def progress(value):
        nonlocal last
        if value - last >= 1_000_000:
            print(json.dumps({"downloaded_bytes": value}), flush=True)
            last = value

    try:
        download_files(directory, progress=progress)
        print('{"done":true}', flush=True)
        return 0
    except Exception as error:
        code = (
            "managed_integrity_failed"
            if str(error) == "managed_integrity_failed"
            else "managed_download_failed"
        )
        print(json.dumps({"error": code}), flush=True)
        return 1


def kill_worker(process):
    # A frozen onefile worker can itself have a bootloader child. Keep the
    # process-group anchor even after its leader exits and reap the whole tree.
    try:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except PermissionError:
            # Darwin reports EPERM for an already-killed, zombie-only group.
            # Reap the captured leader, then still kill any surviving descendants.
            # A live worker's permission failure remains an error, never a bypass.
            if process.poll() is None:
                raise
            os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


class ManagedModel:
    def __init__(self, root):
        self.root = Path(root)
        self.directory = self.root / "models" / CHECKPOINT
        self.lock = threading.RLock()
        self.inference_lock = threading.Lock()
        self.cancelled = threading.Event()
        self.thread = None
        self.process = None
        self.home = None
        self.status = "installed" if self.directory.exists() else "absent"
        self.error = None
        self.downloaded = 0

    def snapshot(self):
        with self.lock:
            if (
                self.process is not None
                and self.status == "ready"
                and self.process.poll() is not None
            ):
                self._reap()
                self.status = "stopped"
                self.error = "managed_runtime_unavailable"
            return {
                "checkpoint": CHECKPOINT,
                "supported": sys.platform in ("linux", "darwin"),
                "status": self.status,
                "error": self.error,
                "active": bool(self.thread and self.thread.is_alive()),
                "downloaded_bytes": self.downloaded,
                "running": self.process is not None and self.status == "ready",
            }

    def command(self, request):
        action = request.get("action")
        if action in ("cancel", "stop"):
            with self.lock:
                self.cancelled.set()
                self._reap()
                self.status = (
                    "cancelling"
                    if self.thread and self.thread.is_alive()
                    else "cancelled" if action == "cancel" else "stopped"
                )
                self.error = None
            return self.snapshot()
        if action not in ("download", "start"):
            raise ValueError("invalid_command")
        if action == "download" and request.get("consent") is not True:
            raise ValueError("consent_required")
        with self.lock:
            if self.snapshot()["active"] or self.process is not None:
                raise ValueError("managed_busy")
            self.cancelled.clear()
            self.error = None
            self.downloaded = 0
            self.status = "downloading" if action == "download" else "starting"
            self.thread = threading.Thread(
                target=self._run, args=(action,), daemon=True
            )
            self.thread.start()
        return self.snapshot()

    def _run(self, action):
        try:
            if action == "download":
                self._download()
            else:
                self._start()
        except Exception as error:
            with self.lock:
                self._reap()
                self.status = "cancelled" if self.cancelled.is_set() else "error"
                allowed = {"managed_integrity_failed", "managed_runtime_unavailable"}
                self.error = (
                    None
                    if self.cancelled.is_set()
                    else (
                        str(error)
                        if str(error) in allowed
                        else (
                            "managed_download_failed"
                            if action == "download"
                            else "managed_runtime_unavailable"
                        )
                    )
                )

    def _check_cancel(self):
        if self.cancelled.is_set():
            raise ValueError("managed_cancelled")

    def _download(self):
        if self.directory.parent.is_symlink():
            raise ValueError("managed_integrity_failed")
        self.directory.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

        if self.directory.exists() or self.directory.is_symlink():
            verify_weights(self.directory)
        else:
            with tempfile.TemporaryDirectory(
                prefix=".managed-", dir=self.directory.parent
            ) as stage:
                stage = Path(stage)
                self._fetch(stage)
                verify_weights(stage)
                self.downloaded = sum((stage / name).stat().st_size for name in FILES)
                with self.lock:
                    self._check_cancel()
                    # Directory rename publishes only a complete checkpoint. A
                    # prior nonempty checkpoint cannot be replaced by rename.
                    os.rename(stage, self.directory)
        with self.lock:
            self._check_cancel()
            self.status = "installed"

    def _start(self):
        verify_weights(self.directory)
        process = self._spawn_worker("model", self.directory)
        self._read(process, time.monotonic() + 20, self.cancelled, ready=True)
        with self.lock:
            self._check_cancel()
            self.status = "ready"

    def _fetch(self, stage):
        process = self._spawn_worker("download", stage)
        deadline = time.monotonic() + 300
        try:
            while True:
                result = self._read(process, deadline, self.cancelled, download=True)
                if result == {"done": True}:
                    if process.wait(timeout=3) != 0:
                        raise ValueError("managed_download_failed")
                    return
                if (
                    set(result) != {"downloaded_bytes"}
                    or type(result["downloaded_bytes"]) is not int
                    or not self.downloaded
                    <= result["downloaded_bytes"]
                    <= MAX_FILE * len(FILES)
                ):
                    raise ValueError("managed_download_failed")
                with self.lock:
                    self.downloaded = result["downloaded_bytes"]
        finally:
            with self.lock:
                self._reap()

    def _spawn_worker(self, kind, directory):
        # Linux and macOS use the same owned POSIX process-group cleanup.
        # Windows remains unavailable until its separate tree cleanup is qualified.
        if sys.platform not in ("linux", "darwin"):
            raise ValueError("managed_runtime_unavailable")
        with self.lock:
            self._check_cancel()
            self.home = tempfile.TemporaryDirectory(prefix="omr-managed-")
            env = {
                k: os.environ[k] for k in ("SystemRoot", "WINDIR") if k in os.environ
            }
            env.update(
                HOME=self.home.name,
                USERPROFILE=self.home.name,
                TMPDIR=self.home.name,
                TEMP=self.home.name,
                TMP=self.home.name,
                TOKENIZERS_PARALLELISM="false",
            )
            argv = [sys.executable]
            if not getattr(sys, "frozen", False):
                source = str(Path(__file__).parent.resolve())
                argv += [
                    "-I",
                    "-c",
                    f"import sys;sys.path.insert(0,{source!r});from desktop_managed import worker,download_worker;from pathlib import Path;sys.exit((worker if sys.argv[1]=='model' else download_worker)(Path(sys.argv[2])))",
                ]
                argv += [kind]
            else:
                argv += [
                    (
                        "--managed-worker"
                        if kind == "model"
                        else "--managed-download-worker"
                    )
                ]
            argv += [str(directory.resolve())]
            self.process = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env=env,
                cwd=self.home.name,
                start_new_session=True,
            )
            return self.process

    def _read(
        self, process, deadline, stopped, ready=False, download=False, payload=None
    ):
        done = threading.Event()

        def watch():
            while not done.wait(0.025):
                if (
                    stopped.is_set()
                    or self.cancelled.is_set()
                    or time.monotonic() >= deadline
                ):
                    kill_worker(process)
                    return

        watcher = threading.Thread(target=watch, daemon=True)
        watcher.start()
        try:
            # The same watchdog owns the entire exchange, including a full
            # stdin pipe or a blocked flush. Killing this captured process group
            # releases either operation without touching a replacement worker.
            if payload is not None:
                assert process.stdin is not None
                remaining = memoryview(payload)
                while remaining:
                    if (
                        stopped.is_set()
                        or self.cancelled.is_set()
                        or time.monotonic() >= deadline
                    ):
                        raise ValueError("managed_runtime_unavailable")
                    written = process.stdin.write(remaining)
                    if not written:
                        raise ValueError("managed_runtime_unavailable")
                    remaining = remaining[written:]
                process.stdin.flush()
            assert process.stdout is not None
            raw = process.stdout.readline(4097)
            if (
                not raw
                or len(raw) > 4096
                or stopped.is_set()
                or self.cancelled.is_set()
                or time.monotonic() >= deadline
            ):
                raise ValueError("managed_runtime_unavailable")
            result = json.loads(raw)
            if result.get("error"):
                if download:
                    raise ValueError(
                        "managed_integrity_failed"
                        if result["error"] == "managed_integrity_failed"
                        else "managed_download_failed"
                    )
                raise ValueError(
                    "decision_context_rejected"
                    if not ready
                    else "managed_runtime_unavailable"
                )
            if ready and result != {"ready": True}:
                raise ValueError("managed_runtime_unavailable")
            return result
        finally:
            done.set()
            watcher.join(0.1)

    def classify(self, context, candidates, stopped, deadline):
        text = prompt_text(context)
        # Serialize the private worker channel; waiting consumes the caller's
        # deadline and remains cancellable rather than queuing unbounded work.
        while not self.inference_lock.acquire(timeout=0.025):
            if stopped.is_set() or time.monotonic() >= deadline:
                raise ValueError("decision_cancelled")
        process = None
        try:
            with self.lock:
                process = self.process
                if self.status != "ready" or process is None:
                    raise ValueError("managed_not_running")
            if stopped.is_set() or time.monotonic() >= deadline:
                raise ValueError("decision_cancelled")
            return self._read(
                process,
                deadline,
                stopped,
                payload=json.dumps({"prompt": text}).encode() + b"\n",
            )
        except Exception as error:
            with self.lock:
                # stop/start may already have reaped this generation. Never
                # clean up or publish status against a different current worker.
                if (
                    str(error) != "decision_context_rejected"
                    and process is not None
                    and self.process is process
                ):
                    self._reap()
                    self.status = "stopped"
            raise
        finally:
            self.inference_lock.release()

    def _reap(self):
        if self.process:
            process, self.process = self.process, None
            kill_worker(process)
            process.wait(timeout=3)
            for stream in (process.stdin, process.stdout):
                if stream:
                    try:
                        stream.close()
                    except OSError:
                        # Closing BufferedWriter can retry a pending flush after
                        # the owned process has been killed. Still close stdout
                        # and remove its HOME; this is not a live-worker failure.
                        pass
        if self.home:
            self.home.cleanup()
            self.home = None

    def shutdown(self):
        self.command({"action": "stop"})
        thread = self.thread
        if thread and thread is not threading.current_thread():
            thread.join(7)
            if thread.is_alive():
                raise ValueError("requests_active")
