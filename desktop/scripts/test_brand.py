"""Brand provenance and native-container regression checks (Pillow 12.0.0)."""

import hashlib
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from typing import Iterable, cast
from PIL import Image, IcoImagePlugin

ROOT = Path(__file__).resolve().parents[1]


class BrandTests(unittest.TestCase):
    def test_original_is_unchanged(self):
        self.assertEqual(
            hashlib.sha256(
                (ROOT / "design/originals/upload_3smffdyj.png").read_bytes()
            ).hexdigest(),
            "e07bb3cfb80edc8e5be8ec2f74959330784a934bf9f850ae08450c86ee8bfd05",
        )

    def test_desktop_formats_and_native_templates(self):
        for name, size in [
            ("icon.png", (512, 512)),
            ("tray.png", (32, 32)),
            ("tray-template.png", (44, 32)),
        ]:
            with self.subTest(name=name):
                im = Image.open(ROOT / "src-tauri/icons" / name)
                self.assertEqual(im.size, size)
                self.assertEqual(im.mode, "RGBA")
                self.assertEqual(
                    cast(tuple[int, int, int, int], im.getpixel((0, 0)))[3], 0
                )
        with Image.open(ROOT / "src-tauri/icons/icon.ico") as im:
            self.assertEqual(
                cast(IcoImagePlugin.IcoImageFile, im).ico.sizes(),
                {(n, n) for n in [16, 24, 32, 48, 64, 128, 256]},
            )
        path = ROOT / "src-tauri/icons/icon.icns"
        data = path.read_bytes()
        self.assertEqual(data[:4], b"icns")
        self.assertEqual(struct.unpack(">I", data[4:8])[0], len(data))
        with Image.open(path) as im:
            self.assertIn((512, 512, 2), im.info["sizes"])
        with Image.open(ROOT / "public/brand/app-128.png") as im:
            self.assertEqual(im.size, (128, 128))
        template = Image.open(ROOT / "src-tauri/icons/tray-template.png")
        pixels = list(cast(Iterable[tuple[int, int, int, int]], template.getdata()))
        self.assertGreater(sum(a > 127 for *_, a in pixels), 30)
        self.assertTrue(all(r == g == b == 0 for r, g, b, a in pixels if a))

    def test_template_keeps_three_destinations_not_only_a_generic_y(self):
        alpha = Image.open(ROOT / "src-tauri/icons/tray-template.png").getchannel("A")
        # Three distinct output blocks in the right-hand quarter of the supplied
        # routing sign must survive monochrome reduction. The former Y has one.
        rows = [
            any(
                cast(int, alpha.getpixel((x, y))) > 127
                for x in range(int(alpha.width * 0.72), int(alpha.width * 0.94))
            )
            for y in range(alpha.height)
        ]
        bands = sum(
            value and (y == 0 or not rows[y - 1]) for y, value in enumerate(rows)
        )
        self.assertEqual(
            bands, 3, "The menu-bar mark lost the three routing destinations"
        )

    def test_rust_uses_monochrome_template_only_on_macos(self):
        rust = (ROOT / "src-tauri/src/main.rs").read_text()
        self.assertRegex(
            rust,
            r'if cfg!\(target_os = "macos"\)\s*\{\s*'
            r'include_bytes!\("../icons/tray-template.png"\)\s*\}\s*else\s*\{\s*'
            r'include_bytes!\("../icons/tray.png"\)',
        )
        self.assertIn('.icon_as_template(cfg!(target_os = "macos"))', rust)

    def test_regeneration_matches_all_committed_derivatives(self):
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/build_brand.py"), "--check"],
            check=True,
        )


if __name__ == "__main__":
    unittest.main()
