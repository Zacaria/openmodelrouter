"""Launcher environment + local HTTP, with opt-in installed Hermes resolver."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer

import omr
from desktop_engine import Runtime, default_config
from test_desktop import connection


class HermesAuthTest(unittest.TestCase):
    def exercise(self, installed_resolver=False):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            runtime = Runtime(directory / "desktop", "synthetic-desktop-" + "x" * 48)
            config = default_config()
            config["connections"] = [connection("synthetic/model")]
            runtime.save_config(config, 0)
            gateway_config = {
                "routes": {
                    "unused": {
                        "url": "http://127.0.0.1:1/v1",
                        "model": "unused",
                        "protocol": "chat",
                    }
                },
                "default_route": "unused",
                "decision": {"type": "fixed"},
            }
            server = ThreadingHTTPServer(
                ("127.0.0.1", 0), omr.handler(gateway_config, desktop=runtime)
            )
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
            home = directory / "home"
            home.mkdir()
            sentinel = home / "config.yaml"
            sentinel.write_text("# synthetic existing profile; must stay unchanged\n")
            client = directory / "hermes"
            code = """import http.client, json, os, sys
from urllib.parse import urlsplit
base = sys.argv[sys.argv.index('--base-url') + 1]
assert 'OMR_DESKTOP_KEY' not in os.environ, 'Desktop credential leaked to client'
key = os.environ['OPENAI_API_KEY']
assert key == os.environ['OMR_PROXY_KEY']
"""
            if installed_resolver:
                source = os.environ["OMR_TEST_HERMES_SOURCE"]
                packages = os.environ["OMR_TEST_HERMES_SITE_PACKAGES"]
                code += f"sys.path[:0] = [{source!r}, {packages!r}]\n"
                code += """from unittest.mock import patch
from hermes_cli import runtime_provider as resolver
from hermes_cli import runtime_provider_custom as custom
with patch.object(resolver, '_get_model_config', return_value={}), \\
     patch.object(resolver, '_try_resolve_from_custom_pool', return_value=None), \\
     patch.object(resolver, '_get_named_custom_provider', return_value=None), \\
     patch.object(custom, '_owning_entry_credential', return_value=(False, '')):
    runtime = resolver._resolve_named_custom_runtime(requested_provider='custom', explicit_base_url=base)
    assert runtime['api_key'] == key, 'installed resolver did not select proxy credential'
    assert runtime['base_url'].rstrip('/') == base
    key = runtime['api_key']
"""
            code += """assert os.environ.get('OPENAI_BASE_URL') == base, 'credential/base URL not associated'
endpoint = urlsplit(base)
client = http.client.HTTPConnection(endpoint.hostname, endpoint.port, timeout=5)
client.request('GET', '/v1/models', headers={'Authorization': 'Bearer ' + key})
response = client.getresponse()
assert response.status == 200, 'proxy rejected resolved credential'
rows = json.loads(response.read())['data']
client.close()
assert [row['id'] for row in rows[:3]] == ['omr/economy', 'omr/balanced', 'omr/quality']
assert len(rows) == 4 and rows[-1]['id'].startswith('direct/')
print(json.dumps({'key_base_associated': True, 'proxy_status': response.status, 'routes': len(rows)}))
"""
            python = (
                os.environ["OMR_TEST_HERMES_PYTHON"]
                if installed_resolver
                else sys.executable
            )
            client.write_text(f"#!{python}\n" + code)
            client.chmod(0o700)
            env = {
                key: os.environ[key]
                for key in ("PATH", "TMPDIR", "LANG")
                if key in os.environ
            }
            env.update(
                {
                    "PATH": str(directory) + os.pathsep + env.get("PATH", ""),
                    "HOME": str(home),
                    "HERMES_HOME": str(home),
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "OMR_DESKTOP_KEY": runtime.key,
                    "OPENAI_API_KEY": "synthetic-unrelated-key",
                    "OPENAI_BASE_URL": "https://unrelated.invalid/v1",
                    "CUSTOM_BASE_URL": "https://unrelated.invalid/v1",
                }
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(Path(__file__).with_name("launch.py")),
                    "hermes",
                    "--desktop",
                    "--port",
                    str(server.server_port),
                    "--session",
                    "00000000-0000-4000-8000-000000000002",
                    "--project",
                    str(directory),
                    "--run-timeout",
                    "15",
                ],
                env=env,
                capture_output=True,
                text=True,
                timeout=25,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                json.loads(result.stdout),
                {
                    "key_base_associated": True,
                    "proxy_status": 200,
                    "routes": 4,
                },
            )
            self.assertEqual(
                sentinel.read_text(),
                "# synthetic existing profile; must stay unchanged\n",
            )
            # Hermes imports may initialize empty support directories in this isolated HOME.
            self.assertFalse((home / ".env").exists())
            self.assertFalse((home / "auth.json").exists())

    def test_launcher_binds_ephemeral_key_to_proxy_url(self):
        self.exercise()

    @unittest.skipUnless(
        all(
            os.environ.get(name)
            for name in (
                "OMR_TEST_HERMES_SOURCE",
                "OMR_TEST_HERMES_SITE_PACKAGES",
                "OMR_TEST_HERMES_PYTHON",
            )
        ),
        "opt-in installed Hermes custom-provider resolver (no profile/pool reads)",
    )
    def test_installed_hermes_resolver_authenticates_local_proxy(self):
        self.exercise(installed_resolver=True)


if __name__ == "__main__":
    unittest.main()
