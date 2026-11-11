"""Private JSONL control channel for the frozen desktop sidecar."""

import json
import sys
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path

import omr
import desktop_benchmarks
from desktop_chat import CHAT_ERRORS, ChatService
from desktop_engine import Runtime
from desktop_subscriptions import CodexLogin
from desktop_portal import PortalConnector


def main():
    directory = Path(sys.argv[1])
    first = json.loads(sys.stdin.readline())
    if (
        first.get("command") != "init"
        or not isinstance(first.get("key"), str)
        or len(first["key"]) < 48
    ):
        raise SystemExit(2)
    runtime = Runtime(directory, first["key"])
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        omr.handler(
            {
                "routes": {
                    "unused": {
                        "url": "http://127.0.0.1:1/v1",
                        "model": "unused",
                        "protocol": "chat",
                    }
                },
                "default_route": "unused",
                "decision": {"type": "fixed"},
            },
            desktop=runtime,
        ),
    )
    runtime.port = server.server_port
    chat = ChatService(runtime)
    subscription = CodexLogin()
    portal = PortalConnector(directory)
    runtime.portal = portal
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(json.dumps({"ok": runtime.snapshot()}), flush=True)
    try:
        for line in sys.stdin:
            shutdown = False
            try:
                request = json.loads(line)
                command = request["command"]
                if command == "snapshot":
                    result = runtime.snapshot()
                elif command == "portal_connector":
                    connection = next(
                        (
                            c
                            for c in runtime.config["connections"]
                            if c["id"] == request.get("connection")
                            and c.get("subscription") == "nous"
                        ),
                        None,
                    )
                    if connection is None:
                        raise ValueError("model_unavailable")
                    result = portal.command(
                        request["action"],
                        request["program"],
                        request["home"],
                        connection["url"],
                    )
                elif command in (
                    "subscription",
                    "subscription_credentials",
                    "subscription_commit",
                ):
                    connection = request.get("connection")
                    if not any(
                        c["id"] == connection and c.get("subscription") == "codex"
                        for c in runtime.config["connections"]
                    ):
                        raise ValueError("model_unavailable")
                    if command == "subscription_credentials":
                        result = subscription.credentials(connection)
                    elif command == "subscription_commit":
                        result = subscription.commit(connection)
                    elif set(request) != {"command", "connection", "action"}:
                        raise ValueError("invalid_command")
                    elif request["action"] == "start":
                        result = subscription.start(connection)
                    elif (
                        request["action"] == "cancel"
                        and subscription.connection == connection
                    ):
                        result = subscription.cancel()
                    elif request["action"] == "status":
                        result = (
                            subscription.snapshot()
                            if subscription.connection == connection
                            else {
                                "connection": connection,
                                "status": "idle",
                                "auth": None,
                            }
                        )
                    else:
                        raise ValueError("invalid_command")
                elif command == "subscription_pending":
                    result = runtime.subscription_refresh.pending()
                elif command == "subscription_invalidate":
                    runtime.subscription_refresh.invalidate(request["connection"])
                    result = True
                elif command == "subscription_refreshed":
                    runtime.subscription_refresh.finish(
                        request["connection"],
                        request["generation"],
                        request.get("error"),
                    )
                    result = True
                elif command == "subscription_refresh":
                    connection = request["connection"]
                    if not any(
                        c["id"] == connection and c.get("subscription") == "codex"
                        for c in runtime.config["connections"]
                    ):
                        raise ValueError("model_unavailable")
                    result = runtime.subscription_refresh.poll(
                        connection, request["secret"]
                    )
                elif command == "benchmark_refresh":
                    if (
                        set(request) != {"command", "force"}
                        or type(request["force"]) is not bool
                    ):
                        raise ValueError("invalid_command")
                    result = desktop_benchmarks.refresh(
                        directory,
                        runtime.secrets.get(desktop_benchmarks.SECRET),
                        request["force"],
                        runtime.tls_context,
                    )
                    with runtime.lock:
                        runtime.benchmark_data = result
                elif command in ("chat_start", "chat_poll", "chat_cancel"):
                    result = chat.command(request)
                elif command == "save_config":
                    if request.get("source") == "file":
                        if set(request) != {"command", "source", "revision"}:
                            raise ValueError("invalid_config")
                        result = runtime.reload_config(request["revision"])
                    else:
                        result = runtime.save_config(
                            request["config"],
                            request["revision"],
                            request.get("consent_for"),
                        )
                    if subscription.connection is not None and not any(
                        c["id"] == subscription.connection
                        and c.get("subscription") == "codex"
                        for c in runtime.config["connections"]
                    ):
                        subscription.cancel()
                elif command == "discover":
                    result = runtime.discover(request["connection"])
                elif command == "test_generation":
                    result = runtime.verify_generation(
                        request["model"], request["consent"]
                    )
                elif command == "native":
                    result = runtime.native.command(request["request"])
                elif command == "managed":
                    result = runtime.managed.command(request["request"])
                elif command == "test_decision":
                    result = runtime.verify_decision(request.get("consent"))
                elif command == "export_receipts":
                    result = json.dumps(runtime.rows, ensure_ascii=False, indent=2)
                elif command == "secrets":
                    with runtime.lock:
                        runtime.secrets = request["values"]
                        runtime.model_states = {}
                    result = True
                elif command == "shutdown":
                    with runtime.lock:
                        if (
                            runtime.active or runtime.native.snapshot()["active"]
                        ) and not request.get("force"):
                            raise ValueError("requests_active")
                        runtime.stopping = True
                    # Tauri may kill the engine immediately after this acknowledgement.
                    # Finish native process and private HOME cleanup before sending it.
                    portal.shutdown()
                    subscription.cancel()
                    if subscription.worker:
                        subscription.worker.join(2)
                    runtime.native.shutdown()
                    chat.shutdown()
                    try:
                        runtime.managed.shutdown()
                    except ValueError:
                        runtime.stopping = False
                        raise
                    # Gateway watchers cancel the private provider children.
                    # Do not acknowledge while Tauri could orphan one by killing
                    # this engine immediately after the reply.
                    deadline = time.monotonic() + 2
                    while runtime.active and time.monotonic() < deadline:
                        time.sleep(0.025)
                    if runtime.active:
                        runtime.stopping = False
                        raise ValueError("requests_active")
                    shutdown = True
                    result = True
                else:
                    raise ValueError("invalid_command")
                print(json.dumps({"ok": result}, allow_nan=False), flush=True)
            except (ValueError, KeyError, TypeError, OSError) as error:
                print(
                    json.dumps(
                        {
                            "error": (
                                "requests_active"
                                if str(error) == "requests_active"
                                else (
                                    str(error)
                                    if str(error) in CHAT_ERRORS
                                    else runtime.safe_error(error)
                                )
                            )
                        }
                    ),
                    flush=True,
                )
            if shutdown:
                break
    finally:
        runtime.stopping = True
        portal.shutdown()
        subscription.cancel()
        if subscription.worker:
            subscription.worker.join(2)
        chat.shutdown()
        runtime.native.shutdown()
        runtime.managed.shutdown()
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--managed-download-worker":
        from desktop_managed import download_worker

        sys.exit(download_worker(Path(sys.argv[2])))
    if len(sys.argv) == 3 and sys.argv[1] == "--managed-worker":
        from desktop_managed import worker

        sys.exit(worker(Path(sys.argv[2])))
    main()
