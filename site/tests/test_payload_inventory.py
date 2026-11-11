"""A pinned payload inventory must describe every regular file exactly."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'check_payload_inventory.py'


class PayloadInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payload = self.root / 'site'
        self.payload.mkdir()
        (self.payload / 'index.html').write_bytes(b'page')
        self.manifest = self.root / 'manifest.json'
        self.entries = {'index.html': {'bytes': 4, 'sha256': hashlib.sha256(b'page').hexdigest()}}

    def check(self):
        self.manifest.write_text(json.dumps(self.entries))
        digest = hashlib.sha256(self.manifest.read_bytes()).hexdigest()
        spec = importlib.util.spec_from_file_location('inventory', SCRIPT)
        self.assertIsNotNone(spec, 'payload inventory checker missing')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.check_inventory(self.payload, self.manifest, digest)

    def test_accepts_exact_inventory(self):
        self.check()

    def test_refuses_modified_missing_extra_and_symlink(self):
        for state in ('modified', 'missing', 'extra', 'symlink'):
            with self.subTest(state=state):
                path = self.payload / 'index.html'
                if path.exists() or path.is_symlink(): path.unlink()
                if state == 'modified': path.write_bytes(b'bad')
                elif state == 'extra':
                    path.write_bytes(b'page')
                    (self.payload / 'extra').write_bytes(b'extra')
                elif state == 'symlink': path.symlink_to(self.manifest)
                with self.assertRaises(ValueError): self.check()
                extra = self.payload / 'extra'
                if extra.exists(): extra.unlink()

    def test_refuses_unsafe_inventory_paths(self):
        self.entries['../escape'] = self.entries.pop('index.html')
        with self.assertRaises(ValueError): self.check()

    def test_refuses_bad_hash_and_invalid_metadata(self):
        self.entries['index.html']['sha256'] = '0' * 64
        with self.assertRaises(ValueError): self.check()
        self.entries['index.html'] = {'bytes': True, 'sha256': hashlib.sha256(b'page').hexdigest()}
        with self.assertRaises(ValueError): self.check()

    def test_refuses_symlink_directory(self):
        (self.payload / 'link').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError): self.check()


if __name__ == '__main__':
    unittest.main()
