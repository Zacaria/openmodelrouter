"""Adapter for a synthetic benchmark; configured commands must be trusted."""
import json
import subprocess
import sys
from pathlib import Path

import router


def main():
    arm, path = sys.argv[1:]
    config = json.loads(Path(path).read_text())
    request = json.load(sys.stdin)
    if arm == 'default':
        result = subprocess.run(config['routes']['low'], input=json.dumps(request), text=True, capture_output=True, timeout=config['timeout_seconds'], check=True, env={})
        receipt = json.loads(result.stdout)
    elif arm == 'configurable':
        receipt = router.run(request, config, router.command_decider(config['decision_command'], config['timeout_seconds']))['result']
    elif arm == 's1d1':
        from s1d1_upstream import Router
        model = Router(config['weights'])
        receipt = router.run(request, config, lambda prompt: model.route([prompt])[0])['result']
    else:
        raise ValueError('unknown arm')
    print(json.dumps(receipt, allow_nan=False))

if __name__ == '__main__':
    main()
