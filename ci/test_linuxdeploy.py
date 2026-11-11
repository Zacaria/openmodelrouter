"""Real Linux relocation regression; a fixture pass is not an OMR release."""

import argparse
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

import desktop as ci

TARGET = "x86_64-unknown-linux-gnu"


class LinuxdeployTests(unittest.TestCase):
    sidecar: Path
    linuxdeploy: Path

    def test_relocation_preserves_identity_but_substitution_does_not(self):
        original = self.sidecar.resolve(strict=True)
        tool = ci.linuxdeploy_tool(self.linuxdeploy)
        with tempfile.TemporaryDirectory(
            prefix="omr-relocation-regression-"
        ) as directory:
            tree = Path(directory) / "Probe.AppDir"
            binaries = tree / "usr/bin"
            binaries.mkdir(parents=True)
            binary = binaries / "omr-engine"
            shutil.copy2(original, binary)
            shutil.copy2("/bin/true", binaries / "omr-desktop")
            for name in ci.LICENSES:
                (binaries / name).write_text("Synthetic regression notice\n")
            # Independent real bundler invocation, not the identity replay helper.
            env = {
                "PATH": os.defpath,
                "HOME": directory,
                "TMPDIR": directory,
                "LC_ALL": "C",
            }
            subprocess.run(
                [str(tool), "--appimage-extract-and-run", "--appdir", str(tree)],
                check=True,
                capture_output=True,
                timeout=120,
                env=env,
            )
            self.assertNotEqual(ci.digest(binary), ci.digest(original))
            self.assertEqual(ci.smoke(binary, TARGET)["ipc"], "pass")
            info = ci.verify_tree(
                tree, original, TARGET, package_format="AppImage", linuxdeploy=tool
            )
            self.assertEqual(info["identity"], "linuxdeploy-07333c6-replay")
            self.assertEqual(info["identity_reference_sha256"], ci.digest(binary))
            with self.assertRaisesRegex(ValueError, "differs from built"):
                ci.verify_tree(tree, original, TARGET, package_format="deb")
            relocated = binary.read_bytes()
            # Preserve architecture, alter bootloader or appended Python payload.
            for offset in [4096, len(relocated) - 256]:
                changed = bytearray(relocated)
                changed[offset] ^= 1
                binary.write_bytes(changed)
                with self.assertRaisesRegex(ValueError, "relocated reference"):
                    ci.verify_tree(
                        tree,
                        original,
                        TARGET,
                        package_format="AppImage",
                        linuxdeploy=tool,
                    )
            shutil.copy2("/bin/true", binary)
            with self.assertRaisesRegex(ValueError, "relocated reference"):
                ci.verify_tree(
                    tree, original, TARGET, package_format="AppImage", linuxdeploy=tool
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sidecar", type=Path, required=True)
    parser.add_argument("--linuxdeploy", type=Path)
    args = parser.parse_args()
    LinuxdeployTests.sidecar = args.sidecar
    LinuxdeployTests.linuxdeploy = args.linuxdeploy or ci.linuxdeploy_tool()
    unittest.main(argv=[__file__], verbosity=2)
