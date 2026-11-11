import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError('expected finite nonnegative number')
    return value

def stats(values):
    return {'mean': statistics.fmean(values), 'stdev_population': statistics.pstdev(values)} if values else None

def compare(path):
    groups = defaultdict(list)
    for line in Path(path).read_text().splitlines():
        row = json.loads(line)
        key = tuple(row[k] for k in ('case', 'split', 'family', 'arm'))
        if not all(isinstance(v, str) and v for v in key) or key[1] not in ('dev', 'validation') or key[3] not in ('default', 's1d1', 'configurable'):
            raise ValueError('invalid case, split, family or arm')
        if type(row['success']) is not bool:
            raise ValueError('success must be boolean')
        elapsed = number(row['elapsed_ms'])
        usage, rates = row['usage'], row['rates']
        if usage is None:
            if row['success'] or rates is not None: raise ValueError('invalid unknown usage')
            groups[key].append((row, elapsed, None, None)); continue
        if not isinstance(usage, dict) or not usage or not isinstance(rates, dict) or not set(usage) <= set(rates):
            raise ValueError('missing observed usage or tariff')
        value = sum(number(n) * number(rates[k]) / 1_000_000 for k, n in usage.items())
        value += number(row['decision_cost']) + number(row['retry_cost'])
        baseline = row.get('baseline_rates')
        if baseline is not None:
            if not isinstance(baseline, dict) or not set(usage) <= set(baseline): raise ValueError('missing baseline tariff')
            baseline = sum(number(n) * number(baseline[k]) / 1_000_000 for k,n in usage.items())
        groups[key].append((row, elapsed, number(value), baseline))
    if not groups: raise ValueError('no runs')
    result = []
    for key, rows in sorted(groups.items()):
        categories = set().union(*(set(x[0]['usage'] or {}) for x in rows))
        result.append(dict(zip(('case', 'split', 'family', 'arm'), key), runs=len(rows), failures=sum(not x[0]['success'] for x in rows), failure_rate=sum(not x[0]['success'] for x in rows)/len(rows), elapsed_ms=stats([x[1] for x in rows]), equivalent_value=stats([x[2] for x in rows if x[2] is not None]), baseline_same_volume_estimate=stats([x[3] for x in rows if x[3] is not None]), usage={k: stats([number(x[0]['usage'][k]) for x in rows if x[0]['usage'] is not None and k in x[0]['usage']]) for k in sorted(categories)}, unknown_usage_runs=sum(x[0]['usage'] is None for x in rows)))
    return result

if __name__ == '__main__':
    try:
        if len(sys.argv) != 2: raise ValueError('usage: python3 compare.py results.jsonl')
        print(json.dumps(compare(sys.argv[1]), indent=2, allow_nan=False))
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        print(f'invalid input: {exc}', file=sys.stderr)
        sys.exit(1)
