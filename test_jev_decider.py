import copy
import io
import json
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

import jev_decider as j


def response():
    return {'model': j.MODEL, 'answers': {'route': {'type': 'choice', 'choice': 'direct', 'confidence': 0.8, 'probabilities': {'direct': 0.8, 'reasoning': 0.2}}}, 'usage': {'input_tokens': 3, 'output_tokens': 2}}


class DecisionTests(unittest.TestCase):
    def decide(self, result, payload=None):
        return j.decide(payload or {'prompt': 'hello'}, 'a', 'b', j.MODEL, 'test-key', lambda body, key: result)

    def test_valid_decision_and_request(self):
        def transport(body, key):
            self.assertEqual(body['state'], {'prompt': 'hello'})
            self.assertEqual(key, 'test-key')
            return response()
        result = j.decide({'prompt': 'hello'}, 'a', 'b', j.MODEL, 'test-key', transport)
        self.assertEqual(result['route'], 'a')
        self.assertEqual(result['usage']['input_tokens'], 3)
        self.assertGreaterEqual(result['elapsed_ms'], 0)
        r = response()
        r['answers']['route'].update(choice='reasoning', probabilities={'direct': 0.2, 'reasoning': 0.8})
        self.assertEqual(self.decide(r)['route'], 'b')

    def test_invalid_provider_answers_fail_closed(self):
        cases = []
        for field, value in [('choice', 'other'), ('choice', 'reasoning'), ('confidence', float('nan')), ('confidence', True), ('probabilities', {'direct': 1}), ('probabilities', {'direct': 2, 'reasoning': -1}), ('probabilities', {'direct': 0.2, 'reasoning': 0.2}), ('type', 'noul')]:
            r = response(); r['answers']['route'][field] = value; cases.append(r)
        for field, value in [('model', 'other'), ('usage', {'input_tokens': True, 'output_tokens': 1}), ('answers', None)]:
            r = response(); r[field] = value; cases.append(r)
        for r in cases:
            with self.subTest(r=r), self.assertRaises(ValueError):
                self.decide(r)

    def test_invalid_inputs_never_call_transport(self):
        for payload in ({}, {'prompt': ''}, {'prompt': 1}, {'prompt': 'x', 'extra': 1}, {'prompt': 'x' * (j.MAX_INPUT + 1)}):
            with self.subTest(payload=str(payload)[:40]), self.assertRaises(ValueError):
                j.decide(payload, 'a', 'b', j.MODEL, 'key', lambda *a: self.fail('transport called'))
        for a, b, model, key in [('a', 'a', j.MODEL, 'key'), ('a', 'b', 'other', 'key'), ('a', 'b', j.MODEL, '')]:
            with self.assertRaises(ValueError):
                j.decide({'prompt': 'x'}, a, b, model, key, lambda *a: self.fail('transport called'))

    def test_http_single_request_redirect_and_size(self):
        class FakeResponse:
            status = 200
            def __init__(self, raw): self.raw = raw
            def read(self, n): return self.raw[:n]
        class FakeConnection:
            def __init__(self, host, timeout):
                self.host, self.timeout = host, timeout
                self.calls = []
            def request(self, *args): self.calls.append(args)
            def getresponse(self): return self.response
            def close(self): pass
        conn = FakeConnection('api.typesafe.ai', j.TIMEOUT)
        conn.response = FakeResponse(json.dumps(response()).encode())
        with patch.object(j.http.client, 'HTTPSConnection', return_value=conn) as factory:
            self.assertEqual(j.request({'x': 1}, 'test-key'), response())
            factory.assert_called_once_with('api.typesafe.ai', timeout=j.TIMEOUT)
            self.assertEqual(len(conn.calls), 1)
            self.assertEqual(conn.calls[0][:2], ('POST', '/v1/systemone'))
            conn.response.status = 302
            with self.assertRaises(ValueError): j.request({}, 'test-key')
            conn.response.status = 200
            conn.response.raw = b'x' * (j.MAX_OUTPUT + 1)
            with self.assertRaises(ValueError): j.request({}, 'test-key')
            self.assertEqual(len(conn.calls), 3)

    def test_cli_requires_consent_and_secret_without_output(self):
        env = dict(os.environ, TYPESAFE_API_KEY='')
        for args in ([], ['--public-prompts']):
            p = subprocess.run([sys.executable, '-B', 'jev_decider.py', '--direct-route', 'a', '--reasoning-route', 'b', *args], input=b'{"prompt":"x"}', capture_output=True, env=env, timeout=5)
            self.assertNotEqual(p.returncode, 0)
            self.assertEqual(p.stdout, b'')

    def test_cli_success_through_injected_transport(self):
        argv = ['jev_decider.py', '--direct-route', 'a', '--reasoning-route', 'b', '--public-prompts']
        stdin = io.TextIOWrapper(io.BytesIO(b'{"prompt":"hello"}'))
        output = io.StringIO()
        # Inject at decide's transport default without touching the network.
        original = j.decide
        with patch.object(sys, 'argv', argv), patch.object(sys, 'stdin', stdin), patch.object(sys, 'stdout', output), patch.dict(os.environ, {'TYPESAFE_API_KEY': 'test-key'}), patch.object(j, 'decide', side_effect=lambda *a: original(*a, transport=lambda body, key: response())):
            self.assertEqual(j.main(), 0)
        self.assertEqual(json.loads(output.getvalue())['route'], 'a')


if __name__ == '__main__':
    unittest.main()
