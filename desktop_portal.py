"""Lifecycle for the installed Hermes Portal connector, in an OMR-owned home."""

import ast
import json
import os
import re
import secrets
import signal
import socket
import subprocess
import threading
from pathlib import Path
from urllib.parse import urlsplit
from desktop_managed import kill_worker

# Executed by the installed Hermes interpreter, not the frozen sidecar's Python.
# Its existing bootstrap is retained; credentials stay in this OMR-owned home.
PORTAL_HOST = r"""
import asyncio, contextlib, hmac, json, logging, os, runpy, signal, sys

def permit(headers, key):
    values = headers.getall("Authorization", [])
    return bool(key) and not headers.get("Origin") and len(values) == 1 and hmac.compare_digest(values[0].encode(), ("Bearer " + key).encode())

def emit(value):
    output.write(json.dumps(value) + "\n")
    output.flush()

def create_guarded_app(adapter, key):
    from aiohttp import web
    from hermes_cli.proxy.server import create_app
    # Refresh before dispatch, never replay an inference after an HTTP failure.
    adapter.get_retry_credential = lambda **kwargs: None
    app = create_app(adapter, bound_host="127.0.0.1")
    @web.middleware
    async def authorize(request, handler):
        if not permit(request.headers, key):
            return web.json_response({"error": {"code": "unauthorized"}}, status=401)
        return await handler(request)
    app.middlewares.insert(0, authorize)
    return app

async def serve(payload):
    from aiohttp import web
    from hermes_cli.proxy.adapters import get_adapter
    adapter = get_adapter("nous")
    if not adapter.is_authenticated():
        raise RuntimeError("portal_unavailable")
    app = create_guarded_app(adapter, payload["key"])
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    try:
        await web.TCPSite(runner, "127.0.0.1", payload["port"]).start()
        emit({"ready": True})
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stop.set)
        await stop.wait()
    finally:
        await runner.cleanup()

def main():
    payload = json.loads(sys.stdin.readline(8193))
    logging.disable(logging.CRITICAL)
    with open(os.devnull, "w") as quiet, contextlib.redirect_stdout(quiet):
        if payload["action"] == "start":
            asyncio.run(serve(payload))
        else:
            import hermes_cli.auth as auth
            import hermes_cli.auth_device_flow as device
            def instructions(url, code, **kwargs):
                emit({"auth": {"url": url, "code": code}})
            auth._print_device_code_instructions = instructions
            device._print_device_code_instructions = instructions
            sys.argv = ["hermes", "auth", "add", "nous", "--type", "oauth", "--no-browser"]
            runpy.run_module("hermes_cli.main", run_name="__main__", alter_sys=True)

if __name__ == "__main__":
    output = sys.stdout
    try:
        main()
    except SystemExit as error:
        emit({"complete": error.code in (None, 0)})
        raise
    except Exception:
        emit({"complete": False})
        sys.exit(1)
    else:
        emit({"complete": True})
"""


def host_command(program, env):
    result = subprocess.run(
        [program, "--print-runtime-command"],
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=10,
        check=True,
    )
    if len(result.stdout) > 65536:
        raise ValueError("portal_unavailable")
    command = json.loads(result.stdout)
    if (
        not isinstance(command, list)
        or len(command) != 4
        or command[1:3] != ["-I", "-c"]
    ):
        raise ValueError("portal_unavailable")
    tree = ast.parse(command[3])
    final = tree.body[-1]
    if not (
        isinstance(final, ast.Expr)
        and isinstance(final.value, ast.Call)
        and isinstance(final.value.func, ast.Attribute)
        and isinstance(final.value.func.value, ast.Name)
        and final.value.func.value.id == "runpy"
        and final.value.func.attr == "run_module"
        and final.value.args
        and isinstance(final.value.args[0], ast.Constant)
        and final.value.args[0].value == "hermes_cli.main"
    ):
        raise ValueError("portal_unavailable")
    tree.body[-1:] = ast.parse(PORTAL_HOST).body
    return [command[0], "-I", "-c", ast.unparse(tree)]


class PortalConnector:
    def __init__(self, directory):
        self.directory = Path(directory) / "portal-connector"
        self.children = {}
        self.lock = threading.RLock()
        self.auth = None
        self.key = None
        self.url = None
        self.ready = False
        self.error = None

    def command(self, action, program, home, url):
        if (
            os.name == "nt"
            or not Path(program).is_file()
            or not Path(program).is_absolute()
        ):
            raise ValueError("portal_unavailable")
        match = re.fullmatch(r"http://127\.0\.0\.1:([0-9]{4,5})/v1", url)
        if not match or not 1024 <= int(match[1]) <= 65535:
            raise ValueError("invalid_config")
        if action == "status":
            return self.snapshot(url)
        if action == "stop":
            self.shutdown()
            return self.snapshot(url)
        if action == "cancel":
            self.stop_child("login")
            with self.lock:
                self.auth = None
            return self.snapshot(url)
        if action not in ("login", "start"):
            raise ValueError("invalid_command")
        old = self.children.get(action)
        if old and old.poll() is None:
            return self.snapshot(url)
        if action == "start":
            with socket.socket() as check:
                try:
                    check.bind(("127.0.0.1", int(match[1])))
                except OSError:
                    raise ValueError("portal_port_in_use") from None
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        env = {
            "HOME": home,
            "USERPROFILE": home,
            "HERMES_HOME": str(self.directory),
            "HERMES_SHARED_AUTH_DIR": str(self.directory / "shared-auth"),
            "HERMES_PROFILE": "default",
            "PATH": "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
            "PYTHONUNBUFFERED": "1",
        }
        args = host_command(program, env)
        with self.lock:
            self.error = None
            if action == "login":
                self.auth = None
            else:
                self.key, self.ready = secrets.token_urlsafe(48), False
                self.url = url
            payload = {"action": action, "port": int(match[1]), "key": self.key}
        process = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=self.directory,
            env=env,
            start_new_session=True,
        )
        with self.lock:
            self.children[action] = process
        assert process.stdin is not None
        try:
            process.stdin.write(json.dumps(payload).encode() + b"\n")
            process.stdin.close()
        except Exception:
            self.stop_child(action)
            raise ValueError("portal_unavailable") from None
        threading.Thread(
            target=self.read_frames, args=(action, process), daemon=True
        ).start()
        return self.snapshot(url)

    def accept_frame(self, action, frame):
        with self.lock:
            if action == "login" and set(frame) == {"auth"}:
                auth = frame["auth"]
                url = urlsplit(auth["url"])
                if (
                    set(auth) != {"url", "code"}
                    or len(auth["url"]) > 2048
                    or url.scheme != "https"
                    or url.hostname != "portal.nousresearch.com"
                    or url.username
                    or url.password
                    or url.port not in (None, 443)
                    or url.fragment
                    or any(ord(c) < 32 for c in auth["url"])
                    or not isinstance(auth["code"], str)
                    or not re.fullmatch(r"[A-Za-z0-9-]{4,32}", auth["code"])
                ):
                    raise ValueError("portal_unavailable")
                self.auth = auth
            elif action == "start" and frame == {"ready": True}:
                self.ready = True
            elif set(frame) == {"complete"} and type(frame["complete"]) is bool:
                if action == "login":
                    self.auth = None
                if not frame["complete"]:
                    self.error = "portal_unavailable"
            else:
                raise ValueError("portal_unavailable")

    def read_frames(self, action, process):
        timer = threading.Timer(600, process.kill) if action == "login" else None
        if timer:
            timer.daemon = True
            timer.start()
        try:
            assert process.stdout is not None
            for _ in range(4):
                line = process.stdout.readline(4097)
                if not line:
                    break
                if len(line) > 4096 or not line.endswith(b"\n"):
                    raise ValueError("portal_unavailable")
                with self.lock:
                    if self.children.get(action) is not process:
                        return
                    self.accept_frame(action, json.loads(line))
            process.wait()
        except Exception:
            with self.lock:
                if self.children.get(action) is process:
                    self.error = "portal_unavailable"
            if process.poll() is None:
                process.kill()
            process.wait()
        finally:
            if timer:
                timer.cancel()
            if process.stdout:
                process.stdout.close()

    def secret(self, url):
        with self.lock:
            process = self.children.get("start")
            if (
                url != self.url
                or not self.ready
                or process is None
                or process.poll() is not None
                or not self.key
            ):
                raise ValueError("portal_unavailable")
            return self.key

    def snapshot(self, url):
        return {
            "url": url,
            "login": (
                self.children["login"].poll() if "login" in self.children else None
            ),
            "logging_in": "login" in self.children
            and self.children["login"].poll() is None,
            "running": "start" in self.children
            and self.children["start"].poll() is None
            and self.ready,
            "auth": self.auth,
            "error": self.error,
        }

    def stop_child(self, action):
        with self.lock:
            process = self.children.pop(action, None)
            if action == "start":
                self.key, self.ready = None, False
        if process is not None and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
            kill_worker(process)
            process.wait()

    def shutdown(self):
        for action in list(self.children):
            self.stop_child(action)
        with self.lock:
            self.auth = None
