"""Collect complete Python notices and macOS build-input notices, with provenance."""

import hashlib
from importlib import metadata
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sysconfig

ROOT = Path(__file__).resolve().parents[2]


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def is_notice(name):
    path = PurePosixPath(str(name))
    if path.suffix.lower() in {".py", ".pyc", ".c", ".h", ".rs"}:
        return False
    return bool(
        re.match(
            r"(?i)^(licen[sc]e|copying|copyright|notice|third.?party.?notices)([._-].*)?$",
            path.name,
        )
    ) or any(p.lower() in {"licenses", "licences"} for p in path.parts[:-1])


def preserve(destination, name, raw, **identity):
    output = destination / name
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    return {**identity, "file": name, "bytes": len(raw), "sha256": sha256(raw)}


def stage_pyinstaller_notice(source, destination):
    """Preserve the installed build notice without shadowing the runtime notice."""
    shutil.copy2(source, destination / "PyInstaller-BUILD-COPYING.txt")
    (destination / "PyInstaller-COPYING.txt").unlink(missing_ok=True)


def collect_packages(destination, requirements, supplements):
    rows = []
    for name, expected in sorted(requirements.items()):
        dist = metadata.distribution(name)
        if expected is not None and dist.version != expected:
            raise ValueError(f"notice version mismatch: {name}")
        found = []
        for source in sorted(dist.files or [], key=str):
            if not is_notice(source):
                continue
            relative = PurePosixPath(str(source))
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"unsafe notice path: {source}")
            path = Path(str(dist.locate_file(source)))
            if not path.is_file():
                raise ValueError(f"missing installed notice: {source}")
            raw = path.read_bytes()
            if not raw.strip():
                raise ValueError(f"empty installed notice: {source}")
            found.append(
                preserve(
                    destination,
                    f"python/{name}/{relative}",
                    raw,
                    package=name,
                    version=dist.version,
                    source=str(source),
                )
            )
        supplement = supplements.get(name)
        if supplement:
            if supplement["version"] != dist.version:
                raise ValueError(f"supplement version mismatch: {name}")
            source = ROOT / "desktop/licenses" / supplement["file"]
            raw = source.read_bytes()
            if sha256(raw) != supplement["sha256"]:
                raise ValueError(f"supplement integrity failure: {name}")
            found.append(
                preserve(
                    destination,
                    f"python/{name}/{source.name}",
                    raw,
                    package=name,
                    version=dist.version,
                    source=supplement["source"],
                    provenance=supplement.get("provenance"),
                )
            )
        if not found:
            raise ValueError(f"missing license texts: {name}")
        rows.extend(found)
    return rows


def collect_python(destination):
    requirements = dict(
        re.findall(
            r"(?m)^([A-Za-z0-9_.-]+)==([^\s\\]+)",
            (ROOT / "desktop/s1d1-requirements.lock").read_text(),
        )
    )
    requirements.update({"certifi": None, "pyinstaller": None})
    supplements = json.loads(
        (ROOT / "desktop/licenses/sidecar-notices.lock.json").read_text()
    )
    rows = collect_packages(destination, requirements, supplements)
    license_file = Path(sysconfig.get_path("stdlib")) / "LICENSE.txt"
    if not license_file.is_file():
        # Other hosts may use the interpreter prefix instead of the stdlib root.
        candidates = list(Path(sysconfig.get_config_var("prefix")).glob("LICENSE*"))
        if not candidates:
            raise ValueError("missing CPython license")
        license_file = candidates[0]
    rows.append(
        preserve(
            destination,
            "python/CPython/LICENSE.txt",
            license_file.read_bytes(),
            package="CPython",
            version=__import__("platform").python_version(),
            source="stdlib/LICENSE.txt",
        )
    )
    (destination / "PYTHON-NOTICES.json").write_text(
        json.dumps({"schema": 1, "files": rows}, indent=2) + "\n"
    )
    return rows


def collect_macos_rust(destination, target):
    """Conservative resolved macOS graph: runtime plus build dependencies."""
    import subprocess

    graph = json.loads(
        subprocess.check_output(
            [
                "cargo",
                "metadata",
                "--locked",
                "--offline",
                "--format-version",
                "1",
                "--filter-platform",
                target,
            ],
            cwd=ROOT / "desktop/src-tauri",
            text=True,
        )
    )
    resolved = {node["id"] for node in graph["resolve"]["nodes"]}
    supplement = json.loads(
        (ROOT / "desktop/licenses/macos-rust-supplements.json").read_text()
    )
    raw = (ROOT / "desktop/licenses" / supplement["file"]).read_bytes()
    if sha256(raw) != supplement["sha256"]:
        raise ValueError("Rust notice supplement integrity failure")
    shared = preserve(
        destination,
        "rust/" + supplement["file"],
        raw,
        source="upstream source revisions in text",
    )
    rows = []
    for package in graph["packages"]:
        if package["id"] not in resolved or not package.get("source"):
            continue
        prefix = Path(package["manifest_path"]).parent
        texts = []
        for source in sorted(prefix.rglob("*")):
            if source.is_file() and is_notice(source.relative_to(prefix)):
                relative = source.relative_to(prefix).as_posix()
                texts.append(
                    preserve(
                        destination,
                        f"rust/{package['name']}-{package['version']}/{relative}",
                        source.read_bytes(),
                        source=relative,
                    )
                )
        if not texts:
            if [package["name"], package["version"]] not in supplement["packages"]:
                raise ValueError(
                    f"missing Rust notice: {package['name']} {package['version']}"
                )
            texts = [shared]
        rows.append(
            {
                "package": package["name"],
                "version": package["version"],
                "license": package["license"],
                "source": f"https://static.crates.io/crates/{package['name']}/{package['name']}-{package['version']}.crate",
                "notices": texts,
            }
        )
    toolchain = Path(
        subprocess.check_output(["rustc", "--print", "sysroot"], text=True).strip()
    )
    docs = toolchain / "share/doc/rust"
    toolchain_texts = [
        docs / "COPYRIGHT-library.html",
        *sorted((docs / "licenses").glob("*")),
    ]
    if not toolchain_texts[0].is_file() or len(toolchain_texts) < 2:
        raise ValueError("missing Rust standard-library notices")
    rust_texts = [
        preserve(
            destination,
            "rust-toolchain/" + source.relative_to(docs).as_posix(),
            source.read_bytes(),
            source=source.relative_to(docs).as_posix(),
        )
        for source in toolchain_texts
        if source.is_file()
    ]
    (destination / "RUST-NOTICES.json").write_text(
        json.dumps(
            {
                "scope": "Resolved macOS graph, conservatively including build dependencies; registry source URLs provide unmodified covered source.",
                "toolchain": subprocess.check_output(["rustc", "-vV"], text=True),
                "standard_library_notices": rust_texts,
                "packages": rows,
            },
            indent=2,
        )
        + "\n"
    )
    return rows


def collect_macos_libraries(binaries, destination):
    """Identify copied Homebrew dylibs from Analysis, not Linux wheel assumptions."""
    rows = []
    destination.mkdir(parents=True, exist_ok=True)
    choices = {
        "openssl@3": ("LICENSE.txt", "AUTHORS.md"),
        "xz": ("COPYING", "COPYING.0BSD"),
        "mpdecimal": ("COPYRIGHT.txt",),
        # SQLite's installed header preserves its public-domain dedication.
        "sqlite": ("include/sqlite3.h",),
        "python@3.13": ("LICENSE",),
    }
    for name, source, kind in binaries:
        if kind != "BINARY":
            continue
        path = Path(source).resolve()
        parts = path.parts
        if "Cellar" not in parts:
            continue
        index = parts.index("Cellar")
        formula, version = parts[index + 1 : index + 3]
        if formula not in choices:
            raise ValueError(f"unreviewed copied macOS library: {name} ({formula})")
        prefix = Path(*parts[: index + 3])
        notices = []
        for relative in choices[formula]:
            notice = prefix / relative
            if not notice.is_file():
                raise ValueError(f"missing macOS library notice: {formula}/{relative}")
            notices.append(
                preserve(
                    destination,
                    f"macos/{formula}/{relative}",
                    notice.read_bytes(),
                    package=formula,
                    version=version,
                    source=relative,
                )
            )
        rows.append(
            {
                "binary": name,
                "source_sha256": sha256(path.read_bytes()),
                "package": formula,
                "version": version,
                "notices": notices,
            }
        )
    (destination / "MACOS-LIBRARY-NOTICES.json").write_text(
        json.dumps({"schema": 1, "libraries": rows}, indent=2) + "\n"
    )
    return rows
