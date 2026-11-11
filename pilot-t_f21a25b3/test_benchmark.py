import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parent

class BenchmarkTest(unittest.TestCase):
    def test_independent_runs_and_failed_attempts(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            good = [sys.executable, '-c', 'import json,sys; json.load(sys.stdin); print(json.dumps(dict(answer="ok",usage={"input":10},rates={"input":2},decision_cost=0,retry_cost=0)))']
            bad = [sys.executable, '-c', 'raise RuntimeError("failed")']
            config = {'arms': {'default': good, 's1d1': good, 'configurable': bad}, 'repetitions': 2, 'timeout_seconds': 2, 'provenance': 'simulated', 'baseline_rates': {'input': 5}}
            cases = [{'case':'one', 'split':'dev', 'family':'simple', 'request': {'messages': [{'role':'user','content':'hello'}]}, 'expected':'ok'}]
            (d/'config.json').write_text(json.dumps(config)); (d/'cases.json').write_text(json.dumps(cases))
            p = subprocess.run([sys.executable, str(ROOT/'benchmark.py'), str(d/'config.json'), str(d/'cases.json'), str(d/'out.jsonl')], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            rows = [json.loads(x) for x in (d/'out.jsonl').read_text().splitlines()]
            self.assertEqual(len(rows), 6)
            self.assertEqual(sum(not r['success'] for r in rows), 2)
            self.assertTrue(all(r['usage'] is None for r in rows if r['arm'] == 'configurable'))
            p = subprocess.run([sys.executable, str(ROOT/'compare.py'), str(d/'out.jsonl')], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            results = {r['arm']:r for r in json.loads(p.stdout)}
            self.assertEqual(results['default']['usage']['input']['mean'], 10)
            self.assertAlmostEqual(results['default']['baseline_same_volume_estimate']['mean'], .00005)
            self.assertEqual(results['configurable']['unknown_usage_runs'], 2)
            self.assertIsNone(results['configurable']['equivalent_value'])
            again = subprocess.run([sys.executable, str(ROOT/'benchmark.py'), str(d/'config.json'), str(d/'cases.json'), str(d/'out.jsonl')], capture_output=True)
            self.assertNotEqual(again.returncode, 0)

if __name__ == '__main__': unittest.main()
