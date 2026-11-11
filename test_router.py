import json
import sys
import unittest
from router import run

class RouterTest(unittest.TestCase):
    def test_executes_selected_route_and_uses_first_user_message(self):
        seen = []
        def classify(text):
            seen.append(text)
            return {"complexity_score": 0.8}
        cmd = [sys.executable, '-c', 'import json,sys; r=json.load(sys.stdin); print(json.dumps({"answer":r["messages"][-1]["content"],"usage":{"input":3}}))']
        request = {"messages":[{"role":"user","content":"first"},{"role":"user","content":"later"}]}
        output = run(request, {"routes":{"high":cmd,"low":cmd},"threshold":0.5,"timeout_seconds":3}, classify)
        self.assertEqual(seen, ["first"])
        self.assertEqual(output['route'], 'high')
        self.assertEqual(output['result']['answer'], 'later')
        self.assertEqual(output['result']['usage'], {'input':3})

    def test_invalid_score_never_executes_route(self):
        from unittest.mock import patch
        request = {'messages': [{'role':'user', 'content':'hello'}]}
        config = {'routes': {'high':['unused'], 'low':['unused']}, 'threshold':0.5, 'timeout_seconds':3}
        with patch('router.subprocess.run') as launch:
            with self.assertRaisesRegex(ValueError, 'invalid score'):
                run(request, config, lambda _: {'complexity_score': float('nan')})
            launch.assert_not_called()

    def test_child_failure_is_not_retried(self):
        request = {'messages':[{'role':'user','content':'hello'}]}
        cmd = [sys.executable, '-c', 'import sys; sys.exit(7)']
        config = {'routes':{'high':cmd,'low':cmd},'threshold':0.5,'timeout_seconds':3}
        import subprocess
        with self.assertRaises(subprocess.CalledProcessError) as err:
            run(request, config, lambda _: {'complexity_score':0.2})
        self.assertEqual(err.exception.returncode, 7)

    def test_child_does_not_inherit_secret_environment(self):
        import os
        from unittest.mock import patch
        cmd = [sys.executable, '-c', 'import json,os; print(json.dumps({"answer":os.getenv("ROUTER_TEST_SECRET", "absent"),"usage":{}}))']
        config = {'routes': {'low': cmd, 'high': cmd}, 'threshold': .5, 'timeout_seconds': 3}
        with patch.dict(os.environ, {'ROUTER_TEST_SECRET': 'private'}):
            out = run({'messages':[{'role':'user','content':'hello'}]}, config, lambda _: {'complexity_score': .1})
        self.assertEqual(out['result']['answer'], 'absent')

    def test_configurable_decider_receives_only_first_prompt(self):
        from router import command_decider
        cmd = [sys.executable, '-c', 'import json,sys; r=json.load(sys.stdin); print(json.dumps({"route":"high" if r == {"prompt":"first"} else "low"}))']
        decision = command_decider(cmd, 3)('first')
        self.assertEqual(decision['route'], 'high')

    def test_configurable_cli_routes_end_to_end(self):
        import subprocess, tempfile
        from pathlib import Path
        decide = [sys.executable, '-c', 'import json,sys; json.load(sys.stdin); print(json.dumps({"route":"high"}))']
        answer = [sys.executable, '-c', 'import json,sys; json.load(sys.stdin); print(json.dumps({"answer":"ok","usage":{"input":1}}))']
        config = {'decision_command': decide, 'routes': {'high':answer,'low':answer}, 'threshold':.5, 'timeout_seconds':3}
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'config.json'
            path.write_text(json.dumps(config))
            p = subprocess.run([sys.executable, 'router.py', '--config', str(path)], input=json.dumps({'messages':[{'role':'user','content':'first'}]}), text=True, capture_output=True, check=True)
        result = json.loads(p.stdout)
        self.assertEqual((result['route'], result['result']['answer']), ('high', 'ok'))

if __name__ == '__main__': unittest.main()
