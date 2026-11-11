"""Compare the Linux frozen candidate to source and embedded pi-ai inputs.

Run with the build interpreter (PyInstaller installed) after native qualification.
Absolute co_filename paths are normalized; all other code metadata is compared.
"""

from pathlib import Path
import hashlib
import importlib.metadata
import json
import marshal
import platform
import types
from PyInstaller.archive.readers import CArchiveReader

root = Path(__file__).resolve().parents[2]
binary = root / "desktop/src-tauri/binaries/omr-engine-x86_64-unknown-linux-gnu"
archive = CArchiveReader(str(binary))
pyz = archive.open_embedded_archive("PYZ.pyz")


def normalized(value):
    if isinstance(value, types.CodeType):
        return {
            "name": value.co_name,
            "qualname": value.co_qualname,
            "code": value.co_code.hex(),
            "consts": [normalized(c) for c in value.co_consts],
            "names": value.co_names,
            "varnames": value.co_varnames,
            "freevars": value.co_freevars,
            "cellvars": value.co_cellvars,
            "nlocals": value.co_nlocals,
            "stacksize": value.co_stacksize,
            "argcount": value.co_argcount,
            "posonly": value.co_posonlyargcount,
            "kwonly": value.co_kwonlyargcount,
            "flags": value.co_flags,
            "firstlineno": value.co_firstlineno,
            "linetable": value.co_linetable.hex(),
            "exceptiontable": value.co_exceptiontable.hex(),
        }
    if isinstance(value, tuple):
        return [normalized(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, bytes):
        return {"bytes": value.hex()}
    if isinstance(value, frozenset):
        return {"frozenset": sorted(repr(v) for v in value)}
    return {"repr": repr(value)}


modules = {}
for module in (
    "desktop_sidecar",
    "desktop_engine",
    "desktop_managed",
    "desktop_deciders",
    "desktop_pi",
    "desktop_native",
    "jev_decider",
    "omr",
):
    path = root / f"{module}.py"
    packaged = (
        marshal.loads(archive.extract(module))
        if module == "desktop_sidecar"
        else pyz.extract(module)
    )
    current = compile(path.read_bytes(), path.name, "exec", optimize=0)
    assert normalized(packaged) == normalized(current), module + " frozen source drift"
    modules[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
assert not any(
    "model_int8.onnx" in name or "vocab_map.npy" in name for name in archive.toc
), "downloaded model weights must not be embedded"
embedded = {}
for path in [
    root / "desktop/provider-runtime/omr-pi",
    *list((root / "desktop/provider-runtime").glob("pi_natives*.node")),
]:
    member = "desktop/provider-runtime/" + path.name
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    actual = hashlib.sha256(archive.extract(member)).hexdigest()
    assert expected == actual, member
    embedded[member] = actual
assert len(embedded) == 2, "expected bridge and exactly one host-native addon"
report = {
    "sidecar_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
    "source_module_sha256": modules,
    "embedded_pi_sha256": embedded,
    "weights_embedded": False,
    "app_sha256": hashlib.sha256(
        (root / "desktop/src-tauri/target/release/omr-desktop").read_bytes()
    ).hexdigest(),
    "frontend": {
        str(p.relative_to(root / "desktop/dist")): hashlib.sha256(
            p.read_bytes()
        ).hexdigest()
        for p in (root / "desktop/dist").rglob("*")
        if p.is_file()
    },
    "ignored_filenames_only": "co_filename is normalized; all other source code/line/exception metadata matches",
    "build_python": platform.python_version(),
    "build_packages": {
        name: importlib.metadata.version(name)
        for name in ("numpy", "tokenizers", "onnxruntime", "PyInstaller", "certifi")
    },
}
out = root / "desktop/.evidence/onboarding-qualified/artifact-integrity.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2))
print(
    json.dumps(
        {
            "sidecar_sha256": report["sidecar_sha256"],
            "app_sha256": report["app_sha256"],
            "source_modules_matched": len(modules),
            "pi_entries_matched": len(embedded),
            "frontend_files": len(report["frontend"]),
            "weights_embedded": False,
            "report": str(out),
        },
        indent=2,
    )
)
