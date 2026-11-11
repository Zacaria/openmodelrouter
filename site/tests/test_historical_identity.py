"""Historical provenance with a real signed fixture tag; no production calls."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

script = Path(__file__).resolve().parents[1] / 'scripts' / 'publish_guard.py'
sys.path.insert(0, str(script.parent))
spec = importlib.util.spec_from_file_location('historical_guard', script)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class HistoricalIdentityTest(unittest.TestCase):
    def test_signed_historical_identity_and_substitutions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=root, stderr=subprocess.DEVNULL, text=True).strip()
            git('init', '-q')
            for key, val in [('user.name', 'Test'), ('user.email', 'test@example.invalid'), ('gpg.format', 'ssh')]:
                git('config', key, val)
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(root / 'key')], check=True)
            git('config', 'user.signingkey', str(root / 'key'))
            (root / 'allowed').write_text('test@example.invalid ' + (root / 'key.pub').read_text())
            git('config', 'gpg.ssh.allowedSignersFile', str(root / 'allowed'))
            (root / 'desktop/src-tauri').mkdir(parents=True)
            (root / 'desktop/package.json').write_text('{"version":"0.1.0"}')
            (root / 'desktop/src-tauri/tauri.conf.json').write_text('{"version":"0.1.0"}')
            (root / 'desktop/src-tauri/Cargo.toml').write_text('[package]\nversion="0.1.0"\n')
            git('add', 'desktop')
            git('commit', '-qm', 'fixture')
            source = git('rev-parse', 'HEAD')
            tag = 'desktop-v0.1.0-candidate.1'
            git('tag', '-s', tag, '-m', 'historical fixture')
            oid = git('rev-parse', 'refs/tags/' + tag)
            items = []
            for system, arch, ext, trust in [('linux','x64','deb','linux-unsigned'), ('windows','x64','exe','windows-unsigned'), ('macos','x64','dmg','macos-notarized'), ('macos','arm64','dmg','macos-notarized')]:
                items.append(dict(version='0.1.0', os=system, arch=arch, file=f'omr-0.1.0-{system}-{arch}.{ext}', bytes=1, sha256='a'*64, sourceCommit=source, releaseApproved=True, native='verified', generation='synthetic-only', trust=trust))
            historical = root / 'historical.json'
            historical.write_text(json.dumps({'artifacts': items}))
            artifact = root / 'artifacts.json'
            artifact.write_text(json.dumps({'artifacts': [dict(x, prerelease=True) for x in items]}))
            bindir = root / 'bin'; bindir.mkdir()
            gh = bindir / 'gh'
            gh.write_text('#!/bin/sh\nprintf \'%s\\n\' ' + "'" + json.dumps({'ref':'refs/tags/' + tag,'object':{'type':'tag','sha':oid}}) + "'\n")
            gh.chmod(0o755)
            args = SimpleNamespace(product=str(root), source=source, tag=tag, artifacts=str(artifact), historical_manifest=str(historical), landing_only=True)
            with patch.object(guard, 'HISTORICAL_SOURCE', source), patch.object(guard, 'HISTORICAL_TAG_OID', oid), patch.object(guard, 'HISTORICAL_MANIFEST_HASH', hashlib.sha256(historical.read_bytes()).hexdigest()), patch.dict(os.environ, {'PATH':str(bindir) + os.pathsep + os.environ['PATH']}):
                guard.check_historical_identity(args)
                # A new release authenticates its own identity separately; the
                # catalogue must retain exactly the signed historical metadata.
                old_items = json.loads(artifact.read_bytes())['artifacts']
                future = dict(old_items[0], version='1.2.3', sourceCommit='b'*40,
                              file='omr-1.2.3-linux-x64.deb', prerelease=False)
                new_artifacts = root / 'new-artifacts.json'
                new_artifacts.write_text(json.dumps({'artifacts': [future]}))
                catalog = root / 'catalog.json'
                combined = {'artifacts': [future, *old_items]}
                catalog.write_text(json.dumps(combined))
                new_args = SimpleNamespace(**{**vars(args), 'catalog': str(catalog),
                    'artifacts': str(new_artifacts), 'landing_only': False,
                    'source': 'b'*40, 'tag': 'desktop-v1.2.3'})
                guard.check_historical_identity(new_args)
                for index, field, value in ((0, 'sourceCommit', 'c'*40),
                                            (1, 'generation', 'verified'),
                                            (1, 'prerelease', False)):
                    changed = json.loads(json.dumps(combined))
                    changed['artifacts'][index][field] = value
                    catalog.write_text(json.dumps(changed))
                    with self.subTest(catalog_field=field), self.assertRaises(ValueError):
                        guard.check_historical_identity(new_args)
                for entries in (combined['artifacts'][:-1], combined['artifacts'][::-1],
                                combined['artifacts'] + [old_items[0]]):
                    catalog.write_text(json.dumps({'artifacts': entries}))
                    with self.subTest(catalog_entries=len(entries)), self.assertRaises(ValueError):
                        guard.check_historical_identity(new_args)
                catalog.write_text(json.dumps(combined))
                for field, val in [('source','b'*40), ('tag','desktop-v0.1.0'), ('landing_only',False)]:
                    original = getattr(args, field); setattr(args, field, val)
                    with self.subTest(field=field), self.assertRaises(ValueError): guard.check_historical_identity(args)
                    setattr(args, field, original)
                original = artifact.read_bytes()
                altered = json.loads(original); altered['artifacts'][0]['generation'] = 'verified'
                artifact.write_text(json.dumps(altered))
                with self.assertRaises(ValueError): guard.check_historical_identity(args)
                altered = json.loads(original); altered['artifacts'][0]['prerelease'] = 1
                artifact.write_text(json.dumps(altered))
                with self.assertRaises(ValueError): guard.check_historical_identity(args)
                artifact.write_bytes(original)
                gh.write_text('#!/bin/sh\nprintf \'%s\\n\' ' + "'" + json.dumps({'ref':'refs/tags/' + tag,'object':{'type':'tag','sha':'b'*40}}) + "'\n")
                with self.assertRaises(ValueError): guard.check_historical_identity(args)
                gh.write_text('#!/bin/sh\nprintf \'%s\\n\' ' + "'" + json.dumps({'ref':'refs/tags/' + tag,'object':{'type':'tag','sha':oid}}) + "'\n")
                (root / 'allowed').write_text('')
                with self.assertRaises(ValueError): guard.check_historical_identity(args)
                (root / 'allowed').write_text('test@example.invalid ' + (root / 'key.pub').read_text())
                historical.write_bytes(historical.read_bytes() + b' ')
                with self.assertRaises(ValueError): guard.check_historical_identity(args)


if __name__ == '__main__': unittest.main()
