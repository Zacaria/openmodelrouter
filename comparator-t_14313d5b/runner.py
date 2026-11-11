"""Offline synthetic comparison. Adapters are trusted code, not a sandbox."""
import argparse
import json
import random
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'integrated-t_dab1958b'))
from fixtures import cases

ARMS = ('default', 's1d1', 'configurable')
ROUTE = {'model': 'synthetic-default', 'effort': 'none'}


def synthetic_generate(prompt, prior, route):
    return 'simulated response'


def execute(case, arm, classify=None, decide=None, generate=synthetic_generate):
    row = {'case': case['id'], 'family': case['family'], 'split': case['split'],
           'arm': arm, 'state': 'unavailable', 'reason': None, 'evaluation': None,
           'provenance': {'input': 'synthetic', 'decision': None, 'generation': None},
           'route': None, 'effort_applied': None, 'usage': None, 'cost': None,
           'classification': None, 'decision_ms': None, 'generation_ms': None,
           'elapsed_ms': None, 'turns_completed': 0}
    start = time.monotonic()
    try:
        if case['family'] in ('code', 'agents'):
            row['reason'] = 'isolation not verified' if case['family'] == 'code' else 'subagent permission adapter missing'
            return row
        if arm == 's1d1' and classify is None:
            row['reason'] = 's1d1 classifier or local weights unavailable'
            return row
        decision_start = time.monotonic()
        if arm == 's1d1':
            row['classification'] = classify(case['prompts'][0])
            row['provenance']['decision'] = 'real-local'
            route = dict(ROUTE)
        elif arm == 'configurable':
            route = (decide or (lambda prompt: dict(ROUTE)))(case['prompts'][0])
            row['provenance']['decision'] = 'simulated'
        elif arm == 'default':
            route = dict(ROUTE)
        else:
            raise ValueError('invalid arm')
        row['decision_ms'] = (time.monotonic() - decision_start) * 1000
        if route != ROUTE:
            raise ValueError('route not in synthetic allowlist')
        row['route'] = dict(route)
        row['provenance']['generation'] = 'simulated'
        generation_start = time.monotonic()
        history = []
        for prompt in case['prompts']:
            answer = generate(prompt, list(history), dict(route))
            if not isinstance(answer, str):
                raise ValueError('invalid answer')
            history.append((prompt, answer))
            row['turns_completed'] += 1
        row['generation_ms'] = (time.monotonic() - generation_start) * 1000
        row['state'] = 'executed'
        if case['expected'] is not None:
            row['evaluation'] = 'pass' if len(history) == len(case['expected']) and all(
                answer.strip() == expected for (_, answer), expected in zip(history, case['expected'])
            ) else 'fail'
        else:
            row['reason'] = 'human blind evaluation unavailable'
    except Exception as exc:
        row['state'] = 'error'
        row['reason'] = type(exc).__name__
    finally:
        row['elapsed_ms'] = (time.monotonic() - start) * 1000
    return row


def run(fixtures, seed=0, repetitions=1, classify=None, decide=None, generate=synthetic_generate):
    if type(repetitions) is not int or not 1 <= repetitions <= 100:
        raise ValueError('repetitions must be 1..100')
    rng = random.Random(seed)
    rows = []
    for case in fixtures:
        for repetition in range(repetitions):
            order = list(ARMS)
            rng.shuffle(order)
            for index, arm in enumerate(order):
                row = execute(case, arm, classify, decide, generate)
                row.update(repetition=repetition, order=index, seed=seed)
                rows.append(row)
    return rows


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        key = (row['split'], row['family'], row['arm'], json.dumps(row['provenance'], sort_keys=True))
        groups[key].append(row)
    output = []
    for (split, family, arm, provenance), group in sorted(groups.items()):
        executed = [r for r in group if r['state'] == 'executed']
        evaluated = [r for r in executed if r['evaluation'] in ('pass', 'fail')]
        times = [r['elapsed_ms'] for r in executed]
        output.append({'split': split, 'family': family, 'arm': arm, 'provenance': json.loads(provenance),
                       'planned': len(group), 'executed': len(executed), 'evaluated': len(evaluated),
                       'passed': sum(r['evaluation'] == 'pass' for r in evaluated),
                       'failed': sum(r['evaluation'] == 'fail' for r in evaluated),
                       'errors': sum(r['state'] == 'error' for r in group),
                       'unavailable': sum(r['state'] == 'unavailable' for r in group),
                       'elapsed_mean_ms': statistics.fmean(times) if times else None,
                       'elapsed_stdev_ms': statistics.pstdev(times) if times else None})
    return output


def local_classifier(weights):
    if not Path(weights).is_dir():
        raise ValueError('weights must be an existing local directory')
    sys.path.insert(0, str(ROOT / 'pilot-t_f21a25b3'))
    from s1d1_upstream import Router
    model = Router(weights)
    return lambda prompt: model.route([prompt])[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--weights')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--repetitions', type=int, default=1)
    parser.add_argument('--output')
    parser.add_argument('--summary')
    args = parser.parse_args()
    if args.summary:
        if args.output or args.weights:
            parser.error('--summary cannot be combined with --output or --weights')
        rows = [json.loads(line) for line in Path(args.summary).read_text().splitlines() if line.strip()]
        print(json.dumps(summarize(rows), ensure_ascii=False, indent=2, allow_nan=False))
        return
    if not args.output:
        parser.error('--output is required')
    classify = None
    error = None
    if args.weights:
        try:
            classify = local_classifier(args.weights)
        except Exception as exc:
            error = type(exc).__name__
    rows = run(cases(), seed=args.seed, repetitions=args.repetitions, classify=classify)
    if error:
        for row in rows:
            if row['arm'] == 's1d1' and row['state'] == 'unavailable' and row['family'] not in ('code', 'agents'):
                row['reason'] = 's1d1 initialization failed: ' + error
    with open(args.output, 'x', encoding='utf-8') as out:
        for row in rows:
            out.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
    print(json.dumps(summarize(rows), ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
