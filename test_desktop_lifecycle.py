import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from test_desktop import connection
from desktop_engine import default_config


class DesktopLifecycleTest(unittest.TestCase):
    def test_hot_config_active_quit_cancel_and_disabled_route(self):
        arrived = threading.Event()
        aborted = threading.Event()

        class API(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                self.wfile.write(b'data: {"model":"synthetic-small","choices":[]}\n\n')
                self.wfile.flush()
                arrived.set()
                self.connection.settimeout(5)
                try:
                    if not self.connection.recv(1):
                        aborted.set()
                except OSError:
                    pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), API)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        with tempfile.TemporaryDirectory() as d:
            binary = os.environ.get("OMR_ENGINE_BIN")
            args = (
                [binary, d]
                if binary
                else [sys.executable, "-B", "desktop_sidecar.py", d]
            )
            process = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            def ipc(command):
                process.stdin.write(json.dumps(command) + "\n")
                process.stdin.flush()
                line = process.stdout.readline()
                if not line:
                    self.fail("sidecar closed unexpectedly: " + process.stderr.read())
                return json.loads(line)

            try:
                key = "synthetic-key-" * 5
                state = ipc({"command": "init", "key": key})["ok"]
                config = default_config()
                c = connection()
                c["url"] = f"http://127.0.0.1:{server.server_port}/v1"
                config["connections"] = [c]
                ipc({"command": "save_config", "config": config, "revision": 0})
                direct = f"direct/{c['id']}/{c['models'][0]['id']}"
                client = http.client.HTTPConnection(
                    "127.0.0.1", state["port"], timeout=5
                )
                payload = {
                    "model": direct,
                    "messages": [
                        {"role": "user", "content": "SYNTHETIC-PRIVATE-CANARY"}
                    ],
                    "stream": True,
                }
                client.request(
                    "POST",
                    "/v1/chat/completions",
                    json.dumps(payload),
                    {
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + key,
                    },
                )
                response = client.getresponse()
                self.assertEqual(response.status, 200)
                self.assertTrue(arrived.wait(3))
                self.assertEqual(
                    ipc({"command": "shutdown", "force": False})["error"],
                    "requests_active",
                )
                c["models"][0]["enabled"] = False
                update = ipc(
                    {"command": "save_config", "config": config, "revision": 1}
                )["ok"]
                self.assertEqual(update["port"], state["port"])
                self.assertEqual(update["active"], 1)
                client.close()
                response.close()
                self.assertTrue(aborted.wait(3), "cancellation did not close upstream")
                for _ in range(100):
                    snapshot = ipc({"command": "snapshot"})["ok"]
                    if snapshot["receipts"] and snapshot["active"] == 0:
                        break
                    time.sleep(0.02)
                self.assertEqual(snapshot["active"], 0)
                self.assertEqual(snapshot["receipts"][0]["status"], "cancelled")
                self.assertNotIn(
                    "SYNTHETIC-PRIVATE-CANARY", Path(d, "receipts.jsonl").read_text()
                )
                client = http.client.HTTPConnection(
                    "127.0.0.1", state["port"], timeout=3
                )
                client.request(
                    "POST",
                    "/v1/chat/completions",
                    json.dumps(payload),
                    {
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + key,
                    },
                )
                result = client.getresponse()
                self.assertEqual(result.status, 400)
                result.read()
                client.close()
                for _ in range(100):
                    snapshot = ipc({"command": "snapshot"})["ok"]
                    if snapshot["active"] == 0:
                        break
                    time.sleep(0.01)
                self.assertTrue(ipc({"command": "shutdown", "force": False})["ok"])
                process.wait(timeout=5)
                self.assertEqual(process.returncode, 0)
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
                process.stdin.close()
                process.stdout.close()
                process.stderr.close()
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
