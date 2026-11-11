"""Explicitly download hash-pinned s1d1 files; never replace existing files."""
import argparse
import hashlib
import os
import tempfile
from pathlib import Path
from urllib.request import urlopen
from omr import S1D1_FILES as FILES

REPOSITORY = 'scombat/s1d1-router-6src-tiny-onnx-int8'
REVISION = 'dac13b5c0356864ea4501fa151d74dcd8b3ea22a'


def download(directory):
    directory = Path(directory)
    if directory.is_symlink():
        raise ValueError('weight directory must not be a symlink')
    directory.mkdir(parents=True, exist_ok=True)
    for name, expected in FILES.items():
        target = directory / name
        if target.is_symlink():
            raise ValueError('weight files must not be symlinks')
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
                raise ValueError('existing weight hash mismatch: ' + name)
            continue
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=directory, prefix='.download-', delete=False) as out:
                temporary = Path(out.name)
                digest = hashlib.sha256(); size = 0
                with urlopen(f'https://huggingface.co/{REPOSITORY}/resolve/{REVISION}/{name}', timeout=60) as response:
                    while chunk := response.read(1024*1024):
                        size += len(chunk)
                        if size > 40_000_000:
                            raise ValueError('weight size limit')
                        out.write(chunk); digest.update(chunk)
            if digest.hexdigest() != expected:
                raise ValueError('download hash mismatch: ' + name)
            # Hard-link installation is atomic and refuses a concurrent existing target.
            os.link(temporary, target)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return directory


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    print(download(args.directory))
