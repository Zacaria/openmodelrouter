import os,sys,json,time,signal,select,subprocess,pathlib,hashlib,secrets,threading,http.client
P=pathlib.Path(__file__).resolve().parent; parent=P.parent; core=parent/'omr.py'
SHA='ec9c11ac447bf37eb5919d98e535d4c91b82a0b39e36202030d01fd8b8eabb0c'
assert hashlib.sha256(core.read_bytes()).hexdigest()==SHA
sid='01a17bd1-7a2a-77e3-b368-7330bedd8b7c'; valid='a613b532-750f-4663-92cc-33aada43c022'; invalid='not-a-uuid'
if len(sys.argv)>1:
 sys.path.insert(0,str(parent)); import omr
 orig=http.client.HTTPSConnection.request; count=[0]; lock=threading.Lock()
 def guarded(self,method,url,*a,**kw):
  if method=='POST' and url=='/backend-api/codex/responses':
   with lock:
    count[0]+=1
    with open(P/'upstream-count.jsonl','a') as f:f.write(json.dumps({'generation_attempt':count[0]})+'\n')
    if count[0]>1: raise OSError('generation limit')
  return orig(self,method,url,*a,**kw)
 http.client.HTTPSConnection.request=guarded
 line=next(i for i,s in enumerate(core.read_text().splitlines(),1) if 'event_frame.clear(); event_kind' in s)
 def trace(f,e,a):
  if e=='line' and f.f_code.co_filename==str(core):
   if f.f_code.co_name=='reply' and f.f_locals.get('status')==400:
    h=f.f_locals['self']; session=h.headers.get('X-OMR-Session');
    with open(P/'local-reject.jsonl','a') as out:out.write(json.dumps({'status':400,'path':h.path,'session_invalid':session==invalid,'peer':h.client_address[0]})+'\n')
   if f.f_code.co_name=='do_POST' and f.f_lineno==line:
    ev=f.f_locals.get('event'); typ=ev.get('type') if isinstance(ev,dict) else None
    if typ=='response.completed':
     with open(P/'terminal.jsonl','a') as out:out.write(json.dumps({'type':typ,'forwarded_after_flush':True})+'\n')
  return trace
 threading.settrace(trace); sys.argv=[str(core),'serve','--config',str(P/'gateway.json'),'--port','0']; omr.main(); sys.exit()
env=os.environ.copy(); env['OMR_TEST_GATEWAY_KEY']=secrets.token_urlsafe(48)
cfg={'routes':{'native':{'url':'https://chatgpt.com/backend-api/codex','protocol':'responses','model':'gpt-6.1-terra','effort':'low','forward_auth':True}},'default_route':'native','decision':{'type':'fixed'},'gateway_key_env':'OMR_TEST_GATEWAY_KEY','receipts':str(P/'receipts.private'),'timeout_seconds':80}
(P/'gateway.json').write_text(json.dumps(cfg)); os.chmod(P/'gateway.json',0o600)
ps=[]; result={'core_sha256':SHA,'candidate':'7e25c6e7e6547fb9d3bf1f2f1d71602dd3950f3b','thread_id':sid,'valid_session':valid,'invalid_session':invalid,'turns':[]}
def stop(p):
 try:os.killpg(p.pid,signal.SIGTERM)
 except ProcessLookupError:pass
 try:p.wait(timeout=3)
 except subprocess.TimeoutExpired:
  try:os.killpg(p.pid,signal.SIGKILL)
  except ProcessLookupError:pass
  p.wait(timeout=3)
def gone(p):
 try:os.killpg(p.pid,0);return False
 except ProcessLookupError:return True
def run(label,base,session,timeout):
 e=env.copy();e['OMR_TEST_SESSION']=session
 opts=['--ignore-user-config','--disable','enable_request_compression','--sandbox','read-only','--skip-git-repo-check','--json','-C',str(parent/'project'),'-m','open-model-router','-c','project_doc_max_bytes=0','-c','model_provider="omr"','-c','model_providers.omr.name="OpenAI"','-c',f'model_providers.omr.base_url="{base}"','-c','model_providers.omr.requires_openai_auth=true','-c','model_providers.omr.supports_websockets=false','-c','model_providers.omr.request_max_retries=0','-c','model_providers.omr.stream_max_retries=0','-c','model_providers.omr.env_http_headers={"X-OMR-Gateway-Key"="OMR_TEST_GATEWAY_KEY","X-OMR-Session"="OMR_TEST_SESSION"}','-c','model_reasoning_effort="low"']
 p=subprocess.Popen(['/opt/homebrew/bin/codex','exec']+opts+['resume',sid,'Reply with one word: RECOVERED.'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True,env=e);ps.append(p);started=time.monotonic()
 try:out,err=p.communicate(timeout=timeout);reason='exit'
 except subprocess.TimeoutExpired:stop(p);out,err=p.communicate();reason='timeout'
 events=[]
 for raw in out.splitlines():
  try:v=json.loads(raw)
  except ValueError:continue
  row={'type':v.get('type')}; item=v.get('item') or {}
  if item.get('type'):row['item_type']=item['type']
  if v.get('thread_id'):row['thread_id']=v['thread_id']
  if v.get('type')=='turn.completed':row['usage']=v.get('usage')
  events.append(row)
 (P/(label+'-events.jsonl')).write_text(''.join(json.dumps(x)+'\n' for x in events))
 low=(out+' '+err).lower(); cats=[x for x in ('unexpected status','400 bad request','invalid_request','stream disconnected','authentication','timed out','rate limit') if x in low]
 r={'label':label,'returncode':p.returncode,'reason':reason,'elapsed_seconds':round(time.monotonic()-started,3),'events':events,'error_categories':cats,'stderr_bytes':len(err.encode()),'group_absent':gone(p)};result['turns'].append(r);return r
try:
 gw=subprocess.Popen(['/opt/homebrew/bin/python3.11',str(P/'closure.py'),'serve'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,start_new_session=True,env=env);ps.append(gw)
 if not select.select([gw.stdout],[],[],5)[0]:raise RuntimeError('gateway startup timeout')
 port=int(gw.stdout.readline());result['gateway_port']=port;result['gateway_host']='127.0.0.1';base=f'http://127.0.0.1:{port}/backend-api/codex'
 bad=run('error',base,invalid,45)
 result['upstream_generation_after_error']=len((P/'upstream-count.jsonl').read_text().splitlines()) if (P/'upstream-count.jsonl').exists() else 0
 rejects=[json.loads(x) for x in (P/'local-reject.jsonl').read_text().splitlines()] if (P/'local-reject.jsonl').exists() else []
 assert result['upstream_generation_after_error']==0 and rejects and all(x['session_invalid'] and x['status']==400 for x in rejects), 'local invalid session rejection not established'
 run('recovery',base,valid,90)
except Exception as e:result['operator_error']=type(e).__name__+': '+str(e)
finally:
 for p in reversed(ps):stop(p)
 result['owned_groups_absent']=all(gone(p) for p in ps)
 r=P/'receipts.private';rows=[]
 if r.exists():
  for x in r.read_text().splitlines():
   z=json.loads(x);rows.append({k:z.get(k) for k in ('session','status','upstream_status','route','model_requested','model_observed','effort_transmitted','usage')})
  r.unlink()
 result['receipts']=rows;result['core_post_sha256']=hashlib.sha256(core.read_bytes()).hexdigest();(P/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
