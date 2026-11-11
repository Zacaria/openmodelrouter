"""Exercise the publication entry point with disposable payloads and inert Vercel."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
import shlex
import shutil
import subprocess
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'publish_guard.py'
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location('publish_guard', SCRIPT)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
REAL_CHECK_IMMUTABLE = guard.check_immutable
REAL_CHECK_IDENTITY = guard.check_identity
REAL_CHECK_REMOTE = guard.check_remote_identity
REAL_CHECK_NEW_PATHS = guard.check_new_paths


class R15ProvenanceTests(unittest.TestCase):
    def test_real_pinned_provenance_and_catalog(self):
        archive = Path(os.environ.get('OMR_R15_TEST_ARCHIVE', ''))
        source_manifest = Path(os.environ.get('OMR_R15_TEST_SOURCE_MANIFEST', ''))
        previous = Path(os.environ.get('OMR_R15_TEST_PREVIOUS_CATALOG', ''))
        if not all(p.is_file() for p in (archive, source_manifest, previous)):
            self.skipTest('retained private R15 evidence unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            item = {'version':'0.3.2', 'os':'macos', 'arch':'arm64',
                'file':'omr-0.3.2-macos-arm64.dmg', 'bytes':147373192,
                'sha256':'3b630c950f95f7fae6692f80cc651090e575896d9324ccd5190a4e1623892550',
                'sourceCommit':'6ad23212def5a9da21b2e1a6b356e95aa2411fe6',
                'prerelease':None, 'releaseApproved':True, 'native':'verified',
                'generation':'synthetic-only', 'trust':'macos-notarized'}
            artifacts, catalog = root / 'artifacts.json', root / 'catalog.json'
            artifacts.write_text(json.dumps({'artifacts':[item]}))
            old = json.loads(previous.read_bytes())['artifacts']
            catalog.write_text(json.dumps({'artifacts':[item, *old]}))
            args = SimpleNamespace(r15_archive=str(archive), r15_source_manifest=str(source_manifest),
                previous_catalog=str(previous), catalog=str(catalog), artifacts=str(artifacts),
                source=item['sourceCommit'], product=str(SCRIPT.parents[2]))
            guard.check_r15_identity(args)
            for change in ('status', 'digest', 'source', 'catalog', 'previous', 'archive', 'manifest'):
                with self.subTest(change=change):
                    original = item.copy()
                    if change == 'status': item['prerelease'] = False
                    if change == 'digest': item['sha256'] = '0' * 64
                    if change == 'source': args.source = '0' * 40
                    if change == 'catalog': catalog.write_text(json.dumps({'artifacts':[item, *old[1:]]}))
                    if change == 'previous': args.previous_catalog = str(artifacts)
                    if change == 'archive': args.r15_archive = str(artifacts)
                    if change == 'manifest': args.r15_source_manifest = str(artifacts)
                    artifacts.write_text(json.dumps({'artifacts':[item]}))
                    with self.assertRaises(ValueError): guard.check_r15_identity(args)
                    item.clear(); item.update(original)
                    args.source = item['sourceCommit']; args.previous_catalog = str(previous)
                    args.r15_archive = str(archive); args.r15_source_manifest = str(source_manifest)
                    catalog.write_text(json.dumps({'artifacts':[item, *old]}))
                    artifacts.write_text(json.dumps({'artifacts':[item]}))


    def test_exact_signed_payload_and_checksum(self):
        import zipfile
        archive = Path(os.environ.get('OMR_R15_TEST_ARCHIVE', ''))
        if not archive.is_file(): self.skipTest('retained private R15 archive unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); name = 'omr-0.3.2-macos-arm64.dmg'
            dest = root / 'site/downloads/0.3.2' / name
            dest.parent.mkdir(parents=True)
            with zipfile.ZipFile(archive) as z, z.open(guard.R15_DMG_NAME) as source, dest.open('wb') as target:
                shutil.copyfileobj(source, target)
            checksum = dest.with_name(name+'.sha256')
            checksum.write_text(f'{guard.R15_DMG_HASH}  {name}\n')
            item = {'version':'0.3.2', 'os':'macos', 'arch':'arm64', 'file':name,
                'bytes':guard.R15_DMG_BYTES, 'sha256':guard.R15_DMG_HASH,
                'sourceCommit':guard.R15_SOURCE, 'prerelease':None, 'releaseApproved':True,
                'native':'verified', 'generation':'synthetic-only', 'trust':'macos-notarized'}
            manifest = root / 'artifacts.json'; manifest.write_text(json.dumps({'artifacts':[item]}))
            args = SimpleNamespace(payload_root=str(root), artifacts=str(manifest), source=guard.R15_SOURCE, r15_no_tag=True)
            self.assertEqual(guard.artifact_paths(args), ['downloads/0.3.2/'+name])
            checksum.write_text('wrong\n')
            with self.assertRaises(ValueError): guard.artifact_paths(args)
            checksum.write_text(f'{guard.R15_DMG_HASH}  {name}\n')
            with dest.open('r+b') as f: f.seek(0); f.write(b'X')
            with self.assertRaises(ValueError): guard.artifact_paths(args)
            args.r15_no_tag = False
            with self.assertRaises(ValueError): guard.artifact_paths(args)

    def test_public_source_streams_verify_parts_and_assembled_archive(self):
        import hashlib
        import io
        bodies = {'https://test/base': b'base', 'https://test/one': b'a', 'https://test/two': b'b', 'https://test/three': b'c'}
        records = [(name, len(data), hashlib.sha256(data).hexdigest()) for name, data in bodies.items()]
        class Response(io.BytesIO):
            status = 200
            headers = {'Content-Encoding': 'identity'}
        class Opener:
            def open(self, request, timeout):
                return Response(bodies[request.full_url])
        with patch.object(guard, 'R15_PUBLIC_SOURCE_PARTS', records), \
             patch.object(guard, 'R15_WEBKIT_ASSEMBLED_HASH', hashlib.sha256(b'abc').hexdigest()), \
             patch.object(guard, 'build_opener', return_value=Opener()):
            guard.check_public_r15_sources()
            bodies['https://test/two'] = b'x'
            with self.assertRaises(ValueError):
                guard.check_public_r15_sources()
            bodies['https://test/two'] = b'b'
            with patch.object(guard, 'R15_WEBKIT_ASSEMBLED_HASH', '0' * 64):
                with self.assertRaises(ValueError): guard.check_public_r15_sources()
            with patch.object(Response, 'status', 404):
                with self.assertRaises(ValueError): guard.check_public_r15_sources()
            with patch.object(Response, 'headers', {'Content-Encoding': 'gzip'}):
                with self.assertRaises(ValueError): guard.check_public_r15_sources()
            with patch.object(guard.time, 'monotonic', side_effect=[0, 901]):
                with self.assertRaisesRegex(ValueError, 'timed out'): guard.check_public_r15_sources()

    def test_r15_material_identity_is_checked_before_network(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            target = root / 'site/assets/materials/0.3.2/rebuild.tar'
            target.parent.mkdir(parents=True)
            target.write_bytes(b'synthetic-material')
            expected = __import__('hashlib').sha256(b'synthetic-material').hexdigest()
            args = SimpleNamespace(payload_root=str(root))
            with patch.object(guard, 'R15_MATERIALS_HASH', expected), \
                 patch.object(guard, 'R15_MATERIALS_BYTES', len(b'synthetic-material')), \
                 patch.object(guard, 'check_public_r15_sources') as remote:
                guard.check_r15_materials(args)
                remote.assert_called_once()
                remote.reset_mock()
                target.write_bytes(b'tampered-material')
                with self.assertRaises(ValueError):
                    guard.check_r15_materials(args)
                remote.assert_not_called()

    def test_no_tag_route_cannot_deploy_or_bypass_gates(self):
        args = SimpleNamespace(r15_no_tag=True, catalog='catalog', r15_archive='archive',
            r15_source_manifest='source', previous_catalog='previous')
        checks = ('check_destination', 'check_r15_identity', 'check_immutable', 'check_payload', 'check_retention', 'check_collisions', 'check_r15_materials')
        from contextlib import ExitStack
        with ExitStack() as stack:
            mocks = {name: stack.enter_context(patch.object(guard, name)) for name in checks}
            deploy = stack.enter_context(patch.object(guard, 'deploy'))
            tagged = stack.enter_context(patch.object(guard, 'check_identity'))
            remote = stack.enter_context(patch.object(guard, 'check_remote_identity'))
            guard.publish(args)
            for mock in mocks.values(): mock.assert_called_once_with(args)
            deploy.assert_called_once_with(args); tagged.assert_not_called(); remote.assert_not_called()
            deploy.reset_mock()
            for name in checks:
                for mock in mocks.values(): mock.reset_mock()
                mocks[name].side_effect = ValueError(name)
                with self.subTest(check=name), self.assertRaisesRegex(ValueError, name): guard.publish(args)
                mocks[name].side_effect = None
                deploy.assert_not_called()
            for name in ('tag', 'tag_annotation', 'release_notes', 'historical_manifest', 'landing_only'):
                setattr(args, name, 'not-allowed')
                with self.subTest(argument=name), self.assertRaises(ValueError): guard.publish(args)
                setattr(args, name, None)
            args.r15_no_tag = False
            with self.assertRaisesRegex(ValueError, 'requires R15'): guard.publish(args)
            deploy.assert_not_called()

    def test_r15_retention_and_both_collision_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); site = root / 'site'; site.mkdir()
            old = {}
            for n in range(12):
                name = f'downloads/old/{n}'
                file = site / name; file.parent.mkdir(parents=True, exist_ok=True); file.write_bytes(str(n).encode())
                old[name] = {'bytes':len(str(n)), 'sha256':hashlib.sha256(str(n).encode()).hexdigest()}
            retained = root / 'retained.json'; retained.write_text(json.dumps(old))
            path = 'downloads/0.3.2/omr-0.3.2-macos-arm64.dmg'
            inventory = root / 'inventory.json'; inventory.write_text(json.dumps({**old, path:{}, path+'.sha256':{}}))
            args = SimpleNamespace(r15_no_tag=True, payload_root=str(root), retained_manifest=str(retained), payload_manifest=str(inventory))
            with patch.object(guard, 'R15_RETAINED_HASH', hashlib.sha256(retained.read_bytes()).hexdigest()), \
                 patch.object(guard, 'artifact_paths', return_value=[path]), \
                 patch.object(guard, 'check_new_paths') as collision:
                guard.check_retention(args); guard.check_collisions(args)
                collision.assert_called_once_with(guard.ORIGIN, ['/'+path, '/'+path+'.sha256', '/assets/materials/0.3.2/', '/assets/materials/0.3.2/index.html', '/assets/materials/0.3.2/rebuild.tar'])
                for name in old:
                    file = site / name; original = file.read_bytes(); file.write_bytes(original+b'x')
                    with self.subTest(path=name), self.assertRaises(ValueError): guard.check_retention(args)
                    file.write_bytes(original)
                inventory.write_text(json.dumps({**old, path:{}}))
                with self.assertRaises(ValueError): guard.check_retention(args)
                retained.write_bytes(retained.read_bytes()+b' ')
                with self.assertRaises(ValueError): guard.check_retention(args)


class RetentionPinTests(unittest.TestCase):
    def test_current_production_downloads_are_the_retention_baseline(self):
        self.assertEqual(guard.RETAINED_HASH,
            '7c029fc2f2e72cc39bdfedb0ddb36fc2dfe58b1ab9022f604cd5c62f8399f6ae')


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payload = self.root / 'deployment'
        (self.payload / '.vercel').mkdir(parents=True)
        (self.payload / '.vercel/project.json').write_text(json.dumps({'projectId': guard.PROJECT, 'orgId': guard.ORG}))
        self.site = self.payload / 'site'
        self.dest = self.site / 'downloads/1.2.3/omr-1.2.3-linux-x64.deb'
        self.dest.parent.mkdir(parents=True)
        self.dest.write_bytes(b'new package')
        digest = hashlib.sha256(self.dest.read_bytes()).hexdigest()
        self.checksum = self.dest.with_name(self.dest.name + '.sha256')
        self.checksum.write_text(f'{digest}  {self.dest.name}\n')
        self.old = self.site / 'downloads/0.1.0/old.deb'
        self.old.parent.mkdir(parents=True)
        self.old.write_bytes(b'old package')
        self.source = 'a' * 40
        artifact = {'version':'1.2.3', 'os':'linux', 'arch':'x64', 'file':self.dest.name, 'bytes':11, 'sha256':digest, 'sourceCommit':self.source, 'prerelease':False, 'releaseApproved':True, 'native':'verified', 'generation':'verified', 'trust':'linux-unsigned'}
        self.artifacts = self.root / 'artifacts.json'
        self.artifacts.write_text(json.dumps({'artifacts':[artifact]}))
        self.retained = self.root / 'retained.json'
        self.retained.write_text(json.dumps({'downloads/0.1.0/old.deb': {'bytes': 11, 'sha256': hashlib.sha256(b'old package').hexdigest()}}))
        self.retained_hash = hashlib.sha256(self.retained.read_bytes()).hexdigest()
        self.inventory = self.root / 'inventory.json'
        (self.root / self.dest.name).write_bytes(b'new package')
        self.build_landing()
        self.refresh_inventory()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.marker = self.root / 'invoked'
        executable = self.bin / 'vercel'
        executable.write_text('#!/bin/sh\nprintf "%s\n" "$*" > "$MARKER"\n')
        executable.chmod(0o755)
        self.args = SimpleNamespace(payload_root=str(self.payload), payload_manifest=str(self.inventory), payload_manifest_hash=hashlib.sha256(self.inventory.read_bytes()).hexdigest(), retained_manifest=str(self.retained), artifacts=str(self.artifacts), source=self.source)
        self.patches = [patch.object(guard, 'RETAINED_HASH', self.retained_hash), patch.object(guard, 'check_identity'), patch.object(guard, 'check_remote_identity'), patch.object(guard, 'check_immutable'), patch.object(guard, 'check_new_paths'), patch.dict(os.environ, {'PATH':str(self.bin) + os.pathsep + os.environ['PATH'], 'MARKER':str(self.marker)})]
        for p in self.patches: p.start()
        self.addCleanup(lambda: [p.stop() for p in reversed(self.patches)])

    def build_landing(self, manifest=None):
        source_site = SCRIPT.parent.parent
        site_dir = self.root / 'renderer'
        if not site_dir.exists():
            site_dir.mkdir()
            for name in ('scripts', 'src', 'assets'):
                shutil.copytree(source_site / name, site_dir / name)
            for name in ('favicon.ico', 'package.json', 'tsconfig.json'):
                shutil.copyfile(source_site / name, site_dir / name)
            (site_dir / 'node_modules').symlink_to(source_site / 'node_modules', target_is_directory=True)
        env = dict(os.environ, OMR_DOWNLOADS_MANIFEST=str(manifest or self.artifacts))
        subprocess.run(['npm', 'run', 'build'], cwd=site_dir, env=env, check=True, stdout=subprocess.DEVNULL)
        for source in (site_dir / 'dist').rglob('*'):
            if source.is_file() and source.relative_to(site_dir / 'dist').parts[0] != 'downloads':
                target = self.site / source.relative_to(site_dir / 'dist')
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)

    def refresh_inventory(self):
        entries = {}
        for path in self.site.rglob('*'):
            if path.is_file():
                data = path.read_bytes()
                entries[path.relative_to(self.site).as_posix()] = {'bytes':len(data), 'sha256':hashlib.sha256(data).hexdigest()}
        self.inventory.write_text(json.dumps(entries))

    def landing_only_fixture(self):
        self.old.unlink()
        self.dest.unlink()
        self.checksum.unlink()
        items = []
        for osname, arch, extension, trust in (
            ('linux', 'x64', 'deb', 'linux-unsigned'),
            ('windows', 'x64', 'exe', 'windows-unsigned'),
            ('macos', 'x64', 'dmg', 'macos-notarized'),
            ('macos', 'arm64', 'dmg', 'macos-notarized'),
        ):
            name = f'omr-0.1.0-{osname}-{arch}.{extension}'
            data = (osname + arch).encode()
            file = self.site / 'downloads/0.1.0' / name
            file.write_bytes(data)
            digest = hashlib.sha256(data).hexdigest()
            file.with_name(name + '.sha256').write_text(f'{digest}  {name}\n')
            (self.root / name).write_bytes(data)
            items.append({'version':'0.1.0', 'os':osname, 'arch':arch, 'file':name,
                'bytes':len(data), 'sha256':digest, 'sourceCommit':self.source,
                'prerelease':False, 'releaseApproved':True, 'native':'verified',
                'generation':'verified', 'trust':trust})
        self.artifacts.write_text(json.dumps({'artifacts':items}))
        self.build_landing()
        self.refresh_inventory()
        entries = json.loads(self.inventory.read_text())
        downloads = {k:v for k,v in entries.items() if k.startswith('downloads/')}
        self.retained.write_text(json.dumps(downloads))
        self.args.payload_manifest_hash = hashlib.sha256(self.inventory.read_bytes()).hexdigest()
        self.args.landing_only = True
        return downloads

    def test_landing_only_exact_four_downloads_and_remote_bytes(self):
        downloads = self.landing_only_fixture()
        payload = self.site
        class Handler(BaseHTTPRequestHandler):
            mode = 'ok'
            def do_GET(self):
                name = self.path.lstrip('/')
                if self.mode == 'redirect':
                    self.send_response(302); self.send_header('Location', self.path); self.end_headers(); return
                if self.mode == 'missing':
                    self.send_response(404); self.end_headers(); return
                data = (payload / name).read_bytes()
                if self.mode == 'changed': data += b'x'
                self.send_response(200); self.end_headers(); self.wfile.write(data)
            def log_message(self, format, *args): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        self.addCleanup(server.server_close); self.addCleanup(thread.join); self.addCleanup(server.shutdown)
        with patch.object(guard, 'RETAINED_HASH', hashlib.sha256(self.retained.read_bytes()).hexdigest()), \
             patch.object(guard, 'ORIGIN', f'http://127.0.0.1:{server.server_port}'):
            guard.publish(self.args)
            self.assertTrue(self.marker.exists()); self.marker.unlink()
            guard.check_identity.assert_called_once_with(self.args)
            guard.check_remote_identity.assert_called_once_with(self.args)
            guard.check_immutable.assert_called_once_with(self.args)
            self.args.landing_only = False
            with self.assertRaisesRegex(ValueError, 'overlap'): guard.check_retention(self.args)
            self.args.landing_only = True
            manifest = json.loads(self.artifacts.read_text())
            self.artifacts.write_text(json.dumps({'artifacts': manifest['artifacts'][:-1]}))
            with self.assertRaisesRegex(ValueError, 'differ'): guard.check_retention(self.args)
            self.artifacts.write_text(json.dumps(manifest))
            receipt = self.retained.read_bytes()
            self.retained.write_bytes(receipt + b' ')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'): guard.check_collisions(self.args)
            self.retained.write_bytes(receipt)
            for mode in ('changed', 'redirect', 'missing'):
                Handler.mode = mode
                with self.subTest(remote=mode), self.assertRaises(ValueError): guard.publish(self.args)
                self.assertFalse(self.marker.exists())
            Handler.mode = 'ok'
            # The pinned receipt cannot be replaced, even if a new inventory matches.
            for name in downloads:
                file = self.site / name
                original = file.read_bytes(); file.write_bytes(original + b'x')
                self.refresh_inventory(); self.args.payload_manifest_hash = hashlib.sha256(self.inventory.read_bytes()).hexdigest()
                with self.subTest(local=name), self.assertRaises(ValueError): guard.publish(self.args)
                self.assertFalse(self.marker.exists()); file.write_bytes(original)
            extra = self.site / 'downloads/0.1.0/extra.deb'; extra.write_bytes(b'extra')
            self.refresh_inventory(); self.args.payload_manifest_hash = hashlib.sha256(self.inventory.read_bytes()).hexdigest()
            with self.assertRaises(ValueError): guard.publish(self.args)
            self.assertFalse(self.marker.exists())

    def test_new_catalog_keeps_new_release_gates_and_retained_bytes(self):
        old = self.old.with_name('omr-0.1.0-linux-x64.deb')
        self.old.rename(old)
        (self.root / old.name).write_bytes(old.read_bytes())
        digest = hashlib.sha256(old.read_bytes()).hexdigest()
        old.with_name(old.name + '.sha256').write_text(f'{digest}  {old.name}\n')
        new = json.loads(self.artifacts.read_bytes())['artifacts']
        historic_item = dict(new[0], version='0.1.0', file=old.name,
            sourceCommit='b'*40, prerelease=True, generation='synthetic-only', sha256=digest)
        catalog = self.root / 'catalog.json'
        catalog.write_text(json.dumps({'artifacts': [*new, historic_item]}))
        self.args.catalog = str(catalog)
        self.args.historical_manifest = str(self.root / 'historical.json')
        self.build_landing(catalog)
        self.assertIn('/downloads/0.1.0/' + old.name, (self.site / 'en/index.html').read_text())
        self.refresh_inventory()
        self.args.payload_manifest_hash = hashlib.sha256(self.inventory.read_bytes()).hexdigest()
        inventory = json.loads(self.inventory.read_bytes())
        self.retained.write_text(json.dumps({k:v for k,v in inventory.items() if k.startswith('downloads/0.1.0/')}))
        with patch.object(guard, 'RETAINED_HASH', hashlib.sha256(self.retained.read_bytes()).hexdigest()), \
             patch.object(guard, 'check_historical_identity') as historical:
            guard.publish(self.args)
            self.assertTrue(self.marker.exists()); self.marker.unlink()
            guard.check_identity.assert_called_once_with(self.args)
            guard.check_remote_identity.assert_called_once_with(self.args)
            guard.check_immutable.assert_called_once_with(self.args)
            historical.assert_called_once_with(self.args)
            paths = ['/' + self.dest.relative_to(self.site).as_posix()]
            guard.check_new_paths.assert_called_once_with(guard.ORIGIN, paths)
            for check in ('check_identity', 'check_remote_identity', 'check_historical_identity', 'check_immutable'):
                with patch.object(guard, check, side_effect=ValueError(check)):
                    with self.subTest(check=check), self.assertRaises(ValueError): guard.publish(self.args)
                self.assertFalse(self.marker.exists())
            self.args.historical_manifest = None
            with self.assertRaisesRegex(ValueError, 'historical'): guard.publish(self.args)
            self.args.historical_manifest = str(self.root / 'historical.json')
            self.args.landing_only = True
            with self.assertRaisesRegex(ValueError, 'catalog'): guard.publish(self.args)
            self.args.landing_only = False
            original = old.read_bytes(); old.write_bytes(original + b'x')
            self.refresh_inventory()
            self.args.payload_manifest_hash = hashlib.sha256(self.inventory.read_bytes()).hexdigest()
            with self.assertRaises(ValueError): guard.publish(self.args)
            self.assertFalse(self.marker.exists())

    def test_missing_landing_is_refused_before_vercel(self):
        (self.site / 'index.html').unlink()
        self.refresh_inventory()
        self.args.payload_manifest_hash = hashlib.sha256(self.inventory.read_bytes()).hexdigest()
        with self.assertRaises(ValueError): guard.publish(self.args)
        self.assertFalse(self.marker.exists())

    def test_landing_metadata_and_each_locale_are_bound_to_manifest(self):
        originals = {p: (self.site / p).read_text() for p in ('index.html', 'en/index.html', 'fr/index.html')}
        for path, old, new in (
            ('index.html', '"prerelease":false', '"prerelease":true'),
            ('en/index.html', '1.2.3', '1.2.4'),
            ('fr/index.html', self.source, 'b' * 40),
            ('en/index.html', self.dest.name, 'omr-1.2.3-linux-x64.AppImage'),
            ('fr/index.html', '"bytes":11', '"bytes":12'),
        ):
            with self.subTest(path=path, field=old):
                target = self.site / path
                self.assertIn(old, originals[path])
                target.write_text(originals[path].replace(old, new, 1))
                self.refresh_inventory()
                self.args.payload_manifest_hash = hashlib.sha256(self.inventory.read_bytes()).hexdigest()
                with self.assertRaises(ValueError): guard.publish(self.args)
                self.assertFalse(self.marker.exists())
                target.write_text(originals[path])

    def test_unexpected_vercel_route_is_refused_before_vercel(self):
        (self.site / 'vercel.json').write_text('{"rewrites":[{"source":"/","destination":"/other"}]}')
        self.refresh_inventory()
        self.args.payload_manifest_hash = hashlib.sha256(self.inventory.read_bytes()).hexdigest()
        with self.assertRaises(ValueError): guard.publish(self.args)
        self.assertFalse(self.marker.exists())

    def test_missing_release_status_is_refused_before_vercel(self):
        manifest = json.loads(self.artifacts.read_text())
        del manifest['artifacts'][0]['prerelease']
        self.artifacts.write_text(json.dumps(manifest))
        with self.assertRaises(ValueError): guard.publish(self.args)
        self.assertFalse(self.marker.exists())

    def test_project_environment_override_is_refused(self):
        with patch.dict(os.environ, {'VERCEL_PROJECT_ID': 'wrong'}):
            with self.assertRaises(ValueError): guard.publish(self.args)
        self.assertFalse(self.marker.exists())

    def test_success_executes_inert_vercel_once(self):
        guard.publish(self.args)
        self.assertEqual(self.marker.read_text(), 'deploy --prod --yes\n')

    def test_full_identity_with_signed_fixture_and_inert_vercel(self):
        self.exercise_full_identity('1.2.3')

    def test_prerelease_suffix_rejects_stable_before_inert_vercel(self):
        self.exercise_full_identity('1.2.3-rc.1')

    def exercise_full_identity(self, version):
        suffix = '-' in version
        if suffix:
            old_dest = self.dest
            self.dest = self.site / f'downloads/{version}/omr-{version}-linux-x64.deb'
            self.dest.parent.mkdir(parents=True)
            old_dest.rename(self.dest)
            self.checksum.unlink()
            self.checksum = self.dest.with_name(self.dest.name + '.sha256')
            self.checksum.write_text(f'{hashlib.sha256(self.dest.read_bytes()).hexdigest()}  {self.dest.name}\n')
            manifest = json.loads(self.artifacts.read_text())
            manifest['artifacts'][0].update(version=version, file=self.dest.name, prerelease=True)
            self.artifacts.write_text(json.dumps(manifest))
            (self.root / self.dest.name).write_bytes(b'new package')

        source_checkout = os.environ.get('OMR_PRODUCT_CHECKOUT')
        if not source_checkout: self.skipTest('set OMR_PRODUCT_CHECKOUT for cross-checkout integration')
        repo = self.root / 'product'
        repo.mkdir()
        def cmd(*args):
            return subprocess.check_output(args, cwd=repo, stderr=subprocess.DEVNULL, text=True).strip()
        cmd('git', 'init', '-q')
        for key, value in [('user.name','Test'), ('user.email','test@example.invalid'), ('commit.gpgsign','false'), ('gpg.format','ssh')]:
            cmd('git', 'config', key, value)
        cmd('ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', 'key')
        (repo / 'allowed').write_text('test@example.invalid ' + (repo / 'key.pub').read_text())
        cmd('git', 'config', 'user.signingkey', str(repo / 'key'))
        cmd('git', 'config', 'gpg.ssh.allowedSignersFile', str(repo / 'allowed'))
        (repo / 'desktop/src-tauri').mkdir(parents=True)
        (repo / 'desktop/package.json').write_text(('{"version":"1.2.3"}').replace("1.2.3", version))
        (repo / 'desktop/src-tauri/tauri.conf.json').write_text(('{"version":"1.2.3"}').replace("1.2.3", version))
        (repo / 'desktop/src-tauri/Cargo.toml').write_text(('[package]\nversion="1.2.3"\n').replace("1.2.3", version))
        cmd('git', 'add', 'desktop')
        cmd('git', 'commit', '-qm', 'fixture')
        sha = cmd('git', 'rev-parse', 'HEAD')
        annotation = self.root / 'annotation'
        annotation.write_text('Signed annotation\n')
        cmd('git', 'tag', '-s', ('desktop-v1.2.3').replace("1.2.3", version), '-F', str(annotation))
        oid = cmd('git', 'rev-parse', ('refs/tags/desktop-v1.2.3').replace("1.2.3", version))
        notes = self.root / 'release-notes'
        notes.write_text('Different GitHub notes\n')
        (repo / 'ci').mkdir()
        for name in ('desktop.py', 'release_preflight.py', 'remote_release_identity.py', 'check_immutable_releases.py'):
            shutil.copyfile(Path(source_checkout) / 'ci' / name, repo / 'ci' / name)
        manifest = json.loads(self.artifacts.read_text())
        manifest['artifacts'][0]['sourceCommit'] = sha
        self.artifacts.write_text(json.dumps(manifest))
        self.args.source = sha
        self.build_landing()
        self.refresh_inventory()
        self.args.payload_manifest_hash = hashlib.sha256(self.inventory.read_bytes()).hexdigest()
        self.args.product = str(repo)
        self.args.tag = ('desktop-v1.2.3').replace("1.2.3", version)
        self.args.tag_annotation = str(annotation)
        self.args.release_notes = str(notes)
        gh = self.bin / 'gh'
        def fake_gh(ref_oid=oid, body='Different GitHub notes\n', enabled=True, immutable=True, fail=False, prerelease=False, duplicate=False):
            ref = json.dumps({'ref':('refs/tags/desktop-v1.2.3').replace("1.2.3", version),'object':{'type':'tag','sha':ref_oid}})
            release = json.dumps({'tag_name':('desktop-v1.2.3').replace("1.2.3", version),'draft':False,'prerelease':prerelease,'immutable':immutable,'body':body})
            alternate = json.dumps([[{'ref':('refs/tags/v1.2.3').replace("1.2.3", version)}] if duplicate else []])
            matching = json.dumps([[{'ref':('refs/tags/desktop-v1.2.3').replace("1.2.3", version)}]])
            script = '#!/bin/sh\n' + ('exit 1\n' if fail else 'case "$*" in\n  *matching-refs/tags/desktop-*) printf \'%s\n\' ' + shlex.quote(matching) + ';;\n  *matching-refs/tags/*) printf \'%s\n\' ' + shlex.quote(alternate) + ';;\n  *git/ref/*) printf \'%s\n\' ' + shlex.quote(ref) + ';;\n  *releases/tags/*) printf \'%s\n\' ' + shlex.quote(release) + ';;\n  *immutable-releases) printf \'%s\n\' ' + shlex.quote(json.dumps({'enabled':enabled})) + ';;\n  *) exit 1;;\nesac\n')
            gh.write_text(script)
            gh.chmod(0o755)
        with patch.object(guard, 'check_identity', side_effect=REAL_CHECK_IDENTITY), patch.object(guard, 'check_remote_identity', side_effect=REAL_CHECK_REMOTE), patch.object(guard, 'check_immutable', side_effect=REAL_CHECK_IMMUTABLE):
            fake_gh()
            if suffix:
                manifest['artifacts'][0]['prerelease'] = False
                self.artifacts.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError, 'prerelease version cannot be stable'): guard.publish(self.args)
                self.assertFalse(self.marker.exists())
                manifest['artifacts'][0]['prerelease'] = True
                self.artifacts.write_text(json.dumps(manifest))
                fake_gh(prerelease=True)
                guard.publish(self.args)
                self.assertEqual(self.marker.read_text(), 'deploy --prod --yes\n')
                return
            guard.publish(self.args)
            self.assertEqual(self.marker.read_text(), 'deploy --prod --yes\n')
            self.marker.unlink()
            manifest = json.loads(self.artifacts.read_text())
            manifest['artifacts'][0]['prerelease'] = True
            self.artifacts.write_text(json.dumps(manifest))
            fake_gh(prerelease=True)
            with self.assertRaises(ValueError): guard.publish(self.args)
            self.assertFalse(self.marker.exists())
            self.build_landing()
            self.refresh_inventory()
            self.args.payload_manifest_hash = hashlib.sha256(self.inventory.read_bytes()).hexdigest()
            guard.publish(self.args)
            self.assertEqual(self.marker.read_text(), 'deploy --prod --yes\n')
            self.marker.unlink()
            manifest['artifacts'][0]['prerelease'] = False
            self.artifacts.write_text(json.dumps(manifest))
            cmd('git', 'tag', '-s', ('v1.2.3').replace("1.2.3", version), '-F', str(annotation))
            fake_gh()
            with self.assertRaises(ValueError): guard.publish(self.args)
            self.assertFalse(self.marker.exists())
            cmd('git', 'tag', '-d', ('v1.2.3').replace("1.2.3", version))
            for mode in ('source', 'tag', 'annotation', 'notes', 'remote-tag', 'network', 'immutable', 'mutable-release', 'prerelease-mismatch', 'duplicate'):
                fake_gh(ref_oid='b'*40 if mode == 'remote-tag' else oid, fail=mode == 'network', enabled=mode != 'immutable', immutable=mode != 'mutable-release', prerelease=mode == 'prerelease-mismatch', duplicate=mode == 'duplicate')
                self.args.source = 'c'*40 if mode == 'source' else sha
                self.args.tag = 'desktop-v1.2.4' if mode == 'tag' else ('desktop-v1.2.3').replace("1.2.3", version)
                annotation.write_text('Changed\n' if mode == 'annotation' else 'Signed annotation\n')
                notes.write_text('Changed\n' if mode == 'notes' else 'Different GitHub notes\n')
                with self.subTest(mode=mode), self.assertRaises(ValueError): guard.publish(self.args)
                self.assertFalse(self.marker.exists())

    def test_real_http_collision_and_server_error_stop_before_vercel(self):
        class Handler(BaseHTTPRequestHandler):
            status = 404
            def do_HEAD(self):
                self.send_response(self.status)
                self.end_headers()
            def log_message(self, format, *args): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join)
        self.addCleanup(server.shutdown)
        origin = f'http://127.0.0.1:{server.server_port}'
        with patch.object(guard, 'ORIGIN', origin), patch.object(guard, 'check_new_paths', side_effect=REAL_CHECK_NEW_PATHS):
            for status in (200, 500):
                Handler.status = status
                with self.subTest(status=status), self.assertRaises(ValueError): guard.publish(self.args)
                self.assertFalse(self.marker.exists())
            Handler.status = 404
            guard.publish(self.args)
            self.assertTrue(self.marker.exists())

    def test_real_immutable_reader_refuses_before_inert_vercel(self):
        product = os.environ.get('OMR_PRODUCT_CHECKOUT')
        if not product:
            self.skipTest('set OMR_PRODUCT_CHECKOUT to exercise the product reader')
        gh = self.bin / 'gh'
        gh.write_text('#!/bin/sh\nprintf \'{"enabled": false}\n\'\n')
        gh.chmod(0o755)
        self.args.product = product
        with patch.object(guard, 'check_immutable', side_effect=REAL_CHECK_IMMUTABLE):
            with self.assertRaises(ValueError): guard.publish(self.args)
        self.assertFalse(self.marker.exists())

    def test_refusals_happen_before_invocation(self):
        for stage in ('destination', 'identity', 'remote', 'immutable', 'payload', 'retained', 'collision', 'checksum', 'unlisted-download'):
            with self.subTest(stage=stage):
                if self.marker.exists(): self.marker.unlink()
                if stage == 'destination': (self.payload / '.vercel/project.json').write_text('{}')
                if stage == 'payload': self.dest.write_bytes(b'corrupt')
                if stage == 'retained':
                    self.old.write_bytes(b'altered old')
                    self.refresh_inventory()
                    self.args.payload_manifest_hash = hashlib.sha256(self.inventory.read_bytes()).hexdigest()
                if stage == 'unlisted-download':
                    (self.dest.parent / 'unexpected.deb').write_bytes(b'extra')
                    self.refresh_inventory()
                    self.args.payload_manifest_hash = hashlib.sha256(self.inventory.read_bytes()).hexdigest()
                if stage == 'checksum':
                    self.checksum.write_text('incorrect')
                    self.refresh_inventory()
                    self.args.payload_manifest_hash = hashlib.sha256(self.inventory.read_bytes()).hexdigest()
                target = {'identity':'check_identity', 'remote':'check_remote_identity', 'immutable':'check_immutable', 'collision':'check_new_paths'}.get(stage)
                ctx = patch.object(guard, target, side_effect=ValueError(stage)) if target else patch.object(guard, 'ORIGIN', guard.ORIGIN)
                with ctx:
                    with self.assertRaises(ValueError): guard.publish(self.args)
                self.assertFalse(self.marker.exists())
                (self.payload / '.vercel/project.json').write_text(json.dumps({'projectId':guard.PROJECT, 'orgId':guard.ORG}))
                self.dest.write_bytes(b'new package')
                self.old.write_bytes(b'old package')
                digest = hashlib.sha256(self.dest.read_bytes()).hexdigest()
                self.checksum.write_text(f'{digest}  {self.dest.name}\n')
                self.refresh_inventory()
                self.args.payload_manifest_hash = hashlib.sha256(self.inventory.read_bytes()).hexdigest()


if __name__ == '__main__': unittest.main()
