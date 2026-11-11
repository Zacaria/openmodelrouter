"""The frozen report remains reproducible without original machine paths."""
import hashlib
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
SCRIPT = ROOT / 'tools/analyze_campaign.py'
SOURCE = ROOT / 'evidence/campaign'


class CampaignAnalysisTests(unittest.TestCase):
    def test_report_and_manifest_reproduce_without_overwriting(self):
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / 'analysis'
            command = [sys.executable, '-B', str(SCRIPT), '--source', str(SOURCE), '--output', str(output)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('120 lignes', result.stdout)
            manifest = (output / 'MANIFEST.sha256').read_text()
            for line in manifest.splitlines():
                digest, name = line.split('  ', 1)
                self.assertEqual(digest, hashlib.sha256((output / name).read_bytes()).hexdigest())
            repeat = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertNotEqual(repeat.returncode, 0)
            self.assertIn('already exists', repeat.stderr)
            self.assertEqual((output / 'MANIFEST.sha256').read_text(), manifest)

    def test_optimized_execution_is_refused_before_file_access(self):
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / 'forbidden'
            for mode in ('-O', '-OO'):
                result = subprocess.run([sys.executable, mode, str(SCRIPT), '--source', '/not-an-input', '--output', str(output)], capture_output=True, text=True, timeout=10)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('requires assertions', result.stderr)
                self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
