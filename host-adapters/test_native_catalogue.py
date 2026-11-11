"""Opt-in native registry checks: metadata only, no thread/turn or provider inference.

OMR_TEST_CODEX_BIN=/absolute/codex OMR_TEST_OMP_BIN=/absolute/omp python3 -B -m unittest discover -s host-adapters -p test_native_catalogue.py -v
Use a real OMP executable (or local Bun wrapper), not a command string.
"""

import importlib.util
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import tempfile
import time
import unittest
import uuid

spec = importlib.util.spec_from_file_location(
    "native_adapter", Path(__file__).with_name("launch.py")
)
assert spec and spec.loader
launch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launch)


class NativeCatalogueTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.models = [
            {"id": "omr/" + profile, "name": name}
            for profile, name in [
                ("economy", "Économie"),
                ("balanced", "Équilibré"),
                ("quality", "Qualité"),
            ]
        ] + [
            {
                "id": f"direct/{uuid.UUID(int=1)}/{uuid.UUID(int=i + 2)}",
                "name": f"Synthetic · model-{i:04}",
            }
            for i in range(601)
        ]
        self.expected = {row["id"] for row in self.models}
        # Supported native config directories provide isolation; HOME alone is not used.
        self.env = {
            key: os.environ[key]
            for key in ["PATH", "HOME", "TMPDIR", "LANG"]
            if key in os.environ
        }
        self.env.update(
            {
                "CODEX_HOME": str(self.root / "codex"),
                "PI_CODING_AGENT_DIR": str(self.root / "omp"),
                "NO_COLOR": "1",
                "TERM": "dumb",
            }
        )
        (self.root / "codex").mkdir()
        (self.root / "omp").mkdir()

    @unittest.skipUnless(
        os.environ.get("OMR_TEST_OMP_BIN"), "opt-in real native OMP registry"
    )
    def test_omp_native_listing_contains_every_route_and_three_modes(self):
        self.env["OMR_PROXY_KEY"] = "synthetic-only-proxy-key"
        config = launch.omp_catalogue(
            self.models, "http://127.0.0.1:1", 8192, 2048, authenticated=True
        )
        (self.root / "omp" / "models.yml").write_text(
            json.dumps(config), encoding="utf-8"
        )
        result = subprocess.run(
            [
                os.environ["OMR_TEST_OMP_BIN"],
                "models",
                "ls",
                "omr",
                "--json",
                "--no-extensions",
            ],
            cwd=self.root,
            env=self.env,
            text=True,
            capture_output=True,
            timeout=40,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("validation failed", result.stderr)
        rows = json.loads(result.stdout)["models"]
        self.assertEqual({row["id"] for row in rows}, self.expected)
        self.assertEqual(len(rows), 604)
        print(
            "OMP native models ls: 604 exact IDs, including 3 profiles and 601 direct routes"
        )

    @unittest.skipUnless(
        os.environ.get("OMR_TEST_CODEX_BIN"), "opt-in real native Codex model/list"
    )
    def test_codex_native_picker_catalogue_contains_every_route_with_pagination(self):
        catalog = self.root / "codex-models.json"
        catalog.write_text(
            json.dumps(launch.codex_catalogue(self.models, 8192)), encoding="utf-8"
        )
        process = subprocess.Popen(
            [
                os.environ["OMR_TEST_CODEX_BIN"],
                "app-server",
                "--strict-config",
                "-c",
                'model_provider="omr"',
                "-c",
                'model_providers.omr={name="OMR",base_url="http://127.0.0.1:1/v1",wire_api="responses",requires_openai_auth=false}',
                "-c",
                "model_catalog_json=" + json.dumps(str(catalog)),
            ],
            cwd=self.root,
            env=self.env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            start_new_session=True,
        )

        def close():
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate(timeout=5)

        self.addCleanup(close)
        assert process.stdin and process.stdout and process.stderr
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        self.addCleanup(selector.close)

        def send(payload):
            process.stdin.write(json.dumps(payload) + "\n")
            process.stdin.flush()

        def receive(identity):
            end = time.monotonic() + 15
            while time.monotonic() < end:
                if selector.select(max(0, end - time.monotonic())):
                    line = process.stdout.readline()
                    if not line:
                        self.fail("native Codex exited: " + process.stderr.read())
                    row = json.loads(line)
                    if row.get("id") == identity:
                        self.assertNotIn("error", row, str(row))
                        return row["result"]
            self.fail("native Codex model/list timed out (no inference attempted)")

        send(
            {
                "id": 1,
                "method": "initialize",
                "params": {
                    "clientInfo": {"name": "omr-catalogue-test", "version": "1"}
                },
            }
        )
        receive(1)
        send({"method": "initialized"})
        rows, cursor, identity = [], None, 2
        while True:
            send(
                {
                    "id": identity,
                    "method": "model/list",
                    "params": {"limit": 100, "cursor": cursor, "includeHidden": False},
                }
            )
            page = receive(identity)
            rows.extend(page["data"])
            cursor = page.get("nextCursor")
            if not cursor:
                break
            identity += 1
            self.assertLess(identity, 20)
        self.assertEqual({row["id"] for row in rows}, self.expected)
        self.assertEqual(len(rows), 604)
        print(
            "Codex native model/list: 604 exact visible IDs with pagination; no thread/turn"
        )


if __name__ == "__main__":
    unittest.main()
