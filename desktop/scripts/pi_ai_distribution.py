"""Prepare pinned runtime sources; never publishes or claims native OS qualification."""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sysconfig
import tarfile
import tempfile
import tomllib
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check_integrity(item, path):
    if "sha256" in item:
        return digest(path) == item["sha256"]
    algorithm, expected = item["integrity"].split("-", 1)
    if algorithm != "sha512":
        raise ValueError("unsupported source integrity algorithm")
    with path.open("rb") as stream:
        actual = base64.b64encode(
            hashlib.file_digest(stream, algorithm).digest()
        ).decode()
    return actual == expected


def verified_source(item, cache):
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    name = item["file"]
    if Path(name).name != name or name in (".", ".."):
        raise ValueError("unsafe source filename")
    path = cache / name
    if not path.exists():
        partial = path.with_name(path.name + ".partial")
        try:
            if "git_archive" in item:
                # GitHub refuses source archives of this exact WebKit revision (422).
                # Fetch source as a build input, without a project clone/worktree.
                with tempfile.TemporaryDirectory(
                    prefix="source-git-", dir=cache
                ) as directory:
                    subprocess.run(
                        ["git", "init", "--bare", directory],
                        check=True,
                        stdout=subprocess.DEVNULL,
                    )
                    subprocess.run(
                        [
                            "git",
                            "-C",
                            directory,
                            "fetch",
                            "--depth=1",
                            item["git_archive"]["repository"],
                            item["revision"],
                        ],
                        check=True,
                    )
                    revision = subprocess.check_output(
                        ["git", "-C", directory, "rev-parse", "FETCH_HEAD"], text=True
                    ).strip()
                    if revision != item["revision"]:
                        raise ValueError("source revision integrity failure")
                    subprocess.run(
                        [
                            "git",
                            "-C",
                            directory,
                            "archive",
                            "--format=tar.gz",
                            f"--prefix={item['git_archive']['prefix']}",
                            "-o",
                            str(partial.resolve()),
                            revision,
                        ],
                        check=True,
                    )
            else:
                with urllib.request.urlopen(item["url"], timeout=180) as response:
                    with partial.open("wb") as stream:
                        shutil.copyfileobj(response, stream)
            if not check_integrity(item, partial):
                raise ValueError(f"source integrity failure: {name}")
            partial.replace(path)
        finally:
            partial.unlink(missing_ok=True)
    if path.is_symlink() or not check_integrity(item, path):
        raise ValueError(f"source integrity failure: {name}")
    return path


def archive_notices(path):
    """Preserve license files and source-header grants with upstream attribution."""
    notices = {}
    with tarfile.open(path, "r|gz") as archive:
        for member in archive:
            if not member.isfile():
                continue
            parts = PurePosixPath(member.name).parts
            whole = bool(
                re.match(
                    r"(?i)^(licen[sc]e|copying|copyright|notice|third.party.notices)([._-].*)?$",
                    parts[-1],
                )
            )
            whole = whole or any(
                p.lower() in ("licenses", "licences") for p in parts[:-1]
            )
            header = PurePosixPath(member.name).suffix.lower() in (
                ".h",
                ".hh",
                ".hpp",
                ".c",
                ".cc",
                ".cpp",
                ".cxx",
                ".m",
                ".mm",
                ".rs",
                ".zig",
                ".js",
                ".jsx",
                ".ts",
                ".tsx",
            )
            if not whole and not header:
                continue
            stream = archive.extractfile(member)
            assert stream is not None
            text = stream.read().decode("utf-8", errors="replace")
            texts = [text] if whole else []
            if not whole:
                # Read complete leading comments, including consecutive grants.
                # Do not truncate a license at a fixed header byte limit.
                position = 1 if text.startswith("\ufeff") else 0
                start, end = None, 0
                while match := re.compile(
                    r"\s*(/\*.*?\*/|//[^\n]*(?:\n[ \t]*//[^\n]*)*)", re.DOTALL
                ).match(text, position):
                    if start is None and re.search(
                        r"copyright|licen[sc]e|permission", match[1], re.I
                    ):
                        start = match.start(1)
                    end = position = match.end()
                # Conditions/disclaimers may be separate comments without any
                # license keyword. Keep the entire header from its first grant.
                if start is not None:
                    texts.append(text[start:end])
            for text in texts:
                if text.strip():
                    notices.setdefault(text, []).append(member.name)
    return (
        "\n\n".join(
            f"Sources: {', '.join(names)}\n{text}"
            for text, names in sorted(notices.items(), key=lambda pair: pair[1][0])
        )
        + "\n"
    )


def bun_mit_notice(lock, cache):
    """Pair Bun's declaration with the pinned standard text, not invented authorship."""
    item = lock["bun_mit_terms"]
    path = verified_source(item, cache)
    return path, (
        "\n=== Bun: declared MIT license / complete standard terms ===\n"
        "Upstream declaration: https://github.com/oven-sh/bun/blob/"
        f"{lock['bun_revision']}/LICENSE.md\n"
        f"Standard text source: {item['url']}\nSHA-256: {item['sha256']}\n"
        "The standard text's <year> and <copyright holders> are unchanged template "
        "placeholders, not a Bun copyright attribution. Actual upstream copyright "
        "and per-file grants are preserved with their source paths below.\n\n"
        + path.read_text(encoding="utf-8")
        + "\n"
    )


def safe_file(root, name):
    relative = PurePosixPath(name)
    if relative.is_absolute() or ".." in relative.parts or "\\" in name or ":" in name:
        raise ValueError("unsafe manifest path")
    # macOS TemporaryDirectory uses /var -> /private/var. Canonicalize only
    # the selected root's parents; still reject a linked root or linked material.
    root = Path(root)
    if root.is_symlink():
        raise ValueError(f"missing regular material: {name}")
    path = root.resolve() / relative
    if not path.is_file() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError(f"missing regular material: {name}")
    return path


def write_manifest(root, metadata, files):
    entries = {
        name: {
            "sha256": digest(safe_file(root, name)),
            "bytes": (root / name).stat().st_size,
        }
        for name in sorted(files)
    }
    (root / "manifest.json").write_text(
        json.dumps({"schema": 1, **metadata, "files": entries}, indent=2) + "\n"
    )


def verify_manifest(root):
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest.get("schema") != 1 or not manifest.get("files"):
        raise ValueError("missing manifest entries")
    for name, entry in manifest["files"].items():
        path = safe_file(root, name)
        if path.stat().st_size != entry["bytes"] or digest(path) != entry["sha256"]:
            raise ValueError(f"material integrity failure: {name}")
    return manifest


def make_kit(root, output):
    manifest = verify_manifest(root)
    partial = output.with_name(output.name + ".partial")
    try:
        with tarfile.open(partial, "w", format=tarfile.PAX_FORMAT) as archive:
            for name in sorted(["manifest.json", *manifest["files"]]):
                path = safe_file(root, name)
                info = tarfile.TarInfo("omr-pi-ai/" + name)
                info.size = path.stat().st_size
                info.mode = 0o755 if name.startswith("bin/") else 0o644
                with path.open("rb") as stream:
                    archive.addfile(info, stream)
        partial.replace(output)
    finally:
        partial.unlink(missing_ok=True)
    return output


def host_target():
    return next(
        line.split(": ", 1)[1]
        for line in subprocess.check_output(["rustc", "-vV"], text=True).splitlines()
        if line.startswith("host: ")
    )


def source_lock():
    return json.loads((ROOT / "desktop/licenses/pi-ai-sources.lock.json").read_text())


def source_cache():
    return Path(
        os.environ.get(
            "OMR_PI_SOURCE_CACHE", ROOT / "desktop/.sidecar-build/distribution-cache"
        )
    ).resolve()


def select_runtime(target):
    lock = source_lock()
    item = lock["runtimes"][target]
    cache = source_cache()
    archive = verified_source(item, cache)
    output = cache / target / ("bun.exe" if "windows" in target else "bun")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zipped:
        matches = [x for x in zipped.infolist() if x.filename == item["member"]]
        if len(matches) != 1:
            raise ValueError("missing unique pinned Bun executable")
        data = zipped.read(matches[0])
    if not output.exists() or output.read_bytes() != data:
        output.write_bytes(data)
    output.chmod(0o755)
    revision = subprocess.check_output([str(output), "--revision"], text=True).strip()
    if revision != lock["bun_version"] + "+" + lock["bun_revision"][:9]:
        raise ValueError("Bun executable/source revision integrity failure")
    return output


def archive_texts(path, wanted):
    result = {}
    with tarfile.open(path, "r|gz") as archive:
        for member in archive:
            relative = member.name.split("/", 1)[-1]
            if member.isfile() and wanted(relative):
                stream = archive.extractfile(member)
                assert stream is not None
                result[relative] = stream.read().decode("utf-8")
    return result


def verify_upstream_pins(lock, paths):
    """Refuse a dependency bump that silently leaves old corresponding sources."""
    bun = archive_texts(
        paths["bun"], lambda p: p == "Cargo.lock" or p.startswith("scripts/build/deps/")
    )
    items = {i["id"]: i for i in lock["archives"]}
    for name, recipe in bun.items():
        repo = re.search(r'repo: "([^"]+)"', recipe)
        commit = re.search(r'const \w+_COMMIT = "([a-f0-9]{40})"', recipe)
        if repo and commit:
            key = PurePosixPath(name).stem
            if (
                items.get(key, {}).get("url")
                != f"https://codeload.github.com/{repo[1]}/tar.gz/{commit[1]}"
            ):
                raise ValueError(f"missing corresponding dependency source: {key}")
    if items["webkit"]["revision"] not in bun["scripts/build/deps/webkit.ts"]:
        raise ValueError("WebKit source revision integrity failure")
    for crate in tomllib.loads(bun["Cargo.lock"])["package"]:
        if "source" not in crate:
            continue
        key = f"crate:{crate['name']}:{crate['version']}"
        if items.get(key, {}).get("sha256") != crate.get("checksum"):
            raise ValueError(f"missing corresponding Rust source: {key}")
    icu = json.loads(
        archive_texts(paths["webkit"], lambda p: p == "icu/source.json")[
            "icu/source.json"
        ]
    )
    if (
        items["icu"]["sha256"] != icu["sha256"]
        or f"icu4c-{icu['version']}-sources.tgz" != items["icu"]["file"]
    ):
        raise ValueError("ICU source revision integrity failure")


def verify_engine_payload(engine, runtime, notice):
    from PyInstaller.archive.readers import CArchiveReader

    build = json.loads((runtime / "runtime-build.json").read_text())
    archive = CArchiveReader(str(engine))
    expected = {
        "desktop/provider-runtime/"
        + build["output"]["file"]: runtime / build["output"]["file"],
        "desktop/provider-runtime/"
        + build["native"]["file"]: runtime / build["native"]["file"],
        "desktop/provider-runtime/runtime-build.json": runtime / "runtime-build.json",
        "licenses/PI-AI-NOTICES.txt": notice,
    }
    for name, source in expected.items():
        if name not in archive.toc or hashlib.sha256(
            archive.extract(name)
        ).hexdigest() != digest(source):
            raise ValueError(f"frozen payload integrity failure: {name}")


def verify_worker_corresponding_sources():
    """Do not emit a composed kit before native-wheel source closure is established."""
    raise ValueError("worker corresponding source provenance is not established")


def worker_wheels(wheelhouse, lockfile):
    """Require one exact locked wheel per worker dependency, with no extras."""
    from packaging.utils import canonicalize_name, parse_wheel_filename

    text = Path(lockfile).read_text(encoding="utf-8")
    headers = list(re.finditer(r"(?m)^([A-Za-z0-9_.-]+)==([^\s;\\]+)[^\n]*$", text))
    required = {}
    for index, header in enumerate(headers):
        name = canonicalize_name(header.group(1))
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        hashes = set(
            re.findall(r"--hash=sha256:([a-f0-9]{64})", text[header.start() : end])
        )
        if name in required or not hashes:
            raise ValueError(f"invalid worker requirement: {name}")
        required[name] = (header.group(2), hashes)
    if not required:
        raise ValueError("empty worker requirements lock")
    paths = sorted(Path(wheelhouse).glob("*.whl"))
    seen = set()
    for path in paths:
        name, version, _, _ = parse_wheel_filename(path.name)
        name = canonicalize_name(name)
        if (
            path.is_symlink()
            or name not in required
            or name in seen
            or str(version) != required[name][0]
            or digest(path) not in required[name][1]
        ):
            raise ValueError(f"worker wheel integrity failure: {path.name}")
        seen.add(name)
    if seen != required.keys():
        raise ValueError("incomplete worker wheelhouse")
    return paths


def install_worker_requirements(python, wheelhouse):
    """Install only locked, hash-verified wheels into the actual build interpreter."""
    uv = shutil.which("uv")
    wheelhouse = Path(wheelhouse).resolve()
    if not uv or not wheelhouse.is_dir():
        raise RuntimeError("uv and the offline worker wheelhouse are required")
    subprocess.run(
        [
            uv,
            "pip",
            "install",
            "--python",
            str(python),
            "--no-index",
            "--find-links",
            str(wheelhouse),
            "--only-binary",
            ":all:",
            "--require-hashes",
            "--reinstall",
            "-r",
            str(ROOT / "desktop/s1d1-requirements.lock"),
        ],
        check=True,
    )


def strict_carchive_reader():
    """Reject duplicate members before PyInstaller's reader collapses its TOC."""
    import struct
    from PyInstaller.archive.readers import CArchiveReader

    class StrictReader(CArchiveReader):
        @classmethod
        def _parse_toc(cls, data):
            seen = set()
            pos = 0
            while pos < len(data):
                if len(data) - pos < cls._TOC_ENTRY_LENGTH:
                    raise ValueError("invalid frozen table of contents")
                size, _, _, _, _, kind = struct.unpack_from(
                    cls._TOC_ENTRY_FORMAT, data, pos
                )
                if size <= cls._TOC_ENTRY_LENGTH or pos + size > len(data):
                    raise ValueError("invalid frozen table of contents")
                raw = data[pos + cls._TOC_ENTRY_LENGTH : pos + size]
                name = raw.rstrip(b"\0").decode("utf-8")
                if "\0" in name:
                    raise ValueError("invalid frozen member name")
                if kind != b"o":
                    if name in seen:
                        raise ValueError(f"duplicate frozen member: {name}")
                    seen.add(name)
                pos += size
            return super()._parse_toc(data)

    return StrictReader


def verify_numpy_link(archive, name, wheel, wheel_sha256):
    """Validate one exact relative link and its wheel-identical target."""
    import zipfile

    if "/" in name or "\\" in name or name in ("", ".", ".."):
        raise ValueError("invalid NumPy library name")
    target = "numpy.libs/" + name
    if (
        archive.toc.get(name, (None,) * 5)[4] != "n"
        or archive.extract(name) != (target + "\0").encode()
    ):
        raise ValueError(f"invalid NumPy library link: {name}")
    if archive.toc.get(target, (None,) * 5)[4] != "b":
        raise ValueError(f"invalid NumPy library target: {target}")
    if digest(wheel) != wheel_sha256:
        raise ValueError("NumPy wheel integrity failure")
    with zipfile.ZipFile(wheel) as zipped:
        matches = [info for info in zipped.infolist() if info.filename == target]
        if (
            len(matches) != 1
            or matches[0].is_dir()
            or zipped.read(matches[0]) != archive.extract(target)
        ):
            raise ValueError(f"NumPy library wheel integrity failure: {target}")
    return True


def linux_libraries(engine, numpy_wheel=None, numpy_sha256=None):
    """Bind Debian libraries to the host and NumPy links to a locked wheel."""
    archive = strict_carchive_reader()(str(engine))
    entries = []
    for name in sorted(archive.toc):
        if "/" in name or ".so" not in name:
            continue
        if archive.toc[name][4] == "n":
            if numpy_wheel is None or numpy_sha256 is None:
                raise ValueError("NumPy wheel required for shared-library link")
            verify_numpy_link(archive, name, numpy_wheel, numpy_sha256)
            continue
        origin = Path("/usr/lib") / sysconfig.get_config_var("MULTIARCH") / name
        origin = origin.resolve()
        if not origin.is_file() or hashlib.sha256(
            archive.extract(name)
        ).hexdigest() != digest(origin):
            raise ValueError(f"copied shared-library origin integrity failure: {name}")
        owner = (
            subprocess.check_output(["dpkg-query", "-S", str(origin)], text=True)
            .strip()
            .rsplit(": ", 1)[0]
        )
        values = subprocess.check_output(
            [
                "dpkg-query",
                "-W",
                "-f=${binary:Package}\\t${Version}\\t${source:Package}\\t${source:Version}",
                owner,
            ],
            text=True,
        ).split("\t")
        package, version, source, source_version = values
        copyright_file = Path("/usr/share/doc") / package.split(":")[0] / "copyright"
        if not copyright_file.is_file():
            raise ValueError(f"missing copied-library copyright: {package}")
        entries.append(
            {
                "file": name,
                "sha256": digest(origin),
                "package": package,
                "version": version,
                "source": source,
                "source_version": source_version,
                "copyright": str(copyright_file),
            }
        )
    return entries


def engine_rebuild_inputs(root):
    return [
        "desktop_sidecar.py",
        "desktop_engine.py",
        "desktop_managed.py",
        "desktop_deciders.py",
        "desktop_pi.py",
        "desktop_native.py",
        "desktop_subscriptions.py",
        "desktop_portal.py",
        "desktop/provider-runtime/subscriptions.ts",
        "jev_decider.py",
        "omr.py",
        "requirements-s1d1.txt",
        "desktop/s1d1-requirements.lock",
    ] + [
        p.relative_to(root).as_posix() for p in sorted((root / "advanced").glob("*.py"))
    ]


def prepare(target, engine=None):
    lock = source_lock()
    runtime = ROOT / "desktop/provider-runtime"
    cache = source_cache()
    destination = ROOT / "desktop/.sidecar-build/pi-ai-distribution"
    destination.mkdir(parents=True, exist_ok=True)
    # A failed preparation must never leave an old accepted manifest.
    (destination / "manifest.json").unlink(missing_ok=True)
    files = []

    def include(source, name):
        output = destination / name
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            output.unlink()
        if name.startswith("sources/"):
            try:
                os.link(source, output)
            except OSError:
                shutil.copy2(source, output)
        else:
            shutil.copy2(source, output)
        files.append(name)

    runtime_archive = verified_source(lock["runtimes"][target], cache)
    include(runtime_archive, "sources/" + runtime_archive.name)
    paths = {}
    for item in lock["archives"]:
        path = verified_source(item, cache)
        paths[item["id"]] = path
        include(path, "sources/" + item["file"])
    verify_upstream_pins(lock, paths)
    notice_parts = [
        "OMR provider runtime uses Bun 1.4.4, statically linked JavaScriptCore/WebKit "
        "(GNU Library GPL v2 and per-file terms) and TinyCC (LGPL 2.1 text; per-file v2-or-later grants). "
        "Pinned library source archives, build recipes and bridge inputs accompany this kit. "
        "Modification for your own use and reverse engineering to debug those modifications "
        "are permitted for this runtime; OMR imposes no contrary restriction. "
        "Upstream terms and disclaimers below remain applicable.\n"
        "The complete standard MIT terms identified by Bun's root LICENSE.md "
        "declaration follow with their pinned provenance. Per-file grants remain "
        "authoritative; this kit is not a public-release approval.\n"
    ]
    mit_source, mit_notice = bun_mit_notice(lock, cache)
    include(mit_source, "sources/" + mit_source.name)
    notice_parts.append(mit_notice)
    for item in lock["archives"]:
        notice_parts.append(
            f"\n=== {item['id']} / {item['file']} ===\n"
            + archive_notices(paths[item["id"]])
        )
    npm_lock = json.loads((runtime / "package-lock.json").read_text())
    if npm_lock["packages"]["node_modules/bun"]["version"] != lock["bun_version"]:
        raise ValueError("Bun npm/source version integrity failure")
    npm_sources = []
    for location, entry in npm_lock["packages"].items():
        if not location or entry.get("dev") or entry.get("devOptional"):
            continue
        installed = runtime / location
        if not installed.exists():
            if not entry.get("optional"):
                raise ValueError(f"missing runtime dependency: {location}")
            continue
        name = location.removeprefix("node_modules/").replace("/", "-").replace("@", "")
        item = {
            "file": f"npm-{name}-{entry['version']}.tgz",
            "url": entry["resolved"],
            "integrity": entry["integrity"],
        }
        path = verified_source(item, cache)
        # Prove the compiler read the source supplied in the material, not a dirty npm tree.
        with tarfile.open(path) as archive:
            for member in archive:
                if not member.isfile():
                    continue
                relative = member.name.split("/", 1)[-1]
                file = safe_file(installed, relative)
                stream = archive.extractfile(member)
                assert stream is not None
                if file.read_bytes() != stream.read():
                    raise ValueError(
                        f"npm installed-source integrity failure: {location}/{relative}"
                    )
        include(path, "sources/" + item["file"])
        npm_sources.append({**item, "location": location})
        notice_parts.append(
            f"\n=== {location} @ {entry['version']} ===\n" + archive_notices(path)
        )
    notice = destination / "PI-AI-NOTICES.txt"
    notice.write_text("\n".join(notice_parts), encoding="utf-8")
    files.append(notice.name)
    for name in (
        "bridge.ts",
        "build.mjs",
        "build_target.mjs",
        "package.json",
        "package-lock.json",
        "tsconfig.json",
    ):
        include(runtime / name, "rebuild/desktop/provider-runtime/" + name)
    for name in engine_rebuild_inputs(ROOT):
        include(ROOT / name, "rebuild/" + name)
    for name in (
        "desktop/scripts/build_sidecar.py",
        "desktop/scripts/sidecar_notices.py",
        "desktop/scripts/sidecar_macos.spec",
        "desktop/scripts/pi_ai_distribution.py",
        "desktop/sidecar-requirements.txt",
        "desktop/PI-AI-DISTRIBUTION.md",
        "desktop/licenses/pi-ai-sources.lock.json",
        "desktop/licenses/sidecar-notices.lock.json",
        "desktop/licenses/macos-rust-supplements.json",
        "desktop/licenses/Tokenizers-0.23.3-sources.json",
    ):
        include(ROOT / name, "rebuild/" + name)
    for path in sorted((ROOT / "desktop/licenses").glob("*")):
        if path.is_file() and path.suffix != ".json":
            include(path, "licenses/" + path.name)
            include(path, "rebuild/desktop/licenses/" + path.name)
    include(ROOT / "desktop/THIRD-PARTY-NOTICES.md", "licenses/THIRD-PARTY-NOTICES.md")
    include(
        ROOT / "desktop/THIRD-PARTY-NOTICES.md",
        "rebuild/desktop/THIRD-PARTY-NOTICES.md",
    )
    generated_notices = ROOT / "desktop/.sidecar-build/licenses"
    for path in sorted(generated_notices.rglob("*")):
        if path.is_file() and path.name not in {"PI-AI-NOTICES.txt", "PI-AI-MATERIALS.json"}:
            include(path, "licenses/" + path.relative_to(generated_notices).as_posix())
    build = json.loads((runtime / "runtime-build.json").read_text())
    if build["target"] + ".zip" != lock["runtimes"][target]["file"]:
        raise ValueError("runtime build target integrity failure")
    if build["bridge_sha256"] != digest(runtime / "bridge.ts") or build[
        "lock_sha256"
    ] != digest(runtime / "package-lock.json"):
        raise ValueError("bridge build input integrity failure")
    for entry in (build["output"], build["native"]):
        path = safe_file(runtime, entry["file"])
        if digest(path) != entry["sha256"]:
            raise ValueError("bridge build output integrity failure")
        include(path, "bin/" + entry["file"])
    include(runtime / "runtime-build.json", "runtime-build.json")
    libraries = []
    if engine is not None:
        verify_engine_payload(engine, runtime, notice)
        include(Path(engine).resolve(), "bin/" + Path(engine).name)
        if "linux" in target:
            wheelhouse = os.environ.get("OMR_WORKER_WHEELS")
            if not wheelhouse:
                raise ValueError("OMR_WORKER_WHEELS must name the locked wheelhouse")
            for wheel in worker_wheels(
                wheelhouse, ROOT / "desktop/s1d1-requirements.lock"
            ):
                include(wheel, "wheels/" + wheel.name)
            numpy_item = lock["numpy_linux_wheel"]
            requirement = (ROOT / "desktop/s1d1-requirements.lock").read_text()
            match = re.search(
                r"(?ms)^numpy==2\.5\.4\s*\\\n(.*?)(?=^[a-zA-Z0-9][^\n]*==|\Z)",
                requirement,
            )
            if match is None or "--hash=sha256:" + numpy_item[
                "sha256"
            ] not in match.group(1):
                raise ValueError("NumPy wheel not pinned by worker requirements lock")
            numpy_wheel = verified_source(numpy_item, cache)
            include(numpy_wheel, "sources/" + numpy_wheel.name)
            libraries = linux_libraries(engine, numpy_wheel, numpy_item["sha256"])
            verify_worker_corresponding_sources()
            corresponding = lock["linux_corresponding_sources"]
            gcc = [e for e in libraries if e["file"].startswith(("libgcc_", "libobjc"))]
            if any(
                (e["source"], e["source_version"])
                != (corresponding["source_package"], corresponding["source_version"])
                for e in gcc
            ):
                raise ValueError(
                    "copied GCC library corresponding-source version is not pinned for this host"
                )
            for item in corresponding["files"]:
                include(verified_source(item, cache), "sources/" + item["file"])
            for entry in libraries:
                name = (
                    "licenses/linux/"
                    + entry["package"].replace(":", "-")
                    + "-copyright.txt"
                )
                if name not in files:
                    include(Path(entry["copyright"]), name)
            for path in sorted(Path("/usr/share/common-licenses").iterdir()):
                if path.is_file() and not path.is_symlink():
                    include(path, "licenses/linux/common/" + path.name)
    metadata = {
        "target": target,
        "copied_linux_libraries": libraries,
        "bun_revision": lock["bun_revision"],
        "npm_sources": npm_sources,
        "qualification": {
            "runtime_source_rebuild": "not_exercised",
            "public_distribution": "not_approved",
            "other_operating_systems": "not_qualified_by_this_build",
        },
    }
    write_manifest(destination, metadata, files)
    verify_manifest(destination)
    notices = ROOT / "desktop/.sidecar-build/licenses"
    notices.mkdir(parents=True, exist_ok=True)
    shutil.copy2(notice, notices / notice.name)
    shutil.copy2(destination / "manifest.json", notices / "PI-AI-MATERIALS.json")
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("runtime", "prepare", "kit", "verify"))
    parser.add_argument("--target")
    parser.add_argument("--engine", type=Path)
    parser.add_argument("--directory", type=Path)
    args = parser.parse_args()
    if args.command == "verify":
        if args.directory is None:
            parser.error("--directory is required")
        manifest = verify_manifest(args.directory)
        print(
            json.dumps(
                {
                    "verified_files": len(manifest["files"]),
                    "target": manifest.get("target"),
                }
            )
        )
        return
    target = args.target or host_target()
    if target != host_target():
        parser.error(
            "only the current host target may be prepared; native qualification is separate"
        )
    if args.command == "runtime":
        print(select_runtime(target))
    else:
        if args.command == "kit" and (not args.engine or "linux" not in target):
            parser.error("kit requires a native Linux target and --engine")
        directory = prepare(target, args.engine)
        if args.command == "kit":
            output = make_kit(directory, directory.parent / f"omr-pi-ai-{target}.tar")
            print(
                json.dumps(
                    {
                        "kit": str(output),
                        "sha256": digest(output),
                        "bytes": output.stat().st_size,
                    }
                )
            )
        else:
            print(directory)


if __name__ == "__main__":
    main()
