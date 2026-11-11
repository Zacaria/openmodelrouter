import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name('compare.py')

def run(rows):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / 'results.jsonl'
        p.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        return subprocess.run([sys.executable, str(SCRIPT), str(p)], capture_output=True, text=True)

def row(success=True, elapsed=100):
    return dict(case='simple-1', split='dev', family='simple', arm='default', success=success, elapsed_ms=elapsed, usage={'input': 1000, 'output': 200}, rates={'input': 2, 'output': 10}, decision_cost=0.01, retry_cost=0.02)

class CompareTest(unittest.TestCase):
    def test_aggregates_failures_and_value(self):
        p = run([row(), row(False, 300)])
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout)[0]
        self.assertEqual(result['runs'], 2)
        self.assertEqual(result['failures'], 1)
        self.assertEqual(result['elapsed_ms']['mean'], 200)
        self.assertEqual(result['elapsed_ms']['stdev_population'], 100)
        self.assertAlmostEqual(result['equivalent_value']['mean'], 0.034)

    def test_rejects_missing_tariff_and_nan(self):
        bad = row(); bad['rates'] = {}
        self.assertNotEqual(run([bad]).returncode, 0)
        bad = row(); bad['elapsed_ms'] = float('nan')
        self.assertNotEqual(run([bad]).returncode, 0)

    def test_keeps_dev_and_validation_separate(self):
        a = row(); b = row(); b['split'] = 'validation'
        p = run([a, b])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(len(json.loads(p.stdout)), 2)

if __name__ == '__main__': unittest.main()
