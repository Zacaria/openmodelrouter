"""Regressions from independent review, real sockets and synthetic bytes only."""
import http.client
import json
import socket
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from test_transport import serve
import omr


class ReviewRegressions(unittest.TestCase):
    def test_terminal_line_without_event_delimiter_is_not_complete(self):
        class Backend(BaseHTTPRequestHandler):
            def log_message(self, format, *args): pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                body = b'data: [DONE]\n'
                self.send_response(200); self.send_header('Content-Type','text/event-stream'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
        with tempfile.TemporaryDirectory() as directory, serve(Backend) as upstream:
            path = Path(directory,'receipts.jsonl')
            config={'routes':{'local':{'url':f'http://127.0.0.1:{upstream}/v1','model':'actual','protocol':'chat'}},'default_route':'local','receipts':str(path)}
            with serve(omr.handler(config)) as gateway:
                c=http.client.HTTPConnection('127.0.0.1',gateway,timeout=2)
                c.request('POST','/v1/chat/completions',json.dumps({'model':'open-model-router','stream':True}),{'Content-Type':'application/json'})
                response=c.getresponse();body=response.read();c.close()
                for _ in range(30):
                    if path.exists() and path.stat().st_size: break
                    time.sleep(.01)
                self.assertEqual(json.loads(path.read_text())['status'],'upstream_error')
                self.assertIn(b'error',body)

    def test_receipt_rejects_untrusted_strings_and_truncated_stream(self):
        class Backend(BaseHTTPRequestHandler):
            def log_message(self, format, *args): pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                data = {'model':'PRIVATE-MODEL','usage':{'private_prompt':'PRIVATE-MARKER','prompt_tokens':3,'prompt_tokens_details':{'private':'PRIVATE-NESTED','cached_tokens':1}},'reasoning':{'effort':'PRIVATE-EFFORT'}}
                chunk = ('data: '+json.dumps(data)+'\n\n').encode()
                self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Content-Length',str(len(chunk)+1000));self.end_headers();self.wfile.write(chunk)
        with tempfile.TemporaryDirectory() as directory, serve(Backend) as upstream:
            path = Path(directory,'receipt.jsonl')
            config={'routes':{'local':{'url':f'http://127.0.0.1:{upstream}/v1','model':'expected','protocol':'chat'}},'default_route':'local','receipts':str(path)}
            with serve(omr.handler(config)) as gateway:
                c=http.client.HTTPConnection('127.0.0.1',gateway,timeout=2)
                c.request('POST','/v1/chat/completions',json.dumps({'model':'open-model-router','messages':[{'role':'user','content':'public'}],'stream':True}),{'Content-Type':'application/json'})
                r=c.getresponse();body=r.read();c.close()
                for _ in range(30):
                    if path.exists() and path.stat().st_size:break
                    time.sleep(.01)
                row=json.loads(path.read_text())
                self.assertNotIn('PRIVATE',path.read_text())
                self.assertEqual(row['usage'],{'prompt_tokens':3,'prompt_tokens_details':{'cached_tokens':1}})
                self.assertEqual(row['status'],'upstream_error')
                self.assertIn(b'error',body)

    def test_drip_body_has_absolute_deadline(self):
        config={'routes':{'local':{'url':'http://127.0.0.1:1/v1','model':'expected','protocol':'chat'}},'default_route':'local','timeout_seconds':.2}
        with serve(omr.handler(config)) as port:
            c=socket.create_connection(('127.0.0.1',port),timeout=2)
            c.sendall(b'POST /v1/chat/completions HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\nContent-Length: 100\r\n\r\n')
            def drip():
                for _ in range(25):
                    try:c.sendall(b' ')
                    except OSError:return
                    time.sleep(.04)
            t=threading.Thread(target=drip,daemon=True);t.start();start=time.monotonic()
            response=c.recv(4096)
            self.assertLess(time.monotonic()-start,.6)
            self.assertIn(b'504',response)
            c.close();t.join(1)


if __name__=='__main__':unittest.main()
