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
    return {'mean': statistics.fmean(values), 'stdev_population': statistics.pstdev(values)}

def compare(path):
    groups = defaultdict(list)
    for line in Path(path).read_text().splitlines():
        row = json.loads(line)
        key = tuple(row[k] for k in ('case', 'split', 'family', 'arm'))
        if not all(isinstance(v, str) and v for v in key) or key[1] not in ('dev', 'validation') or key[3] not in ('default', 's1d1', 'configurable'):
            raise ValueError('invalid case, split, family or arm')
        if type(row['success']) is not bool:
            raise ValueError('success must be boolean')
        usage, rates = row['usage'], row['rates']
        if not isinstance(usage, dict) or not usage or not isinstance(rates, dict) or not set(usage) <= set(rates):
            raise ValueError('missing observed usage or tariff')
        value = sum(number(n) * number(rates[k]) / 1_000_000 for k, n in usage.items())
        value += number(row['decision_cost']) + number(row['retry_cost'])
        groups[key].append((row['success'], number(row['elapsed_ms']), number(value)))
    if not groups:
        raise ValueError('no runs')
    return [dict(zip(('case', 'split', 'family', 'arm'), key), runs=len(rows), failures=sum(not x[0] for x in rows), failure_rate=sum(not x[0] for x in rows)/len(rows), elapsed_ms=stats([x[1] for x in rows]), equivalent_value=stats([x[2] for x in rows])) for key, rows in sorted(groups.items())]

if __name__ == '__main__':
    try:
        if len(sys.argv) != 2: raise ValueError('usage: python3 compare.py results.jsonl')
        print(json.dumps(compare(sys.argv[1]), indent=2, allow_nan=False))
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        print(f'invalid input: {exc}', file=sys.stderr)
        sys.exit(1)
