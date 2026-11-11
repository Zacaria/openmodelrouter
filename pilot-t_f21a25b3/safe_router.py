"""Minimal opt-in request envelope; trusted commands are not sandboxed."""
import argparse
import json
import math
import subprocess
import sys
import time


def run(request, config, decide):
    if not isinstance(request, dict) or set(request) != {'messages'}:
        raise ValueError('only explicitly supplied messages are accepted')
    messages = request['messages']
    if not isinstance(messages, list) or not messages:
        raise ValueError('messages required')
    for m in messages:
        if (not isinstance(m, dict) or set(m) != {'role', 'content'}
                or m['role'] not in ('user', 'assistant', 'system')
                or not isinstance(m['content'], str)):
            raise ValueError('invalid message')
    prompt = next((m['content'] for m in messages if m['role'] == 'user'), None)
    if not prompt:
        raise ValueError('first user message required')
    timeout = config['timeout_seconds']
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 600:
        raise ValueError('invalid timeout')
    routes = config['routes']
    if not isinstance(routes, dict) or not routes:
        raise ValueError('routes required')
    for name, entry in routes.items():
        if (not isinstance(name, str) or not name or not isinstance(entry, dict)
                or set(entry) != {'command', 'model', 'effort'}
                or not isinstance(entry['command'], list) or not entry['command']
                or any(not isinstance(x, str) or not x for x in entry['command'])
                or any(not isinstance(entry[k], str) or not entry[k] for k in ('model', 'effort'))):
            raise ValueError('invalid route')
    if 'fallback' in config and config['fallback'] not in routes:
        raise ValueError('invalid fallback')
    start = time.monotonic()
    try:
        route = decide(prompt)
        if not isinstance(route, str) or route not in routes:
            raise ValueError('invalid decision')
        fallback_reason = None
    except Exception as exc:
        if 'fallback' not in config:
            raise
        route = config['fallback']
        fallback_reason = type(exc).__name__
    entry = routes[route]
    result = subprocess.run(entry['command'], input=json.dumps({'messages': messages}),
                            text=True, capture_output=True, timeout=timeout, check=True, env={})
    payload = json.loads(result.stdout)
    if not isinstance(payload, dict) or not isinstance(payload.get('answer'), str) or not isinstance(payload.get('usage'), dict):
        raise ValueError('invalid generator response')
    return {'route': route, 'model': entry['model'], 'effort': entry['effort'],
            'fallback_reason': fallback_reason, 'elapsed_ms': (time.monotonic()-start)*1000,
            'result': payload}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    with open(args.config, encoding='utf-8') as f:
        config = json.load(f)
    command = config['decision_command']
    if not isinstance(command, list) or not command or any(not isinstance(x, str) or not x for x in command):
        raise ValueError('invalid decision command')
    def decide(prompt):
        p = subprocess.run(command, input=json.dumps({'prompt': prompt}), text=True,
                           capture_output=True, timeout=config['timeout_seconds'], check=True, env={})
        result = json.loads(p.stdout)
        return result['route']
    print(json.dumps(run(json.load(sys.stdin), config, decide), ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
