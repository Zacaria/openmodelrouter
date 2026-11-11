# VM native replay — 27 October 2026

## Frozen candidate

`source.sha256` pins the launcher, tests and README used for both replays. Launcher SHA-256 `5a4b26958337bda4465c673f2d93eaa1273dfb76ec3ce246559219223f3ffcd2`; tests `59ca81aa3af3c621123906bf65e1b1f60dd418c6142f6d0f87f8c6bc8d4fe251`; README `b8cb88b901d712a11abc371f0c22eea046c999cef0ad23ad519298ac0dbfea85`. `tests.log`: eight tests pass. `red-mutation.log` records two failing tests on explicitly mutated candidate (wrong timeout code and wrong OMP context); it is not the original pre-fix RED, whose output was observed in the tool transcript but not saved here. Timeout test includes an ignoring-TERM child, group cleanup and a successful next invocation. No permissions were removed.

Fresh loopback gateway from commit `bcae37dc960bc2abaa8647aaa02a0dd0da6d72ad`, `omr.py` SHA-256 `e361c704c7790578b979e3645f70f619f94a188c6e43063bc619c290b901b568`; local Ollama alias `omr-hermes-qwen3-4b:ctx8192`, chat/responses/anthropic, effort `none`, no auth forwarding. `/api/ps` before starting was empty. Only this task's gateway and launcher processes were stopped. No paid API invoked; Claude's reported costs are estimates, not a billing observation. Synthetic fixture is `OMR_SYNTHETIC_FIXTURE=blue-otter-73`.

## Native observations

`observed/commands.jsonl` contains exact commands, exit codes, process groups and socket snapshots; `observed/config.json`, `receipts.jsonl`, stdout and stderr contain the supporting traces. `replay-observed.py` drives sequential requests; its `psutil` dependency is for evidence collection only, not the launcher. Earlier full pass is also retained in this directory.

- Hermes and Claude both actually invoked `read_file` / `Read` on turn 1, with the fixture in the tool result. A new process resumed the same native session on turn 2, recalled the fixture and made no new Read call. Both emitted native streaming events.
- With the proxy pointed at an unused local upstream port, both timed out naturally at `--run-timeout 30`, printed `OMR: run timeout exceeded; terminating process group` and exited 124, without manual termination. Claude emitted `api_retry` with `error_status: 502`; Hermes produced no native APIError or 502 text before the budget expired. The proxy's 502 response is separately exercised by `test_upstream_connection_closed_on_failure`; an explicit Hermes native APIError is **not established**. Both subsequently resumed and recalled the fixture successfully.
- In cancellation runs, each host emitted real native text before SIGINT: Hermes `type=text`, Claude `content_block_delta` with `text_delta`. Prompt requested counting to 10000; the model began with `I cannot`, so counting itself is not claimed. Each exited 130. For both, the gateway recorded a `cancelled` receipt with upstream 200, an established gateway-to-Ollama socket was observed before SIGINT and absent from the gateway's TCP descriptors afterwards; each recorded child process group had no live members after exit. Both next resumed requests succeeded and recalled the fixture. Closing a connection does **not** prove that GPU computation stopped: backend compute was not instrumented.

The operator context/output limits in README do not alter or detect backend capability. No Mac host, hosted paid route or core changes were tested here. This is VM evidence, not completion of the overall GOAL.
