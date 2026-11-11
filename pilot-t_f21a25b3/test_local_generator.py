import json
import os
import subprocess
import unittest
from pathlib import Path

class LocalGenerationTest(unittest.TestCase):
    def test_offline_cpu_generation_returns_observed_usage(self):
        python = os.environ.get('OMR_GENERATOR_PYTHON')
        weights = os.environ.get('OMR_GENERATOR_WEIGHTS')
        if not python or not weights:
            self.skipTest('set OMR_GENERATOR_PYTHON and OMR_GENERATOR_WEIGHTS for real local inference')
        script = Path(__file__).with_name('local_generator.py')
        result = subprocess.run([python, str(script), weights], input=json.dumps({'messages':[{'role':'user','content':'The capital of France is'}]}), text=True, capture_output=True, env={}, timeout=60, check=True)
        data = json.loads(result.stdout)
        self.assertTrue(data['answer'])
        self.assertGreater(data['usage']['input'], 0)
        self.assertGreater(data['usage']['output'], 0)
        self.assertEqual(data['provenance'], 'real-local')

if __name__ == '__main__': unittest.main()
