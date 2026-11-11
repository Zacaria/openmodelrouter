"""Loopback model router. Credentials and conversation text never enter receipts."""
import argparse
import hashlib
import hmac
import copy
import http.client
import json
import math
import os
import re
import select
import signal
import socket
import subprocess
import tempfile
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

PATHS = {'/v1/chat/completions': 'chat', '/v1/responses': 'responses', '/v1/messages': 'anthropic'}
# Hugging Face revision dac13b5c0356864ea4501fa151d74dcd8b3ea22a; see evidence/s1d1-identity.json.
S1D1_FILES = {
    'model_int8.onnx': '878975a81da55f27744c3b6a0f5c2f38b1723c322f1a348abae33b1586dbad51',
    'tokenizer.json': 'aebee76d0312011b0d73b08a255d4d11d25c83e9639324870c7b916ea102e13e',
    'vocab_map.npy': '3466512656f2b9ca115751505e310b799aa7a2028bf36d43e6b06413b608e104',
    'variant.json': '0739ab58f9e4480772bf24f5493c4b307fe14ee3c44deccaa337de6e5b2f38fd',
    'config.json': '811b936540d9bf542027a81de32251c4bb549cdaa4757b3322da981f15bc2a6b',
    'tokenizer_config.json': '80fd3e43697c68f25c40c6a6a7573709de6e2032edf0bcf5bd4b042185c39afc',
}


def configure(config):
    if not isinstance(config, dict) or set(config) - {'routes', 'default_route', 'decision', 'receipts', 'timeout_seconds', 'max_sessions', 'gateway_key_env'}:
        raise ValueError('unsupported configuration')
    routes = config['routes']
    if not isinstance(routes, dict) or not routes or config['default_route'] not in routes:
        raise ValueError('invalid routes')
    native = any(urlsplit(r.get('url', '')).path.startswith('/backend-api/codex') for r in routes.values())
    if native:
        key_env = config.get('gateway_key_env')
        if not isinstance(key_env, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key_env) or len(os.environ.get(key_env, '')) < 32:
            raise ValueError('native gateway key environment required (32 characters minimum)')
        if len({r.get('model') for r in routes.values()}) != 1:
            raise ValueError('native routes require one concrete model')
    elif 'gateway_key_env' in config:
        raise ValueError('gateway key only supported for native routes')
    for name, route in routes.items():
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', name):
            raise ValueError('invalid route name')
        if set(route) - {'url', 'protocol', 'model', 'effort', 'forward_auth'}:
            raise ValueError('unsupported route fields')
        url = urlsplit(route['url'])
        if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError('invalid route URL')
        if native and (route['url'] != 'https://chatgpt.com/backend-api/codex' or route.get('protocol') != 'responses'):
            raise ValueError('invalid native route')
        if not native and url.path not in (*PATHS, '/v1'):
            raise ValueError('URL must end with /v1 or a supported endpoint')
        protocols = route['protocol'] if isinstance(route['protocol'], list) else [route['protocol']]
        if not protocols or any(x not in PATHS.values() for x in protocols):
            raise ValueError('invalid protocol')
        if url.path in PATHS and protocols != [PATHS[url.path]]:
            raise ValueError('endpoint/protocol mismatch')
        if not isinstance(route['model'], str) or not route['model'] or len(route['model']) > 256:
            raise ValueError('invalid model')
        if route.get('effort') not in (None, 'none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max'):
            raise ValueError('unsupported effort')
        if type(route.get('forward_auth', False)) is not bool:
            raise ValueError('invalid auth permission')
        if route.get('forward_auth') and url.scheme != 'https' and url.hostname not in ('127.0.0.1', '::1', 'localhost'):
            raise ValueError('credential forwarding requires TLS')
    if type(config.get('max_sessions', 2048)) is not int or not 1 <= config.get('max_sessions', 2048) <= 10000:
        raise ValueError('invalid session bound')
    decision = config.get('decision', {'type':'fixed'})
    if decision.get('type') not in ('fixed', 'command', 's1d1'):
        raise ValueError('unsupported decider')
    if decision['type'] == 'command':
        if decision.get('public_prompts') is not True:
            raise ValueError('public prompt consent required')
        seconds = decision.get('timeout_seconds', 10)
        if type(seconds) not in (float, int) or not 0 < seconds <= 60:
            raise ValueError('invalid decision timeout')
    if decision['type'] != 's1d1':
        return None
    threshold = decision.get('threshold')
    if type(threshold) not in (int, float) or not 0 <= threshold <= 1:
        raise ValueError('explicit threshold required')
    if any(decision.get(k) not in routes for k in ('low_route', 'high_route')):
        raise ValueError('s1d1 routes required')
    weights = Path(decision['weights'])
    wrapper = Path(__file__).with_name('s1d1_upstream.py')
    def verify():
        try:
            for filename, sha in S1D1_FILES.items():
                p = weights / filename
                if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest() != sha:
                    raise ValueError('unverified s1d1 weights')
            if hashlib.sha256(wrapper.read_bytes()).hexdigest() != 'baca9d388504abcc2692da385839be2a892c5bb79256de509173ba066621aee4':
                raise ValueError('unverified s1d1 wrapper')
        except OSError:
            raise ValueError('s1d1 files unavailable') from None
    verify()
    from s1d1_upstream import Router
    classifier = Router(str(weights))
    verify()
    return classifier


def first_prompt(data):
    messages = data.get('messages', data.get('input'))
    if isinstance(messages, str):
        prompt = messages
    elif isinstance(messages, list):
        content = next((m.get('content') for m in messages if isinstance(m, dict) and m.get('role') == 'user'), None)
        if isinstance(content, list):
            prompt = '\n'.join(x['text'] for x in content if isinstance(x, dict) and x.get('type') in ('text', 'input_text') and isinstance(x.get('text'), str))
        else:
            prompt = content
    else:
        prompt = None
    if not isinstance(prompt, str) or not prompt or len(prompt.encode()) > 16_000:
        raise ValueError('first user prompt required within decision limit')
    return prompt


def command_decision(decision, prompt, stopped, deadline):
    if decision.get('public_prompts') is not True:
        raise ValueError('public prompt consent required')
    command = decision['command']
    if not isinstance(command, list) or not command or any(not isinstance(x, str) or not x for x in command):
        raise ValueError('invalid decision command')
    env = {'PATH': os.defpath}
    for name in decision.get('allow_env', []):
        if name in os.environ: env[name] = os.environ[name]
    deadline = min(deadline, time.monotonic() + decision.get('timeout_seconds', 10))
    # Trusted commands only. Files bound pipes without buffering unlimited output in RAM.
    with tempfile.TemporaryFile() as source, tempfile.TemporaryFile() as target:
        source.write(json.dumps({'prompt': prompt}).encode()); source.seek(0)
        child = subprocess.Popen(command, stdin=source, stdout=target, stderr=subprocess.DEVNULL,
                                 env=env, start_new_session=True)
        try:
            while child.poll() is None:
                if stopped.wait(.02) or time.monotonic() >= deadline:
                    raise TimeoutError('decision deadline')
                if os.fstat(target.fileno()).st_size > 8192:
                    raise ValueError('decision response too large')
            if child.returncode or os.fstat(target.fileno()).st_size > 8192:
                raise ValueError('decision failed')
            target.seek(0)
            return json.load(target)
        finally:
            # Kill only the process group created above, including command descendants.
            try: os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            child.wait()


def observe(value, row):
    if not isinstance(value, dict):
        return
    if isinstance(value.get('model'), str):
        if value['model'] == row['model_requested'] and not row.get('model_identity_unrecognized'):
            row['model_observed'] = value['model']
        elif value['model'] != row['model_requested']:
            row['model_observed'] = None
            row['model_identity_unrecognized'] = True
    if isinstance(value.get('usage'), dict):
        # Providers are untrusted: never persist arbitrary strings or nested fields.
        numeric = ('input_tokens', 'output_tokens', 'total_tokens', 'prompt_tokens', 'completion_tokens',
                   'cache_creation_input_tokens', 'cache_read_input_tokens')
        details = ('input_tokens_details', 'output_tokens_details', 'prompt_tokens_details', 'completion_tokens_details')
        for key in numeric:
            number = value['usage'].get(key)
            if type(number) is int and 0 <= number <= 10**12:
                row['usage'][key] = number
        for key in details:
            source = value['usage'].get(key)
            if isinstance(source, dict):
                clean = {k: source[k] for k in ('cached_tokens', 'cache_write_tokens', 'reasoning_tokens', 'audio_tokens', 'accepted_prediction_tokens', 'rejected_prediction_tokens') if type(source.get(k)) is int and 0 <= source[k] <= 10**12}
                if clean: row['usage'].setdefault(key, {}).update(clean)
    if isinstance(value.get('reasoning'), dict):
        effort = value['reasoning'].get('effort')
        if effort in ('none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max'):
            row['effort_acknowledged'] = effort
    for key in ('message', 'response'):
        if isinstance(value.get(key), dict):
            observe(value[key], row)


def validate_native_event(event, first, terminal):
    """Bounded contract for headerless Codex SSE; unknown kinds fail closed."""
    if not isinstance(event, dict) or not isinstance(event.get('type'), str) or 'error' in event:
        raise ValueError('invalid native event')
    kind = event['type']
    if terminal or (first and kind != 'response.created') or (not first and kind == 'response.created'):
        raise ValueError('invalid native event order')
    fields = {
        'response.output_text.delta': {'delta': str},
        'response.custom_tool_call_input.delta': {'delta': str},
        'response.reasoning_summary_text.delta': {'delta': str, 'summary_index': int},
        'response.reasoning_summary_text.done': {'item_id': str, 'text': str, 'summary_index': int},
        'response.reasoning_text.delta': {'delta': str, 'content_index': int},
        'response.reasoning_summary_part.added': {'summary_index': int},
        'response.function_call_arguments.delta': {'delta': str},
        'response.function_call_arguments.done': {'arguments': str},
        'response.custom_tool_call_input.done': {'input': str},
        'response.output_text.done': {'text': str},
        'response.content_part.added': {'part': dict},
        'response.content_part.done': {'part': dict},
        'response.reasoning_summary_part.done': {'part': dict},
        'response.in_progress': {'response': dict},
        'response.metadata': {}, 'codex.response.metadata': {},
        'responsesapi.websocket_timing': {},
        'response.created': {'response': dict}, 'response.completed': {'response': dict},
        'response.output_item.added': {'item': dict}, 'response.output_item.done': {'item': dict},
    }
    if kind not in fields or any(type(event.get(k)) is not t for k, t in fields[kind].items()):
        raise ValueError('invalid native event fields')
    if kind in ('response.created', 'response.in_progress', 'response.completed'):
        response = event['response']
        if response.get('error') is not None or response.get('status') in ('failed', 'incomplete'):
            raise ValueError('upstream response error')
        if kind in ('response.created', 'response.completed') and (not isinstance(response.get('id'), str) or not response['id']):
            raise ValueError('missing response id')
    for key, expected in (('item_id', str), ('call_id', str), ('delta', str), ('text', str), ('summary_index', int), ('content_index', int)):
        if event.get(key) is not None and type(event[key]) is not expected: raise ValueError('invalid event field')
    if kind == 'response.custom_tool_call_input.delta' and not any(isinstance(event.get(k), str) for k in ('item_id', 'call_id')):
        raise ValueError('missing tool id')
    if kind == 'response.completed':
        response = event['response']
        if not isinstance(response.get('id'), str): raise ValueError('missing response id')
        usage = response.get('usage')
        if usage is not None:
            if not isinstance(usage, dict) or any(type(usage.get(k)) is not int for k in ('input_tokens', 'output_tokens', 'total_tokens')):
                raise ValueError('invalid usage')
            for key, required in (('input_tokens_details', 'cached_tokens'), ('output_tokens_details', 'reasoning_tokens')):
                detail = usage.get(key)
                if detail is not None and (not isinstance(detail, dict) or type(detail.get(required)) is not int): raise ValueError('invalid usage details')
        if response.get('end_turn') is not None and type(response['end_turn']) is not bool: raise ValueError('invalid end_turn')
    if kind.startswith('response.output_item.'):
        item = event['item']
        requirements = {'message': {'role': str, 'content': list}, 'reasoning': {'summary': list},
                        'function_call': {'name': str, 'arguments': str, 'call_id': str},
                        'custom_tool_call': {'name': str, 'input': str, 'call_id': str}}
        shape = requirements.get(item.get('type'))
        if shape is None or any(type(item.get(k)) is not t for k, t in shape.items()):
            raise ValueError('invalid native item')
        optional = {'id': str, 'internal_chat_message_metadata_passthrough': dict}
        optional.update({'message': {'phase': str}, 'reasoning': {'encrypted_content': str},
                         'function_call': {'namespace': str, 'encrypted_function_args': list},
                         'custom_tool_call': {'namespace': str, 'status': str}}[item['type']])
        if item.get('error') is not None or any(item.get(k) is not None and type(item[k]) is not t for k, t in optional.items()):
            raise ValueError('invalid native item optional field')
        metadata = item.get('internal_chat_message_metadata_passthrough')
        if metadata is not None and ((metadata.get('turn_id') is not None and type(metadata['turn_id']) is not str) or
                                     (metadata.get('create_time') is not None and type(metadata['create_time']) not in (int, float)) or
                                     (metadata.get('content_item_kinds') is not None and (type(metadata['content_item_kinds']) is not list or any(type(kind) is not str for kind in metadata['content_item_kinds'])))):
            raise ValueError('invalid native item metadata')
        if item['type'] == 'message' and item.get('phase') is not None and item['phase'] not in ('commentary', 'partial_answer', 'final_answer'):
            raise ValueError('invalid message phase')
        if item['type'] == 'function_call' and item.get('encrypted_function_args') is not None and any(type(arg) is not str for arg in item['encrypted_function_args']):
            raise ValueError('invalid encrypted function arguments')
        if item['type'] == 'message':
            if any(not isinstance(part, dict) or part.get('type') not in ('input_text', 'output_text') or not isinstance(part.get('text'), str) for part in item['content']): raise ValueError('invalid message content')
        if item['type'] == 'reasoning':
            if any(not isinstance(part, dict) or part.get('type') != 'summary_text' or not isinstance(part.get('text'), str) for part in item['summary']): raise ValueError('invalid reasoning summary')
            content = item.get('content')
            if content is not None and (not isinstance(content, list) or any(not isinstance(part, dict) or part.get('type') not in ('text', 'reasoning_text') or not isinstance(part.get('text'), str) for part in content)): raise ValueError('invalid reasoning content')
    return kind


def handler(config, desktop=None):
    classifier = configure(config)
    receipt_lock = threading.Lock()
    session_lock = threading.Lock()
    sessions = {}
    decision = config.get('decision', {'type': 'fixed'})
    native = 'gateway_key_env' in config
    gateway_key = os.environ[config['gateway_key_env']] if native else None
    catalog = {}
    catalog_lock = threading.Lock()
    timeout = config.get('timeout_seconds', 120)
    if type(timeout) not in (int, float) or not 0 < timeout <= 600:
        raise ValueError('invalid timeout')
    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def handle_one_request(self):
            self._accepted_at = time.monotonic()
            self._body_started = False
            self._receipt_request_id = None
            def close_slow_headers():
                if not self._body_started:
                    try: self.connection.shutdown(socket.SHUT_RDWR)
                    except OSError: pass
            timer = threading.Timer(timeout, close_slow_headers)
            timer.daemon = True
            timer.start()
            try: super().handle_one_request()
            finally: timer.cancel()

        def log_message(self, format, *args):
            pass

        def reply(self, status, body, content_type='application/json'):
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Connection', 'close')
            if self._receipt_request_id is not None: self.send_header('X-OMR-Request', self._receipt_request_id)
            self.end_headers()
            self.wfile.write(body)
            self.close_connection = True

        def native_auth(self):
            supplied = self.headers.get_all('X-OMR-Gateway-Key', [])
            if len(supplied) != 1 or not hmac.compare_digest(supplied[0].encode(), gateway_key.encode()):
                self.reply(401, b'{"error":"unauthorized"}')
                return None
            blocked = {x.strip().lower() for value in self.headers.get_all('Connection', []) for x in value.split(',')}
            if blocked & {'authorization', 'chatgpt-account-id'}:
                self.reply(400, b'{"error":"invalid request"}')
                return None
            auth = self.headers.get_all('Authorization', [])
            account = self.headers.get_all('chatgpt-account-id', [])
            if len(auth) != 1 or not auth[0].startswith('Bearer ') or not auth[0][7:].strip() or len(account) != 1 or not account[0].strip():
                self.reply(401, b'{"error":"unauthorized"}')
                return None
            return hashlib.sha256((auth[0] + '\0' + account[0]).encode()).digest()

        def native_headers(self):
            blocked = {x.strip().lower() for value in self.headers.get_all('Connection', []) for x in value.split(',')}
            names = ('Authorization', 'chatgpt-account-id', 'OpenAI-Beta', 'User-Agent', 'originator',
                     'X-OpenAI-Fedramp', 'x-codex-beta-features', 'x-codex-installation-id', 'x-codex-routing-hint', 'x-codex-parent-thread-id', 'x-codex-window-id', 'session_id', 'conversation_id', 'x-codex-turn-state', 'x-codex-turn-metadata')
            return {name: self.headers[name] for name in names if name.lower() not in blocked and len(self.headers.get_all(name, [])) == 1}

        def do_GET(self):
            self._body_started = True
            parsed = urlsplit(self.path)
            if desktop:
                if not desktop.authorized(self.headers, self.server.server_port):
                    return self.reply(401, b'{"error":"unauthorized"}')
                if self.path != '/v1/models':
                    return self.reply(404, b'{"error":"not found"}')
                return self.reply(200, json.dumps(desktop.catalogue()).encode())
            if not native or parsed.path != '/backend-api/codex/models' or (parsed.query and not re.fullmatch(r'client_version=[A-Za-z0-9._-]{1,64}', parsed.query)):
                return self.reply(404, b'{"error":"not found"}')
            if self.headers.get('Origin'):
                return self.reply(400, b'{"error":"invalid request"}')
            identity = self.native_auth()
            if identity is None: return
            connection = None
            timer = None
            try:
                remaining = timeout - (time.monotonic() - self._accepted_at)
                if remaining <= 0: raise TimeoutError()
                connection = http.client.HTTPSConnection('chatgpt.com', 443, timeout=remaining)
                def expire():
                    try:
                        if connection.sock: connection.sock.shutdown(socket.SHUT_RDWR)
                    except OSError: pass
                timer = threading.Timer(remaining, expire); timer.daemon = True; timer.start()
                connection.request('GET', self.path, headers={**self.native_headers(), 'Accept-Encoding': 'identity'})
                response = connection.getresponse()
                if response.status != 200 or response.getheader('Content-Encoding', 'identity') != 'identity':
                    return self.reply(502, b'{"error":"catalog unavailable"}')
                body = response.read(1000001)
                if len(body) > 1000000:
                    return self.reply(502, b'{"error":"catalog unavailable"}')
                value = json.loads(body)
                models = value['models']
                matches = [m for m in models if isinstance(m, dict) and m.get('slug') == config['routes'][config['default_route']]['model']]
                if len(matches) != 1 or any(isinstance(m, dict) and m.get('slug') == 'open-model-router' for m in models): raise ValueError()
                model = matches[0]
                levels = model['supported_reasoning_levels']
                efforts = [x['effort'] for x in levels if isinstance(x, dict) and isinstance(x.get('effort'), str)]
                if not isinstance(levels, list) or not efforts or len(efforts) != len(levels) or len(set(efforts)) != len(efforts) or model['default_reasoning_level'] not in efforts: raise ValueError()
                alias = copy.deepcopy(model); alias['slug'] = 'open-model-router'
                value['models'].append(alias)
                with catalog_lock:
                    if identity not in catalog and len(catalog) >= config.get('max_sessions', 2048): raise ValueError()
                    catalog[identity] = frozenset(efforts)
                return self.reply(200, json.dumps(value).encode())
            except (OSError, http.client.HTTPException, ValueError, KeyError, TypeError):
                return self.reply(502, b'{"error":"catalog unavailable"}')
            finally:
                if timer: timer.cancel()
                if connection: connection.close()

        def do_POST(self):
            started = self._accepted_at
            self._body_started = True
            if desktop:
                if not desktop.begin(self.headers, self.server.server_port):
                    return self.reply(401, b'{"error":"unauthorized"}')
            self.connection.settimeout(timeout)
            row = {'request_id': str(uuid.uuid4()), 'session': None, 'route': None,
                   'model_requested': None, 'model_observed': None, 'effort_transmitted': None,
                   'effort_acknowledged': None, 'effort_applied': None, 'usage': {},
                   'decision_ms': 0, 'status': 'invalid_request', 'upstream_status': None}
            if desktop: self._receipt_request_id = row['request_id']
            done = threading.Event()
            stopped = threading.Event()
            stop_reason = []
            upstream_socket = []
            connection = None
            response = None
            route = {}
            headers_sent = False
            watcher = None

            def watch():
                while not done.wait(.025):
                    reason = None
                    if desktop and desktop.stopping:
                        reason = 'cancelled'
                    elif time.monotonic() - started >= timeout:
                        reason = 'timeout'
                    else:
                        try:
                            ready, _, _ = select.select([self.connection], [], [], 0)
                            if ready and not self.connection.recv(1, socket.MSG_PEEK):
                                reason = 'cancelled'
                        except OSError:
                            reason = 'cancelled'
                    if reason:
                        stop_reason.append(reason)
                        row['status'] = reason
                        stopped.set()
                        for sock in upstream_socket:
                            try: sock.shutdown(socket.SHUT_RDWR)
                            except OSError: pass
                        return

            try:
                parsed = urlsplit(self.path)
                is_native = native and parsed.path == '/backend-api/codex/responses' and not parsed.query
                if is_native:
                    identity = self.native_auth()
                    if identity is None: return
                    with catalog_lock: native_efforts = catalog.get(identity)
                    if native_efforts is None: raise ValueError('catalog required')
                if not is_native and (native or parsed.path not in PATHS or parsed.query not in ('', 'beta=true')):
                    return self.reply(404, b'{"error":"not found"}')
                if self.headers.get('Origin') or self.headers.get_content_type() != 'application/json':
                    raise ValueError('browser requests are not supported')
                if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length', [])) != 1:
                    raise ValueError('invalid framing')
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 1000000:
                    raise ValueError('invalid length')
                raw = bytearray()
                while len(raw) < length:
                    remaining = timeout - (time.monotonic()-started)
                    if remaining <= 0: raise TimeoutError()
                    self.connection.settimeout(remaining)
                    chunk = self.rfile.read1(min(length-len(raw), 16384))
                    if not chunk: raise ConnectionResetError()
                    raw.extend(chunk)
                data = json.loads(raw)
                if not isinstance(data, dict) or (not desktop and data.get('model') != 'open-model-router'):
                    raise ValueError('invalid model')
                if type(data.get('stream', False)) is not bool:
                    raise ValueError('invalid stream')
                session_headers = self.headers.get_all('X-OMR-Session', [])
                native_sessions = self.headers.get_all('session_id', []) if is_native else []
                if len(session_headers) > 1 or len(native_sessions) > 1:
                    raise ValueError('ambiguous session')
                session = str(uuid.UUID(session_headers[0])) if session_headers else None
                native_session = str(uuid.UUID(native_sessions[0])) if native_sessions else None
                if is_native:
                    if session and native_session and session != native_session: raise ValueError('conflicting sessions')
                    session = session or native_session
                    if not session: raise ValueError('native session required')
                row['session'] = session
                session_key = (identity, session) if is_native and session else session
                watcher = threading.Thread(target=watch, daemon=True)
                watcher.start()
                lock = None
                if session:
                    with session_lock:
                        if session_key not in sessions:
                            if len(sessions) >= config.get('max_sessions', 2048):
                                raise ValueError('session capacity; restart or use another server')
                            sessions[session_key] = {'lock': threading.Lock(), 'route': None}
                        state = sessions[session_key]
                    lock = state['lock']
                    while not lock.acquire(timeout=.025):
                        if stopped.is_set(): raise TimeoutError()
                else:
                    state = {'route': None}
                try:
                    if desktop:
                        # Native Chat pins the config that the user selected.
                        # Fence validation and selection under the same lock.
                        revision = self.headers.get('X-OMR-Config-Revision')
                        if revision is None:
                            selected, route = desktop.select(data, PATHS[parsed.path], session, row, stopped, started+timeout, refresh=True)
                        else:
                            with desktop.lock:
                                if revision != str(desktop.revision) or not isinstance(data.get('model'), str) or not any(m['id'] == data['model'] for m in desktop.catalogue()['data']):
                                    raise ValueError('configuration_conflict')
                                selected, route = desktop.select(data, PATHS[parsed.path], session, row, stopped, started+timeout, refresh=True)
                    elif state['route'] is None:
                        decision_started = time.monotonic()
                        if decision['type'] == 'fixed':
                            selected = config['default_route']
                        elif decision['type'] == 'command':
                            result = command_decision(decision, first_prompt(data), stopped, started+timeout)
                            selected = result['route']
                            if isinstance(result.get('usage'), dict):
                                row['decision_usage'] = {k: result['usage'][k] for k in ('input_tokens', 'output_tokens') if type(result['usage'].get(k)) is int and result['usage'][k] >= 0}
                        elif decision['type'] == 's1d1':
                            if classifier is None: raise ValueError('classifier unavailable')
                            result = classifier.route([first_prompt(data)])[0]
                            score = result['complexity_score']
                            if not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 1:
                                raise ValueError('invalid classification')
                            selected = decision['low_route'] if score < decision['threshold'] else decision['high_route']
                            row['classification'] = {'complexity_score': score}
                            if type(result.get('prompt_tokens')) is int and 0 <= result['prompt_tokens'] <= 10**6:
                                row['classification']['prompt_tokens'] = result['prompt_tokens']
                            row['decision_provenance'] = 'real-local-s1d1-verified'
                            row['policy'] = {k: decision[k] for k in ('threshold', 'low_route', 'high_route')}
                        else:
                            raise ValueError('unknown decider')
                        if not isinstance(selected, str) or selected not in config['routes']:
                            raise ValueError('unknown selected route; no fallback')
                        state['route'] = selected
                        row['decision_ms'] = (time.monotonic()-decision_started)*1000
                    if not desktop: selected = state['route']
                finally:
                    if lock: lock.release()
                if stopped.is_set(): raise TimeoutError()
                if not desktop: route = config['routes'][selected]
                protocols = route['protocol'] if isinstance(route['protocol'], list) else [route['protocol']]
                protocol = 'responses' if is_native else PATHS[parsed.path]
                if protocol not in protocols:
                    raise ValueError('incompatible protocol')
                row.update(route=selected, model_requested=route['model'])
                data['model'] = route['model']
                effort = route.get('effort')
                if is_native:
                    reasoning = data.get('reasoning', {})
                    if not isinstance(reasoning, dict): raise ValueError('invalid reasoning')
                    requested_effort = effort if effort is not None else reasoning.get('effort')
                    if requested_effort is not None and requested_effort not in native_efforts: raise ValueError('unsupported native effort')
                if effort is not None:
                    row['effort_transmitted'] = effort
                    if protocol == 'chat':
                        data['reasoning_effort'] = effort
                    elif protocol == 'responses':
                        data.setdefault('reasoning', {})['effort'] = effort
                    elif effort == 'none':
                        data['thinking'] = {'type': 'disabled'}
                    else:
                        data['thinking'] = {'type': 'adaptive'}
                        data.setdefault('output_config', {})['effort'] = effort
                url = urlsplit(route['url'])
                endpoint = '/backend-api/codex/responses' if is_native else (url.path if url.path in PATHS else url.path.rstrip('/') + parsed.path.removeprefix('/v1'))
                # The SDK receives a validated provider base, not a composed HTTP endpoint.
                if route.get('transport') == 'pi-ai' and desktop:
                    endpoint = parsed.path
                if endpoint != parsed.path:
                    raise ValueError('incompatible endpoint')
                if parsed.query:
                    endpoint += '?' + parsed.query
                payload = json.dumps(data).encode()
                remaining = timeout - (time.monotonic()-started)
                if remaining <= 0:
                    raise TimeoutError()
                if desktop and route.get('transport') == 'pi-ai':
                    from desktop_pi import PiConnection
                    row['transport'] = 'pi-ai'
                    connection = PiConnection(route, protocol, stopped, started + timeout)
                else:
                    cls = http.client.HTTPSConnection if url.scheme == 'https' else http.client.HTTPConnection
                    connection = cls(url.hostname, 443 if is_native else url.port, timeout=remaining,
                                     **({'context': desktop.tls_context} if desktop and url.scheme == 'https' else {}))
                connection.connect()
                if connection.sock is not None: upstream_socket.append(connection.sock)
                if stopped.is_set():
                    raise TimeoutError()
                headers = {'Content-Type': 'application/json', 'Accept-Encoding': 'identity',
                           'Accept': 'text/event-stream' if data.get('stream') else 'application/json'}
                if is_native: headers.update(self.native_headers())
                for name in (() if is_native else ('anthropic-version', 'anthropic-beta')):
                    if self.headers.get(name): headers[name] = self.headers[name]
                if not is_native and route.get('forward_auth'):
                    for name in ('Authorization', 'x-api-key', 'chatgpt-account-id', 'OpenAI-Beta', 'User-Agent'):
                        if self.headers.get(name): headers[name] = self.headers[name]
                if desktop and route.get('_secret'):
                    headers['x-api-key' if protocol == 'anthropic' else 'Authorization'] = route['_secret'] if protocol == 'anthropic' else 'Bearer ' + route['_secret']
                row['status'] = 'upstream_error'
                connection.request('POST', endpoint, payload, headers)
                response = connection.getresponse()
                row['upstream_status'] = response.status
                if desktop and route.get('transport') == 'pi-ai' and response.status == 400:
                    row['status'] = 'invalid_request'
                    row['error'] = 'unsupported_pi_ai_option'
                    return self.reply(400, b'{"error":{"type":"unsupported_pi_ai_option","message":"Request option is not supported by pi-ai transport."}}')
                if not 200 <= response.status < 300:
                    status = response.status if 400 <= response.status < 600 else 502
                    return self.reply(status, b'{"error":{"type":"upstream_error","message":"Upstream rejected the request; no retry performed."}}')
                if response.getheader('Content-Encoding', 'identity') != 'identity':
                    raise ValueError('unsupported response encoding')
                is_stream = bool(data.get('stream'))
                content_type = response.getheader('Content-Type')
                headerless_native = is_stream and is_native and content_type is None
                if is_stream and not headerless_native and (content_type is None or ('text/event-stream' not in content_type if not is_native else content_type.split(';', 1)[0].strip().lower() != 'text/event-stream')):
                    raise ValueError('expected SSE response')
                if headerless_native: row['stream_provenance'] = 'native_absent_content_type'
                def send_upstream_headers():
                    self.send_response(response.status)
                    if content_type is not None: self.send_header('Content-Type', content_type)
                    elif not is_stream: self.send_header('Content-Type', 'application/json')
                    self.send_header('Connection', 'close')
                    self.send_header('X-OMR-Route', row['route'])
                    self.send_header('X-OMR-Effort', row['effort_transmitted'] or 'unverified')
                    self.send_header('X-OMR-Decision-Ms', str(row['decision_ms']))
                    self.send_header('X-OMR-Request', row['request_id'])
                    self.end_headers()
                    self.close_connection = True
                if not headerless_native:
                    send_upstream_headers()
                    headers_sent = True
                total = 0
                buffered = b''
                event_lines = []
                event_frame = bytearray()
                event_kind = b''
                event_size = 0
                terminal_seen = False
                provider_failed = False
                while not stopped.is_set():
                    chunk = response.read1(16384)
                    if not chunk: break
                    total += len(chunk)
                    if total > 16_000_000:
                        raise ValueError('response limit')
                    if not is_stream:
                        self.wfile.write(chunk); self.wfile.flush()
                    buffered += chunk
                    if is_stream:
                        while b'\n' in buffered:
                            line, buffered = buffered.split(b'\n', 1)
                            event_frame.extend(line + b'\n')
                            if len(event_frame) > 1_000_000: raise ValueError('event limit')
                            line = line.removesuffix(b'\r')
                            if headerless_native and line and not line.startswith(b':') and line.partition(b':')[0] not in (b'event', b'data', b'id', b'retry'):
                                raise ValueError('invalid SSE field')
                            if line.startswith(b'event:'):
                                event_kind = line[6:].strip()
                            if line.startswith(b'data:'):
                                event_lines.append(line[5:].removeprefix(b' '))
                                event_size += len(line)
                                if event_size > 1_000_000: raise ValueError('event limit')
                            elif not line:
                                if event_kind in (b'error', b'response.failed', b'response.incomplete'): raise ValueError('upstream event error')
                                event_data = b'\n'.join(event_lines)
                                event_lines.clear(); event_size = 0
                                if headerless_native:
                                    event_frame.decode('utf-8', errors='strict')
                                    if event_data.strip() == b'[DONE]':
                                        if not terminal_seen: raise ValueError('premature done')
                                    else:
                                        event = json.loads(event_data.decode('utf-8'), parse_constant=lambda _: (_ for _ in ()).throw(ValueError('invalid JSON')))
                                        kind = validate_native_event(event, not headers_sent, terminal_seen)
                                        if event_kind and event_kind.decode('utf-8') != kind: raise ValueError('event type mismatch')
                                        observe(event, row)
                                        if kind == 'response.completed': terminal_seen = True
                                    if not headers_sent:
                                        send_upstream_headers(); headers_sent = True
                                elif event_data.strip() == b'[DONE]':
                                    terminal_seen = terminal_seen or protocol == 'chat'
                                else:
                                    try:
                                        event = json.loads(event_data)
                                        observe(event, row)
                                        if isinstance(event, dict):
                                            kind = event.get('type')
                                            if kind == 'response.completed' and protocol == 'responses': terminal_seen = True
                                            if kind == 'message_stop' and protocol == 'anthropic': terminal_seen = True
                                            if 'error' in event or kind in ('error', 'response.failed', 'response.incomplete'): raise ValueError('upstream event error')
                                    except (json.JSONDecodeError, UnicodeError): pass
                                self.wfile.write(event_frame); self.wfile.flush()
                                event_frame.clear(); event_kind = b''
                        if len(buffered) > 1_000_000:
                            raise ValueError('event limit')
                if stopped.is_set():
                    row['status'] = stop_reason[0]
                    if row['status'] == 'timeout': raise TimeoutError()
                if not is_stream and not stopped.is_set():
                    observe(json.loads(buffered), row)
                if not stopped.is_set() and (response.length not in (None, 0) or (is_stream and (not terminal_seen or provider_failed or (headerless_native and (buffered or event_frame))))):
                    raise ValueError('incomplete or failed upstream response')
                if not stopped.is_set(): row['status'] = 'completed'
            except (OSError, http.client.HTTPException, ValueError, KeyError, TypeError) as exc:
                if desktop: row['error'] = desktop.safe_error(exc)
                if stopped.is_set(): row['status'] = stop_reason[0]
                if (stopped.is_set() and row['status'] == 'cancelled') or (isinstance(exc, (BrokenPipeError, ConnectionResetError)) and not isinstance(exc, http.client.RemoteDisconnected) and not (stopped.is_set() and row['status'] == 'timeout')):
                    row['status'] = 'cancelled'
                    return
                if not stopped.is_set():
                    row['status'] = 'timeout' if isinstance(exc, TimeoutError) else ('invalid_request' if connection is None else 'upstream_error')
                if not headers_sent:
                    status = 400 if row['status'] == 'invalid_request' else (504 if row['status'] == 'timeout' else 502)
                    try: self.reply(status, json.dumps({'error': {'type': row['status'], 'message': 'Request failed; inspect the local receipt.'}}).encode())
                    except OSError: pass
                elif row['status'] != 'cancelled':
                    error = {'type': 'error', 'error': {'type': row['status'], 'message': 'Upstream stream failed or ended before its terminal event.'}}
                    try:
                        self.wfile.write(('event: error\ndata: '+json.dumps(error)+'\n\n').encode()); self.wfile.flush()
                    except OSError: pass
            finally:
                done.set()
                if connection is not None: connection.close()
                if response is not None: response.close()
                if watcher is not None: watcher.join(.2)
                row['elapsed_ms'] = (time.monotonic()-started)*1000
                if row.get('transport') == 'pi-ai':
                    # Encoder defaults are not observations; use only the
                    # adapter's raw-SSE callback metadata on the private IPC.
                    metadata = getattr(connection, 'metadata', {})
                    row['model_observed'] = None
                    row.pop('model_identity_unrecognized', None)
                    row['usage'] = {}
                    observe(metadata, row)
                    if metadata.get('model_conflict') is True:
                        row['model_observed'] = None
                        row['model_identity_unrecognized'] = True
                    row['model_identity_source'] = 'provider_sse' if row['model_observed'] else 'not_reported'
                    row['pi_ai_bridge_status'] = row['upstream_status']
                    actual_status = metadata.get('status')
                    row['upstream_status'] = actual_status if type(actual_status) is int and 100 <= actual_status <= 599 else None
                if desktop:
                    try:
                        desktop.record(row)
                    finally:
                        with desktop.lock: desktop.active -= 1
                if config.get('receipts'):
                    with receipt_lock:
                        with open(config['receipts'], 'a', encoding='utf-8') as out:
                            out.write(json.dumps(row, allow_nan=False)+'\n')
    return Handler


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action', required=True)
    serve = sub.add_parser('serve')
    serve.add_argument('--config', required=True)
    serve.add_argument('--port', type=int, required=True)
    args = parser.parse_args()
    with open(args.config, encoding='utf-8') as f:
        config = json.load(f)

    server = ThreadingHTTPServer(('127.0.0.1', args.port), handler(config))
    print(server.server_port, flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
