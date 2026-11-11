"""Fail-closed entry point for an authorized OMR Vercel publication."""
import argparse
import hashlib
import http.client
import io
import json
import tarfile
import zipfile
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import tomllib
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from check_payload_inventory import check_inventory, unique_object
from check_remote_collision import NoRedirect, check_new_paths
from check_retained_downloads import check_retained

REPO = 'Zacaria/open-model-router'
ORIGIN = 'https://open-model-router.vercel.app'
PROJECT = 'prj_2ZuPDmm7IDcBakYR51rVSqjQ9P0k'
ORG = 'team_lpN3ikyEWpXFfrV53eNYNWQd'
RETAINED_HASH = '7c029fc2f2e72cc39bdfedb0ddb36fc2dfe58b1ab9022f604cd5c62f8399f6ae'
# Original input named by the retained t_29098b54 distribution receipt.
HISTORICAL_MANIFEST_HASH = '400e488f56525b8475e4f7b18206ae5a96754ab1a90c917192ba37d6670c314e'
HISTORICAL_SOURCE = '74695fbbd290f8875dbf569254ede228bdfc4150'
HISTORICAL_TAG = 'desktop-v0.1.0-candidate.1'
HISTORICAL_TAG_OID = 'cf8d882deecdf895bcb8b63aa957dd578f77b22e'
R15_SOURCE = '6ad23212def5a9da21b2e1a6b356e95aa2411fe6'
R15_ZIP_HASH = '675f8a47b42cd318b958f9398d49f72941e1949b782e8b66f881323325f2e06f'
R15_MANIFEST_HASH = '2155a1f11d797115085cc7acc5e255b1b06fba62cd50c1c6a15461ced15ae38f'
R15_CATALOG_HASH = '0b9bbe9b2a0c417df0bd85a7ce76d0bd26eb206ca7c0e2a7456d0f53480b4265'
R15_RETAINED_HASH = '67426e8b4f3bbea075a1bfa4c59156e423db7f91537bd23cc937d0e3fb56649f'
R15_DMG_HASH = '3b630c950f95f7fae6692f80cc651090e575896d9324ccd5190a4e1623892550'
R15_DMG_BYTES = 147373192
R15_DMG_NAME = 'OMR-Desktop-0.3.2-aarch64-apple-darwin.dmg'
R15_MATERIALS_HASH = 'be5e73c9cfabf50d11ce3a8d2b9fdebf743344b5d4fc6d1a19de8668e3f51c6d'
R15_MATERIALS_BYTES = 1413120
R15_PUBLIC_SOURCE_PARTS = [
    ('https://open-model-router-materials-3.vercel.app/omr-0.3.0-macos-arm64-materials-base.tar', 601804800, '1540d6207856d38961fa1d2bee892874a7014cf3aad7821d9b69896df9ab7d48'),
    ('https://open-model-router-materials-1.vercel.app/webkit-d6375c72affe0f70222cdcb45012b10f0bf3a9d5.tar.gz.part-001', 900000000, 'cda42e9e9449ea13d0138bc4e6fa13eb7d26156c6f189d03f6451dadefba8caf'),
    ('https://open-model-router-materials-2.vercel.app/webkit-d6375c72affe0f70222cdcb45012b10f0bf3a9d5.tar.gz.part-002', 900000000, 'fbf70cabd2d3e6bc892d5fd96e6d39f8552b95fd9a3b14171ad156fde2f83e34'),
    ('https://open-model-router-materials-3.vercel.app/webkit-d6375c72affe0f70222cdcb45012b10f0bf3a9d5.tar.gz.part-003', 193631802, '5f52948eeca3bf318f1010e8e5c7333233f071baff40e0ff68856bf2d7f85d5c'),
]
R15_WEBKIT_ASSEMBLED_HASH = 'fb9d7b9bede6831ca0e7bad51f1309bcae42f0c2abcb8810688d18fa01135951'


def check_public_r15_sources():
    opener = build_opener(NoRedirect())
    combined = hashlib.sha256()
    deadline = time.monotonic() + 900
    try:
        for index, (url, expected_size, expected_hash) in enumerate(R15_PUBLIC_SOURCE_PARTS):
            if time.monotonic() >= deadline:
                raise ValueError('R15 source verification timed out')
            request = Request(url, headers={'Accept-Encoding': 'identity'})
            with opener.open(request, timeout=30) as response:
                if response.status != 200 or response.headers.get('Content-Encoding', 'identity').lower() != 'identity':
                    raise ValueError('unexpected R15 source response')
                size, part = 0, hashlib.sha256()
                while chunk := response.read(1024 * 1024):
                    if time.monotonic() >= deadline:
                        raise ValueError('R15 source verification timed out')
                    size += len(chunk)
                    if size > expected_size:
                        raise ValueError('R15 public source differs')
                    part.update(chunk)
                    if index:
                        combined.update(chunk)
                if size != expected_size or part.hexdigest() != expected_hash:
                    raise ValueError('R15 public source differs')
        if combined.hexdigest() != R15_WEBKIT_ASSEMBLED_HASH:
            raise ValueError('R15 assembled WebKit differs')
    except (HTTPError, URLError, OSError, http.client.HTTPException) as error:
        raise ValueError('cannot verify R15 public sources') from error


def check_r15_materials(args):
    path = Path(args.payload_root) / 'site/assets/materials/0.3.2/rebuild.tar'
    if path.is_symlink() or not path.is_file() or path.stat().st_size != R15_MATERIALS_BYTES:
        raise ValueError('R15 source delta missing or wrong size')
    if hashlib.sha256(path.read_bytes()).hexdigest() != R15_MATERIALS_HASH:
        raise ValueError('R15 source delta differs')
    check_public_r15_sources()


def run(*command, cwd=None):
    try:
        subprocess.run(command, cwd=cwd, check=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError('command failed') from error


def check_destination(args):
    if any(os.environ.get(name) for name in ('VERCEL_PROJECT_ID', 'VERCEL_ORG_ID')):
        raise ValueError('Vercel environment project override is not allowed')
    root = Path(args.payload_root)
    try:
        if root.is_symlink() or not root.is_dir() or {p.name for p in root.iterdir()} != {'site', '.vercel'}:
            raise ValueError('unexpected deployment root')
        linkdir = root / '.vercel'
        link = linkdir / 'project.json'
        if linkdir.is_symlink() or link.is_symlink() or not link.is_file():
            raise ValueError('invalid Vercel link')
        data = json.loads(link.read_bytes(), object_pairs_hook=unique_object)
        if data.get('projectId') != PROJECT or data.get('orgId') != ORG:
            raise ValueError('unexpected Vercel project')
    except (OSError, TypeError, AttributeError, json.JSONDecodeError) as error:
        raise ValueError('cannot validate destination') from error


def check_identity(args):
    run(sys.executable, str(Path(args.product) / 'ci/release_preflight.py'), '--source', args.source, '--tag', args.tag, '--notes', args.tag_annotation, '--manifest', args.artifacts)


def check_historical_identity(args):
    """Verify the previously distributed bytes' pinned historical provenance, not a release."""
    catalog = getattr(args, 'catalog', None)
    if catalog and getattr(args, 'landing_only', False):
        raise ValueError('catalog cannot be landing-only')
    if not catalog and (not args.landing_only or args.source != HISTORICAL_SOURCE or args.tag != HISTORICAL_TAG):
        raise ValueError('historical identity differs')
    try:
        raw = Path(args.historical_manifest).read_bytes()
        if hashlib.sha256(raw).hexdigest() != HISTORICAL_MANIFEST_HASH:
            raise ValueError('historical manifest hash mismatch')
        historic = json.loads(raw, object_pairs_hook=unique_object)
        current = json.loads(Path(catalog or args.artifacts).read_bytes(), object_pairs_hook=unique_object)
        if set(historic) != {'artifacts'} or not isinstance(historic['artifacts'], list) or len(historic['artifacts']) != 4:
            raise ValueError('invalid historical manifest')
        expected = {'artifacts': [dict(item, prerelease=True) for item in historic['artifacts']]}
        if catalog:
            fresh = json.loads(Path(args.artifacts).read_bytes(), object_pairs_hook=unique_object)
            if set(fresh) != {'artifacts'} or not isinstance(fresh['artifacts'], list) or not fresh['artifacts']:
                raise ValueError('invalid new artifact manifest')
            expected['artifacts'] = fresh['artifacts'] + expected['artifacts']
        if json.dumps(current, sort_keys=True) != json.dumps(expected, sort_keys=True) or any(item.get('sourceCommit') != HISTORICAL_SOURCE or item.get('version') != '0.1.0' for item in historic['artifacts']):
            raise ValueError('historical artifact metadata differs')
        def output(*cmd):
            return subprocess.run(cmd, cwd=args.product, check=True, capture_output=True, timeout=30).stdout
        ref = 'refs/tags/' + HISTORICAL_TAG
        if output('git', 'rev-parse', '--verify', ref).strip().decode() != HISTORICAL_TAG_OID:
            raise ValueError('historical tag object differs')
        raw_tag = output('git', 'cat-file', 'tag', ref)
        if raw_tag.split(b'\n', 2)[:2] != [f'object {HISTORICAL_SOURCE}'.encode(), b'type commit']:
            raise ValueError('historical tag target differs')
        output('git', 'verify-tag', ref)
        package = json.loads(output('git', 'show', f'{HISTORICAL_SOURCE}:desktop/package.json'))
        tauri = json.loads(output('git', 'show', f'{HISTORICAL_SOURCE}:desktop/src-tauri/tauri.conf.json'))
        cargo = tomllib.loads(output('git', 'show', f'{HISTORICAL_SOURCE}:desktop/src-tauri/Cargo.toml').decode())
        if (package['version'], tauri['version'], cargo['package']['version']) != ('0.1.0',) * 3:
            raise ValueError('historical product version differs')
        remote = json.loads(output('gh', 'api', f'repos/{REPO}/git/ref/tags/{HISTORICAL_TAG}'), object_pairs_hook=unique_object)
        if remote.get('ref') != ref or remote.get('object', {}).get('type') != 'tag' or remote['object'].get('sha') != HISTORICAL_TAG_OID:
            raise ValueError('historical remote tag differs')
    except (OSError, TypeError, KeyError, AttributeError, UnicodeError, json.JSONDecodeError, tomllib.TOMLDecodeError, subprocess.SubprocessError) as error:
        raise ValueError('cannot verify historical provenance') from error


def check_r15_identity(args):
    """Check retained R15 evidence; this is not a tag or release assertion."""
    try:
        if args.source != R15_SOURCE:
            raise ValueError('R15 source differs')
        manifest_raw = Path(args.r15_source_manifest).read_bytes()
        previous_raw = Path(args.previous_catalog).read_bytes()
        if hashlib.sha256(manifest_raw).hexdigest() != R15_MANIFEST_HASH or hashlib.sha256(previous_raw).hexdigest() != R15_CATALOG_HASH:
            raise ValueError('R15 manifest or previous catalog hash differs')
        manifest = json.loads(manifest_raw, object_pairs_hook=unique_object)
        previous = json.loads(previous_raw, object_pairs_hook=unique_object)
        fresh = json.loads(Path(args.artifacts).read_bytes(), object_pairs_hook=unique_object)
        catalog = json.loads(Path(args.catalog).read_bytes(), object_pairs_hook=unique_object)
        expected_item = {'version': '0.3.2', 'os': 'macos', 'arch': 'arm64',
            'file': 'omr-0.3.2-macos-arm64.dmg', 'bytes': R15_DMG_BYTES,
            'sha256': R15_DMG_HASH, 'sourceCommit': R15_SOURCE, 'prerelease': None,
            'releaseApproved': True, 'native': 'verified', 'generation': 'synthetic-only',
            'trust': 'macos-notarized'}
        if fresh != {'artifacts': [expected_item]} or set(previous) != {'artifacts'} or not isinstance(previous['artifacts'], list) or catalog != {'artifacts': [expected_item, *previous['artifacts']]}:
            raise ValueError('R15 artifact or catalog differs')
        if manifest['base'] != R15_SOURCE or len(manifest['files']) != 943 or set(manifest['modes']) != set(manifest['files']):
            raise ValueError('R15 source manifest differs')
        # Compare Git's actual content, without pretending its executable-bit model
        # reproduces the one retained 0600 source file's filesystem permissions.
        tree = subprocess.run(['git', '-c', 'tar.umask=0022', 'archive', '--format=tar', R15_SOURCE], cwd=args.product,
                              check=True, capture_output=True, timeout=120).stdout
        with tarfile.open(fileobj=io.BytesIO(tree), mode='r:') as tar:
            entries = {entry.name: entry for entry in tar if entry.isfile()}
            if set(entries) != set(manifest['files']):
                raise ValueError('R15 Git source paths differ')
            for name, entry in entries.items():
                mode = manifest['modes'][name]
                expected_mode = 0o644 if name == 'desktop/src/notifications.tsx' and mode == 0o600 else mode
                if entry.mode != expected_mode or hashlib.file_digest(tar.extractfile(entry), 'sha256').hexdigest() != manifest['files'][name]:
                    raise ValueError('R15 Git source content or mode differs')
        with Path(args.r15_archive).open('rb') as archive:
            if hashlib.file_digest(archive, 'sha256').hexdigest() != R15_ZIP_HASH:
                raise ValueError('R15 archive hash differs')
            archive.seek(0)
            with zipfile.ZipFile(archive) as z:
                names = z.namelist()
                if len(names) != 4 or set(names) != {'source-verification.json', 'verification.json', 'SHA256SUMS', R15_DMG_NAME}:
                    raise ValueError('R15 archive members differ')
                source = json.loads(z.read('source-verification.json'), object_pairs_hook=unique_object)
                verify = json.loads(z.read('verification.json'), object_pairs_hook=unique_object)
                if (source['source_base_commit'], source['source_manifest_sha256'], source['source_files'], source['target'], source['version']) != (R15_SOURCE, R15_MANIFEST_HASH, 943, 'aarch64-apple-darwin', '0.3.2'):
                    raise ValueError('R15 source receipt differs')
                if (verify['product_source_base_sha'], verify['product_source_manifest_sha256'], verify['target'], verify['version'], verify['packages']) != (R15_SOURCE, R15_MANIFEST_HASH, 'aarch64-apple-darwin', '0.3.2', [{'name': R15_DMG_NAME, 'size': R15_DMG_BYTES, 'sha256': R15_DMG_HASH}]):
                    raise ValueError('R15 signed receipt differs')
                if (verify['signing'], verify['notarisation'], verify['stapling'], verify['gatekeeper']) != ('developer-id-verified', 'Accepted', 'app-and-dmg-validated', 'app-and-dmg-accepted') or verify['app_notary']['status'] != 'Accepted' or verify['dmg_notary']['status'] != 'Accepted':
                    raise ValueError('R15 signing receipt differs')
                if z.read('SHA256SUMS') != f'{R15_DMG_HASH}  {R15_DMG_NAME}\n'.encode() or z.getinfo(R15_DMG_NAME).file_size != R15_DMG_BYTES:
                    raise ValueError('R15 package receipt differs')
                with z.open(R15_DMG_NAME) as dmg:
                    if hashlib.file_digest(dmg, 'sha256').hexdigest() != R15_DMG_HASH:
                        raise ValueError('R15 package differs')
    except (OSError, TypeError, KeyError, AttributeError, json.JSONDecodeError, subprocess.SubprocessError, tarfile.TarError, zipfile.BadZipFile) as error:
        raise ValueError('cannot verify R15 provenance') from error


def check_remote_identity(args):
    try:
        data = json.loads(Path(args.artifacts).read_bytes(), object_pairs_hook=unique_object)
        items = data['artifacts']
        if not isinstance(items, list) or not items or any(not isinstance(item, dict) or type(item.get('prerelease')) is not bool for item in items):
            raise ValueError('missing release status')
        status = items[0]['prerelease']
        if any(isinstance(item.get('version'), str) and '-' in item['version'] and item['prerelease'] is False for item in items):
            raise ValueError('prerelease version cannot be stable')
        if any(item['prerelease'] is not status for item in items):
            raise ValueError('mixed release status')
    except (OSError, TypeError, KeyError, json.JSONDecodeError) as error:
        raise ValueError('invalid release status') from error
    run(sys.executable, str(Path(args.product) / 'ci/remote_release_identity.py'), '--repo', REPO, '--tag', args.tag, '--release-notes', args.release_notes, '--expected-status', 'prerelease' if status else 'stable')


def check_immutable(args):
    run(sys.executable, str(Path(args.product) / 'ci/check_immutable_releases.py'), REPO)


def artifact_paths(args):
    try:
        manifest = json.loads(Path(args.artifacts).read_bytes(), object_pairs_hook=unique_object)
        if not isinstance(manifest, dict) or set(manifest) != {'artifacts'} or not isinstance(manifest['artifacts'], list) or not manifest['artifacts']:
            raise ValueError('invalid artifact manifest')
        paths = []
        for item in manifest['artifacts']:
            fields = {'version', 'os', 'arch', 'file', 'bytes', 'sha256', 'sourceCommit', 'prerelease', 'releaseApproved', 'native', 'generation', 'trust'}
            if not isinstance(item, dict) or set(item) != fields:
                raise ValueError('invalid artifact metadata')
            version, osname, arch = item['version'], item['os'], item['arch']
            extensions = {('macos', 'arm64'): ('dmg',), ('macos', 'x64'): ('dmg',), ('windows', 'x64'): ('exe', 'msi'), ('linux', 'x64'): ('deb', 'AppImage')}
            trusts = {'macos': ('macos-notarized',), 'windows': ('windows-signed', 'windows-unsigned'), 'linux': ('linux-unsigned',)}
            r15_null_status = getattr(args, 'r15_no_tag', False) and item['prerelease'] is None
            if not isinstance(version, str) or not re.fullmatch(r'[0-9A-Za-z.-]+', version) or (osname, arch) not in extensions or item['file'] not in [f'omr-{version}-{osname}-{arch}.{ext}' for ext in extensions[(osname, arch)]] or item['sourceCommit'] != args.source or (type(item['prerelease']) is not bool and not r15_null_status) or item['releaseApproved'] is not True or item['native'] != 'verified' or item['generation'] not in ('verified', 'synthetic-only') or item['trust'] not in trusts[osname] or type(item['bytes']) is not int or item['bytes'] <= 0 or not isinstance(item['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', item['sha256']):
                raise ValueError('invalid or unapproved artifact')
            path = f'downloads/{version}/{item["file"]}'
            if path in paths:
                raise ValueError('duplicate artifact')
            paths.append(path)
            file = Path(args.payload_root) / 'site' / path
            with file.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            if file.stat().st_size != item['bytes'] or digest != item['sha256']:
                raise ValueError('artifact bytes differ')
            if file.with_name(file.name + '.sha256').read_bytes() != f'{item["sha256"]}  {item["file"]}\n'.encode():
                raise ValueError('artifact checksum differs')
        return paths
    except (OSError, UnicodeError, TypeError, KeyError, json.JSONDecodeError) as error:
        raise ValueError('cannot verify artifacts') from error


def check_static_payload(args, site):
    # Regenerate in isolation: do not trust routes, scripts or CSS from the payload.
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for name in ('scripts', 'src', 'assets'):
            shutil.copytree(site / name, root / name)
        for name in ('favicon.ico', 'package.json', 'tsconfig.json'):
            shutil.copyfile(site / name, root / name)
        (root / 'node_modules').symlink_to(site / 'node_modules', target_is_directory=True)
        env = dict(os.environ)
        env.pop('OMR_DOWNLOADS_MANIFEST', None)
        env.pop('OMR_R15_SOURCE_DELTA', None)
        if getattr(args, 'r15_no_tag', False):
            env['OMR_R15_SOURCE_DELTA'] = str((Path(args.payload_root) / 'site/assets/materials/0.3.2/rebuild.tar').resolve())
        try:
            subprocess.run(['npm', 'run', 'build'], cwd=root, env=env, check=True, timeout=120, stdout=subprocess.DEVNULL)
        except (OSError, subprocess.SubprocessError) as error:
            raise ValueError('cannot rebuild static payload') from error
        expected_root = root / 'dist'
        payload = Path(args.payload_root) / 'site'
        html = {'index.html', 'en/index.html', 'fr/index.html'}
        expected = {p.relative_to(expected_root).as_posix() for p in expected_root.rglob('*') if p.is_file()} - html
        actual = {p.relative_to(payload).as_posix() for p in payload.rglob('*') if p.is_file() and not p.relative_to(payload).as_posix().startswith('downloads/')} - html
        if actual != expected or any((payload / name).read_bytes() != (expected_root / name).read_bytes() for name in expected):
            raise ValueError('static payload differs from accepted build')


def check_payload(args):
    check_inventory(Path(args.payload_root) / 'site', args.payload_manifest, args.payload_manifest_hash)
    artifact_paths(args)
    site = Path(__file__).resolve().parents[1]
    run(str(site / 'node_modules/.bin/tsx'), str(site / 'scripts/verify-landing.tsx'), str(Path(getattr(args, 'catalog', None) or args.artifacts).resolve()), str((Path(args.payload_root) / 'site').resolve()), cwd=site)
    check_static_payload(args, site)


def check_retention(args):
    retained_hash = R15_RETAINED_HASH if getattr(args, 'r15_no_tag', False) else RETAINED_HASH
    check_retained(Path(args.payload_root) / 'site', args.retained_manifest, retained_hash)
    try:
        retained = json.loads(Path(args.retained_manifest).read_bytes(), object_pairs_hook=unique_object)
        inventory = json.loads(Path(args.payload_manifest).read_bytes(), object_pairs_hook=unique_object)
        old_paths = {name for name in retained if name.startswith('downloads/')}
        new_paths = set(artifact_paths(args))
        artifact_files = new_paths | {path + '.sha256' for path in new_paths}
        if getattr(args, 'landing_only', False):
            if old_paths != artifact_files:
                raise ValueError('landing-only artifacts differ from retained downloads')
            expected = old_paths
        else:
            if old_paths & artifact_files:
                raise ValueError('new paths overlap retained downloads')
            expected = old_paths | artifact_files
        actual = {name for name in inventory if name.startswith('downloads/')}
        if actual != expected:
            raise ValueError('unexpected or missing downloads')
    except (OSError, UnicodeError, TypeError, json.JSONDecodeError) as error:
        raise ValueError('cannot compare download inventory') from error


def check_collisions(args):
    if not getattr(args, 'landing_only', False):
        paths = artifact_paths(args)
        if getattr(args, 'r15_no_tag', False):
            paths += [path + '.sha256' for path in paths]
            paths += ['assets/materials/0.3.2/', 'assets/materials/0.3.2/index.html', 'assets/materials/0.3.2/rebuild.tar']
        check_new_paths(ORIGIN, ['/' + path for path in paths])
        return
    # Authenticate the receipt again rather than trust a second unpinned read.
    raw = Path(args.retained_manifest).read_bytes()
    if hashlib.sha256(raw).hexdigest() != RETAINED_HASH:
        raise ValueError('manifest hash mismatch')
    retained = json.loads(raw, object_pairs_hook=unique_object)
    opener = build_opener(NoRedirect)
    for name, expected in retained.items():
        if not name.startswith('downloads/'):
            continue
        try:
            request = Request(ORIGIN + '/' + name, headers={'Accept-Encoding': 'identity'})
            with opener.open(request, timeout=15) as response:
                if response.status != 200 or response.headers.get('Content-Encoding', 'identity').lower() != 'identity':
                    raise ValueError('unexpected remote download response')
                digest = hashlib.sha256()
                size = 0
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > expected['bytes']:
                        raise ValueError('remote download differs')
                    digest.update(chunk)
                if size != expected['bytes'] or digest.hexdigest() != expected['sha256']:
                    raise ValueError('remote download differs')
        except (HTTPError, URLError, OSError, http.client.HTTPException) as error:
            raise ValueError('cannot verify remote download') from error


def deploy(args):
    run('vercel', 'deploy', '--prod', '--yes', cwd=args.payload_root)


def publish(args):
    historical = getattr(args, 'historical_manifest', None)
    catalog = getattr(args, 'catalog', None)
    if getattr(args, 'r15_no_tag', False):
        if historical or getattr(args, 'landing_only', False) or not all(getattr(args, name, None) for name in ('catalog', 'r15_archive', 'r15_source_manifest', 'previous_catalog')):
            raise ValueError('invalid R15 provenance arguments')
        if any(getattr(args, name, None) for name in ('tag', 'tag_annotation', 'release_notes')):
            raise ValueError('R15 does not have a tag or release')
        for check in (check_destination, check_r15_identity, check_immutable, check_payload, check_retention, check_collisions, check_r15_materials):
            check(args)
        deploy(args)
        return
    if any(getattr(args, name, None) for name in ('r15_archive', 'r15_source_manifest', 'previous_catalog')):
        raise ValueError('R15 evidence requires R15 no-tag mode')
    if catalog and not historical:
        raise ValueError('catalog requires historical manifest')
    if catalog and getattr(args, 'landing_only', False):
        raise ValueError('catalog cannot be landing-only')
    identity_checks = (check_historical_identity,) if historical and not catalog else (check_identity, check_remote_identity)
    if catalog:
        identity_checks += (check_historical_identity,)
    for check in (check_destination, *identity_checks, check_immutable, check_payload, check_retention, check_collisions):
        check(args)
    deploy(args)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('payload-root', 'payload-manifest', 'payload-manifest-hash', 'retained-manifest', 'product', 'source', 'artifacts'):
        parser.add_argument('--' + name, required=True)
    for name in ('tag', 'tag-annotation', 'release-notes', 'r15-archive', 'r15-source-manifest', 'previous-catalog'):
        parser.add_argument('--' + name)
    parser.add_argument('--r15-no-tag', action='store_true')
    parser.add_argument('--landing-only', action='store_true')
    parser.add_argument('--historical-manifest')
    parser.add_argument('--catalog')
    args = parser.parse_args()
    if not args.r15_no_tag and not all((args.tag, args.tag_annotation, args.release_notes)):
        parser.error('tag, tag-annotation and release-notes are required outside R15 no-tag mode')
    try:
        publish(args)
    except (ValueError, OSError) as error:
        parser.exit(1, f'publication refused: {error}\n')


if __name__ == '__main__':
    main()
