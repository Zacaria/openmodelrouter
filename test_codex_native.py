"""Offline regression: the native route must not bypass its local key."""
import http.client
import unittest
from unittest.mock import patch

import omr
from test_transport import serve


class CodexNativeTests(unittest.TestCase):
    def test_models_missing_local_key_is_rejected_by_route(self):
        config = {'routes': {'local': {'url': 'https://chatgpt.com/backend-api/codex',
                                      'model': 'example', 'protocol': 'responses'}},
                  'default_route': 'local', 'gateway_key_env': 'OMR_CODEX_GATEWAY_KEY'}
        with patch.dict('os.environ', {'OMR_CODEX_GATEWAY_KEY': 's' * 32}):
            with serve(omr.handler(config)) as port:
                client = http.client.HTTPConnection('127.0.0.1', port, timeout=2)
                try:
                    client.request('GET', '/backend-api/codex/models?client_version=0.162.1')
                    response = client.getresponse()
                    self.assertEqual(response.status, 401)
                    response.read()
                finally:
                    client.close()

class OfflineNativeTests(unittest.TestCase):
    def test_end_to_end_and_boundaries(self):
        import json, tempfile
        from pathlib import Path
        from http.server import BaseHTTPRequestHandler
        seen = []
        model = {'slug':'actual','display_name':'real metadata','default_reasoning_level':'low', 'supported_reasoning_levels':[{'effort':'low','description':'genuine'},{'effort':'high','description':'deep'}]}
        class Backend(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def respond(self, status, body):
                self.send_response(status); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
            def do_GET(self):
                seen.append((self.command,self.path,dict(self.headers),None))
                self.respond(200,json.dumps({'models':[model]}).encode())
            def do_POST(self):
                data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                seen.append((self.command,self.path,dict(self.headers),data))
                if data.get('stream'):
                    body=b'data: {\"type\":\"response.completed\",\"response\":{\"model\":\"actual\"}}\n\n'
                    self.send_response(200); self.send_header('Content-Type','text/event-stream'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
                else: self.respond(200,json.dumps({'model':'actual'}).encode())
        key = 'K'*32
        config = {'routes': {'a': {'url':'https://chatgpt.com/backend-api/codex','model':'actual','protocol':'responses','effort':'high'}}, 'default_route':'a', 'gateway_key_env':'TEST_GATEWAY_KEY'}
        with tempfile.TemporaryDirectory() as directory, serve(Backend) as upstream, patch.dict('os.environ', {'TEST_GATEWAY_KEY':key}):
            config['receipts'] = str(Path(directory,'receipts'))
            real = http.client.HTTPConnection
            def transport(host, port, timeout):
                self.assertEqual((host,port),('chatgpt.com',443))
                return real('127.0.0.1',upstream,timeout=timeout)
            with patch.object(omr.http.client,'HTTPSConnection',side_effect=transport), serve(omr.handler(config)) as gateway:
                def request(method,path,headers,body=None):
                    c = real('127.0.0.1',gateway,timeout=3)
                    c.request(method,path,body,headers); r=c.getresponse(); result=(r.status,r.read()); c.close(); return result
                auth = {'X-OMR-Gateway-Key':key,'Authorization':'Bearer fake-token','chatgpt-account-id':'acct-one', 'originator':'test-client','X-OpenAI-Fedramp':'true','Cookie':'secret-cookie','Connection':'x-blocked', 'x-blocked':'bad'}
                payload = json.dumps({'model':'open-model-router','input':'PRIVATE-PROMPT','reasoning':{'effort':'high'}})
                postheaders = {**auth,'Content-Type':'application/json','session_id':'12345678-1234-4234-8234-123456789abc'}
                self.assertEqual(request('POST','/backend-api/codex/responses',postheaders,payload)[0],400)
                self.assertEqual(request('GET','/backend-api/codex/models',{})[0],401)
                status, body = request('GET','/backend-api/codex/models?client_version=0.162.1',auth)
                self.assertEqual(status,200)
                alias = json.loads(body)['models'][-1]
                self.assertEqual(alias,{**model,'slug':'open-model-router'})
                self.assertEqual(request('POST','/backend-api/codex/responses',postheaders,payload)[0],200)
                stream = json.dumps({'model':'open-model-router','input':'PRIVATE-PROMPT','stream':True})
                status, event = request('POST','/backend-api/codex/responses',postheaders,stream)
                self.assertEqual(status,200); self.assertIn(b'response.completed',event)
                other = {**postheaders,'chatgpt-account-id':'acct-two'}
                self.assertEqual(request('POST','/backend-api/codex/responses',other,payload)[0],400)
                config['routes']['a']['effort'] = None
                bad = json.dumps({'model':'open-model-router','input':'PRIVATE-PROMPT','reasoning':{'effort':'max'}})
                self.assertEqual(request('POST','/backend-api/codex/responses',postheaders,bad)[0],400)
                self.assertEqual(len(seen),3)
                for _,_,headers,_ in seen:
                    lowered = {k.lower():v for k,v in headers.items()}
                    for name in ('cookie','x-omr-gateway-key','x-blocked'): self.assertNotIn(name,lowered)
                    self.assertEqual(lowered['originator'],'test-client')
                self.assertEqual(seen[1][1],'/backend-api/codex/responses')
                self.assertEqual(seen[1][3]['model'],'actual')
                self.assertEqual(seen[1][2].get('Accept'),'application/json')
                self.assertEqual(seen[2][2].get('Accept'),'text/event-stream')
            text = Path(directory,'receipts').read_text()
            for secret in (key,'fake-token','acct-one','PRIVATE-PROMPT','secret-cookie'): self.assertNotIn(secret,text)

    def test_config_guard_and_mode_off(self):
        import copy
        key='K'*32
        base={'routes':{'a':{'url':'https://chatgpt.com/backend-api/codex','model':'actual','protocol':'responses'}},'default_route':'a','gateway_key_env':'TEST_GATEWAY_KEY'}
        with patch.dict('os.environ',{'TEST_GATEWAY_KEY':key}):
            for url in ('https://chatgpt.com.evil/backend-api/codex','https://chatgpt.com:443/backend-api/codex','https://user@chatgpt.com/backend-api/codex','https://chatgpt.com/backend-api/codex?x=1','http://chatgpt.com/backend-api/codex','https://chatgpt.com/backend-api/codex/responses'):
                cfg=copy.deepcopy(base); cfg['routes']['a']['url']=url
                with self.assertRaises(ValueError): omr.handler(cfg)
            cfg=copy.deepcopy(base); cfg['routes']['b']={**cfg['routes']['a'],'model':'different'}
            with self.assertRaises(ValueError): omr.handler(cfg)
        with patch.dict('os.environ',{'TEST_GATEWAY_KEY':'short'}):
            with self.assertRaises(ValueError): omr.handler(base)
        local={'routes':{'a':{'url':'http://127.0.0.1:1/v1','model':'a','protocol':'responses'}},'default_route':'a'}
        with serve(omr.handler(local)) as port:
            client=http.client.HTTPConnection('127.0.0.1',port,timeout=2); client.request('GET','/backend-api/codex/models'); response=client.getresponse(); self.assertEqual(response.status,404); response.read(); client.close()

    def test_redirect_is_not_followed(self):
        from http.server import BaseHTTPRequestHandler
        seen=[]
        class Backend(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                seen.append(self.path); self.send_response(302); self.send_header('Location','https://evil.invalid/steal'); self.send_header('Content-Length','0'); self.end_headers()
        config={'routes':{'a':{'url':'https://chatgpt.com/backend-api/codex','model':'actual','protocol':'responses'}},'default_route':'a','gateway_key_env':'TEST_GATEWAY_KEY'}
        with serve(Backend) as upstream, patch.dict('os.environ',{'TEST_GATEWAY_KEY':'K'*32}):
            real=http.client.HTTPConnection
            with patch.object(omr.http.client,'HTTPSConnection',side_effect=lambda host,port,timeout:real('127.0.0.1',upstream,timeout=timeout)), serve(omr.handler(config)) as gateway:
                c=real('127.0.0.1',gateway,timeout=2)
                c.request('GET','/backend-api/codex/models',headers={'X-OMR-Gateway-Key':'K'*32,'Authorization':'Bearer synthetic','chatgpt-account-id':'a'})
                r=c.getresponse(); self.assertEqual(r.status,502); r.read(); c.close()
                self.assertEqual(seen,['/backend-api/codex/models'])

    def test_native_stream_disconnect_cancels_upstream(self):
        import json, select, threading
        from http.server import BaseHTTPRequestHandler
        closed=threading.Event()
        class Backend(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self):
                body=json.dumps({'models':[{'slug':'actual','default_reasoning_level':'low','supported_reasoning_levels':[{'effort':'low'}]}]}).encode()
                self.send_response(200); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(200); self.send_header('Content-Type','text/event-stream'); self.end_headers()
                self.wfile.write(b'data: {"type":"response.created"}\n\n'); self.wfile.flush()
                ready,_,_=select.select([self.connection],[],[],3)
                if ready and not self.connection.recv(1): closed.set()
        cfg={'routes':{'a':{'url':'https://chatgpt.com/backend-api/codex','model':'actual','protocol':'responses'}},'default_route':'a','gateway_key_env':'TEST_GATEWAY_KEY','timeout_seconds':5}
        with serve(Backend) as upstream, patch.dict('os.environ',{'TEST_GATEWAY_KEY':'K'*32}):
            real=http.client.HTTPConnection
            with patch.object(omr.http.client,'HTTPSConnection',side_effect=lambda host,port,timeout:real('127.0.0.1',upstream,timeout=timeout)), serve(omr.handler(cfg)) as gateway:
                headers={'X-OMR-Gateway-Key':'K'*32,'Authorization':'Bearer synthetic','chatgpt-account-id':'a'}
                c=real('127.0.0.1',gateway,timeout=2); c.request('GET','/backend-api/codex/models',headers=headers); r=c.getresponse(); self.assertEqual(r.status,200); r.read(); c.close()
                c=real('127.0.0.1',gateway,timeout=2); c.request('POST','/backend-api/codex/responses',json.dumps({'model':'open-model-router','stream':True}),{**headers,'Content-Type':'application/json','session_id':'12345678-1234-4234-8234-123456789abc'}); r=c.getresponse(); self.assertEqual(r.status,200); self.assertIn(b'response.created',r.readline()); r.close(); c.close(); self.assertTrue(closed.wait(1.5))

    def test_session_routing_is_isolated_by_account(self):
        import json, uuid
        from http.server import BaseHTTPRequestHandler
        class Backend(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self):
                body=json.dumps({'models':[{'slug':'actual','default_reasoning_level':'low','supported_reasoning_levels':[{'effort':'low'},{'effort':'high'}]}]}).encode()
                self.send_response(200); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length'])); body=b'{"model":"actual"}'
                self.send_response(200); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
        route={'url':'https://chatgpt.com/backend-api/codex','model':'actual','protocol':'responses'}
        cfg={'routes':{'a':{**route,'effort':'low'},'b':{**route,'effort':'high'}},'default_route':'a','gateway_key_env':'TEST_GATEWAY_KEY','decision':{'type':'command','command':['unused'],'public_prompts':True}}
        with serve(Backend) as upstream, patch.dict('os.environ',{'TEST_GATEWAY_KEY':'K'*32}):
            real=http.client.HTTPConnection
            with patch.object(omr.http.client,'HTTPSConnection',side_effect=lambda host,port,timeout:real('127.0.0.1',upstream,timeout=timeout)), patch.object(omr,'command_decision',side_effect=lambda decision,prompt,stopped,deadline:{'route':prompt}), serve(omr.handler(cfg)) as gateway:
                session=str(uuid.uuid4())
                for account,prompt in [('one','a'),('two','b'),('one','b'),('two','a')]:
                    h={'X-OMR-Gateway-Key':'K'*32,'Authorization':'Bearer synthetic','chatgpt-account-id':account,'session_id':session}
                    c=real('127.0.0.1',gateway,timeout=2); c.request('GET','/backend-api/codex/models',headers=h); r=c.getresponse(); self.assertEqual(r.status,200); r.read(); c.close()
                    c=real('127.0.0.1',gateway,timeout=2); c.request('POST','/backend-api/codex/responses',json.dumps({'model':'open-model-router','input':prompt}),{**h,'Content-Type':'application/json'}); r=c.getresponse(); self.assertEqual(r.status,200); self.assertEqual(r.getheader('X-OMR-Route'),'a' if account=='one' else 'b'); r.read(); c.close()


    def test_review_security_boundaries(self):
        import contextlib, io, json, tempfile, time
        from pathlib import Path
        from http.server import BaseHTTPRequestHandler
        markers = ('synthetic-bearer-marker', 'synthetic-account-marker', 'synthetic-key-marker-' + 'K'*32)
        seen = []
        class Backend(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                seen.append('GET')
                body=json.dumps({'models':[{'slug':'actual','default_reasoning_level':'low','supported_reasoning_levels':[{'effort':'low'}]}]}).encode()
                self.send_response(200); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length'])); seen.append('POST')
                mode=self.headers.get('originator')
                body=(' '.join(markers)).encode()
                if mode == 'stream':
                    body = b'data: {"type":"response.created"}\n\n' + b'event: error\ndata: ' + json.dumps({'type':'error','error':{'message':' '.join(markers)}}).encode() + b'\n\n'
                    status=200
                else: status=int(mode)
                self.send_response(status); self.send_header('Location','https://evil.invalid/'); self.send_header('Content-Type','text/event-stream' if mode=='stream' else 'application/json'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
        cfg={'routes':{'a':{'url':'https://chatgpt.com/backend-api/codex','model':'actual','protocol':'responses'}},'default_route':'a','gateway_key_env':'TEST_GATEWAY_KEY'}
        with tempfile.TemporaryDirectory() as directory, serve(Backend) as upstream, patch.dict('os.environ',{'TEST_GATEWAY_KEY':markers[2]}):
            cfg['receipts']=str(Path(directory,'receipts')); real=http.client.HTTPConnection
            stderr=io.StringIO()
            with contextlib.redirect_stderr(stderr), patch.object(omr.http.client,'HTTPSConnection',side_effect=lambda host,port,timeout:real('127.0.0.1',upstream,timeout=timeout)), serve(omr.handler(cfg)) as gateway:
                headers={'X-OMR-Gateway-Key':markers[2],'Authorization':'Bearer '+markers[0],'chatgpt-account-id':markers[1]}
                def request(method, headers, body=None):
                    c=real('127.0.0.1',gateway,timeout=3); c.request(method,'/backend-api/codex/models' if method=='GET' else '/backend-api/codex/responses',body,headers); r=c.getresponse(); result=(r.status,dict(r.getheaders()),r.read()); c.close(); return result
                self.assertEqual(request('GET',headers)[0],200)
                for blocked in ('Authorization','chatgpt-account-id'):
                    before=len(seen); self.assertEqual(request('GET',{**headers,'Connection':blocked})[0],400); self.assertEqual(len(seen),before)
                base={**headers,'Content-Type':'application/json','session_id':'12345678-1234-4234-8234-123456789abc'}
                payload=json.dumps({'model':'open-model-router','stream':True})
                for mode,expected in [('400',400),('503',503),('302',502),('stream',200)]:
                    status, response_headers, body=request('POST',{**base,'originator':mode},payload)
                    self.assertEqual(status,expected); self.assertNotIn('Location',response_headers)
                    for marker in markers: self.assertNotIn(marker.encode(),body)
                    if mode=='stream': self.assertIn(b'response.created',body); self.assertIn(b'error',body)
                for bad in ({'session_id':''}, {'session_id':'not-a-uuid'}, {'X-OMR-Session':'22345678-1234-4234-8234-123456789abc'}, {'Connection':'Authorization'}):
                    before=len(seen); self.assertEqual(request('POST',{**base,**bad},payload)[0],400); self.assertEqual(len(seen),before)
                missing=dict(base); del missing['session_id']
                self.assertEqual(request('POST',missing,payload)[0],400)
                # Duplicate header fields must not be collapsed by the HTTP client.
                c=real('127.0.0.1',gateway,timeout=3); c.putrequest('POST','/backend-api/codex/responses')
                for k,v in base.items(): c.putheader(k,v)
                c.putheader('session_id',base['session_id']); c.putheader('Content-Length',str(len(payload))); c.endheaders(payload.encode())
                r=c.getresponse(); self.assertEqual(r.status,400); r.read(); c.close()
                c=real('127.0.0.1',gateway,timeout=3); c.putrequest('POST','/backend-api/codex/responses')
                for k,v in base.items(): c.putheader(k,v)
                c.putheader('X-OMR-Session',base['session_id']); c.putheader('X-OMR-Session',base['session_id']); c.putheader('Content-Length',str(len(payload))); c.endheaders(payload.encode())
                r=c.getresponse(); self.assertEqual(r.status,400); r.read(); c.close()
            for _ in range(50):
                if Path(cfg['receipts']).exists() and len(Path(cfg['receipts']).read_text().splitlines()) >= 10: break
                time.sleep(.01)
            text=Path(cfg['receipts']).read_text()+stderr.getvalue()
            for marker in markers: self.assertNotIn(marker,text)


if __name__ == "__main__": unittest.main()
