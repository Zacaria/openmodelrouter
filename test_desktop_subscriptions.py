"""OAuth uses private IPC; snapshots never contain provider credentials."""

import io
import json
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from pathlib import Path
import desktop_subscriptions as subscriptions

CREDENTIALS = {
    "access": "private-access",
    "refresh": "private-refresh",
    "expires": 1900000000000,
}


class Process:
    def __init__(self, frames):
        self.stdin = io.BytesIO()
        self.stdout = io.BytesIO(
            b"".join(json.dumps(f).encode() + b"\n" for f in frames)
        )
        self.killed = False

    def poll(self):
        return 0

    def wait(self, timeout=None):
        return 0

    def kill(self):
        self.killed = True


class Subscriptions(unittest.TestCase):
    def test_replaced_or_removed_grant_fences_old_refresh_and_waiters(self):
        for replacement in ("new-grant", "old-grant", None):
            with self.subTest(replacement=replacement):
                queue = subscriptions.NativeRefresh(threading.RLock())
                release = threading.Event()
                outcomes = []
                fresh = None

                def adapter(secret):
                    self.assertTrue(release.wait(2))
                    return "rotated-" + secret

                def waiter():
                    try:
                        queue.wait("account", None, time.monotonic() + 2)
                        outcomes.append("done")
                    except ValueError as error:
                        outcomes.append(str(error))

                with patch.object(subscriptions, "refresh", side_effect=adapter):
                    queue.poll("account", "old-grant")
                    old = queue.requests["account"]
                    thread = threading.Thread(target=waiter)
                    thread.start()
                    try:
                        deadline = time.monotonic() + 1
                        while not old["waiters"] and time.monotonic() < deadline:
                            time.sleep(0.005)
                        self.assertEqual(old["waiters"], 1)
                        queue.invalidate("account")
                        thread.join(0.5)
                        self.assertEqual(outcomes, ["subscription_expired"])
                        self.assertEqual(queue.pending(), [])
                        if replacement is not None:
                            fresh = queue.poll("account", replacement)
                            self.assertNotEqual(fresh["generation"], old["generation"])
                        release.set()
                        deadline = time.monotonic() + 1
                        while not old["result"] and time.monotonic() < deadline:
                            time.sleep(0.005)
                        self.assertIsNotNone(old["result"])
                        queue.finish("account", old["generation"])
                        if fresh is not None:
                            self.assertEqual(queue.pending()[0]["generation"], fresh["generation"])
                            current = queue.requests["account"]
                            deadline = time.monotonic() + 1
                            while not current["result"] and time.monotonic() < deadline:
                                time.sleep(0.005)
                            self.assertEqual(current["result"]["secret"], f"rotated-{replacement}")
                            queue.finish("account", fresh["generation"])
                        else:
                            self.assertEqual(queue.pending(), [])
                    finally:
                        release.set()
                        thread.join(2)

    def test_changed_source_grant_cannot_return_previous_refresh(self):
        queue = subscriptions.NativeRefresh(threading.RLock())
        with patch.object(subscriptions, "refresh", side_effect=lambda secret: "rotated-" + secret):
            old = queue.poll("account", "old")
            deadline = time.monotonic() + 1
            while not queue.requests["account"]["result"] and time.monotonic() < deadline:
                time.sleep(0.005)
            fresh = queue.poll("account", "new")
            self.assertNotEqual(fresh["generation"], old["generation"])
            self.assertNotIn("rotated-old", str(fresh))
            deadline = time.monotonic() + 1
            while not queue.requests["account"]["result"] and time.monotonic() < deadline:
                time.sleep(0.005)
            self.assertEqual(queue.requests["account"]["result"]["secret"], "rotated-new")

    def test_slow_account_does_not_block_another_or_share_its_vault_failure(self):
        queue = subscriptions.NativeRefresh(threading.RLock())
        release = threading.Event()
        cancel = threading.Event()
        results, calls = {}, []

        def adapter(secret):
            calls.append(secret)
            if secret == "slow":
                self.assertTrue(release.wait(2))
            return json.dumps(CREDENTIALS)

        def waiter(account, stopped=None):
            try:
                queue.wait(account, stopped, time.monotonic() + 2)
                results[account] = "done"
            except ValueError as error:
                results[account] = str(error)

        with patch.object(subscriptions, "refresh", side_effect=adapter):
            threads = [
                threading.Thread(target=waiter, args=("slow", cancel)),
                threading.Thread(target=waiter, args=("fast",)),
            ]
            for thread in threads:
                thread.start()
            try:
                deadline = time.monotonic() + 1
                while len(queue.pending()) < 2 and time.monotonic() < deadline:
                    time.sleep(0.005)
                self.assertEqual(len(queue.pending()), 2)
                slow = queue.poll("slow", "slow")
                self.assertEqual(slow["status"], "refreshing")
                deadline = time.monotonic() + 1
                fast = queue.poll("fast", "fast")
                while fast["status"] == "refreshing" and time.monotonic() < deadline:
                    time.sleep(0.005)
                    fast = queue.poll("fast", "fast")
                self.assertEqual(fast["status"], "authenticated")
                self.assertTrue(threads[1].is_alive(), "Must await native vault commit")
                queue.finish("fast", fast["generation"])
                threads[1].join(0.5)
                self.assertEqual(results, {"fast": "done"})
                self.assertTrue(threads[0].is_alive())
                cancel.set()
                threads[0].join(0.5)
                self.assertEqual(results["slow"], "subscription_expired")
                self.assertEqual(
                    queue.pending(),
                    [{"connection": "slow", "generation": slow["generation"]}],
                )
                retry = threading.Thread(target=waiter, args=("slow",))
                threads.append(retry)
                retry.start()
                deadline = time.monotonic() + 1
                while (
                    queue.requests["slow"]["waiters"] != 1
                    and time.monotonic() < deadline
                ):
                    time.sleep(0.005)
                self.assertEqual(queue.requests["slow"]["waiters"], 1)
                release.set()
                deadline = time.monotonic() + 1
                while slow["status"] == "refreshing" and time.monotonic() < deadline:
                    time.sleep(0.005)
                    slow = queue.poll("slow", "slow")
                self.assertEqual(slow["status"], "authenticated")
                queue.finish("slow", slow["generation"], "vault_unavailable")
            finally:
                release.set()
                for thread in threads:
                    thread.join(2)
            self.assertEqual(results, {"fast": "done", "slow": "vault_unavailable"})
            self.assertEqual(sorted(calls), ["fast", "slow"])

    def test_refresh_coalesces_callers_and_fences_late_completion_after_cancellation(
        self,
    ):
        queue = subscriptions.NativeRefresh(threading.RLock())
        results = {}

        def start(name):
            cancel = threading.Event()

            def call():
                try:
                    queue.wait("connection", cancel, time.monotonic() + 2)
                    results[name] = "done"
                except ValueError as error:
                    results[name] = str(error)

            thread = threading.Thread(target=call)
            thread.start()
            return thread, cancel

        first, cancel = start("first")
        second, _ = start("second")
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            with queue.condition:
                if queue.requests.get("connection", {}).get("waiters") == 2:
                    break
            time.sleep(0.005)
        pending = queue.pending()
        self.assertEqual(len(pending), 1)
        cancel.set()
        first.join(0.5)
        self.assertFalse(first.is_alive())
        self.assertTrue(second.is_alive())
        generation = pending[0]["generation"]
        queue.finish("connection", generation)
        second.join(0.5)
        self.assertEqual(results, {"first": "subscription_expired", "second": "done"})
        third, cancelled = start("third")
        cancelled.set()
        third.join(0.5)
        self.assertEqual(queue.pending(), [])
        fourth, _ = start("fourth")
        deadline = time.monotonic() + 1
        while not queue.pending() and time.monotonic() < deadline:
            time.sleep(0.005)
        fresh = queue.pending()[0]["generation"]
        queue.finish("connection", generation)
        self.assertTrue(fourth.is_alive())
        queue.finish("connection", fresh)
        fourth.join(0.5)
        self.assertEqual(results["fourth"], "done")

    def test_accepts_actual_pinned_sdk_identity_shape_and_rejects_unknown_fields(self):
        # Shape returned by pi-ai exchangeCodeForToken/openAICodexProfileHook.
        value = {
            **CREDENTIALS,
            "accountId": "workspace-1",
            "orgId": "workspace-1",
            "email": "fixture@example.test",
            "orgName": "pro",
        }
        self.assertEqual(subscriptions.validate_credentials(value), value)
        for bad in [
            {**value, "destination": "https://attacker.test"},
            {**value, "email": "bad\nidentity"},
            {**value, "orgId": False},
        ]:
            with self.assertRaises(ValueError):
                subscriptions.validate_credentials(bad)

    def test_device_flow_keeps_credentials_out_of_status_until_native_vault_commit(
        self,
    ):
        process = Process(
            [
                {
                    "auth": {
                        "url": "https://auth.openai.com/codex/device",
                        "code": "ABCD-EFGH",
                    }
                },
                {"credentials": CREDENTIALS},
            ]
        )
        with tempfile.TemporaryDirectory() as folder, patch.object(
            subscriptions,
            "spawn_adapter",
            return_value=(tempfile.TemporaryDirectory(dir=folder), process),
        ):
            login = subscriptions.CodexLogin()
            login.start("connection")
            login.worker.join(2)
            status = login.snapshot()
            self.assertEqual(status["status"], "authenticated")
            self.assertNotIn("private-", json.dumps(status))
            self.assertEqual(json.loads(login.credentials("connection")), CREDENTIALS)
            self.assertIsNone(login.credentials("other-connection"))
            login.commit("connection")
            self.assertEqual(login.snapshot()["status"], "connected")
            self.assertIsNone(login.credentials("connection"))

    def test_rejects_untrusted_login_url_and_provider_owned_errors(self):
        for frame in [
            {"auth": {"url": "https://attacker.test", "code": "abc"}},
            {"error": "private-refresh"},
            {"credentials": {"access": "private-access"}},
        ]:
            process = Process([frame])
            with patch.object(
                subscriptions,
                "spawn_adapter",
                return_value=(tempfile.TemporaryDirectory(), process),
            ):
                login = subscriptions.CodexLogin()
                login.start("connection")
                login.worker.join(2)
                self.assertEqual(login.snapshot()["status"], "failed")
                self.assertIsNone(login.credentials("connection"))
                self.assertNotIn("private-", json.dumps(login.snapshot()))

    def test_cancel_discards_pending_credentials(self):
        login = subscriptions.CodexLogin()
        login.connection, login.value, login.status = (
            "connection",
            CREDENTIALS,
            "authenticated",
        )
        login.cancel()
        self.assertIsNone(login.credentials("connection"))
        self.assertEqual(login.snapshot()["status"], "cancelled")

    def test_refresh_uses_private_input_and_rejects_malformed_output(self):
        process = Process([{"credentials": CREDENTIALS}])
        with patch.object(
            subscriptions,
            "spawn_adapter",
            return_value=(tempfile.TemporaryDirectory(), process),
        ):
            self.assertEqual(
                json.loads(subscriptions.refresh(json.dumps(CREDENTIALS))), CREDENTIALS
            )
        for value in [
            None,
            {"access": "a", "refresh": "r", "expires": 0},
            {**CREDENTIALS, "access": "a\nb"},
        ]:
            with self.assertRaises(ValueError):
                subscriptions.validate_credentials(value)


class Routing(unittest.TestCase):
    def test_removing_connection_invalidates_its_refresh_waiter(self):
        from desktop_engine import Runtime, default_config
        from test_desktop import connection

        with tempfile.TemporaryDirectory() as folder:
            runtime = Runtime(Path(folder), "k" * 48)
            config = default_config()
            c = connection()
            c.update(url="https://chatgpt.com/backend-api/codex", transport="pi-ai", subscription="codex")
            config["connections"] = [c]
            runtime.save_config(config, runtime.revision)
            outcome = []

            def wait():
                try:
                    runtime.subscription_refresh.wait(c["id"], None, time.monotonic() + 2)
                except ValueError as error:
                    outcome.append(str(error))

            thread = threading.Thread(target=wait)
            thread.start()
            try:
                deadline = time.monotonic() + 1
                while not runtime.subscription_refresh.pending() and time.monotonic() < deadline:
                    time.sleep(0.005)
                self.assertTrue(runtime.subscription_refresh.pending())
                runtime.save_config(default_config(), runtime.revision)
                thread.join(0.5)
                self.assertFalse(thread.is_alive())
                self.assertEqual(outcome, ["subscription_expired"])
                self.assertEqual(runtime.subscription_refresh.pending(), [])
            finally:
                thread.join(2)

    def test_portal_host_requires_private_bearer_even_for_non_browser_clients(self):
        import desktop_portal

        scope = {"__name__": "offline_fixture"}
        exec(desktop_portal.PORTAL_HOST, scope)
        permit = scope["permit"]

        class Headers(dict):
            def getall(self, name, default):
                value = self.get(name)
                return (
                    default
                    if value is None
                    else (value if isinstance(value, list) else [value])
                )

        key = "fixture-" + "x" * 48
        self.assertFalse(permit(Headers(), key))
        self.assertFalse(permit(Headers(Authorization="Bearer wrong"), key))
        self.assertFalse(permit(Headers(Authorization=["Bearer " + key] * 2), key))
        self.assertFalse(
            permit(
                Headers(Authorization="Bearer " + key, Origin="http://evil.test"), key
            )
        )
        self.assertTrue(permit(Headers(Authorization="Bearer " + key), key))

    def test_portal_instructions_are_visible_but_foreign_urls_are_never_released(self):
        from desktop_portal import PortalConnector

        with tempfile.TemporaryDirectory() as folder:
            connector = PortalConnector(folder)
            connector.accept_frame(
                "login",
                {
                    "auth": {
                        "url": "https://portal.nousresearch.com/oauth/device?user_code=ABCD",
                        "code": "ABCD-EFGH",
                    }
                },
            )
            self.assertEqual(
                connector.snapshot("http://127.0.0.1:8645/v1")["auth"]["code"],
                "ABCD-EFGH",
            )
            for url in [
                "https://portal.nousresearch.com.attacker.test/device",
                "https://attacker.test",
                "http://portal.nousresearch.com/device",
            ]:
                with self.assertRaises(ValueError):
                    connector.accept_frame(
                        "login", {"auth": {"url": url, "code": "ABCD-EFGH"}}
                    )

    def test_expired_gateway_selection_waits_for_native_commit_without_a_webview(self):
        from desktop_engine import Runtime, default_config
        from test_desktop import connection

        with tempfile.TemporaryDirectory() as folder:
            runtime = Runtime(Path(folder), "k" * 48)
            config = default_config()
            c = connection()
            c.update(
                url="https://chatgpt.com/backend-api/codex",
                transport="pi-ai",
                subscription="codex",
            )
            config["connections"] = [c]
            runtime.save_config(config, 0)
            runtime.secrets[c["id"]] = json.dumps({**CREDENTIALS, "expires": 1})
            result = []

            def select():
                result.append(
                    runtime.select(
                        {
                            "model": f'direct/{c["id"]}/{c["models"][0]["id"]}',
                            "messages": [{"role": "user", "content": "fixture"}],
                        },
                        "chat",
                        None,
                        {},
                        threading.Event(),
                        time.monotonic() + 2,
                        refresh=True,
                    )
                )

            thread = threading.Thread(target=select)
            thread.start()
            deadline = time.monotonic() + 1
            pending = []
            while not pending and time.monotonic() < deadline:
                pending = runtime.subscription_refresh.pending()
                time.sleep(0.005)
            self.assertEqual(len(pending), 1)
            self.assertTrue(thread.is_alive())
            # Models a native vault commit followed by the existing private secrets sync.
            with runtime.lock:
                runtime.secrets[c["id"]] = json.dumps(
                    {**CREDENTIALS, "access": "fresh-access"}
                )
            runtime.subscription_refresh.finish(c["id"], pending[0]["generation"])
            thread.join(1)
            self.assertFalse(thread.is_alive())
            self.assertEqual(result[0][1]["_secret"], "fresh-access")
            self.assertEqual(runtime.subscription_refresh.pending(), [])

    def test_portal_shutdown_never_signals_an_exited_child_process_group(self):
        from desktop_portal import PortalConnector
        from unittest.mock import Mock

        with tempfile.TemporaryDirectory() as folder:
            portal = PortalConnector(folder)
            portal.children["login"] = Mock(pid=12345)
            portal.children["login"].poll.return_value = 0
            with patch("desktop_portal.os.killpg") as signal_group, patch(
                "desktop_portal.kill_worker"
            ) as kill:
                portal.shutdown()
            signal_group.assert_not_called()
            kill.assert_not_called()
            self.assertEqual(portal.children, {})

    def test_portal_connector_is_loopback_only_and_cannot_take_an_omr_key(self):
        from desktop_engine import Runtime, default_config, validate_config
        from test_desktop import connection

        config = default_config()
        c = connection()
        c.update(url="http://127.0.0.1:8645/v1", transport="http", subscription="nous")
        config["connections"] = [c]
        validate_config(config)
        for url in [
            "http://192.168.1.2:8645/v1",
            "https://attacker.test/v1",
            "http://127.0.0.1:80/v1",
        ]:
            bad = json.loads(json.dumps(config))
            bad["connections"][0]["url"] = url
            with self.assertRaises(ValueError):
                validate_config(bad)
        with tempfile.TemporaryDirectory() as folder:
            runtime = Runtime(Path(folder), "k" * 48)
            runtime.secrets[c["id"]] = "unrelated-key"
            with self.assertRaisesRegex(ValueError, "portal_unavailable"):
                runtime.connection_secret(c)

    def test_codex_grant_is_bound_to_exact_upstream_and_only_access_reaches_generation(
        self,
    ):
        from desktop_engine import Runtime, default_config, validate_config
        from test_desktop import connection

        config = default_config()
        c = connection()
        c.update(
            url="https://chatgpt.com/backend-api/codex",
            transport="pi-ai",
            subscription="codex",
        )
        config["connections"] = [c]
        validate_config(config)
        for key, value in [
            ("url", "https://attacker.test"),
            ("transport", "http"),
            ("subscription", "claude"),
        ]:
            bad = json.loads(json.dumps(config))
            bad["connections"][0][key] = value
            with self.assertRaises(ValueError):
                validate_config(bad)
        with tempfile.TemporaryDirectory() as folder:
            runtime = Runtime(Path(folder), "k" * 48)
            runtime.save_config(config, 0)
            runtime.secrets[c["id"]] = json.dumps(CREDENTIALS)
            direct = f'direct/{c["id"]}/{c["models"][0]["id"]}'
            _, route = runtime.select(
                {"model": direct, "messages": [{"role": "user", "content": "hello"}]},
                "chat",
                None,
                {},
                None,
                0,
            )
            self.assertEqual(route["subscription"], "codex")
            self.assertEqual(route["_secret"], "private-access")
            self.assertNotIn("private-", json.dumps(runtime.snapshot()))
            self.assertNotIn("private-", Path(folder, "config.json").read_text())
            runtime.secrets[c["id"]] = json.dumps({**CREDENTIALS, "expires": 1})
            with self.assertRaisesRegex(ValueError, "subscription_expired"):
                runtime.select(
                    {
                        "model": direct,
                        "messages": [{"role": "user", "content": "hello"}],
                    },
                    "chat",
                    None,
                    {},
                    None,
                    0,
                )


if __name__ == "__main__":
    unittest.main()
