"""Opt-in synthetic source-gateway probe; OLLAMA_URL must be explicitly set."""
import http.client
import json
import os
import tempfile
import threading
import time
import uuid
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

import omr
from desktop_engine import Runtime, default_config, decider_identity

url = os.environ["OLLAMA_URL"].rstrip("/")
generator = os.environ["OMR_GENERATOR"]
with urlopen(url + "/api/version", timeout=5) as r:
    version = json.load(r)
with urlopen(url + "/api/ps", timeout=5) as r:
    loaded = json.load(r)
if loaded["models"]:
    raise SystemExit("Refusing to disturb loaded models: " + json.dumps(loaded))
key = uuid.uuid4().hex + uuid.uuid4().hex
with tempfile.TemporaryDirectory() as d:
    runtime = Runtime(Path(d), key)
    c = {"id": str(uuid.uuid4()), "name": "Synthetic live probe", "url": url + "/v1", "models": [{"id": str(uuid.uuid4()), "upstream": generator, "protocols": ["chat"], "enabled": True, "tools": True, "quality": 3, "input_price": None, "output_price": None, "effort": None}]}
    cfg = default_config()
    cfg["connections"] = [c]
    cfg["baseline"] = c["models"][0]["id"]
    cfg["decider"] = {"mode": "server", "protocol": "ollama-systemone", "connection": c["id"], "model": "d3:4b", "consent": True}
    runtime.save_config(cfg, 0, decider_identity(cfg))
    server = ThreadingHTTPServer(("127.0.0.1", 0), omr.handler({"routes": {"unused": {"url": c["url"], "model": generator, "protocol": "chat"}}, "default_route": "unused", "timeout_seconds": 120}, desktop=runtime))
    runtime.port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        request = {"model": "omr/balanced", "messages": [{"role": "user", "content": "Reply with exactly the word HELLO."}], "max_tokens": 32}
        client = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=125)
        started = time.monotonic()
        client.request("POST", "/v1/chat/completions", json.dumps(request), {"Authorization": "Bearer " + key, "Content-Type": "application/json", "X-OMR-Session": str(uuid.uuid4())})
        res = client.getresponse()
        body = json.loads(res.read())
        client.close()
        for _ in range(100):
            if runtime.rows:
                break
            time.sleep(.05)
        report = {"version": version, "generator": generator, "decider": "d3:4b", "gateway_timeout_seconds": 120, "elapsed_seconds": round(time.monotonic() - started, 3), "http_status": res.status, "response": body, "receipts": list(runtime.rows)}
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if res.status != 200 or not body.get("choices") or "HELLO" not in str(body["choices"]).upper():
            raise SystemExit("live route failed")
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
