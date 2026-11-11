import sys
import unittest

from loop import Session


def message(role, text):
    return {'role': role, 'content': text}


def config():
    generator = [sys.executable, '-c', 'import json,sys; r=json.load(sys.stdin); print(json.dumps({"answer":"ok","usage":{"input":3,"output":1},"provenance":"simulated"}))']
    return {'routes': {name: {'command': generator, 'model': name, 'effort': 'low'} for name in ('low', 'high')}, 'timeout_seconds': 5}


class LoopTests(unittest.TestCase):
    def test_route_fixed_on_first_user_and_usage_visible(self):
        seen = []
        session = Session(config(), lambda prompt: seen.append(prompt) or 'high')
        first = session.run({'messages': [message('user', 'first')]})
        second = session.run({'messages': [message('user', 'first'), message('assistant', 'ok'), message('user', 'second')]})
        self.assertEqual(seen, ['first'])
        self.assertEqual((first['route'], second['route'], second['model'], second['effort']), ('high', 'high', 'high', 'low'))
        self.assertEqual(second['result']['usage'], {'input': 3, 'output': 1})
        self.assertIsNone(second['effort_applied'])
        self.assertIsNone(second['model_applied'])

    def test_extra_fields_and_history_change_rejected_before_decision(self):
        seen = []
        session = Session(config(), lambda p: seen.append(p) or 'low')
        with self.assertRaises(ValueError):
            session.run({'messages': [message('user', 'first')], 'tools': ['shell']})
        self.assertEqual(seen, [])
        session.run({'messages': [message('user', 'first')]})
        with self.assertRaises(ValueError):
            session.run({'messages': [message('user', 'changed')]})
        self.assertEqual(seen, ['first'])

    def test_fallback_is_recorded_and_frozen(self):
        conf = config()
        conf['fallback'] = 'low'
        def fail(_):
            raise RuntimeError('secret')
        session = Session(conf, fail)
        first = session.run({'messages': [message('user', 'first')]})
        second = session.run({'messages': [message('user', 'first'), message('assistant', 'ok'), message('user', 'next')]})
        self.assertEqual((first['route'], second['route']), ('low', 'low'))
        self.assertEqual((first['fallback_reason'], second['fallback_reason']), ('RuntimeError', 'RuntimeError'))
        self.assertNotIn('secret', str(second))

    def test_decider_failure_without_fallback_stops(self):
        def fail(_):
            raise RuntimeError('no route')
        with self.assertRaises(RuntimeError):
            Session(config(), fail).run({'messages': [message('user', 'hello')]})

    def test_generator_failure_never_uses_fallback(self):
        conf = config()
        conf['fallback'] = 'low'
        conf['routes']['high']['command'] = [sys.executable, '-c', 'raise SystemExit(2)']
        with self.assertRaises(Exception):
            Session(conf, lambda _: 'high').run({'messages': [message('user', 'hello')]})

    def test_oversized_request_rejected(self):
        seen = []
        with self.assertRaises(ValueError):
            Session(config(), lambda p: seen.append(p) or 'low').run({'messages': [message('user', 'x' * 100001)]})
        self.assertEqual(seen, [])


if __name__ == '__main__':
    unittest.main()
