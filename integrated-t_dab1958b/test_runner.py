import unittest
from fixtures import cases
from runner import run

class RunnerTest(unittest.TestCase):
    def test_seed_and_absent_arms(self):
        a = run(cases(), seed=12)
        b = run(cases(), seed=12)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 30)
        for row in a:
            self.assertEqual(row['state'], 'unavailable')
            self.assertIsNone(row['success'])
            self.assertIsNone(row['usage'])
        self.assertEqual({r['arm'] for r in a}, {'default', 's1d1', 'configurable'})

if __name__ == '__main__':
    unittest.main()
