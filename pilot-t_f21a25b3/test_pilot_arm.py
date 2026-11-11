import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parent

class PilotArmTest(unittest.TestCase):
    def test_configurable_classifies_first_user_message_and_returns_generator_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            config = {
                'threshold': 0.5, 'timeout_seconds': 5,
                'decision_command': [sys.executable, '-c', 'import json,sys; x=json.load(sys.stdin); print(json.dumps({"route":"high" if x == {"prompt":"first"} else "low"}))'],
                'routes': {route: [sys.executable, '-c', 'import json,sys; json.load(sys.stdin); print(json.dumps({"answer":"'+route+'","usage":{"input":1},"rates":{"input":0},"decision_cost":0,"retry_cost":0}))'] for route in ('low', 'high')},
            }
            path = Path(directory) / 'config.json'
            path.write_text(json.dumps(config))
            request = {'messages': [{'role':'user','content':'first'}, {'role':'user','content':'second'}]}
            result = subprocess.run([sys.executable, str(ROOT/'pilot_arm.py'), 'configurable', str(path)], input=json.dumps(request), text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['answer'], 'high')

if __name__ == '__main__': unittest.main()
