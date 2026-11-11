import json
import math
import subprocess
import sys
import time
from pathlib import Path

ARMS = ('default', 's1d1', 'configurable')

def main(config_path, cases_path, output):
    config = json.loads(Path(config_path).read_text())
    cases = json.loads(Path(cases_path).read_text())
    arms = config['arms']
    if set(arms) != set(ARMS) or any(not isinstance(c, list) or not c or any(not isinstance(x, str) or not x for x in c) for c in arms.values()):
        raise ValueError('three command arrays required')
    reps, timeout = config['repetitions'], config['timeout_seconds']
    if type(reps) is not int or not 1 <= reps <= 1000 or isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 600:
        raise ValueError('invalid repetitions or timeout')
    if config['provenance'] not in ('simulated', 'real-local') or not isinstance(cases, list) or not cases:
        raise ValueError('invalid provenance or cases')
    seen = set()
    for case in cases:
        if any(not isinstance(case.get(k), str) or not case[k] for k in ('case', 'family', 'expected')) or case.get('split') not in ('dev', 'validation') or not isinstance(case.get('request'), dict) or case['case'] in seen:
            raise ValueError('invalid or duplicated case')
        seen.add(case['case'])
    with open(output, 'x', encoding='utf-8') as out:
        for case in cases:
            for rep in range(reps):
                for arm in ARMS:
                    start = time.monotonic()
                    row = {k: case[k] for k in ('case', 'split', 'family')}
                    row.update(arm=arm, repetition=rep, provenance=config['provenance'], success=False, usage=None, rates=None, decision_cost=None, retry_cost=None)
                    try:
                        p = subprocess.run(arms[arm], input=json.dumps(case['request']), text=True, capture_output=True, timeout=timeout, check=True, env={})
                        response = json.loads(p.stdout)
                        if not isinstance(response, dict) or not isinstance(response.get('answer'), str) or not isinstance(response.get('usage'), dict) or not isinstance(response.get('rates'), dict):
                            raise ValueError('invalid response')
                        row.update(success=response['answer'] == case['expected'], usage=response['usage'], rates=response['rates'], decision_cost=response['decision_cost'], retry_cost=response['retry_cost'])
                        if 'baseline_rates' in config:
                            row['baseline_rates'] = config['baseline_rates']
                    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError, ValueError, KeyError, TypeError) as e:
                        row['error'] = type(e).__name__
                    row['elapsed_ms'] = (time.monotonic() - start) * 1000
                    out.write(json.dumps(row, allow_nan=False) + '\n'); out.flush()

if __name__ == '__main__':
    try:
        if len(sys.argv) != 4: raise ValueError('usage: benchmark.py config.json cases.json output.jsonl')
        main(*sys.argv[1:])
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f'benchmark error: {e}', file=sys.stderr); sys.exit(1)
