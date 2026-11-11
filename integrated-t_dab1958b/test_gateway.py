import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import HTTPServer
import gateway


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.seen = []
        def route(messages):
            self.seen.append(messages)
            return {'route':'local','model':'tiny','effort':'low', 'fallback_reason':None,
                    'elapsed_ms':1, 'result':{'answer':'yes','usage':{'input':3,'output':1},'provenance':'simulated'}}
        self.server = HTTPServer(('127.0.0.1',0), gateway.handler(route))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = 'http://127.0.0.1:%s/v1/chat/completions' % self.server.server_port

    def tearDown(self):
        self.server.shutdown(); self.thread.join(); self.server.server_close()

    def request(self, **kwargs):
        data = {'model':'local-router','messages':[{'role':'user','content':'hi'}], **kwargs}
        req = urllib.request.Request(self.url, data=json.dumps(data).encode(), headers={'Content-Type':'application/json'})
        return urllib.request.urlopen(req)

    def test_complete_and_usage(self):
        with self.request() as r:
            out=json.load(r)
        self.assertEqual(out['choices'][0]['message']['content'], 'yes')
        self.assertEqual(out['usage']['prompt_tokens'], 3)
        self.assertEqual(self.seen[0][0]['content'], 'hi')

    def test_stream_ends_with_done(self):
        with self.request(stream=True, stream_options={'include_usage':True}) as r:
            data=r.read().decode()
        self.assertIn('"content": "yes"', data)
        self.assertIn('"prompt_tokens": 3', data)
        self.assertTrue(data.endswith('data: [DONE]\n\n'))

    def test_tools_and_unknown_fields_are_rejected_before_routing(self):
        for kw in ({'tools':[]}, {'secret':'x'}, {'model':'other'}):
            with self.assertRaises(urllib.error.HTTPError) as err: self.request(**kw)
            self.assertEqual(err.exception.code, 400)
        self.assertEqual(self.seen, [])

    def test_omp_text_blocks_and_store_false(self):
        blocks = [{'type':'text','text':'one'}, {'type':'text','text':'two'}]
        with self.request(messages=[{'role':'user','content':blocks}], store=False, max_completion_tokens=8) as r:
            self.assertEqual(r.status, 200)
        self.assertEqual(self.seen[0][0]['content'], 'one\ntwo')
        with self.assertRaises(urllib.error.HTTPError): self.request(store=True)
        with self.assertRaises(urllib.error.HTTPError): self.request(messages=[{'role':'user','content':[{'type':'image','url':'secret'}]}])

    def test_no_content_in_logs(self):
        self.assertNotIn('hi', json.dumps(gateway.receipt({'route':'x','result':{'answer':'hi','usage':{}}})))

if __name__ == '__main__': unittest.main()
