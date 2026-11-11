#!/usr/bin/env python3
"""Run a host against a trusted loopback OMR gateway without changing user config."""
import argparse, http.client, http.server, os, pathlib, subprocess, tempfile, threading, uuid, socket, select, signal, time, math, sys
import json
import hmac
import secrets
from typing import cast

HOST_PROTOCOL = {'hermes': 'chat', 'omp': 'chat', 'codex': 'responses', 'claude': 'anthropic'}


def desktop_catalogue(port, key, protocol):
    if not key or '\r' in key or '\n' in key:
        raise ValueError('desktop_key_required')
    client = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
    try:
        client.request('GET', '/v1/models', headers={'Authorization': 'Bearer ' + key})
        response = client.getresponse()
        data = response.read(16 * 1024 * 1024 + 1)
        if response.status != 200 or len(data) > 16 * 1024 * 1024:
            raise ValueError('catalogue_unavailable')
        rows = json.loads(data)['data']
        if not isinstance(rows, list):
            raise ValueError('catalogue_unavailable')
        selected = []
        seen = set()
        for row in rows:
            identity = row['id']
            if not isinstance(identity, str) or identity in seen:
                raise ValueError('catalogue_unavailable')
            seen.add(identity)
            if protocol in row.get('protocols', []):
                selected.append(row)
        return selected
    except (OSError, http.client.HTTPException, ValueError, KeyError, TypeError):
        raise ValueError('catalogue_unavailable') from None
    finally:
        client.close()


def codex_catalogue(models, context_window):
    # Codex 0.159 ModelInfo. No inferred reasoning, image or web capabilities.
    return {'models': [{
        'slug': row['id'], 'display_name': row.get('name', row['id']),
        'description': 'OMR · ' + row.get('name', row['id']),
        'base_instructions': '',
        'supported_reasoning_levels': [], 'shell_type': 'shell_command',
        'visibility': 'list', 'supported_in_api': True, 'priority': i,
        'support_verbosity': False,
        'truncation_policy': {'mode': 'tokens', 'limit': context_window},
        'context_window': context_window, 'experimental_supported_tools': [],
        'input_modalities': ['text'], 'supports_reasoning_summary_parameter': False,
    } for i, row in enumerate(models)]}


def omp_catalogue(models, base, context_window, max_output, authenticated=False):
    # JSON is also YAML; quoting IDs/names avoids delimiter injection.
    return {'providers': {'omr': {
        'baseUrl': base + '/v1', 'api': 'openai-completions',
        **({'apiKey': 'OMR_PROXY_KEY'} if authenticated else {'auth': 'none'}),
        'models': [{'id': row['id'], 'name': row.get('name', row['id']),
                    'reasoning': False, 'input': ['text'],
                    'contextWindow': context_window, 'maxTokens': max_output}
                   for row in models],
    }}}

class Proxy(http.server.BaseHTTPRequestHandler):
    @property
    def gateway(self) -> 'Server':
        return cast('Server', self.server)

    protocol_version = 'HTTP/1.1'
    def log_message(self, format, *args): pass
    def client_authorized(self):
        if not getattr(self.server, 'desktop_key', None):
            return True
        expected = getattr(self.server, 'client_key', None)
        values = self.headers.get_all('Authorization', [])
        keys = self.headers.get_all('x-api-key', [])
        hosts = self.headers.get_all('Host', [])
        token = (values[0][7:] if len(values) == 1 and values[0].startswith('Bearer ') and not keys
                 else keys[0] if len(keys) == 1 and not values else '')
        return bool(expected and token and not self.headers.get('Origin')
                    and len(hosts) == 1 and hosts[0] in (f'127.0.0.1:{self.gateway.server_port}', f'localhost:{self.gateway.server_port}')
                    and hmac.compare_digest(token.encode(), expected.encode()))

    def reject_client(self):
        self.send_response(401)
        self.send_header('Content-Length', '0')
        self.send_header('Connection', 'close')
        self.end_headers()
        self.close_connection = True

    def do_GET(self):
        if not self.client_authorized():
            self.reject_client()
            return
        catalogue = getattr(self.server, 'catalogue', None)
        if self.path != '/v1/models' or catalogue is None:
            self.send_error(404)
            return
        data = json.dumps({'object': 'list', 'data': catalogue}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if not self.client_authorized():
            self.reject_client()
            return
        started = False
        c = None
        done = threading.Event()
        headers_received = threading.Event()
        try:
            length = int(self.headers.get('Content-Length', '-1'))
            if not 0 <= length <= 32 * 1024 * 1024: raise ValueError('invalid length')
            data = self.rfile.read(length)
            headers = {k:v for k,v in self.headers.items() if k.lower() not in ('host','connection','content-length','x-omr-session','transfer-encoding','authorization','x-api-key')}
            headers['X-OMR-Session'] = self.gateway.session
            key = self.gateway.desktop_key
            if key:
                headers['Authorization'] = 'Bearer ' + key
            c = http.client.HTTPConnection('127.0.0.1', self.gateway.upstream, timeout=120)
            c.request('POST', self.path, data, headers)
            upstream_socket = c.sock
            def watch():
                deadline = time.monotonic() + 120
                while not done.is_set():
                    if not headers_received.is_set() and time.monotonic() >= deadline: break
                    try:
                        readable, _, _ = select.select([self.connection], [], [], 0.2)
                        if readable and not self.connection.recv(1, socket.MSG_PEEK): break
                        if readable: done.wait(0.2)
                    except OSError: break
                if not done.is_set():
                    try: upstream_socket.shutdown(socket.SHUT_RDWR)
                    except OSError: pass
            threading.Thread(target=watch, daemon=True).start()
            r = c.getresponse()
            headers_received.set()
            if r.status >= 400: print(f'OMR: upstream HTTP error {r.status}', file=sys.stderr, flush=True)
            self.send_response(r.status); started = True
            for k,v in r.getheaders():
                if k.lower() not in ('connection','transfer-encoding','content-length'): self.send_header(k,v)
            self.send_header('Connection','close'); self.end_headers()
            while True:
                chunk = r.read1(16384)
                if not chunk: break
                self.wfile.write(chunk); self.wfile.flush()
            self.close_connection = True
        except (ValueError, OSError, http.client.HTTPException):
            if not started:
                if not headers_received.is_set(): print('OMR: upstream HTTP error 502', file=sys.stderr, flush=True)
                try: self.send_error(502, 'gateway unavailable or invalid request')
                except OSError: pass
            self.close_connection = True
        finally:
            done.set()
            if c is not None: c.close()

class Server(http.server.ThreadingHTTPServer):
    daemon_threads = True
    session: str
    upstream: int
    desktop_key: str | None = None
    client_key: str = ''
    catalogue: list[dict] | None = None

def main():
    p = argparse.ArgumentParser()
    p.add_argument('host', choices=['hermes','codex','omp','claude'])
    p.add_argument('--port', type=int, required=True, help='trusted gateway loopback port on this host')
    p.add_argument('--proxy-port', type=int, help='explicit stable loopback proxy port')
    p.add_argument('--session', required=True, help='explicit UUID, reuse for same conversation')
    p.add_argument('--project', required=True, help='isolated synthetic working directory')
    p.add_argument('--omp-bin', default='omp')
    p.add_argument('--desktop', action='store_true', help='use the authenticated mixed Desktop catalogue')
    p.add_argument('--key-env', default='OMR_DESKTOP_KEY', help='environment variable containing the ephemeral Desktop key')
    p.add_argument('--model', help='exact Desktop route ID (default: omr/balanced)')
    p.add_argument('--list-models', action='store_true', help='print filtered Desktop catalogue without launching a client')
    p.add_argument('--run-timeout', type=float, help='total command runtime in seconds (default: unlimited)')
    p.add_argument('--context-window', type=int, default=8192, help='OMP operator context limit')
    p.add_argument('--max-output-tokens', type=int, default=2048, help='OMP operator output limit')
    a, args = p.parse_known_args(); session = str(uuid.UUID(a.session))
    if a.run_timeout is not None and (not math.isfinite(a.run_timeout) or a.run_timeout <= 0): p.error('--run-timeout must be finite and positive')
    if a.context_window <= 0 or not 0 < a.max_output_tokens <= a.context_window: p.error('token limits must be positive and max output <= context window')
    if not 1 <= a.port <= 65535: p.error('invalid port')
    project = pathlib.Path(a.project).resolve(strict=True)
    if not project.is_dir(): p.error('project must be a directory')
    args = args[1:] if args[:1] == ['--'] else args
    models = None
    desktop_key = None
    model = a.model or ('omr/balanced' if a.desktop else 'open-model-router')
    if a.desktop:
        desktop_key = os.environ.get(a.key_env, '')
        try:
            models = desktop_catalogue(a.port, desktop_key, HOST_PROTOCOL[a.host])
        except ValueError as error:
            p.error(str(error))
        if a.list_models:
            print(json.dumps({'object': 'list', 'data': models}, ensure_ascii=False))
            return 0
        if model not in {row['id'] for row in models}:
            p.error('model_unavailable_for_client')
    elif a.list_models:
        p.error('--list-models requires --desktop')
    proxy_port = a.proxy_port if a.proxy_port is not None else 20000 + uuid.UUID(session).int % 40000
    if not 1 <= proxy_port <= 65535: p.error('invalid proxy port')
    server = Server(('127.0.0.1', proxy_port), Proxy); server.session = session; server.upstream = a.port
    server.desktop_key = desktop_key
    server.client_key = secrets.token_urlsafe(32) if a.desktop else ''
    server.catalogue = models
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    env = os.environ.copy()
    if a.desktop:
        env.pop(a.key_env, None)
        env['OMR_PROXY_KEY'] = server.client_key
    with tempfile.TemporaryDirectory(prefix='omr-host-') as temp:
        if a.host == 'hermes':
            cmd = ['hermes','chat','--safe-mode','--provider','custom','--base-url',base+'/v1','--model','open-model-router']
        elif a.host == 'claude':
            env['ANTHROPIC_BASE_URL'] = base
            env['ANTHROPIC_AUTH_TOKEN'] = 'omr-local'
            env.pop('ANTHROPIC_API_KEY', None)
            cmd = ['claude','--setting-sources','','--strict-mcp-config','--model','open-model-router']
        elif a.host == 'codex':
            # Codex uses the local gateway without OpenAI authentication.
            cmd = ['codex','-c','model_provider="omr"','-c','model_providers.omr.name="OMR"','-c',f'model_providers.omr.base_url="{base}/v1"','-c','model_providers.omr.wire_api="responses"','-c','model_providers.omr.requires_openai_auth=false','-c','model_providers.omr.supports_websockets=false','-c','model_providers.omr.request_max_retries=0','-c','model_providers.omr.stream_max_retries=0','-m','open-model-router']
        else:
            env['PI_CODING_AGENT_DIR'] = temp
            pathlib.Path(temp,'models.yml').write_text(f'providers:\n  omr:\n    baseUrl: {base}/v1\n    api: openai-completions\n    auth: none\n    models:\n      - id: open-model-router\n        name: open-model-router\n        contextWindow: {a.context_window}\n        maxTokens: {a.max_output_tokens}\n')
            cmd = [a.omp_bin,'--model','omr/open-model-router']
        if a.desktop:
            if a.host == 'codex':
                cmd.extend(['-c', 'model_providers.omr.env_key="OMR_PROXY_KEY"'])
                catalog_path = pathlib.Path(temp, 'codex-models.json')
                catalog_path.write_text(json.dumps(codex_catalogue(models, a.context_window)))
                cmd.extend(['-c', 'model_catalog_json=' + json.dumps(str(catalog_path))])
            elif a.host == 'omp':
                pathlib.Path(temp, 'models.yml').write_text(json.dumps(omp_catalogue(models, base, a.context_window, a.max_output_tokens, authenticated=True), ensure_ascii=False, indent=2))
            elif a.host == 'hermes':
                # Hermes binds OPENAI_API_KEY to OPENAI_BASE_URL, not CUSTOM_BASE_URL.
                env['OPENAI_BASE_URL'] = base + '/v1'
                env['OPENAI_API_KEY'] = server.client_key
                env['CUSTOM_API_KEY'] = server.client_key
            elif a.host == 'claude':
                env.pop('ANTHROPIC_API_KEY', None)
                env['ANTHROPIC_AUTH_TOKEN'] = server.client_key
            # The proxy credential is per-launch; the Desktop bearer stays in the parent only.
        if a.desktop or a.model:
            # Replace only the launcher's own default, not arbitrary client arguments.
            index = cmd.index('-m' if a.host == 'codex' else '--model') + 1
            cmd[index] = ('omr/' if a.host == 'omp' else '') + model
        child = None
        old_handlers = {}
        interrupted = None
        deadline = None
        timed_out = False
        def stop(signum, frame):
            nonlocal interrupted, deadline
            interrupted = signum
            deadline = time.monotonic() + 2
            if child is not None:
                try: os.killpg(child.pid, signum)
                except ProcessLookupError: pass
        try:
            for sig in (signal.SIGINT, signal.SIGTERM): old_handlers[sig] = signal.signal(sig, stop)
            child = subprocess.Popen(cmd + args, cwd=project, env=env, start_new_session=True)
            if interrupted: stop(interrupted, None)
            run_deadline = time.monotonic() + a.run_timeout if a.run_timeout is not None else None
            while True:
                try: code = child.wait(timeout=0.1); break
                except subprocess.TimeoutExpired:
                    if not interrupted and run_deadline is not None and time.monotonic() >= run_deadline:
                        timed_out = True
                        print('OMR: run timeout exceeded; terminating process group', file=sys.stderr, flush=True)
                        stop(signal.SIGTERM, None)
                    if interrupted and time.monotonic() >= deadline:
                        try: os.killpg(child.pid, signal.SIGKILL)
                        except ProcessLookupError: pass
            if interrupted:
                try: os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                return 124 if timed_out else 128 + interrupted
            return code
        finally:
            for sig, handler in old_handlers.items(): signal.signal(sig, handler)
            server.shutdown(); server.server_close()
if __name__ == '__main__': raise SystemExit(main())
