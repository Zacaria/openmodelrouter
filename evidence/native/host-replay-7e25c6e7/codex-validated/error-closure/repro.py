"""Loopback-only receipt diagnostic against frozen gateway; no credentials or model calls."""
import http.client, json, os, select, sys, tempfile, time
from pathlib import Path
from http.server import BaseHTTPRequestHandler
from unittest.mock import patch

ROOT = Path('/srv/omr-private/workspaces/open-model-router/router-gateway')
sys.path.insert(0, str(ROOT))
import omr
from test_transport import serve

created = b'data: {"type":"response.created","response":{"id":"r"}}\n\n'
complete = b'data: {"type":"response.completed","response":{"id":"r","status":"completed","error":null}}\n\n'
mode = ['']
class Backend(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def do_GET(self):
        body = b'{"models":[{"slug":"actual","default_reasoning_level":"low","supported_reasoning_levels":[{"effort":"low"}]}]}'
        self.send_response(200); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        self.rfile.read(int(self.headers['Content-Length']))
        self.send_response(200); self.end_headers()
        self.wfile.write(created + (complete if mode[0] != 'before' else b'')); self.wfile.flush()
        if mode[0] in ('before', 'after'):
            ready, _, _ = select.select([self.connection], [], [], 3)
            assert ready and not self.connection.recv(1), 'gateway did not close upstream'
        elif mode[0] == 'truncated':
            self.wfile.write(b'data: partial'); self.wfile.flush()

headers = {'Content-Type':'application/json','X-OMR-Gateway-Key':'K'*32,'Authorization':'Bearer synthetic','chatgpt-account-id':'synthetic','session_id':'12345678-1234-4234-8234-123456789abc'}
real = http.client.HTTPConnection
with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp, serve(Backend) as upstream, patch.dict(os.environ, {'TEST_GATEWAY_KEY':'K'*32}):
    receipt = Path(tmp, 'receipts.jsonl')
    cfg = {'routes':{'native':{'url':'https://chatgpt.com/backend-api/codex','model':'actual','protocol':'responses'}},'default_route':'native','gateway_key_env':'TEST_GATEWAY_KEY','timeout_seconds':5,'receipts':str(receipt)}
    with patch.object(omr.http.client, 'HTTPSConnection', side_effect=lambda host,port,timeout:real('127.0.0.1',upstream,timeout=timeout)), serve(omr.handler(cfg)) as gateway:
        c=real('127.0.0.1',gateway,timeout=3); c.request('GET','/backend-api/codex/models',headers=headers); r=c.getresponse(); assert r.status==200; r.read(); c.close()
        for n, scenario in enumerate(('after','before','eof','truncated'), 1):
            mode[0]=scenario
            c=real('127.0.0.1',gateway,timeout=3)
            c.request('POST','/backend-api/codex/responses',json.dumps({'model':'open-model-router','stream':True}),headers)
            r=c.getresponse(); assert r.status == 200
            observed=r.read(len(created)); assert observed==created
            if scenario != 'before':
                observed += r.read(len(complete)); assert observed == created+complete
                # Actual gateway validation precedes forwarding. Independently validate the frame too.
                event=json.loads(complete[6:]); assert omr.validate_native_event(event,False,False)=='response.completed'
            if scenario in ('before','after'):
                r.close(); c.close()
            else:
                tail=r.read(); c.close()
                assert (b'event: error' in tail) == (scenario == 'truncated'), tail
            deadline=time.monotonic()+3
            while time.monotonic()<deadline:
                rows=receipt.read_text().splitlines() if receipt.exists() else []
                if len(rows)>=n: break
                time.sleep(.01)
            assert len(rows)==n, rows
            row=json.loads(rows[-1]); expected={'after':'cancelled','before':'cancelled','eof':'completed','truncated':'upstream_error'}[scenario]
            print(f'{scenario}: terminal_delivered={scenario != "before"} status={row["status"]}',flush=True)
            assert row['status']==expected, row
