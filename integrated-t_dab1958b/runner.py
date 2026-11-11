"""Produce a deterministic inventory of unexecuted comparison arms.

This is not an execution adapter and does not make inference calls.
"""
import argparse
import json
import random
from fixtures import cases

ARMS = ('default', 's1d1', 'configurable')
REASONS = {
    'default': 'host default model and effort not observed',
    's1d1': 'first-prompt classifier not connected to comparison runner',
    'configurable': 'decision and generation adapters not connected',
}

def run(fixtures, seed=0):
    rng = random.Random(seed)
    rows = []
    for case in fixtures:
        order = list(ARMS)
        rng.shuffle(order)
        for arm in order:
            rows.append(dict(case=case['id'], family=case['family'], split=case['split'],
                             arm=arm, state='unavailable', reason=REASONS[arm],
                             provenance=None, success=None, usage=None))
    return rows

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args()
    for row in run(cases(), args.seed):
        print(json.dumps(row, ensure_ascii=False, allow_nan=False))

if __name__ == '__main__':
    main()
