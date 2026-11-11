# Native macOS onefile build. Keep the signed Bun/addon inputs byte-identical.
from pathlib import Path
import sys
import certifi

sys.path.insert(0, str(Path(SPECPATH)))
from sidecar_notices import collect_macos_libraries

root = Path(SPECPATH).resolve().parents[1]
cache = root / "desktop/.sidecar-build"
runtime = root / "desktop/provider-runtime"
natives = list(runtime.glob("pi_natives*.node"))
if len(natives) != 1:
    raise RuntimeError("Expected exactly one host-native pi-ai addon")
pi_files = [runtime / "omr-pi", natives[0]]
a = Analysis(
    [str(root / "desktop_sidecar.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[
        *((str(file), "desktop/provider-runtime") for file in pi_files),
        (str(cache / "licenses"), "licenses"),
        (str(root / "desktop/licenses"), "licenses/runtime"),
        (str(runtime / "runtime-build.json"), "desktop/provider-runtime"),
        (certifi.where(), "certifi"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
# These notices depend on the libraries Analysis actually selected. Add them
# explicitly because the initial datas walk happened before this inventory.
collect_macos_libraries(a.binaries, cache / "licenses")
mac_notices = list((cache / "licenses/macos").rglob("*"))
mac_notices.append(cache / "licenses/MACOS-LIBRARY-NOTICES.json")
for file in mac_notices:
    if file.is_file():
        name = "licenses/" + file.relative_to(cache / "licenses").as_posix()
        a.datas = [entry for entry in a.datas if entry[0] != name]
        a.datas.append((name, str(file), "DATA"))
# Analysis reclassifies Mach-O --add-data as BINARY. EXE would then rewrite
# load commands and re-sign these independently compiled, already valid assets.
# They load only system libraries and must retain the exact build-manifest hashes.
pi_names = {"desktop/provider-runtime/" + file.name for file in pi_files}
kept = []
for name, source, kind in a.binaries:
    if name in pi_names:
        a.datas.append((name, source, "DATA"))
    else:
        kept.append((name, source, kind))
a.binaries = kept
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="omr-engine",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
