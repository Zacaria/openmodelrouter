"""Run the exact OMP adapter source over authorized SSH with native auth untouched."""

import argparse
import json
import subprocess
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise SystemExit("evidence already exists; choose a new output")
    # Import the exact owned modules in memory; no native credentials or session are copied.
    script = 'import types,sys\nroot=types.ModuleType("advanced"); root.__path__=[]; sys.modules["advanced"]=root\n'
    for name in ["codex", "omp"]:
        source = Path(__file__).with_name(name + ".py").read_text()
        script += f'm=types.ModuleType("advanced.{name}"); sys.modules[m.__name__]=m; exec(compile({source!r},"advanced/{name}.py","exec"),m.__dict__)\n'
    script += Path(__file__).with_name("omp_remote_probe.py").read_text()
    command = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=8",
        "mac-worker",
        "python3 -",
    ]
    p = subprocess.run(
        command, input=script, text=True, capture_output=True, timeout=350, check=False
    )
    result = {"ssh_exit": p.returncode, "ssh_stderr": p.stderr}
    if p.returncode == 0:
        result["native"] = json.loads(p.stdout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    native = result.get("native", {})
    print(
        json.dumps(
            {
                "ssh_exit": p.returncode,
                "status": native.get("status"),
                "error": native.get("error"),
                "keys": list(native),
            },
            indent=2,
        )
    )
    if p.returncode or native.get("status") != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
