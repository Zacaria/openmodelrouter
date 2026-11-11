"""Codex device login; only the native parent may commit credentials to its vault."""

import json
import re
import threading
import time
from desktop_pi import spawn_adapter


def validate_credentials(value):
    if (
        not isinstance(value, dict)
        or not {"access", "refresh", "expires"} <= set(value)
        or set(value)
        - {"access", "refresh", "expires", "accountId", "orgId", "orgName", "email"}
        or any(
            not isinstance(value[k], str)
            or not 1 <= len(value[k]) <= 16384
            or any(ord(c) < 32 for c in value[k])
            for k in ("access", "refresh")
        )
        or type(value["expires"]) is not int
        or not 0 < value["expires"] <= 9007199254740991
        or any(
            not isinstance(value[k], str)
            or not 1 <= len(value[k]) <= 1024
            or any(ord(c) < 32 for c in value[k])
            for k in ("orgId", "orgName", "email")
            if k in value
        )
        or (
            "accountId" in value
            and (
                not isinstance(value["accountId"], str)
                or not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", value["accountId"])
            )
        )
    ):
        raise ValueError("subscription_failed")
    return value


def run_private(request):
    directory, process = spawn_adapter()
    assert process.stdin is not None and process.stdout is not None
    timer = threading.Timer(30, process.kill)
    timer.daemon = True
    timer.start()
    try:
        process.stdin.write(json.dumps(request).encode())
        process.stdin.close()
        line = process.stdout.readline(65537)
        if len(line) > 65536 or not line.endswith(b"\n"):
            raise ValueError("subscription_failed")
        result = json.loads(line)
        if process.wait() != 0 or "error" in result:
            raise ValueError("subscription_failed")
        return result
    finally:
        timer.cancel()
        if process.poll() is None:
            process.kill()
        process.wait()
        process.stdout.close()
        directory.cleanup()


def refresh(secret):
    value = validate_credentials(json.loads(secret))
    result = validate_credentials(
        run_private({"action": "codex_refresh", "credentials": value})["credentials"]
    )
    if result["expires"] <= time.time() * 1000:
        raise ValueError("subscription_expired")
    return json.dumps(result)


def access(secret):
    try:
        value = validate_credentials(json.loads(secret))
        if value["expires"] <= time.time() * 1000:
            raise ValueError()
        return value["access"]
    except (TypeError, ValueError, KeyError):
        raise ValueError("subscription_expired") from None


class NativeRefresh:
    """Gateway waiters rendezvous with the native vault owner over private IPC."""

    def __init__(self, lock):
        self.condition = threading.Condition(lock)
        self.requests = {}
        self.generation = 0

    def _request(self, connection):
        request = self.requests.get(connection)
        if request is None or request["done"]:
            self.generation += 1
            request = {
                "generation": self.generation,
                "waiters": 0,
                "done": False,
                "error": None,
                "working": False,
                "result": None,
                "source": None,
            }
            self.requests[connection] = request
        return request

    def poll(self, connection, secret):
        """Private native IPC only; parallel grants, never parallel vault writers."""
        with self.condition:
            request = self._request(connection)
            if request["working"] and request["source"] != secret:
                self.invalidate(connection)
                request = self._request(connection)
            if not request["working"]:
                request["working"] = True
                request["source"] = secret

                def run():
                    try:
                        result = {"status": "authenticated", "secret": refresh(secret)}
                    except Exception:
                        result = {"status": "failed", "error": "subscription_failed"}
                    with self.condition:
                        request["result"] = result

                threading.Thread(target=run, daemon=True).start()
            return {
                "generation": request["generation"],
                **(request["result"] or {"status": "refreshing"}),
            }

    def invalidate(self, connection):
        with self.condition:
            request = self.requests.pop(connection, None)
            if request is not None:
                request["done"] = True
                request["error"] = "subscription_expired"
                self.condition.notify_all()

    def wait(self, connection, stopped, deadline):
        deadline = min(deadline or time.monotonic() + 30, time.monotonic() + 30)
        with self.condition:
            request = self._request(connection)
            request["waiters"] += 1
            try:
                while not request["done"]:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or (stopped is not None and stopped.is_set()):
                        raise ValueError("subscription_expired")
                    self.condition.wait(min(0.1, remaining))
                if request["error"]:
                    raise ValueError(request["error"])
            finally:
                request["waiters"] -= 1
                # Finish/persist a rotated grant even if every HTTP caller cancelled.
                if (
                    request["waiters"] == 0
                    and self.requests.get(connection) is request
                    and (request["done"] or not request["working"])
                ):
                    del self.requests[connection]

    def pending(self):
        with self.condition:
            return [
                {"connection": id_, "generation": item["generation"]}
                for id_, item in self.requests.items()
                if not item["done"]
            ]

    def finish(self, connection, generation, error=None):
        with self.condition:
            request = self.requests.get(connection)
            if request is not None and request["generation"] == generation:
                request["done"] = True
                request["error"] = (
                    error
                    if error
                    in (
                        "vault_unavailable",
                        "subscription_failed",
                        "subscription_expired",
                    )
                    else None
                )
                if request["waiters"] == 0:
                    del self.requests[connection]
                self.condition.notify_all()


class CodexLogin:
    def __init__(self):
        self.lock = threading.RLock()
        self.worker = None
        self.process = None
        self.connection = None
        self.status = "idle"
        self.auth = None
        self.value = None

    def start(self, connection):
        with self.lock:
            if self.worker and self.worker.is_alive():
                raise ValueError("subscription_busy")
            self.connection, self.status = connection, "starting"
            self.auth, self.value = None, None
            self.worker = threading.Thread(target=self._login, daemon=True)
            self.worker.start()
        return self.snapshot()

    def _login(self):
        directory, process = None, None
        try:
            directory, process = spawn_adapter()
            assert process.stdin is not None and process.stdout is not None
            with self.lock:
                self.process = process
                if self.status == "cancelled":
                    process.kill()
                    return
            timer = threading.Timer(600, process.kill)
            timer.daemon = True
            timer.start()
            try:
                process.stdin.write(b'{"action":"codex_login"}')
                process.stdin.close()
                for _ in range(3):
                    line = process.stdout.readline(65537)
                    if not line or len(line) > 65536 or not line.endswith(b"\n"):
                        raise ValueError("subscription_failed")
                    frame = json.loads(line)
                    with self.lock:
                        if self.status == "cancelled":
                            return
                        if set(frame) == {"auth"}:
                            auth = frame["auth"]
                            if (
                                set(auth) != {"url", "code"}
                                or auth["url"] != "https://auth.openai.com/codex/device"
                                or not isinstance(auth["code"], str)
                                or not re.fullmatch(r"[A-Za-z0-9-]{4,32}", auth["code"])
                            ):
                                raise ValueError("subscription_failed")
                            self.auth, self.status = auth, "waiting"
                        elif set(frame) == {"credentials"}:
                            value = validate_credentials(frame["credentials"])
                            if value["expires"] <= time.time() * 1000:
                                raise ValueError("subscription_expired")
                            if process.wait() != 0:
                                raise ValueError("subscription_failed")
                            self.value, self.status, self.auth = (
                                value,
                                "authenticated",
                                None,
                            )
                            return
                        else:
                            raise ValueError("subscription_failed")
            finally:
                timer.cancel()
        except Exception:
            with self.lock:
                if self.status != "cancelled":
                    self.status = "failed"
                self.auth, self.value = None, None
        finally:
            if process:
                if process.poll() is None:
                    process.kill()
                process.wait()
                for stream in (process.stdin, process.stdout):
                    if stream and not stream.closed:
                        stream.close()
            if directory:
                directory.cleanup()
            with self.lock:
                self.process = None

    def snapshot(self):
        with self.lock:
            return {
                "connection": self.connection,
                "status": self.status,
                "auth": self.auth,
            }

    def credentials(self, connection):
        with self.lock:
            return (
                json.dumps(self.value)
                if self.value and connection == self.connection
                else None
            )

    def commit(self, connection):
        with self.lock:
            if connection != self.connection or not self.value:
                raise ValueError("subscription_failed")
            self.value, self.status = None, "connected"
        return self.snapshot()

    def cancel(self):
        with self.lock:
            self.value, self.auth, self.status = None, None, "cancelled"
            if self.process and self.process.poll() is None:
                self.process.kill()
        return self.snapshot()
