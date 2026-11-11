"""Behavioral notice closure and release identity regressions."""

import importlib.util
import json
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "desktop/scripts/sidecar_notices.py"


class NoticesTest(unittest.TestCase):
    def module(self):
        self.assertTrue(SCRIPT.is_file(), "sidecar notice collector is required")
        spec = importlib.util.spec_from_file_location("sidecar_notices", SCRIPT)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_pyinstaller_build_notice_keeps_bytes_and_removes_only_stale_name(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "COPYING.txt"
            source.write_bytes(b"installed PyInstaller notice\r\n")
            destination = root / "licenses"
            destination.mkdir()
            legacy = destination / "PyInstaller-COPYING.txt"
            legacy.write_bytes(b"stale build notice")
            other = destination / "other.txt"
            other.write_bytes(b"keep")
            module.stage_pyinstaller_notice(source, destination)
            self.assertFalse(legacy.exists())
            expected = destination / "PyInstaller-BUILD-COPYING.txt"
            self.assertEqual(expected.read_bytes(), source.read_bytes())
            self.assertEqual(other.read_bytes(), b"keep")
            module.stage_pyinstaller_notice(source, destination)
            self.assertEqual(expected.read_bytes(), source.read_bytes())
            legacy.write_bytes(b"retain if copying fails")
            with self.assertRaises(FileNotFoundError):
                module.stage_pyinstaller_notice(root / "missing", destination)
            self.assertEqual(legacy.read_bytes(), b"retain if copying fails")

    def test_package_notices_are_preserved_whole_and_inventoried(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {
                "onnxruntime/LICENSE": b"full MIT grant\n",
                "onnxruntime/ThirdPartyNotices.txt": b"complete third-party terms\n"
                * 100,
                "onnxruntime-1.31.1.dist-info/licenses/NOTICE": b"another notice\n",
            }
            for name, raw in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)

            class Distribution:
                version = "1.31.1"

                def __init__(self):
                    self.files = list(map(Path, files))

                def locate_file(self, name):
                    return root / name

            with patch.object(
                module.metadata, "distribution", return_value=Distribution()
            ):
                rows = module.collect_packages(
                    root / "out", {"onnxruntime": "1.31.1"}, {}
                )
            self.assertEqual(len(rows), len(files))
            for row in rows:
                self.assertEqual(
                    (root / "out" / row["file"]).read_bytes(), files[row["source"]]
                )
                self.assertEqual(row["version"], "1.31.1")
                self.assertEqual(row["bytes"], len(files[row["source"]]))

    def test_missing_or_wrong_version_notices_fail_closed(self):
        module = self.module()

        class Distribution:
            version = "0.23.3"
            files = []

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(module.metadata, "distribution", return_value=Distribution()),
        ):
            with self.assertRaisesRegex(ValueError, "missing.*tokenizers"):
                module.collect_packages(Path(directory), {"tokenizers": "0.23.3"}, {})
            with self.assertRaisesRegex(ValueError, "version"):
                module.collect_packages(Path(directory), {"tokenizers": "0.23.4"}, {})

    def test_notice_matching_does_not_confuse_source_code_with_license(self):
        module = self.module()
        for name in (
            "onnxruntime/ThirdPartyNotices.txt",
            "foo.dist-info/licenses/LICENSE.MIT",
            "COPYRIGHT.txt",
        ):
            self.assertTrue(module.is_notice(name), name)
        for name in ("license.py", "notice.c", "license.pyc", "LICENSES.py"):
            self.assertFalse(module.is_notice(name), name)

    def test_macos_copied_library_notices_bind_actual_inputs(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            formula = root / "Cellar/openssl@3/3.5.0"
            (formula / "lib").mkdir(parents=True)
            library = formula / "lib/libcrypto.3.dylib"
            library.write_bytes(b"native library bytes")
            (formula / "LICENSE.txt").write_bytes(b"complete Apache license")
            (formula / "AUTHORS.md").write_bytes(b"actual attribution")
            rows = module.collect_macos_libraries(
                [("libcrypto.3.dylib", str(library), "BINARY")], root / "out"
            )
            self.assertEqual(rows[0]["version"], "3.5.0")
            self.assertEqual(len(rows[0]["notices"]), 2)
            self.assertEqual(
                (root / "out" / rows[0]["notices"][0]["file"]).read_bytes(),
                b"complete Apache license",
            )
            with self.assertRaisesRegex(ValueError, "unreviewed"):
                module.collect_macos_libraries(
                    [
                        (
                            "other.dylib",
                            str(root / "Cellar/unknown/1/lib/other.dylib"),
                            "BINARY",
                        )
                    ],
                    root / "out",
                )

    def test_rust_inventory_rejects_uncovered_resolved_component(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = {
                "id": "crate-id",
                "source": "registry+crates.io",
                "name": "new-crate",
                "version": "1.0.0",
                "manifest_path": str(root / "Cargo.toml"),
                "license": "MIT",
            }
            graph = {"resolve": {"nodes": [{"id": "crate-id"}]}, "packages": [package]}
            with patch("subprocess.check_output", return_value=json.dumps(graph)):
                with self.assertRaisesRegex(ValueError, "missing Rust notice"):
                    module.collect_macos_rust(root / "out", "x86_64-apple-darwin")
                command = __import__("subprocess").check_output.call_args.args[0]
                self.assertEqual(command[-1], "x86_64-apple-darwin")

    def test_supplement_bytes_and_version_are_required(self):
        module = self.module()

        class Distribution:
            version = "0.23.3"
            files = []

        config = json.loads(
            (ROOT / "desktop/licenses/sidecar-notices.lock.json").read_text()
        )
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(module.metadata, "distribution", return_value=Distribution()),
        ):
            rows = module.collect_packages(
                Path(directory), {"tokenizers": "0.23.3"}, config
            )
            self.assertEqual(rows[0]["sha256"], config["tokenizers"]["sha256"])
            config["tokenizers"]["sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "integrity"):
                module.collect_packages(
                    Path(directory), {"tokenizers": "0.23.3"}, config
                )

    def test_product_sources_identify_new_version(self):
        desktop = ROOT / "desktop"
        for path in ("package.json", "src-tauri/tauri.conf.json"):
            self.assertEqual(
                json.loads((desktop / path).read_text())["version"], "0.3.2", path
            )
        lock = json.loads((desktop / "package-lock.json").read_text())
        self.assertEqual(lock["version"], "0.3.2")
        self.assertEqual(lock["packages"][""]["version"], "0.3.2")
        self.assertEqual(
            tomllib.loads((desktop / "src-tauri/Cargo.toml").read_text())["package"][
                "version"
            ],
            "0.3.2",
        )
        cargo = tomllib.loads((desktop / "src-tauri/Cargo.lock").read_text())
        self.assertEqual(
            next(p for p in cargo["package"] if p["name"] == "omr-desktop")["version"],
            "0.3.2",
        )


if __name__ == "__main__":
    unittest.main()
