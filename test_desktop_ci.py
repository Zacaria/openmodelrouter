"""Offline CI contracts; fixtures are not native package qualification."""

import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("desktop_ci", ROOT / "ci/desktop.py")
assert SPEC is not None and SPEC.loader is not None
ci = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ci)


class ContractTests(unittest.TestCase):
    def test_app_contract_and_frontend_build_cannot_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            desktop = root / "desktop"
            (desktop / "scripts").mkdir(parents=True)
            (desktop / "src-tauri").mkdir()
            (desktop / "scripts/build_sidecar.py").write_text("# app-owned fixture\n")
            (desktop / "package-lock.json").write_text("{}")
            (desktop / "sidecar-requirements.txt").write_text("# fixture")
            (desktop / "src-tauri/Cargo.lock").write_text("# fixture")
            package = {
                "version": "0.1.0",
                "scripts": dict.fromkeys(
                    ["check", "test", "build", "format:check"], "fixture"
                ),
                "dependencies": {"react": "19.3.1"},
            }
            package["scripts"]["native:build"] = "tauri build"
            (desktop / "package.json").write_text(json.dumps(package))
            config = {
                "version": "0.1.0",
                "bundle": {"externalBin": ["binaries/omr-engine"]},
                "build": {
                    "beforeBuildCommand": "npm run build",
                    "frontendDist": "../dist",
                },
            }
            config_path = desktop / "src-tauri/tauri.conf.json"
            config_path.write_text(json.dumps(config))
            (desktop / "src-tauri/Cargo.toml").write_text(
                '[package]\nversion = "0.1.0"\n'
            )
            target = "x86_64-unknown-linux-gnu"
            with (
                patch.object(ci.platform, "system", return_value="Linux"),
                patch.object(ci.platform, "machine", return_value="x86_64"),
                patch.object(
                    ci.subprocess, "check_output", return_value=f"host: {target}\n"
                ),
                patch.object(ci.subprocess, "run"),
            ):
                self.assertEqual(ci.contract(target, root), "0.1.0")
                config["build"]["beforeBuildCommand"] = "echo skipped"
                config_path.write_text(json.dumps(config))
                with self.assertRaisesRegex(ValueError, "frontend build"):
                    ci.contract(target, root)


class ExecutableTests(unittest.TestCase):
    def test_pi_ai_runtime_license_is_a_required_packaged_resource(self):
        self.assertIn("Bun-LICENSE.md", ci.LICENSES)

    def test_native_architecture_headers(self):
        samples = {
            "aarch64-apple-darwin": struct.pack("<II", 0xFEEDFACF, 0x0100000C),
            "x86_64-apple-darwin": struct.pack("<II", 0xFEEDFACF, 0x01000007),
            "x86_64-unknown-linux-gnu": b"\x7fELF\x02\x01"
            + bytes(12)
            + struct.pack("<H", 62),
            "x86_64-pc-windows-msvc": b"MZ"
            + bytes(58)
            + struct.pack("<I", 64)
            + b"PE\0\0"
            + struct.pack("<H", 0x8664),
        }
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "binary"
            for target, data in samples.items():
                binary.write_bytes(data)
                ci.check_binary(binary, target)
                wrong = next(t for t in samples if t != target)
                with self.assertRaises(ValueError):
                    ci.check_binary(binary, wrong)
            binary.write_bytes(b"#!/usr/bin/python3\n")
            with self.assertRaises(ValueError):
                ci.check_binary(binary, "x86_64-unknown-linux-gnu")

    def test_ipc_smoke_rejects_failed_missing_or_secret_output(self):
        good = {"config": {"connections": []}, "port": 12345}
        reply = "\n".join(
            json.dumps(x) for x in [{"ok": good}, {"ok": good}, {"ok": True}]
        )
        ci.check_replies(reply, "synthetic-key")
        for invalid in [
            "",
            "{}",
            reply.replace("true", "false"),
            reply + "\n{}",
            reply + "synthetic-key",
        ]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                ci.check_replies(invalid, "synthetic-key")

    def test_smoke_uses_private_state_no_python_or_path_and_timeout(self):
        good = {"config": {"connections": []}, "port": 12345}
        reply = "\n".join(
            json.dumps(x) for x in [{"ok": good}, {"ok": good}, {"ok": True}]
        )
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "binary"
            binary.write_bytes(b"not-executed")
            with (
                patch.object(ci, "check_binary"),
                patch.object(ci.subprocess, "run") as run,
            ):
                run.return_value.stdout = reply
                ci.smoke(binary, "x86_64-unknown-linux-gnu")
                args, kwargs = run.call_args
                self.assertEqual(kwargs["env"]["PATH"], "")
                self.assertFalse(any(k.startswith("PYTHON") for k in kwargs["env"]))
                self.assertEqual(kwargs["timeout"], 60)
                commands = [json.loads(x) for x in kwargs["input"].splitlines()]
                self.assertEqual(
                    [x["command"] for x in commands], ["init", "snapshot", "shutdown"]
                )
                self.assertFalse(commands[-1].get("force", False))
                self.assertNotEqual(args[0][-1], str(Path.home()))
                self.assertFalse(Path(args[0][-1]).exists())


class PackageTests(unittest.TestCase):
    def test_generated_and_runtime_pyinstaller_notices_do_not_hide_invalid_copies(self):
        spec = importlib.util.spec_from_file_location(
            "sidecar_notices", ROOT / "desktop/scripts/sidecar_notices.py"
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tree = root / "app"
            runtime = tree / "licenses/runtime"
            dependencies = tree / "licenses/dependencies"
            runtime.mkdir(parents=True)
            dependencies.mkdir()
            source = root / "installed-copying.txt"
            source.write_bytes(b"installed notice bytes")
            module.stage_pyinstaller_notice(source, dependencies)
            runtime_notice = runtime / "PyInstaller-COPYING.txt"
            runtime_notice.write_bytes(b"different runtime notice bytes")
            for name in ci.LICENSES:
                if name != runtime_notice.name:
                    (tree / name).write_bytes(b"license")
            (tree / "omr-desktop").write_bytes(b"app")
            (tree / "omr-engine").write_bytes(b"engine")
            with (
                patch.object(ci, "check_binary"),
                patch.object(ci, "smoke", return_value={"ipc": "pass"}) as smoke,
                patch.object(ci.subprocess, "run"),
            ):
                result = ci.verify_tree(tree, root / "original", "aarch64-apple-darwin")
                self.assertEqual(
                    result["licenses"][runtime_notice.name],
                    hashlib.sha256(runtime_notice.read_bytes()).hexdigest(),
                )
                self.assertEqual(
                    (dependencies / "PyInstaller-BUILD-COPYING.txt").read_bytes(),
                    source.read_bytes(),
                )
                smoke.reset_mock()
                duplicate = dependencies / runtime_notice.name
                duplicate.write_bytes(b"extra notice")
                with self.assertRaisesRegex(ValueError, "invalid packaged license: PyInstaller"):
                    ci.verify_tree(tree, root / "original", "aarch64-apple-darwin")
                duplicate.unlink()
                runtime_notice.unlink()
                for invalid in ("missing", "empty", "symlink"):
                    if invalid == "empty":
                        runtime_notice.write_bytes(b"")
                    elif invalid == "symlink":
                        runtime_notice.symlink_to(source)
                    with (
                        self.subTest(invalid=invalid),
                        self.assertRaisesRegex(ValueError, "invalid packaged license: PyInstaller"),
                    ):
                        ci.verify_tree(tree, root / "original", "aarch64-apple-darwin")
                    runtime_notice.unlink(missing_ok=True)
                smoke.assert_not_called()

    def test_macos_package_rejects_invalid_bundle_before_smoke(self):
        def execute(args, **kwargs):
            if args[:2] == ["hdiutil", "attach"]:
                (Path(args[args.index("-mountpoint") + 1]) / "OMR Desktop.app").mkdir()
            if args[0] == "codesign":
                raise ci.subprocess.CalledProcessError(1, args)

        with (
            patch.object(ci.subprocess, "run", side_effect=execute) as run,
            patch.object(ci, "verify_tree") as verify,
        ):
            with self.assertRaises(ci.subprocess.CalledProcessError):
                ci.verify_package(Path("fixture.dmg"), Path("engine"), "aarch64-apple-darwin")
            verify.assert_not_called()
            self.assertTrue(any(c.args[0][:4] == ["codesign", "--verify", "--deep", "--strict"] for c in run.call_args_list))

    def test_macos_embedded_sidecar_strict_signature_is_required(self):
        with tempfile.TemporaryDirectory() as directory:
            tree = Path(directory)
            (tree / "omr-engine").write_bytes(b"engine")
            (tree / "omr-desktop").write_bytes(b"app")
            for name in ci.LICENSES:
                (tree / name).write_text("license")
            with (
                patch.object(ci, "check_binary"),
                patch.object(ci, "smoke") as smoke,
                patch.object(ci.subprocess, "run", side_effect=ci.subprocess.CalledProcessError(1, "codesign")) as run,
            ):
                with self.assertRaises(ci.subprocess.CalledProcessError):
                    ci.verify_tree(tree, tree / "omr-engine", "aarch64-apple-darwin")
                self.assertEqual(run.call_args.args[0][:3], ["codesign", "--verify", "--strict"])
                smoke.assert_not_called()

    def test_appimage_extraction_selects_relocated_identity_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "fixture.AppImage"
            package.write_bytes(b"fixture")
            with (
                patch.object(ci.subprocess, "run"),
                patch.object(ci, "verify_tree", return_value={"ipc": "pass"}) as verify,
            ):
                ci.verify_package(package, Path("original"), "x86_64-unknown-linux-gnu")
                self.assertEqual(
                    verify.call_args.kwargs, {"package_format": "AppImage"}
                )

    def test_relocation_rejects_unpinned_tool_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            tool = Path(directory) / "untrusted-tool"
            tool.write_bytes(b"not the pinned linuxdeploy")
            with patch.object(ci.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "untrusted linuxdeploy"):
                    ci.relocated_sidecar_sha256(Path("original"), tool)
                run.assert_not_called()

    def test_windows_sidecar_still_requires_identical_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            tree = Path(directory) / "package"
            tree.mkdir()
            original = Path(directory) / "original.exe"
            original.write_bytes(b"original")
            (tree / "omr-engine.exe").write_bytes(b"substituted")
            (tree / "omr-desktop.exe").write_bytes(b"native header tested separately")
            for name in ci.LICENSES:
                (tree / name).write_text("license")
            with patch.object(ci, "check_binary"), patch.object(ci, "smoke") as smoke:
                with self.assertRaisesRegex(ValueError, "differs from built"):
                    ci.verify_tree(tree, original, "x86_64-pc-windows-msvc")
                smoke.assert_not_called()

    def test_windows_install_refuses_non_disposable_hosts(self):
        with (
            patch.dict(ci.os.environ, {}, clear=True),
            patch.object(ci.subprocess, "run") as run,
        ):
            with self.assertRaisesRegex(ValueError, "GitHub-hosted"):
                ci.verify_package(
                    Path("fixture.exe"), Path("engine.exe"), "x86_64-pc-windows-msvc"
                )
            run.assert_not_called()

    def test_package_tree_requires_notices(self):
        with tempfile.TemporaryDirectory() as directory:
            tree = Path(directory)
            (tree / "omr-engine").write_bytes(b"engine")
            (tree / "omr-desktop").write_bytes(
                b"\x7fELF\x02\x01" + bytes(12) + struct.pack("<H", 62)
            )
            with patch.object(ci, "smoke", return_value={"ipc": "pass"}):
                with self.assertRaisesRegex(ValueError, "license"):
                    ci.verify_tree(
                        tree, tree / "omr-engine", "x86_64-unknown-linux-gnu"
                    )

    def test_package_tree_requires_native_app_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            tree = Path(directory)
            (tree / "omr-engine").write_bytes(b"engine")
            with patch.object(ci, "smoke", return_value={"ipc": "pass"}):
                with self.assertRaisesRegex(ValueError, "application executable"):
                    ci.verify_tree(
                        tree, tree / "omr-engine", "x86_64-unknown-linux-gnu"
                    )

    def test_bundle_selection_requires_exactly_one_of_every_format(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for suffix, subdir in [("deb", "deb"), ("AppImage", "appimage")]:
                (base / subdir).mkdir()
                (base / subdir / f"OMR_0.1.0.{suffix}").write_bytes(b"fixture")
            self.assertEqual(len(ci.find_bundles(base, "x86_64-unknown-linux-gnu")), 2)
            (base / "deb" / "duplicate.deb").write_bytes(b"fixture")
            with self.assertRaises(ValueError):
                ci.find_bundles(base, "x86_64-unknown-linux-gnu")
            (base / "deb" / "duplicate.deb").unlink()
            (base / "appimage" / "OMR_0.1.0.AppImage").unlink()
            with self.assertRaises(ValueError):
                ci.find_bundles(base, "x86_64-unknown-linux-gnu")

    def test_package_sidecar_missing_duplicate_symlink_or_wrong_bytes_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = root / "expected"
            expected.write_bytes(b"frozen-engine")
            package = root / "package"
            package.mkdir()
            for name in ci.LICENSES:
                (package / name).write_text("fixture license")
            (package / "omr-desktop").write_bytes(
                b"\x7fELF\x02\x01" + bytes(12) + struct.pack("<H", 62)
            )
            with self.assertRaises(ValueError):
                ci.verify_tree(package, expected, "x86_64-unknown-linux-gnu")
            sidecar = package / "omr-engine"
            sidecar.write_bytes(b"frozen-engine")
            with patch.object(ci, "smoke", return_value={"ipc": "pass"}):
                result = ci.verify_tree(package, expected, "x86_64-unknown-linux-gnu")
                self.assertEqual(
                    result["sha256"], hashlib.sha256(b"frozen-engine").hexdigest()
                )
                sidecar.write_bytes(b"changed")
                with self.assertRaises(ValueError):
                    ci.verify_tree(package, expected, "x86_64-unknown-linux-gnu")
                sidecar.unlink()
                sidecar.symlink_to(expected)
                with self.assertRaises(ValueError):
                    ci.verify_tree(package, expected, "x86_64-unknown-linux-gnu")
                sidecar.unlink()
                sidecar.write_bytes(b"frozen-engine")
                (package / "duplicate").mkdir()
                (package / "duplicate" / "omr-engine").write_bytes(b"frozen-engine")
                with self.assertRaises(ValueError):
                    ci.verify_tree(package, expected, "x86_64-unknown-linux-gnu")

    def test_download_checks_hashes_source_target_and_complete_matrix(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for target in ci.TARGETS:
                dest = root / target
                dest.mkdir()
                packages = []
                for extension in ci.TARGETS[target]["extensions"]:
                    name = f"OMR-Desktop-0.1.0-{target}.{extension}"
                    (dest / name).write_bytes(b"fixture")
                    packages.append(
                        {
                            "name": name,
                            "sha256": hashlib.sha256(b"fixture").hexdigest(),
                            "size": 7,
                            "embedded_sidecar": {"ipc": "pass"},
                        }
                    )
                (dest / "verification.json").write_text(
                    json.dumps(
                        {
                            "schema": 1,
                            "source_sha": "a" * 40,
                            "target": target,
                            "version": "0.1.0",
                            "packages": packages,
                            "signing": "unqualified",
                            "notarisation": "unqualified",
                        }
                    )
                )
                (dest / "SHA256SUMS").write_text(
                    "".join(f"{p['sha256']}  {p['name']}\n" for p in packages)
                )
            self.assertEqual(len(ci.verify_download(root, "a" * 40)), 4)
            with self.assertRaises(ValueError):
                ci.verify_download(root, "b" * 40)
            package = next(root.rglob("*.deb"))
            package.write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                ci.verify_download(root, "a" * 40)
            package.write_bytes(b"fixture")
            manifest = package.parent / "verification.json"
            data = json.loads(manifest.read_text())
            data["source_sha"] = "b" * 40
            manifest.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                ci.verify_download(root, "a" * 40)
            manifest.unlink()
            with self.assertRaises(ValueError):
                ci.verify_download(root, "a" * 40)


class WorkflowTests(unittest.TestCase):
    def test_macos_build_explicitly_signs_adhoc(self):
        workflow = (ROOT / ".github/workflows/desktop-build.yml").read_text()
        self.assertIn("APPLE_SIGNING_IDENTITY: ${{ runner.os == 'macOS' && '-' || '' }}", workflow)
        self.assertIn('{"bundle":{"macOS":{"hardenedRuntime":false}}}', workflow)

    def test_manual_readonly_pinned_build_only_and_offline_unchanged(self):
        workflow = (ROOT / ".github/workflows/desktop-build.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        for forbidden in [
            "pull_request_target",
            "secrets.",
            "contents: write",
            "action-gh-release",
            "git push",
            "universal-apple-darwin",
        ]:
            self.assertNotIn(forbidden, workflow)
        import re

        actions = re.findall(r"uses:\s*([^\s]+)", workflow)
        self.assertTrue(actions)
        self.assertTrue(all(re.fullmatch(r"[^@]+@[0-9a-f]{40}", x) for x in actions))
        for target in ci.TARGETS:
            self.assertIn(target, workflow)
        for required in [
            "persist-credentials: false",
            "npm ci",
            "cargo test",
            "--locked",
            "--require-hashes",
            "CARGO_NET_OFFLINE",
            "if-no-files-found: error",
            "fail-fast: false",
        ]:
            self.assertIn(required, workflow)
        offline = (ROOT / ".github/workflows/tests.yml").read_text(encoding="utf-8")
        prerequisite = """      - name: Setup Node for the pinned provider adapter
        uses: actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020 # v4
        with:
          node-version: '24.21.0'
      - name: Build pi-ai transport (synthetic tests; no credentials)
        run: |
          python -m pip install --require-hashes --only-binary=:all: -r desktop/sidecar-requirements.txt
          npm ci --prefix desktop/provider-runtime --no-audit --no-fund
          npm run check --prefix desktop/provider-runtime
          npm run build --prefix desktop/provider-runtime
"""
        self.assertEqual(offline.count(prerequisite), 1)
        whitespace = """      - name: Check whitespace
        run: |
          if git rev-parse --verify HEAD^ >/dev/null 2>&1; then
            git diff --check HEAD^
          else
            git diff-tree --root --check HEAD
          fi
"""
        self.assertEqual(offline.count(whitespace), 1)
        # Preserve the original workflow outside the explicitly changed step.
        original_whitespace = "      - name: Check whitespace\n        run: git diff --check HEAD^\n"
        normalized = offline.replace(prerequisite, "").replace(whitespace, original_whitespace)
        self.assertEqual(
            hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
            "a4c9655009df111d6cfacaa2b59664b101545bd5965753e52791ce02179176c6",
        )


if __name__ == "__main__":
    unittest.main()
