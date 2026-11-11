"""Construct the fixed R15 source delta from the privately verified overlay.

This does not build, sign, publish or deploy an application.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile

OVERLAY_HASH = '006d1511bcb797fabd43f14abc23c8450b810a32def2eaf8ac3fd8547450777d'
RUNTIME_MANIFEST_HASH = '2fc9f82fb8e61a923ee0d3392bb5f354a24ce25d7fdd5366af216cfefa7c6eea'
DELTA_HASH = 'be5e73c9cfabf50d11ce3a8d2b9fdebf743344b5d4fc6d1a19de8668e3f51c6d'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def make_delta(source, runtime_manifest):
    raw = Path(source).read_bytes()
    manifest_raw = Path(runtime_manifest).read_bytes()
    if digest(manifest_raw) != RUNTIME_MANIFEST_HASH:
        raise ValueError('R15 runtime manifest differs')
    reference = {name: {'bytes': item['bytes'], 'sha256': item['sha256']}
                 for name, item in sorted(json.loads(manifest_raw)['files'].items())
                 if not name.startswith('bin/')}
    if len(reference) != 774:
        raise ValueError('R15 source reference differs')
    if digest(raw) != OVERLAY_HASH:
        raise ValueError('R15 overlay differs')
    files = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as archive:
        for member in archive:
            if member.name == 'PRIVATE-PROJECTION.json':
                continue
            parts = PurePosixPath(member.name).parts
            if (not member.isfile() or not parts or parts[0] != 'pi-ai-distribution'
                    or '..' in parts or member.name.startswith('/') or member.name in files):
                raise ValueError('unsafe R15 overlay member')
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError('missing R15 overlay member')
            with stream:
                files[member.name] = stream.read()
    if len(files) != 22:
        raise ValueError('R15 overlay member count differs')
    manifest = {'schema': 1, 'version': '0.3.2', 'platform': 'macos-arm64',
                'files': {name: {'bytes': len(data), 'sha256': digest(data)}
                          for name, data in sorted(files.items())}}
    files['SOURCE-MANIFEST.json'] = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    source_reference = {'schema': 1, 'version': '0.3.2', 'platform': 'macos-arm64', 'files': reference}
    files['SOURCE-REFERENCE.json'] = (json.dumps(source_reference, indent=2, sort_keys=True) + '\n').encode()
    result = io.BytesIO()
    with tarfile.open(fileobj=result, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        for name, data in sorted(files.items()):
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.uid, info.gid, info.mtime = len(data), 0o644, 0, 0, 0
            info.uname = info.gname = ''
            archive.addfile(info, io.BytesIO(data))
    result = result.getvalue()
    if digest(result) != DELTA_HASH:
        raise ValueError('R15 source delta differs')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('overlay')
    parser.add_argument('runtime_manifest')
    parser.add_argument('output')
    args = parser.parse_args()
    data = make_delta(args.overlay, args.runtime_manifest)
    with Path(args.output).open('xb') as output:
        output.write(data)
    print(json.dumps({'sha256': digest(data), 'bytes': len(data)}))


if __name__ == '__main__':
    main()
