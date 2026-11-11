import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import download_s1d1


class DownloadTests(unittest.TestCase):
    def test_verified_download_is_reusable_and_mismatch_never_overwrites(self):
        data = b'synthetic weight fixture'
        sha = hashlib.sha256(data).hexdigest()
        with tempfile.TemporaryDirectory() as directory, patch.object(download_s1d1, 'FILES', {'model.onnx': sha}):
            root = Path(directory)
            with patch.object(download_s1d1, 'urlopen', return_value=io.BytesIO(data)) as request:
                download_s1d1.download(root)
                self.assertEqual((root/'model.onnx').read_bytes(),data)
                download_s1d1.download(root)
                self.assertEqual(request.call_count,1)
            (root/'model.onnx').write_bytes(b'user file')
            with self.assertRaises(ValueError): download_s1d1.download(root)
            self.assertEqual((root/'model.onnx').read_bytes(),b'user file')

    def test_bad_download_does_not_become_a_weight_file(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(download_s1d1, 'FILES', {'model.onnx':'0'*64}), patch.object(download_s1d1,'urlopen',return_value=io.BytesIO(b'bad')):
            with self.assertRaises(ValueError): download_s1d1.download(Path(directory))
            self.assertEqual(list(Path(directory).iterdir()),[])


if __name__ == '__main__': unittest.main()
