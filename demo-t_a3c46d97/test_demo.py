import sys
import unittest
from demo import execute


def config():
    cmd = [sys.executable, '-c', 'import json,sys; json.load(sys.stdin); print(json.dumps({"answer":"ok","usage":{"input":3,"output":1},"provenance":"simulated"}))']
    return {'timeout_seconds': 5, 'routes': {'low': {'model':'local-test', 'effort':'none', 'command':cmd}}}


class IntegrationTests(unittest.TestCase):
    def test_conversation_freezes_route_and_exposes_receipts(self):
        seen = []
        case = {'id':'x','family':'conversation','split':'dev','prompts':['first','next'], 'expected':['ok','ok']}
        row = execute(case, 'configurable', config(), lambda p: seen.append(p) or 'low')
        self.assertEqual(seen, ['first'])
        self.assertEqual(row['evaluation'], 'pass')
        self.assertEqual([x['route'] for x in row['receipts']], ['low','low'])
        self.assertEqual(row['receipts'][0]['usage'], {'input':3,'output':1})
        self.assertIsNone(row['receipts'][0]['model_applied'])
        self.assertEqual(row['receipts'][0]['generation_provenance'], 'simulated')

    def test_blocked_families_and_missing_classifier(self):
        base = {'id':'x','family':'code','split':'dev','prompts':['x'],'expected':None}
        self.assertEqual(execute(base,'default',config(),lambda _: 'low')['state'], 'unavailable')
        base['family'] = 'simple'
        self.assertEqual(execute(base,'s1d1',config(),None)['state'], 'unavailable')

    def test_classifier_is_called_once_and_classification_visible(self):
        from demo import classifier_decider
        seen = []
        decide = classifier_decider(lambda p: seen.append(p) or {'complexity_score':0.7}, 0.5, 'low', 'high', provenance='simulated')
        c = config(); c['routes']['high'] = dict(c['routes']['low'])
        case = {'id':'x','family':'conversation','split':'dev','prompts':['first','next'],'expected':['ok','ok']}
        row = execute(case, 's1d1', c, decide)
        self.assertEqual(seen, ['first'])
        self.assertEqual(row['classification']['complexity_score'], 0.7)
        self.assertEqual(row['receipts'][1]['route'], 'high')
        self.assertEqual(row['decision_provenance'], 'simulated')

    def test_fingerprint_changes_with_unrecognized_weights(self):
        import tempfile
        from pathlib import Path
        from demo import fingerprint
        with tempfile.TemporaryDirectory() as tmp:
            model = Path(tmp) / 'model.onnx'
            model.write_bytes(b'unknown weights')
            a = fingerprint(tmp)
            model.write_bytes(b'other weights')
            self.assertNotEqual(a['model.onnx'], fingerprint(tmp)['model.onnx'])

    def test_unknown_classifier_provenance_and_policy_are_reproducible(self):
        from demo import classifier_decider
        identity = {'status': 'unknown', 'files_sha256': {'model.onnx': 'abc'}}
        c = config(); c['routes']['high'] = dict(c['routes']['low'])
        case = {'id':'x','family':'simple','split':'dev','prompts':['x'],'expected':['ok']}
        decide = classifier_decider(lambda p: {'complexity_score':0.7}, 0.5, 'low', 'high', identity)
        a = execute(case, 's1d1', c, decide)
        b = execute(case, 's1d1', c, decide)
        self.assertEqual(a['decision_provenance'], 'real-local-identity-unknown')
        self.assertEqual(a['classifier_identity'], identity)
        self.assertEqual(a['route_policy'], b['route_policy'])
        self.assertEqual(a['route_policy']['threshold'], 0.5)
        self.assertEqual(a['route_policy']['high']['model'], 'local-test')
        self.assertEqual(a['classifier_identity'], b['classifier_identity'])

    def test_error_without_fallback_and_fallback_receipt(self):
        case = {'id':'x','family':'simple','split':'dev','prompts':['x'],'expected':['ok']}
        def fail(_): raise RuntimeError('private')
        self.assertEqual(execute(case,'configurable',config(),fail)['state'],'error')
        c = config(); c['fallback'] = 'low'
        row = execute(case,'configurable',c,fail)
        self.assertEqual(row['receipts'][0]['fallback_reason'],'RuntimeError')
        self.assertNotIn('private',str(row))

if __name__ == '__main__': unittest.main()
