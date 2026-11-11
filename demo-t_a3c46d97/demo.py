"""Synthetic comparator using the session loop; trusted local commands only."""
import argparse
import hashlib
import importlib.metadata
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'loop-t_daf181c7'))
sys.path.insert(0, str(ROOT / 'integrated-t_dab1958b'))
from loop import Session, safe_router_decider
from fixtures import cases

ARMS = ('default', 's1d1', 'configurable')


def classifier_decider(classify, threshold, low, high, provenance):
    def decide(prompt):
        decide.classification = classify(prompt)
        return high if decide.classification['complexity_score'] >= threshold else low
    decide.classification = None
    decide.identity = provenance if isinstance(provenance, dict) else None
    decide.provenance = 'real-local-identity-unknown' if decide.identity else provenance
    decide.policy = {'threshold': threshold, 'low_route': low, 'high_route': high}
    return decide


def fingerprint(folder):
    """Fingerprint the full local snapshot; identity remains unverified."""
    root = Path(folder)
    files = {}
    for path in sorted(root.rglob('*')):
        if path.is_file():
            digest = hashlib.sha256()
            with path.open('rb') as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b''):
                    digest.update(chunk)
            files[str(path.relative_to(root))] = digest.hexdigest()
    return files


def execute(case, arm, config, decide):
    row = {'case':case['id'], 'family':case['family'], 'split':case['split'], 'arm':arm,
           'state':'unavailable', 'reason':None, 'evaluation':None, 'receipts':[],
           'input_provenance':'synthetic', 'decision_provenance':None, 'elapsed_ms':None}
    start = time.monotonic()
    try:
        if case['family'] in ('code', 'agents'):
            row['reason'] = 'isolation not verified' if case['family'] == 'code' else 'subagent permission adapter missing'
            return row
        if decide is None:
            row['reason'] = 's1d1 classifier and route policy unavailable' if arm == 's1d1' else 'decider unavailable'
            return row
        row['decision_provenance'] = getattr(decide, 'provenance', 'configured-local' if arm == 'configurable' else 'simulated')
        if arm == 's1d1' and getattr(decide, 'identity', None):
            row['classifier_identity'] = decide.identity
            policy = dict(decide.policy)
            for level in ('low', 'high'):
                name = policy[level + '_route']
                policy[level] = {k: config['routes'][name].get(k) for k in ('model', 'effort')}
            row['route_policy'] = policy
        if arm == 's1d1' and hasattr(decide, 'classification'):
            decide.classification = None
        session_config = dict(config)
        if arm == 's1d1':
            session_config.pop('fallback', None)  # Never silently replace a failed baseline.
        session = Session(session_config, decide)
        messages = []
        answers = []
        for prompt in case['prompts']:
            messages.append({'role':'user', 'content':prompt})
            result = session.run({'messages':messages})
            if arm == 's1d1':
                row['classification'] = getattr(decide, 'classification', None)
            answer = result['result']['answer']
            answers.append(answer)
            messages.append({'role':'assistant', 'content':answer})
            row['receipts'].append({'route':result['route'], 'model_requested':result['model'],
                'effort_requested':result['effort'], 'model_applied':result['model_applied'],
                'effort_applied':result['effort_applied'], 'fallback_reason':result['fallback_reason'],
                'elapsed_ms':result['elapsed_ms'], 'usage':result['result'].get('usage'),
                'generation_provenance':result['result'].get('provenance')})
        row['state'] = 'executed'
        if case['expected'] is None:
            row['reason'] = 'human blind evaluation unavailable'
        else:
            row['evaluation'] = 'pass' if len(answers) == len(case['expected']) and all(a.strip() == b for a,b in zip(answers,case['expected'])) else 'fail'
    except Exception as exc:
        row['state'] = 'error'
        row['reason'] = type(exc).__name__
    finally:
        row['elapsed_ms'] = (time.monotonic()-start)*1000
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--weights')
    parser.add_argument('--threshold', type=float)
    parser.add_argument('--low-route')
    parser.add_argument('--high-route')
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    default = config['default_route']
    decide = safe_router_decider(config)
    baseline = None
    baseline_error = None
    if any(x is not None for x in (args.weights, args.threshold, args.low_route, args.high_route)):
        if not (args.weights and args.threshold is not None and 0 <= args.threshold <= 1 and args.low_route in config['routes'] and args.high_route in config['routes']):
            parser.error('weights, threshold (0..1), low-route and high-route must all be provided')
        try:
            if not Path(args.weights).is_dir():
                raise ValueError('weights must be an existing local directory')
            sys.path.insert(0, str(ROOT / 'pilot-t_f21a25b3'))
            from s1d1_upstream import Router
            before = fingerprint(args.weights)
            model = Router(args.weights)
            if before != fingerprint(args.weights):
                raise ValueError('snapshot changed during loading')
            versions = {}
            for package in ('numpy', 'tokenizers', 'onnxruntime'):
                try:
                    versions[package] = importlib.metadata.version(package)
                except importlib.metadata.PackageNotFoundError:
                    versions[package] = None
            identity = {'status': 'unknown', 'backend': model.backend, 'files_sha256': before, 'runtime_versions': versions}
            baseline = classifier_decider(lambda p: model.route([p])[0], args.threshold, args.low_route, args.high_route, identity)
        except Exception as exc:
            baseline_error = type(exc).__name__
    rng = random.Random(args.seed)
    rows = []
    for case in cases():
        order = list(ARMS); rng.shuffle(order)
        for index, arm in enumerate(order):
            decider = (lambda _: default) if arm == 'default' else (decide if arm == 'configurable' else baseline)
            row = execute(case, arm, config, decider)
            if arm == 's1d1' and baseline_error and row['state'] == 'unavailable' and case['family'] not in ('code', 'agents'):
                row['reason'] = 's1d1 initialization failed: ' + baseline_error
            row.update(seed=args.seed, order=index)
            rows.append(row)
    with open(args.output, 'x', encoding='utf-8') as output:
        for row in rows:
            output.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
    print(json.dumps({'planned':len(rows), 'executed':sum(r['state']=='executed' for r in rows),
        'unavailable':sum(r['state']=='unavailable' for r in rows), 'errors':sum(r['state']=='error' for r in rows),
        'passed':sum(r['evaluation']=='pass' for r in rows), 'failed':sum(r['evaluation']=='fail' for r in rows)}, ensure_ascii=False))


if __name__ == '__main__': main()
