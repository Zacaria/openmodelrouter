#!/usr/bin/env python3
"""Build and offline-certify a source-only Git commit archive."""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
import venv

if sys.flags.optimize:
    raise SystemExit('Certification/build refuses Python -O and -OO')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_name(name):
    p = PurePosixPath(name)
    if (not name or '\\' in name or p.is_absolute() or any(x in ('', '.', '..') for x in name.split('/'))
            or re.match(r'^[A-Za-z]:', name)):
        raise ValueError('unsafe path: ' + repr(name))
    return p


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), '--no-optional-locks', *args], env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'})


def git_members(repo, revision):
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('revision must be a full lowercase commit SHA-1')
    if git(repo, 'cat-file', '-t', revision).strip() != b'commit':
        raise ValueError('revision must identify a commit')
    tree = git(repo, 'rev-parse', revision + '^{tree}').decode().strip()
    entries = git(repo, 'ls-tree', '-r', '-z', '--full-tree', revision).split(b'\0')
    members = []
    for entry in filter(None, entries):
        meta, rawname = entry.split(b'\t', 1)
        mode, kind, oid = meta.split()
        name = rawname.decode('utf-8')
        safe_name(name)
        if mode not in (b'100644', b'100755') or kind != b'blob':
            raise ValueError('non-regular Git member: ' + name)
        parts = name.lower().split('/')
        if any(p in ('.git', '__pycache__', '.venv', 'node_modules', '.env') or p.startswith('.env.') for p in parts) or name.lower().endswith(('.onnx', '.safetensors', '.bin', '.pt', '.pth', '.gguf', '.pem', '.key', '.pyc')):
            raise ValueError('forbidden cache, weight or secret-like path: ' + name)
        data = git(repo, 'cat-file', 'blob', oid.decode())
        if len(data) > 5_000_000:
            raise ValueError('oversized source: ' + name)
        members.append((name, mode == b'100755', data))
    members.sort(key=lambda x: x[0])
    return tree, members


def build(repo, revision, version, output):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', version) or version in ('.', '..'):
        raise ValueError('unsafe version')
    tree, members = git_members(repo, revision)
    out = Path(output).absolute()
    repo_path = Path(git(repo, 'rev-parse', '--show-toplevel').decode().strip()).resolve()
    if out.resolve().is_relative_to(repo_path):
        raise ValueError('output must be outside repository')
    out.mkdir(parents=False, exist_ok=False)
    archive = f'open-model-router-{version}.tar.gz'
    with (out / archive).open('xb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as gz, tarfile.open(fileobj=gz, mode='w', format=tarfile.PAX_FORMAT) as tar:
        for name, executable, data in members:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o755 if executable else 0o644
            info.uid = info.gid = info.mtime = 0
            info.uname = info.gname = ''
            tar.addfile(info, io.BytesIO(data))
    sha = digest((out / archive).read_bytes())
    manifest = {'version': version, 'commit': revision, 'tree': tree, 'archive': archive, 'sha256': sha,
                'members': [{'path': name, 'sha256': digest(data), 'mode': '100755' if executable else '100644'} for name, executable, data in members]}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')
    (out / 'SHA256SUMS').write_text(f'{sha}  {archive}\n', encoding='ascii')
    print(f'{sha}  {out / archive}')


def certify(bundle, scratch, repo, revision):
    bundle = Path(bundle)
    manifest = json.loads((bundle / 'manifest.json').read_text(encoding='utf-8'))
    tree, members = git_members(repo, revision)
    if manifest['commit'] != revision or manifest['tree'] != tree:
        raise ValueError('manifest Git identity mismatch')
    git_expected = {name: (0o755 if executable else 0o644, content) for name, executable, content in members}
    archive = manifest['archive']
    if len(safe_name(archive).parts) != 1:
        raise ValueError('invalid archive name')
    data = (bundle / archive).read_bytes()
    sha = digest(data)
    if sha != manifest['sha256'] or (bundle / 'SHA256SUMS').read_text(encoding='ascii') != f'{sha}  {archive}\n':
        raise ValueError('archive SHA256 mismatch')
    expected = {m['path']: m for m in manifest['members']}
    if len(expected) != len(manifest['members']):
        raise ValueError('duplicate manifest path')
    scratch = Path(scratch).absolute()
    if scratch.exists():
        raise ValueError('scratch must not exist')
    # Validate the entire tar before creating anything in the destination.
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as tar:
        entries = tar.getmembers()
        seen = set()
        for member in entries:
            safe_name(member.name)
            if not member.isfile() or member.name in seen or member.name not in expected:
                raise ValueError('unexpected, duplicate or non-regular tar member: ' + member.name)
            content = tar.extractfile(member).read()
            record = expected[member.name]
            if (record['mode'] not in ('100644', '100755') or digest(content) != record['sha256']
                    or member.mode != (0o755 if record['mode'] == '100755' else 0o644)
                    or member.name not in git_expected or (member.mode, content) != git_expected[member.name]):
                raise ValueError('member mismatch: ' + member.name)
            seen.add(member.name)
        if seen != set(expected) or seen != set(git_expected):
            raise ValueError('missing member')
        scratch.mkdir(parents=False)
        source = scratch / 'source'
        source.mkdir()
        for member in entries:
            target = source.joinpath(*safe_name(member.name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(tar.extractfile(member).read())
            target.chmod(member.mode)
    venv.create(scratch / 'venv', with_pip=False)
    python = scratch / 'venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    env = {'PATH': os.environ.get('PATH', ''), 'HOME': str(scratch), 'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
    commands = [[str(python), 'omr.py', '--help']]
    if any(source.glob('test*.py')):
        commands.append([str(python), '-m', 'unittest', 'discover'])
    if (source / 'host-adapters').is_dir():
        commands.append([str(python), 'host-adapters/test_launch.py'])
    if (source / 'tests' / 'test_landing.py').is_file():
        commands.append([str(python), 'tests/test_landing.py'])
    if (source / 'tests').is_dir():
        for test in sorted((source / 'tests').glob('test*.py')):
            if test.name != 'test_landing.py':
                commands.append([str(python), '-m', 'unittest', 'discover', '-s', 'tests', '-p', test.name])
    for cmd in commands:
        print('+', ' '.join(cmd), flush=True)
        subprocess.run(cmd, cwd=source, env=env, check=True)
    print('Offline certification passed; no host integration was tested.')


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action', required=True)
    b = sub.add_parser('build')
    for option in ('repo', 'revision', 'version', 'output'):
        b.add_argument('--' + option, required=True)
    c = sub.add_parser('certify')
    c.add_argument('--repo', required=True)
    c.add_argument('--revision', required=True)
    c.add_argument('--bundle', required=True)
    c.add_argument('--scratch', required=True)
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        parser.error('Python 3.11+ required')
    try:
        if args.action == 'build':
            build(args.repo, args.revision, args.version, args.output)
        else:
            certify(args.bundle, args.scratch, args.repo, args.revision)
    except (ValueError, OSError, subprocess.CalledProcessError, tarfile.TarError, KeyError) as exc:
        parser.exit(1, f'error: {exc}\n')


if __name__ == '__main__':
    main()
