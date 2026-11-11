import unittest
from fixtures import cases
from evaluator import evaluate

class CasesTest(unittest.TestCase):
    def test_fixture_coverage_and_unique_ids(self):
        data = cases()
        self.assertEqual(len(data), 10)
        self.assertEqual(len({c['id'] for c in data}), 10)
        self.assertEqual({c['family'] for c in data}, {'simple', 'code', 'diagnostic', 'conversation', 'agents'})
        for family in {c['family'] for c in data}:
            self.assertEqual({c['split'] for c in data if c['family'] == family}, {'dev', 'validation'})

    def test_exact_answer_and_missing_second_turn(self):
        case = next(c for c in cases() if c['id'] == 'T-D1')
        self.assertEqual(evaluate(case, [' 4 ', '11']), 'pass')
        self.assertEqual(evaluate(case, ['4']), 'fail')

    def test_unsafe_and_human_oracles_are_not_executed(self):
        for case in cases():
            if case['family'] in ('code', 'diagnostic', 'agents'):
                self.assertEqual(evaluate(case, ['anything']), 'not_evaluated')

if __name__ == '__main__':
    unittest.main()
