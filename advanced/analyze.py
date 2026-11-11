"""Deterministic analysis of real probe files; never fills unknown usage with zero."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from advanced.claude_usage import claude_accounting


def codex_arm(arm):
    snapshots = {}
    for e in arm["native_events"]:
        if e["method"] == "thread/tokenUsage/updated":
            p = e["params"]
            snapshots[p["threadId"]] = p["tokenUsage"].get("total")
    actions = arm.get("actions", [])
    final = actions[-1] if actions else {}
    texts = [
        i.get("text", "")
        for i in final.get("items", [])
        if i.get("type") == "agentMessage"
    ]
    text = texts[-1] if texts else ""
    compacted = arm["arm"] == "compact_switch"
    return {
        "arm": arm["arm"],
        "native_status": arm["status"],
        "answer_ok": "blue-otter-73" in text
        and "HEAVY" in text
        and text.startswith("RAPPORT:"),
        "elapsed_seconds": sum(a.get("elapsed_seconds", 0) for a in actions)
        if actions
        else None,
        "thread_snapshots": snapshots,
        "snapshot_caveat": "context-reset, not full billing"
        if compacted
        else "cumulative per thread; no duplicate snapshots",
        "full_token_cost_known": bool(snapshots)
        and not compacted
        and all(child in snapshots for child in final.get("children", {})),
        "full_cost_usd": None,
        "auxiliary_compaction_cost": "unknown" if compacted else "not invoked",
    }


def claude_cases(cases, *, session_start=False):
    rows = []
    previous_by_session = {}
    for index, case in enumerate(cases):
        results = [e for e in case.get("events", []) if e.get("type") == "result"]
        result = results[0] if len(results) == 1 else {}
        sid = result.get("session_id")
        accounting = claude_accounting(
            result,
            previous_by_session.get(sid),
            session_start=session_start and index == 0,
        )
        if sid:
            previous_by_session[sid] = result
        else:
            # A missing/ambiguous action may have consumed unreported resources.
            previous_by_session.clear()
        text = result.get("result", "")
        rows.append(
            {
                "case": case["case"],
                "exit_code": case.get("exit_code"),
                "native_error": result.get("is_error"),
                "adapter_error": case.get("adapter_error"),
                "usage": result.get("usage"),
                "elapsed_ms": result.get("duration_ms"),
                "accounting": accounting,
                "fixture_and_boundary_ok": "blue-otter-73" in text and "HEAVY" in text,
                "instruction_prefix_ok": text.startswith("RAPPORT:"),
                "subagent_stats": result.get("subagent_stats"),
                "full_cost_usd": None,
                "cost_caveat": "session snapshots are cumulative; action deltas include observable auxiliary/child work; native list equivalent, not subscription billing",
            }
        )
    return rows


def omp_run(run):
    n = run["native"]
    messages = {}
    for e in n.get("events", []):
        m = e.get("message", {})
        if e.get("type") == "message_end" and m.get("role") == "assistant":
            key = m.get("responseId")
            if key:
                messages[key] = m
    rows = []
    for m in messages.values():
        text = "".join(
            b.get("text", "") for b in m.get("content", []) if b.get("type") == "text"
        )
        rows.append(
            {
                "model": m.get("model"),
                "provider": m.get("provider"),
                "usage": m.get("usage"),
                "fixture_and_boundary_ok": "blue-otter-73" in text and "HEAVY" in text,
                "instruction_prefix_ok": text.startswith("RAPPORT:"),
            }
        )
    return {
        "status": n.get("status"),
        "messages": rows,
        "compaction_observed": "compaction" in n,
        "full_cost_usd": None,
        "full_token_cost_known": False,
        "caveat": "sequential single session, not independent arms; native stats reset after compaction; auxiliary compaction usage unavailable",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", type=Path, default=Path("advanced/evidence"))
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--codex-run", default="codex-native-5/results.json")
    ap.add_argument("--omp-run", default="omp-native-rpc-6.json")
    ap.add_argument("--claude-run", default="claude-native-5/results.json")
    ap.add_argument(
        "--claude-session-start",
        action="store_true",
        help="Attest that the first Claude case starts a new synthetic UUID, not a resume",
    )
    args = ap.parse_args()

    def read(relative):
        return json.loads((args.evidence / relative).read_text())

    report = {
        "codex": [codex_arm(a) for a in read(args.codex_run)],
        "omp": omp_run(read(args.omp_run)),
        "claude": claude_cases(
            read(args.claude_run), session_start=args.claude_session_start
        ),
        "scope": "synthetic micro-project, fixed order, no general quality/cost superiority claim",
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
