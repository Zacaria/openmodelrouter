"""Session-scoped adapter for the local, trusted-command router."""
import argparse
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'pilot-t_f21a25b3'))
import safe_router

MAX_BYTES = 100_000


class Session:
    def __init__(self, config, decide):
        self.config = copy.deepcopy(config)
        self.decide = decide
        self.route = None
        self.fallback_reason = None
        self.expected_prefix = None

    def run(self, request):
        if not isinstance(request, dict) or set(request) != {'messages'}:
            raise ValueError('only messages are supported')
        messages = request['messages']
        if not isinstance(messages, list) or not messages:
            raise ValueError('messages required')
        for message in messages:
            if (not isinstance(message, dict) or set(message) != {'role', 'content'}
                    or message['role'] not in ('system', 'user', 'assistant')
                    or not isinstance(message['content'], str)):
                raise ValueError('invalid message')
        if len(json.dumps(request, ensure_ascii=False).encode('utf-8')) > MAX_BYTES:
            raise ValueError('request too large')
        if self.expected_prefix is not None:
            if (messages[:len(self.expected_prefix)] != self.expected_prefix
                    or len(messages) != len(self.expected_prefix) + 1
                    or messages[-1]['role'] != 'user'):
                raise ValueError('conversation history changed')
        if self.route is None:
            result = safe_router.run(request, self.config, self.decide)
            self.route = result['route']
            self.fallback_reason = result['fallback_reason']
        else:
            result = safe_router.run(request, self.config, lambda _: self.route)
            result['fallback_reason'] = self.fallback_reason
        result['model_applied'] = result['result'].get('model_applied')
        result['effort_applied'] = result['result'].get('effort_applied')
        self.expected_prefix = copy.deepcopy(messages) + [{'role': 'assistant', 'content': result['result']['answer']}]
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    try:
        config = json.loads(Path(args.config).read_text(encoding='utf-8'))
        decide = safe_router_decider(config)
        request = json.load(sys.stdin)
        print(json.dumps(Session(config, decide).run(request), ensure_ascii=False, allow_nan=False))
    except Exception as exc:
        print(json.dumps({'error': type(exc).__name__}), file=sys.stderr)
        return 1
    return 0


def safe_router_decider(config):
    import subprocess
    cmd = config['decision_command']
    if not isinstance(cmd, list) or not cmd or any(not isinstance(x, str) or not x for x in cmd):
        raise ValueError('invalid decision command')
    def decide(prompt):
        output = subprocess.run(cmd, input=json.dumps({'prompt': prompt}), text=True,
                                capture_output=True, timeout=config['timeout_seconds'], check=True, env={})
        return json.loads(output.stdout)['route']
    return decide


if __name__ == '__main__':
    sys.exit(main())
