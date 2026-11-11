"""Experimental loopback-only OpenAI chat adapter; trusted local commands only."""
import argparse
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'pilot-t_f21a25b3'))
import safe_router

MAX_BODY = 100_000
ALLOWED = {'model', 'messages', 'stream', 'max_tokens', 'max_completion_tokens', 'stream_options', 'store'}


def text_messages(messages):
    if not isinstance(messages, list):
        raise ValueError('messages must be a list')
    normalized = []
    for message in messages:
        if not isinstance(message, dict) or set(message) != {'role', 'content'}:
            raise ValueError('unsupported message')
        content = message['content']
        if isinstance(content, list):
            if not content or any(not isinstance(x, dict) or set(x) != {'type', 'text'} or x['type'] != 'text' or not isinstance(x['text'], str) for x in content):
                raise ValueError('only text blocks supported')
            content = '\n'.join(x['text'] for x in content)
        if not isinstance(content, str):
            raise ValueError('invalid content')
        normalized.append({'role': message['role'], 'content': content})
    return normalized


def receipt(result):
    payload = result.get('result', {})
    return {'route': result.get('route'), 'model_requested': result.get('model'),
            'effort_requested': result.get('effort'), 'effort_applied': payload.get('effort_applied'),
            'fallback_reason': result.get('fallback_reason'), 'elapsed_ms': result.get('elapsed_ms'),
            'generation_provenance': payload.get('provenance'), 'usage': payload.get('usage')}


def handler(route):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def send_json(self, status, value):
            body = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            try:
                if self.path != '/v1/chat/completions':
                    self.send_json(404, {'error': {'message': 'not found'}}); return
                size = int(self.headers.get('Content-Length', '-1'))
                if not 0 < size <= MAX_BODY:
                    raise ValueError('invalid body size')
                request = json.loads(self.rfile.read(size))
                if not isinstance(request, dict) or set(request) - ALLOWED or request.get('model') != 'local-router':
                    raise ValueError('unsupported request or model')
                if not isinstance(request.get('stream', False), bool) or request.get('store', False) is not False:
                    raise ValueError('invalid stream or storage')
                if request.get('stream_options', {'include_usage':True}) != {'include_usage':True}:
                    raise ValueError('unsupported stream options')
                for key in ('max_tokens', 'max_completion_tokens'):
                    if key in request and (type(request[key]) is not int or request[key] < 8):
                        raise ValueError('unsupported token limit')
                # Generator has a fixed cap of eight; caller's higher maximum is an upper bound.
                result = route(text_messages(request.get('messages')))
                answer = result['result']['answer']
                usage = result['result'].get('usage', {})
                token_usage = None
                if all(isinstance(usage.get(k), int) and not isinstance(usage[k], bool) and usage[k] >= 0 for k in ('input','output')):
                    token_usage = {'prompt_tokens':usage['input'], 'completion_tokens':usage['output'], 'total_tokens':usage['input']+usage['output']}
                print(json.dumps(receipt(result), ensure_ascii=False), file=sys.stderr, flush=True)
                created = int(time.time())
                base = {'id': 'local-completion', 'created': created, 'model': 'local-router'}
                if request.get('stream', False):
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/event-stream')
                    self.end_headers()
                    for delta, finish in [({'role':'assistant','content':answer}, None), ({}, 'stop')]:
                        chunk = dict(base, object='chat.completion.chunk', choices=[{'index':0,'delta':delta,'finish_reason':finish}])
                        self.wfile.write(('data: '+json.dumps(chunk, ensure_ascii=False)+'\n\n').encode())
                    if request.get('stream_options', {}).get('include_usage') and token_usage is not None:
                        chunk = dict(base, object='chat.completion.chunk', choices=[], usage=token_usage)
                        self.wfile.write(('data: '+json.dumps(chunk)+'\n\n').encode())
                    self.wfile.write(b'data: [DONE]\n\n')
                else:
                    output = dict(base, object='chat.completion', choices=[{'index':0,'message':{'role':'assistant','content':answer},'finish_reason':'stop'}])
                    if token_usage is not None:
                        output['usage'] = token_usage
                    self.send_json(200, output)
            except (ValueError, TypeError, KeyError, json.JSONDecodeError):
                self.send_json(400, {'error': {'message': 'invalid or unsupported request'}})
            except Exception:
                self.send_json(502, {'error': {'message': 'local route failed'}})
    return Handler


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', required=True)
    p.add_argument('--port', type=int, default=4000)
    args = p.parse_args()
    config = json.loads(Path(args.config).read_text())
    cmd = config['decision_command']
    def decide(prompt):
        import subprocess
        result = subprocess.run(cmd, input=json.dumps({'prompt':prompt}), text=True,
                                capture_output=True, timeout=config['timeout_seconds'], check=True, env={})
        return json.loads(result.stdout)['route']
    def route(messages):
        return safe_router.run({'messages':messages}, config, decide)
    server = HTTPServer(('127.0.0.1', args.port), handler(route))
    print('loopback gateway port %s' % server.server_port, file=sys.stderr, flush=True)
    server.serve_forever()

if __name__ == '__main__': main()
