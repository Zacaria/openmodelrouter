"""Real loopback sockets, synthetic provider; never an inference qualification."""
import contextlib
import http.client
import json
import select
import tempfile
import sys
import uuid
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import omr


@contextlib.contextmanager
def serve(handler):
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port
    finally:
        server.shutdown(); server.server_close(); thread.join(2)


class TransportTests(unittest.TestCase):
    def test_configuration_rejects_unverified_weights_and_unsafe_auth(self):
        base = {'routes': {'local': {'url': 'http://192.0.2.1/v1', 'model':'actual', 'protocol':'chat', 'forward_auth':True}}, 'default_route':'local', 'decision':{'type':'fixed'}}
        with self.assertRaises(ValueError): omr.handler(base)
        base['routes']['local']['forward_auth'] = False
        base['decision'] = {'type':'s1d1','weights':'/nonexistent','threshold':.35,'low_route':'local','high_route':'local'}
        with self.assertRaises(ValueError): omr.handler(base)

    def test_command_decides_once_per_session_and_effort_reaches_provider(self):
        seen = []
        class Backend(BaseHTTPRequestHandler):
            def log_message(self, format, *args): pass
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                seen.append((body, dict(self.headers)))
                answer = json.dumps({'model': body['model'], 'usage': {'prompt_tokens': 3}, 'choices': []}).encode()
                self.send_response(200); self.send_header('Content-Length', str(len(answer))); self.end_headers(); self.wfile.write(answer)
        with tempfile.TemporaryDirectory() as directory, serve(Backend) as upstream:
            marker = Path(directory, 'decisions.jsonl')
            command = [sys.executable, '-c', f"import sys,json; p=json.load(sys.stdin); open({str(marker)!r},'a').write(json.dumps(p)+'\\n'); print(json.dumps({{'route':'selected','usage':{{'input_tokens':2}}}}))"]
            routes = {name: {'url': f'http://127.0.0.1:{upstream}/v1', 'model': name, 'protocol': ['chat', 'responses', 'anthropic'], 'effort': 'none'} for name in ('default', 'selected')}
            config = {'routes': routes, 'default_route': 'default', 'decision': {'type':'command','command':command,'public_prompts':True}, 'receipts':str(Path(directory,'receipts.jsonl'))}
            with serve(omr.handler(config)) as gateway:
                session = str(uuid.uuid4())
                for message in ('first', 'changed difficulty'):
                    client = http.client.HTTPConnection('127.0.0.1', gateway, timeout=3)
                    client.request('POST', '/v1/chat/completions', json.dumps({'model':'open-model-router','messages':[{'role':'system','content':'HIDDEN-SYSTEM'},{'role':'user','content':message}],'reasoning_effort':'high'}), {'Content-Type':'application/json','X-OMR-Session':session,'Authorization':'Bearer DO-NOT-RELAY'})
                    response = client.getresponse()
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.getheader('X-OMR-Route'), 'selected')
                    self.assertEqual(json.load(response)['model'], 'selected')
                    client.close()
            self.assertEqual(marker.read_text().splitlines(), [json.dumps({'prompt':'first'})])
            self.assertTrue(all(body['reasoning_effort']=='none' for body, _ in seen))
            self.assertTrue(all('Authorization' not in headers for _, headers in seen))

    def test_stream_is_live_and_disconnect_aborts_stalled_upstream(self):
        closed = threading.Event()
        class Backend(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(200); self.send_header('Content-Type', 'text/event-stream'); self.end_headers()
                self.wfile.write(b'data: {"model":"actual","choices":[{"delta":{"content":"hello"}}]}\n\n'); self.wfile.flush()
                ready, _, _ = select.select([self.connection], [], [], 3)
                if ready and not self.connection.recv(1): closed.set()
        with tempfile.TemporaryDirectory() as directory, serve(Backend) as upstream:
            receipt = Path(directory, 'receipts.jsonl')
            config = {'routes': {'local': {'url': f'http://127.0.0.1:{upstream}/v1/chat/completions', 'model': 'actual', 'protocol': 'chat'}}, 'default_route': 'local', 'decision': {'type': 'fixed'}, 'timeout_seconds': 5, 'receipts': str(receipt)}
            with serve(omr.handler(config)) as gateway:
                client = http.client.HTTPConnection('127.0.0.1', gateway, timeout=2)
                client.request('POST', '/v1/chat/completions', json.dumps({'model':'open-model-router','messages':[{'role':'user','content':'PRIVATE-MARKER'}],'stream':True}), {'Content-Type':'application/json'})
                response = client.getresponse()
                self.assertEqual(response.status, 200)
                self.assertIn(b'hello', response.readline())
                response.close(); client.close()
                self.assertTrue(closed.wait(1.5), 'upstream not cancelled promptly')
                for _ in range(30):
                    if receipt.exists() and receipt.stat().st_size: break
                    time.sleep(.02)
                text = receipt.read_text()
                self.assertNotIn('PRIVATE-MARKER', text)
                row = json.loads(text)
                self.assertEqual(row['status'], 'cancelled')
                self.assertEqual(row['model_observed'], 'actual')


if __name__ == '__main__': unittest.main()
