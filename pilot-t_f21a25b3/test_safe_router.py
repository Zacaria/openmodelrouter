import json
import sys
import unittest

import safe_router


class SafetyTests(unittest.TestCase):
    def test_authorized_messages_only_and_visible_model_effort(self):
        seen = []
        cmd = [sys.executable, '-c', 'import sys,json; r=json.load(sys.stdin); print(json.dumps({"answer":str(sorted(r)),"usage":{"input":2}}))']
        config = {'routes': {'low': {'command':cmd, 'model':'local-small', 'effort':'low'}}, 'timeout_seconds':3}
        request = {'messages':[{'role':'user','content':'hi'}]}
        result = safe_router.run(request, config, lambda prompt: seen.append(prompt) or 'low')
        self.assertEqual(seen, ['hi'])
        self.assertEqual(result['result']['answer'], "['messages']")
        self.assertEqual((result['model'],result['effort']), ('local-small','low'))

    def test_unknown_context_rejected_before_decider(self):
        seen = []
        with self.assertRaises(ValueError):
            safe_router.run({'messages':[{'role':'user','content':'hi'}], 'tools':['shell']}, {}, lambda p: seen.append(p))
        self.assertEqual(seen, [])

    def test_configured_fallback_records_failure(self):
        cmd = [sys.executable, '-c', 'import json; print(json.dumps({"answer":"ok","usage":{}}))']
        config = {'routes': {'low': {'command':cmd,'model':'local','effort':'low'}}, 'timeout_seconds':3,'fallback':'low'}
        def fail(_): raise RuntimeError('private input')
        output = safe_router.run({'messages':[{'role':'user','content':'hi'}]}, config, fail)
        self.assertEqual(output['fallback_reason'], 'RuntimeError')
        self.assertEqual(output['route'], 'low')
        self.assertNotIn('private input', json.dumps(output))

    def test_no_fallback_when_not_authorized(self):
        def fail(_): raise RuntimeError('fail')
        config = {'routes': {'low': {'command':['unused'],'model':'local','effort':'low'}}, 'timeout_seconds':3}
        with self.assertRaises(RuntimeError):
            safe_router.run({'messages':[{'role':'user','content':'hi'}]}, config, fail)

if __name__ == '__main__': unittest.main()
