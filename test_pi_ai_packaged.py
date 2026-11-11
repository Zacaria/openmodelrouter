"""Frozen engine must traverse pi-ai with no Node/Bun/Python on PATH."""

import http.client
import json
import os
import queue
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

import test_pi_ai


@unittest.skipUnless(
    os.environ.get("OMR_TEST_ENGINE"), "set OMR_TEST_ENGINE to the frozen engine"
)
class PackagedPiAiTest(unittest.TestCase):
    def test_embedded_adapter_stream_tools_errors_and_no_runtime_path(self):
        fixture = test_pi_ai.PiAiTest()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        with tempfile.TemporaryDirectory() as directory:
            env = {
                k: os.environ[k] for k in ("SystemRoot", "WINDIR") if k in os.environ
            }
            env.update(
                HOME=directory,
                USERPROFILE=directory,
                PATH="",
                TMPDIR=directory,
                TEMP=directory,
                TMP=directory,
            )
            binary = Path(os.environ["OMR_TEST_ENGINE"]).resolve()
            proc = subprocess.Popen(
                [str(binary), str(Path(directory) / "state")],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=directory,
                env=env,
            )
            assert (
                proc.stdin is not None
                and proc.stdout is not None
                and proc.stderr is not None
            )
            stdin, stdout, stderr = proc.stdin, proc.stdout, proc.stderr
            messages = queue.Queue()

            def read():
                for line in stdout:
                    messages.put(line)

            threading.Thread(target=read, daemon=True).start()

            def command(value):
                stdin.write(json.dumps(value) + "\n")
                stdin.flush()
                result = json.loads(messages.get(timeout=30))
                self.assertNotIn("error", result, result)
                return result["ok"]

            try:
                state = command({"command": "init", "key": "k" * 48})
                state = command(
                    {"command": "save_config", "config": fixture.config, "revision": 0}
                )
                command(
                    {
                        "command": "secrets",
                        "values": {fixture.conn["id"]: test_pi_ai.CANARY},
                    }
                )

                def request(_path="/v1/responses", **fields):
                    client = http.client.HTTPConnection(
                        "127.0.0.1", state["port"], timeout=30
                    )
                    data = {
                        "model": f"direct/{fixture.conn['id']}/{fixture.conn['models'][0]['id']}",
                        **(
                            {"input": "Synthetic packaged task"}
                            if _path == "/v1/responses"
                            else {
                                "messages": [
                                    {
                                        "role": "user",
                                        "content": "Synthetic packaged task",
                                    }
                                ]
                            }
                        ),
                        **fields,
                    }
                    client.request(
                        "POST",
                        _path,
                        json.dumps(data),
                        {
                            "Authorization": "Bearer " + "k" * 48,
                            "Content-Type": "application/json",
                        },
                    )
                    response = client.getresponse()
                    result = response.status, response.read()
                    client.close()
                    return result

                for streaming in (False, True):
                    status, raw = request(stream=streaming)
                    self.assertEqual(status, 200, raw)
                    self.assertIn(b"Synthetic reply", raw)
                    self.assertTrue(fixture.calls[-1][2]["stream"])
                fixture.behavior = "tool"
                status, raw = request(
                    stream=True,
                    tools=[
                        {
                            "type": "function",
                            "name": "lookup",
                            "parameters": {"type": "object", "properties": {}},
                        }
                    ],
                )
                self.assertEqual(status, 200, raw)
                self.assertIn(b"response.function_call_arguments.delta", raw)
                fixture.behavior = "error"
                status, raw = request()
                self.assertEqual(status, 502, raw)
                self.assertNotIn(test_pi_ai.CANARY.encode(), raw)
                end = time.monotonic() + 5
                while True:
                    snapshot = command({"command": "snapshot"})
                    if snapshot["active"] == 0 and len(snapshot["receipts"]) == 4:
                        break
                    if time.monotonic() >= end:
                        self.fail("packaged receipts did not finalize")
                    time.sleep(0.02)
                receipts = snapshot["receipts"]
                self.assertEqual(len(receipts), 4)
                self.assertTrue(all(row["transport"] == "pi-ai" for row in receipts))
                self.assertEqual(
                    [row["status"] for row in receipts],
                    ["completed"] * 3 + ["upstream_error"],
                )
                self.assertNotIn(test_pi_ai.CANARY, json.dumps(snapshot))
                self.assertEqual(len(fixture.calls), 4)

                # Reuse the real-gateway intent regressions against the frozen
                # engine, not the development bridge on the build host.
                def configure():
                    nonlocal state
                    end = time.monotonic() + 5
                    while command({"command": "snapshot"})["active"]:
                        if time.monotonic() >= end:
                            self.fail("packaged request did not finish")
                        time.sleep(0.01)
                    state = command(
                        {
                            "command": "save_config",
                            "config": fixture.config,
                            "revision": state["revision"],
                        }
                    )

                fixture.start = configure
                fixture.request = request
                fixture.behavior = "text"
                for name in (
                    "test_responses_allowed_tools_cannot_weaken_required_allowlist",
                    "test_anthropic_parallel_control_cannot_be_dropped",
                    "test_chat_explicit_strictness_cannot_be_rewritten",
                    "test_anthropic_does_not_request_cache_without_client_policy",
                    "test_explicit_cache_policy_is_refused_at_every_envelope",
                    "test_unqualified_content_tools_and_nested_controls_fail_before_network",
                    "test_qualified_text_function_choices_and_results_still_reach_provider",
                    "test_chat_stream_usage_is_returned_only_when_requested",
                ):
                    with self.subTest(contract=name):
                        getattr(fixture, name)()
                fixture.conn["models"][0]["protocols"] = ["responses"]
                configure()
                # An unfinished request body has no provider child yet. If a
                # bounded forced shutdown refuses it, authorization must recover.
                partial = http.client.HTTPConnection(
                    "127.0.0.1", state["port"], timeout=5
                )
                self.addCleanup(partial.close)
                partial.putrequest("POST", "/v1/responses")
                partial.putheader("Authorization", "Bearer " + "k" * 48)
                partial.putheader("Content-Type", "application/json")
                partial.putheader("Content-Length", "100000")
                partial.endheaders()
                partial.send(b"{")
                end = time.monotonic() + 2
                while (
                    command({"command": "snapshot"})["active"] == 0
                    and time.monotonic() < end
                ):
                    time.sleep(0.01)
                stdin.write(json.dumps({"command": "shutdown", "force": True}) + "\n")
                stdin.flush()
                self.assertEqual(
                    json.loads(messages.get(timeout=5)), {"error": "requests_active"}
                )
                probe = http.client.HTTPConnection(
                    "127.0.0.1", state["port"], timeout=5
                )
                probe.request(
                    "GET", "/v1/models", headers={"Authorization": "Bearer " + "k" * 48}
                )
                response = probe.getresponse()
                self.assertEqual(
                    response.status,
                    200,
                    "a refused shutdown must restore service authorization",
                )
                response.read()
                probe.close()
                partial.close()
                end = time.monotonic() + 2
                while (
                    command({"command": "snapshot"})["active"]
                    and time.monotonic() < end
                ):
                    time.sleep(0.01)
                fixture.behavior = "stall"
                fixture.arrived.clear()
                held = http.client.HTTPConnection("127.0.0.1", state["port"], timeout=5)
                self.addCleanup(held.close)
                held.request(
                    "POST",
                    "/v1/responses",
                    json.dumps(
                        {
                            "model": f"direct/{fixture.conn['id']}/{fixture.conn['models'][0]['id']}",
                            "input": "Synthetic forced stop",
                        }
                    ),
                    {
                        "Authorization": "Bearer " + "k" * 48,
                        "Content-Type": "application/json",
                    },
                )
                self.assertTrue(fixture.arrived.wait(3))
                stdin.write(json.dumps({"command": "shutdown", "force": False}) + "\n")
                stdin.flush()
                self.assertEqual(
                    json.loads(messages.get(timeout=5)), {"error": "requests_active"}
                )
                started = time.monotonic()
                command({"command": "shutdown", "force": True})
                self.assertLess(time.monotonic() - started, 3)
                held.close()
                proc.stdin.close()
                self.assertEqual(proc.wait(timeout=20), 0)
                self.assertEqual(stderr.read(), "")
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=10)
                for stream in (proc.stdin, proc.stdout, proc.stderr):
                    if not stream.closed:
                        stream.close()


if __name__ == "__main__":
    unittest.main()
