import argparse
import json
import math
import os
import subprocess
import sys
import time


def command_decider(cmd, timeout):
    if not isinstance(cmd, list) or not cmd or any(not isinstance(x, str) or not x for x in cmd):
        raise ValueError('invalid decision command')
    def decide(prompt):
        result = subprocess.run(cmd, input=json.dumps({'prompt': prompt}), text=True, capture_output=True, timeout=timeout, check=True, env={})
        decision = json.loads(result.stdout)
        if not isinstance(decision, dict) or decision.get('route') not in ('low', 'high'):
            raise ValueError('invalid decision route')
        return decision
    return decide


def run(request, config, classify):
    messages = request['messages']
    prompt = next((m['content'] for m in messages if m.get('role') == 'user'), None)
    if not isinstance(prompt, str) or not prompt:
        raise ValueError('first user message required')
    threshold = config['threshold']
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError('invalid threshold')
    timeout = config['timeout_seconds']
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 600:
        raise ValueError('invalid timeout')
    start = time.monotonic()
    decision = classify(prompt)
    if 'route' in decision:
        route = decision['route']
        if route not in ('low', 'high'):
            raise ValueError('invalid decision route')
    else:
        score = decision['complexity_score']
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError('invalid score')
        route = 'high' if score >= threshold else 'low'
    cmd = config['routes'][route]
    if not isinstance(cmd, list) or not cmd or any(not isinstance(x, str) or not x for x in cmd):
        raise ValueError('invalid route command')
    result = subprocess.run(cmd, input=json.dumps(request), text=True, capture_output=True, timeout=timeout, check=True, env={})
    payload = json.loads(result.stdout)
    if not isinstance(payload, dict) or not isinstance(payload.get('answer'), str) or not isinstance(payload.get('usage'), dict):
        raise ValueError('invalid route response')
    return {'route': route, 'decision': decision, 'elapsed_ms': round((time.monotonic()-start)*1000, 3), 'result': payload}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights')
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    with open(args.config, encoding='utf-8') as f:
        config = json.load(f)
    request = json.load(sys.stdin)
    if 'decision_command' in config:
        decide = command_decider(config['decision_command'], config['timeout_seconds'])
    else:
        if not args.weights or not os.path.isdir(args.weights):
            parser.error('weights must be an existing local directory for s1d1')
        from s1d1_upstream import Router
        router = Router(args.weights)
        decide = lambda prompt: router.route([prompt])[0]
    print(json.dumps(run(request, config, decide), ensure_ascii=False))

if __name__ == '__main__':
    main()
