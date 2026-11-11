"""Offline lifecycle checks: actual TCP, no inference."""
import http.client
import json
import select
import threading
import time
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler
from test_transport import serve
import omr


class DeadlineTests(unittest.TestCase):
    def test_deadline_shutdown_before_upstream_getresponse_returns_504(self):
        closed = threading.Event()
        class Backend(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                if select.select([self.connection], [], [], 3)[0] and not self.connection.recv(1):
                    closed.set()
        with serve(Backend) as upstream:
            config = {'routes': {'fixed': {'url': f'http://127.0.0.1:{upstream}/v1', 'model': 'actual', 'protocol': 'chat'}}, 'default_route': 'fixed', 'timeout_seconds': .2}
            original = http.client.HTTPConnection.getresponse
            def synchronized(connection):
                if connection.port == upstream:
                    if not closed.wait(2): raise AssertionError('watcher did not close upstream')
                return original(connection)
            with patch.object(http.client.HTTPConnection, 'getresponse', synchronized), serve(omr.handler(config)) as gateway:
                client = http.client.HTTPConnection('127.0.0.1', gateway, timeout=3)
                client.request('POST', '/v1/chat/completions', json.dumps({'model': 'open-model-router', 'messages': []}), {'Content-Type': 'application/json'})
                response = client.getresponse()
                self.assertEqual(response.status, 504)
                self.assertEqual(json.load(response)['error']['type'], 'timeout')
                client.close()

    def test_stream_deadline_reports_timeout_after_headers(self):
        closed = threading.Event()
        class Backend(BaseHTTPRequestHandler):
            def log_message(self, format, *args): pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(200); self.send_header('Content-Type', 'text/event-stream'); self.end_headers()
                self.wfile.write(b'data: {"choices":[]}\n\n'); self.wfile.flush()
                if select.select([self.connection], [], [], 3)[0] and not self.connection.recv(1): closed.set()
        with serve(Backend) as upstream:
            config = {'routes': {'fixed': {'url': f'http://127.0.0.1:{upstream}/v1', 'model': 'actual', 'protocol': 'chat'}}, 'default_route': 'fixed', 'timeout_seconds': .2}
            original_response = http.client.HTTPConnection.getresponse
            original_read = http.client.HTTPResponse.read1
            def mark(connection):
                response = original_response(connection)
                if connection.port == upstream: response._deadline_test_reads = 0
                return response
            def synchronized(response, size):
                if hasattr(response, '_deadline_test_reads'):
                    response._deadline_test_reads += 1
                    if response._deadline_test_reads == 2 and not closed.wait(2): raise AssertionError('watcher did not close upstream')
                return original_read(response, size)
            with patch.object(http.client.HTTPConnection, 'getresponse', mark), patch.object(http.client.HTTPResponse, 'read1', synchronized), serve(omr.handler(config)) as gateway:
                client = http.client.HTTPConnection('127.0.0.1', gateway, timeout=3)
                client.request('POST', '/v1/chat/completions', json.dumps({'model': 'open-model-router', 'stream': True}), {'Content-Type': 'application/json'})
                response = client.getresponse()
                self.assertEqual(response.status, 200)
                body = response.read()
                self.assertTrue(closed.wait(1))
                self.assertIn(b'event: error\ndata:', body)
                self.assertIn(b'"type": "timeout"', body)
                client.close()

    def test_no_headers_deadline_closes_backend_and_next_request_recovers(self):
        calls = []
        closed = threading.Event()
        class Backend(BaseHTTPRequestHandler):
            def log_message(self, format, *args): pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                calls.append(1)
                if len(calls) == 1:
                    ready, _, _ = select.select([self.connection], [], [], 2)
                    if ready and self.connection.recv(1) == b'': closed.set()
                    return
                body = b'{"model":"actual","choices":[]}'
                self.send_response(200); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
        with serve(Backend) as upstream:
            config = {'routes': {'fixed': {'url':f'http://127.0.0.1:{upstream}/v1','model':'actual','protocol':['chat','responses','anthropic']}}, 'default_route':'fixed','timeout_seconds':.2}
            with serve(omr.handler(config)) as gateway:
                statuses = []
                start = time.monotonic()
                for _ in range(2):
                    client = http.client.HTTPConnection('127.0.0.1',gateway,timeout=2)
                    client.request('POST','/v1/messages?beta=true',json.dumps({'model':'open-model-router','messages':[{'role':'user','content':'test'}]}),{'Content-Type':'application/json'})
                    response = client.getresponse(); statuses.append(response.status); response.read(); client.close()
                self.assertEqual(statuses,[504,200])
                self.assertLess(time.monotonic()-start,1)
                self.assertTrue(closed.wait(1))
                self.assertEqual(len(calls),2)

    def test_invalid_decision_never_calls_default_provider(self):
        import sys
        calls = []
        class Backend(BaseHTTPRequestHandler):
            def log_message(self, format, *args): pass
            def do_POST(self): calls.append(1); self.send_error(500)
        with serve(Backend) as upstream:
            config = {'routes': {'default':{'url':f'http://127.0.0.1:{upstream}/v1','model':'actual','protocol':'chat'}},'default_route':'default', 'decision':{'type':'command','public_prompts':True,'command':[sys.executable,'-c','print(\'{"route":"not-allowed"}\')']}}
            with serve(omr.handler(config)) as gateway:
                client = http.client.HTTPConnection('127.0.0.1',gateway,timeout=2)
                client.request('POST','/v1/chat/completions',json.dumps({'model':'open-model-router','messages':[{'role':'user','content':'hello'}]}),{'Content-Type':'application/json'})
                response = client.getresponse(); self.assertEqual(response.status,400);response.read();client.close()
                self.assertEqual(calls,[])


if __name__ == '__main__': unittest.main()
