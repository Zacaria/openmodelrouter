"""Offline integrity tests for pi-ai distribution materials."""

import hashlib
import io
import json
import tarfile
import importlib.util
import os
import subprocess
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "desktop/scripts/pi_ai_distribution.py"


def load_module():
    spec = importlib.util.spec_from_file_location("pi_ai_distribution", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DistributionTest(unittest.TestCase):
    def test_numpy_symlink_requires_exact_wheel_target_and_bytes(self):
        import zipfile

        dist = load_module()
        name = "libgfortran-test.so.5"
        target = "numpy.libs/" + name

        class Archive:
            def __init__(self):
                self.toc = {name: (0, 0, 0, 0, "n"), target: (0, 0, 0, 0, "b")}
                self.data = {name: (target + "\0").encode(), target: b"wheel ELF"}

            def extract(self, key):
                return self.data[key]

        with tempfile.TemporaryDirectory() as directory:
            wheel = Path(directory) / "numpy.whl"
            with zipfile.ZipFile(wheel, "w") as z:
                z.writestr(target, b"wheel ELF")
            sha = dist.digest(wheel)
            archive = Archive()
            self.assertTrue(dist.verify_numpy_link(archive, name, wheel, sha))
            for bad in (
                b"../" + name.encode() + b"\0",
                b"/numpy.libs/" + name.encode() + b"\0",
                (target + "x\0").encode(),
                target.encode(),
            ):
                archive.data[name] = bad
                with self.assertRaises(ValueError):
                    dist.verify_numpy_link(archive, name, wheel, sha)
            archive.data[name] = (target + "\0").encode()
            archive.data[target] = b"altered"
            with self.assertRaises(ValueError):
                dist.verify_numpy_link(archive, name, wheel, sha)
            archive.data[target] = b"wheel ELF"
            archive.toc[target] = (0, 0, 0, 0, "n")
            with self.assertRaises(ValueError):
                dist.verify_numpy_link(archive, name, wheel, sha)
            archive.toc[target] = (0, 0, 0, 0, "b")
            with self.assertRaises(ValueError):
                dist.verify_numpy_link(archive, name, wheel, "0" * 64)
            with zipfile.ZipFile(wheel, "a") as z:
                z.writestr(target, b"wheel ELF")
            with self.assertRaises(ValueError):
                dist.verify_numpy_link(archive, name, wheel, dist.digest(wheel))

    def test_missing_worker_corresponding_source_evidence_is_refused(self):
        dist = load_module()
        with self.assertRaisesRegex(
            ValueError, "worker corresponding source provenance"
        ):
            dist.verify_worker_corresponding_sources()

    def test_worker_wheelhouse_rejects_missing_extra_and_altered_wheels(self):
        dist = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "demo-1.2-py3-none-any.whl"
            first.write_bytes(b"locked wheel")
            lock = root / "requirements.lock"
            lock.write_text(
                "demo==1.2 \\\n    --hash=sha256:" + dist.digest(first) + "\n"
            )
            self.assertEqual(dist.worker_wheels(root, lock), [first])
            first.write_bytes(b"altered wheel")
            with self.assertRaises(ValueError):
                dist.worker_wheels(root, lock)
            first.write_bytes(b"locked wheel")
            extra = root / "extra-1.0-py3-none-any.whl"
            extra.write_bytes(b"extra")
            with self.assertRaises(ValueError):
                dist.worker_wheels(root, lock)
            extra.unlink()
            first.unlink()
            with self.assertRaises(ValueError):
                dist.worker_wheels(root, lock)

    def test_worker_build_installs_locked_requirements_from_wheelhouse(self):
        from unittest.mock import patch

        dist = load_module()
        with tempfile.TemporaryDirectory() as directory, patch.object(
            dist.shutil, "which", return_value="/tools/uv"
        ), patch.object(dist.subprocess, "run") as run:
            dist.install_worker_requirements("/build/python", Path(directory))
            args, kwargs = run.call_args
            self.assertEqual(
                args[0][:5],
                ["/tools/uv", "pip", "install", "--python", "/build/python"],
            )
            for flag in (
                "--require-hashes",
                "--reinstall",
                "--no-index",
                "--only-binary",
            ):
                self.assertIn(flag, args[0])
            self.assertIn(str(Path(directory).resolve()), args[0])
            self.assertIn(str(dist.ROOT / "desktop/s1d1-requirements.lock"), args[0])
            self.assertTrue(kwargs["check"])

    def test_linux_libraries_retains_debian_integrity_check(self):
        from unittest.mock import patch

        dist = load_module()

        class Archive:
            toc = {"libz.so.1": (0, 0, 0, 0, "b")}

            def extract(self, name):
                return b"altered Debian library"

        with patch.object(
            dist, "strict_carchive_reader", return_value=lambda _: Archive()
        ):
            with self.assertRaisesRegex(ValueError, "origin integrity"):
                dist.linux_libraries("unused")

    def test_duplicate_frozen_entries_are_rejected(self):
        import struct

        dist = load_module()

        def entry(name):
            payload = name.encode() + b"\0"
            return struct.pack("!IIIIBc", 18 + len(payload), 0, 0, 0, 0, b"b") + payload

        reader = dist.strict_carchive_reader()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            reader._parse_toc(entry("numpy.libs/libx.so") * 2)

    def test_rebuild_inputs_cover_managed_worker_and_pinned_requirements(self):
        dist = load_module()
        inputs = dist.engine_rebuild_inputs(ROOT)
        for name in (
            "desktop_managed.py",
            "desktop_deciders.py",
            "desktop_subscriptions.py",
            "desktop_portal.py",
            "desktop/provider-runtime/subscriptions.ts",
            "jev_decider.py",
            "requirements-s1d1.txt",
            "desktop/s1d1-requirements.lock",
        ):
            self.assertIn(name, inputs)
            self.assertTrue((ROOT / name).is_file())

    def test_required_source_is_fetched_and_corrupt_cache_is_refused(self):
        self.assertTrue(SCRIPT.is_file(), "distribution integrity producer is missing")
        dist = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            upstream = root / "upstream.tgz"
            upstream.write_bytes(b"synthetic source archive")
            item = {
                "file": "library.tgz",
                "url": upstream.as_uri(),
                "sha256": hashlib.sha256(upstream.read_bytes()).hexdigest(),
            }
            cache = root / "cache"
            source = dist.verified_source(item, cache)
            self.assertEqual(source.read_bytes(), upstream.read_bytes())
            source.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "integrity"):
                dist.verified_source(item, cache)
            self.assertEqual(source.read_bytes(), b"tampered")

    def test_npm_sources_validate_lockfile_sri(self):
        dist = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            upstream = root / "npm.tgz"
            upstream.write_bytes(b"npm package")
            item = {
                "file": "npm.tgz",
                "url": upstream.as_uri(),
                "integrity": "sha512-wrong",
            }
            with self.assertRaisesRegex(ValueError, "integrity"):
                dist.verified_source(item, root / "cache")
            import base64

            item["integrity"] = (
                "sha512-"
                + base64.b64encode(
                    hashlib.sha512(upstream.read_bytes()).digest()
                ).decode()
            )
            self.assertEqual(
                dist.verified_source(item, root / "cache").read_bytes(),
                upstream.read_bytes(),
            )

    def test_preparation_entrypoint_exists(self):
        dist = load_module()
        self.assertTrue(
            hasattr(dist, "prepare"), "sidecar preparation entrypoint missing"
        )
        self.assertTrue(
            hasattr(dist, "select_runtime"), "hash-pinned Bun selection missing"
        )

    def test_missing_source_and_bad_download_leave_no_accepted_file(self):
        dist = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "bad"
            source.write_bytes(b"not the source")
            item = {"file": "source.tar.gz", "url": source.as_uri(), "sha256": "0" * 64}
            with self.assertRaisesRegex(ValueError, "integrity"):
                dist.verified_source(item, root / "cache")
            self.assertEqual(list((root / "cache").iterdir()), [])

    def test_nested_notices_and_copyright_headers_are_preserved_verbatim(self):
        dist = load_module()
        self.assertTrue(
            hasattr(dist, "archive_notices"), "upstream notice collection missing"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "library.tar.gz"
            files = {
                "lib/Source/JavaScriptCore/COPYING.LIB": b"GNU LIBRARY GENERAL PUBLIC LICENSE\nVersion 2, June 1991\n",
                "lib/Source/JavaScriptCore/API/JSBase.h": b"/* Copyright Synthetic BSD holder\n * conditions and disclaimer\n */\nint f();",
                "lib/licenses/nested/COPYRIGHT": b"Nested copyright and conditions\n",
                "lib/test.js": b"console.log('not a license')",
            }
            with tarfile.open(path, "w:gz") as archive:
                for name, data in files.items():
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    archive.addfile(info, io.BytesIO(data))
            notice = dist.archive_notices(path)
            self.assertIn(
                files["lib/Source/JavaScriptCore/COPYING.LIB"].decode(), notice
            )
            self.assertIn("Copyright Synthetic BSD holder", notice)
            self.assertIn("conditions and disclaimer", notice)
            self.assertIn("Nested copyright and conditions", notice)
            self.assertNotIn("console.log", notice)

    def test_bun_style_headers_outside_webkit_keep_terms_and_source_attribution(self):
        dist = load_module()
        grants = {
            "bun/packages/bun-uws/src/MoveOnlyFunction.h": (
                "/*\nMIT License\nCopyright (c) Synthetic MIT holder\n"
                "Permission is hereby granted: synthetic complete conditions.\n"
                'THE SOFTWARE IS PROVIDED "AS IS".\n*/'
            ),
            "bun/src/jsc/bindings/FormatStackTraceForJS.h": (
                "/*\n * Copyright Synthetic BSD holder\n"
                " * Redistribution in binary form must reproduce these conditions.\n"
                " * SYNTHETIC DISCLAIMER.\n */"
            ),
            "bun/src/glob/matcher.rs": (
                "// Portions derived from works under the MIT License:\n//\n"
                "// Copyright Synthetic Rust holder\n//\n"
                "// Permission and synthetic complete conditions.\n"
                '// THE SOFTWARE IS PROVIDED "AS IS".'
            ),
            "bun/src/other.zig": (
                "// SPDX-License-Identifier: MIT\n"
                "// Synthetic license reference without a copyright statement."
            ),
            "bun/src/other.ts": (
                "/* Harmless leading comment. */\n\n"
                "// Copyright Synthetic TypeScript holder\n// Synthetic conditions."
            ),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bun.tgz"
            with tarfile.open(path, "w:gz") as archive:
                for name, header in grants.items():
                    data = (
                        header + "\n\nconst excluded_implementation = 1;\n"
                    ).encode()
                    member = tarfile.TarInfo(name)
                    member.size = len(data)
                    archive.addfile(member, io.BytesIO(data))
            notice = dist.archive_notices(path)
            for name, header in grants.items():
                with self.subTest(source=name):
                    self.assertIn("Sources: " + name, notice)
                    expected = header.removeprefix(
                        "/* Harmless leading comment. */\n\n"
                    )
                    self.assertIn(expected, notice)
            self.assertNotIn("excluded_implementation", notice)
            self.assertNotIn("Harmless leading comment", notice)

    def test_split_header_grants_keep_conditions_disclaimers_and_bom(self):
        dist = load_module()
        headers = {
            "bun/src/split.h": (
                "/* Copyright Synthetic holder */\n\n"
                "/* Redistribution conditions must remain. */\n"
                '/* THE SOFTWARE IS PROVIDED "AS IS". */'
            ),
            "bun/src/split.rs": (
                "// Copyright Synthetic holder\n\n"
                "// Redistribution conditions must remain.\n\n"
                '// THE SOFTWARE IS PROVIDED "AS IS".'
            ),
            "bun/src/bom.ts": "/* Copyright Synthetic holder with UTF-8 BOM */",
            "bun/src/long.zig": (
                "/* Copyright Synthetic holder\n" + "Terms.\n" * 6000 + "*/"
            ),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bun.tgz"
            with tarfile.open(path, "w:gz") as archive:
                for name, header in headers.items():
                    prefix = "\ufeff" if name.endswith("bom.ts") else ""
                    data = (prefix + header + "\nconst implementation = 1;\n").encode()
                    member = tarfile.TarInfo(name)
                    member.size = len(data)
                    archive.addfile(member, io.BytesIO(data))
            notice = dist.archive_notices(path)
            for name, header in headers.items():
                with self.subTest(source=name):
                    self.assertIn("Sources: " + name, notice)
                    self.assertTrue(header in notice, "complete grant missing: " + name)
            self.assertNotIn("const implementation", notice)

    def test_bun_mit_terms_are_complete_attributed_and_hash_verified(self):
        dist = load_module()
        self.assertTrue(hasattr(dist, "bun_mit_notice"), "standard MIT notice missing")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "MIT.txt"
            # Offline text fixture; the real SPDX text is independently pinned below.
            text = "MIT License\nCopyright (c) <year> <copyright holders>\nFull synthetic terms.\n"
            original.write_text(text)
            item = {
                "file": "spdx-MIT.txt",
                "url": original.as_uri(),
                "sha256": dist.digest(original),
            }
            lock = {"bun_revision": "a" * 40, "bun_mit_terms": item}
            path, notice = dist.bun_mit_notice(lock, root / "cache")
            self.assertEqual(path.read_text(), text)
            self.assertIn(text, notice)
            self.assertIn(item["url"], notice)
            self.assertIn(item["sha256"], notice)
            self.assertIn("a" * 40 + "/LICENSE.md", notice)
            self.assertIn("not a Bun copyright attribution", notice)
            path.write_text("modified license")
            with self.assertRaisesRegex(ValueError, "integrity"):
                dist.bun_mit_notice(lock, root / "cache")
        item = dist.source_lock()["bun_mit_terms"]
        self.assertEqual(
            item["url"],
            "https://raw.githubusercontent.com/spdx/license-list-data/"
            "31846481de7ea17d92f2f46fad76abe58b2e9bb0/text/MIT.txt",
        )
        self.assertEqual(
            item["sha256"],
            "b05785f9f18e6716bab63424b11454513b9943a222595b70411009202fc592b5",
        )

    def test_source_lock_covers_actual_libraries_not_just_mit_bun(self):
        lock = json.loads(
            (ROOT / "desktop/licenses/pi-ai-sources.lock.json").read_text()
        )
        items = {item["id"]: item for item in lock["archives"]}
        for name in ("bun", "webkit", "tinycc", "icu", "boringssl"):
            self.assertIn(name, items)
            self.assertRegex(items[name]["sha256"], r"^[a-f0-9]{64}$")
        self.assertEqual(
            items["webkit"]["revision"], "d6375c72affe0f70222cdcb45012b10f0bf3a9d5"
        )
        self.assertEqual(
            items["tinycc"]["revision"], "05f0fafaa3be31e31d7b4b5c17dc60f62c991171"
        )

    @unittest.skipUnless(
        shutil.which("npm")
        and (ROOT / "desktop/provider-runtime/node_modules/.bin/bun").exists(),
        "install locked runtime build dependencies",
    )
    def test_relink_build_refuses_missing_replacement_instead_of_downloading_upstream(
        self,
    ):
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=ROOT / "desktop/provider-runtime",
            env={
                **os.environ,
                "OMR_BUN_EXECUTABLE_PATH": str(ROOT / "missing-modified-bun"),
            },
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertNotEqual(
            result.returncode,
            0,
            "replacement was ignored; upstream runtime silently used",
        )
        self.assertIn("replacement", result.stderr.lower())

    @unittest.skipUnless(
        os.environ.get("OMR_TEST_ENGINE"),
        "set OMR_TEST_ENGINE to inspect frozen archive",
    )
    def test_frozen_payload_identity_and_notice_integrity(self):
        dist = load_module()
        self.assertTrue(
            hasattr(dist, "verify_engine_payload"),
            "frozen payload verification missing",
        )
        engine = Path(os.environ["OMR_TEST_ENGINE"])
        runtime = ROOT / "desktop/provider-runtime"
        notice = ROOT / "desktop/.sidecar-build/licenses/PI-AI-NOTICES.txt"
        dist.verify_engine_payload(engine, runtime, notice)
        text = notice.read_text()
        for required in (
            "packages/bun-uws/src/MoveOnlyFunction.h",
            "Copyright (c) 2020 Oleg Fatkhiev",
            "src/jsc/bindings/FormatStackTraceForJS.h",
            "Copyright (C) 2024 Jarred Sumner",
            "src/glob/matcher.rs",
            "Copyright (c) 2023 Devon Govett",
            "Copyright (c) 2023 Stephen Gregoratto",
            "Copyright (c) 2024 shulaoda",
            "not a Bun copyright attribution",
            dist.source_lock()["bun_mit_terms"]["url"],
            dist.source_lock()["bun_mit_terms"]["sha256"],
        ):
            with self.subTest(required=required):
                self.assertTrue(required in text, f"missing runtime notice: {required}")
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "notice.txt"
            changed.write_text("not the frozen notice")
            with self.assertRaisesRegex(ValueError, "integrity"):
                dist.verify_engine_payload(engine, runtime, changed)

    @unittest.skipUnless(
        os.environ.get("OMR_TEST_ENGINE") and shutil.which("dpkg-query"),
        "requires a frozen Debian engine",
    )
    def test_linux_copied_shared_libraries_have_exact_package_provenance(self):
        dist = load_module()
        self.assertTrue(
            hasattr(dist, "linux_libraries"), "copied shared-library inventory missing"
        )
        item = dist.source_lock()["numpy_linux_wheel"]
        wheelhouse = os.environ.get("OMR_WORKER_WHEELS")
        wheel = Path(wheelhouse) / item["file"] if wheelhouse else None
        entries = dist.linux_libraries(
            Path(os.environ["OMR_TEST_ENGINE"]),
            wheel,
            item["sha256"] if wheel else None,
        )
        self.assertIn("libpython3.13.so.1.0", {e["file"] for e in entries})
        self.assertIn("libgcc_s.so.1", {e["file"] for e in entries})
        self.assertTrue(
            all(e["package"] and e["version"] and e["source_version"] for e in entries)
        )

    def test_material_root_accepts_a_host_parent_alias_but_not_internal_links(self):
        dist = load_module()
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            actual = base / "actual"
            root = actual / "kit"
            root.mkdir(parents=True)
            (root / "NOTICE.txt").write_text("notice")
            alias = base / "alias"
            alias.symlink_to(actual, target_is_directory=True)
            self.assertEqual(
                dist.safe_file(alias / "kit", "NOTICE.txt").read_text(), "notice"
            )
            (root / "linked").symlink_to(root / "NOTICE.txt")
            with self.assertRaisesRegex(ValueError, "missing regular"):
                dist.safe_file(alias / "kit", "linked")
            with self.assertRaisesRegex(ValueError, "missing regular"):
                dist.safe_file(alias, "kit/NOTICE.txt")

    def test_manifest_rejects_path_traversal_and_symlink(self):
        dist = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("../outside", "C:/outside", "/absolute", "a\\b"):
                with self.assertRaisesRegex(ValueError, "unsafe"):
                    dist.safe_file(root, name)
            source = root / "source"
            source.write_bytes(b"source")
            link = root / "link"
            try:
                link.symlink_to(source)
            except OSError:
                self.skipTest("host does not permit symlinks")
            with self.assertRaisesRegex(ValueError, "missing regular"):
                dist.safe_file(root, "link")

    def test_kit_is_deterministic_and_rejects_missing_or_tampered_materials(self):
        dist = load_module()
        self.assertTrue(
            hasattr(dist, "make_kit"), "deterministic kit producer is missing"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sources").mkdir()
            (root / "sources/library.tgz").write_bytes(
                b"synthetic corresponding source"
            )
            (root / "NOTICE.txt").write_text("Library license notice")
            files = ["NOTICE.txt", "sources/library.tgz"]
            dist.write_manifest(root, {"target": "x86_64-unknown-linux-gnu"}, files)
            first = dist.make_kit(root, root.parent / (root.name + "-a.tar"))
            self.addCleanup(first.unlink, missing_ok=True)
            (root / "NOTICE.txt").touch()
            second = dist.make_kit(root, root.parent / (root.name + "-b.tar"))
            self.addCleanup(second.unlink, missing_ok=True)
            self.assertEqual(dist.digest(first), dist.digest(second))
            (root / "NOTICE.txt").write_text("tampered")
            with self.assertRaisesRegex(ValueError, "integrity"):
                dist.make_kit(root, root / "must-not-exist.tar")
            self.assertFalse((root / "must-not-exist.tar").exists())
            (root / "NOTICE.txt").unlink()
            with self.assertRaisesRegex(ValueError, "missing"):
                dist.verify_manifest(root)


if __name__ == "__main__":
    unittest.main()
