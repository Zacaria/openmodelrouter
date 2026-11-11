"""Real integrated native replay, synthetic context only; explicit quota consent.

OMR_NATIVE_REPLAY_CONSENT=1 python desktop/scripts/replay_native_strategies.py
Set OMR_TEST_ENGINE to exercise the frozen sidecar instead of source.
No account details, prompts, replies or raw native errors are persisted.
"""

import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]


def main():
    if os.environ.get("OMR_NATIVE_REPLAY_CONSENT") != "1":
        raise SystemExit(
            "Set OMR_NATIVE_REPLAY_CONSENT=1 to use the existing native subscription with synthetic tasks."
        )
    results = []
    receipts = []
    evidence = Path(
        os.environ.get(
            "OMR_NATIVE_EVIDENCE", ROOT / "desktop/.evidence/native-strategies.json"
        )
    )
    evidence.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="omr-integrated-") as directory:
        engine = os.environ.get("OMR_TEST_ENGINE")
        argv = (
            [engine]
            if engine
            else [sys.executable, "-B", str(ROOT / "desktop_sidecar.py")]
        )
        env = {
            k: os.environ[k]
            for k in ("TMPDIR", "LANG", "SystemRoot", "WINDIR")
            if k in os.environ
        }
        env["PATH"] = "/nonexistent"
        process = subprocess.Popen(
            argv + [directory],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            env=env,
        )
        input_stream, output_stream = process.stdin, process.stdout
        assert input_stream is not None and output_stream is not None
        selector = selectors.DefaultSelector()
        selector.register(output_stream, selectors.EVENT_READ)

        def send(request):
            input_stream.write(json.dumps(request) + "\n")
            input_stream.flush()
            if not selector.select(10):
                raise AssertionError("private IPC did not respond within ten seconds")
            line = output_stream.readline()
            if not line:
                raise AssertionError("sidecar exited unexpectedly")
            return json.loads(line)

        def snapshot():
            return send({"command": "snapshot"})["ok"]

        def action(**request):
            return send({"command": "native", "request": request})

        def check(name, condition):
            if not condition:
                raise AssertionError(name)
            results.append(name)
            print("PASS", name, flush=True)

        def wait():
            deadline = time.monotonic() + 155
            while time.monotonic() < deadline:
                s = snapshot()
                if not s["native"]["active"]:
                    return s
                time.sleep(0.15)
            raise AssertionError("native operation deadline")

        try:
            s = send({"command": "init", "key": "synthetic-private-ipc-key-" * 3})["ok"]
            original = s["config"]
            check(
                "no automatic native session", s["native"]["status"] == "disconnected"
            )
            check(
                "permission refusal before process launch",
                action(action="connect", consent=False).get("error")
                == "consent_required",
            )
            action(
                action="connect",
                consent=True,
                instructions="Answer in French with each final response starting exactly RAPPORT:.",
                context="Public synthetic fixture BLUE-OWL-42. Required tag HEAVY. Do not authorize other tools.",
            )
            s = wait()
            check(
                "new isolated native subscription session connected",
                s["native"]["status"] == "ready" and not s["native"]["error"],
            )
            models = s["native"]["models"]
            target = (
                "gpt-6-luna"
                if "gpt-6-luna" in models
                else next(m for m in models if m != s["native"]["model"])
            )
            check(
                "unknown model refused before native turn",
                action(action="switch", model="NOT-ADVERTISED", prompt="synthetic").get(
                    "error"
                )
                == "native_model_unavailable",
            )
            for name, request in [
                (
                    "maintain",
                    {
                        "prompt": "For this session, answer in French starting exactly RAPPORT:. Call read_context exactly once. Reply with the fixture and required tag. Do not use other tools."
                    },
                ),
                (
                    "switch",
                    {
                        "model": target,
                        "prompt": "Without tools, repeat the fixture and required tag from the previous tool result.",
                    },
                ),
                ("compact", {}),
                (
                    "recall_after_compact",
                    {
                        "prompt": "Without tools, repeat the fixture and required tag from our history."
                    },
                ),
                (
                    "delegate",
                    {
                        "prompt": "Delegate exactly once to a native child. Give it BLUE-OWL-42 and HEAVY, ask it to return them without tools. Wait, integrate the result and close it. Preserve the RAPPORT: response prefix."
                    },
                ),
            ]:
                action(
                    action="maintain" if name == "recall_after_compact" else name,
                    **request,
                )
                s = wait()
                row = s["receipts"][-1]
                check(
                    name + " native completion",
                    row["status"] == "completed" and not s["native"]["error"],
                )
                if name != "compact":
                    check(
                        name + " synthetic recall and instructions",
                        "BLUE-OWL-42" in s["native"]["reply"]
                        and "HEAVY" in s["native"]["reply"]
                        and s["native"]["reply"].startswith("RAPPORT:"),
                    )
                if name == "maintain":
                    check(
                        "native context tool completion observed",
                        "dynamicToolCall" in row["native"]["event_types"],
                    )
                if name == "switch":
                    check(
                        "switch model confirmed by native thread read",
                        row["model_observed"] == target,
                    )
                if name == "compact":
                    check(
                        "native compaction item observed",
                        "contextCompaction" in row["native"]["event_types"],
                    )
                if name == "delegate":
                    check(
                        "exactly one native child completed",
                        row["native"]["completed_children"] == 1,
                    )
            baseline = s["native"]["events"].get("turn/started", 0)
            action(
                action="maintain",
                prompt="Think through and list 200 distinct synthetic alphabet ordering exercises in full. Do not use tools.",
            )
            deadline = time.monotonic() + 20
            while (
                snapshot()["native"]["events"].get("turn/started", 0) <= baseline
                and time.monotonic() < deadline
            ):
                time.sleep(0.05)
            check(
                "normal quit refuses active native work",
                send({"command": "shutdown", "force": False}).get("error")
                == "requests_active",
            )
            action(action="cancel")
            s = wait()
            check(
                "native interrupted terminal not just interrupt acknowledgement",
                s["receipts"][-1]["status"] == "cancelled",
            )
            action(
                action="maintain",
                prompt="Without tools, return BLUE-OWL-42 HEAVY with our required prefix.",
            )
            s = wait()
            check(
                "resume after interruption",
                s["receipts"][-1]["status"] == "completed"
                and "BLUE-OWL-42" in s["native"]["reply"],
            )
            check("direct API configuration untouched", s["config"] == original)
            receipts = s["receipts"]
            exported = send({"command": "export_receipts"})["ok"]
            check(
                "no synthetic transcript in receipt export",
                "BLUE-OWL-42" not in exported and "HEAVY" not in exported,
            )
            check(
                "unknown costs never zeroed or added to API usage",
                all(
                    r["native"]["auxiliary_cost_usd"] is None
                    and r["native"]["actual_billed_usd"] is None
                    and r["usage"] == {}
                    for r in receipts
                ),
            )
            action(action="close")
            s = wait()
            check(
                "close clears in-memory session and reply",
                s["native"]["status"] == "disconnected" and not s["native"]["reply"],
            )
        finally:
            try:
                receipts = snapshot()["receipts"]
                send({"command": "shutdown", "force": True})
            finally:
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                selector.close()
                input_stream.close()
                output_stream.close()
                evidence.write_text(
                    json.dumps(
                        {
                            "engine": "frozen" if engine else "source",
                            "checks": results,
                            "receipts": receipts,
                            "limitations": [
                                "Synthetic context only",
                                "Sequential paths, not independent cost comparison arms",
                                "Auxiliary usage and subscription invoice unknown",
                                "Other hosts unavailable, not qualified by this replay",
                            ],
                        },
                        indent=2,
                    )
                    + "\n"
                )
    print("Evidence:", evidence)


if __name__ == "__main__":
    main()
