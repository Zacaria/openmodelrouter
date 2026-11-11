import unittest
import runner


class ComparatorTests(unittest.TestCase):
    def test_first_prompt_once_and_session_route_frozen(self):
        seen = []
        history = []
        def classify(prompt):
            seen.append(prompt)
            return {'complexity_score': 0.4, 'task': 'math', 'needs_tools_probability': 0.1, 'prompt_tokens': 4}
        def generate(prompt, prior, route):
            history.append((prompt, list(prior), route))
            return '4' if len(prior) == 0 else '11'
        case = {'id': 'T', 'family': 'conversation', 'split': 'dev', 'prompts': ['first', 'second'], 'expected': ['4', '11']}
        row = runner.execute(case, 's1d1', classify=classify, generate=generate)
        self.assertEqual(seen, ['first'])
        self.assertEqual(row['evaluation'], 'pass')
        self.assertEqual(history[1][1], [('first', '4')])
        self.assertEqual(history[0][2], history[1][2])
        self.assertEqual(row['provenance']['decision'], 'real-local')
        self.assertEqual(row['provenance']['generation'], 'simulated')

    def test_unavailable_baseline_no_substitution(self):
        case = {'id': 'S', 'family': 'simple', 'split': 'dev', 'prompts': ['x'], 'expected': ['x']}
        row = runner.execute(case, 's1d1')
        self.assertEqual(row['state'], 'unavailable')
        self.assertIsNone(row['evaluation'])
        self.assertIsNone(row['usage'])

    def test_unsupported_and_non_evaluated_not_success(self):
        for family, state in [('code', 'unavailable'), ('agents', 'unavailable'), ('diagnostic', 'executed')]:
            case = {'id': family, 'family': family, 'split': 'dev', 'prompts': ['x'], 'expected': None}
            row = runner.execute(case, 'default')
            self.assertEqual(row['state'], state)
            self.assertIsNone(row['evaluation'])

    def test_deterministic_order_and_configurable_decider(self):
        case = {'id': 'S', 'family': 'simple', 'split': 'dev', 'prompts': ['x'], 'expected': ['y']}
        seen = []
        def decide(prompt):
            seen.append(prompt)
            return runner.ROUTE
        rows = runner.run([case], seed=2, decide=decide)
        self.assertEqual([r['arm'] for r in rows], [r['arm'] for r in runner.run([case], seed=2)])
        self.assertEqual(seen, ['x'])
        self.assertEqual(runner.summarize(rows)[0]['planned'], 1)

    def test_failed_adapter_is_error_not_success(self):
        case = {'id': 'S', 'family': 'simple', 'split': 'dev', 'prompts': ['x'], 'expected': ['x']}
        def broken(*args):
            raise RuntimeError('sensitive exception')
        row = runner.execute(case, 'default', generate=broken)
        self.assertEqual(row['state'], 'error')
        self.assertIsNone(row['evaluation'])
        self.assertNotIn('sensitive', str(row))


if __name__ == '__main__':
    unittest.main()
