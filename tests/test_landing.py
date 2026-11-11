"""Offline contract for the supplied Landing Ready; no browser or network."""
from html.parser import HTMLParser
from hashlib import sha256
from pathlib import Path
import json
import os
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
BUILT = Path(os.environ.get("OMR_TEST_BUILT_DIR", SITE / "dist"))


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.ids, self.links, self.assets, self.tags, self.text = [], [], [], [], []
        self.remote = []
        self.footer_depth = 0
        self.lang = None
        self.hidden_text = 0
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        raw_attrs = attrs
        attrs = dict(attrs)
        if tag == "footer": self.footer_depth += 1
        for key, value in raw_attrs:
            if key.endswith(("src", "href")) and not re.fullmatch(r"(?:/(?![/\\])|#)[^\s\\\x00-\x1f\x7f]*", value or ""):
                self.remote.append((tag, key, value, attrs.get("class", ""), self.footer_depth > 0))
        self.tags.append((tag, attrs))
        if tag == "html": self.lang = attrs.get("lang")
        if "id" in attrs: self.ids.append(attrs["id"])
        if tag == "a" and "href" in attrs: self.links.append(attrs["href"])
        if tag in ("script", "img"): self.assets.append(attrs.get("src", ""))
        if tag == "link" and attrs.get("rel") in ("stylesheet", "icon"): self.assets.append(attrs.get("href", ""))
        if tag in ("script", "style"): self.hidden_text += 1

    def handle_endtag(self, tag):
        if tag == "footer": self.footer_depth = max(0, self.footer_depth - 1)
        if tag in ("script", "style"): self.hidden_text -= 1

    def handle_data(self, data):
        if not self.hidden_text: self.text.append(data)


class LandingContract(unittest.TestCase):
    def assert_no_remote_loads(self, page):
        for asset in page.assets:
            self.assertTrue(not asset or (asset.startswith("/") and not asset.startswith("//")), asset)
        self.assertEqual(page.remote, [("a", "href", "https://open-model-router-materials-3.vercel.app/", "source-materials", True)])

    def test_remote_loads_are_rejected_for_every_tag(self):
        allowed = '<footer><a class="source-materials" href="https://open-model-router-materials-3.vercel.app/">Sources</a></footer>'
        self.assert_no_remote_loads(Page(allowed))
        for extra in (
            '<iframe src="https://blocked.invalid/frame"></iframe>',
            '<link rel="preload" href="https://blocked.invalid/font">',
            '<iframe class="source-materials" src="https://open-model-router-materials-3.vercel.app/"></iframe>',
            '<link class="source-materials" rel="preload" href="https://open-model-router-materials-3.vercel.app/">',
            '<iframe src="https://blocked.invalid/first" src="/local"></iframe>',
            '<svg><image xlink:href="https://blocked.invalid/image" /></svg>',
        ):
            with self.subTest(extra=extra), self.assertRaises(AssertionError):
                self.assert_no_remote_loads(Page(allowed + extra))

    def test_browser_normalized_urls_and_relocated_exception_are_rejected(self):
        anchor = '<a class="source-materials" href="https://open-model-router-materials-3.vercel.app/">Sources</a>'
        allowed = '<footer>' + anchor + '</footer>'
        self.assert_no_remote_loads(Page(allowed))
        for value in ("https:&#10;//blocked.invalid/frame", "ht&#9;tps://blocked.invalid/frame", "/&#13;/blocked.invalid/frame", "/&#92;blocked.invalid/frame"):
            with self.subTest(value=value), self.assertRaises(AssertionError):
                self.assert_no_remote_loads(Page(allowed + '<iframe src="' + value + '"></iframe>'))
        with self.assertRaises(AssertionError):
            self.assert_no_remote_loads(Page('<main>' + anchor + '</main>'))

    def test_source_keeps_reference_sections_and_interactive_contract(self):
        for lang in ("en", "fr"):
            html = (SITE / "src/templates" / (lang + ".html")).read_text()
            page = Page(html)
            self.assertEqual(page.lang, lang)
            self.assertEqual(len(page.ids), len(set(page.ids)))
            self.assertTrue({"main", "pourquoi", "profils", "capacites", "fonctionnement", "disponibilite", "faq"} <= set(page.ids))
            self.assertEqual(sum(tag == "h1" for tag, attrs in page.tags), 1)
            self.assertEqual(sum("data-download" in attrs for tag, attrs in page.tags), 2)
            scenarios = [attrs["data-scenario"] for tag, attrs in page.tags if tag == "button" and "data-scenario" in attrs]
            self.assertEqual(scenarios, ["quick", "chat", "reason", "vision"] * 2)
            self.assertEqual(sum("data-route" in attrs for tag, attrs in page.tags), 4)
            self.assertIn('id="release-data"', html)
            self.assertIn('id="ui-copy"', html)
            self.assert_no_remote_loads(page)
            expected = "Chaque requête. Le bon modèle." if lang == "fr" else "Every request. Right model."
            self.assertIn(expected, " ".join(" ".join(page.text).split()))

    def test_reader_copy_preserves_configuration_and_privacy_limits_not_internal_status(self):
        html = (SITE / "src/templates/fr.html").read_text()
        text = " ".join(" ".join(Page(html).text).lower().split())
        for needed in ("un abonnement ne fournit pas automatiquement", "local ne signifie pas hors ligne", "explicitement configuré et consenti", "code de confiance", "les données manquantes restent inconnues"):
            self.assertIn(needed, text)
        for internal in ("non vérifiée", "backend synthétique", "en développement", "mock backend", "axe-core", "test pass", "sha git"):
            self.assertNotIn(internal, text)
        css = (SITE / "src/ready.css").read_text()
        self.assertIn("prefers-reduced-motion", css)
        self.assertNotRegex(css, r"https?://|@import")
        for font in ("dm-sans.ttf", "space-grotesk.ttf", "ibm-plex-mono.ttf"):
            self.assertTrue((SITE / "assets/fonts" / font).is_file())
        self.assertTrue((SITE / "assets/logo.webp").is_file())

    def test_built_locales_resources_and_exact_download_bytes(self):
        if "--built" not in sys.argv: self.skipTest("build output checked by npm test --built")
        for lang, file in (("en", "index.html"), ("en", "en/index.html"), ("fr", "fr/index.html")):
            html = (BUILT / file).read_text()
            page = Page(html)
            self.assertEqual(page.lang, lang)
            self.assertEqual(len(page.ids), len(set(page.ids)))
            self.assertIn('tabindex="-1"', html)
            self.assert_no_remote_loads(page)
            self.assertNotIn("<!--release-data-->", html)
            self.assertNotIn("<!--packages-->", html)
            for asset in page.assets:
                if not asset: continue
                self.assertTrue(asset.startswith("/"), asset)
                self.assertTrue((BUILT / asset.lstrip("/")).is_file(), asset)
            for link in page.links:
                if link.startswith("/downloads/"):
                    self.assertRegex(link, r"^/downloads/[0-9A-Za-z.-]+/omr-[0-9A-Za-z.-]+\.(?:dmg|exe|msi|deb|AppImage)(?:\.sha256)?$")
                    self.assertTrue((BUILT / link[1:]).is_file(), link)
                elif link == "/assets/materials/0.3.2/":
                    source_page = (BUILT / link[1:] / "index.html").read_text()
                    archive = (BUILT / link[1:] / "rebuild.tar").read_bytes()
                    self.assertEqual(sha256(archive).hexdigest(), "be5e73c9cfabf50d11ce3a8d2b9fdebf743344b5d4fc6d1a19de8668e3f51c6d")
                    self.assertIn(sha256(archive).hexdigest(), source_page)
                elif link == "/assets/materials/0.3.1/":
                    source_page = (BUILT / link[1:] / "index.html").read_text()
                    patch = (BUILT / link[1:] / "rebuild.patch").read_bytes()
                    self.assertIn(sha256(patch).hexdigest(), source_page)
                    self.assertIn("fdc83fc014755b4432072fce31b8f6802cd658ed", source_page)
                else:
                    self.assertTrue(link in ("/en/", "/fr/", "https://open-model-router-materials-3.vercel.app/") or (link.startswith("#") and link[1:] in page.ids), link)
            release_match = re.search(r'<script id="release-data" type="application/json">(.*?)</script>', html, re.S)
            if release_match is None: self.fail("Missing built release data")
            release = json.loads(release_match[1])
            for package in release["packages"]:
                binary = BUILT / package["url"].lstrip("/")
                self.assertEqual(binary.stat().st_size, package["bytes"])
                self.assertEqual(sha256(binary.read_bytes()).hexdigest(), package["sha256"])
                self.assertEqual((BUILT / package["checksumUrl"].lstrip("/")).read_text(), f'{package["sha256"]}  {package["file"]}\n')
            text = " ".join(page.text).lower()
            for internal in ("backend synthétique", "non vérifiée", "en développement", "development build"):
                self.assertNotIn(internal, text)


if __name__ == "__main__":
    unittest.main(argv=[arg for arg in sys.argv if arg != "--built"], verbosity=2)
