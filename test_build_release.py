import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

import build_release as release


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        subprocess.run(['git', '-C', str(self.repo), 'config', 'user.name', 'test'], check=True)
        subprocess.run(['git', '-C', str(self.repo), 'config', 'user.email', 'test@example.invalid'], check=True)
        (self.repo / 'a.txt').write_text('committed')
        subprocess.run(['git', '-C', str(self.repo), 'add', 'a.txt'], check=True)
        subprocess.run(['git', '-C', str(self.repo), '-c', 'commit.gpgsign=false', 'commit', '-qm', 'fixture'], check=True)
        self.commit = subprocess.check_output(['git', '-C', str(self.repo), 'rev-parse', 'HEAD'], text=True).strip()
        (self.repo / 'a.txt').write_text('dirty')
        (self.repo / 'untracked').write_text('secret')

    def tearDown(self):
        self.tmp.cleanup()

    def commit_files(self, files):
        for name, content in files.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        subprocess.run(['git', '-C', str(self.repo), 'add', *files], check=True)
        subprocess.run(['git', '-C', str(self.repo), '-c', 'commit.gpgsign=false', 'commit', '-qm', 'fixture files'], check=True)
        return subprocess.check_output(['git', '-C', str(self.repo), 'rev-parse', 'HEAD'], text=True).strip()

    def test_png_committed_archived_without_omission(self):
        import base64
        png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC')
        commit = self.commit_files({'evidence/landing.png': png})
        bundle = self.root / 'png-bundle'
        release.build(self.repo, commit, 'test', bundle)
        with tarfile.open(bundle / 'open-model-router-test.tar.gz') as tar:
            self.assertEqual(tar.getnames(), ['a.txt', 'evidence/landing.png'])
            self.assertEqual(tar.extractfile('evidence/landing.png').read(), png)
        manifest = json.loads((bundle / 'manifest.json').read_text())
        self.assertEqual({m['path'] for m in manifest['members']}, {'a.txt', 'evidence/landing.png'})

    def test_certification_discovers_all_expected_suites(self):
        for failing in ('test_extra.py', 'host-adapters/test_launch.py', 'tests/test_landing.py', 'tests/test_other.py'):
            with self.subTest(failing=failing):
                files = {'omr.py': b'print("help")\n',
                         'test_extra.py': b'import unittest\nclass T(unittest.TestCase):\n def test_it(self): pass\n',
                         'host-adapters/test_launch.py': b'import unittest\nclass T(unittest.TestCase):\n def test_it(self): pass\n',
                         'tests/test_other.py': b'import unittest\nclass T(unittest.TestCase):\n def test_it(self): pass\n',
                         'tests/test_landing.py': b'import unittest\nclass T(unittest.TestCase):\n def test_it(self): pass\n'}
                files[failing] = b'import unittest\nclass T(unittest.TestCase):\n def test_it(self): self.fail("suite ran")\nif __name__ == "__main__": unittest.main()\n'
                commit = self.commit_files(files)
                bundle = self.root / ('bundle-' + failing.replace('/', '-'))
                release.build(self.repo, commit, 'test', bundle)
                with self.assertRaises(subprocess.CalledProcessError):
                    release.certify(bundle, self.root / ('scratch-' + failing.replace('/', '-')), self.repo, commit)

    def test_certification_old_tree_without_optional_directories(self):
        commit = self.commit_files({'omr.py': b'print("help")\n', 'test_old.py': b'import unittest\nclass T(unittest.TestCase):\n def test_it(self): pass\n'})
        bundle = self.root / 'old-bundle'
        release.build(self.repo, commit, 'test', bundle)
        release.certify(bundle, self.root / 'old-scratch', self.repo, commit)

    def test_forbidden_and_oversized_files_fail_without_output(self):
        for i, (name, data) in enumerate([('model.gguf', b'a'), ('cache/__pycache__/x', b'a'), ('private.key', b'a'), ('large.png', b'x' * 5_000_001)]):
            commit = self.commit_files({name: data})
            with self.assertRaises(ValueError):
                release.build(self.repo, commit, 'test', self.root / f'bad-{i}')
            self.assertFalse((self.root / f'bad-{i}').exists())
            subprocess.run(['git', '-C', str(self.repo), 'rm', '-q', name], check=True)
            subprocess.run(['git', '-C', str(self.repo), '-c', 'commit.gpgsign=false', 'commit', '-qm', 'remove'], check=True)

    def test_determinism_and_committed_tree_only(self):
        for name in ('one', 'two'):
            release.build(self.repo, self.commit, 'test', self.root / name)
        a, b = (self.root / 'one'), (self.root / 'two')
        self.assertEqual((a / 'open-model-router-test.tar.gz').read_bytes(), (b / 'open-model-router-test.tar.gz').read_bytes())
        self.assertEqual((a / 'manifest.json').read_bytes(), (b / 'manifest.json').read_bytes())
        with tarfile.open(a / 'open-model-router-test.tar.gz') as tar:
            self.assertEqual(tar.getnames(), ['a.txt'])
            self.assertEqual(tar.extractfile('a.txt').read(), b'committed')

    def test_forged_identity_rejected_before_extraction(self):
        commit = self.commit_files({'omr.py': b'print("help")\n', 'test_ok.py': b'import unittest\nclass T(unittest.TestCase):\n def test_it(self): pass\n'})
        bundle = self.root / 'bundle'
        release.build(self.repo, commit, 'test', bundle)
        path = bundle / 'manifest.json'
        manifest = json.loads(path.read_text())
        manifest['commit'], manifest['tree'] = '0' * 40, '1' * 40
        path.write_text(json.dumps(manifest))
        dest = self.root / 'extract'
        with self.assertRaisesRegex(ValueError, 'identity'):
            release.certify(bundle, dest, self.repo, commit)
        self.assertFalse(dest.exists())

    def test_forged_content_and_manifest_rejected_before_extraction(self):
        bundle = self.root / 'bundle'
        release.build(self.repo, self.commit, 'test', bundle)
        path = bundle / 'manifest.json'
        manifest = json.loads(path.read_text())
        archive = bundle / manifest['archive']
        data = b'forged content'
        with tarfile.open(archive, 'w:gz') as tar:
            info = tarfile.TarInfo('a.txt')
            info.size = len(data)
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(data))
        manifest['members'][0]['sha256'] = release.digest(data)
        manifest['sha256'] = release.digest(archive.read_bytes())
        path.write_text(json.dumps(manifest))
        (bundle / 'SHA256SUMS').write_text(f"{manifest['sha256']}  {manifest['archive']}\n")
        dest = self.root / 'extract'
        with self.assertRaisesRegex(ValueError, 'member mismatch'):
            release.certify(bundle, dest, self.repo, self.commit)
        self.assertFalse(dest.exists())

    def test_hash_mismatch(self):
        bundle = self.root / 'bundle'
        release.build(self.repo, self.commit, 'test', bundle)
        (bundle / 'open-model-router-test.tar.gz').write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            release.certify(bundle, self.root / 'extract', self.repo, self.commit)
        self.assertFalse((self.root / 'extract').exists())

    def test_malicious_paths_and_links(self):
        for name, kind in [('../escape', tarfile.REGTYPE), ('/absolute', tarfile.REGTYPE), ('link', tarfile.SYMTYPE)]:
            stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode='w:gz') as tar:
                info = tarfile.TarInfo(name)
                info.type = kind
                if kind == tarfile.SYMTYPE:
                    info.linkname = '../escape'
                tar.addfile(info, io.BytesIO(b''))
            data = stream.getvalue()
            sha = hashlib.sha256(data).hexdigest()
            bundle = self.root / ('bundle' + str(len(list(self.root.iterdir()))))
            bundle.mkdir()
            (bundle / 'a.tar.gz').write_bytes(data)
            (bundle / 'SHA256SUMS').write_text(f'{sha}  a.tar.gz\n')
            (bundle / 'manifest.json').write_text(json.dumps({'commit': self.commit, 'tree': release.git(self.repo, 'rev-parse', self.commit + '^{tree}').decode().strip(), 'archive': 'a.tar.gz', 'sha256': sha, 'members': [{'path': name, 'sha256': hashlib.sha256(b'').hexdigest(), 'mode': '100644'}]}))
            dest = bundle / 'dest'
            with self.assertRaises(ValueError):
                release.certify(bundle, dest, self.repo, self.commit)
            self.assertFalse(dest.exists())

    def test_optimized_rejected_before_access(self):
        script = Path(release.__file__)
        for flag in ('-O', '-OO'):
            for args in (['certify', '--repo', '/nonexistent', '--revision', '0' * 40, '--bundle', '/nonexistent', '--scratch', str(self.root / 'out')],
                         ['build', '--repo', '/nonexistent', '--revision', '0' * 40, '--version', 'test', '--output', str(self.root / 'out')]):
                result = subprocess.run([sys.executable, flag, str(script), *args], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('refuses Python', result.stderr)
                self.assertFalse((self.root / 'out').exists())


if __name__ == '__main__':
    unittest.main()
