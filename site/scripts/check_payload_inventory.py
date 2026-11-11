"""Verify a complete pinned static payload inventory; not a publication gate."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate manifest key')
        result[key] = value
    return result


def check_inventory(payload, manifest, manifest_hash):
    try:
        raw = Path(manifest).read_bytes()
        if not re.fullmatch(r'[0-9a-f]{64}', manifest_hash) or hashlib.sha256(raw).hexdigest() != manifest_hash:
            raise ValueError('manifest hash mismatch')
        entries = json.loads(raw, object_pairs_hook=unique_object)
        if not isinstance(entries, dict) or not entries:
            raise ValueError('empty or invalid inventory')
        root = Path(payload)
        if not stat.S_ISDIR(root.lstat().st_mode):
            raise ValueError('payload root is not a directory')
        actual = set()
        for directory, directories, files in os.walk(root, followlinks=False, onerror=lambda error: (_ for _ in ()).throw(error)):
            for name in directories:
                if not stat.S_ISDIR((Path(directory) / name).lstat().st_mode):
                    raise ValueError('unsafe directory')
            for name in files:
                path = Path(directory) / name
                if not stat.S_ISREG(path.lstat().st_mode):
                    raise ValueError('unsafe file')
                actual.add(path.relative_to(root).as_posix())
        if actual != set(entries):
            raise ValueError('payload paths differ from inventory')
        for name, entry in entries.items():
            if not isinstance(name, str) or any(not part or part in ('.', '..') for part in name.split('/')) or '\\' in name or any(ord(c) < 32 for c in name):
                raise ValueError('unsafe inventory path')
            if not isinstance(entry, dict) or set(entry) != {'bytes', 'sha256'} or type(entry['bytes']) is not int or entry['bytes'] < 0 or not isinstance(entry['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', entry['sha256']):
                raise ValueError('invalid inventory entry')
            path = root / name
            with path.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            if path.stat().st_size != entry['bytes'] or digest != entry['sha256']:
                raise ValueError('payload bytes differ from inventory')
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError) as error:
        raise ValueError('cannot verify payload inventory') from error
