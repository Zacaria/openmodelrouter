"""Exercise the installed Hermes proxy and OMR bearer guard, using no account or provider.

Runs the real native bootstrap and aiohttp listener with an injected fixture adapter.
No OAuth, credential files, generation, or public listener is involved.
"""

import argparse
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from desktop_portal import host_command

FIXTURE = r"""
from aiohttp.test_utils import TestClient, TestServer
from hermes_cli.auth_nous import _nous_shared_auth_dir
from pathlib import Path
assert _nous_shared_auth_dir() == Path(os.environ["HERMES_SHARED_AUTH_DIR"])

class FixtureAdapter:
    display_name = "offline fixture"
    allowed_paths = frozenset({"/chat/completions", "/models"})
    upstream_calls = 0
    health_checks = 0
    def is_authenticated(self):
        self.health_checks += 1
        return True
    def get_credential(self):
        self.upstream_calls += 1
        raise AssertionError("No upstream may be touched in this test")

async def check():
    adapter = FixtureAdapter()
    key = "offline-fixture-" + "x" * 48
    app = create_guarded_app(adapter, key)
    async with TestClient(TestServer(app)) as client:
        for headers in [[], [("Authorization", "Bearer wrong")],
            [("Authorization", "Bearer " + key)] * 2,
            [("Authorization", "Bearer " + key), ("Origin", "https://attacker.test")]]:
            response = await client.post("/v1/chat/completions", headers=headers, json={"model": "fixture"})
            assert response.status == 401, response.status
            await response.read()
        response = await client.get("/health", headers={"Authorization": "Bearer " + key})
        assert response.status == 200, response.status
        await response.read()
    assert adapter.upstream_calls == 0
    assert adapter.health_checks == 1
    assert adapter.get_retry_credential(failed_credential=None, status_code=429) is None
    print(json.dumps({"passed": True, "unauthorized_rejections": 4, "health_checks": 1,
        "upstream_calls": 0, "shared_auth_isolated": True, "inference_retry_disabled": True}))
asyncio.run(check())
"""


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--hermes", default=shutil.which("hermes"))
    args = parser.parse_args()
    if not args.hermes:
        raise RuntimeError("The installed Hermes connector is required for this test")
    with tempfile.TemporaryDirectory(prefix="omr-portal-offline-") as folder:
        env = {
            "HOME": str(Path.home()),
            "HERMES_HOME": folder,
            "HERMES_SHARED_AUTH_DIR": str(Path(folder) / "shared-auth"),
            "HERMES_PROFILE": "default",
            "PATH": os.defpath,
        }
        command = host_command(args.hermes, env)
        tree = ast.parse(command[3])
        assert isinstance(tree.body[-1], ast.If)
        # Replace only the live login/start entry point with the offline fixture.
        tree.body[-1:] = ast.parse(FIXTURE).body
        command[3] = ast.unparse(tree)
        result = subprocess.run(
            command,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode:
            raise RuntimeError(result.stderr[-2000:])
        report = json.loads(result.stdout.strip())
        assert report["passed"] and report["upstream_calls"] == 0
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
