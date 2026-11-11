"""Verify old payload downloads against a separately pinned manifest."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat


def check_retained(payload, manifest, manifest_hash):
    try:
        raw = Path(manifest).read_bytes()
        if not re.fullmatch(r'[0-9a-f]{64}', manifest_hash) or hashlib.sha256(raw).hexdigest() != manifest_hash:
            raise ValueError('manifest hash mismatch')
        entries = json.loads(raw)
        if not isinstance(entries, dict):
            raise ValueError('invalid manifest')
        downloads = [(name, item) for name, item in entries.items() if name.startswith('downloads/')]
        if not downloads:
            raise ValueError('no retained downloads')
        root = Path(payload)
        if not stat.S_ISDIR(root.lstat().st_mode):
            raise ValueError('payload is not a directory')
        for name, expected in downloads:
            parts = name.split('/')
            if len(parts) < 3 or any(not part or part in ('.', '..') or '\\' in part for part in parts):
                raise ValueError('unsafe path')
            if not isinstance(expected, dict) or type(expected.get('bytes')) is not int or expected['bytes'] <= 0 or not isinstance(expected.get('sha256'), str) or not re.fullmatch(r'[0-9a-f]{64}', expected['sha256']):
                raise ValueError('invalid manifest entry')
            path = root
            for index, part in enumerate(parts):
                path = path / part
                mode = path.lstat().st_mode
                if index < len(parts) - 1:
                    if not stat.S_ISDIR(mode):
                        raise ValueError('unsafe directory')
                elif not stat.S_ISREG(mode):
                    raise ValueError('not a regular file')
            with path.open('rb') as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if path.stat().st_size != expected['bytes'] or actual != expected['sha256']:
                raise ValueError('retained download differs')
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError) as error:
        raise ValueError('cannot verify retained payload') from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('payload')
    parser.add_argument('manifest')
    parser.add_argument('manifest_hash')
    args = parser.parse_args()
    try:
        check_retained(args.payload, args.manifest, args.manifest_hash)
    except ValueError as error:
        parser.exit(1, f'preflight refused: {error}\n')
    print('Retained download bytes match the pinned manifest; remote state remains unverified.')


if __name__ == '__main__':
    main()
