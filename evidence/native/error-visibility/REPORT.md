# Adapter error visibility

Baseline: three SHA-256 hashes match the GO review at `/srv/omr-private/workspaces/open-model-router/host-adapter-review.md`. Only `host-adapters/launch.py`, `test_launch.py`, and `README.md` changed; final hashes are in `source.sha256`.

The proxy emits only `OMR: upstream HTTP error <numeric status>` for upstream HTTP >=400, or 502 on failure before upstream headers. It does not print response bodies, headers, URLs, tokens or exception text. This is adapter stderr, not a native Hermes APIError. Existing response forwarding and timeout behavior remain unchanged.

`red.log` records the socket/captured-stderr test failing on the reviewed launcher; `green.log` records all nine tests passing after the change. The socket test checks 503 and connection-refused 502 with secret-bearing body, header, URL and authorization, requiring exact stderr lines.

`replay.json`, `hermes.stderr`, and `hermes.stdout` record a real Hermes CLI invocation against a bound-but-not-listening loopback port, with a 30-second runtime budget. It emitted adapter 502 messages, exited 124 after 30.37 seconds, and its observed child process group 3256201 had no live members after exit. No model generation or paid API was used. This does not claim a native Hermes APIError.
