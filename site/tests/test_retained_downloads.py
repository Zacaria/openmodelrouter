"""Retention checks use synthetic files, never published installers."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('retention', Path(__file__).parents[1] / 'scripts/check_retained_downloads.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payload = self.root / 'payload'
        self.path = self.payload / 'downloads/0.1.0/fixture.deb'
        self.path.parent.mkdir(parents=True)
        self.path.write_bytes(b'old fixture')
        self.data = {'downloads/0.1.0/fixture.deb': {'bytes': 11, 'sha256': hashlib.sha256(b'old fixture').hexdigest()}}
        self.manifest = self.root / 'manifest.json'
        self.save()

    def save(self):
        data = json.dumps(self.data).encode()
        self.manifest.write_bytes(data)
        self.hash = hashlib.sha256(data).hexdigest()

    def check(self):
        module.check_retained(self.payload, self.manifest, self.hash)

    def test_retains_original_bytes(self):
        self.check()

    def test_missing_changed_and_symlink_refused(self):
        self.path.write_bytes(b'bad fixture')
        with self.assertRaises(ValueError): self.check()
        self.path.unlink()
        with self.assertRaises(ValueError): self.check()
        outside = self.root / 'outside'
        outside.write_bytes(b'old fixture')
        self.path.symlink_to(outside)
        with self.assertRaises(ValueError): self.check()

    def test_rejects_bad_manifest_and_hash(self):
        with self.assertRaises(ValueError): module.check_retained(self.payload, self.manifest, '0' * 64)
        self.data = {'downloads/../private': {'bytes': 11, 'sha256': '0' * 64}}
        self.save()
        with self.assertRaises(ValueError): self.check()
        self.data = {'index.html': {'bytes': 1, 'sha256': '0' * 64}}
        self.save()
        with self.assertRaises(ValueError): self.check()
        self.data = {'downloads/0.1.0/fixture.deb': {'bytes': 11, 'sha256': '0' * 64}}
        self.save()
        with self.assertRaises(ValueError): self.check()


if __name__ == '__main__':
    unittest.main()
