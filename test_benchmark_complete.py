import json
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
import benchmark_runner as b

class CompleteTest(unittest.TestCase):
    def test_behavioral_code_oracle(self):
        c = next(c for c in b.cases() if c['family'] == 'code')
        equivalent = '```python\ndef transform(x):\n    return 1 + x + x\n```'
        results = []
        self.assertTrue(b.evaluate(c, [equivalent], [], results))
        self.assertEqual([r['x'] for r in results], [-3, 0, 1, 9])
        self.assertTrue(all(r['pass'] for r in results))
        results = []
        self.assertFalse(b.evaluate(c, ['def transform(x):\n return x'], [], results))
        self.assertEqual(len(results), 4)
        for source in ('def transform(x):\n return transform(x)', 'def transform(x):\n return x**2', 'def transform(x):\n return x.real', 'def transform(x):\n return ' + 'x+' * 33 + '1'):
            self.assertFalse(b.evaluate(c, [source], []))

    def test_frozen_matrix_and_static_code(self):
        cases = b.cases()
        self.assertEqual(len(cases), 100)
        for split in ('dev', 'validation'):
            for family in ('simple', 'code', 'diagnostic', 'conversation', 'agents'):
                self.assertEqual(sum(c['split'] == split and c['family'] == family for c in cases), 10)
        c = next(c for c in cases if c['family'] == 'code')
        self.assertTrue(b.evaluate(c, [c['reference']], []))
        self.assertFalse(b.evaluate(c, ['import os\n' + c['reference']], []))

    def test_code_receipt_records_executed_tests(self):
        from unittest.mock import patch
        c = next(c for c in b.cases() if c['family'] == 'code')
        class Response:
            headers = {}
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, *args):
                return json.dumps({'choices':[{'message':{'content':'def transform(x):\n return x + x + 1'}}]}).encode()
        with patch('urllib.request.build_opener') as opener:
            opener.return_value.open.return_value = Response()
            row = b.execute(c, 'default', 'http://localhost:1', 1)
        self.assertEqual(row['evaluation'], 'pass')
        self.assertEqual([r['x'] for r in row['code_test_results']], [-3, 0, 1, 9])

    def test_diagnostic_requires_evidence_and_ambiguous_first_turn(self):
        c = next(c for c in b.cases() if c['family'] == 'diagnostic')
        answers = c['expected']
        self.assertFalse(b.evaluate(c, answers, []))
        events = [{'name':'lookup', 'key':c['fixture_key'], 'turn':1}]
        self.assertTrue(b.evaluate(c, answers, events))
        self.assertFalse(b.evaluate(c, [answers[1], answers[1]], events))
        self.assertFalse(b.evaluate(c, answers, [{'name':'lookup', 'key':c['fixture_key'], 'turn':0}]))

    def test_child_really_calls_gateway_in_distinct_session(self):
        case = next(c for c in b.cases() if c['family'] == 'agents')
        class Handler(BaseHTTPRequestHandler):
            seen = []
            def log_message(self, *args): pass
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                session = self.headers['X-OMR-Session']; self.seen.append((session, payload))
                if len(self.seen) == 1:
                    msg = {'role':'assistant','content':None,'tool_calls':[{'id':'1','type':'function','function':{'name':'delegate','arguments':json.dumps({'task':case['child_task']})}}]}
                elif len(self.seen) == 2:
                    msg = {'role':'assistant','content':case['child_answer']}
                else:
                    msg = {'role':'assistant','content':case['expected'][0]}
                body = json.dumps({'model':'observed','choices':[{'message':msg}], 'usage':{'prompt_tokens':4,'completion_tokens':2,'prompt_tokens_details':{'cached_tokens':1},'completion_tokens_details':{'reasoning_tokens':1}}}).encode()
                self.send_response(200); self.send_header('X-OMR-Route','r'); self.send_header('X-OMR-Effort','low'); self.send_header('X-OMR-Decision-Ms','2.5'); self.end_headers(); self.wfile.write(body)
        server = HTTPServer(('127.0.0.1', 0), Handler); thread = Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            row = b.execute(case, 'default', f'http://127.0.0.1:{server.server_port}', 2)
            self.assertEqual(row['evaluation'], 'pass')
            self.assertEqual(row['calls'], 3)
            self.assertNotEqual(Handler.seen[0][0], Handler.seen[1][0])
            self.assertEqual(row['usage']['cache_read'], 3)
            self.assertEqual(row['decision_ms'], 7.5)
        finally:
            server.shutdown(); server.server_close(); thread.join()

if __name__ == '__main__': unittest.main()
