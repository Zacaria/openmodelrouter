"""Exercise the build entry point through its dependency-install boundary."""

import importlib.util
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "desktop/scripts"


class StopBeforeBridge(Exception):
    pass


class MacOSBuildTest(unittest.TestCase):
    def run_until_bridge(self, target, wheelhouse):
        spec = importlib.util.spec_from_file_location(
            "pi_ai_distribution", SCRIPTS / "pi_ai_distribution.py"
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        calls = []

        def run(command, **kwargs):
            calls.append((command, kwargs))
            if command[1:2] == ["ci"]:
                raise StopBeforeBridge
            return subprocess.CompletedProcess(command, 0)

        with (
            patch.dict(
                sys.modules,
                {
                    "pi_ai_distribution": module,
                    "certifi": types.SimpleNamespace(),
                },
            ),
            patch.object(sys, "path", [str(SCRIPTS), *sys.path]),
            patch.dict(os.environ, wheelhouse, clear=True),
            patch.object(subprocess, "check_output", return_value=f"host: {target}\n"),
            patch.object(
                module.shutil, "which", side_effect=lambda name: f"/tools/{name}"
            ),
            patch.object(subprocess, "run", side_effect=run),
        ):
            with self.assertRaises(StopBeforeBridge):
                runpy.run_path(str(SCRIPTS / "build_sidecar.py"), run_name="__main__")
        return calls

    def test_macos_spec_keeps_only_pi_assets_out_of_binary_rewriting(self):
        runtime = ROOT / "desktop/provider-runtime"
        addon = runtime / "pi_natives.fixture.node"
        assets = [
            ("desktop/provider-runtime/omr-pi", str(runtime / "omr-pi"), "BINARY"),
            ("desktop/provider-runtime/" + addon.name, str(addon), "BINARY"),
        ]
        other = ("libpython.dylib", "/build/libpython.dylib", "BINARY")
        analysis = types.SimpleNamespace(
            binaries=[*assets, other], datas=[], pure=[], scripts=[]
        )
        collector = Mock()
        with (
            patch.object(
                Path,
                "write_text",
                side_effect=AssertionError(
                    "spec fixture must not write production build resources"
                ),
            ),
            patch.object(Path, "glob", return_value=[addon]),
            patch.dict(
                sys.modules,
                {
                    "certifi": types.SimpleNamespace(where=lambda: "/build/ca.pem"),
                    "sidecar_notices": types.SimpleNamespace(
                        collect_macos_libraries=collector
                    ),
                },
            ),
        ):
            runpy.run_path(
                str(SCRIPTS / "sidecar_macos.spec"),
                init_globals={
                    "SPECPATH": str(SCRIPTS),
                    "Analysis": lambda *args, **kwargs: analysis,
                    "PYZ": lambda *args: None,
                    "EXE": lambda *args, **kwargs: None,
                },
            )
        self.assertEqual(analysis.binaries, [other])
        self.assertEqual(
            [
                row
                for row in analysis.datas
                if row[0].startswith("desktop/provider-runtime/")
            ],
            [(name, source, "DATA") for name, source, _ in assets],
        )
        collector.assert_called_once_with(
            [*assets, other], ROOT / "desktop/.sidecar-build/licenses"
        )

    def test_bun_targets_match_the_pinned_native_archives(self):
        code = """
import { runtimeTarget } from './desktop/provider-runtime/build_target.mjs';
console.log(JSON.stringify([
  ['linux', 'x64'], ['linux', 'arm64'], ['darwin', 'arm64'],
  ['darwin', 'x64'], ['win32', 'x64'],
].map(([platform, arch]) => runtimeTarget(platform, arch) + '.zip')));
"""
        result = subprocess.run(
            ["node", "--input-type=module", "-e", code],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        targets = json.loads(result.stdout)
        lock = json.loads(
            (ROOT / "desktop/licenses/pi-ai-sources.lock.json").read_text()
        )
        self.assertEqual(
            set(targets), {value["file"] for value in lock["runtimes"].values()}
        )

    def test_macos_requires_an_explicit_offline_wheelhouse(self):
        with self.assertRaisesRegex(RuntimeError, "OMR_WORKER_WHEELS"):
            self.run_until_bridge("aarch64-apple-darwin", {})

    def test_macos_declares_the_native_onnx_minimum_os(self):
        config = ROOT / "desktop/src-tauri/tauri.macos.conf.json"
        self.assertTrue(config.is_file(), "macOS deployment minimum must be explicit")
        self.assertEqual(
            json.loads(config.read_text())["bundle"]["macOS"]["minimumSystemVersion"],
            "14.0",
        )

    def test_macos_installs_hash_locked_native_worker_before_freezing(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            calls = self.run_until_bridge(
                "aarch64-apple-darwin", {"OMR_WORKER_WHEELS": directory}
            )
        self.assertEqual(len(calls), 2)
        command, options = calls[0]
        self.assertEqual(
            command[:5], ["/tools/uv", "pip", "install", "--python", sys.executable]
        )
        for flag in ("--require-hashes", "--no-index", "--reinstall", "--only-binary"):
            self.assertIn(flag, command)
        self.assertIn(str(ROOT / "desktop/s1d1-requirements.lock"), command)
        self.assertTrue(options["check"])


if __name__ == "__main__":
    unittest.main()
