"""The source delta is reproducible, input-bound, and contains only chosen files."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/build-r15-source-delta.py'
spec = importlib.util.spec_from_file_location('r15_delta', SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError('source delta generator unavailable')
delta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delta)


def archive(files):
    result = io.BytesIO()
    with tarfile.open(fileobj=result, mode='w', format=tarfile.USTAR_FORMAT) as tar:
        for path, data in sorted(files.items()):
            info = tarfile.TarInfo(path)
            info.size = len(data)
            info.mode = 0o644
            info.uid = info.gid = info.mtime = 0
            info.uname = info.gname = ''
            tar.addfile(info, io.BytesIO(data))
    return result.getvalue()


def sha(data):
    return hashlib.sha256(data).hexdigest()


class DeltaTests(unittest.TestCase):
    def test_reproducible_bound_and_private_projection_omitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contents = {f'pi-ai-distribution/rebuild/{i}.py': str(i).encode() for i in range(22)}
            overlay = archive({**contents, 'PRIVATE-PROJECTION.json': b'private evidence'})
            roster = {'files': {f'sources/{i}.txt': {'bytes': 1, 'sha256': sha(b'x')} for i in range(774)}}
            manifest = json.dumps(roster).encode()
            records = {name: {'bytes': len(data), 'sha256': sha(data)} for name, data in sorted(contents.items())}
            files = dict(contents)
            files['SOURCE-MANIFEST.json'] = (json.dumps({'schema': 1, 'version': '0.3.2', 'platform': 'macos-arm64', 'files': records}, indent=2, sort_keys=True) + '\n').encode()
            files['SOURCE-REFERENCE.json'] = (json.dumps({'schema': 1, 'version': '0.3.2', 'platform': 'macos-arm64', 'files': roster['files']}, indent=2, sort_keys=True) + '\n').encode()
            expected = archive(files)
            a, b = root/'overlay.tar', root/'manifest.json'
            a.write_bytes(overlay); b.write_bytes(manifest)
            with patch.object(delta, 'OVERLAY_HASH', sha(overlay)), patch.object(delta, 'RUNTIME_MANIFEST_HASH', sha(manifest)), patch.object(delta, 'DELTA_HASH', sha(expected)):
                self.assertEqual(delta.make_delta(a, b), expected)
                a.write_bytes(overlay + b'changed')
                with self.assertRaises(ValueError): delta.make_delta(a, b)
                a.write_bytes(overlay); b.write_bytes(manifest + b' ')
                with self.assertRaises(ValueError): delta.make_delta(a, b)


if __name__ == '__main__':
    unittest.main()
