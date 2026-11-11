import json
import threading
import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from http.server import BaseHTTPRequestHandler, HTTPServer
import benchmark_runner as b

class Handler(BaseHTTPRequestHandler):
    seen = []
    def log_message(self, *args): pass
    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.seen.append((self.path, self.headers.get('X-OMR-Session'), payload))
        msg = {'role': 'assistant', 'content': '102'}
        data = json.dumps({'model': 'observed-model', 'choices': [{'message': msg}], 'usage': {'prompt_tokens': 3, 'completion_tokens': 2}}).encode()
        self.send_response(200); self.end_headers(); self.wfile.write(data)

class PilotTest(unittest.TestCase):
    def test_bounded_plan_persists_before_calls_and_errors(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            output = str(Path(directory) / 'run.jsonl')
            args = SimpleNamespace(authorized=True, repetitions=2, timeout=1, cases_per_family=1, split='dev', seed=0, output=output, default='http://localhost:1', s1d1='http://localhost:2', configurable='http://localhost:3')
            def fake(case, arm, url, timeout):
                plan = json.loads(Path(output + '.plan.json').read_text())
                self.assertEqual(plan['planned_total'], 30)
                return {'state':'error', 'evaluation':None}
            with patch.object(b, 'execute', side_effect=fake): b.run(args)
            plan = json.loads(Path(output + '.plan.json').read_text())
            rows = [json.loads(line) for line in Path(output).read_text().splitlines()]
            self.assertEqual(len(rows), 30)
            self.assertEqual([r['global_order'] for r in rows], list(range(30)))
            self.assertTrue(all(r['fixture_sha256'] == plan['fixture_sha256'] and r['planned_total'] == 30 for r in rows))
            self.assertEqual(len({r['case'] for r in plan['runs']}), 5)
            self.assertTrue(all(r['state'] == 'error' for r in rows))
            for invalid in (0, 11):
                args.cases_per_family = invalid
                with self.assertRaises(ValueError): b.run(args)

    def test_http_session_exact_and_redaction(self):
        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            case = {'id':'S-D1', 'family':'simple', 'split':'dev', 'prompts':['secret prompt'], 'expected':['102']}
            row = b.execute(case, 'default', f'http://127.0.0.1:{server.server_port}', 2)
            self.assertEqual(row['evaluation'], 'pass')
            self.assertEqual(Handler.seen[-1][0], '/v1/chat/completions')
            self.assertEqual(Handler.seen[-1][1], row['session'])
            self.assertNotIn('secret prompt', json.dumps(row))
            self.assertEqual(row['usage']['input'], 3)
            self.assertIsNone(row['usage']['decision'])
        finally: server.shutdown(); server.server_close(); thread.join()

    def test_failure_and_unknown_not_success(self):
        case = {'id':'x', 'family':'code', 'split':'dev', 'prompts':['x'], 'expected':None}
        row = b.execute(case, 'default', 'http://127.0.0.1:1', 0.1)
        self.assertNotEqual(row['evaluation'], 'pass')
        self.assertEqual(row['state'], 'error')
        self.assertIsNone(row['usage']['input'])
        self.assertEqual(b.tool_result('lookup', '{"key":"alpha"}'), '7')
        with self.assertRaises(ValueError): b.tool_result('lookup', '{"key":"secret"}')

    def test_tool_round_trip_and_report_are_simulated(self):
        class ToolHandler(BaseHTTPRequestHandler):
            seen = []
            def log_message(self, *args): pass
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                self.seen.append(payload)
                if len(self.seen) == 1:
                    message = {'role':'assistant', 'content':None, 'tool_calls':[{'id':'call1', 'type':'function', 'function':{'name':'lookup', 'arguments':'{"key":"alpha"}'}}]}
                else:
                    message = {'role':'assistant', 'content':'7'}
                data = json.dumps({'choices':[{'message':message}], 'usage':{'prompt_tokens':2,'completion_tokens':1}}).encode()
                self.send_response(200); self.end_headers(); self.wfile.write(data)
        server = HTTPServer(('127.0.0.1', 0), ToolHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            row = b.execute({'id':'x','family':'simple','split':'dev','prompts':['x'],'expected':['7']}, 'default', f'http://127.0.0.1:{server.server_port}', 2)
            self.assertEqual(row['evaluation'], 'pass')
            self.assertEqual(ToolHandler.seen[-1]['messages'][-1], {'role':'tool','tool_call_id':'call1','content':'7'})
            self.assertEqual(row['usage']['input'], 4)
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory); (root/'in.jsonl').write_text(json.dumps(row)+'\n')
                b.report(SimpleNamespace(input=str(root/'in.jsonl'), output=str(root/'report.md'), svg=str(root/'chart.svg')))
                self.assertIn('inconnus', (root/'report.md').read_text())
                self.assertIn('<svg', (root/'chart.svg').read_text())
        finally: server.shutdown(); server.server_close(); thread.join()

if __name__ == '__main__': unittest.main()
