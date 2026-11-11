"""Offline synthetic native SSE regression."""
import http.client
import json
import unittest
from http.server import BaseHTTPRequestHandler
from unittest.mock import patch

import omr
from test_transport import serve


class HeaderlessNativeTests(unittest.TestCase):
    def test_non_native_missing_mime_rejected(self):
        class Backend(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(200); self.end_headers(); self.wfile.write(b'data: [DONE]\n\n')
        with serve(Backend) as upstream:
            cfg={'routes':{'a':{'url':f'http://127.0.0.1:{upstream}/v1','model':'actual','protocol':'chat'}},'default_route':'a'}
            with serve(omr.handler(cfg)) as gateway:
                c=http.client.HTTPConnection('127.0.0.1',gateway,timeout=3)
                c.request('POST','/v1/chat/completions',json.dumps({'model':'open-model-router','stream':True}),{'Content-Type':'application/json'})
                r=c.getresponse(); self.assertEqual(r.status,502); r.read(); c.close()

    def test_first_frame_is_delayed_until_complete(self):
        import select, threading
        partial=threading.Event(); release=threading.Event()
        created=b'data: {"type":"response.created","response":{"id":"r"}}\n\n'
        complete=b'data: {"type":"response.completed","response":{"id":"r","error":null}}\n\n'
        class Backend(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self):
                body=b'{"models":[{"slug":"actual","default_reasoning_level":"low","supported_reasoning_levels":[{"effort":"low"}]}]}'
                self.send_response(200); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length'])); self.send_response(200); self.end_headers()
                self.wfile.write(created[:-1]); self.wfile.flush(); partial.set(); release.wait(2)
                self.wfile.write(created[-1:]+complete); self.wfile.flush()
        cfg={'routes':{'a':{'url':'https://chatgpt.com/backend-api/codex','model':'actual','protocol':'responses'}},'default_route':'a','gateway_key_env':'TEST_GATEWAY_KEY'}
        h={'Content-Type':'application/json','X-OMR-Gateway-Key':'K'*32,'Authorization':'Bearer synthetic','chatgpt-account-id':'synthetic','session_id':'12345678-1234-4234-8234-123456789abc'}
        with serve(Backend) as upstream, patch.dict('os.environ',{'TEST_GATEWAY_KEY':'K'*32}):
            real=http.client.HTTPConnection
            with patch.object(omr.http.client,'HTTPSConnection',side_effect=lambda host,port,timeout:real('127.0.0.1',upstream,timeout=timeout)), serve(omr.handler(cfg)) as gateway:
                c=real('127.0.0.1',gateway,timeout=3); c.request('GET','/backend-api/codex/models',headers=h); r=c.getresponse(); r.read(); c.close()
                c=real('127.0.0.1',gateway,timeout=3); c.request('POST','/backend-api/codex/responses',json.dumps({'model':'open-model-router','stream':True}),h)
                try:
                    self.assertTrue(partial.wait(1)); self.assertFalse(select.select([c.sock],[],[],.15)[0])
                finally: release.set()
                r=c.getresponse(); self.assertEqual(r.status,200); self.assertIsNone(r.getheader('Content-Type')); self.assertEqual(r.read(),created+complete); c.close()

    def test_headerless_valid_stream(self):
        created = b'data: {"type":"response.created","response":{"id":"r"}}\n\n'
        completed = b'data: {"type":"response.completed","response":{"id":"r"}}\n\n'
        class Backend(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                body = b'{"models":[{"slug":"actual","default_reasoning_level":"low","supported_reasoning_levels":[{"effort":"low"}]}]}'
                self.send_response(200); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(200); self.send_header('Content-Length', str(len(created + completed))); self.end_headers(); self.wfile.write(created + completed)
        cfg = {'routes': {'a': {'url': 'https://chatgpt.com/backend-api/codex', 'model': 'actual', 'protocol': 'responses'}}, 'default_route': 'a', 'gateway_key_env': 'TEST_GATEWAY_KEY'}
        headers = {'Content-Type': 'application/json', 'X-OMR-Gateway-Key': 'K'*32, 'Authorization': 'Bearer synthetic', 'chatgpt-account-id': 'synthetic', 'session_id': '12345678-1234-4234-8234-123456789abc'}
        with serve(Backend) as upstream, patch.dict('os.environ', {'TEST_GATEWAY_KEY':'K'*32}):
            real = http.client.HTTPConnection
            with patch.object(omr.http.client, 'HTTPSConnection', side_effect=lambda host, port, timeout: real('127.0.0.1', upstream, timeout=timeout)), serve(omr.handler(cfg)) as gateway:
                c = real('127.0.0.1', gateway, timeout=3)
                c.request('GET', '/backend-api/codex/models', headers=headers); r = c.getresponse(); self.assertEqual(r.status, 200); r.read(); c.close()
                c = real('127.0.0.1', gateway, timeout=3)
                c.request('POST', '/backend-api/codex/responses', json.dumps({'model':'open-model-router','stream':True}), headers)
                r = c.getresponse(); self.assertEqual(r.status, 200); self.assertIsNone(r.getheader('Content-Type')); self.assertEqual(r.read(), created + completed); c.close()

    def test_bad_streams_and_mime(self):
        created = b'data: {"type":"response.created","response":{"id":"r"}}\n\n'
        complete = b'data: {"type":"response.completed","response":{"id":"r"}}\n\n'
        cases = [
            (None, b'data: {"type":"response.created","response":{}}\n\n', 502, False),
            (None, b'data: {"type":"response.created","response":{"id":"r","error":{"message":"secret"}}}\n\n', 502, False),
            (None, b'data: {"type":"response.created","response":{"id":"r","status":"failed"}}\n\n', 502, False),
            (None, b'<html>secret</html>\n' + created, 502, False),
            (None, b'{"secret":1}\n' + created, 502, False),
            (None, created[:-1] + b'unknown: secret\n\n', 502, False),
            (None, created + b'data: {"type":"response.completed","response":{"id":"r","error":{"message":"secret"}}}\n\n', 200, True),
            (None, created + b'data: {"type":"response.completed","response":{"id":"r","status":"incomplete"}}\n\n', 200, True),
            (None, created + b'unknown: secret\n' + complete, 200, True),
            (None, b'<html>bad</html>', 502, False),
            (None, b'{"type":"response.created"}', 502, False),
            (None, b'data: \xff\n\n', 502, False),
            (None, b'data: {bad}\n\n', 502, False),
            (None, b'data: {"type":"response.created","response":[]}\n\n', 502, False),
            ('', created + complete, 502, False),
            ('application/json', created + complete, 502, False),
            ('application/text/event-stream', created + complete, 502, False),
            (None, created + b'data: {"type":"response.unknown"}\n\n', 200, True),
            (None, created + b'data: [DONE]\n\n', 200, True),
            (None, created + b'data: {"type":"response.failed","error":"secret"}\n\n', 200, True),
            (None, created + complete + b'data: partial', 200, True),
            (None, created, 200, True),
        ]
        current = [None, b'']
        class Backend(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                body=b'{"models":[{"slug":"actual","default_reasoning_level":"low","supported_reasoning_levels":[{"effort":"low"}]}]}'
                self.send_response(200); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(200)
                if current[0] is not None: self.send_header('Content-Type',current[0])
                self.send_header('Content-Length',str(len(current[1]))); self.end_headers(); self.wfile.write(current[1])
        cfg={'routes':{'a':{'url':'https://chatgpt.com/backend-api/codex','model':'actual','protocol':'responses'}},'default_route':'a','gateway_key_env':'TEST_GATEWAY_KEY'}
        h={'Content-Type':'application/json','X-OMR-Gateway-Key':'K'*32,'Authorization':'Bearer synthetic','chatgpt-account-id':'synthetic','session_id':'12345678-1234-4234-8234-123456789abc'}
        with serve(Backend) as upstream, patch.dict('os.environ',{'TEST_GATEWAY_KEY':'K'*32}):
            real=http.client.HTTPConnection
            with patch.object(omr.http.client,'HTTPSConnection',side_effect=lambda host,port,timeout:real('127.0.0.1',upstream,timeout=timeout)), serve(omr.handler(cfg)) as gateway:
                c=real('127.0.0.1',gateway,timeout=3); c.request('GET','/backend-api/codex/models',headers=h); r=c.getresponse(); self.assertEqual(r.status,200); r.read(); c.close()
                for mime, body, status, late in cases:
                    with self.subTest(mime=mime, body=body):
                        current[:]=[mime,body]
                        c=real('127.0.0.1',gateway,timeout=3); c.request('POST','/backend-api/codex/responses',json.dumps({'model':'open-model-router','stream':True}),h)
                        r=c.getresponse(); self.assertEqual(r.status,status); result=r.read(); c.close()
                        if late: self.assertIn(b'event: error', result)
                        self.assertNotIn(b'secret',result)

    def test_item_boundary_rejections_on_route(self):
        # Separate defects: neither malformed item may reach the client.
        created = b'data: {"type":"response.created","response":{"id":"r"}}\n\n'
        complete = b'data: {"type":"response.completed","response":{"id":"r"}}\n\n'
        current = [b'']
        class Backend(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                body=b'{"models":[{"slug":"actual","default_reasoning_level":"low","supported_reasoning_levels":[{"effort":"low"}]}]}'
                self.send_response(200); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length'])); self.send_response(200); self.send_header('Content-Length',str(len(current[0]))); self.end_headers(); self.wfile.write(current[0])
        cfg={'routes':{'a':{'url':'https://chatgpt.com/backend-api/codex','model':'actual','protocol':'responses'}},'default_route':'a','gateway_key_env':'TEST_GATEWAY_KEY'}
        h={'Content-Type':'application/json','X-OMR-Gateway-Key':'K'*32,'Authorization':'Bearer synthetic','chatgpt-account-id':'synthetic','session_id':'12345678-1234-4234-8234-123456789abc'}
        base={'type':'function_call','name':'run','arguments':'{}','call_id':'c'}
        with serve(Backend) as upstream, patch.dict('os.environ',{'TEST_GATEWAY_KEY':'K'*32}):
            real=http.client.HTTPConnection
            with patch.object(omr.http.client,'HTTPSConnection',side_effect=lambda host,port,timeout:real('127.0.0.1',upstream,timeout=timeout)), serve(omr.handler(cfg)) as gateway:
                c=real('127.0.0.1',gateway,timeout=3); c.request('GET','/backend-api/codex/models',headers=h); r=c.getresponse(); r.read(); c.close()
                for defect in ({'namespace':42}, {'error':{'message':'SYNTHETIC_SECRET'}}):
                    with self.subTest(defect=defect):
                        item={'type':'response.output_item.done','item':{**base,**defect}}
                        frame=b'data: '+json.dumps(item).encode()+b'\n\n'
                        current[0]=created+frame+complete
                        c=real('127.0.0.1',gateway,timeout=3); c.request('POST','/backend-api/codex/responses',json.dumps({'model':'open-model-router','stream':True}),h)
                        r=c.getresponse(); self.assertEqual(r.status,200); result=r.read(); c.close()
                        self.assertIn(b'event: error',result); self.assertNotIn(frame,result); self.assertNotIn(b'SYNTHETIC_SECRET',result); self.assertNotIn(complete,result)

    def test_sdk_item_optional_fields(self):
        items=[{'type':'message','role':'assistant','content':[]}, {'type':'reasoning','summary':[]}, {'type':'function_call','name':'run','arguments':'{}','call_id':'c'}, {'type':'custom_tool_call','name':'run','input':'x','call_id':'c'}]
        invalid=[(i,'id',42) for i in range(4)]+[(i,'internal_chat_message_metadata_passthrough',42) for i in range(4)]+[(i,'internal_chat_message_metadata_passthrough',{'turn_id':42}) for i in range(4)]+[(i,'internal_chat_message_metadata_passthrough',{'create_time':True}) for i in range(4)]+[(i,'internal_chat_message_metadata_passthrough',{'content_item_kinds':[42]}) for i in range(4)]+[(0,'phase','invalid'),(0,'phase',42),(1,'encrypted_content',42),(2,'namespace',42),(2,'encrypted_function_args',[42]),(3,'namespace',42),(3,'status',42)]
        for index,key,value in invalid:
            event={'type':'response.output_item.done','item':{**items[index],key:value}}
            with self.subTest(event=event), self.assertRaises(ValueError): omr.validate_native_event(event,False,False)
        for item in items:
            item.update({'id':'i','error':None,'internal_chat_message_metadata_passthrough':{'turn_id':'t','create_time':1.5,'content_item_kinds':['text'],'extension':{'error':'ok'}},'extension':{'error':'ok'}})
            event={'type':'response.output_item.done','item':item}
            with self.subTest(event=event): self.assertEqual(omr.validate_native_event(event,False,False),event['type'])
        for item in ({**items[0],'phase':'final_answer'}, {**items[1],'encrypted_content':'cipher'}, {**items[2],'namespace':'ns','encrypted_function_args':['x'],'arguments':'{"error":"failed"}'}, {**items[3],'namespace':'ns','status':'completed','input':'error'}):
            event={'type':'response.output_item.done','item':item}
            with self.subTest(event=event): self.assertEqual(omr.validate_native_event(event,False,False),event['type'])

    def test_live_delivery_and_cancel(self):
        import select, threading
        sent=threading.Event(); closed=threading.Event()
        created=b'data: {"type":"response.created","response":{"id":"r"}}\n\n'
        class Backend(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self):
                body=b'{"models":[{"slug":"actual","default_reasoning_level":"low","supported_reasoning_levels":[{"effort":"low"}]}]}'
                self.send_response(200); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length'])); self.send_response(200); self.end_headers()
                self.wfile.write(created); self.wfile.flush(); sent.set()
                ready,_,_=select.select([self.connection],[],[],3)
                if ready and not self.connection.recv(1): closed.set()
        cfg={'routes':{'a':{'url':'https://chatgpt.com/backend-api/codex','model':'actual','protocol':'responses'}},'default_route':'a','gateway_key_env':'TEST_GATEWAY_KEY','timeout_seconds':5}
        h={'Content-Type':'application/json','X-OMR-Gateway-Key':'K'*32,'Authorization':'Bearer synthetic','chatgpt-account-id':'synthetic','session_id':'12345678-1234-4234-8234-123456789abc'}
        with serve(Backend) as upstream, patch.dict('os.environ',{'TEST_GATEWAY_KEY':'K'*32}):
            real=http.client.HTTPConnection
            with patch.object(omr.http.client,'HTTPSConnection',side_effect=lambda host,port,timeout:real('127.0.0.1',upstream,timeout=timeout)), serve(omr.handler(cfg)) as gateway:
                c=real('127.0.0.1',gateway,timeout=3); c.request('GET','/backend-api/codex/models',headers=h); r=c.getresponse(); r.read(); c.close()
                c=real('127.0.0.1',gateway,timeout=3); c.request('POST','/backend-api/codex/responses',json.dumps({'model':'open-model-router','stream':True}),h)
                r=c.getresponse(); self.assertEqual(r.status,200); self.assertEqual(r.read(len(created)),created); self.assertTrue(sent.wait(1.5)); r.close(); c.close(); self.assertTrue(closed.wait(1.5))

    def test_sdk_families_and_invalid_fields(self):
        valid = [
            {'type':'response.completed','response':{'id':'r','error':None,'status':'completed'}},
            {'type':'response.output_item.done','item':{'type':'function_call','name':'run','arguments':'{"error":"failed"}','call_id':'c'}},
            {'type':'response.output_item.added','item':{'type':'message','role':'assistant','content':[]}},
            {'type':'response.output_item.done','item':{'type':'message','role':'assistant','content':[{'type':'output_text','text':'hello'}]}},
            {'type':'response.output_item.done','item':{'type':'reasoning','summary':[{'type':'summary_text','text':'x'}]}},
            {'type':'response.output_item.done','item':{'type':'function_call','name':'run','arguments':'{}','call_id':'c'}},
            {'type':'response.output_item.done','item':{'type':'custom_tool_call','name':'run','input':'x','call_id':'c'}},
            {'type':'response.output_text.delta','delta':'hello','extension':{'x':1}},
            {'type':'response.reasoning_summary_text.delta','delta':'x','summary_index':0},
            {'type':'response.reasoning_text.delta','delta':'x','content_index':0},
            {'type':'response.function_call_arguments.delta','delta':'x'},
            {'type':'response.custom_tool_call_input.delta','delta':'x','item_id':'i'},
        ]
        for event in valid:
            with self.subTest(event=event): self.assertEqual(omr.validate_native_event(event,False,False),event['type'])
        invalid=[{'type':'response.created','response':[]}, {'type':'response.completed','response':{}}, {'type':'response.output_text.delta','delta':2}, {'type':'response.reasoning_summary_text.delta','delta':'x','summary_index':True}, {'type':'response.output_item.done','item':{'type':'message','role':'assistant','content':[{}]}}, {'type':'response.future.delta','delta':'x'}, {'type':'response.custom_tool_call_input.delta','delta':'x'}]
        for event in invalid:
            with self.subTest(event=event), self.assertRaises(ValueError): omr.validate_native_event(event,event['type']=='response.created',False)
