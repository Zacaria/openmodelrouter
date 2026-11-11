import json
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from pathlib import Path


class GatewayTest(unittest.TestCase):
    def test_fixed_chat_passes_tools_and_upstream_identity(self):
        seen = []
        class Upstream(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                seen.append((self.path, json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
                body = json.dumps({'model': 'real-model', 'choices': [{'message': {'tool_calls': [{'id': 'one'}]}}]}).encode()
                self.send_response(200); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
        server = HTTPServer(('127.0.0.1', 0), Upstream)
        Thread(target=server.serve_forever, daemon=True).start()
        with tempfile.TemporaryDirectory() as d:
            config = {'routes': {'local': {'url': f'http://127.0.0.1:{server.server_port}/v1/chat/completions', 'model': 'real-model', 'protocol': 'chat'}}, 'default_route': 'local', 'decision': {'type': 'fixed'}}
            Path(d, 'config.json').write_text(json.dumps(config))
            p = subprocess.Popen([sys.executable, 'omr.py', 'serve', '--config', str(Path(d, 'config.json')), '--port', '0'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                line = p.stdout.readline().strip()
                if not line.isdigit():
                    self.fail(f'gateway failed to start: {p.stderr.read()}')
                payload = {'model': 'open-model-router', 'messages': [{'role': 'user', 'content': 'hello'}], 'tools': [{'type': 'function', 'function': {'name': 'f'}}]}
                req = urllib.request.Request(f'http://127.0.0.1:{line}/v1/chat/completions', json.dumps(payload).encode(), {'Content-Type':'application/json'})
                with urllib.request.urlopen(req, timeout=3) as response: result = json.load(response)
                self.assertEqual(result['model'], 'real-model')
                self.assertEqual(result['choices'][0]['message']['tool_calls'][0]['id'], 'one')
                self.assertEqual(seen[0][1], dict(payload, model='real-model'))
            finally:
                p.terminate(); p.wait(timeout=3); p.stdout.close(); p.stderr.close(); server.shutdown(); server.server_close()

if __name__ == '__main__': unittest.main()
