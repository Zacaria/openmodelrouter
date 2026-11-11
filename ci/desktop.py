"""Build-only OMR packaging checks. No credentials or release publication."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import secrets
import shutil
import struct
import subprocess
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]
TARGETS = {
    "aarch64-apple-darwin": {"os": "Darwin", "arch": "arm64", "extensions": ["dmg"]},
    "x86_64-apple-darwin": {"os": "Darwin", "arch": "x86_64", "extensions": ["dmg"]},
    "x86_64-unknown-linux-gnu": {
        "os": "Linux",
        "arch": "x86_64",
        "extensions": ["deb", "AppImage"],
    },
    "x86_64-pc-windows-msvc": {"os": "Windows", "arch": "amd64", "extensions": ["exe"]},
}
LICENSES = (
    "Bun-LICENSE.md",
    "THIRD-PARTY-NOTICES.md",
    "NPM-LICENSES.txt",
    "CPython-LICENSE.txt",
    "PyInstaller-COPYING.txt",
)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_binary(path, target):
    """Read only the executable header, not a potentially huge frozen payload."""
    with Path(path).open("rb") as stream:
        header = stream.read(64)
        arch = None
        if header.startswith(b"\x7fELF\x02\x01") and len(header) >= 20:
            if struct.unpack_from("<H", header, 18)[0] == 62:
                arch = "x86_64-unknown-linux-gnu"
        elif header[:4] == b"\xcf\xfa\xed\xfe" and len(header) >= 8:
            arch = {
                0x01000007: "x86_64-apple-darwin",
                0x0100000C: "aarch64-apple-darwin",
            }.get(struct.unpack_from("<I", header, 4)[0])
        elif header.startswith(b"MZ") and len(header) == 64:
            offset = struct.unpack_from("<I", header, 60)[0]
            require(64 <= offset <= 1024 * 1024, "invalid PE header offset")
            stream.seek(offset)
            pe = stream.read(6)
            if pe == b"PE\0\0\x64\x86":
                arch = "x86_64-pc-windows-msvc"
        require(
            arch == target,
            f"executable architecture is not {target}: {Path(path).name}",
        )


def check_replies(stdout, key):
    require(key not in stdout, "sidecar disclosed the synthetic IPC key")
    try:
        rows = [json.loads(line) for line in stdout.splitlines()]
        require(len(rows) == 3, "expected init, snapshot and shutdown replies")
        for row in rows[:2]:
            require(
                set(row) == {"ok"} and isinstance(row["ok"], dict), "sidecar IPC failed"
            )
            state = row["ok"]
            require(
                state["config"]["connections"] == [],
                "sidecar did not use isolated empty config",
            )
            require(
                type(state["port"]) is int and 0 < state["port"] < 65536,
                "sidecar did not start loopback service",
            )
        require(rows[0] == rows[1], "snapshot differs from init")
        require(rows[2] == {"ok": True}, "sidecar shutdown failed")
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("invalid sidecar IPC replies") from error


def smoke(binary, target):
    binary = Path(binary).resolve(strict=True)
    check_binary(binary, target)
    key = secrets.token_urlsafe(48)
    commands = [
        {"command": "init", "key": key},
        {"command": "snapshot"},
        {"command": "shutdown"},
    ]
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("PYTHON", "OMR_", "_PYI"))
    }
    env["PATH"] = ""
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    with tempfile.TemporaryDirectory(prefix="omr-ci-smoke-") as directory:
        result = subprocess.run(
            [str(binary), directory],
            input="".join(json.dumps(c) + "\n" for c in commands),
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=True,
            timeout=60,
            env=env,
            cwd=directory,
        )
        require(key not in result.stderr, "sidecar disclosed synthetic key on stderr")
        check_replies(result.stdout, key)
    return {
        "ipc": "pass",
        "architecture": target,
        "python_on_path": False,
        "state": "isolated-synthetic",
    }


def contract(target, root=ROOT):
    root = Path(root)
    spec = TARGETS[target]
    require(
        platform.system() == spec["os"] and platform.machine().lower() == spec["arch"],
        f"native host required for {target}",
    )
    host = subprocess.check_output(["rustc", "-vV"], text=True)
    require(
        f"host: {target}" in host.splitlines(),
        "Rust host does not match sidecar target",
    )
    for path in [
        "desktop/package-lock.json",
        "desktop/src-tauri/Cargo.lock",
        "desktop/sidecar-requirements.txt",
    ]:
        require((root / path).is_file(), f"missing app lockfile: {path}")
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", path],
            cwd=root,
            check=True,
            capture_output=True,
        )
    package = json.loads((root / "desktop/package.json").read_text(encoding="utf-8"))
    tauri = json.loads(
        (root / "desktop/src-tauri/tauri.conf.json").read_text(encoding="utf-8")
    )
    cargo = tomllib.loads(
        (root / "desktop/src-tauri/Cargo.toml").read_text(encoding="utf-8")
    )
    version = package["version"]
    require(
        re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?", version),
        "unsafe version",
    )
    require(
        version == tauri["version"] == cargo["package"]["version"],
        "app versions disagree",
    )
    require(
        package["scripts"]["native:build"] == "tauri build",
        "unexpected native build command",
    )
    require(
        all(
            name in package["scripts"]
            for name in ["check", "test", "build", "format:check"]
        ),
        "missing npm checks",
    )
    for section in ["dependencies", "devDependencies"]:
        require(
            all(
                re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", v)
                for v in package.get(section, {}).values()
            ),
            "npm dependencies must be exact versions",
        )
    require(
        tauri["build"]["beforeBuildCommand"] == "npm run build"
        and tauri["build"]["frontendDist"] == "../dist",
        "frontend build contract changed",
    )
    require(
        tauri["bundle"]["externalBin"] == ["binaries/omr-engine"],
        "unexpected sidecar bundle contract",
    )
    require(
        (root / "desktop/scripts/build_sidecar.py").is_file(),
        "missing app-owned sidecar builder",
    )
    return version


def find_bundles(base, target):
    directories = {"dmg": "dmg", "deb": "deb", "AppImage": "appimage", "exe": "nsis"}
    result = []
    for extension in TARGETS[target]["extensions"]:
        paths = list((Path(base) / directories[extension]).glob(f"*.{extension}"))
        require(
            len(paths) == 1 and paths[0].is_file() and not paths[0].is_symlink(),
            f"expected exactly one {extension} bundle",
        )
        result.append(paths[0])
    return result


def linuxdeploy_tool(tool=None):
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    tool = (
        Path(tool)
        if tool is not None
        else cache / "tauri/linuxdeploy-07333c6-x86_64.AppImage"
    )
    require(
        digest(tool)
        in {
            # Tauri CLI 2.12.4's upstream asset, and its cleared AppImage marker.
            "36a2d7e274d12e1050d0e9ecfe11d339ed54720b2bec464c286d53f8b07f5c62",
            "bd9521cd5ff3ca351fecb78cd9b236a4e37b3621014ac05cac0c2d767ffa0474",
        },
        "untrusted linuxdeploy executable",
    )
    return tool.resolve(strict=True)


def relocated_sidecar_sha256(original, tool=None):
    """Replay the pinned bundler on original bytes; never trust only working IPC."""
    tool = linuxdeploy_tool(tool)
    with tempfile.TemporaryDirectory(prefix="omr-ci-relocation-") as directory:
        work = Path(directory)
        tree = work / "Reference.AppDir"
        binary = tree / "usr/bin/omr-engine"
        binary.parent.mkdir(parents=True)
        shutil.copy2(original, binary)
        subprocess.run(
            [str(tool), "--appimage-extract-and-run", "--appdir", str(tree)],
            check=True,
            capture_output=True,
            timeout=120,
            env={
                "PATH": os.defpath,
                "HOME": directory,
                "TMPDIR": directory,
                "LC_ALL": "C",
            },
            cwd=work,
        )
        return digest(binary)


def verify_tree(tree, original, target, *, package_format=None, linuxdeploy=None):
    app_names = (
        ["omr-desktop.exe", "OMR Desktop.exe"]
        if TARGETS[target]["os"] == "Windows"
        else ["omr-desktop", "OMR Desktop"]
    )
    apps = [
        p
        for name in app_names
        for p in Path(tree).rglob(name)
        if p.is_file() and not p.is_symlink()
    ]
    require(len(apps) == 1, "expected exactly one native application executable")
    check_binary(apps[0], target)
    licenses = {}
    for filename in LICENSES:
        copies = list(Path(tree).rglob(filename))
        require(
            len(copies) == 1
            and copies[0].is_file()
            and not copies[0].is_symlink()
            and copies[0].stat().st_size > 0,
            f"missing or invalid packaged license: {filename}",
        )
        licenses[filename] = digest(copies[0])
    name = "omr-engine.exe" if TARGETS[target]["os"] == "Windows" else "omr-engine"
    paths = list(Path(tree).rglob(name))
    require(
        len(paths) == 1 and paths[0].is_file() and not paths[0].is_symlink(),
        "expected exactly one real embedded sidecar",
    )
    binary = paths[0]
    if TARGETS[target]["os"] == "Darwin":
        subprocess.run(["codesign", "--verify", "--strict", str(binary)], check=True, timeout=60)
    sha = digest(binary)
    identity = "platform-resigning"
    reference = None
    if target == "x86_64-unknown-linux-gnu" and package_format == "AppImage":
        reference = relocated_sidecar_sha256(original, linuxdeploy)
        require(sha == reference, "embedded sidecar differs from relocated reference")
        identity = "linuxdeploy-07333c6-replay"
    elif TARGETS[target]["os"] != "Darwin":
        reference = digest(original)
        require(sha == reference, "embedded sidecar differs from built sidecar")
        identity = "byte-identical"
    return {
        **smoke(binary, target),
        "identity": identity,
        "identity_reference_sha256": reference,
        "sha256": sha,
        "path": binary.relative_to(tree).as_posix(),
        "app_path": apps[0].relative_to(tree).as_posix(),
        "app_sha256": digest(apps[0]),
        "licenses": licenses,
    }


def verify_package(package, original, target):
    """Native-only extraction/install. Never runs on user machines automatically."""
    with tempfile.TemporaryDirectory(prefix="omr-ci-package-") as directory:
        work = Path(directory)
        os_name = TARGETS[target]["os"]
        if os_name == "Darwin":
            mount = work / "mount"
            mount.mkdir()
            subprocess.run(
                [
                    "hdiutil",
                    "attach",
                    "-readonly",
                    "-nobrowse",
                    "-mountpoint",
                    str(mount),
                    str(package),
                ],
                check=True,
                timeout=120,
            )
            try:
                apps = list(mount.glob("*.app"))
                require(len(apps) == 1, "expected exactly one app in DMG")
                subprocess.run(
                    ["codesign", "--verify", "--deep", "--strict", str(apps[0])],
                    check=True,
                    timeout=120,
                )
                info = verify_tree(apps[0], original, target)
                return {**info, "method": "readonly-dmg-mount"}
            finally:
                subprocess.run(
                    ["hdiutil", "detach", str(mount)], check=True, timeout=60
                )
        if os_name == "Linux":
            if package.suffix == ".deb":
                subprocess.run(
                    ["dpkg-deb", "--extract", str(package), str(work / "root")],
                    check=True,
                    timeout=120,
                )
                tree = work / "root"
                method = "deb-extract"
            else:
                package.chmod(package.stat().st_mode | 0o100)
                subprocess.run(
                    [str(package), "--appimage-extract"],
                    cwd=work,
                    check=True,
                    timeout=120,
                    capture_output=True,
                )
                tree = work / "squashfs-root"
                method = "appimage-extract"
            return {
                **verify_tree(
                    tree, original, target, package_format=package.suffix.lstrip(".")
                ),
                "method": method,
            }
        install = work / "installed"
        require(
            os.environ.get("GITHUB_ACTIONS") == "true"
            and os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted",
            "NSIS installation check requires a disposable GitHub-hosted runner",
        )
        # NSIS /D must be the last argument and is not quoted inside its value.
        subprocess.run([str(package), "/S", f"/D={install}"], check=True, timeout=180)
        try:
            return {
                **verify_tree(install, original, target),
                "method": "nsis-silent-install",
            }
        finally:
            uninstall = install / "uninstall.exe"
            if uninstall.is_file():
                subprocess.run(
                    [str(uninstall), "/S", f"_?={install}"], check=True, timeout=120
                )


def collect(target, output, root=ROOT):
    root = Path(root)
    version = contract(target, root)
    output = Path(output)
    require(not output.exists(), "artifact output must not already exist")
    suffix = ".exe" if TARGETS[target]["os"] == "Windows" else ""
    original = root / "desktop/src-tauri/binaries" / f"omr-engine-{target}{suffix}"
    smoke(original, target)
    packages = find_bundles(
        root / "desktop/src-tauri/target" / target / "release/bundle", target
    )
    rows = []
    # Verify before exposing any candidate artifacts.
    for package in packages:
        before = digest(package)
        evidence = verify_package(package.resolve(), original, target)
        require(digest(package) == before, "package changed while verifying")
        rows.append(
            {
                "name": f"OMR-Desktop-{version}-{target}.{package.suffix.lstrip('.')}",
                "sha256": before,
                "size": package.stat().st_size,
                "embedded_sidecar": evidence,
            }
        )
    source = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    require(re.fullmatch("[0-9a-f]{40}", source), "invalid source SHA")
    require(
        not subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=root,
            text=True,
        ),
        "tracked source changed during build",
    )
    output.mkdir(parents=True)
    for package, row in zip(packages, rows, strict=True):
        shutil.copy2(package, output / row["name"])
        require(digest(output / row["name"]) == row["sha256"], "copy checksum mismatch")
    report = {
        "schema": 1,
        "source_sha": source,
        "target": target,
        "version": version,
        "packages": rows,
        "built_sidecar_sha256": digest(original),
        "signing": "unqualified",
        "notarisation": "unqualified",
        "gui_launch": "not-tested",
        "provider_generation": "not-tested",
    }
    (output / "verification.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    (output / "SHA256SUMS").write_text(
        "".join(f"{row['sha256']}  {row['name']}\n" for row in rows), encoding="utf-8"
    )
    return report


def verify_download(directory, expected_source):
    require(
        re.fullmatch("[0-9a-f]{40}", expected_source),
        "expected source must be a full SHA",
    )
    manifests = list(Path(directory).rglob("verification.json"))
    require(
        len(manifests) == len(TARGETS),
        "download must contain exactly four native manifests",
    )
    reports = []
    seen = set()
    for manifest in manifests:
        report = json.loads(manifest.read_text(encoding="utf-8"))
        target = report["target"]
        require(
            report["schema"] == 1 and target in TARGETS and target not in seen,
            "invalid/duplicate target",
        )
        require(
            report["source_sha"] == expected_source,
            "download is not the reviewed composition source",
        )
        require(
            re.fullmatch(
                r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?", report["version"]
            ),
            "invalid version",
        )
        seen.add(target)
        rows = report["packages"]
        expected_names = {
            f"OMR-Desktop-{report['version']}-{target}.{ext}"
            for ext in TARGETS[target]["extensions"]
        }
        require(
            len(rows) == len(expected_names)
            and {r["name"] for r in rows} == expected_names,
            "unexpected packages",
        )
        sums = "".join(f"{row['sha256']}  {row['name']}\n" for row in rows)
        require(
            (manifest.parent / "SHA256SUMS").read_text(encoding="utf-8") == sums,
            "checksum index mismatch",
        )
        for row in rows:
            file = manifest.parent / row["name"]
            require(
                file.is_file() and not file.is_symlink(), "missing or symlinked package"
            )
            require(
                file.stat().st_size == row["size"] and digest(file) == row["sha256"],
                "package checksum mismatch",
            )
            require(
                row["embedded_sidecar"]["ipc"] == "pass", "embedded IPC not verified"
            )
        reports.append(report)
    require(
        len({r["source_sha"] for r in reports}) == 1
        and len({r["version"] for r in reports}) == 1,
        "matrix contains different source commits or versions",
    )
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ["contract", "smoke", "collect"]:
        child = sub.add_parser(command)
        child.add_argument("--target", choices=TARGETS, required=True)
        if command == "smoke":
            child.add_argument("--binary", type=Path, required=True)
        if command == "collect":
            child.add_argument("--output", type=Path, required=True)
    download = sub.add_parser("verify-download")
    download.add_argument("directory", type=Path)
    download.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    try:
        if args.command == "contract":
            result = {"version": contract(args.target)}
        elif args.command == "smoke":
            result = smoke(args.binary, args.target)
        elif args.command == "collect":
            result = collect(args.target, args.output)
        else:
            result = verify_download(args.directory, args.source_sha)
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        # Do not print captured child stdout/stderr: IPC may contain private values.
        parser.exit(1, f"CI verification failed: {type(error).__name__}: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
