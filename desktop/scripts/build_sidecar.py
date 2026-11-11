"""Build the sidecar for this host; never claims cross-OS validation."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
from importlib import metadata
import certifi
from pi_ai_distribution import install_worker_requirements, prepare, select_runtime
from sidecar_notices import stage_pyinstaller_notice

root = Path(__file__).resolve().parents[2]
triple = next(
    line.split(": ", 1)[1]
    for line in subprocess.check_output(["rustc", "-vV"], text=True).splitlines()
    if line.startswith("host: ")
)
output = root / "desktop" / "src-tauri" / "binaries"
output.mkdir(parents=True, exist_ok=True)
cache = root / "desktop" / ".sidecar-build"
if "linux" in triple or "apple-darwin" in triple:
    wheelhouse = os.environ.get("OMR_WORKER_WHEELS")
    if not wheelhouse:
        raise RuntimeError("OMR_WORKER_WHEELS must name the offline locked wheelhouse")
    install_worker_requirements(sys.executable, wheelhouse)
runtime = root / "desktop" / "provider-runtime"
npm = shutil.which("npm")
if not npm:
    raise RuntimeError("npm is required on the build host, not the user machine")
subprocess.run([npm, "ci", "--no-audit", "--no-fund"], cwd=runtime, check=True)
replacement = os.environ.get("OMR_BUN_EXECUTABLE_PATH") or str(select_runtime(triple))
subprocess.run(
    [npm, "run", "build"],
    cwd=runtime,
    check=True,
    env={**os.environ, "OMR_BUN_EXECUTABLE_PATH": replacement},
)
suffix = ".exe" if os.name == "nt" else ""
natives = list(runtime.glob("pi_natives*.node"))
if len(natives) != 1:
    raise RuntimeError("Expected exactly one host-native pi-ai addon")
pi_data = []
for file in [runtime / f"omr-pi{suffix}", natives[0]]:
    pi_data += ["--add-data", f"{file}:desktop/provider-runtime"]
notices = cache / "licenses"
notices.mkdir(parents=True, exist_ok=True)
license_file = next(
    file for file in metadata.files("certifi") if file.name.upper() == "LICENSE"
)
shutil.copy2(license_file.locate(), notices / "Certifi-LICENSE.txt")
bootloader_files = metadata.files("pyinstaller")
assert bootloader_files is not None
bootloader_license = next(
    file for file in bootloader_files if file.name == "COPYING.txt"
)
stage_pyinstaller_notice(bootloader_license.locate(), notices)
if "apple-darwin" in triple:
    subprocess.run(
        ["node", str(root / "desktop/scripts/build_notices.mjs")],
        cwd=root / "desktop",
        check=True,
    )
    from sidecar_notices import collect_macos_rust, collect_python

    collect_python(notices)
    collect_macos_rust(notices, triple)
prepare(triple)
subprocess.run(
    (
        [
            sys.executable,
            "-I",
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            *pi_data,
            "--add-data",
            f"{notices}:licenses",
            "--add-data",
            f"{root / 'desktop' / 'licenses'}:licenses/runtime",
            "--add-data",
            f"{runtime / 'runtime-build.json'}:desktop/provider-runtime",
            "--add-data",
            f"{certifi.where()}:certifi",
            "--name",
            "omr-engine",
            "--distpath",
            str(cache / "dist"),
            "--workpath",
            str(cache / "work"),
            "--specpath",
            str(cache),
            str(root / "desktop_sidecar.py"),
        ]
        if "apple-darwin" not in triple
        else [
            sys.executable,
            "-I",
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--distpath",
            str(cache / "dist"),
            "--workpath",
            str(cache / "work"),
            str(root / "desktop/scripts/sidecar_macos.spec"),
        ]
    ),
    cwd=root,
    check=True,
)
suffix = ".exe" if os.name == "nt" else ""
path = output / f"omr-engine-{triple}{suffix}"
shutil.copy2(cache / "dist" / f"omr-engine{suffix}", path)
print(path)
